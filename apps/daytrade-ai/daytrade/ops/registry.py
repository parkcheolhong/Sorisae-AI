"""모델 레지스트리 — `current.json`(M7 핫스왑 포인터)을 런타임 설정으로 결선(설계서 §7).

재학습 오케스트레이터가 승격 시 쓰는 `models/current.json` 에는 모델 아티팩트 경로와 best 시그널
임계(ai/obi/vol)·라벨 horizon·튜닝 메타가 담긴다. 본 모듈은 그것을 읽어:
  - 운영 모델 경로(ONNX 우선, 없으면 JSON)를 고르고,
  - best 시그널 임계를 `SignalConfig` 에 반영한 `TradingConfig` 를 만든다.
이로써 "기록만" 되던 핫스왑 결과가 실제 추론/탐지에 적용된다(`TradingPipeline.reload_from_current`).
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

from ..config import TradingConfig


@dataclass(slots=True)
class CurrentModel:
    version: int
    model_path: str | None        # 운영 추론 모델(ONNX 우선, 없으면 JSON)
    signal: dict = field(default_factory=dict)   # best 시그널 임계(ai_threshold/obi_threshold/volume_spike_ratio)
    horizon: int = 0
    raw: dict = field(default_factory=dict)


def _resolve_safe_model_dir(model_dir: str | Path) -> Path:
    raw = str(model_dir or "").strip()
    if not raw:
        raise ValueError("model_dir 가 비어 있습니다.")
    if "\x00" in raw:
        raise ValueError("model_dir 에 허용되지 않는 문자가 포함되어 있습니다.")
    input_path = Path(raw).expanduser()
    if not input_path.is_absolute() and any(part == ".." for part in input_path.parts):
        raise ValueError("상위 경로(..)는 model_dir 로 허용되지 않습니다.")
    return input_path.resolve() if input_path.is_absolute() else (Path.cwd() / input_path).resolve()


def current_path(model_dir: str | Path) -> Path:
    return _resolve_safe_model_dir(model_dir) / "current.json"


def history_path(model_dir: str | Path) -> Path:
    return _resolve_safe_model_dir(model_dir) / "history.jsonl"


def append_history(model_dir: str | Path, entry: dict) -> None:
    """승격된 current.json 스냅샷을 history.jsonl 에 누적(롤백 후보 보관)."""
    path = history_path(model_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_history(model_dir: str | Path) -> list[dict]:
    """history.jsonl 의 모든 승격 스냅샷(시간순). 없으면 빈 리스트."""
    path = history_path(model_dir)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def rollback_current(model_dir: str | Path, *, to_version: int | None = None) -> dict | None:
    """current.json 을 이전(또는 지정) 버전으로 복구(M7-L 자동/수동 롤백).

    history.jsonl 에서 대상 스냅샷을 골라 current.json 을 덮어쓴다(롤백 메타 첨부).
    대상 미지정 시 **현재 버전보다 작은 가장 최근** 버전으로 복귀. 후보 없으면 None.
    반환: 복구된 {version, model_path, signal} 또는 None.
    """
    from datetime import datetime, timezone

    hist = load_history(model_dir)
    if not hist:
        return None
    cur = load_current(model_dir)
    cur_ver = cur.version if cur is not None else None

    if to_version is not None:
        target = next((h for h in hist if int(h.get("version", -1)) == to_version), None)
    else:
        # 현재보다 낮은 버전 중 최신(가장 큰 버전).
        prior = [h for h in hist if cur_ver is None or int(h.get("version", -1)) < cur_ver]
        target = max(prior, key=lambda h: int(h.get("version", -1)), default=None)
    if target is None:
        return None

    restored = dict(target)
    restored["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
    restored["rolled_back_from"] = cur_ver
    current_path(model_dir).write_text(
        json.dumps(restored, ensure_ascii=False, indent=2), encoding="utf-8")
    artifacts = restored.get("artifacts", {}) or {}
    model_path = artifacts.get("onnx") or artifacts.get("json")
    return {"version": int(restored.get("version", 0)), "model_path": model_path,
            "signal": dict(restored.get("signal", {}) or {}), "rolled_back_from": cur_ver}


def load_current(model_dir: str | Path) -> CurrentModel | None:
    """`<model_dir>/current.json` 을 읽어 CurrentModel 반환. 없으면 None."""
    path = current_path(model_dir)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    artifacts = data.get("artifacts", {}) or {}
    model_path = artifacts.get("onnx") or artifacts.get("json")
    return CurrentModel(
        version=int(data.get("version", 0)),
        model_path=model_path,
        signal=dict(data.get("signal", {}) or {}),
        horizon=int(data.get("horizon", 0) or 0),
        raw=data,
    )


def apply_signal_overrides(config: TradingConfig, current: CurrentModel) -> TradingConfig:
    """current.json 의 best 시그널 임계를 SignalConfig 에 반영한 새 TradingConfig 반환.

    누락 키는 기존 설정을 유지한다(부분 override 안전). `ai_threshold` 는 매수/매도 공통 적용.
    """
    sig = current.signal or {}
    if not sig:
        return config
    ai = sig.get("ai_threshold")
    new_signal = replace(
        config.signal,
        ai_buy_threshold=float(ai) if ai is not None else config.signal.ai_buy_threshold,
        ai_sell_threshold=float(ai) if ai is not None else config.signal.ai_sell_threshold,
        obi_threshold=float(sig.get("obi_threshold", config.signal.obi_threshold)),
        volume_spike_ratio=float(sig.get("volume_spike_ratio", config.signal.volume_spike_ratio)),
    )
    return replace(config, signal=new_signal)


# ── M7-M: 롤백 가드 상태(블랙리스트 + 연속 롤백 → 재학습 일시중지) ──────────────

def guard_path(model_dir: str | Path) -> Path:
    return _resolve_safe_model_dir(model_dir) / "guard.json"


def _load_guard(model_dir: str | Path) -> dict:
    path = guard_path(model_dir)
    if not path.exists():
        return {"blacklist": [], "rollbacks": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    data.setdefault("blacklist", [])
    data.setdefault("rollbacks", [])
    return data


def _save_guard(model_dir: str | Path, state: dict) -> None:
    path = guard_path(model_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def signature_params(entry: dict) -> dict:
    """모델 식별 시그니처용 핵심 파라미터(라벨 + best 시그널 임계)."""
    sig = entry.get("signal", {}) or {}
    return {
        "horizon": entry.get("horizon"),
        "up_bps": entry.get("up_bps"),
        "down_bps": entry.get("down_bps"),
        "ai_threshold": sig.get("ai_threshold"),
        "obi_threshold": sig.get("obi_threshold"),
        "volume_spike_ratio": sig.get("volume_spike_ratio"),
    }


def model_signature(params: dict) -> str:
    """라벨/시그널 파라미터의 안정적 해시(부동소수 노이즈 제거). 같은 '나쁜 모델' 재승격 탐지용."""
    norm = {}
    for k, v in params.items():
        if isinstance(v, float):
            norm[k] = round(v, 4)
        else:
            norm[k] = v
    blob = json.dumps(norm, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def add_blacklist(model_dir: str | Path, signature: str, *, version: int | None,
                  cooldown_sec: float, now: float | None = None) -> None:
    """시그니처를 쿨다운(until) 동안 재승격 금지 목록에 추가."""
    now = time.time() if now is None else now
    state = _load_guard(model_dir)
    state["blacklist"] = [b for b in state["blacklist"] if b.get("signature") != signature]
    state["blacklist"].append({"signature": signature, "version": version,
                               "until": now + cooldown_sec, "added_at": now})
    _save_guard(model_dir, state)


def is_signature_blacklisted(model_dir: str | Path, signature: str, *, now: float | None = None) -> bool:
    """해당 시그니처가 아직 쿨다운 중이면 True(만료 항목은 무시)."""
    now = time.time() if now is None else now
    for b in _load_guard(model_dir)["blacklist"]:
        if b.get("signature") == signature and float(b.get("until", 0.0)) > now:
            return True
    return False


def record_rollback(model_dir: str | Path, *, version: int | None, now: float | None = None) -> None:
    now = time.time() if now is None else now
    state = _load_guard(model_dir)
    state["rollbacks"].append({"version": version, "at": now})
    _save_guard(model_dir, state)


def recent_rollback_count(model_dir: str | Path, *, window_sec: float, now: float | None = None) -> int:
    now = time.time() if now is None else now
    return sum(1 for r in _load_guard(model_dir)["rollbacks"]
               if (now - float(r.get("at", 0.0))) <= window_sec)


def retrain_paused_until(model_dir: str | Path, *, max_consecutive: int, window_sec: float,
                         pause_sec: float, now: float | None = None) -> float:
    """최근 window 내 롤백이 한도 이상이면 (마지막 롤백 + pause_sec) 까지 일시중지. 아니면 0."""
    now = time.time() if now is None else now
    rolls = _load_guard(model_dir)["rollbacks"]
    recent = [float(r.get("at", 0.0)) for r in rolls if (now - float(r.get("at", 0.0))) <= window_sec]
    if len(recent) < max_consecutive:
        return 0.0
    until = max(recent) + pause_sec
    return until if until > now else 0.0


def auto_rollback(model_dir: str | Path, *, cooldown_sec: float = 86_400.0,
                  now: float | None = None) -> dict | None:
    """현재(나쁜) 버전 → 직전 버전 복구 + 나쁜 시그니처 블랙리스트 + 롤백 기록(가드 일원화).

    LiveRunner/오케스트레이터가 동일 동작을 쓰도록 `rollback_current` 를 감싼다.
    """
    now = time.time() if now is None else now
    bad = load_current(model_dir)
    restored = rollback_current(model_dir)
    if restored is None:
        return None
    if bad is not None:
        sig = model_signature(signature_params(bad.raw))
        add_blacklist(model_dir, sig, version=bad.version, cooldown_sec=cooldown_sec, now=now)
        restored["blacklisted_signature"] = sig
    record_rollback(model_dir, version=(bad.version if bad else None), now=now)
    return restored
