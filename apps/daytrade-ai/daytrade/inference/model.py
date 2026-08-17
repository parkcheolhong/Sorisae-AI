"""추론 모델 — 인터페이스 + 기본(휴리스틱) + ONNX 어댑터(선택)."""
from __future__ import annotations

import abc
import math

from ..features.engine import FeatureVector


class InferenceModel(abc.ABC):
    """피처 벡터 → (prob_buy, prob_sell). 두 확률은 독립적이며 각각 [0,1]."""

    @abc.abstractmethod
    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        raise NotImplementedError

    # 워밍업(cold-start 지연 제거). 기본은 no-op.
    def warmup(self) -> None:  # pragma: no cover - trivial
        return None


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


class HeuristicModel(InferenceModel):
    """의존성 없는 기본 모델.

    정규화 OBI(z-score), 모멘텀 부호, 볼륨 급증을 로지스틱으로 합성해 방향 확률을 만든다.
    실제 학습 모델(ONNX)이 준비되기 전의 안전한 기본값이며, 단독으로도 동작 가능하다.
    """

    def __init__(self, obi_weight: float = 1.2, mom_weight: float = 8.0, vol_weight: float = 0.6) -> None:
        self.obi_weight = obi_weight
        self.mom_weight = mom_weight
        self.vol_weight = vol_weight

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        vol_excess = max(0.0, fv.volume_spike - 1.0)
        # 방향 점수: 양수면 매수 쪽, 음수면 매도 쪽.
        score = (
            self.obi_weight * fv.obi_norm
            + self.mom_weight * _sign(fv.micro_momentum) * min(abs(fv.micro_momentum), 1.0)
        )
        # 볼륨 급증은 '확신 폭'을 키운다(방향과 무관한 게인).
        gain = 1.0 + self.vol_weight * vol_excess
        prob_buy = _sigmoid(score * gain)
        prob_sell = _sigmoid(-score * gain)
        return prob_buy, prob_sell


def _sign(x: float) -> float:
    return 1.0 if x > 0 else (-1.0 if x < 0 else 0.0)


class OnnxModel(InferenceModel):
    """ONNX 사전학습 모델 어댑터(선택). onnxruntime 필요.

    입력: FEATURE_NAMES 순서의 float32 벡터 (shape [1, N]).
    출력: shape [1,2] = [prob_buy, prob_sell].
    """

    def __init__(self, model_path: str, input_name: str | None = None) -> None:
        import onnxruntime as ort  # 지연 임포트(미설치 환경 보호)  # pyright: ignore[reportMissingImports]

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        available = ort.get_available_providers()
        providers = [p for p in providers if p in available] or ["CPUExecutionProvider"]
        self._sess = ort.InferenceSession(model_path, providers=providers)
        self._input_name = input_name or self._sess.get_inputs()[0].name

    def warmup(self) -> None:
        import numpy as np  # pyright: ignore[reportMissingImports]

        dummy = np.zeros((1, 8), dtype=np.float32)
        self._sess.run(None, {self._input_name: dummy})

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        import numpy as np  # pyright: ignore[reportMissingImports]

        inp = np.asarray([fv.as_array()], dtype=np.float32)
        out = self._sess.run(None, {self._input_name: inp})[0]
        prob_buy = float(out[0][0])
        prob_sell = float(out[0][1])
        return prob_buy, prob_sell


class NumpyLogRegModel(InferenceModel):
    """순수 numpy 학습 모델(`NumpyLogReg`) 어댑터 — onnxruntime 없이 동작.

    `model.json`(표준화 내장 2-head 로지스틱)을 로드해 단일 피처벡터로 (prob_buy, prob_sell) 추론.
    학습 피처 순서(feature_names)가 런타임 FEATURE_NAMES 와 다르면 즉시 오류(skew 방지).
    """

    def __init__(self, model_path: str | None = None, *, model=None) -> None:
        from ..features.engine import FEATURE_NAMES
        from ..training.logreg import NumpyLogReg

        if model is not None:
            self._m = model
        elif model_path is not None:
            self._m = NumpyLogReg.load_json(model_path)
        else:
            raise ValueError("model_path 또는 model 중 하나는 필요합니다.")
        if tuple(self._m.feature_names) != tuple(FEATURE_NAMES):
            raise ValueError(
                f"feature order mismatch: model={self._m.feature_names} runtime={FEATURE_NAMES}"
            )

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        proba = self._m.predict_proba([fv.as_array()])[0]
        return float(proba[0]), float(proba[1])


class SequenceOnnxModel(InferenceModel):
    """시퀀스 ONNX 모델(LSTM/Transformer) 어댑터 — 내부에 길이 seq_len 피처 윈도를 유지.

    입력: [1, seq_len, N] float32 (표준화는 그래프에 내장). 출력: [1, 2]=[prob_buy, prob_sell].
    윈도가 채워지기 전(워밍업 구간)에는 0 패딩으로 추론한다.
    """

    def __init__(self, model_path: str, seq_len: int, n_features: int, input_name: str | None = None) -> None:
        import collections

        import numpy as np  # pyright: ignore[reportMissingImports]
        import onnxruntime as ort  # pyright: ignore[reportMissingImports]

        self._np = np
        self.seq_len = int(seq_len)
        self.n_features = int(n_features)
        available = ort.get_available_providers()
        providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
        self._sess = ort.InferenceSession(model_path, providers=providers or ["CPUExecutionProvider"])
        self._input_name = input_name or self._sess.get_inputs()[0].name
        self._buf: "collections.deque" = collections.deque(maxlen=self.seq_len)

    def warmup(self) -> None:
        dummy = self._np.zeros((1, self.seq_len, self.n_features), dtype=self._np.float32)
        self._sess.run(None, {self._input_name: dummy})

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        np = self._np
        self._buf.append(np.asarray(fv.as_array(), dtype=np.float32))
        window = list(self._buf)
        if len(window) < self.seq_len:
            pad = [np.zeros(self.n_features, dtype=np.float32)] * (self.seq_len - len(window))
            window = pad + window
        inp = np.asarray([window], dtype=np.float32)  # [1, seq_len, F]
        out = self._sess.run(None, {self._input_name: inp})[0]
        return float(out[0][0]), float(out[0][1])


class OnnxPolicyModel(InferenceModel):
    """연속 RL 정책 ONNX 어댑터 — RL 정책을 M4 추론 인터페이스로 연결(stateful).

    `export_continuous_policy_to_onnx` 산출물(입력 [1, F+1]=[features, position],
    출력 [1,1]=목표 포지션 ∈[-1,1])을 로드한다. 정책은 현재 포지션에 의존하므로 내부에
    포지션 상태를 유지하며(서빙 시 self-consistent), 목표 포지션을 (prob_buy, prob_sell) 로 사상한다:
        prob_buy = max(position, 0), prob_sell = max(-position, 0).
    파이프라인/디텍션의 AI 임계 로직이 기존과 동일하게 이 확률을 소비한다.
    """

    def __init__(self, model_path: str, input_name: str | None = None) -> None:
        import numpy as np  # pyright: ignore[reportMissingImports]
        import onnxruntime as ort  # pyright: ignore[reportMissingImports]

        self._np = np
        available = ort.get_available_providers()
        providers = [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available]
        self._sess = ort.InferenceSession(model_path, providers=providers or ["CPUExecutionProvider"])
        self._input_name = input_name or self._sess.get_inputs()[0].name
        self._position = 0.0

    def reset(self) -> None:
        self._position = 0.0

    def warmup(self) -> None:
        import numpy as np  # pyright: ignore[reportMissingImports]

        dummy = np.zeros((1, 9), dtype=np.float32)
        self._sess.run(None, {self._input_name: dummy})

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        np = self._np
        obs = np.asarray([list(fv.as_array()) + [self._position]], dtype=np.float32)
        out = self._sess.run(None, {self._input_name: obs})[0]
        target = float(out[0][0])
        self._position = target
        return max(target, 0.0), max(-target, 0.0)


def _onnx_output_dim(model_path: str) -> int | None:
    """ONNX 첫 출력의 마지막 차원(구체 정수)을 반환 — 정책(1) vs 확률(2) 판별용."""
    import onnxruntime as ort  # pyright: ignore[reportMissingImports]

    sess = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
    shape = sess.get_outputs()[0].shape
    if not shape:
        return None
    last = shape[-1]
    return int(last) if isinstance(last, int) else None


def load_model(model_path: str | None = None) -> InferenceModel:
    """모델 로더 — 확장자/그래프 출력으로 디스패치하며, 어떤 경우에도 동작하는 모델을 반환.

    - ``*.json`` → NumpyLogRegModel(의존성 없음)
    - ``*.onnx`` (출력 [N,1]) → OnnxPolicyModel(연속 RL 정책, stateful)
    - ``*.onnx`` (출력 [N,2]) → OnnxModel(단일 벡터 확률, onnxruntime 필요)
    - 그 외/실패 → HeuristicModel(안전 폴백, 서비스 가용성 우선)
    """
    if model_path:
        try:
            if model_path.endswith(".json"):
                return NumpyLogRegModel(model_path)
            # 연속 RL 정책 ONNX(출력 차원 1)는 stateful OnnxPolicyModel 로 로드.
            if _onnx_output_dim(model_path) == 1:
                return OnnxPolicyModel(model_path)
            return OnnxModel(model_path)
        except Exception:
            # 미설치/로드 실패/포맷 불일치 → 안전 폴백
            return HeuristicModel()
    return HeuristicModel()
