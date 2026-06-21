"""CallOrchestrator — #3 Call Orchestrator 진입점.

통화 라이프사이클 상태 전이 + admission 정책 + 감사를 캡슐화한다. Session Core와
동일하게 **플래그 off(기본)면 모든 메서드가 무해한 no-op/None 을 반환**한다.
"""

from __future__ import annotations

from typing import Optional

from . import policy as _policy
from .config import CallOrchestratorConfig, get_call_orchestrator_config
from .models import CallLifecycle, CallStateV2, PolicyDecision
from .store import InMemoryLifecycleStore, LifecycleStore


class CallOrchestrator:
    def __init__(
        self,
        store: Optional[LifecycleStore] = None,
        config: Optional[CallOrchestratorConfig] = None,
    ) -> None:
        self._config = config or get_call_orchestrator_config()
        self._store = store or InMemoryLifecycleStore(max_calls=self._config.max_calls)

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    @property
    def store(self) -> LifecycleStore:
        return self._store

    def evaluate_admission(self) -> PolicyDecision:
        """새 통화 admission 결정. 플래그 off면 무조건 allow(관찰조차 안 함)."""

        if not self._config.enabled:
            return PolicyDecision(allow=True, code="orchestrator_disabled", reason="")
        return _policy.evaluate_admission(
            active_count=self._store.active_count(),
            max_concurrent_active=self._config.max_concurrent_active,
            enforce=self._config.enforce_policy,
        )

    def on_call_init(
        self,
        call_id: str,
        *,
        session_id: Optional[str] = None,
        route: Optional[str] = None,
        initial_status: Optional[str] = None,
        admission: Optional[PolicyDecision] = None,
    ) -> Optional[CallLifecycle]:
        if not self._config.enabled or not call_id:
            return None
        lc = self._store.get(call_id)
        if lc is None:
            lc = CallLifecycle(call_id=call_id, session_id=session_id, route=route)
        else:
            if session_id and not lc.session_id:
                lc.session_id = session_id
            if route and not lc.route:
                lc.route = route
        state = CallStateV2.from_router_status(initial_status) if initial_status else CallStateV2.INITIATING
        lc.transition(state, reason="call_init", max_events=self._config.max_events)
        if admission is not None:
            lc.policy_decisions.append(admission)
        self._store.put(lc)
        return lc

    def on_status(
        self,
        call_id: str,
        status: str,
        *,
        reason: Optional[str] = None,
    ) -> Optional[CallLifecycle]:
        if not self._config.enabled or not call_id:
            return None
        lc = self._store.get(call_id)
        if lc is None:
            lc = CallLifecycle(call_id=call_id)
        lc.transition(
            CallStateV2.from_router_status(status),
            reason=reason or "status_update",
            max_events=self._config.max_events,
        )
        self._store.put(lc)
        return lc

    def on_call_end(
        self,
        call_id: str,
        *,
        status: str = "ended",
        reason: Optional[str] = None,
    ) -> Optional[CallLifecycle]:
        if not self._config.enabled or not call_id:
            return None
        lc = self._store.get(call_id)
        if lc is None:
            lc = CallLifecycle(call_id=call_id)
        lc.transition(
            CallStateV2.from_router_status(status),
            reason=reason or "call_end",
            max_events=self._config.max_events,
        )
        self._store.put(lc)
        return lc

    def get(self, call_id: str) -> Optional[CallLifecycle]:
        if not self._config.enabled or not call_id:
            return None
        return self._store.get(call_id)

    def active_count(self) -> int:
        if not self._config.enabled:
            return 0
        return self._store.active_count()

    def purge_expired(self) -> int:
        if not self._config.enabled:
            return 0
        return self._store.purge_expired(self._config.ttl_sec)
