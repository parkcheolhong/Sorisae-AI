"""지역 무관 통화 일관성 검증 — 어느 네트워크(LAN·LTE/5G·타 와이파이)에서나 동일하게 실행.

원거리 통화 먹통("신호만 받고 음성이 안 흐름")의 원인은 거의 항상 TURN 릴레이 미도달이다.
이 스크립트는 *실행한 그 네트워크에서* 다음을 측정해 일관된 PASS/FAIL 로 보고한다:

  1) 백엔드 도달성   : GET {base}/api/health (200 이면 OK)
  2) TURN 시그널 포트 : turn 호스트:포트 TCP 연결 (CGNAT 뒤에서도 릴레이 진입점에 닿는지)

같은 도구를 LAN 과 LTE 핫스팟에서 각각 돌려 결과가 동일해야 "지역 무관 일관" 이다.
의존성 없음(stdlib) — 폰 테더링 노트북/서버 어디서나 즉시 구동.

사용:
  python scripts/verify_turn_relay.py
  python scripts/verify_turn_relay.py --base-url https://metanova1004.com --turn turn:211.218.172.124:3478
  # --turn 미지정 시: env TURN_URLS → coturn/.env(TURN_EXTERNAL_IP:TURN_LISTENING_PORT) 순으로 자동 탐지
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple


def _read_coturn_env() -> dict:
    """coturn/.env 또는 .env.example 에서 TURN 엔드포인트 힌트를 읽는다(있으면)."""
    root = Path(__file__).resolve().parents[1]
    out: dict = {}
    for name in (".env", ".env.example"):
        p = root / "coturn" / name
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out.setdefault(k.strip(), v.strip())
        if out:
            break
    return out


def _parse_host_port(turn_url: str, default_port: int = 3478) -> Optional[Tuple[str, int]]:
    """'turn:host:port' / 'turns:host:port?transport=tcp' / 'host:port' → (host, port)."""
    s = (turn_url or "").strip()
    if not s:
        return None
    s = re.sub(r"^stuns?:", "", re.sub(r"^turns?:", "", s))
    s = s.split("?", 1)[0]
    if ":" in s:
        host, _, port = s.rpartition(":")
        try:
            return host, int(port)
        except ValueError:
            return host or s, default_port
    return s, default_port


def _discover_turn_targets(explicit: Optional[str]) -> List[Tuple[str, int]]:
    raw = explicit or os.getenv("TURN_URLS", "") or os.getenv("TURN_URL", "")
    targets: List[Tuple[str, int]] = []
    if raw:
        for part in raw.split(","):
            hp = _parse_host_port(part)
            if hp:
                targets.append(hp)
    if not targets:
        env = _read_coturn_env()
        ip = env.get("TURN_EXTERNAL_IP", "").strip()
        port = env.get("TURN_LISTENING_PORT", "3478").strip() or "3478"
        if ip and not ip.startswith("203.0.113."):  # .example 의 더미 IP 제외
            try:
                targets.append((ip, int(port)))
            except ValueError:
                pass
    return targets


def _check_http(base_url: str, timeout: float) -> Tuple[bool, str]:
    url = base_url.rstrip("/") + "/api/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "verify-turn-relay/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            code = resp.getcode()
            return (200 <= code < 300), f"HTTP {code}"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def _check_tcp(host: str, port: int, timeout: float) -> Tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, "TCP connect OK"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="지역 무관 통화 일관성 검증(백엔드+TURN 도달성)")
    ap.add_argument("--base-url", default=os.getenv("VERIFY_BASE_URL", "https://metanova1004.com"))
    ap.add_argument("--turn", default=None, help="turn:host:port (미지정 시 env/coturn 자동 탐지)")
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    args = ap.parse_args(argv)

    net = "unknown"
    try:
        net = socket.gethostname()
    except Exception:
        pass

    results: dict = {"network_host": net, "base_url": args.base_url, "checks": []}

    ok_http, http_detail = _check_http(args.base_url, args.timeout)
    results["checks"].append({"name": "backend_health", "ok": ok_http, "detail": http_detail})

    turn_targets = _discover_turn_targets(args.turn)
    if not turn_targets:
        results["checks"].append({
            "name": "turn_relay", "ok": False,
            "detail": "TURN 엔드포인트 미탐지 — --turn 지정 또는 TURN_URLS/coturn .env 설정 필요(=원거리 통화 불가)",
        })
    else:
        for host, port in turn_targets:
            ok_tcp, tcp_detail = _check_tcp(host, port, args.timeout)
            results["checks"].append({
                "name": f"turn_relay {host}:{port}", "ok": ok_tcp, "detail": tcp_detail,
            })

    results["all_ok"] = all(c["ok"] for c in results["checks"])

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(f"[verify] network={net} base={args.base_url}")
        for c in results["checks"]:
            flag = "PASS" if c["ok"] else "FAIL"
            print(f"  [{flag}] {c['name']}: {c['detail']}")
        verdict = "지역 무관 일관 통화 가능 신호" if results["all_ok"] else "원거리 통화 불가/불일치 — 위 FAIL 항목 해소 필요"
        print(f"[verify] {'OK' if results['all_ok'] else 'NG'} — {verdict}")
        print("[verify] 같은 명령을 LAN 과 LTE 핫스팟에서 각각 실행해 결과가 동일해야 합니다.")

    return 0 if results["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
