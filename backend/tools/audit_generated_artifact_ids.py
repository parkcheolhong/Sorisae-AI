from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES = {
    ".py",
    ".pyi",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".scss",
    ".sh",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".env",
    ".txt",
    ".go",
    ".rs",
}
SOURCE_FILENAMES = {"Dockerfile", "Makefile"}
EXCLUDED_PARTS = {
    ".delivery-venv",
    ".zip-venv",
    "__pycache__",
    ".pytest_cache",
    ".pytest-tmp",
    "node_modules",
    ".next",
    "runtime",
    "cache",
}
TS_STYLE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx", ".css", ".scss"}
LINE_COMMENT_PREFIX_MARKERS = ["# FILE-ID:", "# SECTION-ID:", "# FEATURE-ID:", "# CHUNK-ID:"]
BLOCK_COMMENT_MARKERS = ["FILE-ID:", "SECTION-ID:", "FEATURE-ID:", "CHUNK-ID:"]


def _normalize_relative_path(value: str) -> str:
    return str(value or "").strip().replace("\\", "/")


def _is_excluded(relative_path: str) -> bool:
    parts = [part for part in _normalize_relative_path(relative_path).split("/") if part]
    return any(part in EXCLUDED_PARTS for part in parts)


def _is_audit_target(relative_path: str) -> bool:
    normalized = _normalize_relative_path(relative_path)
    if not normalized or normalized.startswith("docs/") or _is_excluded(normalized):
        return False
    path = Path(normalized)
    if path.name in SOURCE_FILENAMES:
        return True
    return path.suffix.lower() in SOURCE_SUFFIXES


def _load_written_files(output_dir: Path) -> list[str]:
    traceability_path = output_dir / "docs" / "traceability_map.json"
    if not traceability_path.exists():
        raise FileNotFoundError(f"traceability map not found: {traceability_path}")
    payload = json.loads(traceability_path.read_text(encoding="utf-8"))
    written_files = payload.get("written_files") or []
    return [
        normalized
        for normalized in (_normalize_relative_path(item) for item in written_files)
        if normalized
    ]


def _iter_audit_targets(output_dir: Path, written_files: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for relative_path in written_files:
        if not _is_audit_target(relative_path):
            continue
        if relative_path in seen:
            continue
        file_path = output_dir / relative_path
        if not file_path.is_file():
            continue
        seen.add(relative_path)
        deduped.append(relative_path)
    return deduped


def _has_required_markers(relative_path: str, text: str) -> bool:
    head = text[:400]
    suffix = Path(relative_path).suffix.lower()
    if suffix in TS_STYLE_SUFFIXES:
        return all(marker in head for marker in BLOCK_COMMENT_MARKERS)
    return all(marker in head for marker in LINE_COMMENT_PREFIX_MARKERS)


def audit_output(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    written_files = _load_written_files(output_dir)
    audit_targets = _iter_audit_targets(output_dir, written_files)
    missing: list[str] = []
    for relative_path in audit_targets:
        file_path = output_dir / relative_path
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if not _has_required_markers(relative_path, text):
            missing.append(relative_path)
    return {
        "output_dir": str(output_dir),
        "written_files_count": len(written_files),
        "audit_target_count": len(audit_targets),
        "missing_count": len(missing),
        "missing": missing,
        "excluded_prefixes": sorted(EXCLUDED_PARTS),
        "ok": len(missing) == 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir")
    args = parser.parse_args()
    target = Path(args.output_dir)
    if not target.is_absolute():
        target = ROOT / target
    print(json.dumps(audit_output(target), ensure_ascii=False))


if __name__ == "__main__":
    main()
