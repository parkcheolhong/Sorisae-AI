from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

import numpy as np
import torch
from PIL import Image
from torchvision import models
from torchvision.models.detection import (
    KeypointRCNN_ResNet50_FPN_Weights,
    keypointrcnn_resnet50_fpn,
)
from torchvision.models.optical_flow import Raft_Small_Weights, raft_small

from backend.movie_studio.quality.arcface_adapter import build_face_recognition_adapter


_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class DetectorModelUnavailable(RuntimeError):
    pass


class BaseDetectorRunner:
    detector_name = "base-detector"

    def __init__(self) -> None:
        self.device = _DEVICE
        self.model = None
        self.preprocess = None
        self.model_name = ""
        self.load_error = ""
        self.model_state = self._load_model_state()

    def _load_model_state(self) -> Dict[str, object]:
        return {
            "device": self.device,
            "available": torch.cuda.is_available() or self.device == "cpu",
            "model_source": "torchvision-pretrained",
        }

    def _build_model(self):
        raise NotImplementedError

    def _ensure_model(self) -> bool:
        if self.model is not None:
            return True
        if self.load_error:
            return False
        try:
            model, preprocess, model_name = self._build_model()
            self.model = model.to(self.device).eval()
            self.preprocess = preprocess
            self.model_name = model_name
            self.model_state.update(
                {
                    "loaded": True,
                    "model_name": model_name,
                }
            )
            return True
        except Exception as exc:
            self.load_error = str(exc)
            self.model_state.update(
                {
                    "loaded": False,
                    "error": self.load_error,
                }
            )
            return False

    def _existing_paths(self, paths: Iterable[str]) -> List[Path]:
        return [
            Path(value)
            for value in (str(item or "").strip() for item in paths)
            if value and Path(value).exists() and Path(value).is_file()
        ]

    def _load_tensor(self, path: Path) -> torch.Tensor:
        image = Image.open(path).convert("RGB")
        if callable(self.preprocess):
            processed = self.preprocess(image)
            tensor = processed.unsqueeze(0) if processed.ndim == 3 else processed
        else:
            tensor = torch.from_numpy(np.array(image)).float() / 255.0
            tensor = tensor.permute(2, 0, 1).unsqueeze(0)
        return tensor.to(self.device)

    def run(self, **_: object) -> Dict[str, object]:
        raise NotImplementedError


class FaceEmbeddingDetectorRunner(BaseDetectorRunner):
    detector_name = "face-consistency-detector-ml"

    def __init__(self) -> None:
        super().__init__()
        self.face_adapter, self.face_adapter_status = build_face_recognition_adapter()

    def _build_model(self):
        weights = models.ResNet18_Weights.DEFAULT
        model = models.resnet18(weights=weights)
        model.fc = torch.nn.Identity()
        return model, weights.transforms(), "resnet18-imagenet-face-embed-proxy"

    def run(self, reference_paths: List[str], frame_paths: List[str]) -> Dict[str, object]:
        references = self._existing_paths(reference_paths)
        frames = self._existing_paths(frame_paths)
        if not references or not frames:
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": "missing face references or frames",
                "device": self.device,
                "adapter": self.face_adapter_status,
            }
        if self.face_adapter.is_available():
            with torch.inference_mode():
                reference_tensor = self.face_adapter.embed(references[0])
                sample_frames = frames[: min(6, len(frames))]
                similarities = []
                for frame_path in sample_frames:
                    frame_tensor = self.face_adapter.embed(frame_path)
                    similarity = torch.nn.functional.cosine_similarity(reference_tensor, frame_tensor).mean().item()
                    similarities.append(max(0.0, similarity))
            score = max(0.0, min(100.0, (sum(similarities) / max(1, len(similarities))) * 100.0))
            return {
                "detector": self.detector_name,
                "available": True,
                "score": round(score, 2),
                "sample_count": len(sample_frames),
                "device": self.device,
                "model_name": self.face_adapter_status.get("embedding_backend") or self.model_name,
                "adapter": self.face_adapter_status,
            }
        if not self._ensure_model():
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": self.load_error or "model unavailable",
                "device": self.device,
                "model_source": "torchvision-pretrained",
                "adapter": self.face_adapter_status,
            }
        with torch.inference_mode():
            reference_tensor = torch.nn.functional.normalize(self.model(self._load_tensor(references[0])), dim=1)
            sample_frames = frames[: min(6, len(frames))]
            similarities = []
            for frame_path in sample_frames:
                frame_tensor = torch.nn.functional.normalize(self.model(self._load_tensor(frame_path)), dim=1)
                similarity = torch.nn.functional.cosine_similarity(reference_tensor, frame_tensor).mean().item()
                similarities.append(max(0.0, similarity))
        score = max(0.0, min(100.0, (sum(similarities) / max(1, len(similarities))) * 100.0))
        sample_frames = frames[: min(6, len(frames))]
        return {
            "detector": self.detector_name,
            "available": True,
            "score": round(score, 2),
            "sample_count": len(sample_frames),
            "device": self.device,
            "model_name": self.model_name,
            "adapter": self.face_adapter_status,
        }


class HandLandmarkDetectorRunner(BaseDetectorRunner):
    detector_name = "hand-anatomy-detector-ml"

    def _build_model(self):
        weights = KeypointRCNN_ResNet50_FPN_Weights.DEFAULT
        model = keypointrcnn_resnet50_fpn(weights=weights)
        return model, weights.transforms(), "keypointrcnn-resnet50-fpn-coco-hand-proxy"

    def _load_detection_tensor(self, path: Path) -> torch.Tensor:
        image = Image.open(path).convert("RGB")
        array = np.array(image).astype("float32") / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1)
        return tensor.to(self.device)

    def run(self, frame_paths: List[str]) -> Dict[str, object]:
        frames = self._existing_paths(frame_paths)
        if not self._ensure_model():
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": self.load_error or "model unavailable",
                "device": self.device,
                "model_source": "torchvision-pretrained",
            }
        if not frames:
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": "missing frames",
                "device": self.device,
            }
        sample_frames = frames[:: max(1, int(len(frames) / 6))][:6]
        scores = []
        with torch.inference_mode():
            for frame_path in sample_frames:
                predictions = self.model([self._load_detection_tensor(frame_path)])[0]
                scores_tensor = predictions.get("scores")
                keypoints = predictions.get("keypoints")
                if scores_tensor is None or len(scores_tensor) == 0 or keypoints is None or keypoints.shape[0] == 0:
                    scores.append(0.0)
                    continue
                top_score = float(scores_tensor[0].item())
                visible_ratio = min(1.0, float(keypoints[0][:, 2].gt(0.0).float().mean().item()))
                scores.append(min(1.0, top_score * visible_ratio))
        score = (sum(scores) / max(1, len(scores))) * 100.0
        return {
            "detector": self.detector_name,
            "available": True,
            "score": round(score, 2),
            "sample_count": len(sample_frames),
            "device": self.device,
            "model_name": self.model_name,
        }


class AnatomyPoseDetectorRunner(BaseDetectorRunner):
    detector_name = "body-ratio-detector-ml"

    def _build_model(self):
        weights = KeypointRCNN_ResNet50_FPN_Weights.DEFAULT
        model = keypointrcnn_resnet50_fpn(weights=weights)
        return model, weights.transforms(), "keypointrcnn-resnet50-fpn-coco-pose-proxy"

    def run(self, frame_paths: List[str]) -> Dict[str, object]:
        frames = self._existing_paths(frame_paths)
        if not self._ensure_model():
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": self.load_error or "model unavailable",
                "device": self.device,
                "model_source": "torchvision-pretrained",
            }
        if len(frames) < 2:
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": "not enough frames",
                "device": self.device,
            }
        sample_frames = frames[: min(6, len(frames))]
        with torch.inference_mode():
            keypoint_vectors = []
            confidences = []
            for path in sample_frames:
                predictions = self.model([HandLandmarkDetectorRunner._load_detection_tensor(self, path)])[0]
                scores_tensor = predictions.get("scores")
                keypoints = predictions.get("keypoints")
                if scores_tensor is None or len(scores_tensor) == 0 or keypoints is None or keypoints.shape[0] == 0:
                    keypoint_vectors.append(None)
                    confidences.append(0.0)
                    continue
                confidences.append(float(scores_tensor[0].item()))
                keypoint_vectors.append(keypoints[0][:, :2].reshape(-1))
            similarities = []
            for index in range(len(keypoint_vectors) - 1):
                first = keypoint_vectors[index]
                second = keypoint_vectors[index + 1]
                if first is None or second is None:
                    similarities.append(0.0)
                    continue
                similarities.append(torch.nn.functional.cosine_similarity(first.unsqueeze(0), second.unsqueeze(0)).mean().item())
        average_similarity = sum(similarities) / max(1, len(similarities))
        confidence_floor = (sum(confidences) / max(1, len(confidences))) if confidences else 0.0
        if confidence_floor < 0.2:
            score = 100.0
        else:
            score = max(0.0, min(100.0, average_similarity * 100.0))
        return {
            "detector": self.detector_name,
            "available": True,
            "score": round(score, 2),
            "sample_count": len(sample_frames),
            "device": self.device,
            "model_name": self.model_name,
            "confidence_floor": round(confidence_floor, 4),
        }


class FlickerFlowDetectorRunner(BaseDetectorRunner):
    detector_name = "temporal-flicker-detector-ml"

    def _build_model(self):
        weights = Raft_Small_Weights.DEFAULT
        model = raft_small(weights=weights, progress=False)
        return model, weights.transforms(), "raft-small-optical-flow-flicker"

    def _load_video_clip(self, frame_paths: List[Path]) -> torch.Tensor:
        frames = []
        for path in frame_paths:
            image = Image.open(path).convert("RGB").resize((112, 112), Image.Resampling.BILINEAR)
            array = np.array(image).astype("float32") / 255.0
            tensor = torch.from_numpy(array).permute(2, 0, 1)
            frames.append(tensor)
        clip = torch.stack(frames, dim=1).unsqueeze(0)
        mean = torch.tensor([0.43216, 0.394666, 0.37645], dtype=torch.float32).view(1, 3, 1, 1, 1)
        std = torch.tensor([0.22803, 0.22145, 0.216989], dtype=torch.float32).view(1, 3, 1, 1, 1)
        clip = (clip - mean) / std
        return clip.to(self.device)

    def _load_raft_tensor(self, path: Path) -> torch.Tensor:
        image = Image.open(path).convert("RGB")
        width = max(8, (image.width // 8) * 8)
        height = max(8, (image.height // 8) * 8)
        image = image.resize((width, height), Image.Resampling.BILINEAR)
        array = np.array(image).astype("float32") / 255.0
        tensor = torch.from_numpy(array).permute(2, 0, 1)
        return tensor.to(self.device)

    def run(self, frame_paths: List[str]) -> Dict[str, object]:
        frames = self._existing_paths(frame_paths)
        if not self._ensure_model():
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": self.load_error or "model unavailable",
                "device": self.device,
                "model_source": "torchvision-pretrained",
            }
        if len(frames) < 2:
            return {
                "detector": self.detector_name,
                "available": False,
                "score": 0.0,
                "reason": "not enough frames",
                "device": self.device,
            }
        sample_frames = frames[:: max(1, int(len(frames) / 8))][:8]
        with torch.inference_mode():
            flow_magnitudes = []
            for index in range(len(sample_frames) - 1):
                tensor_a = self._load_raft_tensor(sample_frames[index]).unsqueeze(0)
                tensor_b = self._load_raft_tensor(sample_frames[index + 1]).unsqueeze(0)
                flow_prediction = self.model(tensor_a, tensor_b)[-1]
                flow_magnitudes.append(torch.linalg.norm(flow_prediction, dim=1).mean().item())
        average_flow = sum(flow_magnitudes) / max(1, len(flow_magnitudes))
        score = max(0.0, min(100.0, 100.0 - (average_flow * 8.0)))
        return {
            "detector": self.detector_name,
            "available": True,
            "score": round(score, 2),
            "sample_count": len(sample_frames),
            "device": self.device,
            "model_name": self.model_name,
            "average_flow": round(average_flow, 4),
        }
