"""M2 — AI 학습 파이프라인.

라벨링 → 피처 데이터셋 → 학습(순수 numpy 로지스틱 기본 / torch LSTM·Transformer 선택)
→ ONNX export → 런타임 추론 모델(OnnxModel / SequenceOnnxModel / NumpyLogRegModel) 연결.

설계 원칙:
- **런타임 정합**: 학습 피처는 반드시 `FeatureEngine` 로 생성(FEATURE_NAMES 순서 고정) →
  추론 시 동일 피처가 들어가도록 보장(train/serve skew 제거).
- **look-ahead 차단**: 시점 t 의 피처로 t+h 미래수익을 예측. 미래가 없는 마지막 h행은 제거.
- **표준화 내장**: 학습 시 산출한 mean/std 를 추론·ONNX 그래프에 함께 실어, 원시 피처가
  그대로 들어와도 동일 결과(스케일 차이가 큰 OBI/VWAP/mid_price 안정화).
- **의존성 계층**: numpy 경로는 항상 동작(테스트 보장). onnx/onnxruntime/torch 는 선택.
"""
from .labeling import make_labels
from .dataset import (
    DatasetBundle,
    build_feature_matrix,
    build_dataset,
    make_sequences,
    train_val_split,
)
from .logreg import NumpyLogReg, train_logreg
from .walkforward import (
    WFSplit,
    WalkForwardReport,
    walk_forward_backtest,
    walk_forward_splits,
    walk_forward_validate,
)
from .tuning import (
    ParamSpec,
    RiskConstraints,
    TuningResult,
    default_search_space,
    run_tuning,
    score_summary,
)
from .kpi import (
    KpiRegressionReport,
    RegimeResult,
    compare_regime,
    compare_regimes,
)

__all__ = [
    "make_labels",
    "DatasetBundle",
    "build_feature_matrix",
    "build_dataset",
    "make_sequences",
    "train_val_split",
    "NumpyLogReg",
    "train_logreg",
    "WFSplit",
    "WalkForwardReport",
    "walk_forward_splits",
    "walk_forward_validate",
    "walk_forward_backtest",
    "ParamSpec",
    "RiskConstraints",
    "TuningResult",
    "default_search_space",
    "run_tuning",
    "score_summary",
    "KpiRegressionReport",
    "RegimeResult",
    "compare_regime",
    "compare_regimes",
]
