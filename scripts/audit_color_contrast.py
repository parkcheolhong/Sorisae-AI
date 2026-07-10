"""WCAG 2.1 색대비 전수점검 — 관광 UI(모바일 일정패널·데이터출처 모달·admin 검수).

법·윤리·품질 체크리스트 '다양성·포함성(접근성)' 항목.
- 각 텍스트색/배경색 쌍의 대비비(contrast ratio)를 계산해 AA 기준 충족 여부 판정.
  · 일반 텍스트 AA: ≥ 4.5:1
  · 큰 텍스트(≥24px 또는 ≥19px 굵게) AA: ≥ 3.0:1
- 리포트 출력 + reports/color_contrast_audit.json 저장. 미달 1건이상이면 exit 1(게이트).
"""

from __future__ import annotations

import json
import os
import sys
from typing import List, Tuple

REPORT_PATH = os.path.join("reports", "color_contrast_audit.json")


def _srgb_to_lin(c: float) -> float:
    c = c / 255.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.2126 * _srgb_to_lin(r) + 0.7152 * _srgb_to_lin(g) + 0.0722 * _srgb_to_lin(b)


def contrast_ratio(fg: str, bg: str) -> float:
    l1, l2 = _luminance(fg), _luminance(bg)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


# (영역, 설명, 전경색, 배경색, px, bold)
PAIRS: List[Tuple[str, str, str, str, int, bool]] = [
    # ── 모바일: 일정 패널 ──
    ("itinerary", "title", "#e6edf3", "#0b1622", 15, True),
    ("itinerary", "subtitle", "#79c0ff", "#0b1622", 12, False),
    ("itinerary", "hint", "#8b9bad", "#0b1622", 12, False),
    ("itinerary", "label", "#a9b7c6", "#0b1622", 12, False),
    ("itinerary", "summary", "#e6edf3", "#0b1622", 14, True),
    ("itinerary", "error", "#ff9b9b", "#0b1622", 13, False),
    ("itinerary", "disclosure", "#8b9bad", "#0b1622", 11, False),
    ("itinerary", "attribution", "#79889a", "#0b1622", 10, False),
    ("itinerary", "input-text", "#e6edf3", "#08121d", 14, False),
    ("itinerary", "placeholder", "#79889a", "#08121d", 14, False),
    ("itinerary", "consentText", "#c2cedb", "#10202e", 12, False),
    ("itinerary", "consentBtnText", "#a9b7c6", "#0d2236", 12, True),
    ("itinerary", "dayBtnText", "#a9b7c6", "#0d2236", 13, True),
    ("itinerary", "dayCardTitle", "#79c0ff", "#08121d", 14, True),
    ("itinerary", "placeName", "#e6edf3", "#08121d", 14, True),
    ("itinerary", "placeBlurb", "#c2cedb", "#08121d", 13, False),
    ("itinerary", "placeMeta", "#8b9bad", "#08121d", 12, False),
    ("itinerary", "mapLinkText", "#79c0ff", "#0d2a4a", 12, True),
    ("itinerary", "kgTitle", "#c9a6ff", "#161029", 13, True),
    ("itinerary", "kgLabel", "#b08bff", "#161029", 12, True),
    ("itinerary", "kgName", "#e6edf3", "#161029", 13, True),
    ("itinerary", "kgDesc", "#a99cc4", "#161029", 12, False),
    ("itinerary", "kgFoods", "#ddd3f0", "#161029", 13, False),
    ("itinerary", "tipsTitle", "#9be8b3", "#0d1f14", 13, True),
    ("itinerary", "tipText", "#cfe8d6", "#0d1f14", 13, False),
    # ── 모바일: 데이터 출처 모달 ──
    ("data-sources", "text", "#e6edf3", "#151b23", 14, True),
    ("data-sources", "intro/sub", "#8b949e", "#151b23", 13, False),
    ("data-sources", "usage", "#8b949e", "#0b1622", 12, False),
    ("data-sources", "link", "#79c0ff", "#0b1622", 12, False),
    ("data-sources", "licenseText", "#79c0ff", "#0d2236", 11, True),
    # ── admin: 관광 검수 페이지 ──
    ("admin-review", "body-text", "#e6edf3", "#0d1117", 14, False),
    ("admin-review", "sub", "#8b949e", "#0d1117", 12, False),
    ("admin-review", "accent", "#79c0ff", "#0d1117", 14, True),
    ("admin-review", "stats-green", "#9be8b3", "#161b22", 13, False),
    ("admin-review", "card-muted", "#8b949e", "#161b22", 13, False),
]


def is_large(px: int, bold: bool) -> bool:
    return px >= 24 or (px >= 19 and bold)


def main() -> int:
    rows = []
    failures = 0
    for area, name, fg, bg, px, bold in PAIRS:
        ratio = contrast_ratio(fg, bg)
        large = is_large(px, bold)
        threshold = 3.0 if large else 4.5
        ok = ratio >= threshold
        if not ok:
            failures += 1
        rows.append({
            "area": area, "name": name, "fg": fg, "bg": bg, "px": px, "bold": bold,
            "ratio": round(ratio, 2), "threshold": threshold, "large": large, "pass": ok,
        })

    print(f"WCAG AA 색대비 점검 — {len(rows)}쌍, 통과 {len(rows) - failures} / 미달 {failures}\n")
    print(f"{'AREA':<14}{'NAME':<16}{'FG':<9}{'BG':<9}{'RATIO':>7}{'  REQ':>6}  RESULT")
    print("-" * 72)
    for r in rows:
        mark = "OK " if r["pass"] else "FAIL"
        print(f"{r['area']:<14}{r['name']:<16}{r['fg']:<9}{r['bg']:<9}{r['ratio']:>7}{r['threshold']:>6}  {mark}")

    os.makedirs("reports", exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({"total": len(rows), "failures": failures, "rows": rows}, f, ensure_ascii=False, indent=2)
    print(f"\n리포트 저장: {REPORT_PATH}")

    if failures:
        print(f"\n[FAIL] AA 미달 {failures}건 — 색 토큰 교정 필요")
        return 1
    print("\n[OK] 전 항목 AA 충족")
    return 0


if __name__ == "__main__":
    sys.exit(main())
