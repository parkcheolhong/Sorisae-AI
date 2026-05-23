#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
IGNORED_PREFIXES = (
    "uploads/",
    "tmp/",
    "node_modules/",
)

UNCHECKED_RE = re.compile(r"^\s*[-*]\s*\[\s\]\s+")
CHECKED_RE = re.compile(r"^\s*[-*]\s*\[(?:x|X)\]\s+")
ITEM_STATUS_COMPLETE_RE = re.compile(r"^\s*[-*]\s*상태\s*:\s*완료됨\s*$")
TOP_STATUS_COMPLETE_RE = re.compile(r"^\s*(?:현재\s*)?상태\s*:\s*완료됨\s*$")
EVIDENCE_RE = re.compile(r"^\s*[-*]\s*근거\s*:\s*.+")
PENDING_RE = re.compile(r"대기|차단|미완료|미해결|기록\s*대기|TODO", re.IGNORECASE)


@dataclass
class Finding:
    path: Path
    line: int
    message: str


def _run_git(args: List[str]) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def normalize_line(line: str) -> str:
    return line.replace("**", "").strip()


def is_checklist_markdown(path: Path) -> bool:
    normalized = path.as_posix()
    if any(normalized.startswith(prefix) for prefix in IGNORED_PREFIXES):
        return False
    return path.suffix.lower() == ".md" and "checklist" in path.name.lower()


def collect_target_files(args: argparse.Namespace) -> List[Path]:
    if args.files:
        return [Path(p) for p in args.files if is_checklist_markdown(Path(p))]

    if args.all:
        tracked = _run_git(["ls-files"]).splitlines()
        return [Path(p) for p in tracked if is_checklist_markdown(Path(p))]

    if args.base and args.head and not set(args.base) == {"0"}:
        changed = _run_git(["diff", "--name-only", args.base, args.head])
        return [
            Path(p)
            for p in changed.splitlines()
            if is_checklist_markdown(Path(p))
        ]

    tracked = _run_git(["ls-files"]).splitlines()
    return [Path(p) for p in tracked if is_checklist_markdown(Path(p))]


def find_unchecked_lines(lines: List[str]) -> List[int]:
    result: List[int] = []
    for idx, line in enumerate(lines, start=1):
        if UNCHECKED_RE.match(line):
            result.append(idx)
    return result


def find_item_status_complete_lines(lines: List[str]) -> List[int]:
    result: List[int] = []
    for idx, line in enumerate(lines, start=1):
        if ITEM_STATUS_COMPLETE_RE.match(normalize_line(line)):
            result.append(idx)
    return result


def check_file(path: Path) -> List[Finding]:
    findings: List[Finding] = []
    abs_path = REPO_ROOT / path
    if not abs_path.exists():
        return findings

    lines = abs_path.read_text(encoding="utf-8", errors="replace").splitlines()
    normalized = [normalize_line(line) for line in lines]
    unchecked_lines = find_unchecked_lines(lines)
    item_complete_lines = find_item_status_complete_lines(lines)

    # Rule 1: Unchecked item cannot be followed by item-level "상태: 완료됨".
    for unchecked_line in unchecked_lines:
        window_end = min(unchecked_line + 3, len(lines))
        for idx in range(unchecked_line + 1, window_end + 1):
            if ITEM_STATUS_COMPLETE_RE.match(normalized[idx - 1]):
                findings.append(
                    Finding(
                        path=path,
                        line=unchecked_line,
                        message="미체크 항목([ ])에 '상태: 완료됨'이 연결되어 있습니다.",
                    )
                )
                break

    # Rule 2: Top-level completed state cannot coexist with unchecked boxes.
    top_scan_limit = min(40, len(lines))
    top_has_completed = any(
        TOP_STATUS_COMPLETE_RE.match(normalized[idx])
        for idx in range(top_scan_limit)
    )
    if top_has_completed and unchecked_lines:
        findings.append(
            Finding(
                path=path,
                line=unchecked_lines[0],
                message="문서 상단 상태가 '완료됨'인데 미체크 항목([ ])이 남아 있습니다.",
            )
        )

    # Rule 2b: Top-level completed state cannot coexist with pending/blocking wording.
    if top_has_completed:
        for idx, text in enumerate(normalized, start=1):
            if PENDING_RE.search(text):
                findings.append(
                    Finding(
                        path=path,
                        line=idx,
                        message="문서 상단 상태가 '완료됨'인데 대기/차단/미해결/TODO/기록 대기 표현이 남아 있습니다.",
                    )
                )
                break

    # Rule 3: item-level 완료됨 must belong to a checked [x] item.
    for status_line in item_complete_lines:
        search_start = max(1, status_line - 4)
        owner_line = None
        for idx in range(status_line - 1, search_start - 1, -1):
            line = lines[idx - 1]
            if CHECKED_RE.match(line) or UNCHECKED_RE.match(line):
                owner_line = idx
                break
        if owner_line is None:
            findings.append(
                Finding(
                    path=path,
                    line=status_line,
                    message="'상태: 완료됨'에 대응되는 체크 항목([x])을 찾을 수 없습니다.",
                )
            )
            continue
        owner_text = lines[owner_line - 1]
        if not CHECKED_RE.match(owner_text):
            findings.append(
                Finding(
                    path=path,
                    line=owner_line,
                    message="미체크 항목([ ]) 또는 비정상 항목에 '상태: 완료됨'이 연결되어 있습니다.",
                )
            )

    # Rule 4: item-level 완료됨 must have nearby evidence.
    for status_line in item_complete_lines:
        evidence_found = False
        for idx in range(status_line + 1, min(len(lines), status_line + 5) + 1):
            if EVIDENCE_RE.match(normalized[idx - 1]):
                evidence_found = True
                break
        if not evidence_found:
            findings.append(
                Finding(
                    path=path,
                    line=status_line,
                    message="'상태: 완료됨' 아래 근거 항목이 없습니다. 최소 1개 근거가 필요합니다.",
                )
            )

    # Rule 5: 완료됨 cannot coexist with pending/blocking wording in the same item block.
    for status_line in item_complete_lines:
        block_end = min(len(lines), status_line + 5)
        for idx in range(status_line + 1, block_end + 1):
            text = normalized[idx - 1]
            if PENDING_RE.search(text):
                findings.append(
                    Finding(
                        path=path,
                        line=idx,
                        message="완료됨 항목 블록에 대기/차단/미해결 표현이 포함되어 있습니다.",
                    )
                )
                break

    return findings


def main(argv: Iterable[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Checklist consistency hard gate",
    )
    parser.add_argument("--base", help="git diff base sha", default="")
    parser.add_argument("--head", help="git diff head sha", default="")
    parser.add_argument(
        "--all",
        action="store_true",
        help="scan all tracked checklist files",
    )
    parser.add_argument("--files", nargs="*", help="explicit checklist file paths")
    args = parser.parse_args(list(argv))

    try:
        targets = collect_target_files(args)
    except subprocess.CalledProcessError as exc:
        print("[checklist-gate] git command failed:", exc, file=sys.stderr)
        return 2

    if not targets:
        print("[checklist-gate] 대상 체크리스트 파일이 없어 통과합니다.")
        return 0

    all_findings: List[Finding] = []
    for path in sorted(set(targets), key=lambda p: p.as_posix()):
        all_findings.extend(check_file(path))

    if not all_findings:
        print(f"[checklist-gate] 정합성 검사 통과 ({len(set(targets))} files)")
        return 0

    print("[checklist-gate] 정합성 위반 발견:")
    for finding in all_findings:
        print(f"- {finding.path.as_posix()}:{finding.line}: {finding.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
