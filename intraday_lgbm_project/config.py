"""
config.py — 단타 LightGBM 자동매매 연구 프로젝트 전역 설정
모든 파라미터는 이 파일 한 곳에서 관리합니다.
"""

from dataclasses import dataclass, field
from typing import List, Optional


# ─────────────────────────────────────────
# 데이터 설정
# ─────────────────────────────────────────
@dataclass
class DataConfig:
    ticker: str = "AAPL"
    interval: str = "5m"          # yfinance 지원 인터벌: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1d
    start_date: str = "2024-01-01"
    end_date: str = "2025-01-01"
    # 로컬 CSV 경로 (None 이면 yfinance 다운로드)
    csv_path: Optional[str] = None
    # 학습/검증/테스트 분할 비율
    train_ratio: float = 0.65
    val_ratio: float = 0.15
    # test_ratio = 1 - train_ratio - val_ratio


# ─────────────────────────────────────────
# 신호 설정
# ─────────────────────────────────────────
@dataclass
class SignalConfig:
    # RSI
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    # MACD
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    # Volume spike (배수)
    volume_spike_mult: float = 2.0
    # EMA Crossover
    ema_short: int = 9
    ema_long: int = 21


# ─────────────────────────────────────────
# 피처 설정
# ─────────────────────────────────────────
@dataclass
class FeatureConfig:
    # 수익률 룩백
    return_periods: List[int] = field(default_factory=lambda: [1, 3, 5, 10, 20])
    # 변동성 윈도우
    volatility_windows: List[int] = field(default_factory=lambda: [5, 10, 20])
    # 거래량 MA 윈도우
    volume_ma_windows: List[int] = field(default_factory=lambda: [5, 10, 20])
    # 가격 모멘텀 윈도우
    momentum_windows: List[int] = field(default_factory=lambda: [3, 5, 10])
    # ATR 기간
    atr_period: int = 14
    # RSI 기간 목록
    rsi_periods: List[int] = field(default_factory=lambda: [7, 14, 21])
    # 시간 피처 사용 여부
    use_time_features: bool = True
    # NaN 처리 방식: "drop" | "fill_zero" | "fill_ffill"
    nan_handling: str = "drop"


# ─────────────────────────────────────────
# 라벨 설정
# ─────────────────────────────────────────
@dataclass
class LabelConfig:
    # 예측 대상 미래 봉 수
    forward_bars: int = 3
    # 수익(롱 진입) 판정 임계값 (소수점, 예: 0.003 = 0.3%)
    profit_threshold: float = 0.003
    # 손실 판정 임계값 (양수로 입력, 절댓값 사용)
    loss_threshold: float = 0.003
    # 라벨 방식: "binary" (수익 여부) | "ternary" (수익/중립/손실)
    label_mode: str = "binary"
    # 타겟 컬럼 이름
    target_col: str = "label"


# ─────────────────────────────────────────
# 모델 설정
# ─────────────────────────────────────────
@dataclass
class ModelConfig:
    # LightGBM 하이퍼파라미터
    lgbm_params: dict = field(default_factory=lambda: {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 31,
        "max_depth": -1,
        "learning_rate": 0.05,
        "n_estimators": 500,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_samples": 20,
        "reg_alpha": 0.1,
        "reg_lambda": 0.1,
        "class_weight": "balanced",
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    })
    # 조기 종료
    early_stopping_rounds: int = 50
    # 교차검증 fold 수 (0 이면 단순 hold-out)
    cv_folds: int = 5
    # 시계열 CV 사용 여부
    time_series_cv: bool = True
    # 모델 저장 경로
    model_save_path: str = "artifacts/lgbm_model.pkl"
    # 피처 중요도 저장 경로
    feature_importance_path: str = "artifacts/feature_importance.csv"


# ─────────────────────────────────────────
# 임계값 탐색 설정
# ─────────────────────────────────────────
@dataclass
class ThresholdConfig:
    # 탐색 범위
    search_range_start: float = 0.3
    search_range_end: float = 0.9
    search_steps: int = 60
    # 최적화 기준: "f1" | "precision" | "recall" | "profit_factor"
    optimize_metric: str = "f1"
    # 최소 신호 수 (너무 적으면 통계적 의미 없음)
    min_signal_count: int = 30


# ─────────────────────────────────────────
# 백테스트 설정
# ─────────────────────────────────────────
@dataclass
class BacktestConfig:
    # 초기 자산
    initial_capital: float = 1_000_000.0
    # 수수료 + 슬리피지 (편도, 소수점)
    commission: float = 0.0005
    # 1회 진입 비율 (총 자산 대비)
    position_size_pct: float = 0.1
    # 최대 동시 포지션 수
    max_positions: int = 1
    # 손절 비율 (None = 미사용)
    stop_loss_pct: Optional[float] = 0.005
    # 이익실현 비율 (None = forward_bars 후 청산)
    take_profit_pct: Optional[float] = 0.01
    # 결과 저장 경로
    result_path: str = "artifacts/backtest_result.csv"


# ─────────────────────────────────────────
# 전역 설정 통합 객체
# ─────────────────────────────────────────
@dataclass
class ProjectConfig:
    data: DataConfig = field(default_factory=DataConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    feature: FeatureConfig = field(default_factory=FeatureConfig)
    label: LabelConfig = field(default_factory=LabelConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    threshold: ThresholdConfig = field(default_factory=ThresholdConfig)
    backtest: BacktestConfig = field(default_factory=BacktestConfig)
    # 로그 레벨: DEBUG | INFO | WARNING
    log_level: str = "INFO"
    # 결과 산출물 디렉토리
    artifacts_dir: str = "artifacts"
    # 재현성 시드
    random_seed: int = 42


# 기본 설정 인스턴스 (다른 모듈에서 import해서 사용)
CFG = ProjectConfig()
