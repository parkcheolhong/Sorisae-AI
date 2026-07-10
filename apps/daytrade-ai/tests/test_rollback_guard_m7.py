"""M7 (M) 롤백 쿨다운/블랙리스트 + (N) 통합 E2E 시나리오 테스트.

(M): 롤백된 '나쁜 모델' 시그니처를 쿨다운 동안 재승격 금지 + 연속 롤백 시 재학습 일시중지.
(N): 스케줄러→재학습→핫스왑→인위적 KPI 악화→자동 롤백→(블랙리스트 차단·알림 신호)까지 한 흐름 검증.
"""
from __future__ import annotations

from daytrade.config import SignalConfig, TradingConfig
from daytrade.execution import TradeStore
from daytrade.feed.memory import ListFeed
from daytrade.feed.simulated import SimulatedFeed
from daytrade.monitoring import AuditLog, LiveMetrics, registry_from_kpi_verdict
from daytrade.ops import (
    AcceptanceConfig,
    RetrainOrchestrator,
    RunnerConfig,
    LiveRunner,
    Scheduler,
    TriggerConfig,
    add_blacklist,
    auto_rollback,
    is_signature_blacklisted,
    load_current,
    load_history,
    model_signature,
    record_rollback,
    signature_params,
)
from daytrade.pipeline import TradingPipeline

LOOSE = dict(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50)


def _ticks(n=900, seed=4):
    return list(SimulatedFeed(symbol="AAPL", n_ticks=n, seed=seed).ticks())


def _orch(tmp_path, **kw):
    return RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(**LOOSE), n_splits=3, **kw)


def _two_versions(tmp_path):
    orch = _orch(tmp_path)
    ticks = _ticks()
    orch.train_and_validate(ListFeed(ticks))   # v1
    orch.train_and_validate(ListFeed(ticks))   # v2
    return tmp_path / "models", orch, ticks


# ── (M) 시그니처/블랙리스트 ──

def test_model_signature_stable_and_discriminating():
    s1 = model_signature(signature_params({"horizon": 20, "up_bps": 5.0, "down_bps": 5.0, "signal": {}}))
    s2 = model_signature(signature_params({"horizon": 20, "up_bps": 5.0, "down_bps": 5.0, "signal": {}}))
    s3 = model_signature(signature_params({"horizon": 9, "up_bps": 5.0, "down_bps": 5.0, "signal": {}}))
    assert s1 == s2 and s1 != s3


def test_blacklist_expires(tmp_path):
    md = tmp_path / "models"
    add_blacklist(md, "deadbeef", version=2, cooldown_sec=100.0, now=1000.0)
    assert is_signature_blacklisted(md, "deadbeef", now=1050.0) is True   # 쿨다운 중
    assert is_signature_blacklisted(md, "deadbeef", now=1200.0) is False  # 만료


def test_blacklisted_signature_blocks_promotion(tmp_path):
    orch = _orch(tmp_path)
    md = tmp_path / "models"
    sig = model_signature(signature_params(
        {"horizon": 20, "up_bps": 5.0, "down_bps": 5.0, "signal": {}}))
    add_blacklist(md, sig, version=99, cooldown_sec=1e6)
    rep = orch.train_and_validate(ListFeed(_ticks()))
    assert rep.accepted is False
    assert any("blacklisted" in r for r in rep.reasons)
    assert load_current(md) is None      # 승격 안 됨(current 없음)


def test_auto_rollback_blacklists_bad_and_records(tmp_path):
    md, _, _ = _two_versions(tmp_path)
    restored = auto_rollback(md, cooldown_sec=1e6, now=5000.0)
    assert restored["version"] == 1
    # v2(나쁜) 시그니처가 블랙리스트에 등록됨.
    bad_sig = restored["blacklisted_signature"]
    assert is_signature_blacklisted(md, bad_sig, now=5001.0) is True


# ── (M) 연속 롤백 → 재학습 일시중지 ──

def test_retrain_pauses_after_consecutive_rollbacks(tmp_path):
    import time

    orch = _orch(tmp_path, max_consecutive_rollbacks=2,
                 rollback_window_sec=10_000.0, retrain_pause_sec=10_000.0)
    md = tmp_path / "models"
    md.mkdir(parents=True, exist_ok=True)
    now = time.time()
    record_rollback(md, version=3, now=now - 200.0)
    record_rollback(md, version=2, now=now - 100.0)   # 2회 → 한도 도달
    assert orch.retrain_pause_state(now=now) > now
    # orchestrate 가 일시중지로 즉시 반환(트리거/학습 안 함; 내부적으로 real time.time() 사용).
    store = TradeStore(":memory:")
    rep = orch.orchestrate(store, ListFeed(_ticks()),
                           trigger=TriggerConfig(force=True))
    store.close()
    assert rep.triggered is False
    assert any("retrain_paused" in r for r in rep.reasons)


def test_retrain_resumes_after_pause_window(tmp_path):
    orch = _orch(tmp_path, max_consecutive_rollbacks=2,
                 rollback_window_sec=100.0, retrain_pause_sec=100.0)
    md = tmp_path / "models"
    md.mkdir(parents=True, exist_ok=True)
    record_rollback(md, version=3, now=1000.0)
    record_rollback(md, version=2, now=1000.0)
    # window(100s) 밖에서 평가 → 최근 롤백 0 → 중지 아님.
    assert orch.retrain_pause_state(now=2000.0) == 0.0


# ── (N) 통합 E2E ──

def test_e2e_schedule_retrain_hotswap_rollback_alert(tmp_path):
    md = tmp_path / "models"
    audit = AuditLog(str(tmp_path / "audit.jsonl"))
    ticks = _ticks()
    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(md),
        acceptance=AcceptanceConfig(**LOOSE), n_splits=3, audit=audit,
        max_consecutive_rollbacks=2, blacklist_cooldown_sec=1e6)
    store = TradeStore(":memory:")

    # 1) 스케줄러 → 재학습 2회(force) → v1, v2 승격(current.json 핫스왑 포인터).
    mono = [0.0]
    sch = Scheduler(mono=lambda: mono[0], wall=lambda: 0.0, sleep=lambda s: None)
    sch.every("retrain", 1.0, lambda: orch.orchestrate(
        store, ListFeed(ticks), trigger=TriggerConfig(force=True)), run_at_start=True)
    sch.run_due(0.0, 0.0)        # v1
    mono[0] = 5.0
    sch.run_due(5.0, 0.0)        # v2
    assert load_current(md).version == 2
    assert [h["version"] for h in load_history(md)] == [1, 2]

    # 2) 라이브 러너: v1 에서 시작 → v2 감지(핫스왑) → 인위적 낙폭 → 자동 롤백.
    pipe = TradingPipeline(TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True)))
    live = LiveMetrics(symbol="AAPL", mode="paper")
    runner = LiveRunner(
        pipe, feed_factory=lambda: ListFeed(ticks[:5]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=5,
                            model_dir=str(md), rollback_enabled=True,
                            rollback_drawdown_pct=1.0, rollback_window_sec=1e9),
        audit=audit, live=live, sleep=lambda s: None, mono=lambda: 0.0,
        rollback_fn=lambda: auto_rollback(str(md)))
    runner._loaded_model_version = 1
    runner._maybe_reload_model()                 # v2 핫스왑 + 감시 무장
    assert runner._loaded_model_version == 2 and runner._swap_watch is not None
    runner._swap_watch["peak"] = 100_000.0
    runner._equity = lambda: 97_000.0            # 3% 낙폭(>1% 한도)
    runner._check_rollback_guard()
    assert runner._rollbacks == 1
    assert runner._loaded_model_version == 1     # 직전 버전 복귀
    assert load_current(md).version == 1
    # 모델 게이지가 롤백 후 버전 1 반영.
    assert live.registry._metrics["daytrade_model_version"].values

    # 3) 가드: v2 시그니처 블랙리스트 → 동일 파라미터 재승격 차단.
    rep = orch.orchestrate(store, ListFeed(ticks), trigger=TriggerConfig(force=True))
    store.close()
    assert rep.accepted is False and any("blacklisted" in r for r in rep.reasons)

    # 4) 알림 신호: 감사 체인 무결 + kpi_breach·model_reload(롤백) 기록.
    assert audit.verify().ok
    events = [json_line["event"] for json_line in _read_audit(tmp_path / "audit.jsonl")]
    assert "kpi_breach" in events
    assert "model_reload" in events              # 롤백 reload(v1)
    assert "promotion_blocked" in events         # 블랙리스트 차단
    # Alertmanager 트리거 신호: verdict passed=False → daytrade_kpi_passed 0.
    reg = registry_from_kpi_verdict({"metric": "mean_oos_sharpe", "passed": False})
    assert "daytrade_kpi_passed" in reg.render()
    assert reg._metrics["daytrade_kpi_passed"].values[(("metric", "mean_oos_sharpe"),)] == 0.0


def _read_audit(path):
    import json
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out
