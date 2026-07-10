from backend.services.nadotongryoksa.image_normalize import normalize_image_bytes_for_ocr


def test_normalize_image_bytes_for_ocr_small_payload_unchanged():
    payload = b"\xff\xd8\xff" + b"x" * 100
    assert normalize_image_bytes_for_ocr(payload) == payload
