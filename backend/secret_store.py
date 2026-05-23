import os
from pathlib import Path


def _read_dotenv_value(name: str) -> str:
    dotenv_path = Path(os.getenv("CODEAI_ENV_PATH", "/app/.env"))
    if not dotenv_path.exists() or not dotenv_path.is_file():
        return ""
    try:
        for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in raw_line:
                continue
            key, value = raw_line.split("=", 1)
            if key.strip() == name:
                return value.strip()
    except Exception:
        return ""
    return ""


def read_secret_env(name: str, default: str = "") -> str:
    configured = str(os.getenv(name) or "").strip()
    if configured:
        return configured

    dotenv_value = _read_dotenv_value(name)
    if dotenv_value:
        return dotenv_value

    file_path = str(os.getenv(f"{name}_FILE") or "").strip()
    if not file_path:
        return default

    try:
        return Path(file_path).read_text(encoding="utf-8").strip()
    except Exception:
        return default