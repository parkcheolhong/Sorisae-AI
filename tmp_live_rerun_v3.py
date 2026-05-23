import json
import os
from datetime import datetime
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
LOGIN_USER = "ui.admin.round@devanalysis.local"
LOGIN_PASS = "RoundUi!20260426"
WORKSPACE_ROOT = Path.cwd()

session = requests.Session()
login = session.post(f"{BASE}/api/auth/login", data={"username": LOGIN_USER, "password": LOGIN_PASS}, timeout=30)
login.raise_for_status()
headers = {"Authorization": f"Bearer {login.json()['access_token']}"}


def parse_sse_text(text: str):
    events = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line.startswith("data:"):
            continue
        payload_text = line.split(":", 1)[1].strip()
        if not payload_text:
            continue
        try:
            payload = json.loads(payload_text)
        except Exception:
            continue
        events.append(payload)
    return events


def map_output_path(raw_output_dir: str) -> Path:
    normalized = str(raw_output_dir or "").replace("\\", "/")
    marker = "/app/uploads/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        return WORKSPACE_ROOT / "uploads" / Path(suffix)
    if normalized.startswith("/app/uploads"):
        suffix = normalized[len("/app/uploads"):].lstrip("/")
        return WORKSPACE_ROOT / "uploads" / Path(suffix)
    return Path(raw_output_dir)


def count_code_lines(root: Path):
    exts = {".py", ".ts", ".tsx", ".js", ".jsx"}
    total = 0
    for p in root.rglob("*"):
        try:
            is_file = p.is_file()
        except Exception:
            continue
        if is_file and p.suffix.lower() in exts:
            try:
                with p.open("r", encoding="utf-8", errors="ignore") as fh:
                    total += sum(1 for _ in fh)
            except Exception:
                pass
    return total


def run_one(index: int):
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    project_name = f"ai-engine-stock-trading-program-rerun{index}-{now}"
    task = f"""[고객 주문 생성 요청]\n- 상품 ID: stock-ai-autotrader\n- 카테고리: ai엔진군 주식매매프로그램\n- 도메인: finance\n- 유형: custom-order\n- 실행명: {project_name}\n- 요구 기능: 시그널, 리스크가드, 주문실행, 포트폴리오 API, 테스트, ZIP\n\n[추가 조건]\nsource_path: /app\nPython FastAPI 기반 실프로젝트 구조로 생성하고 AI 엔진 기본 탑재, 실검증/출고 문서 포함.\n"""

    payload = {"task": task, "mode": "full", "project_name": project_name}
    create = session.post(f"{BASE}/api/marketplace/customer-orchestrate/stage-runs", json=payload, headers=headers, timeout=30)
    create.raise_for_status()
    stage = create.json()
    payload["stage_run_id"] = stage.get("run_id")
    payload["stage_id"] = stage.get("current_stage_id") or "ARCH-001"

    accepted = session.post(f"{BASE}/api/marketplace/customer-orchestrate/accepted", json=payload, headers=headers, timeout=30)
    accepted.raise_for_status()

    stream = session.post(f"{BASE}/api/marketplace/customer-orchestrate/stream", json=payload, headers=headers, timeout=7200)
    stream.raise_for_status()
    events = parse_sse_text(stream.text)

    result_event = next((e for e in reversed(events) if e.get("event") == "result"), None)
    error_event = next((e for e in reversed(events) if e.get("event") == "error"), None)
    if error_event is not None:
        raise RuntimeError(f"stream error event: {error_event}")
    if result_event is None:
        raise RuntimeError("result event missing")

    result_payload = result_event.get("payload") or {}
    result = result_payload.get("result") or {}
    raw_output_dir = result.get("output_dir")
    if not raw_output_dir:
        raise RuntimeError("output_dir missing in result payload")

    output_path = map_output_path(raw_output_dir)
    validation_path = output_path / "docs" / "automatic_validation_result.json"
    validation = json.loads(validation_path.read_text(encoding="utf-8", errors="ignore")) if validation_path.exists() else {}
    check_path = output_path / "scripts" / "check.sh"
    check_text = check_path.read_text(encoding="utf-8", errors="ignore") if check_path.exists() else ""

    files = 0
    dirs = 0
    if output_path.exists():
        for _, dnames, fnames in os.walk(output_path):
            dirs += len(dnames)
            files += len(fnames)

    return {
        "index": index,
        "project_name": project_name,
        "run_id": payload.get("stage_run_id"),
        "stage_id": payload.get("stage_id"),
        "raw_output_dir": raw_output_dir,
        "output_dir": str(output_path),
        "output_archive_path": validation.get("output_archive_path"),
        "status": validation.get("status"),
        "failed_reasons": validation.get("failed_reasons") or [],
        "validation_profile": validation.get("validation_profile"),
        "profile_id": (validation.get("order_profile") or {}).get("profile_id"),
        "file_count": files,
        "dir_count": dirs,
        "code_lines": count_code_lines(output_path) if output_path.exists() else 0,
        "check_sh_has_compileall": "python -m compileall" in check_text,
        "check_sh_has_pytest_q_s": "pytest -q -s" in check_text,
        "check_sh_has_lock_marker": "requirements.delivery.lock.txt" in check_text,
    }


results = []
for idx in (1, 2):
    print(f"[RUN {idx}] starting")
    data = run_one(idx)
    results.append(data)
    print(f"[RUN {idx}] done run_id={data['run_id']} status={data['status']} profile={data['profile_id']}")

report = {"generated_at": datetime.utcnow().isoformat() + "Z", "results": results}
report_path = Path("docs/checklists") / f"marketplace-live-order-ai-stock-trading-rerun-report-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("REPORT_PATH", report_path)
print(json.dumps(report, ensure_ascii=False, indent=2))
