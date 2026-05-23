from backend.movie_studio.quality.arcface_adapter import build_face_recognition_adapter


def test_build_face_recognition_adapter_returns_primary_or_fallback():
    adapter, status = build_face_recognition_adapter()

    assert adapter is not None
    assert status["adapter_mode"] in {"primary", "secondary", "fallback"}
    assert "adapter_name" in status
    assert "available" in status
    assert "embedding_backend" in status
