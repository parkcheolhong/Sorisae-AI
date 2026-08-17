from __future__ import annotations

import argparse
import json
import random
import subprocess
import string
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional, Tuple


DEFAULT_BASE_URL = "http://127.0.0.1:8000"
DUPLICATE_LOGIN_MESSAGE = (
    "이미 다른 기기 또는 세션에서 로그인 상태가 남아 있습니다. "
    "현재 사용 중인 기기가 없다면 계정 복구(본인확인) 후 세션 해제 뒤 다시 시도해 주세요."
)


def _request_json(
    *,
    method: str,
    url: str,
    token: Optional[str] = None,
    form: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 20.0,
) -> Tuple[int, Any]:
    headers: Dict[str, str] = {"Accept": "application/json"}
    data: Optional[bytes] = None

    if form is not None:
        data = urllib.parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        method=method,
        data=data,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {"detail": raw}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def _make_user_credentials() -> Dict[str, str]:
    random_suffix = "".join(
        random.choices(string.ascii_lowercase + string.digits, k=6)
    )
    suffix = f"{int(time.time() * 1000):x}{random_suffix}"
    return {
        "username": f"dup_login_{suffix}",
        "email": f"dup-login-{suffix}@worldlinco.dev",
        "password": f"WorldLinco!{suffix}A1",
    }


def _signup(base_url: str, credentials: Dict[str, str]) -> None:
    status, payload = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/signup",
        body={
            "username": credentials["username"],
            "email": credentials["email"],
            "password": credentials["password"],
            "preferred_language": "ko",
            "country_code": "KR",
            "full_name": "Duplicate Login E2E",
            "member_type": "individual",
        },
    )
    if status >= 400:
        raise RuntimeError(f"signup failed ({status}): {payload}")


def _login(base_url: str, email: str, password: str) -> Tuple[int, Any]:
    return _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/login",
        form={"username": email, "password": password},
    )


def _logout(base_url: str, token: str) -> Tuple[int, Any]:
    return _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/logout",
        token=token,
    )


def _clear_active_sessions_for_email_local(email: str) -> int:
    command = [
        "docker",
        "exec",
        "-e",
        f"AUTH_E2E_EMAIL={email}",
        "devanalysis114-backend",
        "python",
        "-c",
        (
            "import os; "
            "import backend.marketplace.database as d; "
            "d._get_or_create_engine(); "
            "from backend.models import User; "
            "from backend.marketplace.models import UserActiveSession; "
            "s=d.SessionLocal(); "
            "email=os.getenv('AUTH_E2E_EMAIL','').strip().lower(); "
            "u=s.query(User).filter(User.email==email).first() if email else None; "
            "rows=s.query(UserActiveSession).filter(UserActiveSession.user_id==int(u.id)).all() if u else []; "
            "[s.delete(r) for r in rows]; s.commit(); print(len(rows)); s.close()"
        ),
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "auto clear active sessions failed: "
            f"exit={completed.returncode} stderr={completed.stderr.strip()}"
        )
    raw = (completed.stdout or "").strip().splitlines()
    if not raw:
        return 0
    try:
        return int(raw[-1].strip())
    except ValueError:
        return 0


def run_scenario(
    base_url: str,
    email: Optional[str] = None,
    password: Optional[str] = None,
    auto_clear_active_session: bool = False,
) -> Dict[str, Any]:
    if email and password:
        credentials = {
            "username": email.split("@")[0],
            "email": email,
            "password": password,
        }
        if auto_clear_active_session:
            cleared_count = _clear_active_sessions_for_email_local(
                credentials["email"]
            )
        else:
            cleared_count = 0
    else:
        credentials = _make_user_credentials()
        cleared_count = 0
        try:
            _signup(base_url, credentials)
        except RuntimeError as exc:
            message = str(exc)
            if "signup failed (428)" in message:
                raise RuntimeError(
                    "signup requires OTP in this environment. "
                    "Re-run with --email and --password "
                    "for an existing account."
                ) from exc
            raise

    first_status, first_payload = _login(
        base_url,
        credentials["email"],
        credentials["password"],
    )
    first_token = str((first_payload or {}).get("access_token") or "").strip()
    if first_status != 200 or not first_token:
        raise RuntimeError(
            f"first login failed ({first_status}): {first_payload}"
        )

    second_status, second_payload = _login(
        base_url,
        credentials["email"],
        credentials["password"],
    )
    if second_status != 409:
        raise RuntimeError(
            "duplicate login should be blocked with 409, "
            f"got ({second_status}): {second_payload}"
        )

    second_detail = str((second_payload or {}).get("detail") or "").strip()

    logout_status, logout_payload = _logout(base_url, first_token)
    if logout_status not in (200, 204):
        raise RuntimeError(
            f"logout failed ({logout_status}): {logout_payload}"
        )

    third_status, third_payload = _login(
        base_url,
        credentials["email"],
        credentials["password"],
    )
    third_token = str((third_payload or {}).get("access_token") or "").strip()
    if third_status != 200 or not third_token:
        raise RuntimeError(
            f"re-login failed ({third_status}): {third_payload}"
        )

    return {
        "base_url": base_url,
        "email": credentials["email"],
        "precheck": {
            "auto_clear_active_session": auto_clear_active_session,
            "cleared_active_sessions": cleared_count,
        },
        "login_1": {"status": first_status, "token_issued": bool(first_token)},
        "login_2_duplicate_blocked": {
            "status": second_status,
            "detail": second_detail,
            "matches_mobile_ux": second_detail == DUPLICATE_LOGIN_MESSAGE,
        },
        "logout": {"status": logout_status},
        "login_3_after_logout": {
            "status": third_status,
            "token_issued": bool(third_token),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "E2E for login -> duplicate login blocked -> logout -> re-login"
        )
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Backend base URL (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--email",
        default="",
        help="Existing account email (optional)",
    )
    parser.add_argument(
        "--password",
        default="",
        help="Existing account password (optional)",
    )
    parser.add_argument(
        "--auto-clear-active-session",
        action="store_true",
        help=(
            "Before scenario, clear user_active_sessions for the given --email "
            "via local backend container (devanalysis114-backend)."
        ),
    )
    args = parser.parse_args()

    if bool(args.email.strip()) ^ bool(args.password.strip()):
        raise SystemExit("Both --email and --password are required together.")

    result = run_scenario(
        args.base_url,
        email=args.email.strip() or None,
        password=args.password.strip() or None,
        auto_clear_active_session=args.auto_clear_active_session,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["login_2_duplicate_blocked"]["matches_mobile_ux"]:
        print(
            "[warn] duplicate-login detail does not exactly "
            "match mobile UX message"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
