"""Call Orchestrator (#3) 단위테스트.

핵심 불변식: 플래그 off면 완전 no-op, 켜지면 라이프사이클/정책이 동작하고,
integration 훅은 절대 throw 하지 않는다.
"""

import pytest  # pyright: ignore[reportMissingImports]

from backend.communication.orchestrator.config import CallOrchestratorConfig
from backend.communication.orchestrator.manager import CallOrchestrator
from backend.communication.orchestrator.models import (
    CallStateV2,
    CallLifecycle,
    is_valid_transition,
)
from backend.communication.orchestrator import integration as orch_integration


def _cfg(**kw) -> CallOrchestratorConfig:
    base = dict(enabled=True, ttl_sec=3600, max_calls=100, max_events=8,
                max_concurrent_active=0, enforce_policy=False)
    base.update(kw)
    return CallOrchestratorConfig(**base)


def test_disabled_is_noop():
    orch = CallOrchestrator(config=_cfg(enabled=False))
    assert orch.on_call_init("call-1", session_id="s1") is None
    assert orch.on_status("call-1", "active") is None
    assert orch.get("call-1") is None
    assert orch.evaluate_admission().allow is True
    assert orch.active_count() == 0


def test_lifecycle_transitions_recorded():
    orch = CallOrchestrator(config=_cfg())
    orch.on_call_init("call-1", session_id="s1", route="app_webrtc", initial_status="connecting")
    orch.on_status("call-1", "active")
    lc = orch.on_call_end("call-1", status="ended")
    assert lc is not None
    assert lc.state == CallStateV2.ENDED
    assert lc.session_id == "s1"
    states = [e.state for e in lc.events]
    assert states == [CallStateV2.CONNECTING, CallStateV2.ACTIVE, CallStateV2.ENDED]
    assert all(not e.out_of_order for e in lc.events)


def test_out_of_order_transition_flagged_not_rejected():
    orch = CallOrchestrator(config=_cfg())
    orch.on_call_init("call-1", initial_status="ended")  # terminal first
    lc = orch.on_status("call-1", "active")  # ended -> active is invalid
    assert lc is not None
    assert lc.events[-1].out_of_order is True
    assert lc.state == CallStateV2.ACTIVE  # 관찰만, 거부 아님


def test_router_status_mapping():
    assert CallStateV2.from_router_status("callee_offline") == CallStateV2.RINGING
    assert CallStateV2.from_router_status("dialer_required") == CallStateV2.CONNECTING
    assert CallStateV2.from_router_status("weird") == CallStateV2.INITIATING
    assert CallStateV2.ENDED.is_terminal() and CallStateV2.MISSED.is_terminal()
    assert not CallStateV2.ACTIVE.is_terminal()


def test_admission_observe_vs_enforce():
    # 관찰 모드: 상한 초과해도 allow.
    orch = CallOrchestrator(config=_cfg(max_concurrent_active=1, enforce_policy=False))
    orch.on_call_init("c1", initial_status="active")
    d_obs = orch.evaluate_admission()
    assert d_obs.allow is True and d_obs.code == "over_cap_observe_only"

    # 강제 모드: 상한 도달 시 거부.
    orch2 = CallOrchestrator(config=_cfg(max_concurrent_active=1, enforce_policy=True))
    orch2.on_call_init("c1", initial_status="active")
    d_enf = orch2.evaluate_admission()
    assert d_enf.allow is False and d_enf.code == "max_concurrent_reached"


def test_active_count_tracks_state():
    orch = CallOrchestrator(config=_cfg())
    orch.on_call_init("c1", initial_status="active")
    orch.on_call_init("c2", initial_status="ringing")
    assert orch.active_count() == 1
    orch.on_call_end("c1")
    assert orch.active_count() == 0


def test_events_capped():
    orch = CallOrchestrator(config=_cfg(max_events=3))
    orch.on_call_init("c1", initial_status="connecting")
    for _ in range(10):
        orch.on_status("c1", "active")
        orch.on_status("c1", "connecting")
    lc = orch.get("c1")
    assert lc is not None and len(lc.events) == 3


def test_purge_expired_only_terminal():
    cfg = _cfg(ttl_sec=0)
    orch = CallOrchestrator(config=cfg)
    orch.on_call_init("active-call", initial_status="active")
    orch.on_call_init("ended-call", initial_status="ended")
    purged = orch.purge_expired()
    assert purged == 1  # 종료된 것만
    assert orch.get("active-call") is not None
    assert orch.get("ended-call") is None


def test_is_valid_transition_helper():
    assert is_valid_transition(CallStateV2.INITIATING, CallStateV2.ACTIVE)
    assert is_valid_transition(CallStateV2.ACTIVE, CallStateV2.ENDED)
    assert not is_valid_transition(CallStateV2.ENDED, CallStateV2.ACTIVE)
    assert is_valid_transition(CallStateV2.ACTIVE, CallStateV2.ACTIVE)  # self ok


def test_integration_noop_when_disabled(monkeypatch):
    monkeypatch.delenv("COMM_V2_CALL_ORCHESTRATOR", raising=False)
    orch_integration.reset_for_test()
    # 절대 throw 하지 않고, 비활성이면 admission allow.
    orch_integration.on_call_init("c1", session_id="s1", initial_status="active")
    orch_integration.on_call_status("c1", "active")
    orch_integration.on_call_end("c1")
    assert orch_integration.evaluate_admission().allow is True
    orch_integration.reset_for_test()


def test_integration_records_when_enabled(monkeypatch):
    monkeypatch.setenv("COMM_V2_CALL_ORCHESTRATOR", "true")
    orch_integration.reset_for_test()
    try:
        orch_integration.on_call_init("c1", session_id="s1", initial_status="connecting")
        orch_integration.on_call_status("c1", "active")
        orch_integration.on_call_end("c1")
        lc = orch_integration._get().get("c1")
        assert lc is not None and lc.state == CallStateV2.ENDED
    finally:
        orch_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_CALL_ORCHESTRATOR", raising=False)
        orch_integration.reset_for_test()


def test_integration_never_throws(monkeypatch):
    monkeypatch.setenv("COMM_V2_CALL_ORCHESTRATOR", "true")
    orch_integration.reset_for_test()
    try:
        # None/빈 입력에도 throw 금지.
        orch_integration.on_call_init(None, session_id=None)
        orch_integration.on_call_status(None, None)
        orch_integration.on_call_end(None)
    finally:
        orch_integration.reset_for_test()
        monkeypatch.delenv("COMM_V2_CALL_ORCHESTRATOR", raising=False)
        orch_integration.reset_for_test()
