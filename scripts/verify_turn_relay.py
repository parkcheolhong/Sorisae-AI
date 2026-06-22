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
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import socket
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import List, Optional, Tuple

_STUN_MAGIC = 0x2112A442


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
        # 백엔드 한-노브 정책과 동일: TURN_SECRET 만 있으면 TURN_DOMAIN/TURN_REALM:TURN_PORT 로 유도.
        if (os.getenv("TURN_SECRET", "") or "").strip():
            domain = (
                os.getenv("TURN_DOMAIN", "")
                or os.getenv("TURN_REALM", "")
                or "metanova1004.com"
            ).strip()
            port = (os.getenv("TURN_PORT", "3478") or "3478").strip()
            try:
                targets.append((domain, int(port)))
            except ValueError:
                pass
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


# --- TURN Allocate 프로브(미디어 경로 실측) ---------------------------------
# 시그널 포트(3478) TCP 연결만으로는 '음성이 실제로 릴레이되는가'를 알 수 없다.
# TURN Allocate 요청을 실제 자격증명(use-auth-secret)으로 보내, 서버가 릴레이 주소를
# 발급하는지(=미디어 평면 동작)까지 확인한다. 이것이 '신호만 받고 음성 먹통'의 진짜 게이트다.


def _stun_attr(attr_type: int, value: bytes) -> bytes:
    pad = (4 - (len(value) % 4)) % 4
    return struct.pack("!HH", attr_type, len(value)) + value + (b"\x00" * pad)


def _build_allocate(txid: bytes, *, username: bytes = b"", realm: bytes = b"",
                    nonce: bytes = b"", secret: str = "") -> bytes:
    # REQUESTED-TRANSPORT=UDP(17)
    attrs = _stun_attr(0x0019, struct.pack("!BBH", 17, 0, 0))
    if username:
        attrs += _stun_attr(0x0006, username)
        attrs += _stun_attr(0x0014, realm)
        attrs += _stun_attr(0x0015, nonce)
        # MESSAGE-INTEGRITY: key = MD5(username:realm:password), password=base64(HMAC-SHA1(secret, username))
        password = base64.b64encode(
            hmac.new(secret.encode(), username, hashlib.sha1).digest()
        )
        key = hashlib.md5(username + b":" + realm + b":" + password).digest()
        header_len = len(attrs) + 24  # + MESSAGE-INTEGRITY attr(4+20)
        msg = struct.pack("!HHI", 0x0003, header_len, _STUN_MAGIC) + txid + attrs
        integrity = hmac.new(key, msg, hashlib.sha1).digest()
        attrs += _stun_attr(0x0008, integrity)
    return struct.pack("!HHI", 0x0003, len(attrs), _STUN_MAGIC) + txid + attrs


def _parse_attrs(data: bytes) -> dict:
    out: dict = {}
    i = 20
    while i + 4 <= len(data):
        at, ln = struct.unpack("!HH", data[i:i + 4])
        val = data[i + 4:i + 4 + ln]
        out[at] = val
        i += 4 + ln + ((4 - (ln % 4)) % 4)
    return out


def _xor_addr(val: bytes, txid: bytes) -> str:
    if len(val) < 8:
        return "?"
    fam = val[1]
    port = struct.unpack("!H", val[2:4])[0] ^ (_STUN_MAGIC >> 16)
    if fam == 0x01:
        ip = bytes(b ^ m for b, m in zip(val[4:8], struct.pack("!I", _STUN_MAGIC)))
        return f"{ip[0]}.{ip[1]}.{ip[2]}.{ip[3]}:{port}"
    return f"[v6]:{port}"


def _turn_allocate(host: str, port: int, secret: str, realm: str, timeout: float) -> Tuple[bool, str]:
    """실제 TURN Allocate 로 릴레이 주소 발급까지 확인(미디어 평면)."""
    if not secret:
        return False, "TURN_SECRET 미설정 — allocate 프로브 불가"
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            # 1차: 비인증 → 401 + REALM/NONCE 회수
            txid = secrets.token_bytes(12)
            sock.send(_build_allocate(txid))
            resp = sock.recv(2048)
            attrs = _parse_attrs(resp)
            srv_realm = attrs.get(0x0014, realm.encode()) or realm.encode()
            nonce = attrs.get(0x0015, b"")
            if not nonce:
                return False, "NONCE 미수신(401 응답 없음) — TURN 인증 흐름 비정상"
            # 2차: use-auth-secret 시간제한 자격으로 인증 Allocate
            username = f"{int(time.time()) + 600}:verify".encode()
            txid2 = secrets.token_bytes(12)
            sock.send(_build_allocate(
                txid2, username=username, realm=srv_realm, nonce=nonce, secret=secret
            ))
            resp2 = sock.recv(2048)
            mtype = struct.unpack("!H", resp2[0:2])[0]
            if mtype == 0x0103:  # Allocate Success
                relayed = _parse_attrs(resp2).get(0x0016, b"")
                addr = _xor_addr(relayed, txid2) if relayed else "?"
                return True, f"Allocate 성공 — 릴레이 주소 {addr} (미디어 평면 OK)"
            err = _parse_attrs(resp2).get(0x0009, b"")
            code = (err[2] * 100 + err[3]) if len(err) >= 4 else "?"
            return False, f"Allocate 실패(에러 {code}) — 자격/시크릿 불일치 또는 릴레이 거부"
        finally:
            sock.close()
    except socket.timeout:
        return False, "UDP 타임아웃 — 3478/udp 또는 미디어 릴레이 차단 가능"
    except Exception as e:  # noqa: BLE001
        return False, f"{type(e).__name__}: {e}"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="지역 무관 통화 일관성 검증(백엔드+TURN 도달성)")
    ap.add_argument("--base-url", default=os.getenv("VERIFY_BASE_URL", "https://metanova1004.com"))
    ap.add_argument("--turn", default=None, help="turn:host:port (미지정 시 env/coturn 자동 탐지)")
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--json", action="store_true", help="결과를 JSON 으로 출력")
    ap.add_argument("--allocate", action="store_true",
                    help="TURN Allocate 실측(미디어 평면) — TURN_SECRET 필요")
    args = ap.parse_args(argv)
    turn_secret = (os.getenv("TURN_SECRET", "") or "").strip()
    turn_realm = (os.getenv("TURN_DOMAIN", "") or os.getenv("TURN_REALM", "") or "metanova1004.com").strip()

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
            if args.allocate:
                ok_alloc, alloc_detail = _turn_allocate(
                    host, port, turn_secret, turn_realm, args.timeout
                )
                results["checks"].append({
                    "name": f"turn_allocate {host}:{port}", "ok": ok_alloc, "detail": alloc_detail,
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
