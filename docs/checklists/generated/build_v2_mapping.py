import csv
import json
import re
from pathlib import Path

root = Path(r"c:/Users/WORK/source/repos/parkcheolhong/codeAI")
sorisae = root / "tmp/external_migrations/run_all_shinsegye.py"
outdir = root / "docs/checklists/generated"
outdir.mkdir(parents=True, exist_ok=True)

patterns_primary = [
    (r"interpreter|translation|multilingual", "통역/언어"),
    (r"music|composer|audio|voice|sound", "음악/오디오"),
    (r"code|dev|program|coding", "코드/개발"),
    (r"dashboard|ui|web|frontend|streamlit", "대시보드/UI"),
    (r"api|router|server|endpoint", "API/서버"),
    (r"brain|cognitive|memory|learning|evolution", "브레인/학습"),
    (r"security|auth|permission|policy", "보안/권한"),
    (r"monitor|observ|telemetry|health|status", "운영관측/헬스"),
    (r"data|db|storage|vector|qdrant", "데이터/저장소"),
    (r"agent|orchestr|workflow|automation", "오케스트레이션/에이전트"),
    (r"test|verify|validate|check", "검증/테스트"),
]
patterns_secondary = [
    (r"chat|conversation|dialog", "대화"),
    (r"tts|stt|speech|voice", "음성"),
    (r"image|vision|camera|opencv", "비전"),
    (r"iot|sensor|device|arduino", "IoT"),
    (r"blockchain|crypto|wallet", "블록체인"),
    (r"recommend|ranking|search", "추천/검색"),
    (r"pipeline|queue|worker|job", "배치/큐"),
    (r"security|auth|token|jwt", "인증보안"),
    (r"game|simulation", "시뮬레이션"),
    (r"market|commerce|purchase", "마켓"),
]

rows = []
for p in sorisae.rglob("*.py"):
    if "__pycache__" in p.parts:
        continue
    rel = p.relative_to(sorisae).as_posix()
    stem = p.stem.lower()
    primary = "기타"
    for pat, name in patterns_primary:
        if re.search(pat, stem):
            primary = name
            break
    secondary = "기타-미분류"
    for pat, name in patterns_secondary:
        if re.search(pat, stem):
            secondary = name
            break
    rows.append((rel, primary, secondary))

rows.sort(key=lambda x: x[0])
with (outdir / "sorisae_file_secondary_classification.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["file", "primary_category", "secondary_category"])
    w.writerows(rows)

etc_rows = [r for r in rows if r[1] == "기타"]
with (outdir / "sorisae_etc_243_secondary_table.md").open("w", encoding="utf-8") as f:
    f.write("# 소리새 기타군 2차 분류표 (자동생성)\n\n")
    f.write("| 파일 | 1차분류 | 2차분류 |\n")
    f.write("| --- | --- | --- |\n")
    for rel, pcat, scat in etc_rows:
        f.write(f"| {rel} | {pcat} | {scat} |\n")

engine_re = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", re.M)
engines = []
for p in sorisae.rglob("*.py"):
    if "__pycache__" in p.parts:
        continue
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for name in engine_re.findall(txt):
        if re.search(r"Engine|System|Module|Brain", name):
            eid = f"ENG-{len(engines)+1:03d}"
            engines.append({
                "engine_id": eid,
                "engine_class": name,
                "file": p.relative_to(sorisae).as_posix(),
            })

api = []
router_dir = root / "backend/marketplace"
for p in router_dir.glob("*router*.py"):
    txt = p.read_text(encoding="utf-8", errors="ignore")
    for m in re.finditer(r"@(router|marketplace_router)\.(get|post|put|delete|patch)\(\s*\"([^\"]+)\"", txt):
        method = m.group(2).upper()
        path = m.group(3)
        if not path.startswith("/"):
            path = "/" + path
        api.append({"method": method, "path": "/api/marketplace" + path, "router_file": p.name})

tests = [p.name for p in (root / "frontend/frontend/tests").glob("*.spec.ts")]

for e in engines:
    n = e["engine_class"].lower()
    mapped_api = []
    if any(k in n for k in ["interpreter", "translation", "language"]):
        mapped_api = [a for a in api if "interpreter" in a["path"]]
    elif any(k in n for k in ["music", "audio", "voice", "sound"]):
        mapped_api = [a for a in api if "music" in a["path"]]
    elif any(k in n for k in ["code", "dev", "coding", "program"]):
        mapped_api = [a for a in api if "code-generator" in a["path"]]
    elif any(k in n for k in ["search", "rank", "recommend"]):
        mapped_api = [a for a in api if "search" in a["path"] or "stats" in a["path"]]
    else:
        mapped_api = [a for a in api if any(x in a["path"] for x in ["orchestrate", "feature", "customer", "campaign"])][:2]

    e["api_mapping"] = "; ".join(sorted({f"{a['method']} {a['path']}" for a in mapped_api})) if mapped_api else "미매핑"
    e["ui_mapping"] = "/marketplace/code-generator" if any(k in n for k in ["interpreter", "translation", "music", "audio", "code", "dev", "coding"]) else "미노출"
    related_tests = [t for t in tests if any(k in t.lower() for k in ["shinsegye", "music", "generator", "marketplace"])]
    e["test_mapping"] = "; ".join(sorted(related_tests[:4])) if related_tests else "미매핑"

with (outdir / "engine_api_ui_test_mapping_v2.csv").open("w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["engine_id", "engine_class", "file", "api_mapping", "ui_mapping", "test_mapping"])
    w.writeheader()
    w.writerows(engines)

with (outdir / "mapping_summary.json").open("w", encoding="utf-8") as f:
    json.dump(
        {
            "total_py": len(rows),
            "etc_count": len(etc_rows),
            "engine_candidates": len(engines),
            "api_count": len(api),
            "test_count": len(tests),
        },
        f,
        ensure_ascii=False,
        indent=2,
    )

print(f"TOTAL_PY={len(rows)}")
print(f"ETC_COUNT={len(etc_rows)}")
print(f"ENGINE_CANDIDATES={len(engines)}")
print(f"API_COUNT={len(api)}")
print(f"TEST_COUNT={len(tests)}")
