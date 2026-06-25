"""M7 (H) — current.json 런타임 결선 테스트.

핫스왑 포인터(current.json)를 읽어 추론 모델 + best 시그널 임계를 실제 런타임(파이프라인/러너)에
적용하는지 검증한다. 재학습 오케스트레이터가 만든 current.json 을 입력으로 사용한다.
"""
from __future__ import annotations

import json

from daytrade.config import SignalConfig, TradingConfig
from daytrade.feed.memory import ListFeed
from daytrade.feed.simulated import SimulatedFeed
from daytrade.ops import (
    AcceptanceConfig,
    CurrentModel,
    LiveRunner,
    RetrainOrchestrator,
    RunnerConfig,
    apply_signal_overrides,
    load_current,
    load_history,
    rollback_current,
)
from daytrade.pipeline import TradingPipeline


def _orch(tmp_path):
    return RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50),
        n_splits=3,
    )


def _make_two_versions(tmp_path):
    """두 번 학습·승격 → history 에 v1,v2 적재(롤백 후보 확보)."""
    ticks = list(SimulatedFeed(symbol="AAPL", n_ticks=900, seed=4).ticks())
    orch = _orch(tmp_path)
    orch.train_and_validate(ListFeed(ticks))   # v1
    orch.train_and_validate(ListFeed(ticks))   # v2
    return tmp_path / "models", orch, ticks


def _make_current(tmp_path):
    """재학습으로 실제 current.json + 모델 아티팩트 생성(force)."""
    ticks = list(SimulatedFeed(symbol="AAPL", n_ticks=900, seed=4).ticks())
    orch = RetrainOrchestrator(
        signal=SignalConfig(use_ai=True), model_dir=str(tmp_path / "models"),
        acceptance=AcceptanceConfig(min_oos_bal_acc=0.0, max_overfit_gap=1.0, min_samples=50),
        n_splits=3,
    )
    rep = orch.tune_and_validate(ticks, n_trials=4, backend="random", tuning_seed=1)
    assert rep.promoted
    return tmp_path / "models", rep, ticks


# ── 레지스트리 로드/override ──

def test_load_current_none_when_missing(tmp_path):
    assert load_current(tmp_path / "nope") is None


def test_load_current_and_apply_overrides(tmp_path):
    model_dir, rep, _ = _make_current(tmp_path)
    cur = load_current(model_dir)
    assert isinstance(cur, CurrentModel)
    assert cur.version == rep.model_version
    assert cur.model_path and ("model_v" in cur.model_path)
    assert {"ai_threshold", "obi_threshold", "volume_spike_ratio"} <= set(cur.signal)

    base = TradingConfig(signal=SignalConfig(obi_threshold=1.0, volume_spike_ratio=9.9))
    applied = apply_signal_overrides(base, cur)
    assert applied.signal.obi_threshold == cur.signal["obi_threshold"]
    assert applied.signal.volume_spike_ratio == cur.signal["volume_spike_ratio"]
    assert applied.signal.ai_buy_threshold == cur.signal["ai_threshold"]
    # 원본 config 는 불변(replace 로 새 객체 반환).
    assert base.signal.obi_threshold == 1.0


def test_apply_overrides_partial_keeps_defaults(tmp_path):
    base = TradingConfig(signal=SignalConfig(obi_threshold=123.0, volume_spike_ratio=4.0,
                                             ai_buy_threshold=0.8))
    cur = CurrentModel(version=1, model_path=None, signal={"obi_threshold": 999.0})
    applied = apply_signal_overrides(base, cur)
    assert applied.signal.obi_threshold == 999.0
    assert applied.signal.volume_spike_ratio == 4.0   # 누락 키 → 유지
    assert applied.signal.ai_buy_threshold == 0.8


# ── 파이프라인 런타임 핫스왑 ──

def test_pipeline_reload_from_current(tmp_path):
    model_dir, _, _ = _make_current(tmp_path)
    cfg = TradingConfig(symbols=("AAPL",),
                        signal=SignalConfig(use_ai=True, obi_threshold=1.0, volume_spike_ratio=9.9))
    pipe = TradingPipeline(cfg)
    info = pipe.reload_from_current(str(model_dir))
    assert info is not None and info["version"] >= 1
    cur = load_current(model_dir)
    # 시그널 임계가 런타임 설정 + 탐지 엔진에 반영됨.
    assert pipe.config.signal.obi_threshold == cur.signal["obi_threshold"]
    assert pipe.detection.config.obi_threshold == cur.signal["obi_threshold"]


def test_pipeline_reload_none_when_no_current(tmp_path):
    pipe = TradingPipeline(TradingConfig(symbols=("AAPL",)))
    assert pipe.reload_from_current(str(tmp_path / "empty")) is None


# ── 러너 무중단 핫스왑(시동 + 세션 경계) ──

def test_runner_loads_current_on_start(tmp_path):
    model_dir, rep, ticks = _make_current(tmp_path)
    cfg = TradingConfig(symbols=("AAPL",),
                        signal=SignalConfig(use_ai=True, obi_threshold=1.0))
    pipe = TradingPipeline(cfg)
    reloads = []
    runner = LiveRunner(
        pipe, feed_factory=lambda: ListFeed(ticks[:50]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=50,
                            model_dir=str(model_dir)),
        sleep=lambda s: None, mono=lambda: 0.0,
        on_reload=reloads.append,
    )
    summary = runner.run()
    assert summary["model_version"] == rep.model_version
    assert summary["model_reloads"] == 1
    assert reloads and reloads[0]["version"] == rep.model_version
    # 시그널 임계가 실제 적용됨.
    cur = load_current(model_dir)
    assert pipe.config.signal.obi_threshold == cur.signal["obi_threshold"]


def test_runner_exposes_model_gauges(tmp_path):
    from daytrade.monitoring import LiveMetrics

    model_dir, rep, ticks = _make_current(tmp_path)
    pipe = TradingPipeline(TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True)))
    live = LiveMetrics(symbol="AAPL", mode="paper")
    runner = LiveRunner(
        pipe, feed_factory=lambda: ListFeed(ticks[:30]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=30,
                            model_dir=str(model_dir)),
        sleep=lambda s: None, mono=lambda: 0.0, live=live,
    )
    runner.run()
    text = live.registry.render()
    # M7-I: 모델 버전·핫스왑 게이지가 /metrics 텍스트에 노출됨.
    assert "daytrade_model_version" in text
    assert "daytrade_model_reloads_total" in text
    assert live.registry._metrics["daytrade_model_version"].values  # 값이 채워짐


# ── 모델 롤백(M7-L) ──

def test_history_records_promotions(tmp_path):
    model_dir, _, _ = _make_two_versions(tmp_path)
    hist = load_history(model_dir)
    assert [h["version"] for h in hist] == [1, 2]
    assert load_current(model_dir).version == 2


def test_rollback_current_to_prior(tmp_path):
    model_dir, _, _ = _make_two_versions(tmp_path)
    restored = rollback_current(model_dir)
    assert restored["version"] == 1 and restored["rolled_back_from"] == 2
    cur = load_current(model_dir)
    assert cur.version == 1
    assert cur.raw.get("rolled_back_from") == 2


def test_rollback_to_specific_version(tmp_path):
    model_dir, _, _ = _make_two_versions(tmp_path)
    # v2 가 현재 → to_version=1 명시.
    assert rollback_current(model_dir, to_version=1)["version"] == 1


def test_rollback_none_when_no_prior(tmp_path):
    model_dir, rep, ticks = _make_current(tmp_path)  # 단일 버전만.
    assert rollback_current(model_dir) is None


def test_orchestrator_rollback_audits(tmp_path):
    from daytrade.monitoring import AuditLog

    model_dir, _, _ = _make_two_versions(tmp_path)
    audit = AuditLog(str(tmp_path / "audit.jsonl"))
    orch = _orch(tmp_path)
    orch.audit = audit
    restored = orch.rollback()
    assert restored["version"] == 1
    assert audit.verify().ok


def test_runner_auto_rollback_on_drawdown(tmp_path):
    model_dir, _, ticks = _make_two_versions(tmp_path)
    # 현재 current.json=v2. 러너를 v1 에서 시작했다고 가정 → v2 승격 감지 시 감시 무장.
    pipe = TradingPipeline(TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True)))
    events = []
    runner = LiveRunner(
        pipe, feed_factory=lambda: ListFeed(ticks[:10]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=10,
                            model_dir=str(model_dir), rollback_enabled=True,
                            rollback_drawdown_pct=1.0, rollback_window_sec=300.0),
        sleep=lambda s: None, mono=lambda: 0.0,
        rollback_fn=lambda: rollback_current(str(model_dir)),
        on_reload=events.append,
    )
    runner._loaded_model_version = 1            # v1 에서 시작
    runner._maybe_reload_model()                # v2 감지 → 로드 + 감시 무장
    assert runner._loaded_model_version == 2
    assert runner._swap_watch is not None
    # 스왑 후 2% 낙폭 시뮬(peak 대비) → 가드가 롤백 실행.
    runner._swap_watch["peak"] = 100_000.0
    runner._equity = lambda: 98_000.0           # 2% 하락
    runner._check_rollback_guard()
    assert runner._rollbacks == 1
    assert runner._loaded_model_version == 1    # 직전 버전 복귀
    assert load_current(model_dir).version == 1
    assert any(e.get("event") == "rollback" for e in events)


def test_runner_rollback_window_expiry_disarms(tmp_path):
    model_dir, _, ticks = _make_two_versions(tmp_path)

    class _Wall:
        t = 0.0

        def __call__(self):
            return self.t

    wall = _Wall()
    pipe = TradingPipeline(TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True)))
    runner = LiveRunner(
        pipe, feed_factory=lambda: ListFeed(ticks[:5]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=5,
                            model_dir=str(model_dir), rollback_enabled=True,
                            rollback_window_sec=300.0),
        sleep=lambda s: None, mono=lambda: 0.0, wall=wall,
        rollback_fn=lambda: rollback_current(str(model_dir)),
    )
    runner._loaded_model_version = 1
    wall.t = 0.0
    runner._maybe_reload_model()                # arm (armed_wall=0)
    assert runner._swap_watch is not None
    wall.t = 1000.0
    runner._check_rollback_guard()              # 1000-0>300 → 윈도 경과 → 해제(롤백 없음)
    assert runner._swap_watch is None
    assert runner._rollbacks == 0


def test_runner_hotswaps_on_new_version(tmp_path):
    model_dir, rep, ticks = _make_current(tmp_path)
    pipe = TradingPipeline(TradingConfig(symbols=("AAPL",), signal=SignalConfig(use_ai=True)))
    runner = LiveRunner(
        pipe, feed_factory=lambda: ListFeed(ticks[:10]),
        config=RunnerConfig(symbol="AAPL", heartbeat_sec=1e9, max_ticks=10,
                            model_dir=str(model_dir)),
        sleep=lambda s: None, mono=lambda: 0.0,
    )
    runner._maybe_reload_model()
    assert runner._loaded_model_version == rep.model_version
    v0 = runner._model_reloads
    # 같은 버전 재점검 → 추가 리로드 없음(불필요한 swap 방지).
    runner._maybe_reload_model()
    assert runner._model_reloads == v0
    # 새 버전 승격(파일 갱신) → 무중단 핫스왑.
    cur_file = model_dir / "current.json"
    data = json.loads(cur_file.read_text(encoding="utf-8"))
    data["version"] = rep.model_version + 1
    cur_file.write_text(json.dumps(data), encoding="utf-8")
    runner._maybe_reload_model()
    assert runner._loaded_model_version == rep.model_version + 1
    assert runner._model_reloads == v0 + 1
