import asyncio
import base64
import logging
import os
import re
import time

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from backend.llm.correlation import (
    FEATURE_IDS,
    ensure_correlation_id,
)
from backend.llm.loader import llm_loader
from backend.llm.voice_gateway import _synthesize_tts

router = APIRouter(prefix="/api/llm", tags=["llm-status"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_llm_status():
    return llm_loader.get_status()


# ── WorldLinco 전용 공개 번역 엔드포인트 (인증 불필요, 소리새 독립) ──
class _MobileTranslateRequest(BaseModel):
    text: str
    from_lang: str = "ko"
    to_lang: str = "en"
    region_hint: str | None = None


def _coerce_to_optional_int(value: object) -> int | None:
    """상관/순서 텔레메트리 필드 코어션 — 절대 422를 내지 않는다(핫 오디오 경로 보호).

    ``int``·``float``·숫자 문자열 등 어떤 표현이 와도 정수로 강제 변환하고, 변환 불가 시
    ``None`` 으로 흘려보낸다. (pydantic v2 strict ``int`` 가 실수/문자열을 거부해 통역 hot
    path 가 422로 죽는 회귀를 원천 차단 — VoIP/대면 양 채널 공통 방어선)
    """
    if value is None:
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        try:
            return int(float(value))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return None


def _coerce_lang_default(value: object, default: str) -> str:
    """언어 코드 코어션 — 핫 오디오 경로 보호. 클라이언트가 null/빈값/비문자열을 보내도
    422로 죽지 않고 기본값으로 보정한다(언어 상태가 잠깐 비는 순간의 세그먼트 손실 방지)."""
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _coerce_bool_default(value: object, default: bool) -> bool:
    """불리언 코어션 — null/문자열/숫자를 관대하게 받아 기본값으로 보정(422 방지)."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return default


class _MobileVoiceTranslateRequest(BaseModel):
    audio_base64: str | None = None
    transcript: str | None = None
    from_lang: str = "ko"
    to_lang: str = "en"
    region_hint: str | None = None
    language: str | None = None
    # 채널 모드 명시 필드(V.2 Delivery 채널 경계). 미지정 시 bilingual_mode 불리언으로 폴백.
    #   - 'bilingual'/'face'         → 여행 대면 통역(자동 감지 + GPS)
    #   - 'designated'/'voip'/'chat' → 지정 언어 고정(언어 락)
    mode: str | None = None
    bilingual_mode: bool = False
    lang_a: str | None = None
    lang_b: str | None = None
    device_tts: bool = False
    # V.2 오케스트레이터 ID 백본 — 기능 ID 자동 매핑→셀프 서빙→전송(딜리버리)→음성 발화 자동 상관용.
    # 모두 선택 필드(하위호환): 없으면 서버가 동일 스킴으로 새로 발급해 echo 한다.
    correlation_id: str | None = None
    feature_id: str | None = None
    utterance_id: str | None = None
    seq_id: int | None = None
    chunk_index: int | None = None
    # V.2 Session Core(선택, 하위호환) — 통화/세션 단위 언어쌍·턴 맥락 기억용.
    # 미지정 시 Session Core 기록은 no-op. 응답 contract 무변경.
    session_id: str | None = None

    @field_validator("seq_id", "chunk_index", mode="before")
    @classmethod
    def _coerce_optional_int(cls, value: object) -> int | None:
        return _coerce_to_optional_int(value)

    @field_validator("from_lang", mode="before")
    @classmethod
    def _coerce_from_lang(cls, value: object) -> str:
        return _coerce_lang_default(value, "ko")

    @field_validator("to_lang", mode="before")
    @classmethod
    def _coerce_to_lang(cls, value: object) -> str:
        return _coerce_lang_default(value, "en")

    @field_validator("bilingual_mode", "device_tts", mode="before")
    @classmethod
    def _coerce_mobile_bools(cls, value: object) -> bool:
        # bilingual_mode 기본 False, device_tts 기본 False — 둘 다 null이면 기존 기본값 보존.
        return _coerce_bool_default(value, False)


# ── 채널별 100% 분리(V.2 격리) ──────────────────────────────────────────────
# 사용자는 기능을 동시 사용하지 않으므로 VoIP와 대면(face)을 완전 분리한다.
# 요청 모델뿐 아니라 핵심 통역 로직(STT→번역→TTS)도 채널별 독립 코어 함수로 물리 분리한다
# (``_voip_voice_translate_core`` / ``_face_voice_translate_core``). 한 채널의 계약·검증·코어
# 로직에 버그가 생겨도 다른 채널에 절대 전파되지 않는다.
class _VoipVoiceTranslateRequest(BaseModel):
    """VoIP 통화 음성 릴레이 전용(designated/언어 락). 대면 통역과 계약 분리."""

    audio_base64: str | None = None
    transcript: str | None = None
    from_lang: str = "ko"
    to_lang: str = "en"
    region_hint: str | None = None
    language: str | None = None
    mode: str | None = "designated"
    device_tts: bool = False
    correlation_id: str | None = None
    feature_id: str | None = None
    utterance_id: str | None = None
    seq_id: int | None = None
    chunk_index: int | None = None
    session_id: str | None = None

    @field_validator("seq_id", "chunk_index", mode="before")
    @classmethod
    def _coerce_optional_int(cls, value: object) -> int | None:
        return _coerce_to_optional_int(value)

    @field_validator("from_lang", mode="before")
    @classmethod
    def _coerce_from_lang(cls, value: object) -> str:
        return _coerce_lang_default(value, "ko")

    @field_validator("to_lang", mode="before")
    @classmethod
    def _coerce_to_lang(cls, value: object) -> str:
        return _coerce_lang_default(value, "en")

    @field_validator("device_tts", mode="before")
    @classmethod
    def _coerce_voip_bool(cls, value: object) -> bool:
        return _coerce_bool_default(value, False)

    def to_core(self) -> "_MobileVoiceTranslateRequest":
        return _MobileVoiceTranslateRequest(
            audio_base64=self.audio_base64,
            transcript=self.transcript,
            from_lang=self.from_lang,
            to_lang=self.to_lang,
            region_hint=self.region_hint,
            language=self.language,
            mode=self.mode or "designated",
            bilingual_mode=False,
            device_tts=self.device_tts,
            correlation_id=self.correlation_id,
            feature_id=self.feature_id or FEATURE_IDS["voip_voice_relay"],
            utterance_id=self.utterance_id,
            seq_id=self.seq_id,
            chunk_index=self.chunk_index,
            session_id=self.session_id,
        )


class _FaceVoiceTranslateRequest(BaseModel):
    """여행 대면 통역 전용(bilingual 자동 감지 또는 수동 단방향 designated). VoIP와 계약 분리.

    대면은 순서/세션 텔레메트리(seq_id·chunk_index·session_id)를 사용하지 않으므로 계약에서
    제외한다 — VoIP 전용 필드의 검증 변경이 대면 요청에 절대 영향을 줄 수 없다.
    """

    audio_base64: str | None = None
    transcript: str | None = None
    from_lang: str = "ko"
    to_lang: str = "en"
    region_hint: str | None = None
    language: str | None = None
    mode: str | None = "bilingual"
    bilingual_mode: bool = True
    lang_a: str | None = None
    lang_b: str | None = None
    device_tts: bool = True
    correlation_id: str | None = None
    feature_id: str | None = None

    @field_validator("from_lang", mode="before")
    @classmethod
    def _coerce_from_lang(cls, value: object) -> str:
        return _coerce_lang_default(value, "ko")

    @field_validator("to_lang", mode="before")
    @classmethod
    def _coerce_to_lang(cls, value: object) -> str:
        return _coerce_lang_default(value, "en")

    @field_validator("bilingual_mode", "device_tts", mode="before")
    @classmethod
    def _coerce_face_bools(cls, value: object) -> bool:
        return _coerce_bool_default(value, True)

    def to_core(self) -> "_MobileVoiceTranslateRequest":
        return _MobileVoiceTranslateRequest(
            audio_base64=self.audio_base64,
            transcript=self.transcript,
            from_lang=self.from_lang,
            to_lang=self.to_lang,
            region_hint=self.region_hint,
            language=self.language,
            mode=self.mode or "bilingual",
            bilingual_mode=self.bilingual_mode,
            lang_a=self.lang_a,
            lang_b=self.lang_b,
            device_tts=self.device_tts,
            correlation_id=self.correlation_id,
            feature_id=self.feature_id or FEATURE_IDS["face_interpret"],
        )


_BILINGUAL_VOICE_MODES = {"bilingual", "face", "face_conversation"}
_DESIGNATED_VOICE_MODES = {"designated", "voip", "voip_relay", "chat"}


def _resolve_voice_channel_mode(payload: "_MobileVoiceTranslateRequest") -> bool:
    """요청의 채널 모드를 해석해 bilingual 여부를 반환한다.

    명시적 ``mode`` 필드를 우선하고, 없으면 레거시 ``bilingual_mode`` 불리언으로 폴백한다.
    (hot path 계약 보존 — 구버전 클라이언트도 그대로 동작)
    """
    requested = str(payload.mode or "").strip().lower()
    if requested in _BILINGUAL_VOICE_MODES:
        return True
    if requested in _DESIGNATED_VOICE_MODES:
        return False
    return bool(payload.bilingual_mode)


def _decode_mobile_voice_audio(audio_base64: str) -> bytes:
    try:
        return base64.b64decode(audio_base64, validate=True)
    except Exception as exc:  # pragma: no cover
        raise ValueError("유효한 audio_base64 형식이 아닙니다") from exc


def _transcribe_mobile_voice_audio(
    audio_bytes: bytes,
    language_hint: str | None = None,
    source_lang_hint: str | None = None,
    lock_language: bool = False,
) -> tuple[str, str | None, dict[str, object]]:
    """지정 언어(designated) 모드용 STT.

    VoIP/채팅은 화자의 언어를 이미 알고 있으므로 ``lock_language=True``로 호출하면
    Whisper를 해당 언어로 고정한다.

    [2-3 Language-ID 게이트] 화자 언어가 정해졌을 때, 먼저 음향 기반 언어감지
    (auto-detect)로 실제 언어 확률을 본다.
    - 감지 언어 == from_lang  → 그대로 사용(추가 추론 없음, 1패스).
    - 감지 언어 != from_lang 이고 **확신이 높으면**(language_probability ≥ 임계값)
      → 지정 언어 외 타국어/에코로 보고 잡음 거부.
    - 확신이 낮으면(모호/혼합/짧음) → 거부하지 않고 from_lang 고정 디코딩으로 폴백.
      (정상 지정-언어 발화가 오감지로 잘리는 회귀를 원천 차단)
    ``VOICE_DESIGNATED_LANG_GATE=0`` 으로 비활성, ``VOICE_DESIGNATED_LID_REJECT_PROB``
    으로 임계값(기본 0.80) 조정.
    """
    from backend.llm.voice_gateway import (
        _normalize_voice_audio_bytes,
        _normalize_whisper_language_hint,
        classify_voice_relay_stt_trust,
        _run_faster_whisper,
    )

    normalized_audio = _normalize_voice_audio_bytes(audio_bytes)
    hinted_language = _normalize_whisper_language_hint(language_hint)
    source_language = _normalize_whisper_language_hint(source_lang_hint)
    initial_prompt = ""

    expected_lang = source_language or hinted_language
    lid_gate_enabled = (
        lock_language
        and bool(expected_lang)
        and os.getenv("VOICE_DESIGNATED_LANG_GATE", "1").strip().lower() not in ("0", "false", "no")
    )
    if lid_gate_enabled:
        try:
            reject_prob = float(os.getenv("VOICE_DESIGNATED_LID_REJECT_PROB", "0.80"))
        except ValueError:
            reject_prob = 0.80
        try:
            auto_payload = _run_faster_whisper(normalized_audio, None, initial_prompt)
        except Exception:
            auto_payload = None
        if auto_payload is not None:
            auto_tx = str(auto_payload.get("transcript") or "").strip()
            auto_lang = str(auto_payload.get("detected_language") or "").strip().lower() or None
            auto_prob = float(auto_payload.get("language_probability", 0.0) or 0.0)
            if auto_tx:
                auto_trust = str(auto_payload.get("stt_trust") or classify_voice_relay_stt_trust(
                    auto_tx,
                    float(auto_payload.get("avg_logprob", -5.0)),
                    float(auto_payload.get("max_no_speech_prob", 1.0)),
                ))
                if _voice_lang_codes_equivalent(auto_lang, expected_lang):
                    # 이미 지정 언어로 감지됨 → 그대로 사용.
                    return auto_tx, auto_lang, auto_payload
                if auto_trust != "low" and auto_prob >= reject_prob:
                    logger.info(
                        "[voice-stt] designated LID gate rejected foreign audio "
                        "from_lang=%s detected=%s p=%.2f text=%r",
                        expected_lang,
                        auto_lang,
                        auto_prob,
                        auto_tx,
                    )
                    raise RuntimeError("음성이 감지되지 않았습니다. (지정 언어 외 잡음)")
                # 확신 낮음(모호/혼합) → 아래 from_lang 고정 디코딩으로 정확도 확보.

    attempts: list[str | None] = []
    if hinted_language:
        attempts.append(hinted_language)
    if source_language and source_language not in attempts:
        attempts.append(source_language)
    # 지정 언어 모드에서는 auto-detect 폴백을 추가하지 않는다(언어를 이미 알고 있음).
    if not lock_language and None not in attempts:
        attempts.append(None)
    if not attempts:
        attempts.append(None)

    last_error: Exception | None = None
    best_payload: dict[str, object] | None = None
    for attempt_language in attempts:
        try:
            payload = _run_faster_whisper(
                normalized_audio,
                attempt_language,
                initial_prompt,
            )
            transcript = str(payload.get("transcript") or "").strip()
            if not transcript:
                continue
            trust = str(payload.get("stt_trust") or classify_voice_relay_stt_trust(
                transcript,
                float(payload.get("avg_logprob", -5.0)),
                float(payload.get("max_no_speech_prob", 1.0)),
            ))
            if trust == "low":
                continue
            best_payload = payload
            break
        except Exception as exc:
            last_error = exc

    if best_payload is not None:
        transcript = str(best_payload.get("transcript") or "").strip()
        detected = str(best_payload.get("detected_language") or "").strip() or None
        return transcript, detected, best_payload

    if last_error is not None:
        raise RuntimeError(str(last_error)) from last_error
    raise RuntimeError("음성이 감지되지 않았습니다. 다시 말씀해 주세요.")


def _normalize_voice_lang_code(value: str | None) -> str | None:
    normalized = str(value or "").strip().lower().replace("_", "-")
    if not normalized:
        return None
    from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES

    if normalized in SUPPORTED_LANGUAGES:
        return normalized
    base = normalized.split("-")[0]
    return base if base in SUPPORTED_LANGUAGES else None


def _voice_lang_codes_equivalent(left: str | None, right: str | None) -> bool:
    normalized_left = _normalize_voice_lang_code(left)
    normalized_right = _normalize_voice_lang_code(right)
    if not normalized_left or not normalized_right:
        return False
    if normalized_left == normalized_right:
        return True
    return normalized_left.split("-")[0] == normalized_right.split("-")[0]


def _transcribe_bilingual_voice_audio(
    audio_bytes: bytes,
    lang_a: str,
    lang_b: str,
) -> tuple[str, str | None, dict[str, object]]:
    from backend.llm.voice_gateway import (
        _normalize_voice_audio_bytes,
        _normalize_whisper_language_hint,
        classify_voice_relay_stt_trust,
        _run_faster_whisper,
    )

    normalized_audio = _normalize_voice_audio_bytes(audio_bytes)

    last_error: Exception | None = None
    best_payload: dict[str, object] | None = None
    best_score = -999.0

    def _consider(payload: dict[str, object]) -> bool:
        """후보를 점수화해 best로 갱신. detected가 언어쌍과 일치하면 True를 반환한다."""
        nonlocal best_payload, best_score
        transcript = str(payload.get("transcript") or "").strip()
        if not transcript:
            return False
        trust = str(payload.get("stt_trust") or classify_voice_relay_stt_trust(
            transcript,
            float(payload.get("avg_logprob", -5.0)),
            float(payload.get("max_no_speech_prob", 1.0)),
        ))
        if trust == "low":
            return False
        detected = _normalize_voice_lang_code(
            str(payload.get("detected_language") or "").strip() or None,
        )
        matched = _voice_lang_codes_equivalent(detected, lang_a) or _voice_lang_codes_equivalent(
            detected,
            lang_b,
        )
        score = float(payload.get("avg_logprob", -5.0)) + (0.75 if matched else 0.0)
        if score > best_score:
            best_score = score
            best_payload = payload
        return matched

    # 1) auto-detect 단일 패스 우선 — 지연을 줄이기 위해 먼저 1회만 추론한다.
    #    Whisper 자체 언어감지가 빠르고 정확하므로, 감지 언어가 언어쌍과 일치하고
    #    신뢰도가 높으면 추가 패스 없이 즉시 반환한다(공통 경로 = 1회 추론).
    try:
        auto_payload = _run_faster_whisper(normalized_audio, None, "")
        if _consider(auto_payload) and best_payload is auto_payload:
            transcript = str(auto_payload.get("transcript") or "").strip()
            detected = str(auto_payload.get("detected_language") or "").strip() or None
            return transcript, detected, auto_payload
    except Exception as exc:
        last_error = exc

    # 2) auto가 애매/불일치한 경우에만 언어 힌트 패스로 보강한다(드문 경로).
    hint_attempts: list[str] = []
    for lang in (lang_a, lang_b):
        hint = _normalize_whisper_language_hint(lang)
        if hint and hint not in hint_attempts:
            hint_attempts.append(hint)
    for attempt_language in hint_attempts:
        try:
            _consider(_run_faster_whisper(normalized_audio, attempt_language, ""))
        except Exception as exc:
            last_error = exc

    if best_payload is not None:
        transcript = str(best_payload.get("transcript") or "").strip()
        detected = str(best_payload.get("detected_language") or "").strip() or None
        return transcript, detected, best_payload

    if last_error is not None:
        raise RuntimeError(str(last_error)) from last_error
    raise RuntimeError("음성이 감지되지 않았습니다. 다시 말씀해 주세요.")


def _resolve_bilingual_route(
    *,
    detected_language: str | None,
    transcript: str,
    lang_a: str,
    lang_b: str,
) -> tuple[str, str] | None:
    from backend.designated_language import text_matches_designated_language

    detected = _normalize_voice_lang_code(detected_language)
    if _voice_lang_codes_equivalent(detected, lang_a):
        return lang_a, lang_b
    if _voice_lang_codes_equivalent(detected, lang_b):
        return lang_b, lang_a

    a_matches = text_matches_designated_language(transcript, lang_a, min_match_ratio=0.55)
    b_matches = text_matches_designated_language(transcript, lang_b, min_match_ratio=0.55)
    if a_matches and not b_matches:
        return lang_a, lang_b
    if b_matches and not a_matches:
        return lang_b, lang_a

    # V.2 보강: Whisper 감지·문자셋 매칭이 애매하면 LLM 언어식별로 판정한다.
    # (짧은 발화 오감지로 대면 통역이 422로 거부되던 문제 완화 — 같은 vLLM 재사용.)
    try:
        from backend.services.nadotongryoksa.translator import NadoTranslator

        guessed = NadoTranslator.get_instance().identify_language(transcript, [lang_a, lang_b])
    except Exception:
        guessed = None
    guessed_norm = _normalize_voice_lang_code(guessed)
    if _voice_lang_codes_equivalent(guessed_norm, lang_a):
        return lang_a, lang_b
    if _voice_lang_codes_equivalent(guessed_norm, lang_b):
        return lang_b, lang_a
    return None


# NOTE(G4): `_is_likely_silence_hallucination` 데드코드 제거됨(2026-06-20).
# silence/짧은 발화 hallucination 사전필터는 모바일(meter-dead/fixed-interval 경로)에서 수행하며,
# 서버는 아래 gibberish 가드 + whisper hallucination 시그니처로 처리한다.


# Whisper가 무음/잡음 구간에서 뱉는 "영상 아웃트로" 환각 문구. 전화/대면 통역 맥락에서는
# 절대 등장하지 않는 식별 시그니처(視聴/시청/watching/観看/チャンネル登録/구독/subscribe 등)만
# 잡는다. 일반 인사·감사("ありがとうございました"/"감사합니다"/"thank you")는 대화의 핵심이라
# 절대 막지 않는다(시그니처 토큰이 있을 때만 매칭). 언어 비의존 — 어느 source_lang으로
# 강제 디코딩돼도 동일 시그니처면 환각으로 본다.
_WHISPER_HALLUCINATION_SIGNATURES = (
    # 일본어 유튜브 아웃트로 계열
    re.compile(r"ご(?:視聴|清聴)\s*(?:いただき)?\s*(?:誠に)?\s*ありがとうござい(?:ました|ます)", re.U),
    re.compile(r"最後まで(?:ご視聴|ご覧)\s*(?:いただき)?", re.U),
    re.compile(r"本日は(?:ご覧|ご視聴)\s*いただき", re.U),
    re.compile(r"チャンネル登録\s*(?:と高評価\s*)?(?:を)?\s*(?:よろしく)?", re.U),
    re.compile(r"高評価\s*(?:と)?\s*チャンネル登録", re.U),
    re.compile(r"以上で(?:終わり|終わります|終了(?:します|いたします)?)", re.U),
    re.compile(r"次の(?:動画|ビデオ)で(?:お)?会いしましょう", re.U),
    re.compile(r"ご協力ありがとうござい(?:ました|ます)", re.U),
    # 한국어 유튜브 아웃트로 계열
    re.compile(r"시청\s*해?\s*주셔서\s*감사", re.U),
    re.compile(r"구독\s*(?:과|,|\s)*\s*좋아요", re.U),
    re.compile(r"구독.*부탁", re.U),
    re.compile(r"다음\s*(?:영상|시간)(?:에서)?\s*(?:만나|뵙)", re.U),
    # 한국어 STT 근접무음 환각: 실통화에서 "통역 문장"(메타 단어)·자막 크레딧이 반복 생성돼
    # 상대에게 같은 문구가 중복 발화되던 문제(전화/대면 대화엔 등장하지 않는 메타 문구만 차단).
    re.compile(r"^\s*통역\s*문장\s*[.!?]*$", re.U),
    # "통역 문장 1, 통역 문장 2, …" 반복 환각(무음 구간에서 메타 문구가 번호와 함께 반복 생성).
    re.compile(r"(?:통역\s*문장\s*\d*\s*[,，、.]?\s*){3,}", re.U),
    re.compile(r"자막\s*(?:제공|by|바이)", re.I | re.U),
    re.compile(r"자막을?\s*(?:사용|제공)(?:하였|했|합)", re.U),
    # 영어 유튜브 아웃트로 계열
    re.compile(r"thank you for watching", re.I),
    re.compile(r"thanks for watching", re.I),
    re.compile(r"please\s+(?:like|subscribe)", re.I),
    re.compile(r"subscribe to (?:my|the|our) channel", re.I),
    re.compile(r"see you (?:in the )?next (?:video|time)", re.I),
    re.compile(r"don'?t forget to subscribe", re.I),
    # 자막/전사 크레딧 환각(무음·잡음 구간에서 매우 흔함). 대면/통화 대화엔 등장하지 않는 메타 문구.
    re.compile(r"casting\s*words", re.I),
    re.compile(r"transcription\s+by", re.I),
    re.compile(r"transcribed\s+by", re.I),
    re.compile(r"subtitles?\s+by", re.I),
    re.compile(r"amara\.org", re.I),
    # 중국어 유튜브 아웃트로 계열
    re.compile(r"感谢(?:大家的)?观看", re.U),
    re.compile(r"谢谢(?:大家的?)?观看", re.U),
    re.compile(r"请(?:点赞)?(?:订阅|关注)", re.U),
    # 스칸디나비아 유튜브 아웃트로 계열(무음 구간 Whisper가 no/sv/da로 강제 디코딩하며 흔히 생성).
    # 예: "Takk for att du så med." → 통역 경로에서 영어로 번역·발화되던 환각.
    re.compile(r"takk\s+for\s+at", re.I | re.U),  # no: "takk for at(t) du så / takk for ating med" 변형 전부
    re.compile(r"tack\s+f[\u00f6o]r\s+att\s+du\s+tittade", re.I | re.U),
    re.compile(r"tak\s+fordi\s+du\s+s[\u00e5a]\s+med", re.I | re.U),
    # 독·불·서 유튜브 아웃트로/자막 크레딧 계열
    re.compile(r"vielen\s+dank\s+f[\u00fcu]rs\s+zuschauen", re.I | re.U),
    re.compile(r"danke\s+f[\u00fcu]rs\s+zuschauen", re.I | re.U),
    re.compile(r"merci\s+d'avoir\s+regard[\u00e9e]", re.I | re.U),
    re.compile(r"gracias\s+por\s+ver", re.I | re.U),
    # 자막/번역 크레딧 환각(무음 구간에서 이름과 함께 생성). 예: "Teksting av Nicolai Winther".
    # 통역/소리새 AI 경로 모두에서 발화로 누수되던 핵심 케이스. 대화엔 등장하지 않는 메타 문구만 차단.
    re.compile(r"\bteksting\s+av\b", re.I | re.U),  # no: subtitling by
    re.compile(r"\bundertekst(?:er|et|ing)?\b", re.I | re.U),  # no/da: subtitles
    re.compile(r"\btekstet\s+av\b", re.I | re.U),  # no
    re.compile(r"\boversatt\s+av\b", re.I | re.U),  # no: translated by
    re.compile(r"\bundertextning\b", re.I | re.U),  # sv
    re.compile(r"\bunterti?tel", re.I | re.U),  # de
    re.compile(r"\bsous-?titr", re.I | re.U),  # fr
    re.compile(r"\bsottotitoli\b", re.I | re.U),  # it
    re.compile(r"\bsubt[\u00edi]tulos?\b", re.I | re.U),  # es
    re.compile(r"\blegendas?\b", re.I | re.U),  # pt
    re.compile(r"\bsubtitles?\s+by\b", re.I | re.U),
    re.compile(r"\bsubtitled\s+by\b", re.I | re.U),
    re.compile(r"\bcaptions?\s+by\b", re.I | re.U),
    re.compile(r"\u5b57\u5e55", re.U),  # ja/zh: 字幕
    # 유튜브 인트로/채널 환각(무음 구간). 통역/여행 대화엔 등장하지 않는 고유 토큰만.
    # 예: "Hello everyone, welcome back to my channel, today I will show you ..."
    re.compile(r"\b(?:my|the|our)\s+channel\b", re.I | re.U),
    re.compile(r"\bwelcome back to\b", re.I | re.U),
    re.compile(r"\bthis video\b", re.I | re.U),
    re.compile(r"\bin (?:today'?s|this) video\b", re.I | re.U),
    re.compile(r"\blike and subscribe\b", re.I | re.U),
    re.compile(r"\bhit the (?:like|bell)\b", re.I | re.U),
    re.compile(r"\btoday i(?:'|\u2019)?(?:ll| will| am going to| am gonna)?\s+show you\b", re.I | re.U),
    re.compile(r"\bin this tutorial\b", re.I | re.U),
)


def _is_whisper_hallucination_phrase(transcript: str) -> bool:
    """무음/잡음에서 생성되는 영상 아웃트로 Whisper 환각인지 판정(언어 비의존).

    Whisper 환각은 종종 高신뢰도(avg_logprob 양호)로 나와 STT trust 게이트를 통과하므로,
    식별 시그니처 문구 매칭으로 별도 차단한다.
    """
    text = str(transcript or "").strip()
    if not text:
        return True
    return any(pattern.search(text) for pattern in _WHISPER_HALLUCINATION_SIGNATURES)


_WHISPER_NOISE_SCRIPT_PATTERNS = (
    re.compile(r"[\u10A0-\u10FF]"),  # Georgian
    re.compile(r"[\u0530-\u058F]"),  # Armenian
    re.compile(r"[\u1200-\u137F]"),  # Ethiopic
    re.compile(r"[\u2C00-\u2C5F]"),  # Glagolitic
)

_RELAY_LANG_CHAR_CHECKS: dict[str, re.Pattern[str]] = {
    "ko": re.compile(r"[\uAC00-\uD7A3\u3131-\u318E]"),
    "en": re.compile(r"[A-Za-z]"),
    "ja": re.compile(r"[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]"),
    "zh": re.compile(r"[\u4E00-\u9FFF]"),
    "vi": re.compile(r"[\u00C0-\u024FA-Za-z\u1E00-\u1EFF]"),
    "th": re.compile(r"[\u0E00-\u0E7F]"),
    "ar": re.compile(r"[\u0600-\u06FF]"),
    "ru": re.compile(r"[\u0400-\u04FF]"),
}

_RELAY_NEUTRAL_CHAR = re.compile(r"[\s\d\.,!?;:'\"()\[\]{}<>/\\|@#$%^&*+=~`\-—…·]")


def _normalize_relay_lang_code(lang: str | None) -> str:
    return str(lang or "").strip().lower().split("-")[0]


def _char_matches_relay_langs(char: str, langs: set[str]) -> bool:
    if _RELAY_NEUTRAL_CHAR.fullmatch(char):
        return True
    for lang in langs:
        pattern = _RELAY_LANG_CHAR_CHECKS.get(lang)
        if pattern and pattern.search(char):
            return True
        if lang not in _RELAY_LANG_CHAR_CHECKS and re.search(r"[A-Za-z\u00C0-\u024F]", char):
            return True
    return False


_WELSH_HALLUCINATION = re.compile(r"\b(?:rwy'n|rwyf|ddweud|dweud)\b", re.IGNORECASE)


def _contains_unexpected_noise_script(text: str, expected_langs: set[str]) -> bool:
    if expected_langs & {"ka", "hy", "am", "cy"}:
        return False
    if _WELSH_HALLUCINATION.search(text):
        return True
    return any(pattern.search(text) for pattern in _WHISPER_NOISE_SCRIPT_PATTERNS)


def _is_likely_gibberish_relay_transcript(
    transcript: str,
    *expected_langs: str | None,
) -> bool:
    trimmed = str(transcript or "").strip()
    if not trimmed:
        return True
    if "\ufffd" in trimmed:
        return True

    langs = {_normalize_relay_lang_code(lang) for lang in expected_langs if _normalize_relay_lang_code(lang)}
    if not langs:
        langs = {"en"}

    if _contains_unexpected_noise_script(trimmed, langs):
        return True

    compact = _RELAY_NEUTRAL_CHAR.sub("", trimmed)
    if not compact:
        return True
    if re.search(r"(.)\1{3,}", compact):
        return True

    letter_like = [char for char in compact if not _RELAY_NEUTRAL_CHAR.fullmatch(char)]
    if not letter_like:
        return True

    allowed = sum(1 for char in letter_like if _char_matches_relay_langs(char, langs))
    ratio = allowed / len(letter_like)
    # Ratio-only rejection: keep strict for obvious noise, lenient for mixed/natural speech.
    if ratio < 0.35:
        return True
    return False


def _collapse_repeated_relay_phrases(text: str, min_repeat: int = 3) -> str:
    import re

    trimmed = re.sub(r"\s+", " ", str(text or "").strip())
    if not trimmed:
        return ""
    sentence_parts = [
        part.strip().rstrip(".!?。")
        for part in re.split(r"\.\s+", trimmed)
        if part.strip()
    ]
    if len(sentence_parts) >= min_repeat:
        first_norm = sentence_parts[0].casefold()
        if all(part.casefold() == first_norm for part in sentence_parts):
            return sentence_parts[0]
    comma_parts = [part.strip() for part in trimmed.split(", ") if part.strip()]
    if len(comma_parts) >= min_repeat:
        first_norm = comma_parts[0].casefold()
        if all(part.casefold() == first_norm for part in comma_parts):
            return comma_parts[0]
    return trimmed


@router.post("/translate", tags=["mobile-public"])
async def mobile_translate(payload: _MobileTranslateRequest):
    """WorldLinco 모바일 앱 전용 번역 엔드포인트. 소리새와 완전 독립. 50개 언어 지원."""
    from backend.services.nadotongryoksa.translator import (
        NadoTranslator,
        SUPPORTED_LANGUAGES,
    )

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text 필수")

    from_lang = payload.from_lang.lower().strip()
    to_lang = payload.to_lang.lower().strip()

    if from_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 출발 언어: {from_lang}",
        )
    if to_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도착 언어: {to_lang}",
        )

    try:
        translator = NadoTranslator.get_instance()
        translated = translator.translate(
            text,
            from_lang=from_lang,
            to_lang=to_lang,
            region_hint=payload.region_hint,
        )
        return {
            "translated": translated,
            "engine": "nado",
            "from": from_lang,
            "to": to_lang,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"번역 오류: {exc}") from exc


async def _voip_voice_translate_core(payload: _MobileVoiceTranslateRequest):
    """VoIP 통화 음성 릴레이 전용 코어(STT→번역→TTS). 대면(face) 코어와 100% 독립.

    완전 채널 격리(사용자 요구) — 이 함수의 수정/버그는 대면 통역 경로에 절대 영향을 주지
    않는다(코드 경로 물리 분리). transcript 직접 입력 또는 audio_base64 STT를 지원한다.
    """
    from backend.services.nadotongryoksa.translator import (
        NadoTranslator,
        SUPPORTED_LANGUAGES,
    )

    from_lang = payload.from_lang.lower().strip()
    to_lang = payload.to_lang.lower().strip()
    bilingual_mode = _resolve_voice_channel_mode(payload)
    channel_mode = "bilingual" if bilingual_mode else "designated"
    # V.2 상관 ID — 클라이언트가 보낸 고유 ID를 그대로 이어받고(echo), 없으면 발급한다.
    # 이 한 줄로 기능 ID 자동 매핑→셀프 서빙→전송(딜리버리)→음성 발화가 동일 ID로 자동 연결된다.
    default_feature = (
        FEATURE_IDS["face_interpret"]
        if bilingual_mode
        else FEATURE_IDS["voip_voice_relay"]
    )
    correlation_id = ensure_correlation_id(
        payload.correlation_id,
        payload.feature_id or default_feature,
    )
    lang_a = _normalize_voice_lang_code(payload.lang_a or from_lang) or from_lang
    lang_b = _normalize_voice_lang_code(payload.lang_b or to_lang) or to_lang
    if bilingual_mode:
        from_lang = lang_a
        to_lang = lang_b

    if from_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 출발 언어: {from_lang}",
        )
    if to_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도착 언어: {to_lang}",
        )
    if bilingual_mode:
        if lang_a == lang_b:
            raise HTTPException(
                status_code=400,
                detail="대면 통역에는 서로 다른 두 언어가 필요합니다.",
            )
        if lang_a not in SUPPORTED_LANGUAGES or lang_b not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail="대면 통역 언어 쌍이 지원 범위를 벗어났습니다.",
            )

    def normalize_voice_lang(value: str | None) -> str | None:
        return _normalize_voice_lang_code(value)

    transcript = (payload.transcript or "").strip()
    detected_language = normalize_voice_lang(
        payload.language,
    ) or normalize_voice_lang(from_lang)
    stt_meta: dict[str, object] = {}
    # [V2 감정 E1] register 제어용 PCM16 오디오 보관(designated/VOIP 경로만, best-effort).
    relay_audio_bytes: bytes | None = None
    if not transcript:
        audio_base64 = (payload.audio_base64 or "").strip()
        if not audio_base64:
            raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")
        try:
            audio_bytes = _decode_mobile_voice_audio(audio_base64)
            relay_audio_bytes = audio_bytes
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            if bilingual_mode:
                transcript, detected_language, stt_meta = await asyncio.to_thread(
                    _transcribe_bilingual_voice_audio,
                    audio_bytes,
                    lang_a,
                    lang_b,
                )
            else:
                # 지정 언어 모드: 화자 언어를 이미 알고 있으므로 항상 from_lang로 고정한다.
                language_hint = from_lang
                transcript, detected_language, stt_meta = await asyncio.to_thread(
                    _transcribe_mobile_voice_audio,
                    audio_bytes,
                    language_hint,
                    from_lang,
                    True,
                )
        except Exception as exc:
            message = str(exc)
            status_code = 422 if (
                "너무 짧습니다" in message
                or "음성이 감지되지 않았습니다" in message
            ) else 400
            raise HTTPException(
                status_code=status_code,
                detail=message if status_code == 422 else f"STT 실패: {message}",
            ) from exc

    detected_from_lang = normalize_voice_lang(detected_language)
    if not detected_from_lang:
        detected_from_lang = normalize_voice_lang(from_lang)

    if bilingual_mode:
        routed = await asyncio.to_thread(
            _resolve_bilingual_route,
            detected_language=detected_from_lang,
            transcript=transcript,
            lang_a=lang_a,
            lang_b=lang_b,
        )
        if routed is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{lang_a}/{lang_b} 중 하나로 말씀해 주세요. "
                    "감지된 언어가 대면 통역 언어 쌍과 일치하지 않습니다."
                ),
            )
        effective_from_lang, effective_to_lang = routed
    else:
        # 지정 언어(designated) 모드 — VoIP/채팅.
        # 화자의 언어를 이미 알고 있고 STT도 from_lang으로 고정(lock_language)했으므로
        # Whisper의 언어 추정값으로 거부하지 않는다. 언어 불일치 422 거부는 제거되었다.
        # (지정 언어로 정상 발화했는데 짧은 음절을 오감지해 듣기가 멈추던 문제를 원천 차단)
        # 실제 잡음/무음은 아래 gibberish 필터가 별도로 처리한다.
        detected_from_lang = from_lang
        effective_from_lang = from_lang
        effective_to_lang = to_lang

    # Silence hallucination filtering is applied on mobile for meter-dead / fixed-interval
    # captures only. Backend accepts short natural utterances from real speech segments.

    if _is_likely_gibberish_relay_transcript(
        transcript,
        effective_from_lang,
        effective_to_lang,
        from_lang,
        to_lang,
    ):
        logger.info(
            "[voice-translate] rejected gibberish transcript from=%s to=%s text=%r",
            effective_from_lang,
            effective_to_lang,
            transcript,
        )
        raise HTTPException(
            status_code=422,
            detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
        )

    # Whisper 무음/잡음 환각(영상 아웃트로 계열) 차단 — designated/bilingual 공통 길목.
    # 한국어 발화를 ja로 강제 디코딩할 때 "ご視聴ありがとうございました" 등이 나와 번역되어
    # "좋은 아침입니다" 같은 엉뚱한 발화로 이어지던 문제를 원천 차단한다.
    if _is_whisper_hallucination_phrase(transcript):
        logger.info(
            "[voice-translate] rejected whisper hallucination from=%s to=%s text=%r",
            effective_from_lang,
            effective_to_lang,
            transcript,
        )
        raise HTTPException(
            status_code=422,
            detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
        )

    transcript = _collapse_repeated_relay_phrases(transcript)

    logger.info(
        "[voice-translate] cid=%s mode=%s stt from=%s to=%s detected=%s transcript=%r",
        correlation_id,
        channel_mode,
        from_lang,
        to_lang,
        detected_from_lang or effective_from_lang,
        (transcript[:120] + "…") if len(transcript) > 120 else transcript,
    )

    try:
        # [V2 Session Core → #9 Meaning] designated(VOIP) 모드에서만 세션 맥락을 MT 보조
        # 힌트로 주입(대면/bilingual 경로는 동결 — 미주입). flag off / session_id 없음 / 빈
        # 맥락이면 None → 기존 동작과 동일.
        context_hint = None
        if not bilingual_mode and payload.session_id:
            from backend.communication.session import integration as _session_integration

            context_hint = _session_integration.build_context_hint(payload.session_id)
        # [V2 감정 E1] designated(VOIP) 모드에서 감정→register(존댓말/어휘) 지시문을 MT 힌트에
        # 합성(best-effort, COMM_V2_EMOTION_REGISTER off / 중립·저신뢰면 no-op → 기존과 동일).
        if not bilingual_mode and relay_audio_bytes:
            from backend.communication.emotion import integration as _emotion_integration
            from backend.communication.emotion.register import compose_hint as _compose_hint

            register_hint = _emotion_integration.build_register_hint_from_pcm16(
                relay_audio_bytes, target_lang=effective_to_lang
            )
            if register_hint:
                context_hint = _compose_hint(context_hint, register_hint)
        translator = NadoTranslator.get_instance()
        _translate_kwargs: dict[str, object] = {
            "from_lang": effective_from_lang,
            "to_lang": effective_to_lang,
            "region_hint": payload.region_hint,
        }
        # 맥락이 실제로 있을 때만 kwarg 전달 → 무맥락 시 기존 호출과 100% 동일(테스트 더블 포함).
        if context_hint:
            _translate_kwargs["context_hint"] = context_hint
        translated = translator.translate(transcript, **_translate_kwargs)
        translated = _collapse_repeated_relay_phrases(translated)
        if _is_likely_gibberish_relay_transcript(
            translated,
            effective_from_lang,
            effective_to_lang,
            from_lang,
            to_lang,
        ):
            logger.info(
                "[voice-translate] rejected gibberish translation from=%s to=%s text=%r",
                effective_from_lang,
                effective_to_lang,
                translated,
            )
            raise HTTPException(
                status_code=422,
                detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
            )
        logger.info(
            "[voice-translate] cid=%s translated from=%s to=%s text=%r",
            correlation_id,
            effective_from_lang,
            effective_to_lang,
            (translated[:120] + "…") if len(translated) > 120 else translated,
        )
        # [V2 감정 E3] 표현형 TTS 운율 플랜(카나리, COMM_V2_EMOTION_EXPRESSIVE_TTS).
        # 입력 PCM16 감정 → rate/pitch/volume 델타(제품 기본속도 기준). off / 중립·저신뢰면
        # None → 비표현형(기존) 합성과 100% 동일. 음색 전이 없이 운율만 "재현"(설계 E3).
        expressive_plan = None
        if not bilingual_mode and relay_audio_bytes:
            from backend.communication.emotion import budget as _expr_budget
            from backend.communication.emotion import integration as _emotion_integration
            from backend.llm.voice_gateway import edge_tts_base_rate_pct as _base_rate_pct

            expressive_plan = _emotion_integration.build_expressive_tts_plan_from_pcm16(
                relay_audio_bytes, base_rate_pct=_base_rate_pct()
            )
            # [E3 §6 지연 예산] 표현형 합성 P95 가 예산(COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS,
            # 기본 2000ms) 초과면 서킷브레이커가 표현형을 차단 → 비표현형 폴백(회복 시 자동 복귀).
            if expressive_plan is not None and not _expr_budget.expressive_allowed():
                logger.info(
                    "[voice-translate] cid=%s EXPRESSIVE_TTS budget-fallback (p95=%sms)",
                    correlation_id,
                    _expr_budget.p95_ms(),
                )
                expressive_plan = None
            elif expressive_plan is not None:
                logger.info(
                    "[voice-translate] cid=%s EXPRESSIVE_TTS %s",
                    correlation_id,
                    expressive_plan.to_dict(),
                )
        audio_base64 = None
        audio_format = None
        if not payload.device_tts:
            _tts_t0 = time.perf_counter()
            try:
                (
                    synthesized_audio_base64,
                    synthesized_audio_format,
                ) = await asyncio.to_thread(
                    _synthesize_tts,
                    translated,
                    effective_to_lang,
                    expressive=expressive_plan,
                )
                if synthesized_audio_base64 and str(
                    synthesized_audio_format or ""
                ).startswith("audio/"):
                    audio_base64 = synthesized_audio_base64
                    audio_format = synthesized_audio_format
            except Exception:
                audio_base64 = None
                audio_format = None
            finally:
                # [E3] TTS 합성 지연을 메트릭/서킷브레이커에 기록(표현형 라벨, best-effort).
                try:
                    from backend.communication.emotion import budget as _expr_budget

                    _expr_budget.observe_tts_latency(
                        time.perf_counter() - _tts_t0, expressive=expressive_plan is not None
                    )
                except Exception:
                    pass
        if audio_base64:
            logger.info(
                "[voice-translate] cid=%s synthesized server_audio (%s)",
                correlation_id,
                audio_format,
            )
        # [V2 감정 E2] 원문(입력 PCM16)↔출력(TTS) 감정을 추정해 EMOTION_PROBE 페이로드 생성.
        # 응답에 동봉 → 클라가 로그캣 emit → 평가 하니스가 감정 보존도를 실데이터로 산출.
        # COMM_V2_EMOTION_PROBE off / 입력·TTS 어느 한쪽이라도 없으면 no-op(기존과 동일).
        emotion_probe = None
        if not bilingual_mode and relay_audio_bytes and audio_base64:
            from backend.communication.emotion import integration as _emotion_integration

            try:
                _out_audio_bytes = base64.b64decode(audio_base64)
            except Exception:
                _out_audio_bytes = None
            emotion_probe = await asyncio.to_thread(
                _emotion_integration.build_emotion_probe,
                relay_audio_bytes,
                _out_audio_bytes,
            )
            if emotion_probe:
                logger.info(
                    "[voice-translate] cid=%s EMOTION_PROBE %s",
                    correlation_id,
                    emotion_probe,
                )
        # [V2 Session Core] relay 1턴 기록(best-effort, session_id 없거나 flag off면 no-op).
        if payload.session_id:
            from backend.communication.session import integration as _session_integration

            _session_integration.record_relay_turn(
                payload.session_id,
                source_lang=effective_from_lang,
                target_lang=effective_to_lang,
                source_text=transcript,
                translated_text=translated,
            )
        return {
            "original_text": transcript,
            "translated": translated,
            "engine": "nado-voice",
            "from": effective_from_lang,
            "to": effective_to_lang,
            "detected_language": detected_from_lang or effective_from_lang,
            "audio_url": None,
            "audio_base64": audio_base64,
            "audio_format": audio_format,
            "tts_delivery": "server_audio" if audio_base64 else "device_speech",
            # [V2 감정 E2] EMOTION_PROBE 페이로드(없으면 None → 클라 emit 생략, 하위호환).
            "emotion": emotion_probe,
            "stt_trust": str(stt_meta.get("stt_trust") or "high"),
            "stt_avg_logprob": float(stt_meta.get("avg_logprob", 0.0)) if stt_meta else None,
            # V.2 ID 백본: 동일 상관 ID를 echo 해 클라이언트가 발화 단계까지 자동 연결한다.
            "correlation_id": correlation_id,
            "utterance_id": payload.utterance_id or correlation_id,
            "seq_id": payload.seq_id,
            "chunk_index": payload.chunk_index,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"음성 통역 오류: {exc}",
        ) from exc


async def _face_voice_translate_core(payload: _MobileVoiceTranslateRequest):
    """여행 대면 통역 전용 코어(STT→번역→TTS). VoIP 코어와 100% 독립.

    완전 채널 격리(사용자 요구) — 이 함수의 수정/버그는 VoIP 통화 통역 경로에 절대 영향을
    주지 않는다(코드 경로 물리 분리). bilingual 자동 감지 및 수동 단방향(designated)을 지원한다.
    """
    from backend.services.nadotongryoksa.translator import (
        NadoTranslator,
        SUPPORTED_LANGUAGES,
    )

    from_lang = payload.from_lang.lower().strip()
    to_lang = payload.to_lang.lower().strip()
    bilingual_mode = _resolve_voice_channel_mode(payload)
    channel_mode = "bilingual" if bilingual_mode else "designated"
    # V.2 상관 ID — 클라이언트가 보낸 고유 ID를 그대로 이어받고(echo), 없으면 발급한다.
    # 이 한 줄로 기능 ID 자동 매핑→셀프 서빙→전송(딜리버리)→음성 발화가 동일 ID로 자동 연결된다.
    default_feature = (
        FEATURE_IDS["face_interpret"]
        if bilingual_mode
        else FEATURE_IDS["voip_voice_relay"]
    )
    correlation_id = ensure_correlation_id(
        payload.correlation_id,
        payload.feature_id or default_feature,
    )
    lang_a = _normalize_voice_lang_code(payload.lang_a or from_lang) or from_lang
    lang_b = _normalize_voice_lang_code(payload.lang_b or to_lang) or to_lang
    if bilingual_mode:
        from_lang = lang_a
        to_lang = lang_b

    if from_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 출발 언어: {from_lang}",
        )
    if to_lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 도착 언어: {to_lang}",
        )
    if bilingual_mode:
        if lang_a == lang_b:
            raise HTTPException(
                status_code=400,
                detail="대면 통역에는 서로 다른 두 언어가 필요합니다.",
            )
        if lang_a not in SUPPORTED_LANGUAGES or lang_b not in SUPPORTED_LANGUAGES:
            raise HTTPException(
                status_code=400,
                detail="대면 통역 언어 쌍이 지원 범위를 벗어났습니다.",
            )

    def normalize_voice_lang(value: str | None) -> str | None:
        return _normalize_voice_lang_code(value)

    transcript = (payload.transcript or "").strip()
    detected_language = normalize_voice_lang(
        payload.language,
    ) or normalize_voice_lang(from_lang)
    stt_meta: dict[str, object] = {}
    # [V2 감정 E1] register 제어용 PCM16 오디오 보관(designated 경로만, best-effort).
    relay_audio_bytes: bytes | None = None
    if not transcript:
        audio_base64 = (payload.audio_base64 or "").strip()
        if not audio_base64:
            raise HTTPException(status_code=400, detail="텍스트 또는 오디오 입력이 필요합니다")
        try:
            audio_bytes = _decode_mobile_voice_audio(audio_base64)
            relay_audio_bytes = audio_bytes
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            if bilingual_mode:
                transcript, detected_language, stt_meta = await asyncio.to_thread(
                    _transcribe_bilingual_voice_audio,
                    audio_bytes,
                    lang_a,
                    lang_b,
                )
            else:
                # 지정 언어 모드: 화자 언어를 이미 알고 있으므로 항상 from_lang로 고정한다.
                language_hint = from_lang
                transcript, detected_language, stt_meta = await asyncio.to_thread(
                    _transcribe_mobile_voice_audio,
                    audio_bytes,
                    language_hint,
                    from_lang,
                    True,
                )
        except Exception as exc:
            message = str(exc)
            status_code = 422 if (
                "너무 짧습니다" in message
                or "음성이 감지되지 않았습니다" in message
            ) else 400
            raise HTTPException(
                status_code=status_code,
                detail=message if status_code == 422 else f"STT 실패: {message}",
            ) from exc

    detected_from_lang = normalize_voice_lang(detected_language)
    if not detected_from_lang:
        detected_from_lang = normalize_voice_lang(from_lang)

    if bilingual_mode:
        routed = await asyncio.to_thread(
            _resolve_bilingual_route,
            detected_language=detected_from_lang,
            transcript=transcript,
            lang_a=lang_a,
            lang_b=lang_b,
        )
        if routed is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"{lang_a}/{lang_b} 중 하나로 말씀해 주세요. "
                    "감지된 언어가 대면 통역 언어 쌍과 일치하지 않습니다."
                ),
            )
        effective_from_lang, effective_to_lang = routed
    else:
        # 지정 언어(designated) 모드 — 대면 화면의 수동 단방향.
        # 화자의 언어를 이미 알고 있고 STT도 from_lang으로 고정(lock_language)했으므로
        # Whisper의 언어 추정값으로 거부하지 않는다. 언어 불일치 422 거부는 제거되었다.
        # (지정 언어로 정상 발화했는데 짧은 음절을 오감지해 듣기가 멈추던 문제를 원천 차단)
        # 실제 잡음/무음은 아래 gibberish 필터가 별도로 처리한다.
        detected_from_lang = from_lang
        effective_from_lang = from_lang
        effective_to_lang = to_lang

    # Silence hallucination filtering is applied on mobile for meter-dead / fixed-interval
    # captures only. Backend accepts short natural utterances from real speech segments.

    if _is_likely_gibberish_relay_transcript(
        transcript,
        effective_from_lang,
        effective_to_lang,
        from_lang,
        to_lang,
    ):
        logger.info(
            "[face-voice-translate] rejected gibberish transcript from=%s to=%s text=%r",
            effective_from_lang,
            effective_to_lang,
            transcript,
        )
        raise HTTPException(
            status_code=422,
            detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
        )

    # Whisper 무음/잡음 환각(영상 아웃트로 계열) 차단 — designated/bilingual 공통 길목.
    # 한국어 발화를 ja로 강제 디코딩할 때 "ご視聴ありがとうございました" 등이 나와 번역되어
    # "좋은 아침입니다" 같은 엉뚱한 발화로 이어지던 문제를 원천 차단한다.
    if _is_whisper_hallucination_phrase(transcript):
        logger.info(
            "[face-voice-translate] rejected whisper hallucination from=%s to=%s text=%r",
            effective_from_lang,
            effective_to_lang,
            transcript,
        )
        raise HTTPException(
            status_code=422,
            detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
        )

    transcript = _collapse_repeated_relay_phrases(transcript)

    logger.info(
        "[face-voice-translate] cid=%s mode=%s stt from=%s to=%s detected=%s transcript=%r",
        correlation_id,
        channel_mode,
        from_lang,
        to_lang,
        detected_from_lang or effective_from_lang,
        (transcript[:120] + "…") if len(transcript) > 120 else transcript,
    )

    try:
        # [V2 Session Core → #9 Meaning] designated 모드에서만 세션 맥락을 MT 보조
        # 힌트로 주입(bilingual 경로는 동결 — 미주입). flag off / session_id 없음 / 빈
        # 맥락이면 None → 기존 동작과 동일.
        context_hint = None
        if not bilingual_mode and payload.session_id:
            from backend.communication.session import integration as _session_integration

            context_hint = _session_integration.build_context_hint(payload.session_id)
        # [V2 감정 E1] designated 모드에서 감정→register(존댓말/어휘) 지시문을 MT 힌트에
        # 합성(best-effort, COMM_V2_EMOTION_REGISTER off / 중립·저신뢰면 no-op → 기존과 동일).
        if not bilingual_mode and relay_audio_bytes:
            from backend.communication.emotion import integration as _emotion_integration
            from backend.communication.emotion.register import compose_hint as _compose_hint

            register_hint = _emotion_integration.build_register_hint_from_pcm16(
                relay_audio_bytes, target_lang=effective_to_lang
            )
            if register_hint:
                context_hint = _compose_hint(context_hint, register_hint)
        translator = NadoTranslator.get_instance()
        _translate_kwargs: dict[str, object] = {
            "from_lang": effective_from_lang,
            "to_lang": effective_to_lang,
            "region_hint": payload.region_hint,
        }
        # 맥락이 실제로 있을 때만 kwarg 전달 → 무맥락 시 기존 호출과 100% 동일(테스트 더블 포함).
        if context_hint:
            _translate_kwargs["context_hint"] = context_hint
        translated = translator.translate(transcript, **_translate_kwargs)
        translated = _collapse_repeated_relay_phrases(translated)
        if _is_likely_gibberish_relay_transcript(
            translated,
            effective_from_lang,
            effective_to_lang,
            from_lang,
            to_lang,
        ):
            logger.info(
                "[face-voice-translate] rejected gibberish translation from=%s to=%s text=%r",
                effective_from_lang,
                effective_to_lang,
                translated,
            )
            raise HTTPException(
                status_code=422,
                detail="음성이 감지되지 않았습니다. 다시 말씀해 주세요.",
            )
        logger.info(
            "[face-voice-translate] cid=%s translated from=%s to=%s text=%r",
            correlation_id,
            effective_from_lang,
            effective_to_lang,
            (translated[:120] + "…") if len(translated) > 120 else translated,
        )
        # [V2 감정 E3] 표현형 TTS 운율 플랜(카나리, COMM_V2_EMOTION_EXPRESSIVE_TTS).
        # 입력 PCM16 감정 → rate/pitch/volume 델타(제품 기본속도 기준). off / 중립·저신뢰면
        # None → 비표현형(기존) 합성과 100% 동일. 음색 전이 없이 운율만 "재현"(설계 E3).
        expressive_plan = None
        if not bilingual_mode and relay_audio_bytes:
            from backend.communication.emotion import budget as _expr_budget
            from backend.communication.emotion import integration as _emotion_integration
            from backend.llm.voice_gateway import edge_tts_base_rate_pct as _base_rate_pct

            expressive_plan = _emotion_integration.build_expressive_tts_plan_from_pcm16(
                relay_audio_bytes, base_rate_pct=_base_rate_pct()
            )
            # [E3 §6 지연 예산] 표현형 합성 P95 가 예산(COMM_V2_EMOTION_EXPRESSIVE_TTS_MAX_MS,
            # 기본 2000ms) 초과면 서킷브레이커가 표현형을 차단 → 비표현형 폴백(회복 시 자동 복귀).
            if expressive_plan is not None and not _expr_budget.expressive_allowed():
                logger.info(
                    "[face-voice-translate] cid=%s EXPRESSIVE_TTS budget-fallback (p95=%sms)",
                    correlation_id,
                    _expr_budget.p95_ms(),
                )
                expressive_plan = None
            elif expressive_plan is not None:
                logger.info(
                    "[face-voice-translate] cid=%s EXPRESSIVE_TTS %s",
                    correlation_id,
                    expressive_plan.to_dict(),
                )
        audio_base64 = None
        audio_format = None
        if not payload.device_tts:
            _tts_t0 = time.perf_counter()
            try:
                (
                    synthesized_audio_base64,
                    synthesized_audio_format,
                ) = await asyncio.to_thread(
                    _synthesize_tts,
                    translated,
                    effective_to_lang,
                    expressive=expressive_plan,
                )
                if synthesized_audio_base64 and str(
                    synthesized_audio_format or ""
                ).startswith("audio/"):
                    audio_base64 = synthesized_audio_base64
                    audio_format = synthesized_audio_format
            except Exception:
                audio_base64 = None
                audio_format = None
            finally:
                # [E3] TTS 합성 지연을 메트릭/서킷브레이커에 기록(표현형 라벨, best-effort).
                try:
                    from backend.communication.emotion import budget as _expr_budget

                    _expr_budget.observe_tts_latency(
                        time.perf_counter() - _tts_t0, expressive=expressive_plan is not None
                    )
                except Exception:
                    pass
        if audio_base64:
            logger.info(
                "[face-voice-translate] cid=%s synthesized server_audio (%s)",
                correlation_id,
                audio_format,
            )
        # [V2 감정 E2] 원문(입력 PCM16)↔출력(TTS) 감정을 추정해 EMOTION_PROBE 페이로드 생성.
        emotion_probe = None
        if not bilingual_mode and relay_audio_bytes and audio_base64:
            from backend.communication.emotion import integration as _emotion_integration

            try:
                _out_audio_bytes = base64.b64decode(audio_base64)
            except Exception:
                _out_audio_bytes = None
            emotion_probe = await asyncio.to_thread(
                _emotion_integration.build_emotion_probe,
                relay_audio_bytes,
                _out_audio_bytes,
            )
            if emotion_probe:
                logger.info(
                    "[face-voice-translate] cid=%s EMOTION_PROBE %s",
                    correlation_id,
                    emotion_probe,
                )
        # [V2 Session Core] relay 1턴 기록(best-effort, session_id 없거나 flag off면 no-op).
        if payload.session_id:
            from backend.communication.session import integration as _session_integration

            _session_integration.record_relay_turn(
                payload.session_id,
                source_lang=effective_from_lang,
                target_lang=effective_to_lang,
                source_text=transcript,
                translated_text=translated,
            )
        return {
            "original_text": transcript,
            "translated": translated,
            "engine": "nado-voice",
            "from": effective_from_lang,
            "to": effective_to_lang,
            "detected_language": detected_from_lang or effective_from_lang,
            "audio_url": None,
            "audio_base64": audio_base64,
            "audio_format": audio_format,
            "tts_delivery": "server_audio" if audio_base64 else "device_speech",
            # [V2 감정 E2] EMOTION_PROBE 페이로드(없으면 None → 클라 emit 생략, 하위호환).
            "emotion": emotion_probe,
            "stt_trust": str(stt_meta.get("stt_trust") or "high"),
            "stt_avg_logprob": float(stt_meta.get("avg_logprob", 0.0)) if stt_meta else None,
            # V.2 ID 백본: 동일 상관 ID를 echo 해 클라이언트가 발화 단계까지 자동 연결한다.
            "correlation_id": correlation_id,
            "utterance_id": payload.utterance_id or correlation_id,
            "seq_id": payload.seq_id,
            "chunk_index": payload.chunk_index,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"음성 통역 오류: {exc}",
        ) from exc


@router.post("/voip/voice-translate", tags=["mobile-public", "voip"])
async def voip_voice_translate(payload: _VoipVoiceTranslateRequest):
    """VoIP 통화 음성 릴레이 전용 통역 라우트(designated). 대면과 계약 격리.

    VoIP 전용 필드(seq_id·chunk_index·session_id)는 이 라우트에서만 검증되며, 코어 로직도
    대면과 물리적으로 분리(``_voip_voice_translate_core``)되어 100% 독립이다.
    """
    return await _voip_voice_translate_core(payload.to_core())


@router.post("/face/voice-translate", tags=["mobile-public", "face"])
async def face_voice_translate(payload: _FaceVoiceTranslateRequest):
    """여행 대면 통역 전용 통역 라우트(bilingual 자동 감지 또는 수동 designated).

    VoIP와 계약 격리 + 코어 로직 물리 분리(``_face_voice_translate_core``)로 100% 독립이다.
    """
    return await _face_voice_translate_core(payload.to_core())


@router.post("/voice-translate", tags=["mobile-public"])
async def mobile_voice_translate(payload: _MobileVoiceTranslateRequest):
    """레거시 공유 음성 통역 엔드포인트(하위호환 유지).

    이미 배포된 앱(예: build 157)이 이 경로를 호출하므로 제거하지 않는다. 신규 빌드는
    채널별 분리 라우트(``/voip/voice-translate``·``/face/voice-translate``)를 사용한다.

    레거시는 자체 로직을 두지 않고 mode 로 분기해 채널 코어로 위임한다 — 따라서 레거시
    경로도 채널 격리를 그대로 따른다(한 채널 코어 버그가 다른 채널에 전파되지 않음).
    """
    if _resolve_voice_channel_mode(payload):
        return await _face_voice_translate_core(payload)
    return await _voip_voice_translate_core(payload)


@router.get("/translate/languages", tags=["mobile-public"])
async def get_supported_languages():
    """WorldLinco 지원 언어 목록 반환 (50개국어)."""
    from backend.services.nadotongryoksa.translator import SUPPORTED_LANGUAGES

    return {
        "languages": SUPPORTED_LANGUAGES,
        "count": len(SUPPORTED_LANGUAGES),
    }


@router.get("/translate/dialect-profiles", tags=["mobile-public"])
async def get_supported_dialect_profiles():
    from backend.services.nadotongryoksa.translator import (
        SUPPORTED_DIALECT_COUNTRY_PROFILES,
    )

    return {
        "profiles": SUPPORTED_DIALECT_COUNTRY_PROFILES,
        "count": len(SUPPORTED_DIALECT_COUNTRY_PROFILES),
    }
