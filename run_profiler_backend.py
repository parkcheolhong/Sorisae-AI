from __future__ import annotations

import ipaddress
import logging
import os
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ["ENABLE_AD_ORDER_WORKER_BOOTSTRAP"] = "false"
os.environ["ENABLE_AD_ORDER_RUNTIME_RECOVERY_BOOTSTRAP"] = "false"
os.environ["ENABLE_SELF_RUN_VIDEO_WORKER_BOOTSTRAP"] = "false"
os.environ["ORCH_FORCE_COMPLETE"] = "false"
os.environ["QDRANT_REST_ONLY"] = "true"
os.environ["QDRANT_PREFER_GRPC"] = "false"

from backend.main import app  # noqa: E402


logger = logging.getLogger(__name__)


def _is_container_runtime() -> bool:
    return (
        Path("/.dockerenv").exists()
        or Path("/run/.containerenv").exists()
        or bool(os.getenv("KUBERNETES_SERVICE_HOST"))
    )


def _default_profiler_host() -> str:
    return "127.0.0.1"


def _resolve_profiler_host() -> str:
    requested_host = (os.getenv("BACKEND_PROFILER_HOST") or _default_profiler_host()).strip()
    allow_remote = (os.getenv("BACKEND_PROFILER_ALLOW_REMOTE", "") or "").strip().lower() in {"1", "true", "yes", "on"}
    if requested_host == "localhost":
        try:
            infos = socket.getaddrinfo("localhost", None)
            if infos and all(ipaddress.ip_address(info[4][0]).is_loopback for info in infos):
                return requested_host
        except Exception:
            logger.warning("[WARN] failed to resolve localhost loopback addresses", exc_info=True)
        logger.warning("[WARN] localhost does not resolve to loopback only; fallback to 127.0.0.1")
        return "127.0.0.1"
    if requested_host in {"127.0.0.1", "::1"}:
        return requested_host
    try:
        requested_ip = ipaddress.ip_address(requested_host)
    except (TypeError, ValueError):
        logger.warning("[WARN] hostname profiler host=%s is not allowed; fallback to 127.0.0.1", requested_host)
        return "127.0.0.1"
    if requested_ip.is_loopback:
        return requested_host
    if allow_remote:
        if requested_ip.is_unspecified:
            logger.warning("[WARN] profiler backend is binding to all interfaces (host=%s)", requested_host)
        return requested_host
    logger.warning("[WARN] remote profiler host=%s blocked; set BACKEND_PROFILER_ALLOW_REMOTE=true to allow", requested_host)
    return "127.0.0.1"


def _can_bind(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def _resolve_bind_port(host: str, requested_port: int, max_attempts: int = 20) -> int:
    if _can_bind(host, requested_port):
        return requested_port
    for offset in range(1, max_attempts + 1):
        candidate = requested_port + offset
        if _can_bind(host, candidate):
            logger.warning(
                "[WARN] requested port %s is already in use; falling back to %s",
                requested_port,
                candidate,
            )
            os.environ["BACKEND_PROFILER_EFFECTIVE_PORT"] = str(candidate)
            return candidate
    raise RuntimeError(
        f"사용 가능한 포트를 찾지 못했습니다. 시작 포트={requested_port}, 검사 범위={requested_port + max_attempts}"
    )


def main() -> None:
    import uvicorn

    host = _resolve_profiler_host()
    port = _resolve_bind_port(host, int(os.getenv("BACKEND_PROFILER_PORT", "8000")))
    logger.info("[OK] profiler backend bind target: http://%s:%s", host, port)
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
