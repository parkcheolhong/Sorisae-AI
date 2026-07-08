"""설정 + 안전 게이트(SafetyGate).

실거래(LIVE) 활성화는 **이중 게이트**를 모두 통과해야만 가능하다:
    1) ``TradingConfig.mode == TradingMode.LIVE``
    2) 환경변수 ``DAYTRADE_ALLOW_LIVE == "I_UNDERSTAND_THE_RISK"``
둘 중 하나라도 어긋나면 실행기는 강제로 paper(모의)로 폴백한다. 이는 실수로 실주문이
나가는 것을 코드 레벨에서 차단하기 위함이다(법·규제·자본 손실 방지).
"""
from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from enum import Enum


class TradingMode(str, Enum):
    PAPER = "paper"          # 모의투자(기본)
    BACKTEST = "backtest"    # 과거 데이터 시뮬레이션
    LIVE = "live"            # 실거래(이중 게이트 필요)


LIVE_ENV_KEY = "DAYTRADE_ALLOW_LIVE"
LIVE_ENV_TOKEN = "I_UNDERSTAND_THE_RISK"
SIGNAL_TICK_INTERVAL_MS = 10.0


@dataclass(frozen=True, slots=True)
class RiskConfig:
    """리스크 한도 — 설계서 §8 위험관리 대응."""

    max_position_value: float = 1_000_000.0   # 종목당 최대 시가평가 노출
    max_position_qty: float = 10_000.0         # 종목당 최대 보유 수량
    max_gross_exposure: float = 5_000_000.0    # 전체 총노출 한도
    day_stop_loss_pct: float = 0.02            # 당일 -2% 손절(자본 대비)
    day_take_profit_pct: float = 0.02          # 당일 +2% 익절(옵션)
    max_leverage: float = 1.0                  # 레버리지 상한(1.0=현금)
    # 레이턴시 서킷브레이커: 처리 지연이 이 값을 넘으면 신규 진입 중단.
    max_latency_ms: float = 10.0
    # 슬리피지 가드: 의도가 대비 이 비율 초과 시 주문 거절.
    max_slippage_pct: float = 0.005


@dataclass(frozen=True, slots=True)
class SignalConfig:
    """탐지/추론 임계값 — 설계서 §3 시그널 로직 대응."""

    depth: int = 10                  # 오더북 깊이(레벨)
    obi_threshold: float = 1.0e6     # 오더북 불균형 임계(매수/매도 수량 차)
    volume_spike_ratio: float = 2.0  # 거래량 급증 배수
    momentum_window_ms: float = 10.0 # 마이크로 모멘텀 윈도(ms)
    vwap_window: int = 50            # VWAP 이동 윈도(틱)
    ai_buy_threshold: float = 0.90   # AI 매수 확신 임계
    ai_sell_threshold: float = 0.90  # AI 매도 임계
    use_ai: bool = True              # AI 추론 사용 여부(False=규칙만)

    @property
    def momentum_window_ticks(self) -> int:
        return max(1, math.ceil(self.momentum_window_ms / SIGNAL_TICK_INTERVAL_MS))


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    default_qty: float = 100.0
    # paper 체결 모델: 시장가 슬리피지(미드 대비 bps)와 거래소 거절 확률.
    paper_slippage_bps: float = 1.0          # 1bp = 0.01%
    paper_reject_prob: float = 0.0
    # 비용 모델(설계서 §7 슬리피지/거래비용 반영).
    commission_bps: float = 0.0              # 체결 명목가 대비 수수료(bps), 매수·매도 공통
    sell_tax_bps: float = 0.0                # 매도 시 거래세(bps). 예: KRX 매도세
    # 부분체결: True 면 반대 호가 best 레벨의 가용 수량까지만 체결(현실적 유동성 제약).
    partial_fill: bool = False


@dataclass(slots=True)
class TradingConfig:
    """최상위 설정."""

    mode: TradingMode = TradingMode.PAPER
    symbols: tuple[str, ...] = ("AAPL",)
    starting_cash: float = 1_000_000.0
    risk: RiskConfig = field(default_factory=RiskConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    seed: int | None = 42  # 재현 가능한 시뮬레이션용 RNG 시드

    @classmethod
    def paper(cls, **kwargs) -> "TradingConfig":
        return cls(mode=TradingMode.PAPER, **kwargs)

    @classmethod
    def backtest(cls, **kwargs) -> "TradingConfig":
        return cls(mode=TradingMode.BACKTEST, **kwargs)


@dataclass(frozen=True, slots=True)
class SafetyGate:
    """실거래 허용 여부 판정 결과."""

    requested_mode: TradingMode
    effective_mode: TradingMode
    live_allowed: bool
    reason: str

    @property
    def downgraded(self) -> bool:
        return self.requested_mode != self.effective_mode


def resolve_safety_gate(config: TradingConfig, env: dict[str, str] | None = None) -> SafetyGate:
    """요청 모드와 환경변수 게이트로 **실효 실행 모드**를 결정한다.

    LIVE 요청이라도 환경변수 토큰이 정확히 일치하지 않으면 PAPER 로 강등한다.
    """
    environ = env if env is not None else dict(os.environ)
    requested = config.mode

    if requested != TradingMode.LIVE:
        return SafetyGate(
            requested_mode=requested,
            effective_mode=requested,
            live_allowed=False,
            reason="non-live mode (safe by default)",
        )

    token = environ.get(LIVE_ENV_KEY, "")
    if token == LIVE_ENV_TOKEN:
        return SafetyGate(
            requested_mode=requested,
            effective_mode=TradingMode.LIVE,
            live_allowed=True,
            reason=f"live explicitly authorized via {LIVE_ENV_KEY}",
        )

    return SafetyGate(
        requested_mode=requested,
        effective_mode=TradingMode.PAPER,
        live_allowed=False,
        reason=(
            f"live requested but {LIVE_ENV_KEY} != '{LIVE_ENV_TOKEN}' "
            "→ forced to PAPER for safety"
        ),
    )
