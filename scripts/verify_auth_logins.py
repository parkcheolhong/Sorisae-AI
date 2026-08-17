from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class Account:
    label: str
    username: str
    password: str


DEFAULT_ACCOUNTS = [
    Account("ADMIN", "ui.admin.round@devanalysis.local", "RoundUi!20260426"),
    Account("MARKET_A", "ui.pod.round.a@devanalysis.local", "x"),
    Account("MARKET_B", "ui.pod.round.b@devanalysis.local", "x"),
]


def verify_login(base_url: str, account: Account) -> tuple[bool, str]:
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        data={"username": account.username, "password": account.password},
        timeout=20,
    )
    token = ""
    try:
        token = str(
            (login_response.json() or {}).get("access_token") or ""
        ).strip()
    except Exception:
        token = ""

    me_status = "NA"
    if token:
        me_response = requests.get(
            f"{base_url}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20,
        )
        me_status = str(me_response.status_code)

    ok = (
        login_response.status_code == 200
        and bool(token)
        and me_status == "200"
    )
    line = (
        f"{account.label} LOGIN={login_response.status_code} "
        f"TOKEN={bool(token)} "
        f"ME={me_status} USER={account.username}"
    )
    return ok, line


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify auth login/api-auth-me for policy test accounts"
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")

    health = requests.get(f"{base_url}/api/health", timeout=15)
    print(f"HEALTH {health.status_code}")
    if health.status_code != 200:
        print("RESULT FAIL: health check failed")
        return 1

    all_ok = True
    for account in DEFAULT_ACCOUNTS:
        ok, line = verify_login(base_url, account)
        print(line)
        all_ok = all_ok and ok

    print(f"RESULT {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
