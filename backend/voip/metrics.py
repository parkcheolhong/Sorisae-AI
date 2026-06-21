"""VoIP 전용 Prometheus 메트릭 (#7 Monitoring) — off-path, best-effort.

설계 불변식:

1. **hot path 무영향** — 모든 record 함수는 예외를 흡수해 **절대 throw 하지 않는다**.
   시그널링/통화 루프의 정상 동작은 메트릭 실패와 무관하다.
2. **의존성 가드** — `prometheus_client` 부재 시 no-op 스텁으로 폴백(임포트 안전).
3. **마켓플레이스 메트릭과 분리** — 같은 레지스트리에 `voip_*` 네임스페이스로 등록되어
   `/metrics`(`backend/main.py`) 한 곳에서 함께 노출된다.

노출 메트릭:
- ``voip_calls_initiated_total{route,mode}``    : 통화 개시(app/pstn × 모드)
- ``voip_active_ws_connections``                : 현재 활성 시그널링 WS(게이지)
- ``voip_ws_connections_total{role}``           : 누적 WS 접속(caller/callee)
- ``voip_signaling_messages_total{type,role}``  : 시그널링 메시지(offer/answer/candidate/…)
- ``voip_signaling_errors_total{reason}``       : 시그널링 거절/오류(auth/room/loop)
- ``voip_turn_credentials_issued_total{kind}``  : TURN 자격 발급(dynamic/static/none)
- ``voip_call_join_latency_seconds``            : 룸 생성→콜리 WS 합류 지연(셋업 프록시)
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:  # 의존성 가드 — prometheus_client 부재 시 no-op.
    from prometheus_client import Counter, Gauge, Histogram

    _PROM = True
except Exception:  # pragma: no cover - 방어적
    _PROM = False


if _PROM:
    CALLS_INITIATED = Counter(
        "voip_calls_initiated_total", "VoIP calls initiated", ["route", "mode"]
    )
    ACTIVE_WS = Gauge(
        "voip_active_ws_connections", "Active VoIP signaling WebSocket connections"
    )
    WS_CONNECTIONS = Counter(
        "voip_ws_connections_total", "VoIP signaling WS connections", ["role"]
    )
    SIGNALING_MESSAGES = Counter(
        "voip_signaling_messages_total", "VoIP signaling messages relayed", ["type", "role"]
    )
    SIGNALING_ERRORS = Counter(
        "voip_signaling_errors_total", "VoIP signaling rejections/errors", ["reason"]
    )
    TURN_ISSUED = Counter(
        "voip_turn_credentials_issued_total", "TURN credentials issued", ["kind"]
    )
    CALL_JOIN_LATENCY = Histogram(
        "voip_call_join_latency_seconds",
        "Latency from room creation to callee WS join (setup proxy)",
        buckets=(0.5, 1, 2, 3, 5, 8, 13, 21, 34, 60),
    )
else:  # pragma: no cover
    CALLS_INITIATED = ACTIVE_WS = WS_CONNECTIONS = None
    SIGNALING_MESSAGES = SIGNALING_ERRORS = TURN_ISSUED = CALL_JOIN_LATENCY = None


def record_call_initiated(route: str, mode: str) -> None:
    try:
        if _PROM:
            CALLS_INITIATED.labels(route=route or "unknown", mode=mode or "unknown").inc()
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] record_call_initiated skipped", exc_info=True)


def record_turn_issued(kind: str) -> None:
    """kind: 'dynamic'(HMAC 시간제한) | 'static'(고정자격) | 'none'(자격 없음)."""

    try:
        if _PROM:
            TURN_ISSUED.labels(kind=kind or "none").inc()
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] record_turn_issued skipped", exc_info=True)


def ws_connected(role: str) -> None:
    try:
        if _PROM:
            ACTIVE_WS.inc()
            WS_CONNECTIONS.labels(role=role or "unknown").inc()
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] ws_connected skipped", exc_info=True)


def ws_disconnected() -> None:
    try:
        if _PROM:
            ACTIVE_WS.dec()
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] ws_disconnected skipped", exc_info=True)


def record_signaling_message(msg_type: str, role: str) -> None:
    try:
        if _PROM:
            SIGNALING_MESSAGES.labels(type=msg_type or "unknown", role=role or "unknown").inc()
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] record_signaling_message skipped", exc_info=True)


def record_signaling_error(reason: str) -> None:
    try:
        if _PROM:
            SIGNALING_ERRORS.labels(reason=reason or "unknown").inc()
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] record_signaling_error skipped", exc_info=True)


def observe_call_join_latency(seconds: float) -> None:
    try:
        if _PROM and seconds is not None and seconds >= 0:
            CALL_JOIN_LATENCY.observe(float(seconds))
    except Exception:  # pragma: no cover
        logger.debug("[voip-metrics] observe_call_join_latency skipped", exc_info=True)
