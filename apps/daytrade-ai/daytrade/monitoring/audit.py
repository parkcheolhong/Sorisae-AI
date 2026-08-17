"""불변 감사 로그(설계서 §8 감사 / §10-5) — 해시 체인 WAL(append-only, tamper-evident).

주문·취소·거절·체결 등 거래 이벤트를 **추가 전용(append-only) JSONL** 로 기록하고, 각 레코드를
직전 레코드 해시와 연결(hash chain)해 사후 변조를 탐지한다(블록체인식 무결성). 5년 보관은 운영
정책(스토리지 수명주기)으로 강제한다. 외부 의존성 없음(`hashlib`/`json`).

레코드 스키마(JSON 한 줄):
    {"seq", "ts", "event", "payload", "prev_hash", "hash"}
  hash = sha256(prev_hash + canonical_json({seq, ts, event, payload}))
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone

GENESIS_HASH = "0" * 64


def _canonical(obj: dict) -> str:
    """결정적 직렬화(키 정렬·공백 제거) — 해시 안정성 보장."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(prev_hash: str, record_core: dict) -> str:
    return hashlib.sha256((prev_hash + _canonical(record_core)).encode("utf-8")).hexdigest()


@dataclass
class VerifyResult:
    ok: bool
    records: int
    broken_seq: int | None = None
    reason: str = ""


class AuditLog:
    """해시 체인 append-only 감사 로그.

    Args:
        path: JSONL 파일 경로. 기존 파일이 있으면 마지막 해시를 이어받아 체인 연장.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._seq = 0
        self._last_hash = GENESIS_HASH
        if os.path.exists(path):
            self._resume()

    def _resume(self) -> None:
        last = None
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last = line
        if last:
            rec = json.loads(last)
            self._seq = int(rec["seq"])
            self._last_hash = rec["hash"]

    def append(self, event: str, **payload) -> dict:
        """이벤트를 체인에 추가하고 기록된 레코드(dict)를 반환."""
        self._seq += 1
        core = {
            "seq": self._seq,
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "payload": payload,
        }
        h = _hash(self._last_hash, core)
        record = {**core, "prev_hash": self._last_hash, "hash": h}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(_canonical({**core, "prev_hash": self._last_hash, "hash": h}) + "\n")
        self._last_hash = h
        return record

    def read_all(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        out = []
        with open(self.path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
        return out

    def verify(self) -> VerifyResult:
        """체인 무결성 검증 — 어느 한 레코드라도 변조되면 그 지점을 보고."""
        prev = GENESIS_HASH
        records = self.read_all()
        for i, rec in enumerate(records):
            core = {"seq": rec["seq"], "ts": rec["ts"], "event": rec["event"], "payload": rec["payload"]}
            if rec.get("prev_hash") != prev:
                return VerifyResult(False, len(records), rec.get("seq"), "prev_hash 불일치(체인 절단/변조)")
            expected = _hash(prev, core)
            if rec.get("hash") != expected:
                return VerifyResult(False, len(records), rec.get("seq"), "hash 불일치(레코드 변조)")
            if rec["seq"] != i + 1:
                return VerifyResult(False, len(records), rec.get("seq"), "seq 비연속(누락/재정렬)")
            prev = rec["hash"]
        return VerifyResult(True, len(records))
