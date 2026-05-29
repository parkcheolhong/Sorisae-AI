"""마켓플레이스 데이터베이스 연결 설정"""
import os
import socket
import threading
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect as sqlalchemy_inspect, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.secret_store import read_secret_env


def _candidate_env_paths() -> list[Path]:
    current = Path(__file__).resolve()
    return [
        current.parents[2] / ".env",
        current.parents[1] / ".env",
    ]


def _read_plain_env_value(name: str, default: str = "") -> str:
    configured = str(os.getenv(name) or "").strip()
    if configured:
        return configured
    for env_path in _candidate_env_paths():
        if not env_path.exists() or not env_path.is_file():
            continue
        try:
            for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key.strip() == name:
                    return value.strip()
        except Exception:
            continue
    return default


def _host_resolves(host: str) -> bool:
    normalized = str(host or "").strip()
    if not normalized:
        return False
    try:
        socket.getaddrinfo(normalized, None)
        return True
    except OSError:
        return False


def _host_accepts_tcp(host: str, port: int, timeout: float = 0.35) -> bool:
    normalized = str(host or "").strip()
    if not normalized:
        return False
    try:
        with socket.create_connection((normalized, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def _is_unusable_container_sqlite_url(database_url: str) -> bool:
    try:
        parsed = make_url(database_url)
    except Exception:
        return False

    if parsed.get_backend_name() != "sqlite":
        return False

    target = str(parsed.database or "").replace("\\", "/")
    return os.name != "nt" and len(target) >= 3 and target[1] == ":" and target[2] == "/"


def _is_container_runtime() -> bool:
    return Path("/.dockerenv").exists()


def _normalize_container_postgres_url(database_url: str) -> str:
    try:
        parsed = make_url(database_url)
    except Exception:
        return database_url

    backend_name = parsed.get_backend_name()
    if not backend_name.startswith("postgresql"):
        return database_url

    host = str(parsed.host or "").strip().lower()
    if host not in {"localhost", "127.0.0.1", "::1"}:
        return database_url

    configured_host = _read_plain_env_value("POSTGRES_HOST", "postgres") or "postgres"
    configured_host = str(configured_host).strip() or "postgres"
    if configured_host.lower() in {"localhost", "127.0.0.1", "::1"}:
        configured_host = "postgres"

    rewritten = parsed.set(host=configured_host)
    return rewritten.render_as_string(hide_password=False)


def _resolve_database_url() -> str:
    configured = read_secret_env("DATABASE_URL") or _read_plain_env_value("DATABASE_URL")
    if configured:
        if _is_unusable_container_sqlite_url(configured):
            configured = ""
        else:
            if _is_container_runtime():
                configured = _normalize_container_postgres_url(configured)
            return configured

    user = _read_plain_env_value("POSTGRES_USER", "admin") or "admin"
    password = read_secret_env("POSTGRES_PASSWORD", _read_plain_env_value("POSTGRES_PASSWORD", "changeme"))
    configured_host = _read_plain_env_value("POSTGRES_HOST", "postgres") or "postgres"
    host_aliases = [
        value.strip()
        for value in _read_plain_env_value("POSTGRES_HOST_ALIASES", "localhost,host.docker.internal").split(",")
        if value.strip()
    ]
    port = _read_plain_env_value("POSTGRES_PORT", "5432") or "5432"
    candidate_hosts = []
    for candidate in [configured_host, *host_aliases]:
        normalized = str(candidate or "").strip()
        if normalized and normalized not in candidate_hosts:
            candidate_hosts.append(normalized)

    host = configured_host
    reachable_candidates = [
        candidate for candidate in candidate_hosts
        if _host_resolves(candidate) and _host_accepts_tcp(candidate, int(port))
    ]
    if reachable_candidates:
        host = reachable_candidates[0]
    elif configured_host == "postgres" and not _host_resolves(configured_host):
        for candidate in candidate_hosts[1:]:
            if _host_resolves(candidate):
                host = candidate
                break

    database_name = _read_plain_env_value("POSTGRES_DB", "devanalysis114") or "devanalysis114"
    return (
        f"postgresql://{quote_plus(user)}:{quote_plus(password)}"
        f"@{host}:{port}/{quote_plus(database_name)}"
    )


def _mask_database_url(database_url: str) -> str:
    try:
        parsed = make_url(database_url)
        return parsed.render_as_string(hide_password=True)
    except Exception:
        return database_url


DATABASE_URL = _resolve_database_url()


def _build_engine_kwargs(database_url: str) -> tuple[str, dict]:
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,
        "pool_timeout": 10,
    }

    try:
        parsed = make_url(database_url)
    except Exception:
        return database_url, engine_kwargs

    backend_name = parsed.get_backend_name()
    if backend_name.startswith("postgresql"):
        query = dict(parsed.query)
        query.setdefault("connect_timeout", "5")
        query.setdefault("application_name", "codeai-backend")
        parsed = parsed.set(query=query)
        return parsed.render_as_string(hide_password=False), engine_kwargs

    return database_url, engine_kwargs


Base = declarative_base()
RESOLVED_DATABASE_URL, ENGINE_KWARGS = _build_engine_kwargs(DATABASE_URL)
_ENGINE_LOCK = threading.Lock()
_ENGINE_INSTANCE: Engine | None = None
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
)


def add_missing_columns(
    connection: Connection,
    table_name: str,
    columns: dict[str, str],
    *,
    inspector=None,
) -> bool:
    active_inspector = inspector or sqlalchemy_inspect(connection)
    if not active_inspector.has_table(table_name):
        return False

    existing_columns = {
        column["name"]
        for column in active_inspector.get_columns(table_name)
    }
    for column_name, column_type in columns.items():
        if column_name in existing_columns:
            continue
        connection.execute(
            text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        )
    return True


def _get_or_create_engine() -> Engine:
    global _ENGINE_INSTANCE
    if _ENGINE_INSTANCE is None:
        with _ENGINE_LOCK:
            if _ENGINE_INSTANCE is None:
                # 테스트 수집 단계에서는 실제 DB 드라이버 로딩을 늦춘다.
                _ENGINE_INSTANCE = create_engine(RESOLVED_DATABASE_URL, **ENGINE_KWARGS)
                SessionLocal.configure(bind=_ENGINE_INSTANCE)
    return _ENGINE_INSTANCE


class _LazyEngineProxy:
    def __getattr__(self, name: str):
        return getattr(_get_or_create_engine(), name)

    def __repr__(self) -> str:
        return repr(_get_or_create_engine())


engine = _LazyEngineProxy()

# SQLAlchemy 2.x inspection 등록: inspect(engine) 호출 시 실제 Engine 반환
try:
    from sqlalchemy import inspection as _sa_inspection

    @_sa_inspection._inspects(_LazyEngineProxy)
    def _inspect_lazy_engine_proxy(subject: _LazyEngineProxy):
        return sqlalchemy_inspect(_get_or_create_engine())
except Exception:
    pass


def get_db():
    """데이터베이스 세션 의존성"""
    _get_or_create_engine()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """데이터베이스 초기화"""
    from . import models  # noqa: F401
    from . import subscription_models  # noqa: F401

    Base.metadata.create_all(bind=_get_or_create_engine())


def check_database_availability() -> tuple[bool, str]:
    try:
        with _get_or_create_engine().connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return True, "database connection ok"
    except SQLAlchemyError as exc:
        return False, f"database unavailable via {_mask_database_url(RESOLVED_DATABASE_URL)} :: {exc}"
    except Exception as exc:
        return False, f"database unavailable via {_mask_database_url(RESOLVED_DATABASE_URL)} :: {exc}"