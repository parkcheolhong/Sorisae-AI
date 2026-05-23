import json
import time
from datetime import datetime
from pathlib import Path

import requests

BASE = "http://127.0.0.1:8000"
LOGIN_USER = "ui.admin.round@devanalysis.local"
LOGIN_PASS = "RoundUi!20260426"
RUN_TIMEOUT_SEC = 1800
POLL_INTERVAL_SEC = 5


def login_session() -> tuple[requests.Session, dict]:
    session = requests.Session()
    resp = session.post(
        f"{BASE}/api/auth/login",
        data={"username": LOGIN_USER, "password": LOGIN_PASS},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    return session, {"Authorization": f"Bearer {token}"}


def get_stage_run(session: requests.Session, headers: dict, run_id: str) -> dict:
    resp = session.get(
        f"{BASE}/api/marketplace/customer-orchestrate/stage-runs/{run_id}",
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def run_one(index: int) -> dict:
    session, headers = login_session()
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
    create = session.post(
        f"{BASE}/api/marketplace/customer-orchestrate/stage-runs",
        json=payload,
        headers=headers,
        timeout=30,
    )
    create.raise_for_status()
    stage = create.json()

    payload["stage_run_id"] = stage.get("run_id")
    payload["stage_id"] = stage.get("current_stage_id") or "ARCH-001"

    accepted = session.post(
        f"{BASE}/api/marketplace/customer-orchestrate/accepted",
        json=payload,
        headers=headers,
        timeout=30,
    )
    accepted.raise_for_status()

    print(f"[RUN {index}] stage_run_id={payload['stage_run_id']} stream start", flush=True)
    stream_resp = session.post(
        f"{BASE}/api/marketplace/customer-orchestrate/stream",
        json=payload,
        headers=headers,
        timeout=RUN_TIMEOUT_SEC,
    )
    print(f"[RUN {index}] stream status_code={stream_resp.status_code}", flush=True)

    started = time.time()
    last = {}
    while time.time() - started < RUN_TIMEOUT_SEC:
        last = get_stage_run(session, headers, payload["stage_run_id"])
        execution = ((last.get("metadata") or {}).get("orchestration_execution") or {})
        status = str(execution.get("status") or "")
        if status in {"completed", "failed"}:
            break
        time.sleep(POLL_INTERVAL_SEC)

    execution = ((last.get("metadata") or {}).get("orchestration_execution") or {})
    output_dir = execution.get("output_dir")
    result = {
        "index": index,
        "project_name": project_name,
        "run_id": payload.get("stage_run_id"),
        "execution_status": execution.get("status"),
        "output_dir": output_dir,
    }

    if output_dir:
        local_output = Path(str(output_dir).replace("/app/uploads/", "uploads/").replace("/", "\\"))
        avr = local_output / "docs" / "automatic_validation_result.json"
        opa = local_output / "docs" / "output_audit.json"
        profile = local_output / "docs" / "order_profile.md"
        if avr.exists():
            d = json.loads(avr.read_text(encoding="utf-8", errors="ignore"))
            sg = d.get("semantic_gate") or {}
            result["semantic_gate_ok"] = sg.get("ok")
            result["semantic_gate_score"] = sg.get("score")
            result["semantic_gate_checklist"] = sg.get("checklist")
            result["semantic_audit_ok"] = d.get("semantic_audit_ok")
            result["semantic_audit_score"] = d.get("semantic_audit_score")
            result["failed_reasons"] = d.get("failed_reasons")
        if opa.exists():
            d = json.loads(opa.read_text(encoding="utf-8", errors="ignore"))
            result["output_audit_semantic_ok"] = d.get("semantic_audit_ok")
            result["output_audit_semantic_score"] = d.get("semantic_audit_score")
        if profile.exists():
            text = profile.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                if line.strip().startswith("- profile_id:"):
                    result["profile_id"] = line.split(":", 1)[1].strip()
                    break

    print(json.dumps(result, ensure_ascii=False), flush=True)
    return result


def main() -> None:
    results = []
    for idx in (1, 2):
        print(f"[RUN {idx}] starting", flush=True)
        results.append(run_one(idx))
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "results": results,
    }
    out = Path("docs/checklists") / f"marketplace-live-order-sync-rerun-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print("REPORT_PATH", str(out), flush=True)
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
