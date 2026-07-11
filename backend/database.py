"""공용 백엔드 데이터베이스 호환 레이어"""
import re

from sqlalchemy import inspect, text

from backend.marketplace.database import Base, SessionLocal, check_database_availability, engine, get_db


def add_missing_columns(connection, table_name: str, column_specs: dict[str, str], *, inspector) -> set[str]:
    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    added_columns: set[str] = set()
    is_sqlite = connection.dialect.name == "sqlite"

    for column_name, column_type in column_specs.items():
        if column_name in existing_columns:
            continue
        ddl_type = column_type
        if is_sqlite:
            # SQLite cannot add a column with an inline UNIQUE constraint.
            ddl_type = re.sub(r"\s+UNIQUE\b", "", ddl_type, flags=re.IGNORECASE)
        connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl_type}"))
        added_columns.add(column_name)

    return added_columns


def ensure_user_role_columns() -> None:
    """기존 users 테이블에 관리자 권한 및 가입 유형 컬럼이 없으면 추가한다."""
    inspector = inspect(engine)
    if not inspector.has_table("users"):
        return

    with engine.begin() as connection:
        added_columns = add_missing_columns(
            connection,
            "users",
            {
                "is_active": "BOOLEAN NOT NULL DEFAULT TRUE",
                "is_admin": "BOOLEAN NOT NULL DEFAULT FALSE",
                "is_superuser": "BOOLEAN NOT NULL DEFAULT FALSE",
                "member_type": "VARCHAR(30) NOT NULL DEFAULT 'individual'",
                "business_name": "VARCHAR(200)",
                "business_registration_number": "VARCHAR(50)",
                "representative_name": "VARCHAR(120)",
                "preferred_language": "VARCHAR(16)",
                "country_code": "VARCHAR(8)",
                "phone_number": "VARCHAR(40)",
                "is_staff": "BOOLEAN NOT NULL DEFAULT FALSE",
                "passkey_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
                "passkey_credential_id": "VARCHAR(255) UNIQUE",
                "passkey_public_key": "TEXT",
                "passkey_device_label": "VARCHAR(120)",
                "passkey_sign_count": "INTEGER NOT NULL DEFAULT 0",
                "passkey_registered_at": "TIMESTAMP",
                "native_language": "VARCHAR(10)",
                "country": "VARCHAR(10)",
            },
            inspector=inspector,
        )
        if "phone_number" in added_columns:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_users_phone_number ON users (phone_number)"))
        if connection.dialect.name == "sqlite" and "passkey_credential_id" in added_columns:
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_passkey_credential_id "
                "ON users (passkey_credential_id)"
            ))


def ensure_traceability_schema() -> None:
    """기존 주요 테이블에 trace 컬럼을 추가하고 새 추적 테이블을 생성한다."""
    from backend.marketplace import models  # noqa: F401
    from backend.mobile.song_translation import models as mobile_song_translation_models  # noqa: F401

    Base.metadata.create_all(bind=engine)

    inspector = inspect(engine)
    table_column_specs = {
        "customer_orchestrator_completions": {
            "trace_id": "VARCHAR(120)",
            "flow_id": "VARCHAR(40)",
            "step_id": "VARCHAR(40)",
            "action": "VARCHAR(80)",
        },
        "ad_video_orders": {
            "trace_id": "VARCHAR(120)",
            "flow_id": "VARCHAR(40)",
            "step_id": "VARCHAR(40)",
            "action": "VARCHAR(80)",
        },
    }

    with engine.begin() as connection:
        for table_name, columns in table_column_specs.items():
            if not inspector.has_table(table_name):
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, column_type in columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))

        if inspector.has_table("feature_execution_logs"):
            existing_columns = {column["name"] for column in inspector.get_columns("feature_execution_logs")}
            feature_execution_columns = {
                "feature_id": "VARCHAR(100)",
                "entity_type": "VARCHAR(80)",
                "entity_id": "VARCHAR(120)",
                "run_id": "VARCHAR(120)",
                "prompt": "TEXT",
                "message": "TEXT",
                "payload_json": "TEXT",
                "output_payload_json": "TEXT",
                "error_message": "TEXT",
            }
            for column_name, column_type in feature_execution_columns.items():
                if column_name in existing_columns:
                    continue
                connection.execute(text(
                    f"ALTER TABLE feature_execution_logs ADD COLUMN {column_name} {column_type}"
                ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET feature_id = COALESCE(NULLIF(feature_id, ''), entity_type, 'feature_execution')"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET entity_type = COALESCE(NULLIF(entity_type, ''), feature_id, 'feature_execution')"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET entity_id = COALESCE(NULLIF(entity_id, ''), run_id, trace_id, CAST(id AS TEXT))"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET message = COALESCE(NULLIF(message, ''), error_message, prompt, '')"
            ))
            connection.execute(text(
                "UPDATE feature_execution_logs SET payload_json = COALESCE(payload_json, output_payload_json)"
            ))

        if inspector.has_table("feature_retry_queue"):
            feature_retry_columns = {column["name"] for column in inspector.get_columns("feature_retry_queue")}
            feature_retry_column_specs = {
                "user_id": "INTEGER",
                "feature_id": "VARCHAR(100)",
                "entity_type": "VARCHAR(80)",
                "entity_id": "VARCHAR(120)",
                "queue_name": "VARCHAR(80)",
                "last_error": "TEXT",
                "attempt_count": "INTEGER",
                "max_attempts": "INTEGER",
                "retry_count": "INTEGER",
            }
            for column_name, column_type in feature_retry_column_specs.items():
                if column_name in feature_retry_columns:
                    continue
                connection.execute(
                    text(f"ALTER TABLE feature_retry_queue ADD COLUMN {column_name} {column_type}")
                )
            connection.execute(text(
                "UPDATE feature_retry_queue SET feature_id = COALESCE(NULLIF(feature_id, ''), entity_type, queue_name, 'feature_retry')"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET entity_type = COALESCE(NULLIF(entity_type, ''), feature_id, 'feature_retry')"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET entity_id = COALESCE(NULLIF(entity_id, ''), trace_id, CAST(id AS TEXT))"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET queue_name = COALESCE(NULLIF(queue_name, ''), feature_id, 'feature_retry_queue')"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET attempt_count = COALESCE(attempt_count, retry_count, 0)"
            ))
            connection.execute(text(
                "UPDATE feature_retry_queue SET max_attempts = COALESCE(max_attempts, 3)"
            ))