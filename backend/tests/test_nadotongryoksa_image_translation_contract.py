# FILE-ID: FILE-BACKEND-TEST-NADOTONGRYOKSA-IMAGE-TRANSLATION-CONTRACT-PY
# SECTION-ID: SECTION-BACKEND-TEST-NADOTONGRYOKSA-IMAGE-TRANSLATION-CONTRACT-MAIN
# FEATURE-ID: FEATURE-NADOTONGRYOKSA-IMAGE-TRANSLATION-CONTRACT-TESTS
# CHUNK-ID: CHUNK-BACKEND-TEST-NADOTONGRYOKSA-IMAGE-TRANSLATION-CONTRACT-001

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.mobile.image_translation import service as image_translation_service
from backend.mobile.image_translation.router import router
from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES


image_translation_router_module = importlib.import_module("backend.mobile.image_translation.router")


def _build_test_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_image_translation_contract_returns_ocr_and_translated_text(monkeypatch):
    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint: str | None = None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(image_translation_service, "extract_text_from_image", lambda _image_bytes: ("서울역\n체크인", 2))
    monkeypatch.setattr(image_translation_router_module, "extract_text_from_image", lambda _image_bytes: ("서울역\n체크인", 2))
    monkeypatch.setattr(image_translation_service.NadoTranslator, "get_instance", classmethod(lambda cls: _FakeTranslator()))

    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={"source_language": "ko", "target_language": "en"},
        files={"file": ("station.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["file_name"] == "station.png"
    assert payload["content_type"] == "image/png"
    assert payload["original_text"] == "서울역\n체크인"
    assert payload["translated"] == "ko->en:서울역\n체크인"
    assert payload["line_count"] == 2
    assert payload["engine"] == "rapidocr+nado"


def test_image_translation_corrects_source_language_from_ocr_text(monkeypatch):
    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint: str | None = None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(
        image_translation_service,
        "extract_text_from_image",
        lambda _image_bytes: ("Welcome to Seoul Station", 1),
    )
    monkeypatch.setattr(
        image_translation_router_module,
        "extract_text_from_image",
        lambda _image_bytes: ("Welcome to Seoul Station", 1),
    )
    monkeypatch.setattr(
        image_translation_service.NadoTranslator,
        "get_instance",
        classmethod(lambda cls: _FakeTranslator()),
    )

    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={"source_language": "ko", "target_language": "ko", "region_hint": "jeju"},
        files={"file": ("station.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_language"] == "en"
    assert payload["target_language"] == "ko"
    assert payload["translated"] == "서울역에 오신 것을 환영합니다"


def test_image_translation_rejects_non_image_upload():
    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={"source_language": "ko", "target_language": "en"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )

    assert response.status_code == 400
    assert "확장자" in response.json()["detail"]


def test_image_translation_accepts_extended_50_language_codes(monkeypatch):
    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint: str | None = None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(image_translation_service, "extract_text_from_image", lambda _image_bytes: ("שלום", 1))
    monkeypatch.setattr(image_translation_router_module, "extract_text_from_image", lambda _image_bytes: ("שלום", 1))
    monkeypatch.setattr(image_translation_service.NadoTranslator, "get_instance", classmethod(lambda cls: _FakeTranslator()))

    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={"source_language": "he", "target_language": "fil"},
        files={"file": ("hebrew-sign.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["original_text"] == "שלום"
    assert payload["translated"] == "he->fil:שלום"
    assert payload["source_language"] == "he"
    assert payload["target_language"] == "fil"


@pytest.mark.parametrize(
    ("target_language", "sample_text"),
    [(code, f"sample->{code}") for code in SUPPORTED_LANGUAGES if code != "ko"],
)
def test_image_translation_smokes_every_supported_target_language(monkeypatch, target_language, sample_text):
    class _FakeTranslator:
        def translate(
            self,
            text: str,
            from_lang: str = "ko",
            to_lang: str = "en",
            region_hint: str | None = None,
        ) -> str:
            return f"{from_lang}->{to_lang}:{text}"

    monkeypatch.setattr(image_translation_service, "extract_text_from_image", lambda _image_bytes: (sample_text, 1))
    monkeypatch.setattr(image_translation_router_module, "extract_text_from_image", lambda _image_bytes: (sample_text, 1))
    monkeypatch.setattr(image_translation_service.NadoTranslator, "get_instance", classmethod(lambda cls: _FakeTranslator()))

    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={"source_language": "ko", "target_language": target_language},
        files={"file": (f"ocr-{target_language}.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["original_text"] == sample_text
    assert payload["translated"] == f"ko->{target_language}:{sample_text}"
    assert payload["source_language"] == "ko"
    assert payload["target_language"] == target_language


def test_image_translation_normalizes_supported_dialect_profile(monkeypatch):
    monkeypatch.setattr(image_translation_service, "extract_text_from_image", lambda _image_bytes: ("혼저 옵서예", 1))
    monkeypatch.setattr(image_translation_router_module, "extract_text_from_image", lambda _image_bytes: ("혼저 옵서예", 1))
    translator = image_translation_service.NadoTranslator.get_instance()
    translator._cache.clear()
    monkeypatch.setattr(
        translator,
        "_googletrans",
        lambda text, from_lang, to_lang: f"{from_lang}:jeju:{text}",
    )

    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={"source_language": "ko", "target_language": "en", "region_hint": "jeju"},
        files={"file": ("jeju-sign.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["translated"] == "ko:jeju:어서 오세요"


@pytest.mark.parametrize(
    ("source_language", "region_hint", "sample_text", "expected_text"),
    [
        ("ko", "jeju", "혼저 옵서예. 하영 고맙수다.", "어서 오세요. 많이 고맙습니다."),
        ("zh", "guangdong", "唔该，喺边度食饭？", "谢谢，在哪里吃饭？"),
        ("ja", "kansai", "ほんま、おおきに。あかんで。", "本当、ありがとう。だめで。"),
        (
            "hi",
            "bihar",
            "humra kitna hai re, jaldi karo na",
            "hamara kitna hai, kripya jaldi kijiye",
        ),
        ("it", "naples", "Uaglio, che fai mo?", "ragazzo, cosa fai adesso?"),
    ],
)
def test_image_translation_smokes_supported_country_dialect_samples(
    monkeypatch,
    source_language,
    region_hint,
    sample_text,
    expected_text,
):
    monkeypatch.setattr(
        image_translation_service,
        "extract_text_from_image",
        lambda _image_bytes: (sample_text, 1),
    )
    monkeypatch.setattr(
        image_translation_router_module,
        "extract_text_from_image",
        lambda _image_bytes: (sample_text, 1),
    )
    translator = image_translation_service.NadoTranslator.get_instance()
    translator._cache.clear()
    monkeypatch.setattr(
        translator,
        "_googletrans",
        lambda text, current_from, _to: f"{current_from}:{region_hint}:{text}",
    )

    client = _build_test_client()
    response = client.post(
        "/api/mobile/image-translation",
        data={
            "source_language": source_language,
            "target_language": "en",
            "region_hint": region_hint,
        },
        files={
            "file": (
                f"{source_language}-{region_hint}.png",
                b"fake-image",
                "image/png",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert (
        payload["translated"]
        == f"{source_language}:{region_hint}:{expected_text}"
    )
