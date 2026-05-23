from __future__ import annotations

import ast
import json
from pathlib import Path


ENGINES_DIR = Path(__file__).resolve().parents[1] / "services" / "shinsegye" / "engines120"
MANIFEST_PATH = ENGINES_DIR / "engines120_manifest.json"


def _load_manifest() -> list[dict]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8-sig"))


def test_manifest_has_120_slots() -> None:
    manifest = _load_manifest()
    assert len(manifest) == 120
    slots = sorted(int(entry["slot"]) for entry in manifest)
    assert slots == list(range(1, 121))


def test_all_manifest_files_exist_and_are_non_empty() -> None:
    manifest = _load_manifest()
    missing: list[str] = []
    empty: list[str] = []
    for entry in manifest:
        target = ENGINES_DIR / str(entry["target_file"])
        if not target.exists():
            missing.append(str(target.name))
            continue
        if target.stat().st_size <= 0:
            empty.append(str(target.name))

    assert not missing, f"missing engine files: {missing}"
    assert not empty, f"empty engine files: {empty}"


def test_all_engine_files_are_python_parseable() -> None:
    manifest = _load_manifest()
    parse_failures: list[str] = []

    for entry in manifest:
        target = ENGINES_DIR / str(entry["target_file"])
        source = target.read_text(encoding="utf-8")
        try:
            ast.parse(source, filename=str(target))
        except SyntaxError as exc:
            parse_failures.append(f"{target.name}: {exc.msg} ({exc.lineno}:{exc.offset})")

    assert not parse_failures, "\n".join(parse_failures)
