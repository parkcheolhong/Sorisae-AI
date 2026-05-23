from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from PIL import Image, ImageChops, ImageFilter, ImageStat


def _existing_paths(paths: Iterable[str]) -> List[Path]:
    return [
        Path(value)
        for value in (str(item or "").strip() for item in paths)
        if value and Path(value).exists() and Path(value).is_file()
    ]


def _mean_rgb(path: Path) -> List[float]:
    stat = ImageStat.Stat(Image.open(path).convert("RGB"))
    return [float(channel) for channel in stat.mean]


def _diff_score(path_a: Path, path_b: Path) -> float:
    image_a = Image.open(path_a).convert("RGB")
    image_b = Image.open(path_b).convert("RGB")
    diff = ImageChops.difference(image_a, image_b)
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / max(1, len(stat.mean)))


def _edge_score(path: Path) -> float:
    image = Image.open(path).convert("L")
    edges = image.filter(ImageFilter.FIND_EDGES)
    stat = ImageStat.Stat(edges)
    return float(stat.mean[0])


def _blurred_edge_image(path: Path) -> Image.Image:
    return Image.open(path).convert("L").filter(ImageFilter.GaussianBlur(radius=2.0)).filter(ImageFilter.FIND_EDGES)


def _structure_delta(path_a: Path, path_b: Path) -> float:
    image_a = _blurred_edge_image(path_a)
    image_b = _blurred_edge_image(path_b)
    diff = ImageChops.difference(image_a, image_b)
    stat = ImageStat.Stat(diff)
    return float(stat.mean[0])


def _silhouette_mask(path: Path) -> Image.Image:
    image = Image.open(path).convert("L").filter(ImageFilter.GaussianBlur(radius=1.4))
    return image.point(lambda value: 255 if value > 96 else 0)


def _mask_density(mask: Image.Image) -> float:
    stat = ImageStat.Stat(mask)
    return float(stat.mean[0] / 255.0)


def run_face_detector(reference_paths: List[str], frame_paths: List[str]) -> Dict[str, object]:
    references = _existing_paths(reference_paths)
    frames = _existing_paths(frame_paths)
    if not references or not frames:
        return {
            "detector": "face-consistency-detector",
            "available": False,
            "score": 0.0,
            "reason": "missing face references or frames",
        }
    baseline = _mean_rgb(references[0])
    sample_frames = frames[: min(6, len(frames))]
    deltas = []
    for frame_path in sample_frames:
        frame_mean = _mean_rgb(frame_path)
        deltas.append(sum(abs(frame_mean[index] - baseline[index]) for index in range(3)) / 3.0)
    average_delta = sum(deltas) / max(1, len(deltas))
    score = max(0.0, 100.0 - (average_delta * 2.8))
    return {
        "detector": "face-consistency-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(average_delta, 3),
        "sample_count": len(sample_frames),
    }


def run_hand_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if not frames:
        return {
            "detector": "hand-anatomy-detector",
            "available": False,
            "score": 0.0,
            "reason": "missing frames",
        }
    sample_frames = frames[:: max(1, int(len(frames) / 6))][:6]
    edge_values = [_edge_score(path) for path in sample_frames]
    average_edges = sum(edge_values) / max(1, len(edge_values))
    score = min(100.0, average_edges * 4.2)
    return {
        "detector": "hand-anatomy-detector",
        "available": True,
        "score": round(score, 2),
        "average_edges": round(average_edges, 3),
        "sample_count": len(sample_frames),
    }


def run_anatomy_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 2:
        return {
            "detector": "body-ratio-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    sample_pairs = [(frames[index], frames[index + 1]) for index in range(min(5, len(frames) - 1))]
    deltas = [_diff_score(first, second) for first, second in sample_pairs]
    average_delta = sum(deltas) / max(1, len(deltas))
    score = min(100.0, average_delta * 5.8)
    return {
        "detector": "body-ratio-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(average_delta, 3),
        "sample_count": len(sample_pairs),
    }


def run_flicker_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 2:
        return {
            "detector": "temporal-flicker-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    samples = frames[:: max(1, int(len(frames) / 8))][:8]
    if len(samples) < 2:
        return {
            "detector": "temporal-flicker-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough sampled frames",
        }
    deltas = [_diff_score(samples[index], samples[index + 1]) for index in range(len(samples) - 1)]
    average_delta = sum(deltas) / max(1, len(deltas))
    score = max(0.0, 100.0 - (average_delta * 4.0))
    return {
        "detector": "temporal-flicker-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(average_delta, 3),
        "sample_count": len(samples),
    }


def run_background_detector(reference_paths: List[str], frame_paths: List[str]) -> Dict[str, object]:
    references = _existing_paths(reference_paths)
    frames = _existing_paths(frame_paths)
    if len(frames) < 2:
        return {
            "detector": "environment-structure-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    sample_frames = frames[:: max(1, int(len(frames) / 8))][:8]
    temporal_deltas = [_structure_delta(sample_frames[index], sample_frames[index + 1]) for index in range(len(sample_frames) - 1)]
    temporal_average = sum(temporal_deltas) / max(1, len(temporal_deltas))
    reference_penalty = 0.0
    if references:
        reference = references[0]
        reference_samples = sample_frames[: min(3, len(sample_frames))]
        reference_deltas = [_structure_delta(reference, frame_path) for frame_path in reference_samples]
        reference_penalty = (sum(reference_deltas) / max(1, len(reference_deltas))) * 0.15
    score = max(0.0, 100.0 - ((temporal_average + reference_penalty) * 2.4))
    return {
        "detector": "environment-structure-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(temporal_average, 3),
        "reference_penalty": round(reference_penalty, 3),
        "sample_count": len(sample_frames),
    }


def run_walking_cycle_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 4:
        return {
            "detector": "walking-cycle-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    samples = frames[:: max(1, int(len(frames) / 10))][:10]
    deltas = [_diff_score(samples[index], samples[index + 1]) for index in range(len(samples) - 1)]
    if not deltas:
        return {
            "detector": "walking-cycle-detector",
            "available": False,
            "score": 0.0,
            "reason": "insufficient motion deltas",
        }
    motion_variance = max(deltas) - min(deltas)
    average_delta = sum(deltas) / max(1, len(deltas))
    score = max(0.0, min(100.0, (average_delta * 3.8) + (motion_variance * 1.7)))
    return {
        "detector": "walking-cycle-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(average_delta, 3),
        "motion_variance": round(motion_variance, 3),
        "sample_count": len(samples),
    }


def run_gesture_performance_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 4:
        return {
            "detector": "gesture-performance-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    samples = frames[:: max(1, int(len(frames) / 8))][:8]
    edge_values = [_edge_score(path) for path in samples]
    if not edge_values:
        return {
            "detector": "gesture-performance-detector",
            "available": False,
            "score": 0.0,
            "reason": "insufficient edge samples",
        }
    average_edges = sum(edge_values) / max(1, len(edge_values))
    spread = max(edge_values) - min(edge_values)
    score = max(0.0, min(100.0, (average_edges * 3.2) + spread))
    return {
        "detector": "gesture-performance-detector",
        "available": True,
        "score": round(score, 2),
        "average_edges": round(average_edges, 3),
        "spread": round(spread, 3),
        "sample_count": len(samples),
    }


def run_speech_lipsync_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 4:
        return {
            "detector": "speech-lipsync-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    samples = frames[:: max(1, int(len(frames) / 8))][:8]
    mouth_motion = [_diff_score(samples[index], samples[index + 1]) for index in range(len(samples) - 1)]
    if not mouth_motion:
        return {
            "detector": "speech-lipsync-detector",
            "available": False,
            "score": 0.0,
            "reason": "insufficient temporal mouth samples",
        }
    average_delta = sum(mouth_motion) / max(1, len(mouth_motion))
    score = max(0.0, min(100.0, average_delta * 4.5))
    return {
        "detector": "speech-lipsync-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(average_delta, 3),
        "sample_count": len(samples),
    }


def run_silhouette_preservation_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 2:
        return {
            "detector": "silhouette-preservation-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    samples = frames[:: max(1, int(len(frames) / 8))][:8]
    masks = [_silhouette_mask(path) for path in samples]
    densities = [_mask_density(mask) for mask in masks]
    spread = max(densities) - min(densities)
    score = max(0.0, 100.0 - (spread * 180.0))
    return {
        "detector": "silhouette-preservation-detector",
        "available": True,
        "score": round(score, 2),
        "density_spread": round(spread, 4),
        "sample_count": len(samples),
    }


def run_shape_blur_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if not frames:
        return {
            "detector": "shape-blur-detector",
            "available": False,
            "score": 0.0,
            "reason": "missing frames",
        }
    samples = frames[:: max(1, int(len(frames) / 8))][:8]
    edges = [_edge_score(path) for path in samples]
    average_edges = sum(edges) / max(1, len(edges))
    score = max(0.0, min(100.0, (average_edges - 8.0) * 6.0))
    return {
        "detector": "shape-blur-detector",
        "available": True,
        "score": round(score, 2),
        "average_edges": round(average_edges, 3),
        "sample_count": len(samples),
    }


def run_chunk_seam_detector(frame_paths: List[str]) -> Dict[str, object]:
    frames = _existing_paths(frame_paths)
    if len(frames) < 4:
        return {
            "detector": "chunk-seam-detector",
            "available": False,
            "score": 0.0,
            "reason": "not enough frames",
        }
    head = frames[:2]
    tail = frames[-2:]
    seam_deltas = [_structure_delta(tail[index], head[index]) for index in range(min(len(head), len(tail)))]
    seam_average = sum(seam_deltas) / max(1, len(seam_deltas))
    score = max(0.0, 100.0 - (seam_average * 3.5))
    return {
        "detector": "chunk-seam-detector",
        "available": True,
        "score": round(score, 2),
        "average_delta": round(seam_average, 3),
        "sample_count": len(seam_deltas),
    }
