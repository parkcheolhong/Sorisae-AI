"""백테스트 연동 — Backtrader 어댑터 + 리포트 고도화(설계서 §9 검증 도구).

자체 워크포워드 백테스트(`training/walkforward.py`)가 핵심 검증을 담당하지만, 성숙한 외부
프레임워크(Backtrader: 지표·브로커·수수료 모델·분석기)로 **교차검증·리서치**를 하고 싶을 때를 위한
어댑터다. 틱 → OHLCV 바 집계 코어는 **의존성 없이**(`ticks_to_ohlcv`) 항상 동작하고, Backtrader/
pandas 결선부는 설치 시에만 활성(미설치 시 명확한 ImportError). `report.py` 는 equity curve 기반
리스크/성과 분석 + JSON·HTML 리포트를 제공한다.
"""
from .backtrader_adapter import (
    Bar,
    bars_to_dataframe,
    has_backtrader,
    run_backtrader,
    ticks_to_backtrader_feed,
    ticks_to_ohlcv,
)
from .report import (
    BacktestAnalytics,
    analyze_equity_curve,
    analyze_run,
    report_to_html,
    report_to_json,
)

__all__ = [
    "Bar",
    "ticks_to_ohlcv",
    "bars_to_dataframe",
    "ticks_to_backtrader_feed",
    "run_backtrader",
    "has_backtrader",
    "BacktestAnalytics",
    "analyze_equity_curve",
    "analyze_run",
    "report_to_json",
    "report_to_html",
]
