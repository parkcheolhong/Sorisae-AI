"""M7 — 데이터·재학습 오케스트레이션 테스트(트리거→학습→워크포워드→export→핫스왑)."""
from __future__ import annotations

from datetime import datetime, timezone

from daytrade.config import SignalConfig
from daytrade.execution import TradeStore
from daytrade.feed.simulated import SimulatedFeed
from daytrade.inference.model import HeuristicModel
from daytrade.inference.trt import HotSwapModel
from daytrade.ops import (
    AcceptanceConfig,
    RetrainOrchestrator,
    TriggerConfig,
    evaluate_trigger,
)
from daytrade.types import Fill, Order, OrderSide


def _seed_store(equities, fills=30):
    store = TradeStore(":memory:")
    rid = store.start_run(mode="paper", symbol="AAPL",
                          started_at=datetime.now(timezone.utc).isoformat())
    for i in range(fills):
        order = Order(symbol="AAPL", side=OrderSide.BUY, qty=10, ts_ns=i)
        store.record_fill(Fill(order=order, filled_qty=10, avg_price=100.0, ts_ns=i,
                               slippage=0.0001, status="filled"), run_id=rid)
    for i, eq in enumerate(equities):
        store.record_equity(i, eq, run_id=rid)
    return store, rid


# ---------------- 트리거 판정 ----------------

def test_trigger_fires_on_drawdown():
    # 자본곡선이 100만→98만(=낙폭 약 2%) → 재학습 트리거.
    store, rid = _seed_store([1_000_000, 1_005_000, 980_000, 985_000])
    d = evaluate_trigger(store, rid, cfg=TriggerConfig(max_drawdown_pct=1.5, min_new_fills=10))
    assert d.should_retrain
    assert any("drawdown" in r for r in d.reasons)
    assert d.live["fills"] == 30
    store.close()


def test_trigger_skips_on_insufficient_fills():
    store, rid = _seed_store([1_000_000, 1_001_000], fills=3)
    d = evaluate_trigger(store, rid, cfg=TriggerConfig(min_new_fills=20))
    assert not d.should_retrain
    assert any("insufficient_fills" in r for r in d.reasons)
    store.close()


def test_trigger_force():
    store, rid = _seed_store([1_000_000, 1_000_100], fills=1)
    d = evaluate_trigger(store, rid, cfg=TriggerConfig(force=True))
    assert d.should_retrain and "force" in d.reasons
    store.close()


# ---------------- 학습·검증·export ----------------

def test_train_validate_and_artifacts(tmp_path):
    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50),
        n_splits=3,
    )
    rep = orch.train_and_validate(SimulatedFeed(symbol="AAPL", n_ticks=1200, seed=7))
    assert rep.trained and rep.accepted
    assert rep.wf_summary["n_folds"] >= 1
    # JSON 아티팩트 + current 포인터 생성.
    assert rep.artifacts["json"].endswith("model_v1.json")
    assert (tmp_path / "models" / "current.json").exists()
    assert rep.model_version == 1


def test_validation_rejects_with_strict_gate(tmp_path):
    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.999, max_overfit_gap=0.0, min_samples=50),
        n_splits=3,
    )
    rep = orch.train_and_validate(SimulatedFeed(symbol="AAPL", n_ticks=1000, seed=3))
    assert rep.trained and not rep.accepted
    assert "validation_rejected" in rep.reasons
    assert not rep.artifacts  # 거절 → 아티팩트 미생성


# ---------------- 핫스왑 승격 + 엔드투엔드 ----------------

def test_promote_hotswaps_model(tmp_path):
    audit_events = []

    class _Audit:
        def append(self, event, **kw):
            audit_events.append(event)

    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50),
        n_splits=3, audit=_Audit(),
    )
    hot = HotSwapModel(active=HeuristicModel())
    rep = orch.train_and_validate(SimulatedFeed(symbol="AAPL", n_ticks=1200, seed=11))
    orch.promote(rep, hotswap=hot)
    assert rep.promoted
    assert hot.generation == 1                       # 원자적 교체 발생
    assert not isinstance(hot.active, HeuristicModel)  # 새 학습 모델로 교체
    assert "model_hotswap" in audit_events


def test_orchestrate_end_to_end(tmp_path):
    store, rid = _seed_store([1_000_000, 1_004_000, 982_000, 986_000])  # 낙폭 트리거
    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50),
        n_splits=3,
    )
    hot = HotSwapModel(active=HeuristicModel())
    rep = orch.orchestrate(store, SimulatedFeed(symbol="AAPL", n_ticks=1200, seed=5),
                           run_id=rid, trigger=TriggerConfig(max_drawdown_pct=1.5, min_new_fills=10),
                           hotswap=hot)
    assert rep.triggered and rep.trained and rep.accepted and rep.promoted
    assert hot.generation == 1
    store.close()


def test_tune_and_validate_integrates_tuning(tmp_path):
    from daytrade.feed.simulated import SimulatedFeed as _SF
    from daytrade.training import RiskConstraints

    ticks = list(_SF(symbol="AAPL", n_ticks=900, seed=4).ticks())
    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50),
        n_splits=3,
    )
    rep = orch.tune_and_validate(
        ticks, n_trials=4, metric="mean_oos_sharpe", backend="random",
        constraints=RiskConstraints(max_worst_mdd_pct=5.0), tuning_seed=1,
    )
    assert rep.trained and rep.accepted
    # 튜닝 메타가 리포트와 current.json 에 기록됨.
    assert rep.tuning["backend"] == "random" and rep.tuning["metric"] == "mean_oos_sharpe"
    assert set(rep.tuning["best_params"]) >= {"horizon", "up_bps", "lr", "epochs"}
    import json as _json
    current = _json.loads((tmp_path / "models" / "current.json").read_text(encoding="utf-8"))
    assert "tuning" in current and "signal" in current


def test_orchestrate_no_trigger_skips_training(tmp_path):
    store, rid = _seed_store([1_000_000, 1_000_100], fills=2)  # 데이터 부족 → 트리거 안함
    orch = RetrainOrchestrator(model_dir=str(tmp_path / "models"))
    rep = orch.orchestrate(store, SimulatedFeed(symbol="AAPL", n_ticks=500, seed=1),
                           run_id=rid, trigger=TriggerConfig(min_new_fills=20))
    assert not rep.triggered and not rep.trained
    store.close()
