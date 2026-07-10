import os
from pathlib import Path


def _candidate_dotenv_paths() -> list[Path]:
    explicit = str(os.getenv("CODEAI_ENV_PATH", "")).strip()
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))

    candidates.extend(
        [
            Path("/app/.env"),
            Path(__file__).resolve().parents[1] / ".env",
        ]
    )

    unique: list[Path] = []
    for path in candidates:
        if path not in unique:
            unique.append(path)
    return unique


def _read_dotenv_value(name: str) -> str:
    for dotenv_path in _candidate_dotenv_paths():
        if not dotenv_path.exists() or not dotenv_path.is_file():
            continue
        try:
            for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in raw_line:
                    continue
                key, value = raw_line.split("=", 1)
                if key.strip() == name:
                    return value.strip()
        except Exception:
            continue
    return ""


def _candidate_secret_file_paths(file_path: str) -> list[Path]:
    raw = str(file_path or "").strip()
    if not raw:
        return []

    primary = Path(raw)
    candidates: list[Path] = [primary]

    # When helper scripts run on host, /run/codeai-secrets/* isn't mounted.
    # Map to repo-local secret mirror (.runtime/secrets/*) as fallback.
    normalized = raw.replace("\\", "/")
    secret_prefix = "/run/codeai-secrets/"
    if normalized.startswith(secret_prefix):
        relative = normalized[len(secret_prefix):].lstrip("/")
        repo_secret = Path(__file__).resolve().parents[1] / ".runtime" / "secrets" / relative
        candidates.append(repo_secret)

    unique: list[Path] = []
    for path in candidates:
        if path not in unique:
            unique.append(path)
    return unique


def read_secret_env(name: str, default: str = "") -> str:
    configured = str(os.getenv(name) or "").strip()
    if configured:
        return configured

    dotenv_value = _read_dotenv_value(name)
    if dotenv_value:
        return dotenv_value

    file_path = str(os.getenv(f"{name}_FILE") or "").strip()
    if not file_path:
        file_path = _read_dotenv_value(f"{name}_FILE")
    if not file_path:
        return default

    for candidate in _candidate_secret_file_paths(file_path):
        try:
            if candidate.exists() and candidate.is_file():
                return candidate.read_text(encoding="utf-8").strip()
        except Exception:
            continue
    return default