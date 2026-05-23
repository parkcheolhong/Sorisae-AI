import csv
from pathlib import Path

root = Path(r"c:/Users/WORK/source/repos/parkcheolhong/codeAI")
csv_path = root / "docs/checklists/generated/engine_api_ui_test_mapping_v2.csv"
md_path = root / "docs/checklists/shinsegye-engine-api-ui-test-mapping-v2-20260430.md"
rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))

with md_path.open("w", encoding="utf-8") as f:
    f.write("# 신세계 엔진 ID to API to UI to 테스트 100% 매핑표 v2 (2026-04-30)\n\n")
    f.write("- 본 문서는 엔진 후보 99건 전수에 대해 최소 1개 이상의 API/UI/테스트 매핑 필드를 채운 v2 기준표다.\n")
    f.write("- 매핑 필드 값이 `미노출` 또는 `미매핑`인 경우도 전수 매핑 행 자체는 포함한다.\n\n")
    f.write("| 엔진ID | 엔진클래스 | 파일 | API 매핑 | UI 매핑 | 테스트 매핑 |\n")
    f.write("| --- | --- | --- | --- | --- | --- |\n")
    for r in rows:
        vals = [
            r["engine_id"],
            r["engine_class"],
            r["file"],
            r["api_mapping"],
            r["ui_mapping"],
            r["test_mapping"],
        ]
        vals = [v.replace("|", "\\|") for v in vals]
        f.write("| " + " | ".join(vals) + " |\n")

print("WROTE {}".format(md_path))
print("ROWS={}".format(len(rows)))
