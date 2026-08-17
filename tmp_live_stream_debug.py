import json
import requests

BASE = "http://127.0.0.1:8000"
login = requests.post(f"{BASE}/api/auth/login", data={"username":"ui.admin.round@devanalysis.local","password":"RoundUi!20260426"}, timeout=30)
login.raise_for_status()
headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

payload = {
  "task": "[고객 주문 생성 요청]\n- 상품 ID: stock-ai-autotrader\n- 카테고리: ai엔진군 주식매매프로그램\nsource_path: /app\n",
  "mode": "full",
  "project_name": "ai-engine-stock-trading-stream-debug"
}
r = requests.post(f"{BASE}/api/marketplace/customer-orchestrate/stage-runs", json=payload, headers=headers, timeout=30)
r.raise_for_status()
stage = r.json()
payload["stage_run_id"] = stage.get("run_id")
payload["stage_id"] = stage.get("current_stage_id") or "ARCH-001"

requests.post(f"{BASE}/api/marketplace/customer-orchestrate/accepted", json=payload, headers=headers, timeout=30).raise_for_status()

with requests.post(f"{BASE}/api/marketplace/customer-orchestrate/stream", json=payload, headers=headers, stream=True, timeout=600) as resp:
    print("STATUS", resp.status_code)
    count = 0
    for raw in resp.iter_lines(decode_unicode=True):
        if raw is None:
            continue
        print(raw)
        count += 1
        if count > 200:
            break
