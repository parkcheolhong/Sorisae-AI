"""알림 규칙 평가기(설계서 §10-5 Alertmanager 대응) — 의존성 없는 인프로세스 규칙 엔진.

런타임 지표 스냅샷(dict)에 규칙을 적용해 경보(Alert)를 생성한다. Prometheus/Alertmanager 가
있는 운영에서는 동일 임계를 `config/alert_rules.yml` 로 옮겨 쓰며, 여기서는 봇/테스트가 즉시
자체 경보를 낼 수 있게 한다(서킷브레이커·이상손실·연결끊김·레이턴시·주문거절률).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass(frozen=True)
class Alert:
    name: str
    severity: str  # info | warning | critical
    message: str
    value: float


@dataclass(frozen=True)
class AlertRule:
    name: str
    severity: str
    predicate: Callable[[dict], bool]
    message: Callable[[dict], str]
    value_key: str = ""

    def evaluate(self, snapshot: dict) -> Alert | None:
        if self.predicate(snapshot):
            val = float(snapshot.get(self.value_key, 0.0)) if self.value_key else 0.0
            return Alert(self.name, self.severity, self.message(snapshot), val)
        return None


def default_rules(
    *,
    max_drawdown_pct: float = 2.0,
    max_latency_ms_p99: float = 5.0,
    max_reject_rate: float = 0.5,
    max_staleness_ms: float = 5_000.0,
) -> list[AlertRule]:
    """운영 기본 규칙 세트. 임계는 설계서 §8 위험관리/§1 레이턴시 표 기준."""
    return [
        AlertRule(
            "CircuitBreakerHalted", "critical",
            lambda s: bool(s.get("halted")),
            lambda s: "서킷브레이커 발동 — 신규 진입 중단(레이턴시/일일손실 한도 초과)",
        ),
        AlertRule(
            "DrawdownExceeded", "critical",
            lambda s: float(s.get("max_drawdown_pct", 0.0)) >= max_drawdown_pct,
            lambda s: f"최대낙폭 {s.get('max_drawdown_pct'):.2f}% ≥ 한도 {max_drawdown_pct}%",
            value_key="max_drawdown_pct",
        ),
        AlertRule(
            "LatencyP99High", "warning",
            lambda s: float(s.get("latency_ms_p99", 0.0)) > max_latency_ms_p99,
            lambda s: f"처리 레이턴시 p99 {s.get('latency_ms_p99'):.2f}ms > 예산 {max_latency_ms_p99}ms",
            value_key="latency_ms_p99",
        ),
        AlertRule(
            "OrderRejectRateHigh", "warning",
            lambda s: _reject_rate(s) > max_reject_rate,
            lambda s: f"주문 거절률 {_reject_rate(s)*100:.1f}% > 한도 {max_reject_rate*100:.0f}%",
            value_key="",
        ),
        AlertRule(
            "FeedStale", "critical",
            lambda s: float(s.get("staleness_ms", 0.0)) > max_staleness_ms,
            lambda s: f"피드 정체 {s.get('staleness_ms'):.0f}ms > {max_staleness_ms:.0f}ms (연결 끊김 의심)",
            value_key="staleness_ms",
        ),
    ]


def _reject_rate(s: dict) -> float:
    orders = float(s.get("orders_submitted", 0.0))
    rejects = float(s.get("rejects", 0.0))
    return rejects / orders if orders > 0 else 0.0


@dataclass
class AlertEngine:
    rules: list[AlertRule] = field(default_factory=default_rules)

    def evaluate(self, snapshot: dict) -> list[Alert]:
        out = []
        for rule in self.rules:
            a = rule.evaluate(snapshot)
            if a is not None:
                out.append(a)
        return out
