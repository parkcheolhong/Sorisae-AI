import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

BASE_URL_DEFAULT = "http://127.0.0.1:8000"
LOGIN_PATH = "/api/auth/login"
DISPATCH_PATH = "/api/marketplace/sorisae/dispatch"
REGISTER_PATH = "/api/marketplace/sorisae/register"

USERNAME_DEFAULT = "119cash@naver.com"
PASSWORD_DEFAULT = "space0215@"


def _append_result(results: List[Dict[str, Any]], name: str, passed: bool, detail: str, status_code: int) -> None:
    results.append(
        {
            "name": name,
            "passed": passed,
            "detail": detail,
            "status_code": status_code,
        }
    )


def _contains_internal_leak(text: str) -> bool:
    lowered = text.lower()
    leak_keywords = [
        "traceback",
        "file \"",
        "line ",
        "module ",
        "sqlalchemy",
        "uvicorn",
        "fastapi",
    ]
    return any(keyword in lowered for keyword in leak_keywords)


def run_validation(base_url: str, username: str, password: str) -> Dict[str, Any]:
    session = requests.Session()
    results: List[Dict[str, Any]] = []

    # 1) Unauthenticated request must be blocked.
    no_auth = session.post(
        f"{base_url}{DISPATCH_PATH}",
        json={"engine_type": "master"},
        timeout=10,
    )
    no_auth_text = no_auth.text
    no_auth_ok = no_auth.status_code == 401 and "not authenticated" in no_auth_text.lower()
    _append_result(
        results,
        "unauthenticated_dispatch_blocked",
        no_auth_ok,
        no_auth_text[:300],
        no_auth.status_code,
    )

    # 2) Invalid bearer token must be blocked.
    bad_token = session.post(
        f"{base_url}{DISPATCH_PATH}",
        headers={"Authorization": "Bearer invalid.token.value"},
        json={"engine_type": "master"},
        timeout=10,
    )
    bad_token_text = bad_token.text
    bad_token_ok = bad_token.status_code == 401
    _append_result(
        results,
        "invalid_token_blocked",
        bad_token_ok,
        bad_token_text[:300],
        bad_token.status_code,
    )

    # Authenticate for subsequent checks.
    login = session.post(
        f"{base_url}{LOGIN_PATH}",
        data={"username": username, "password": password},
        timeout=10,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 3) Input validation: missing required field must return 422 and no internal leak.
    missing_engine = session.post(
        f"{base_url}{DISPATCH_PATH}",
        headers=auth_headers,
        json={"context": {}},
        timeout=10,
    )
    missing_engine_text = missing_engine.text
    missing_engine_ok = (
        missing_engine.status_code == 422
        and "engine_type" in missing_engine_text
        and not _contains_internal_leak(missing_engine_text)
    )
    _append_result(
        results,
        "missing_engine_type_validated",
        missing_engine_ok,
        missing_engine_text[:300],
        missing_engine.status_code,
    )

    # 4) Input validation: unknown engine should return standardized failure payload.
    unknown_engine = session.post(
        f"{base_url}{DISPATCH_PATH}",
        headers=auth_headers,
        json={"engine_type": "unknown_security_probe"},
        timeout=10,
    )
    unknown_text = unknown_engine.text
    unknown_body: Dict[str, Any] = {}
    try:
        unknown_body = unknown_engine.json()
    except Exception:
        unknown_body = {}

    unknown_detail = unknown_body.get("detail", {}) if isinstance(unknown_body, dict) else {}
    unknown_ok = (
        unknown_engine.status_code == 400
        and isinstance(unknown_detail, dict)
        and unknown_detail.get("error_code") == "INPUT_ENGINE_TYPE_NOT_REGISTERED"
        and unknown_detail.get("source") == "router_validation"
        and not _contains_internal_leak(unknown_text)
    )
    _append_result(
        results,
        "unknown_engine_standardized_error",
        unknown_ok,
        unknown_text[:300],
        unknown_engine.status_code,
    )

    # 5) Runtime exception should not expose traceback details.
    session.post(
        f"{base_url}{REGISTER_PATH}",
        headers=auth_headers,
        json={"engine_type": "runtime_probe", "slot_file": "slot999_failure_probe.py"},
        timeout=10,
    )
    runtime_probe = session.post(
        f"{base_url}{DISPATCH_PATH}",
        headers=auth_headers,
        json={
            "engine_type": "runtime_probe",
            "context": {"probe": "security_gate4"},
            "entry_fn": "main",
            "use_module_adapter": True,
            "adapter_entry_candidates": ["run", "execute", "start"],
        },
        timeout=20,
    )
    runtime_text = runtime_probe.text
    runtime_body: Dict[str, Any] = {}
    try:
        runtime_body = runtime_probe.json()
    except Exception:
        runtime_body = {}

    runtime_ok = (
        runtime_probe.status_code == 200
        and runtime_body.get("error_code") == "ENGINE_RUNTIME_ERROR"
        and runtime_body.get("source") == "engine_runtime"
        and runtime_body.get("retryable") is False
        and not _contains_internal_leak(runtime_text)
    )
    _append_result(
        results,
        "runtime_error_no_internal_traceback_leak",
        runtime_ok,
        runtime_text[:300],
        runtime_probe.status_code,
    )

    # 6) CORS allowed origin should receive ACAO header.
    cors_allowed = session.options(
        f"{base_url}{DISPATCH_PATH}",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
        timeout=10,
    )
    allowed_origin = cors_allowed.headers.get("access-control-allow-origin")
    cors_allowed_ok = cors_allowed.status_code == 200 and allowed_origin == "http://localhost:3000"
    _append_result(
        results,
        "cors_allowed_origin_present",
        cors_allowed_ok,
        f"acao={allowed_origin}",
        cors_allowed.status_code,
    )

    # 7) CORS disallowed origin should not receive ACAO header.
    cors_disallowed = session.options(
        f"{base_url}{DISPATCH_PATH}",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
        },
        timeout=10,
    )
    denied_origin = cors_disallowed.headers.get("access-control-allow-origin")
    cors_disallowed_ok = denied_origin is None
    _append_result(
        results,
        "cors_disallowed_origin_blocked",
        cors_disallowed_ok,
        f"acao={denied_origin}",
        cors_disallowed.status_code,
    )

    passed_count = sum(1 for item in results if item["passed"])
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "base_url": base_url,
        "total_checks": len(results),
        "passed_checks": passed_count,
        "failed_checks": len(results) - passed_count,
        "pass_rate": round((passed_count / len(results)) * 100.0, 2),
        "checks": results,
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Gate #4 security validation for sorisae dispatch")
    parser.add_argument("--base-url", default=BASE_URL_DEFAULT)
    parser.add_argument("--username", default=USERNAME_DEFAULT)
    parser.add_argument("--password", default=PASSWORD_DEFAULT)
    parser.add_argument("--output", required=True, help="Path to output JSON report")
    args = parser.parse_args()

    report = run_validation(args.base_url, args.username, args.password)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(
        f"SECURITY_GATE4|passed={report['passed_checks']}/{report['total_checks']}|"
        f"pass_rate={report['pass_rate']}|output={output_path.as_posix()}"
    )
    for check in report["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        print(
            f"{status}|{check['name']}|http={check['status_code']}|detail={check['detail']}"
        )

    if report["failed_checks"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
