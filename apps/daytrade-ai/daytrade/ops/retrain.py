"""M7 — 데이터·재학습 오케스트레이션(설계서 §7 백테스트→실전 / §2 재학습 루프).

상주 러너가 쌓는 `TradeStore`(체결/자본곡선)·감사로그를 **트리거 입력**으로,
캡처된 시장 틱을 **학습 입력**으로 받아 다음을 자동 연결한다.

    트리거 판정(라이브 성과/체결/주기) → 데이터셋 빌드(라벨링) → 재학습(logreg)
    → 워크포워드 검증(OOS, 과최적화 갭) → 인수 게이트 → ONNX/JSON export
    → 모델 핫스왑 트리거(Blue-Green, 감사로그 기록).

원칙:
- **train/serve skew 제거**: 학습 피처는 런타임과 동일한 `FeatureEngine`(`build_dataset`).
- **누수 차단**: 워크포워드 분할은 시간순 + `purge=horizon`(embargo).
- **안전한 승격**: 검증 인수기준을 통과한 후보만 핫스왑. 의존성 0(numpy/JSON) 경로 항상 동작,
  onnx 설치 시 ONNX 아티팩트도 함께 생성(생산용).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np  # pyright: ignore[reportMissingImports]

from ..config import SignalConfig
from ..feed.base import MarketFeed
from ..training.dataset import build_dataset
from ..training.logreg import train_logreg
from ..training.onnx_export import export_numpy_logreg_to_onnx
from ..training.walkforward import walk_forward_validate
from ..types import MarketTick


@dataclass
class TriggerConfig:
    min_new_fills: int = 20          # 최소 신규 체결(데이터 충분성)
    max_drawdown_pct: float = 1.5    # 라이브 낙폭 한도 초과 시 재학습(드리프트 의심)
    min_return_pct: float = 0.0      # 라이브 수익률이 이 값 미만이면 재학습
    force: bool = False              # 스케줄/수동 강제


@dataclass
class AcceptanceConfig:
    min_oos_bal_acc: float = 0.50    # 평균 OOS balanced accuracy 하한(랜덤=0.5)
    max_overfit_gap: float = 0.10    # 평균 과최적화 갭 상한
    min_samples: int = 100           # 데이터셋 최소 표본


@dataclass
class TriggerDecision:
    should_retrain: bool
    reasons: list[str]
    live: dict


@dataclass
class RetrainReport:
    triggered: bool
    trained: bool = False
    accepted: bool = False
    promoted: bool = False
    reasons: list[str] = field(default_factory=list)
    live: dict = field(default_factory=dict)
    n_samples: int = 0
    train_metrics: dict = field(default_factory=dict)
    wf_summary: dict = field(default_factory=dict)
    artifacts: dict = field(default_factory=dict)
    model_version: int = 0
    tuning: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "triggered": self.triggered, "trained": self.trained,
            "accepted": self.accepted, "promoted": self.promoted,
            "reasons": self.reasons, "live": self.live, "n_samples": self.n_samples,
            "wf_summary": self.wf_summary, "artifacts": self.artifacts,
            "model_version": self.model_version, "tuning": self.tuning,
        }


def _drawdown_pct(curve: list[float]) -> float:
    if len(curve) < 2:
        return 0.0
    arr = np.asarray(curve, dtype=float)
    peak = np.maximum.accumulate(arr)
    return float(np.max((peak - arr) / np.where(peak == 0, 1.0, peak)) * 100.0)


def evaluate_trigger(store, run_id: int | None = None, *, cfg: TriggerConfig | None = None) -> TriggerDecision:
    """TradeStore(체결/자본곡선)에서 라이브 성과를 읽어 재학습 트리거를 판정."""
    cfg = cfg or TriggerConfig()
    rid = run_id if run_id is not None else store.latest_run_id()
    curve = store.equity_curve(rid) if rid is not None else []
    fills = store.fills_count(rid) if rid is not None else 0
    start_eq = curve[0] if curve else 0.0
    end_eq = curve[-1] if curve else 0.0
    ret_pct = ((end_eq - start_eq) / start_eq * 100.0) if start_eq else 0.0
    dd = _drawdown_pct(curve)
    live = {"run_id": rid, "fills": fills, "return_pct": round(ret_pct, 4),
            "max_drawdown_pct": round(dd, 4), "equity_points": len(curve)}

    reasons: list[str] = []
    if cfg.force:
        reasons.append("force")
    if fills < cfg.min_new_fills:
        # 데이터가 부족하면 재학습해도 신뢰 낮음 → 트리거하지 않음(force 제외).
        if not cfg.force:
            return TriggerDecision(False, [f"insufficient_fills({fills}<{cfg.min_new_fills})"], live)
    if dd >= cfg.max_drawdown_pct:
        reasons.append(f"drawdown {dd:.2f}%>={cfg.max_drawdown_pct}%")
    if ret_pct < cfg.min_return_pct:
        reasons.append(f"return {ret_pct:.2f}%<{cfg.min_return_pct}%")
    return TriggerDecision(bool(reasons), reasons, live)


class RetrainOrchestrator:
    """재학습 오케스트레이터. 데이터셋→학습→검증→export→핫스왑을 한 번에 구동."""

    def __init__(
        self,
        *,
        signal: SignalConfig | None = None,
        model_dir: str = "models",
        horizon: int = 20,
        up_bps: float = 5.0,
        down_bps: float = 5.0,
        n_splits: int = 4,
        acceptance: AcceptanceConfig | None = None,
        audit=None,
        blacklist_cooldown_sec: float = 86_400.0,
        max_consecutive_rollbacks: int = 3,
        rollback_window_sec: float = 86_400.0,
        retrain_pause_sec: float = 86_400.0,
    ) -> None:
        self.signal = signal or SignalConfig()
        self.model_dir = Path(model_dir)
        self.horizon = horizon
        self.up_bps = up_bps
        self.down_bps = down_bps
        self.n_splits = n_splits
        self.acceptance = acceptance or AcceptanceConfig()
        self.audit = audit
        # M7-M: 롤백 가드(블랙리스트 쿨다운 + 연속 롤백 시 재학습 일시중지).
        self.blacklist_cooldown_sec = blacklist_cooldown_sec
        self.max_consecutive_rollbacks = max_consecutive_rollbacks
        self.rollback_window_sec = rollback_window_sec
        self.retrain_pause_sec = retrain_pause_sec

    def _next_version(self) -> int:
        self.model_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(self.model_dir.glob("model_v*.json"))
        if not existing:
            return 1
        nums = [int(p.stem.split("v")[-1]) for p in existing if p.stem.split("v")[-1].isdigit()]
        return (max(nums) + 1) if nums else 1

    def train_and_validate(
        self,
        feed: MarketFeed,
        *,
        horizon: int | None = None,
        up_bps: float | None = None,
        down_bps: float | None = None,
        lr: float | None = None,
        epochs: int | None = None,
        meta: dict | None = None,
    ) -> RetrainReport:
        """데이터셋 빌드 → 학습 → 워크포워드 검증 → 인수 게이트 → 아티팩트 저장.

        라벨/학습 하이퍼파라미터(horizon/up_bps/down_bps/lr/epochs)는 튜닝 결과로 override 가능.
        """
        h = horizon if horizon is not None else self.horizon
        ub = up_bps if up_bps is not None else self.up_bps
        db = down_bps if down_bps is not None else self.down_bps
        rep = RetrainReport(triggered=True)
        bundle = build_dataset(feed, self.signal, horizon=h, up_bps=ub, down_bps=db)
        rep.n_samples = len(bundle)
        if rep.n_samples < self.acceptance.min_samples:
            rep.reasons.append(f"insufficient_samples({rep.n_samples}<{self.acceptance.min_samples})")
            return rep

        train_kwargs = {"feature_names": bundle.feature_names, "horizon": bundle.horizon}
        if lr is not None:
            train_kwargs["lr"] = float(lr)
        if epochs is not None:
            train_kwargs["epochs"] = int(epochs)
        model, metrics = train_logreg(bundle.X, bundle.y_buy, bundle.y_sell, **train_kwargs)
        rep.trained = True
        rep.train_metrics = {"val": metrics.get("val", {}), "n_features": metrics.get("n_features")}

        wf = walk_forward_validate(bundle, n_splits=self.n_splits)
        rep.wf_summary = wf.summary
        rep.accepted = self._accept(wf.summary)
        if not rep.accepted:
            rep.reasons.append("validation_rejected")
            return rep

        # M7-M: 블랙리스트 게이트 — 직전에 롤백된 '나쁜 모델'과 동일 시그니처면 재승격 금지(쿨다운).
        from .registry import is_signature_blacklisted, model_signature, signature_params
        cand_sig = model_signature(signature_params(
            {"horizon": h, "up_bps": ub, "down_bps": db, "signal": (meta or {}).get("signal", {})}))
        if is_signature_blacklisted(self.model_dir, cand_sig):
            rep.accepted = False
            rep.reasons.append(f"blacklisted_signature({cand_sig})")
            if self.audit is not None:
                self.audit.append("promotion_blocked", reason="blacklisted", signature=cand_sig)
            return rep

        # 인수 통과 → 버전 아티팩트 저장(JSON 항상, ONNX best-effort).
        version = self._next_version()
        rep.model_version = version
        json_path = self.model_dir / f"model_v{version}.json"
        model.save_json(json_path)
        artifacts = {"json": str(json_path)}
        try:
            onnx_path = self.model_dir / f"model_v{version}.onnx"
            export_numpy_logreg_to_onnx(model, onnx_path)
            artifacts["onnx"] = str(onnx_path)
        except ModuleNotFoundError:
            artifacts["onnx"] = None  # onnx 미설치 — JSON 으로 운영(폴백)
        # 'current' 포인터(러너/배포가 읽는 최신 모델).
        current = self.model_dir / "current.json"
        entry = {
            "version": version, "artifacts": artifacts, "horizon": h,
            "up_bps": ub, "down_bps": db,
            "wf_summary": wf.summary, "updated_at": datetime.now(timezone.utc).isoformat(),
            **(meta or {}),
        }
        current.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
        # 롤백 후보 보관(history.jsonl 에 누적).
        from .registry import append_history
        append_history(self.model_dir, entry)
        artifacts["current"] = str(current)
        rep.artifacts = artifacts
        return rep

    def rollback(self, *, to_version: int | None = None, hotswap=None) -> dict | None:
        """current.json 을 이전(또는 지정) 버전으로 복구하고(선택) 모델 핫스왑·감사.

        나쁜 시그니처를 블랙리스트(쿨다운)에 등록하고 롤백을 기록한다(M7-M). `to_version` 지정 시
        해당 버전으로, 미지정 시 직전 버전으로 복귀.

        반환: 복구된 {version, model_path, signal, rolled_back_from} 또는 후보 없으면 None.
        """
        from .registry import auto_rollback, rollback_current

        if to_version is None:
            restored = auto_rollback(self.model_dir, cooldown_sec=self.blacklist_cooldown_sec)
        else:
            restored = rollback_current(self.model_dir, to_version=to_version)
        if restored is None:
            if self.audit is not None:
                self.audit.append("model_rollback", ok=False, reason="no_prior_version")
            return None
        if hotswap is not None and restored.get("model_path"):
            try:
                hotswap.swap(restored["model_path"])
            except Exception as exc:  # noqa: BLE001 — 스왑 실패는 감사에 남기고 진행
                if self.audit is not None:
                    self.audit.append("model_rollback", ok=False, reason=f"swap_failed:{exc}")
        if self.audit is not None:
            self.audit.append("model_rollback", ok=True, version=restored["version"],
                              rolled_back_from=restored.get("rolled_back_from"),
                              model_path=restored.get("model_path"))
        return restored

    def tune_and_validate(
        self,
        ticks: list[MarketTick],
        *,
        base_config=None,
        n_trials: int = 20,
        metric: str = "mean_oos_sharpe",
        backend: str = "auto",
        constraints=None,
        n_splits: int | None = None,
        tuning_seed: int = 42,
        hotswap=None,
    ) -> RetrainReport:
        """튜닝(워크포워드 Sharpe 목적함수) → best 하이퍼파라미터로 재학습·검증·승격.

        (E) 자동 탐색을 (D) 재학습 게이트와 결합. 튜닝은 walk_forward_backtest(OOS P&L/Sharpe)로
        평가하고, 최적 라벨/학습 파라미터로 logreg 를 재학습한 뒤 동일 인수 게이트를 통과해야 승격.
        """
        from ..config import TradingConfig
        from ..feed.memory import ListFeed
        from ..training.tuning import run_tuning

        paused = self.retrain_pause_state()
        if paused:
            return self._paused_report(paused)
        base = base_config or TradingConfig(signal=replace(self.signal, use_ai=True))
        result = run_tuning(
            ticks, base, n_trials=n_trials, metric=metric, backend=backend,
            constraints=constraints, n_splits=n_splits or self.n_splits, seed=tuning_seed,
        )
        best = result.best_params
        tuning_meta = {
            "backend": result.backend, "metric": result.metric,
            "best_value": result.best_value, "n_trials": len(result.trials),
            "best_params": best,
        }
        rep = self.train_and_validate(
            ListFeed(ticks),
            horizon=int(best["horizon"]), up_bps=float(best["up_bps"]),
            down_bps=float(best["down_bps"]), lr=float(best["lr"]), epochs=int(best["epochs"]),
            meta={"tuning": tuning_meta,
                  "signal": {"ai_threshold": float(best["ai_threshold"]),
                             "obi_threshold": float(best["obi_threshold"]),
                             "volume_spike_ratio": float(best["volume_spike_ratio"])}},
        )
        rep.tuning = tuning_meta
        if rep.accepted:
            self.promote(rep, hotswap=hotswap)
        if self.audit is not None:
            self.audit.append("tune_retrain_result", **rep.as_dict())
        return rep

    def retrain_pause_state(self, now: float | None = None) -> float:
        """연속 롤백 과다 시 재학습 일시중지 만료시각(unixtime). 0=중지 아님(M7-M)."""
        from .registry import retrain_paused_until

        return retrain_paused_until(
            self.model_dir, max_consecutive=self.max_consecutive_rollbacks,
            window_sec=self.rollback_window_sec, pause_sec=self.retrain_pause_sec, now=now)

    def _paused_report(self, until: float) -> RetrainReport:
        reason = f"retrain_paused_until={round(until, 1)}(consecutive_rollbacks)"
        if self.audit is not None:
            self.audit.append("retrain_paused", until=until,
                              max_consecutive=self.max_consecutive_rollbacks)
        return RetrainReport(triggered=False, reasons=[reason])

    def _accept(self, summary: dict) -> bool:
        if not summary.get("n_folds"):
            return False
        bal_buy = summary.get("mean_oos_bal_acc_buy", 0.0)
        bal_sell = summary.get("mean_oos_bal_acc_sell", 0.0)
        gap = summary.get("mean_overfit_gap", 1.0)
        return (min(bal_buy, bal_sell) >= self.acceptance.min_oos_bal_acc
                and gap <= self.acceptance.max_overfit_gap)

    def promote(self, report: RetrainReport, hotswap=None):
        """인수된 후보를 핫스왑(Blue-Green)으로 승격. 감사로그에 기록."""
        if not report.accepted or not report.artifacts:
            return None
        from ..inference.model import load_model

        path = report.artifacts.get("onnx") or report.artifacts["json"]
        new_model = load_model(path)
        prev = None
        if hotswap is not None:
            prev = hotswap.swap(new_model)
        report.promoted = True
        if self.audit is not None:
            self.audit.append("model_hotswap", version=report.model_version,
                              path=path, generation=getattr(hotswap, "generation", None),
                              wf=report.wf_summary)
        return new_model

    def orchestrate(self, store, feed: MarketFeed, *, run_id: int | None = None,
                    trigger: TriggerConfig | None = None, hotswap=None) -> RetrainReport:
        """엔드투엔드: 트리거 판정 → (통과 시) 학습·검증·export → (인수 시) 핫스왑."""
        paused = self.retrain_pause_state()
        if paused:
            return self._paused_report(paused)
        decision = evaluate_trigger(store, run_id, cfg=trigger)
        if self.audit is not None:
            self.audit.append("retrain_trigger", should_retrain=decision.should_retrain,
                              reasons=decision.reasons, live=decision.live)
        if not decision.should_retrain:
            return RetrainReport(triggered=False, reasons=decision.reasons, live=decision.live)

        rep = self.train_and_validate(feed)
        rep.live = decision.live
        rep.reasons = decision.reasons + rep.reasons
        if rep.accepted:
            self.promote(rep, hotswap=hotswap)
        if self.audit is not None:
            self.audit.append("retrain_result", **rep.as_dict())
        return rep
