from pathlib import Path

from PIL import Image

from backend.movie_studio.quality.ml_detector_runtime import (
    AnatomyPoseDetectorRunner,
    FaceEmbeddingDetectorRunner,
    FlickerFlowDetectorRunner,
    HandLandmarkDetectorRunner,
)


def test_ml_detector_runners_return_structured_scores(tmp_path: Path):
    reference = tmp_path / "reference.png"
    frame_one = tmp_path / "frame_0001.png"
    frame_two = tmp_path / "frame_0002.png"
    Image.new("RGB", (320, 180), color=(100, 100, 100)).save(reference)
    Image.new("RGB", (320, 180), color=(110, 110, 110)).save(frame_one)
    Image.new("RGB", (320, 180), color=(120, 120, 120)).save(frame_two)

    face_runner = FaceEmbeddingDetectorRunner()
    hand_runner = HandLandmarkDetectorRunner()
    anatomy_runner = AnatomyPoseDetectorRunner()
    flicker_runner = FlickerFlowDetectorRunner()

    face = face_runner.run(reference_paths=[str(reference)], frame_paths=[str(frame_one), str(frame_two)])
    hand = hand_runner.run(frame_paths=[str(frame_one), str(frame_two)])
    anatomy = anatomy_runner.run(frame_paths=[str(frame_one), str(frame_two)])
    flicker = flicker_runner.run(frame_paths=[str(frame_one), str(frame_two)])

    assert face["detector"] == "face-consistency-detector-ml"
    assert hand["detector"] == "hand-anatomy-detector-ml"
    assert anatomy["detector"] == "body-ratio-detector-ml"
    assert flicker["detector"] == "temporal-flicker-detector-ml"
    assert "score" in face and "score" in hand and "score" in anatomy and "score" in flicker
    assert "adapter" in face
    if face.get("available"):
        assert face["adapter"]["adapter_mode"] in {"primary", "secondary", "fallback"}
    if hand.get("available"):
        assert hand["model_name"] == "keypointrcnn-resnet50-fpn-coco-hand-proxy"
    if anatomy.get("available"):
        assert anatomy["model_name"] == "keypointrcnn-resnet50-fpn-coco-pose-proxy"
    if flicker.get("available"):
        assert flicker["model_name"] == "raft-small-optical-flow-flicker"
