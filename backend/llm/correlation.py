"""WorldLinco V.2 오케스트레이터 상관 ID(correlation id) 백본 — 백엔드 SSOT.

모든 기능(VOIP 음성 릴레이 / 대면 통역 / 채팅 번역 / 마켓 TTS / OCR / 가사 등)이
단일 고유 ID로 ``기능 ID 자동 매핑 → 셀프 서빙 → 전송(딜리버리) → 음성 발화`` 전 구간을
자동으로 묶을 수 있도록, 공통 ID 스킴과 echo 규칙을 한 곳에서 정의한다.

ID 포맷(클라이언트 ``src/features/correlation/correlationId.ts`` 와 동일):
    ``{feature_id}-{base36(epoch_ms)}-{rand6}``
    예) ``voip.voice_relay-l9x2k3-a3f9c2``

- ``feature_id`` 는 접두로 박혀 어느 기능에서 왔는지 자가 식별된다(스스로 ID를 찾아 붙음).
- 시간 + 난수 조합으로 전역 충돌이 사실상 불가능하다.
- 클라이언트가 보낸 ID 는 그대로 echo 하고, 없으면 서버가 동일 스킴으로 새로 발급한다.
"""

from __future__ import annotations

import re
import secrets
import time

# 기능 ID 레지스트리 — 클라이언트 FEATURE_IDS 와 1:1 정합되어야 한다.
FEATURE_IDS: dict[str, str] = {
    "voip_voice_relay": "voip.voice_relay",
    "face_interpret": "face.interpret",
    "chat_translate": "chat.translate",
    "voice_synthesize": "tts.synthesize",
    "image_translate": "ocr.image",
    "song_translate": "song.translate",
    "orchestrate": "orchestrate.voice",
}

_VALID_FEATURE_IDS = set(FEATURE_IDS.values())
_DEFAULT_FEATURE_ID = FEATURE_IDS["orchestrate"]

# {feature}-{ts36}-{rand} ; feature 는 영숫자/점/언더스코어, 전체 길이 안전 상한.
_CORRELATION_RE = re.compile(r"^[a-zA-Z0-9._]{1,48}-[a-z0-9]{1,12}-[a-z0-9]{4,12}$")
_MAX_LEN = 128

_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def _base36(value: int) -> str:
    if value <= 0:
        return "0"
    out: list[str] = []
    while value > 0:
        value, rem = divmod(value, 36)
        out.append(_ALPHABET[rem])
    return "".join(reversed(out))


def normalize_feature_id(feature_id: str | None) -> str:
    """알 수 없는 feature_id 는 기본값으로 안전 보정한다."""
    candidate = str(feature_id or "").strip()
    if candidate in _VALID_FEATURE_IDS:
        return candidate
    return _DEFAULT_FEATURE_ID


def new_correlation_id(feature_id: str | None = None) -> str:
    """주어진 기능에 대한 새 상관 ID를 발급한다."""
    feature = normalize_feature_id(feature_id)
    ts36 = _base36(int(time.time() * 1000))
    rand = secrets.token_hex(3)  # 6 hex chars
    return f"{feature}-{ts36}-{rand}"


def is_valid_correlation_id(value: str | None) -> bool:
    if not value:
        return False
    text = str(value).strip()
    return len(text) <= _MAX_LEN and bool(_CORRELATION_RE.match(text))


def feature_of(correlation_id: str | None) -> str:
    """상관 ID 접두에서 feature_id 를 복원한다(스스로 자기 기능을 식별)."""
    if not correlation_id:
        return _DEFAULT_FEATURE_ID
    head = str(correlation_id).split("-", 1)[0]
    return normalize_feature_id(head)


def ensure_correlation_id(
    correlation_id: str | None,
    feature_id: str | None = None,
) -> str:
    """클라이언트가 보낸 유효한 ID는 그대로 쓰고(echo), 없으면 새로 발급한다.

    잘못된 형식이 들어오면 위조/오염 방지를 위해 서버가 재발급한다.
    """
    if is_valid_correlation_id(correlation_id):
        return str(correlation_id).strip()
    # feature 힌트가 없으면 들어온 ID 접두에서라도 추정한다.
    resolved_feature = feature_id or feature_of(correlation_id)
    return new_correlation_id(resolved_feature)
