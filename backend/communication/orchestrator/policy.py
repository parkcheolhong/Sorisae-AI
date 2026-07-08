"""Call Orchestrator admission/정책 — 순수 함수(부수효과 없음).

현재는 **동시 active 통화 상한**만 구현. 기본은 관찰 전용(allow)이며,
``enforce`` 가 True일 때만 거부할 수 있다. 향후 차단 사용자·요율 제한·시간대 정책
등을 같은 시그니처로 확장한다(`PolicyDecision` 반환).
"""

from __future__ import annotations

from .models import PolicyDecision


def evaluate_admission(
    *,
    active_count: int,
    max_concurrent_active: int,
    enforce: bool,
) -> PolicyDecision:
    """새 통화 admission 결정.

    Args:
        active_count: 현재 active 통화 수.
        max_concurrent_active: 상한(0 = 무제한).
        enforce: True면 상한 초과 시 거부, False면 관찰만(항상 allow하되 사유 기록).
    """

    if max_concurrent_active <= 0:
        return PolicyDecision(allow=True, code="allow", reason="no_concurrency_cap")

    over = active_count >= max_concurrent_active
    if not over:
        return PolicyDecision(
            allow=True, code="allow",
            reason=f"active={active_count}/{max_concurrent_active}",
        )

    if enforce:
        return PolicyDecision(
            allow=False, code="max_concurrent_reached",
            reason=f"active={active_count}>={max_concurrent_active}",
        )
    # 관찰 모드: 초과했지만 허용(데이터만 수집).
    return PolicyDecision(
        allow=True, code="over_cap_observe_only",
        reason=f"active={active_count}>={max_concurrent_active} (observe)",
    )
