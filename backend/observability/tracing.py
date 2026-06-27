"""OpenTelemetry 분산 트레이싱 — opt-in · 의존성 가드 · fail-open.

레퍼런스 아키텍처 적합성 평가에서 유일한 "명확한 갭"으로 확인된 **정밀 ns 타임스탬프 +
분산 트레이싱**(STT→번역→TTS 발화 단위 추적)의 해소 1단계. 기술서 §0.22 / 체크리스트 §10.

설계 불변식(`backend/voip/metrics.py`·`backend/services/carbon_meter.py` 동일):

1. **기본 비활성** — ``OTEL_TRACING_ENABLED``(1/true/on/yes)일 때만 동작. 미설정 시 즉시 no-op.
2. **의존성 가드** — ``opentelemetry`` 미설치 시 import/기동 안전(예외 흡수, no-op 폴백).
3. **fail-open** — 초기화 실패가 앱 기동·요청 처리를 **절대** 막지 않는다.
4. **NTP 전제** — 타임스탬프 정밀도(±1ms)는 노드 시계(`chrony`) 동기화에 의존(OS 레벨).

활성화(운영, 옵션)::

    pip install -r requirements-observability.txt
    export OTEL_TRACING_ENABLED=1
    export OTEL_EXPORTER_OTLP_ENDPOINT=http://tempo:4317   # 또는 jaeger OTLP
    export OTEL_SERVICE_NAME=devanalysis114-backend

비활성/미설치 시 모든 공개 함수는 부작용 없이 즉시 반환한다.
"""

from __future__ import annotations

import logging
import os
from contextlib import nullcontext

logger = logging.getLogger(__name__)

_ENABLED_VALUES = {"1", "true", "on", "yes"}
_initialized = False


def tracing_enabled() -> bool:
    """``OTEL_TRACING_ENABLED`` 환경변수 게이트(기본 False)."""
    return str(os.getenv("OTEL_TRACING_ENABLED", "")).strip().lower() in _ENABLED_VALUES


def init_tracing(app=None) -> bool:
    """OTel TracerProvider + OTLP exporter 구성 후 FastAPI/httpx 자동 계측.

    Args:
        app: FastAPI 인스턴스(있으면 요청 span 자동 계측). None이면 SDK만 초기화.

    Returns:
        True  — 트레이싱 활성(계측 부착 완료).
        False — 비활성/미설치/초기화 실패(no-op). 어느 경우에도 예외를 올리지 않는다.
    """
    global _initialized
    if _initialized:
        return True
    if not tracing_enabled():
        logger.info("[otel] tracing disabled (OTEL_TRACING_ENABLED unset)")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        service_name = os.getenv("OTEL_SERVICE_NAME", "devanalysis114-backend")
        endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
        trace.set_tracer_provider(provider)

        # FastAPI 자동 계측 — 요청 span + http.server.duration.
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

                FastAPIInstrumentor.instrument_app(app)
            except Exception as exc:  # pragma: no cover - 계측 패키지 미설치
                logger.warning("[otel] FastAPI instrument skipped: %s", exc)

        # 아웃바운드 httpx 자동 계측 — STT/번역/TTS·외부 API 호출을 동일 trace 로 연결.
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

            HTTPXClientInstrumentor().instrument()
        except Exception as exc:  # pragma: no cover - 계측 패키지 미설치
            logger.debug("[otel] httpx instrument skipped: %s", exc)

        _initialized = True
        logger.info(
            "[otel] tracing enabled -> %s (service=%s)", endpoint, service_name
        )
        return True
    except Exception as exc:  # pragma: no cover - 의존성/환경 의존
        logger.warning("[otel] tracing init failed (fail-open): %s", exc)
        return False


class _NoopTracer:
    """OTel 미설치/비활성 시 수동 span 코드가 그대로 동작하도록 하는 폴백 tracer."""

    def start_as_current_span(self, *_args, **_kwargs):  # noqa: D401
        return nullcontext()

    def start_span(self, *_args, **_kwargs):
        return nullcontext()


def get_tracer(name: str = "devanalysis114"):
    """수동 span용 tracer 반환. 미설치/비활성 시 no-op tracer.

    사용 예::

        from backend.observability.tracing import get_tracer
        with get_tracer().start_as_current_span("rag.retrieve"):
            ...
    """
    try:
        from opentelemetry import trace

        return trace.get_tracer(name)
    except Exception:  # pragma: no cover - 미설치 폴백
        return _NoopTracer()
