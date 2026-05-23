from __future__ import annotations

from pathlib import Path

from backend.movie_studio.utils.path_tools import ensure_directory


def studio_asset_root() -> Path:
    return ensure_directory(Path(__file__).resolve().parents[2] / "uploads" / "tmp" / "movie_studio_assets")
