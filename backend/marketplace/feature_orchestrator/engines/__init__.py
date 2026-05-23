"""
P1-1: Feature Orchestrator Engines — 엔진 레지스트리

각 feature_id에 대응하는 엔진을 매핑합니다.
"""
from .spreadsheet_generation_engine import SpreadsheetGenerationEngine
from .powerpoint_generation_engine import PowerPointGenerationEngine
from .image_generation_engine import ImageGenerationEngine
from .music_generation_engine import MusicGenerationEngine
from .document_generation_engine import DocumentGenerationEngine
from .video_generation_engine import VideoGenerationEngine

ENGINE_REGISTRY = {
    "spreadsheet-builder": SpreadsheetGenerationEngine,
    "powerpoint-builder": PowerPointGenerationEngine,
    "hybrid-image": ImageGenerationEngine,
    "music-generator": MusicGenerationEngine,
    "doc-writer": DocumentGenerationEngine,
    "video-producer": VideoGenerationEngine,
}


def get_engine(feature_id: str):
    """feature_id에 해당하는 엔진 인스턴스를 반환합니다."""
    engine_cls = ENGINE_REGISTRY.get(feature_id)
    if engine_cls is None:
        raise ValueError(f"Unknown feature_id: {feature_id}")
    return engine_cls()
