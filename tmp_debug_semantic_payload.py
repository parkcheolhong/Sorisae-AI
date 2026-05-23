import json
import datetime
import requests

BASE = "http://127.0.0.1:8000"

s = requests.Session()
login = s.post(
    f"{BASE}/api/auth/login",
    data={"username": "ui.admin.round@devanalysis.local", "password": "RoundUi!20260426"},
    timeout=30,
)
login.raise_for_status()
headers = {"Authorization": "Bearer " + login.json()["access_token"]}

name = "debug-semantic-" + datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
task = f"""[고객 주문 생성 요청]\n- 상품 ID: stock-ai-autotrader\n- 카테고리: ai엔진군 주식매매프로그램\n- 도메인: finance\n- 유형: custom-order\n- 실행명: {name}\n- 요구 기능: 시그널, 리스크가드, 주문실행, 포트폴리오 API, 테스트, ZIP\n\n[추가 조건]\nsource_path: /app\nPython FastAPI 기반 실프로젝트 구조로 생성하고 AI 엔진 기본 탑재, 실검증/출고 문서 포함.\n"""
payload = {"task": task, "mode": "full", "project_name": name}

create = s.post(f"{BASE}/api/marketplace/customer-orchestrate/stage-runs", json=payload, headers=headers, timeout=30)
create.raise_for_status()
stage = create.json()
payload["stage_run_id"] = stage.get("run_id")
payload["stage_id"] = stage.get("current_stage_id") or "ARCH-001"

accepted = s.post(f"{BASE}/api/marketplace/customer-orchestrate/accepted", json=payload, headers=headers, timeout=30)
accepted.raise_for_status()

stream = s.post(f"{BASE}/api/marketplace/customer-orchestrate/stream", json=payload, headers=headers, timeout=7200)
stream.raise_for_status()

result_event = None
for raw in stream.text.splitlines():
    line = raw.strip()
    if not line.startswith("data:"):
        continue
    txt = line.split(":", 1)[1].strip()
    if not txt:
        continue
    try:
        ev = json.loads(txt)
    except Exception:
        continue
    if ev.get("event") == "result":
        result_event = ev

if result_event is None:
    raise RuntimeError("No result event found")

result = (result_event.get("payload") or {}).get("result") or {}
print("run_id", payload["stage_run_id"])
print("result_keys", sorted(result.keys()))
for key in [
    "completion_state",
    "completion_gate_ok",
    "status",
    "failed_reasons",
    "output_dir",
    "semantic_gate",
    "quality_findings",
    "completion_judge",
]:
    if key in result:
        print(f"\n== {key}")
        value = result[key]
        if isinstance(value, (dict, list)):
            print(json.dumps(value, ensure_ascii=False, indent=2)[:4000])
        else:
            print(value)

print("\nresult_preview")
print(json.dumps(result, ensure_ascii=False, indent=2)[:8000])
