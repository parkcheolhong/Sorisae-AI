"""POST /api/llm/voice-translate (STT→번역) 엔드포인트 테스트.

STT는 모킹(오디오/모델 불필요), 번역은 NadoTranslator 오프라인 사전 경로로 검증.
"""
import base64

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import backend.llm.voice_gateway as vg


@pytest.fixture()
def client():
    app = FastAPI()
    app.include_router(vg.router)
    with TestClient(app) as c:
        yield c


def test_voice_translate_with_transcript_uses_offline_dict(client):
    # transcript 직접 전달 → STT 생략. en→ko 'hello'는 NadoTranslator 사전에 존재.
    resp = client.post("/api/llm/voice-translate", json={
        "transcript": "hello",
        "from_lang": "en",
        "to_lang": "ko",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["original_text"] == "hello"
    assert data["translated"] == "안녕하세요"
    assert data["engine"] == "nado"
    assert data["from_lang"] == "en" and data["to_lang"] == "ko"


def test_voice_translate_stt_path_is_invoked(client, monkeypatch):
    # 오디오 경로: _transcribe_audio를 모킹해 STT→번역 배선을 검증.
    def _fake_transcribe(audio_bytes, language=None):
        assert language == "en"  # from_lang이 STT 힌트로 전달되는지 확인
        return "hello", "en"

    monkeypatch.setattr(vg, "_transcribe_audio", _fake_transcribe)
    audio_b64 = base64.b64encode(b"dummy-audio").decode("ascii")

    resp = client.post("/api/llm/voice-translate", json={
        "audio_base64": audio_b64,
        "from_lang": "en",
        "to_lang": "ko",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["original_text"] == "hello"
    assert data["translated"] == "안녕하세요"
    assert data["detected_language"] == "en"


def test_voice_translate_requires_input(client):
    resp = client.post("/api/llm/voice-translate", json={"from_lang": "en", "to_lang": "ko"})
    assert resp.status_code == 400
