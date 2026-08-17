import json
import os
import re
import shutil
import tempfile
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

_CODE_GENERATOR_HISTORY_LIMIT = 30
_CODE_GENERATOR_HISTORY_LOCK = threading.Lock()


def _resolve_marketplace_upload_root() -> Path:
    configured_root = (os.getenv("MARKETPLACE_UPLOAD_ROOT", "") or "").strip()
    if configured_root:
        if os.name != "nt" and re.match(r"^[A-Za-z]:[\\/]", configured_root):
            mounted_upload_root = Path("/app/uploads")
            if mounted_upload_root.exists():
                return mounted_upload_root.resolve()
        return Path(configured_root).expanduser().resolve()
    workspace_root = Path(__file__).resolve().parents[2]
    return (workspace_root / "uploads").resolve()


def _resolve_code_generator_root() -> Path:
    root = (_resolve_marketplace_upload_root() / "code_generator").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _resolve_code_generator_history_file() -> Path:
    return (_resolve_code_generator_root() / "history.json").resolve()


def _resolve_code_generator_artifacts_root() -> Path:
    root = (_resolve_code_generator_root() / "artifacts").resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _read_history_payload() -> dict[str, Any]:
    history_file = _resolve_code_generator_history_file()
    if not history_file.exists():
        return {"users": {}}
    try:
        payload = json.loads(history_file.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and isinstance(payload.get("users"), dict):
            return payload
    except Exception:
        pass
    return {"users": {}}


def _write_history_payload(payload: dict[str, Any]) -> None:
    history_file = _resolve_code_generator_history_file()
    history_file.parent.mkdir(parents=True, exist_ok=True)
    history_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _resolve_user_history_key(current_user: Any) -> str:
    user_id = getattr(current_user, "id", None)
    username = str(getattr(current_user, "username", "") or "").strip()
    if isinstance(user_id, int):
        return f"user:{user_id}"
    if username:
        return f"username:{username}"
    return "anonymous"


def _safe_project_slug(name: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", (name or "project").strip())
    normalized = normalized.strip("-._")
    return normalized[:64] or "project"


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in metadata.items()
        if isinstance(value, (str, int, float, bool, list))
    }


def _list_user_history(current_user: Any) -> list[dict[str, Any]]:
    user_key = _resolve_user_history_key(current_user)
    with _CODE_GENERATOR_HISTORY_LOCK:
        payload = _read_history_payload()
        users = payload.get("users") if isinstance(payload, dict) else None
        if not isinstance(users, dict):
            return []
        entries = users.get(user_key)
        if not isinstance(entries, list):
            return []
        return [entry for entry in entries if isinstance(entry, dict)]


def _store_user_history_entry(current_user: Any, entry: dict[str, Any]) -> None:
    user_key = _resolve_user_history_key(current_user)
    with _CODE_GENERATOR_HISTORY_LOCK:
        payload = _read_history_payload()
        users = payload.setdefault("users", {})
        entries = users.get(user_key)
        if not isinstance(entries, list):
            entries = []
        entries.insert(0, entry)
        users[user_key] = entries[:_CODE_GENERATOR_HISTORY_LIMIT]
        _write_history_payload(payload)


def build_code_generator_router(contract: Any) -> APIRouter:
    router = APIRouter()

    @router.get("/code-generator/profiles")
    def list_code_generator_profiles() -> dict[str, Any]:
        try:
            from backend.non_python_code_generator import SUPPORTED_NON_PYTHON_PROFILES
            from backend.python_code_generator import SUPPORTED_PYTHON_PROFILES
        except Exception:
            return {"python": [], "non_python": [], "multi": False}
        return {
            "python": sorted(list(SUPPORTED_PYTHON_PROFILES)),
            "non_python": sorted(list(SUPPORTED_NON_PYTHON_PROFILES)),
            "multi": True,
        }

    @router.post("/code-generator/generate")
    def generate_code_project(
        payload: dict[str, Any],
        current_user=Depends(contract.get_current_user),
    ) -> dict[str, Any]:
        project_name = str(payload.get("project_name") or "my-project").strip()
        task = str(payload.get("task") or "").strip()
        profile = str(payload.get("profile") or "python_fastapi").strip()
        if not task:
            raise HTTPException(status_code=400, detail="task 필수")
        output_dir = Path(tempfile.mkdtemp(prefix="codegen_"))
        try:
            from backend.generators.facade import generate_non_python_project_bundle, generate_python_project_bundle
            from backend.non_python_code_generator import SUPPORTED_NON_PYTHON_PROFILES
            from backend.python_code_generator import SUPPORTED_PYTHON_PROFILES

            if profile in SUPPORTED_PYTHON_PROFILES:
                result = generate_python_project_bundle(
                    project_name=project_name,
                    profile=profile,
                    task=task,
                    output_dir=output_dir,
                )
            elif profile in SUPPORTED_NON_PYTHON_PROFILES:
                result = generate_non_python_project_bundle(
                    project_name=project_name,
                    profile=profile,
                    task=task,
                    output_dir=output_dir,
                )
            else:
                raise HTTPException(status_code=400, detail=f"지원되지 않는 프로필: {profile}")

            generation_id = str(uuid4())
            created_at = datetime.now(timezone.utc).isoformat()
            project_slug = _safe_project_slug(project_name)
            artifact_root = (_resolve_code_generator_artifacts_root() / generation_id).resolve()
            artifact_root.mkdir(parents=True, exist_ok=True)
            zip_filename = f"{project_slug}-{generation_id[:8]}.zip"
            zip_path = (artifact_root / zip_filename).resolve()
            with zipfile.ZipFile(zip_path, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
                for source_file in output_dir.rglob("*"):
                    if source_file.is_file():
                        archive.write(source_file, arcname=source_file.relative_to(output_dir).as_posix())

            written_files = list(result.written_files or [])
            if not written_files:
                written_files = [
                    path.relative_to(output_dir).as_posix()
                    for path in output_dir.rglob("*")
                    if path.is_file()
                ]

            history_entry = {
                "generation_id": generation_id,
                "project_name": project_name,
                "profile": profile,
                "task_preview": task[:180],
                "file_count": len(written_files),
                "files": written_files[:50],
                "created_at": created_at,
                "zip_filename": zip_filename,
            }
            _store_user_history_entry(current_user, history_entry)

            return {
                "project_name": project_name,
                "profile": profile,
                "task": task,
                "file_count": len(written_files),
                "files": written_files[:50],
                "metadata": _safe_metadata(result.metadata),
                "generation_id": generation_id,
                "created_at": created_at,
                "download_url": f"/api/marketplace/code-generator/download/{generation_id}",
            }
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        finally:
            shutil.rmtree(output_dir, ignore_errors=True)

    @router.get("/code-generator/history")
    def list_code_generation_history(
        current_user=Depends(contract.get_current_user),
    ) -> dict[str, Any]:
        entries = _list_user_history(current_user)
        return {
            "items": [
                {
                    "generation_id": str(entry.get("generation_id") or ""),
                    "project_name": str(entry.get("project_name") or ""),
                    "profile": str(entry.get("profile") or ""),
                    "task_preview": str(entry.get("task_preview") or ""),
                    "file_count": int(entry.get("file_count") or 0),
                    "created_at": str(entry.get("created_at") or ""),
                    "download_url": f"/api/marketplace/code-generator/download/{str(entry.get('generation_id') or '')}",
                }
                for entry in entries
                if entry.get("generation_id")
            ]
        }

    @router.get("/code-generator/download/{generation_id}")
    def download_code_generation_zip(
        generation_id: str,
        current_user=Depends(contract.get_current_user),
    ):
        normalized_generation_id = str(generation_id or "").strip()
        if not re.fullmatch(r"[0-9a-fA-F-]{8,64}", normalized_generation_id):
            raise HTTPException(status_code=400, detail="잘못된 generation_id 형식")

        entries = _list_user_history(current_user)
        matched = next(
            (entry for entry in entries if str(entry.get("generation_id") or "") == normalized_generation_id),
            None,
        )
        if matched is None:
            raise HTTPException(status_code=404, detail="생성 이력을 찾을 수 없습니다")

        zip_filename = str(matched.get("zip_filename") or "").strip()
        if not zip_filename:
            raise HTTPException(status_code=404, detail="ZIP 정보가 없습니다")

        artifacts_root = _resolve_code_generator_artifacts_root()
        zip_path = (artifacts_root / normalized_generation_id / zip_filename).resolve()
        if not str(zip_path).startswith(str(artifacts_root)):
            raise HTTPException(status_code=400, detail="ZIP 경로 검증 실패")
        if not zip_path.exists() or not zip_path.is_file():
            raise HTTPException(status_code=404, detail="ZIP 파일을 찾을 수 없습니다")

        return FileResponse(
            path=str(zip_path),
            media_type="application/zip",
            filename=zip_filename,
        )

    return router