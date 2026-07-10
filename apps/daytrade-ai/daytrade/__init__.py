"""daytrade-ai — AI 주식 단타(스캘핑·초단타) 자동매매 시스템.

설계 아키텍처(Feed → Feature → Detection → AI Inference → Risk → Execution → Monitoring)를
이 개발 환경에서 **실제로 동작하는 Python 소프트웨어**로 구현한 패키지.

안전 원칙(중요):
    - 기본 실행 모드는 ``paper``(모의투자) 이다. 실거래(real broker 주문)는 명시적으로
      ``TradingMode.LIVE`` + 환경변수 게이트를 모두 통과해야만 활성화된다(``config.SafetyGate``).
    - 실거래 브로커 연동은 어댑터 인터페이스(``execution.base.OrderExecutor``)만 제공하며,
      이 저장소에는 실주문을 내는 구현체를 포함하지 않는다(법·규제·계정 책임 분리).
"""

from .version import __version__

__all__ = ["__version__"]
