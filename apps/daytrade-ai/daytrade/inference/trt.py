"""M4 — AI-Inference 엔진 스캐폴드(설계서 §3-3): TensorRT/ONNX Runtime, 모델 핫스왑, 레이턴시 계측.

설계서 §3-3 의 C++ 추론 스레드(TensorRT enqueueV2 async, ≤1ms)에 대응하는 **파이썬 측 결선**.
GPU/TensorRT 가 있는 서버(RTX 5090)에서는 TensorRT 엔진으로, 없으면 ONNX Runtime(CUDA→CPU)으로,
그것도 없으면 휴리스틱으로 **graceful fallback** 한다(서비스 가용성 우선 — 프로젝트 공통 원칙).

구성:
  - `LatencyHistogram`     : 추론 레이턴시 p50/p95/p99 집계·export(§3-3 "추론 레이턴시 히스토그램").
  - `MeasuredModel`        : 임의 `InferenceModel` 을 감싸 predict 레이턴시를 계측(데코레이터).
  - `HotSwapModel`         : Blue-Green 무중단 모델 교체(stage→activate, 스레드 안전).
  - `TensorRTModel`        : TensorRT 엔진 추론 어댑터(서버 전용, guarded import).
  - `build_engine`         : ONNX → TensorRT 엔진(.plan) 빌드(FP32/FP16/INT8). 서버 전용.
  - `load_inference_model` : TensorRT → ORT(CUDA) → ORT(CPU) → Heuristic 폴백 팩토리.

C++ 헤더 스캐폴드는 `cpp/include/daytrade/inference_engine.hpp` 참고(M3 패턴 — 서버 빌드).
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from ..features.engine import FeatureVector
from .model import HeuristicModel, InferenceModel, load_model


@dataclass
class LatencyHistogram:
    """추론 레이턴시 집계(마이크로초). 가벼운 리스트 누적 후 분위수 산출.

    운영에서는 고정 버킷 HDR-histogram 으로 교체 가능하나, 스캘핑 추론 호출량에선 충분.
    """

    _samples_us: list[float] = field(default_factory=list)
    max_samples: int = 100_000

    def record_ns(self, dt_ns: int) -> None:
        if len(self._samples_us) < self.max_samples:
            self._samples_us.append(dt_ns / 1_000.0)

    def reset(self) -> None:
        self._samples_us.clear()

    def summary(self) -> dict:
        n = len(self._samples_us)
        if n == 0:
            return {"count": 0, "p50_us": 0.0, "p95_us": 0.0, "p99_us": 0.0, "max_us": 0.0, "mean_us": 0.0}
        s = sorted(self._samples_us)

        def pct(p: float) -> float:
            idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
            return round(s[idx], 3)

        return {
            "count": n,
            "p50_us": pct(50),
            "p95_us": pct(95),
            "p99_us": pct(99),
            "max_us": round(s[-1], 3),
            "mean_us": round(sum(s) / n, 3),
        }


class MeasuredModel(InferenceModel):
    """임의 모델을 감싸 predict 레이턴시를 `LatencyHistogram` 에 기록."""

    def __init__(self, inner: InferenceModel, histogram: LatencyHistogram | None = None) -> None:
        self.inner = inner
        self.histogram = histogram or LatencyHistogram()

    def warmup(self) -> None:
        self.inner.warmup()

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        t0 = time.perf_counter_ns()
        out = self.inner.predict(fv)
        self.histogram.record_ns(time.perf_counter_ns() - t0)
        return out


class HotSwapModel(InferenceModel):
    """Blue-Green 무중단 모델 핫스왑(설계서 §3-3 "모델 핫스왑(Blue-Green)").

    추론 트래픽은 항상 `active` 모델을 사용한다. 새 모델은 `stage()` 로 준비(warmup 포함)한 뒤
    `activate()` 로 원자적 교체 → 진행 중 추론에 끊김 없음. `swap()` 은 stage+activate 단축형.
    """

    def __init__(self, active: InferenceModel) -> None:
        self._active = active
        self._staged: InferenceModel | None = None
        self._lock = threading.Lock()
        self.generation = 0

    @property
    def active(self) -> InferenceModel:
        return self._active

    def warmup(self) -> None:
        self._active.warmup()

    def predict(self, fv: FeatureVector) -> tuple[float, float]:
        # 참조 읽기는 원자적(GIL) — 락 없이 현재 active 로 추론.
        return self._active.predict(fv)

    def stage(self, model: InferenceModel) -> None:
        """후보 모델을 준비(워밍업)해 대기열에 올린다. 트래픽엔 영향 없음."""
        model.warmup()
        with self._lock:
            self._staged = model

    def activate(self) -> InferenceModel | None:
        """stage 된 모델을 active 로 승격. 반환: 직전 active(롤백/정리용)."""
        with self._lock:
            if self._staged is None:
                return None
            old, self._active, self._staged = self._active, self._staged, None
            self.generation += 1
            return old

    def swap(self, model: InferenceModel) -> InferenceModel:
        """stage + activate 단축형. 반환: 직전 active."""
        self.stage(model)
        return self.activate()  # type: ignore[return-value]


def build_engine(
    onnx_path: str,
    engine_path: str,
    *,
    precision: str = "fp16",
    max_workspace_mb: int = 4096,
    calibrator=None,
):
    """ONNX → TensorRT 직렬화 엔진(.plan) 빌드. **TensorRT 설치 서버 전용**.

    Args:
        precision: "fp32" | "fp16" | "int8"(calibrator 필요).
        calibrator: INT8 보정기(trt.IInt8Calibrator). int8 일 때 필수.
    Raises:
        ModuleNotFoundError: tensorrt 미설치(개발 PC).
        ValueError: int8 인데 calibrator 미제공 / ONNX 파싱 실패.
    """
    try:
        import tensorrt as trt  # type: ignore  # pyright: ignore[reportMissingImports]
    except ModuleNotFoundError as exc:  # pragma: no cover - GPU 서버 전용
        raise ModuleNotFoundError(
            "TensorRT 엔진 빌드에는 'tensorrt' 패키지(+CUDA)가 필요합니다 — RTX 5090 서버에서 실행하세요. "
            "개발 PC 에서는 load_inference_model() 이 ONNX Runtime/휴리스틱으로 폴백합니다."
        ) from exc

    logger = trt.Logger(trt.Logger.WARNING)
    builder = trt.Builder(logger)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)
    with open(onnx_path, "rb") as f:
        if not parser.parse(f.read()):
            errs = "; ".join(str(parser.get_error(i)) for i in range(parser.num_errors))
            raise ValueError(f"ONNX 파싱 실패: {errs}")

    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, max_workspace_mb * (1 << 20))
    precision = precision.lower()
    if precision == "fp16":
        config.set_flag(trt.BuilderFlag.FP16)
    elif precision == "int8":
        if calibrator is None:
            raise ValueError("int8 정밀도에는 calibrator(trt.IInt8Calibrator) 가 필요합니다.")
        config.set_flag(trt.BuilderFlag.INT8)
        config.int8_calibrator = calibrator

    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
        raise ValueError("TensorRT 엔진 빌드 실패(build_serialized_network → None).")
    with open(engine_path, "wb") as f:
        f.write(serialized)
    return engine_path


class TensorRTModel(InferenceModel):
    """TensorRT 엔진 추론 어댑터(설계서 §3-3). **GPU/TensorRT 서버 전용**.

    입력: FEATURE_NAMES 순서 float32 [1, N]. 출력: [1,2]=[prob_buy, prob_sell].
    개발 PC 에서는 인스턴스화 시 ModuleNotFoundError → `load_inference_model` 이 폴백 처리.
    """

    def __init__(self, engine_path: str, *, input_name: str | None = None) -> None:  # pragma: no cover - GPU 전용
        import numpy as np  # pyright: ignore[reportMissingImports]
        import tensorrt as trt  # type: ignore  # pyright: ignore[reportMissingImports]

        try:
            import pycuda.autoinit  # noqa: F401  # type: ignore  # pyright: ignore[reportMissingImports]
            import pycuda.driver as cuda  # type: ignore  # pyright: ignore[reportMissingImports]
        except ModuleNotFoundError as exc:
            raise ModuleNotFoundError(
                "TensorRT 추론에는 'pycuda'(또는 cuda-python) 가 필요합니다 — 서버에서 설치."
            ) from exc

        self._np = np
        self._cuda = cuda
        logger = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f, trt.Runtime(logger) as runtime:
            self._engine = runtime.deserialize_cuda_engine(f.read())
        self._context = self._engine.create_execution_context()
        self._input_name = input_name or self._engine.get_tensor_name(0)
        self.histogram = LatencyHistogram()

    def warmup(self) -> None:  # pragma: no cover - GPU 전용
        dummy = self._np.zeros((1, 8), dtype=self._np.float32)
        self._infer(dummy)

    def _infer(self, inp):  # pragma: no cover - GPU 전용
        # 최소 동기 추론(스캐폴드). 운영 C++ 경로는 enqueueV2 + stream 비동기(§3-3).
        cuda = self._cuda
        np = self._np
        out = np.empty((1, 2), dtype=np.float32)
        d_in = cuda.mem_alloc(inp.nbytes)
        d_out = cuda.mem_alloc(out.nbytes)
        cuda.memcpy_htod(d_in, inp)
        self._context.execute_v2([int(d_in), int(d_out)])
        cuda.memcpy_dtoh(out, d_out)
        return out

    def predict(self, fv: FeatureVector) -> tuple[float, float]:  # pragma: no cover - GPU 전용
        inp = self._np.asarray([fv.as_array()], dtype=self._np.float32)
        t0 = time.perf_counter_ns()
        out = self._infer(inp)
        self.histogram.record_ns(time.perf_counter_ns() - t0)
        return float(out[0][0]), float(out[0][1])


def load_inference_model(
    model_path: str | None = None,
    *,
    engine_path: str | None = None,
    prefer_tensorrt: bool = True,
    measure: bool = False,
    hot_swappable: bool = False,
) -> InferenceModel:
    """추론 모델 팩토리 — TensorRT → ONNX Runtime → 휴리스틱 graceful fallback.

    Args:
        model_path: ONNX/JSON 모델(ORT/numpy 경로). None 이면 휴리스틱.
        engine_path: TensorRT 직렬화 엔진(.plan). 있으면 우선 시도.
        prefer_tensorrt: True 면 engine_path 의 TensorRT 를 먼저 시도(서버).
        measure: True 면 `MeasuredModel` 로 감싸 레이턴시 계측.
        hot_swappable: True 면 `HotSwapModel` 로 감싸 무중단 교체 지원.
    """
    model: InferenceModel | None = None
    if prefer_tensorrt and engine_path:
        try:
            model = TensorRTModel(engine_path)
        except Exception:
            model = None  # 미설치/로드 실패 → 다음 폴백
    if model is None:
        # load_model 이 .onnx(ORT, CUDA EP 자동) / .json(numpy) / 정책ONNX 디스패치 + 휴리스틱 폴백.
        model = load_model(model_path) if model_path else HeuristicModel()

    if measure:
        model = MeasuredModel(model)
    if hot_swappable:
        model = HotSwapModel(model)
    return model
