"""AI Inference — 피처 → (prob_buy, prob_sell) 추론(설계서 §3-3 대응).

플러거블 모델 인터페이스(``InferenceModel``)를 두고:
    - ``HeuristicModel``: 의존성 없는 기본 모델(로지스틱 합성). 항상 동작.
    - ``OnnxModel``: onnxruntime 설치 시 사전학습(LSTM/Transformer→ONNX) 모델 로드.
                     미설치/로드 실패 시 HeuristicModel 로 자동 폴백.
"""
from .model import (
    InferenceModel,
    HeuristicModel,
    OnnxModel,
    NumpyLogRegModel,
    SequenceOnnxModel,
    OnnxPolicyModel,
    load_model,
)
from .trt import (
    LatencyHistogram,
    MeasuredModel,
    HotSwapModel,
    TensorRTModel,
    build_engine,
    load_inference_model,
)

__all__ = [
    "InferenceModel",
    "HeuristicModel",
    "OnnxModel",
    "NumpyLogRegModel",
    "SequenceOnnxModel",
    "OnnxPolicyModel",
    "load_model",
    # M4 추론 엔진 스캐폴드
    "LatencyHistogram",
    "MeasuredModel",
    "HotSwapModel",
    "TensorRTModel",
    "build_engine",
    "load_inference_model",
]
