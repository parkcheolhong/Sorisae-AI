#!/usr/bin/env python3
"""Feature-engine isolation gate.

Detect forbidden cross-imports between Sorisae, face modules, and VoIP relay.
Acts as a self-diagnosis guard and prints concrete auto-fix hints.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "apps/mobile-nadotongryoksa/src/features"

IMPORT_RE = re.compile(
    r"^\s*import(?:\s+type)?\s+.*?from\s+['\"]([^'\"]+)['\"]"
)

RULES = {
    "sorisae": (
        "../face-interpretation/",
        "../face-conversation/",
        "../voip-voice-relay/",
    ),
    "face-interpretation": ("../sorisae/",),
    "face-conversation": ("../sorisae/",),
    "voip-voice-relay": (
        "../sorisae/",
        "../face-interpretation/",
        "../face-conversation/",
    ),
}

AUTO_FIX_HINTS = {
    "../face-interpretation/faceConversationTiming": (
        "../shared/audioConversationTiming"
    ),
    "../face-interpretation/faceConversationAudioRoute": (
        "../shared/audioRouteKernel"
    ),
    "../face-conversation/faceConversationVadController": (
        "../shared/audioControllerTypes"
    ),
}


def _iter_ts_files(folder: Path):
    if not folder.exists():
        return
    for file_path in folder.rglob("*.ts"):
        rel = file_path.relative_to(ROOT).as_posix()
        if "/dist/" in rel:
            continue
        yield file_path
    for file_path in folder.rglob("*.tsx"):
        rel = file_path.relative_to(ROOT).as_posix()
        if "/dist/" in rel:
            continue
        yield file_path


def _collect_violations() -> list[tuple[str, int, str, str]]:
    violations: list[tuple[str, int, str, str]] = []
    for engine, forbidden_prefixes in RULES.items():
        for file_path in _iter_ts_files(SRC / engine):
            rel = file_path.relative_to(ROOT).as_posix()
            try:
                lines = file_path.read_text(encoding="utf-8").splitlines()
            except UnicodeDecodeError:
                lines = file_path.read_text(
                    encoding="utf-8", errors="ignore"
                ).splitlines()
            for index, line in enumerate(lines, start=1):
                match = IMPORT_RE.search(line)
                if not match:
                    continue
                import_path = match.group(1)
                for prefix in forbidden_prefixes:
                    if import_path.startswith(prefix):
                        violations.append((rel, index, import_path, engine))
                        break
    return violations


def _print_hints(import_path: str) -> None:
    if replacement := AUTO_FIX_HINTS.get(import_path):
        print(f"      auto-fix-hint: {import_path} -> {replacement}")


def main() -> int:
    violations = _collect_violations()
    if not violations:
        print("[PASS] feature engine isolation")
        print("  forbidden cross-imports: none")
        return 0

    print("[FAIL] feature engine isolation")
    for rel, line_no, import_path, engine in violations:
        print(
            f"  - {rel}:{line_no} [{engine}] "
            f"imports forbidden path {import_path}"
        )
        _print_hints(import_path)
    print(f"\nSummary: {len(violations)} violation(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
