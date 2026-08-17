import json
import os
from datetime import datetime
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
LOGIN_USER = "ui.admin.round@devanalysis.local"
LOGIN_PASS = "RoundUi!20260426"

session = requests.Session()
login = session.post(f"{BASE}/api/auth/login", data={"username": LOGIN_USER, "password": LOGIN_PASS}, timeout=30)
login.raise_for_status()
token = login.json().get("access_token")
if not token:
    raise RuntimeError("login token missing")
headers = {"Authorization": f"Bearer {token}"}

def count_code_lines(root: Path):
    exts = {".py", ".ts", ".tsx", ".js", ".jsx"}
    total = 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            try:
                with p.open("r", encoding="utf-8", errors="ignore") as fh:
                    total += sum(1 for _ in fh)
            except Exception:
                pass
    return total

def run_one(index: int):
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    project_name = f"ai-engine-stock-trading-program-rerun{index}-{now}"
    task = """[고객 주문 생성 요청]
- 상품 ID: stock-ai-autotrader
- 카테고리: ai엔진군 주식매매프로그램
- 도메인: finance
- 유형: custom-order
- 실행명: {project_name}
- 요구 기능: 시그널, 리스크가드, 주문실행, 포트폴리오 API, 테스트, ZIP

[추가 조건]
source_path: /app
Python FastAPI 기반 실프로젝트 구조로 생성하고 AI 엔진 기본 탑재, 실검증/출고 문서 포함.
""".format(project_name=project_name)

    create_payload = {"task": task, "mode": "full", "project_name": project_name}
    r_create = session.post(f"{BASE}/api/marketplace/customer-orchestrate/stage-runs", json=create_payload, headers=headers, timeout=30)
    r_create.raise_for_status()
    stage_run = r_create.json()
    run_id = stage_run.get("run_id")
    stage_id = stage_run.get("current_stage_id") or "ARCH-001"
    if not run_id:
        raise RuntimeError("run_id missing")

    accept_payload = dict(create_payload)
    accept_payload.update({"stage_run_id": run_id, "stage_id": stage_id})
    r_accept = session.post(f"{BASE}/api/marketplace/customer-orchestrate/accepted", json=accept_payload, headers=headers, timeout=30)
    r_accept.raise_for_status()

    result_payload = None
    error_payload = None
    with session.post(f"{BASE}/api/marketplace/customer-orchestrate/stream", json=accept_payload, headers=headers, stream=True, timeout=7200) as resp:
        resp.raise_for_status()
        current_event = None
        for raw in resp.iter_lines(decode_unicode=True):
            if raw is None:
                continue
            line = raw.strip()
            if not line:
                continue
            if line.startswith("event:"):
                current_event = line.split(":", 1)[1].strip()
                continue
            if line.startswith("data:"):
                payload_text = line.split(":", 1)[1].strip()
                payload = {}
                if payload_text:
                    try:
                        payload = json.loads(payload_text)
                    except Exception:
                        payload = {"raw": payload_text}
                if current_event == "result":
                    result_payload = payload
                    break
                if current_event == "error":
                    error_payload = payload
                    break

    if error_payload:
        raise RuntimeError(f"stream error: {error_payload}")
    if not result_payload:
        raise RuntimeError("stream ended without result payload")

    result = result_payload.get("result") or {}
    output_dir = result.get("output_dir")
    if not output_dir:
        raise RuntimeError(f"output_dir missing in result: {result}")

    output_path = Path(output_dir)
    validation_json_path = output_path / "docs" / "automatic_validation_result.json"
    validation = {}
    if validation_json_path.exists():
        validation = json.loads(validation_json_path.read_text(encoding="utf-8", errors="ignore"))

    check_sh_path = output_path / "scripts" / "check.sh"
    check_sh = check_sh_path.read_text(encoding="utf-8", errors="ignore") if check_sh_path.exists() else ""

    files = 0
    dirs = 0
    for _, dnames, fnames in os.walk(output_path):
        dirs += len(dnames)
        files += len(fnames)

    return {
        "index": index,
        "project_name": project_name,
        "run_id": run_id,
        "stage_id": stage_id,
        "output_dir": str(output_path),
        "output_archive_path": validation.get("output_archive_path"),
        "status": validation.get("status"),
        "failed_reasons": validation.get("failed_reasons") or [],
        "file_count": files,
        "dir_count": dirs,
        "code_lines": count_code_lines(output_path),
        "profile_id": (validation.get("order_profile") or {}).get("profile_id"),
        "validation_profile": validation.get("validation_profile"),
        "check_sh_has_compileall": "python -m compileall" in check_sh,
        "check_sh_has_pytest_q_s": "pytest -q -s" in check_sh,
        "check_sh_has_lock_marker": "requirements.delivery.lock.txt" in check_sh,
        "check_sh_preview": check_sh[:500],
    }

results = []
for i in (1, 2):
    print(f"[RUN {i}] starting")
    data = run_one(i)
    results.append(data)
    print(f"[RUN {i}] done run_id={data['run_id']} status={data['status']} profile={data['profile_id']}")

report = {"generated_at": datetime.utcnow().isoformat() + "Z", "results": results}
report_path = Path("docs/checklists") / f"marketplace-live-order-ai-stock-trading-rerun-report-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("REPORT_PATH", report_path)
print(json.dumps(report, ensure_ascii=False, indent=2))
