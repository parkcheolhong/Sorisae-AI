import socket
import subprocess
import urllib.error
from unittest import mock

import requests

from backend.services.shinsegye.engine_hub import _dispatch_to_flask_server

BASE = "http://127.0.0.1:8000"
MASTER_SLOT = "slot106_sorisae_master_system.py"
MASTER_CONTAINER = "devanalysis114-sorisae-master-system"


def main() -> None:
    session = requests.Session()
    login = session.post(
        f"{BASE}/api/auth/login",
        data={"username": "119cash@naver.com", "password": "space0215@"},
        timeout=10,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    reg_runtime = session.post(
        f"{BASE}/api/marketplace/sorisae/register",
        headers=headers,
        json={"engine_type": "runtime_probe", "slot_file": "slot999_failure_probe.py"},
        timeout=10,
    )
    reg_missing = session.post(
        f"{BASE}/api/marketplace/sorisae/register",
        headers=headers,
        json={"engine_type": "missing_probe", "slot_file": "slot998_not_exists_probe.py"},
        timeout=10,
    )
    print(f"REGISTER|runtime={reg_runtime.status_code}|missing={reg_missing.status_code}")

    def dispatch(label: str, engine: str) -> None:
        payload = {
            "engine_type": engine,
            "context": {"probe": label},
            "entry_fn": "main",
            "use_module_adapter": True,
            "adapter_entry_candidates": ["run", "execute", "start"],
        }
        resp = session.post(
            f"{BASE}/api/marketplace/sorisae/dispatch",
            headers=headers,
            json=payload,
            timeout=20,
        )
        body = resp.json()
        if resp.status_code >= 400:
            detail = body.get("detail", {}) if isinstance(body, dict) else {}
            print(
                f"{label}|kind={engine}|http={resp.status_code}|"
                f"status={detail.get('status')}|error_code={detail.get('error_code')}|"
                f"retryable={detail.get('retryable')}|source={detail.get('source')}"
            )
            return

        print(
            f"{label}|kind={engine}|http={resp.status_code}|"
            f"status={body.get('status')}|error_code={body.get('error_code')}|"
            f"retryable={body.get('retryable')}|source={body.get('source')}"
        )

    for round_label in ("R1", "R2"):
        dispatch(round_label, "unknown_probe")
        dispatch(round_label, "missing_probe")
        dispatch(round_label, "runtime_probe")

        subprocess.run(["docker", "stop", MASTER_CONTAINER], check=True, stdout=subprocess.DEVNULL)
        try:
            dispatch(round_label, "master")
        finally:
            subprocess.run(["docker", "start", MASTER_CONTAINER], check=True, stdout=subprocess.DEVNULL)

    with mock.patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError(socket.timeout("timed out")),
    ):
        timeout_1 = _dispatch_to_flask_server("master", MASTER_SLOT, {}, timeout=0.01)
    with mock.patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError(socket.timeout("timed out")),
    ):
        timeout_2 = _dispatch_to_flask_server("master", MASTER_SLOT, {}, timeout=0.01)

    print(
        "T1|kind=timeout_simulated|"
        f"status={timeout_1.get('status')}|error_code={timeout_1.get('error_code')}|"
        f"retryable={timeout_1.get('retryable')}|source={timeout_1.get('source')}"
    )
    print(
        "T2|kind=timeout_simulated|"
        f"status={timeout_2.get('status')}|error_code={timeout_2.get('error_code')}|"
        f"retryable={timeout_2.get('retryable')}|source={timeout_2.get('source')}"
    )


if __name__ == "__main__":
    main()
