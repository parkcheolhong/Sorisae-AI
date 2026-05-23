from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import torch
from PIL import Image

_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class FaceRecognitionAdapter(ABC):
    adapter_name = "face-recognition-adapter"

    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def status(self) -> Dict[str, object]:
        raise NotImplementedError

    @abstractmethod
    def embed(self, image_path: Path) -> torch.Tensor:
        raise NotImplementedError


class ArcFaceInsightAdapter(FaceRecognitionAdapter):
    adapter_name = "arcface-insightface"

    def __init__(self) -> None:
        self.device = _DEVICE
        self._model = None
        self._error = ""
        try:
            import insightface  # type: ignore

            provider = "CUDAExecutionProvider" if self.device == "cuda" else "CPUExecutionProvider"
            app = insightface.app.FaceAnalysis(providers=[provider])
            ctx_id = 0 if self.device == "cuda" else -1
            app.prepare(ctx_id=ctx_id, det_size=(640, 640))
            self._model = app
        except Exception as exc:  # pragma: no cover - optional runtime dependency
            self._error = str(exc)

    def is_available(self) -> bool:
        return self._model is not None

    def status(self) -> Dict[str, object]:
        return {
            "adapter_name": self.adapter_name,
            "available": self.is_available(),
            "device": self.device,
            "reason": self._error or None,
            "embedding_backend": "insightface-arcface" if self.is_available() else None,
        }

    def embed(self, image_path: Path) -> torch.Tensor:
        if not self._model:
            raise RuntimeError(self._error or "ArcFace adapter unavailable")
        image = np.array(Image.open(image_path).convert("RGB"))
        faces = self._model.get(image)
        if not faces:
            raise RuntimeError(f"no face detected in {image_path}")
        embedding = torch.tensor(faces[0].embedding, dtype=torch.float32)
        return torch.nn.functional.normalize(embedding.unsqueeze(0), dim=1).to(self.device)


class FaceNetArcFaceCompatibleAdapter(FaceRecognitionAdapter):
    adapter_name = "facenet-arcface-compatible"

    def __init__(self) -> None:
        self.device = _DEVICE
        self._model = None
        self._error = ""
        try:
            from facenet_pytorch import InceptionResnetV1  # type: ignore

            self._model = InceptionResnetV1(pretrained="vggface2").eval().to(self.device)
        except Exception as exc:  # pragma: no cover - optional runtime dependency
            self._error = str(exc)

    def is_available(self) -> bool:
        return self._model is not None

    def status(self) -> Dict[str, object]:
        return {
            "adapter_name": self.adapter_name,
            "available": self.is_available(),
            "device": self.device,
            "reason": self._error or None,
            "embedding_backend": "facenet-inceptionresnet-v1" if self.is_available() else None,
        }

    def embed(self, image_path: Path) -> torch.Tensor:
        if not self._model:
            raise RuntimeError(self._error or "FaceNet adapter unavailable")
        image = Image.open(image_path).convert("RGB").resize((160, 160), Image.Resampling.BILINEAR)
        tensor = torch.from_numpy(np.array(image)).float() / 255.0
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        tensor = (tensor - 0.5) / 0.5
        tensor = tensor.to(self.device)
        with torch.inference_mode():
            embedding = self._model(tensor)
        return torch.nn.functional.normalize(embedding, dim=1)


class TorchvisionFaceFallbackAdapter(FaceRecognitionAdapter):
    adapter_name = "torchvision-face-fallback"

    def __init__(self) -> None:
        self.device = _DEVICE
        self._model = None
        self._preprocess = None
        self._error = ""
        try:
            from torchvision import models as tv_models  # type: ignore # lazy
            self._weights = tv_models.ResNet18_Weights.DEFAULT
            self._model = tv_models.resnet18(weights=self._weights)
            self._model.fc = torch.nn.Identity()
            self._model = self._model.to(self.device).eval()
            self._preprocess = self._weights.transforms()
        except Exception as exc:
            self._error = str(exc)

    def is_available(self) -> bool:
        return self._model is not None

    def status(self) -> Dict[str, object]:
        return {
            "adapter_name": self.adapter_name,
            "available": self._model is not None,
            "device": self.device,
            "reason": self._error or None,
            "embedding_backend": "torchvision-resnet18-fallback",
        }

    def embed(self, image_path: Path) -> torch.Tensor:
        if self._model is None or self._preprocess is None:
            raise RuntimeError(self._error or "TorchvisionFaceFallbackAdapter unavailable")
        image = Image.open(image_path).convert("RGB")
        tensor = self._preprocess(image).unsqueeze(0).to(self.device)
        with torch.inference_mode():
            embedding = self._model(tensor)
        return torch.nn.functional.normalize(embedding, dim=1)


def build_face_recognition_adapter() -> Tuple[FaceRecognitionAdapter, Dict[str, object]]:
    primary = ArcFaceInsightAdapter()
    if primary.is_available():
        return primary, {
            "adapter_mode": "primary",
            **primary.status(),
        }
    secondary = FaceNetArcFaceCompatibleAdapter()
    if secondary.is_available():
        return secondary, {
            "adapter_mode": "secondary",
            "fallback_from": primary.adapter_name,
            "fallback_reason": primary.status().get("reason"),
            **secondary.status(),
        }
    fallback = TorchvisionFaceFallbackAdapter()
    return fallback, {
        "adapter_mode": "fallback",
        "fallback_from": secondary.adapter_name,
        "fallback_reason": secondary.status().get("reason") or primary.status().get("reason"),
        **fallback.status(),
    }
