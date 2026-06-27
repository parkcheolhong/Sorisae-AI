"""감정 → MT register(존댓말/어휘·어조) 제어 — E1.

[`EMOTION_EXPRESSIVE_DESIGN.md`](../../../docs/worldlinco-v2/EMOTION_EXPRESSIVE_DESIGN.md) §5 E1.
E0 SER 추정(arousal/valence/범주)을 **MT 프롬프트 보조 지시문**으로 변환한다. 음색 전이 없이
어조·격식만 제어해 체감을 개선(특히 한국어/일본어 존댓말 일관성).

순수 함수(부수효과 없음). 중립/저신뢰면 ``None`` → MT는 기존과 동일하게 동작.
"""

from __future__ import annotations

from typing import Optional

from .models import EmotionEstimate, EmotionLabel

# 존댓말/격식 제어가 특히 유효한 대상 언어(높임 체계 보유).
_HONORIFIC_LANGS = {"ko", "ja"}

# 라벨 → (한국어/일본어 대상용 지시문, 그 외 언어용 지시문).
_DIRECTIVES: dict[EmotionLabel, tuple[str, str]] = {
    EmotionLabel.ANGRY: (
        "화자가 화났거나 격앙된 상태입니다. 정중하고 차분한 존댓말과 공손한 어휘로, "
        "도발적이지 않게 완화된 어조로 번역하세요.",
        "The speaker sounds angry or agitated. Translate calmly and politely, "
        "de-escalating the tone without adding hostility.",
    ),
    EmotionLabel.SAD: (
        "화자가 슬프거나 가라앉은 상태입니다. 공감적이고 부드러운 존댓말 어조로 번역하세요.",
        "The speaker sounds sad or subdued. Translate with a gentle, empathetic tone.",
    ),
    EmotionLabel.HAPPY: (
        "화자가 기쁘고 활기찬 상태입니다. 밝고 긍정적인 어조를 살려 자연스럽게 번역하세요.",
        "The speaker sounds happy and upbeat. Preserve a bright, positive tone naturally.",
    ),
    EmotionLabel.CALM: (
        "화자가 차분한 상태입니다. 정중하고 안정적인 존댓말 어조를 유지하세요.",
        "The speaker sounds calm. Keep a polite, steady tone.",
    ),
}


def register_directive_from_emotion(
    estimate: Optional[EmotionEstimate],
    *,
    target_lang: Optional[str] = None,
    min_confidence: float = 0.5,
) -> Optional[str]:
    """감정 추정 → register 지시문. 중립/저신뢰/없음이면 ``None``.

    Args:
        estimate: E0 SER 결과.
        target_lang: 번역 대상 언어(ko/ja면 존댓말 제어 지시문 사용).
        min_confidence: 이 미만 신뢰도면 지시문을 내지 않음(약신호 과조정 방지).
    """

    if estimate is None:
        return None
    if estimate.label == EmotionLabel.NEUTRAL:
        return None
    if estimate.confidence < min_confidence:
        return None

    pair = _DIRECTIVES.get(estimate.label)
    if pair is None:
        return None

    lang = (target_lang or "").strip().lower().split("-")[0]
    ko_ja, other = pair
    directive = ko_ja if lang in _HONORIFIC_LANGS else other
    return f"[감정 인지 어조] {directive}"


def compose_hint(*parts: Optional[str], separator: str = " ") -> Optional[str]:
    """None/빈 문자열을 제외하고 힌트 조각을 합친다. 모두 비면 ``None``."""

    kept = [p.strip() for p in parts if p and p.strip()]
    if not kept:
        return None
    return separator.join(kept)
