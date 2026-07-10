"""ONNX export — 학습 산출물을 런타임 추론 그래프로 변환.

- `export_numpy_logreg_to_onnx`: 표준화+로지스틱을 onnx.helper 로 직접 구성.
  그래프: probs = Sigmoid(((x - mean)/std) @ W + b). 입력 [N, F] → 출력 [N, 2].
  생산 아티팩트는 `OnnxModel`(단일 벡터 [1,F]) 로 그대로 로드된다.
- `export_torch_sequence_to_onnx`: torch 시퀀스 모델을 torch.onnx 로 export(torch 경로).

onnx 미설치 시 명확한 안내 예외를 던진다(numpy JSON 경로는 영향 없음).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .logreg import NumpyLogReg

OPSET = 13
# 일부 onnxruntime 빌드는 최신 onnx 의 IR 버전을 아직 지원하지 않으므로 보수적으로 고정.
IR_VERSION = 10


def export_numpy_logreg_to_onnx(
    model: NumpyLogReg,
    path: str | Path,
    *,
    input_name: str = "features",
    output_name: str = "probs",
) -> str:
    try:
        import onnx
        from onnx import TensorProto, helper, numpy_helper
    except ModuleNotFoundError as exc:  # pragma: no cover - 환경 의존
        raise ModuleNotFoundError(
            "ONNX export 에는 'onnx' 패키지가 필요합니다: pip install onnx"
        ) from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    f = model.n_features

    mean = numpy_helper.from_array(model.mean.astype(np.float32), name="mean")
    std = numpy_helper.from_array(model.std.astype(np.float32), name="std")
    w = numpy_helper.from_array(model.W.astype(np.float32), name="W")
    b = numpy_helper.from_array(model.b.astype(np.float32), name="b")

    nodes = [
        helper.make_node("Sub", [input_name, "mean"], ["centered"]),
        helper.make_node("Div", ["centered", "std"], ["scaled"]),
        helper.make_node("MatMul", ["scaled", "W"], ["logits_mm"]),
        helper.make_node("Add", ["logits_mm", "b"], ["logits"]),
        helper.make_node("Sigmoid", ["logits"], [output_name]),
    ]

    inp = helper.make_tensor_value_info(input_name, TensorProto.FLOAT, ["N", f])
    out = helper.make_tensor_value_info(output_name, TensorProto.FLOAT, ["N", 2])

    graph = helper.make_graph(
        nodes, "numpy_logreg", [inp], [out], initializer=[mean, std, w, b]
    )
    model_proto = helper.make_model(
        graph,
        opset_imports=[helper.make_operatorsetid("", OPSET)],
        producer_name="daytrade-ai",
    )
    model_proto.ir_version = IR_VERSION
    model_proto.doc_string = (
        "daytrade-ai numpy logreg: Sigmoid(((x-mean)/std) @ W + b). "
        f"feature_names={list(model.feature_names)} horizon={model.horizon}"
    )
    onnx.checker.check_model(model_proto)
    onnx.save(model_proto, str(path))
    return str(path)


def export_continuous_policy_to_onnx(
    W,
    b: float,
    feat_mean,
    feat_std,
    path: str | Path,
    *,
    input_name: str = "obs",
    output_name: str = "position",
) -> str:
    """연속 RL 정책(`ContinuousPPOAgent`)을 ONNX 로 export.

    그래프: position = Tanh( ((obs - mean9)/std9) @ W + b ).
      - obs = [raw 8 features, position] (shape [N, 9]).
      - 표준화를 그래프에 내장: mean9=[feat_mean..., 0], std9=[feat_std..., 1] →
        피처 8개만 표준화하고 마지막 position 슬롯은 그대로 통과(학습 obs 와 동일).
      - W: shape (9,) → MatMul 위해 (9,1) 로 reshape. 출력 [N,1] → Tanh.
    `OnnxPolicyModel` 이 그대로 로드해 추론(M4 추론 엔진 인터페이스 연결).
    """
    try:
        import onnx
        from onnx import TensorProto, helper, numpy_helper
    except ModuleNotFoundError as exc:  # pragma: no cover - 환경 의존
        raise ModuleNotFoundError(
            "ONNX export 에는 'onnx' 패키지가 필요합니다: pip install onnx"
        ) from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    W = np.asarray(W, dtype=np.float32).reshape(-1)
    feat_mean = np.asarray(feat_mean, dtype=np.float32).reshape(-1)
    feat_std = np.asarray(feat_std, dtype=np.float32).reshape(-1)
    obs_dim = W.shape[0]
    f = obs_dim - 1
    if feat_mean.shape[0] != f or feat_std.shape[0] != f:
        raise ValueError(
            f"feat_mean/std 길이({feat_mean.shape[0]}/{feat_std.shape[0]})는 obs_dim-1({f}) 여야 합니다."
        )

    mean9 = np.concatenate([feat_mean, np.zeros(1, dtype=np.float32)])
    std9 = np.concatenate([feat_std, np.ones(1, dtype=np.float32)])

    mean_init = numpy_helper.from_array(mean9, name="mean9")
    std_init = numpy_helper.from_array(std9, name="std9")
    w_init = numpy_helper.from_array(W.reshape(obs_dim, 1), name="W")
    b_init = numpy_helper.from_array(np.array([[b]], dtype=np.float32), name="b")

    nodes = [
        helper.make_node("Sub", [input_name, "mean9"], ["centered"]),
        helper.make_node("Div", ["centered", "std9"], ["scaled"]),
        helper.make_node("MatMul", ["scaled", "W"], ["proj"]),
        helper.make_node("Add", ["proj", "b"], ["pre"]),
        helper.make_node("Tanh", ["pre"], [output_name]),
    ]
    inp = helper.make_tensor_value_info(input_name, TensorProto.FLOAT, ["N", obs_dim])
    out = helper.make_tensor_value_info(output_name, TensorProto.FLOAT, ["N", 1])
    graph = helper.make_graph(
        nodes, "continuous_policy", [inp], [out],
        initializer=[mean_init, std_init, w_init, b_init],
    )
    model_proto = helper.make_model(
        graph,
        opset_imports=[helper.make_operatorsetid("", OPSET)],
        producer_name="daytrade-ai",
    )
    model_proto.ir_version = IR_VERSION
    model_proto.doc_string = (
        "daytrade-ai continuous RL policy: Tanh(((obs-mean9)/std9) @ W + b). "
        f"obs_dim={obs_dim} (last slot = current position)"
    )
    onnx.checker.check_model(model_proto)
    onnx.save(model_proto, str(path))
    return str(path)


def export_torch_sequence_to_onnx(
    module,
    path: str | Path,
    *,
    seq_len: int,
    n_features: int,
    input_name: str = "features",
    output_name: str = "probs",
) -> str:
    """torch 시퀀스 모델(forward: [B, seq_len, F] → [B, 2] 확률)을 ONNX 로 export."""
    import torch  # pyright: ignore[reportMissingImports]

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    module.eval()
    dummy = torch.zeros(1, seq_len, n_features, dtype=torch.float32)
    torch.onnx.export(
        module,
        dummy,
        str(path),
        input_names=[input_name],
        output_names=[output_name],
        dynamic_axes={input_name: {0: "batch"}, output_name: {0: "batch"}},
        opset_version=OPSET,
    )
    _clamp_ir_version(path)
    return str(path)


def _clamp_ir_version(path: str | Path) -> None:
    """export 산출물의 IR 버전이 런타임 한계를 넘으면 낮춰 재저장(호환성)."""
    try:
        import onnx

        m = onnx.load(str(path))
        if m.ir_version > IR_VERSION:
            m.ir_version = IR_VERSION
            onnx.save(m, str(path))
    except ModuleNotFoundError:  # pragma: no cover
        pass
