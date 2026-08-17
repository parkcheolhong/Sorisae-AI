from __future__ import annotations

import argparse
import json
import imaplib
import email
from email.message import Message
import os
import random
import re
import string
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DEFAULT_BASE_URL = "https://metanova1004.com"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _request_json(
    *,
    method: str,
    url: str,
    token: Optional[str] = None,
    form: Optional[Dict[str, str]] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 30.0,
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

    request = urllib.request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, (json.loads(raw) if raw.strip() else {})
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw) if raw.strip() else {"detail": raw}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def _gen_signup_identity() -> Dict[str, str]:
    suffix = f"{int(time.time() * 1000):x}{''.join(random.choices(string.ascii_lowercase + string.digits, k=5))}"
    return {
        "email": f"feature-e2e-{suffix}@worldlinco.dev",
        "username": f"feature_e2e_{suffix}",
        "password": f"WorldLinco!{suffix}A1",
    }


def _extract_otp_code(text: str) -> str:
    match = re.search(r"(?<!\d)(\d{6})(?!\d)", str(text or ""))
    return match.group(1) if match else ""


def _decode_email_body(message_obj: Message) -> str:
    if message_obj.is_multipart():
        parts: list[str] = []
        for part in message_obj.walk():
            content_type = str(part.get_content_type() or "")
            if content_type != "text/plain":
                continue
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or "utf-8"
            if not isinstance(payload, (bytes, bytearray)):
                continue
            try:
                parts.append(payload.decode(charset, errors="replace"))
            except Exception:
                parts.append(payload.decode("utf-8", errors="replace"))
        return "\n".join(parts)

    payload = message_obj.get_payload(decode=True)
    charset = message_obj.get_content_charset() or "utf-8"
    if not isinstance(payload, (bytes, bytearray)):
        raw = message_obj.get_payload()  # type: ignore[assignment]
        return str(raw or "")
    try:
        return payload.decode(charset, errors="replace")
    except Exception:
        return payload.decode("utf-8", errors="replace")


def _fetch_otp_from_imap(
    *,
    host: str,
    username: str,
    password: str,
    mailbox: str,
    from_filter: str,
    subject_filter: str,
    timeout_seconds: int,
    poll_interval_seconds: float,
) -> str:
    deadline = time.monotonic() + max(1, int(timeout_seconds))
    from_filter = str(from_filter or "").strip()
    subject_filter = str(subject_filter or "").strip()
    search_terms = ['ALL']
    if from_filter:
        search_terms += ['FROM', f'"{from_filter}"']
    if subject_filter:
        search_terms += ['SUBJECT', f'"{subject_filter}"']

    while time.monotonic() < deadline:
        try:
            with imaplib.IMAP4_SSL(host) as imap:
                imap.login(username, password)
                imap.select(mailbox)
                status, data = imap.search(None, *search_terms)
                if status != "OK":
                    time.sleep(poll_interval_seconds)
                    continue

                message_ids = (data[0] or b"").split()
                for message_id in reversed(message_ids[-15:]):
                    fetch_status, fetched = imap.fetch(
                        message_id.decode("ascii", errors="ignore"),
                        "(RFC822)",
                    )
                    if fetch_status != "OK" or not fetched:
                        continue
                    chunk = fetched[0] if fetched else None
                    raw_msg = (
                        chunk[1]
                        if isinstance(chunk, tuple)
                        and len(chunk) > 1
                        and isinstance(chunk[1], bytes)
                        else b""
                    )
                    if not raw_msg:
                        continue
                    message_obj = email.message_from_bytes(raw_msg)
                    body = _decode_email_body(message_obj)
                    otp = _extract_otp_code(body)
                    if otp:
                        return otp
        except Exception:
            pass

        time.sleep(poll_interval_seconds)

    return ""


def _resolve_otp_code(
    *,
    explicit_otp_code: str,
    dev_hint: str,
    otp_fetch_command: str,
    imap_enabled: bool,
    imap_host: str,
    imap_username: str,
    imap_password: str,
    imap_mailbox: str,
    imap_from_filter: str,
    imap_subject_filter: str,
    otp_timeout_seconds: int,
    otp_poll_interval_seconds: float,
) -> Tuple[str, str]:
    explicit = str(explicit_otp_code or "").strip()
    if explicit:
        return explicit, "explicit"

    hinted = str(dev_hint or "").strip()
    if hinted:
        return hinted, "dev_hint"

    command = str(otp_fetch_command or "").strip()
    if command:
        try:
            if os.name == "nt":
                proc = subprocess.run(
                    ["cmd", "/c", command],
                    capture_output=True,
                    text=True,
                    check=False,
                )
            else:
                proc = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            merged_output = f"{proc.stdout}\n{proc.stderr}".strip()
            otp = _extract_otp_code(merged_output)
            if otp:
                return otp, "otp_fetch_command"
        except Exception:
            pass

    if imap_enabled and imap_host and imap_username and imap_password:
        otp = _fetch_otp_from_imap(
            host=imap_host,
            username=imap_username,
            password=imap_password,
            mailbox=imap_mailbox,
            from_filter=imap_from_filter,
            subject_filter=imap_subject_filter,
            timeout_seconds=otp_timeout_seconds,
            poll_interval_seconds=otp_poll_interval_seconds,
        )
        if otp:
            return otp, "imap"

    return "", "unresolved"


def _run_public_feature_checks(base_url: str) -> Dict[str, Dict[str, Any]]:
    checks: Dict[str, Dict[str, Any]] = {}
    targets = {
        "apk_manifest": ("GET", "/api/marketplace/apk/worldlinco/manifest", None),
        "marketplace_categories": ("GET", "/api/marketplace/categories", None),
        "marketplace_projects": ("GET", "/api/marketplace/projects?skip=0&limit=6", None),
        "ml_detectors_status": ("GET", "/api/marketplace/ml-detectors/status", None),
        "extras_health": ("GET", "/api/marketplace/extras/health", None),
    }

    for name, (method, path, payload) in targets.items():
        status, body = _request_json(
            method=method,
            url=f"{base_url.rstrip('/')}{path}",
            body=payload,
        )
        checks[name] = {
            "status": status,
            "ok": status == 200,
            "detail": body if isinstance(body, dict) else {"raw": str(body)[:300]},
        }
    return checks


def _run_auth_feature_checks(base_url: str, token: str) -> Dict[str, Dict[str, Any]]:
    checks: Dict[str, Dict[str, Any]] = {}

    status_me, body_me = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/api/auth/me",
        token=token,
    )
    checks["auth_me"] = {
        "status": status_me,
        "ok": status_me == 200,
        "email": (body_me or {}).get("email") if isinstance(body_me, dict) else None,
    }

    status_voip, body_voip = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/api/v1/voip/health",
        token=token,
    )
    checks["voip_health"] = {
        "status": status_voip,
        "ok": status_voip == 200,
        "detail": body_voip if isinstance(body_voip, dict) else {"raw": str(body_voip)[:300]},
    }

    status_rooms, body_rooms = _request_json(
        method="GET",
        url=f"{base_url.rstrip('/')}/api/mobile/chat/rooms",
        token=token,
    )
    checks["chat_rooms"] = {
        "status": status_rooms,
        "ok": status_rooms == 200,
        "room_count": len(body_rooms) if isinstance(body_rooms, list) else None,
    }

    for name, path in {
        "interpreter_health": "/api/marketplace/interpreter/health",
        "sorisae_health": "/api/marketplace/sorisae/health",
    }.items():
        status, body = _request_json(
            method="GET",
            url=f"{base_url.rstrip('/')}{path}",
            token=token,
        )
        checks[name] = {
            "status": status,
            "ok": status == 200,
            "detail": body if isinstance(body, dict) else {"raw": str(body)[:300]},
        }

    return checks


def _run_playwright_chain(
    *,
    repo_root: Path,
    marketplace_base_url: str,
    passkey_email: str,
) -> Dict[str, Any]:
    frontend_dir = repo_root / "frontend" / "frontend"
    env = os.environ.copy()
    env["PLAYWRIGHT_USE_WEBSERVER"] = "1"
    env["PLAYWRIGHT_MARKETPLACE_BASE_URL"] = marketplace_base_url
    env["PLAYWRIGHT_PASSKEY_EMAIL"] = passkey_email
    started_at = time.monotonic()

    if os.name == "nt":
        command = ["cmd", "/c", "npm run e2e:marketplace:passkey-feature-chain"]
    else:
        command = ["npm", "run", "e2e:marketplace:passkey-feature-chain"]

    try:
        completed = subprocess.run(
            command,
            cwd=str(frontend_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # pragma: no cover
        return {
            "requested": True,
            "ok": False,
            "exit_code": -1,
            "command": " ".join(command),
            "error": str(exc),
            "summary": {
                "passed": False,
                "failed": True,
                "duration_seconds": round(time.monotonic() - started_at, 3),
            },
        }

    duration_seconds = round(time.monotonic() - started_at, 3)
    stdout_tail = "\n".join(completed.stdout.splitlines()[-120:])
    stderr_tail = "\n".join(completed.stderr.splitlines()[-120:])
    passed = completed.returncode == 0
    return {
        "requested": True,
        "ok": passed,
        "exit_code": completed.returncode,
        "command": " ".join(command),
        "cwd": str(frontend_dir),
        "marketplace_base_url": marketplace_base_url,
        "summary": {
            "passed": passed,
            "failed": not passed,
            "duration_seconds": duration_seconds,
        },
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }


def run_scenario(
    *,
    base_url: str,
    signup_email: str,
    signup_username: str,
    signup_password: str,
    otp_code: str,
    otp_fetch_command: str,
    otp_timeout_seconds: int,
    otp_poll_interval_seconds: float,
    imap_otp_enabled: bool,
    imap_host: str,
    imap_username: str,
    imap_password: str,
    imap_mailbox: str,
    imap_from_filter: str,
    imap_subject_filter: str,
    skip_signup: bool,
    run_playwright: bool,
    playwright_marketplace_base_url: str,
) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "generated_at": _utc_iso(),
        "base_url": base_url,
        "signup": {},
        "login": {},
        "public_feature_checks": {},
        "auth_feature_checks": {},
        "playwright_ui_checks": {
            "requested": run_playwright,
            "ok": False,
            "exit_code": None,
        },
        "playwright_summary": {
            "requested": run_playwright,
            "passed": False,
            "failed": False,
            "duration_seconds": 0.0,
        },
        "notes": [],
    }

    token = ""

    if not skip_signup:
        request_payload = {
            "username": signup_username,
            "email": signup_email,
            "password": signup_password,
            "preferred_language": "ko",
            "country_code": "KR",
            "full_name": "WorldLinco Feature E2E",
            "member_type": "individual",
            "verificationChannel": "email",
        }
        req_status, req_body = _request_json(
            method="POST",
            url=f"{base_url.rstrip('/')}/api/auth/signup/request-code",
            body=request_payload,
        )
        report["signup"]["request_code"] = {
            "status": req_status,
            "ok": req_status == 200,
        }
        if req_status != 200:
            report["signup"]["request_code"]["detail"] = req_body
            report["public_feature_checks"] = _run_public_feature_checks(base_url)
            return report

        session_token = str((req_body or {}).get("signupSessionToken") or "").strip()
        dev_hint = str((req_body or {}).get("devOtpHint") or "").strip()
        selected_code, otp_source = _resolve_otp_code(
            explicit_otp_code=otp_code,
            dev_hint=dev_hint,
            otp_fetch_command=otp_fetch_command,
            imap_enabled=imap_otp_enabled,
            imap_host=imap_host,
            imap_username=imap_username,
            imap_password=imap_password,
            imap_mailbox=imap_mailbox,
            imap_from_filter=imap_from_filter,
            imap_subject_filter=imap_subject_filter,
            otp_timeout_seconds=otp_timeout_seconds,
            otp_poll_interval_seconds=otp_poll_interval_seconds,
        )
        report["signup"]["session_token_issued"] = bool(session_token)
        report["signup"]["dev_otp_hint_available"] = bool(dev_hint)
        report["signup"]["otp_source"] = otp_source

        if not session_token:
            report["signup"]["confirm"] = {
                "status": 0,
                "ok": False,
                "detail": "signupSessionToken missing",
            }
            report["public_feature_checks"] = _run_public_feature_checks(base_url)
            return report

        if not selected_code:
            report["signup"]["confirm"] = {
                "status": 0,
                "ok": False,
                "detail": (
                    "OTP code could not be resolved. "
                    "Use --otp-code, --otp-fetch-command, or IMAP options."
                ),
            }
            report["public_feature_checks"] = _run_public_feature_checks(base_url)
            return report

        confirm_status, confirm_body = _request_json(
            method="POST",
            url=f"{base_url.rstrip('/')}/api/auth/signup/confirm",
            body={
                "signupSessionToken": session_token,
                "verificationCode": selected_code,
                "preferred_language": "ko",
                "country_code": "KR",
            },
        )
        report["signup"]["confirm"] = {
            "status": confirm_status,
            "ok": confirm_status in (200, 201),
            "detail": confirm_body if confirm_status >= 400 else None,
        }
        if confirm_status not in (200, 201):
            report["public_feature_checks"] = _run_public_feature_checks(base_url)
            return report

    login_status, login_body = _request_json(
        method="POST",
        url=f"{base_url.rstrip('/')}/api/auth/login",
        form={"username": signup_email, "password": signup_password},
    )
    token = str((login_body or {}).get("access_token") or "").strip() if isinstance(login_body, dict) else ""
    login_detail = str((login_body or {}).get("detail") or "") if isinstance(login_body, dict) else ""

    passkey_only_blocked = (login_status == 428 and "패스키" in login_detail)
    report["login"] = {
        "status": login_status,
        "ok": login_status == 200 and bool(token),
        "passkey_only_blocked": passkey_only_blocked,
        "detail": login_detail if login_status >= 400 else "",
    }

    report["public_feature_checks"] = _run_public_feature_checks(base_url)

    if token:
        report["auth_feature_checks"] = _run_auth_feature_checks(base_url, token)
    else:
        report["notes"].append("auth_feature_checks skipped because no bearer token was issued.")

    if passkey_only_blocked:
        report["notes"].append(
            "Environment is passkey-only for password login. WebAuthn passkey flow must be validated from browser/app UI."
        )

    if run_playwright:
        repo_root = Path(__file__).resolve().parents[1]
        report["playwright_ui_checks"] = _run_playwright_chain(
            repo_root=repo_root,
            marketplace_base_url=playwright_marketplace_base_url,
            passkey_email=signup_email,
        )
        summary = report["playwright_ui_checks"].get("summary", {})
        report["playwright_summary"] = {
            "requested": True,
            "passed": bool(summary.get("passed")),
            "failed": bool(summary.get("failed")),
            "duration_seconds": float(summary.get("duration_seconds") or 0.0),
        }

    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Formal signup OTP -> login -> feature-by-feature marketplace smoke checks"
        )
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--email", default="")
    parser.add_argument("--username", default="")
    parser.add_argument("--password", default="")
    parser.add_argument("--otp-code", default="")
    parser.add_argument(
        "--otp-fetch-command",
        default="",
        help="Command that prints OTP in stdout/stderr (first 6-digit code is used).",
    )
    parser.add_argument("--otp-timeout-seconds", type=int, default=180)
    parser.add_argument("--otp-poll-interval-seconds", type=float, default=5.0)
    parser.add_argument("--imap-otp-enabled", action="store_true")
    parser.add_argument("--imap-host", default=os.getenv("OTP_IMAP_HOST", ""))
    parser.add_argument("--imap-username", default=os.getenv("OTP_IMAP_USERNAME", ""))
    parser.add_argument("--imap-password", default=os.getenv("OTP_IMAP_PASSWORD", ""))
    parser.add_argument("--imap-mailbox", default=os.getenv("OTP_IMAP_MAILBOX", "INBOX"))
    parser.add_argument("--imap-from-filter", default=os.getenv("OTP_IMAP_FROM", ""))
    parser.add_argument(
        "--imap-subject-filter",
        default=os.getenv("OTP_IMAP_SUBJECT", "WorldLinco"),
    )
    parser.add_argument("--skip-signup", action="store_true")
    parser.add_argument("--with-playwright", action="store_true")
    parser.add_argument(
        "--playwright-marketplace-base-url",
        default="http://127.0.0.1:3005",
    )
    parser.add_argument(
        "--output",
        default=str(Path("evidence") / "marketplace-formal-signup-feature-e2e.json"),
    )
    args = parser.parse_args()

    if args.skip_signup and (not args.email.strip() or not args.password.strip()):
        raise SystemExit("--skip-signup requires both --email and --password")

    if args.email.strip() and not args.username.strip():
        args.username = args.email.split("@")[0]

    if not args.email.strip() or not args.username.strip() or not args.password.strip():
        generated = _gen_signup_identity()
        args.email = generated["email"]
        args.username = generated["username"]
        args.password = generated["password"]

    report = run_scenario(
        base_url=args.base_url,
        signup_email=args.email.strip(),
        signup_username=args.username.strip(),
        signup_password=args.password.strip(),
        otp_code=args.otp_code.strip(),
        otp_fetch_command=args.otp_fetch_command.strip(),
        otp_timeout_seconds=int(args.otp_timeout_seconds),
        otp_poll_interval_seconds=float(args.otp_poll_interval_seconds),
        imap_otp_enabled=bool(args.imap_otp_enabled),
        imap_host=args.imap_host.strip(),
        imap_username=args.imap_username.strip(),
        imap_password=args.imap_password,
        imap_mailbox=args.imap_mailbox.strip() or "INBOX",
        imap_from_filter=args.imap_from_filter.strip(),
        imap_subject_filter=args.imap_subject_filter.strip(),
        skip_signup=bool(args.skip_signup),
        run_playwright=bool(args.with_playwright),
        playwright_marketplace_base_url=args.playwright_marketplace_base_url,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[report] {output_path}")

    public_checks = report.get("public_feature_checks", {})
    public_ok = bool(public_checks) and all(bool(v.get("ok")) for v in public_checks.values())

    signup_default_ok = args.skip_signup
    signup_ok = bool(
        report.get("signup", {}).get("confirm", {}).get("ok", signup_default_ok)
    )
    login_ok = bool(report.get("login", {}).get("ok"))
    passkey_only = bool(report.get("login", {}).get("passkey_only_blocked"))
    playwright_checks = report.get("playwright_ui_checks", {})
    playwright_requested = bool(playwright_checks.get("requested"))
    playwright_ok = bool(playwright_checks.get("ok"))

    auth_checks = report.get("auth_feature_checks", {})
    auth_ok = (not auth_checks) or all(bool(v.get("ok")) for v in auth_checks.values())

    if not public_ok:
        return 1
    if not signup_ok and not args.skip_signup:
        return 1
    if login_ok and auth_ok:
        if playwright_requested and not playwright_ok:
            return 1
        return 0
    if passkey_only and signup_ok:
        if playwright_requested and not playwright_ok:
            return 1
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
