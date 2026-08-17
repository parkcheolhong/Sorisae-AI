from __future__ import annotations

from pathlib import Path

from backend.movie_studio.storage.studio_asset_store import studio_asset_root
from backend.movie_studio.utils.path_tools import ensure_directory


def scene_bundle_root(project_id: str) -> Path:
    return ensure_directory(studio_asset_root() / project_id / "scene_bundles")
