import json
import threading
import time
from datetime import datetime
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
LOGIN_USER = "ui.admin.round@devanalysis.local"
LOGIN_PASS = "RoundUi!20260426"
WORKSPACE_ROOT = Path.cwd()
POLL_INTERVAL_SEC = 5
RUN_TIMEOUT_SEC = 1800
HTTP_RETRY = 8

session = requests.Session()
login = session.post(
    f"{BASE}/api/auth/login",
    data={"username": LOGIN_USER, "password": LOGIN_PASS},
    timeout=30,
)
login.raise_for_status()
headers = {"Authorization": f"Bearer {login.json()['access_token']}"}


def map_app_path(raw_path: str | None) -> Path | None:
    if not raw_path:
        return None
    normalized = str(raw_path).replace("\\", "/")
    marker = "/app/uploads/"
    if marker in normalized:
        suffix = normalized.split(marker, 1)[1]
        return WORKSPACE_ROOT / "uploads" / Path(suffix)
    if normalized.startswith("/app/uploads"):
        suffix = normalized[len("/app/uploads") :].lstrip("/")
        return WORKSPACE_ROOT / "uploads" / Path(suffix)
    return Path(raw_path)


def trigger_stream_background(payload: dict) -> None:
    def _run() -> None:
        try:
            session.post(
                f"{BASE}/api/marketplace/customer-orchestrate/stream",
                json=payload,
                headers=headers,
                timeout=RUN_TIMEOUT_SEC,
            )
        except Exception:
            pass

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()


def request_with_retry(method: str, url: str, **kwargs) -> requests.Response:
    last_error: Exception | None = None
    for attempt in range(1, HTTP_RETRY + 1):
        try:
            resp = session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except Exception as exc:
            last_error = exc
            if attempt >= HTTP_RETRY:
                raise
            time.sleep(min(2 * attempt, 10))
    if last_error is not None:
        raise last_error
    raise RuntimeError("request failed without explicit exception")


def get_stage_run(run_id: str) -> dict:
    resp = request_with_retry(
        "GET",
        f"{BASE}/api/marketplace/customer-orchestrate/stage-runs/{run_id}",
        headers=headers,
        timeout=30,
    )
    return resp.json()


def run_one(index: int) -> dict:
    now = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    project_name = f"ai-engine-stock-trading-program-rerun{index}-{now}"
    task = (
        "[고객 주문 생성 요청]\n"
        "- 상품 ID: stock-ai-autotrader\n"
        "- 카테고리: ai엔진군 주식매매프로그램\n"
        "- 도메인: finance\n"
        "- 유형: custom-order\n"
        f"- 실행명: {project_name}\n"
        "- 요구 기능: 시그널, 리스크가드, 주문실행, 포트폴리오 API, 테스트, ZIP\n\n"
        "[추가 조건]\n"
        "source_path: /app\n"
        "Python FastAPI 기반 실프로젝트 구조로 생성하고 AI 엔진 기본 탑재, 실검증/출고 문서 포함.\n"
    )

    payload = {"task": task, "mode": "full", "project_name": project_name}
    create = request_with_retry(
        "POST",
        f"{BASE}/api/marketplace/customer-orchestrate/stage-runs",
        json=payload,
        headers=headers,
        timeout=30,
    )
    stage = create.json()
    payload["stage_run_id"] = stage.get("run_id")
    payload["stage_id"] = stage.get("current_stage_id") or "ARCH-001"

    request_with_retry(
        "POST",
        f"{BASE}/api/marketplace/customer-orchestrate/accepted",
        json=payload,
        headers=headers,
        timeout=30,
    )

    trigger_stream_background(payload)

    started = time.time()
    last_snapshot: dict = {}
    while time.time() - started < RUN_TIMEOUT_SEC:
        snapshot = get_stage_run(payload["stage_run_id"])
        last_snapshot = snapshot
        meta = snapshot.get("metadata") or {}
        execution = meta.get("orchestration_execution") or {}
        status = str(execution.get("status") or "")
        if status in {"completed", "failed"}:
            break
        time.sleep(POLL_INTERVAL_SEC)

    meta = last_snapshot.get("metadata") or {}
    execution = meta.get("orchestration_execution") or {}
    output_dir_raw = execution.get("output_dir")
    output_dir = map_app_path(output_dir_raw)

    validation = {}
    check_text = ""
    zip_exists = False
    validation_path = None
    zip_path = None

    if output_dir is not None:
        validation_path = output_dir / "docs" / "automatic_validation_result.json"
        if validation_path.exists():
            validation = json.loads(validation_path.read_text(encoding="utf-8", errors="ignore"))
        check_path = output_dir / "scripts" / "check.sh"
        if check_path.exists():
            check_text = check_path.read_text(encoding="utf-8", errors="ignore")
        archive_raw = validation.get("output_archive_path")
        zip_path = map_app_path(archive_raw) if archive_raw else None
        zip_exists = bool(zip_path and zip_path.exists())

    return {
        "index": index,
        "project_name": project_name,
        "run_id": payload.get("stage_run_id"),
        "stage_status": last_snapshot.get("status"),
        "execution_status": execution.get("status"),
        "raw_output_dir": output_dir_raw,
        "output_dir": str(output_dir) if output_dir else None,
        "validation_json_exists": bool(validation_path and validation_path.exists()),
        "automatic_validation_result_path": str(validation_path) if validation_path else None,
        "status": validation.get("status"),
        "failed_reasons": validation.get("failed_reasons") or [],
        "validation_profile": validation.get("validation_profile"),
        "output_archive_path": validation.get("output_archive_path"),
        "shipment_zip_local_path": str(zip_path) if zip_path else None,
        "shipment_zip_exists": zip_exists,
        "check_sh_has_compileall": "python -m compileall" in check_text,
        "check_sh_has_pytest_q_s": "pytest -q -s" in check_text,
        "check_sh_has_lock_marker": "requirements.delivery.lock.txt" in check_text,
    }


results = []
for idx in (1, 2):
    print(f"[RUN {idx}] starting", flush=True)
    data = run_one(idx)
    results.append(data)
    print(
        f"[RUN {idx}] done run_id={data['run_id']} status={data['status']} validation_json={data['validation_json_exists']} zip={data['shipment_zip_exists']}",
        flush=True,
    )

report = {"generated_at": datetime.utcnow().isoformat() + "Z", "results": results}
report_path = Path("docs/checklists") / (
    f"marketplace-live-order-ai-stock-trading-rerun-report-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
)
report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print("REPORT_PATH", report_path, flush=True)
print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
