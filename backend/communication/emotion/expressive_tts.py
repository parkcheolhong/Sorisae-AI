"""감정 E3 — SER 조건 표현형 TTS 운율 매핑 (ko 우회, 스캐폴드).

[`EMOTION_EXPRESSIVE_DESIGN.md`](../../../docs/worldlinco-v2/EMOTION_EXPRESSIVE_DESIGN.md) §3·§5 E3.
SeamlessExpressive 표현 보존은 한국어 미지원이므로, 음향 SER(언어 무관)로 **감정을 추정해
한국어 TTS의 운율(rate·pitch·volume)·스타일로 "재현"** 한다(전이 대신 재현).

설계 원칙:
- **차원 우선**: arousal(각성)은 비교적 신뢰 가능 → rate/volume/pitch 주신호. valence는 약신호 →
  pitch 소폭만 반영(설계서 §6 오인식 안전망).
- **신뢰도 게이트**: confidence < 임계면 **중립 운율(=합성 변형 없음)** 반환 → 기존 합성과 동일.
- **엔진 독립**: `to_edge_tts_kwargs`(edge-tts: rate/volume/pitch) + `to_azure_ssml`(Azure
  `mstts:express-as` 스타일 — 향후 표현형 한국어 보이스). hot path 무배선(카나리 전).
- **지연 예산**: 운율 파라미터화는 비용 0(엔진 인자만 변경). 무거운 표현형 모델은 E5.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .models import EmotionEstimate, EmotionLabel


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else hi if v > hi else v


@dataclass(frozen=True)
class ExpressiveTTSParams:
    """엔진 무관 표현형 운율 파라미터.

    rate/volume/pitch 는 edge-tts 형식 문자열(예: "+12%", "-3%", "+8Hz").
    style/style_degree 는 Azure `mstts:express-as` 용(향후 표현형 보이스).
    neutral=True 면 합성 변형 없음(기존과 동일) → 안전 폴백.
    """

    rate: str = "+0%"
    volume: str = "+0%"
    pitch: str = "+0Hz"
    style: Optional[str] = None
    style_degree: float = 1.0
    neutral: bool = True

    def to_dict(self) -> dict:
        return {
            "rate": self.rate, "volume": self.volume, "pitch": self.pitch,
            "style": self.style, "style_degree": round(self.style_degree, 2),
            "neutral": self.neutral,
        }


# 감정 라벨 → Azure express-as 스타일(한국어 표현형 보이스가 지원하는 스타일에 매핑).
_LABEL_STYLE: dict[EmotionLabel, str] = {
    EmotionLabel.ANGRY: "angry",
    EmotionLabel.HAPPY: "cheerful",
    EmotionLabel.SAD: "sad",
    EmotionLabel.CALM: "calm",
    EmotionLabel.NEUTRAL: "",
}

NEUTRAL_PARAMS = ExpressiveTTSParams()


def expressive_params_from_emotion(
    estimate: Optional[EmotionEstimate],
    *,
    min_confidence: float = 0.55,
    base_rate_pct: float = 0.0,
) -> ExpressiveTTSParams:
    """감정 추정 → 표현형 운율 파라미터(best-effort, 안전 폴백).

    None/저신뢰/중립이면 ``NEUTRAL_PARAMS``(변형 없음). arousal·valence 0..1(0.5 중립) 기준.
    """

    if estimate is None or estimate.confidence < min_confidence:
        return NEUTRAL_PARAMS
    if estimate.label == EmotionLabel.NEUTRAL:
        return NEUTRAL_PARAMS

    # arousal 0.5 중심 편차 → rate/volume/pitch. high arousal → 빠르고 크고 높게.
    a = _clamp(estimate.arousal, 0.0, 1.0) - 0.5      # -0.5..+0.5
    v = _clamp(estimate.valence, 0.0, 1.0) - 0.5      # -0.5..+0.5

    rate_pct = base_rate_pct + a * 40.0               # ±20%
    volume_pct = a * 30.0                             # ±15%
    # pitch: arousal 주신호 + valence 보조(긍정→약간 상승).
    pitch_hz = a * 24.0 + v * 8.0                     # ±~16Hz

    style = _LABEL_STYLE.get(estimate.label) or None
    # 신뢰도가 높을수록 스타일 강도↑(0.5..2.0 범위로 매핑).
    style_degree = _clamp(0.5 + estimate.confidence * 1.5, 0.5, 2.0)

    return ExpressiveTTSParams(
        rate=_fmt_pct(rate_pct),
        volume=_fmt_pct(volume_pct),
        pitch=_fmt_hz(pitch_hz),
        style=style,
        style_degree=style_degree,
        neutral=False,
    )


def _fmt_pct(x: float) -> str:
    return f"{x:+.0f}%"


def _fmt_hz(x: float) -> str:
    return f"{x:+.0f}Hz"


def to_edge_tts_kwargs(params: ExpressiveTTSParams) -> dict[str, str]:
    """edge-tts `Communicate(rate=, volume=, pitch=)` 인자(현 ko 보이스에 즉시 적용 가능)."""

    return {"rate": params.rate, "volume": params.volume, "pitch": params.pitch}


def to_azure_ssml(text: str, params: ExpressiveTTSParams, *, voice: str, lang: str = "ko-KR") -> str:
    """Azure Speech SSML(`mstts:express-as` + `prosody`) — 향후 표현형 한국어 보이스용.

    style 미지정/neutral 이면 prosody만 적용. 텍스트는 XML 이스케이프.
    """

    safe = (
        str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    prosody = f'<prosody rate="{params.rate}" pitch="{params.pitch}" volume="{params.volume}">{safe}</prosody>'
    inner = prosody
    if params.style and not params.neutral:
        inner = (
            f'<mstts:express-as style="{params.style}" styledegree="{params.style_degree:.1f}">'
            f"{prosody}</mstts:express-as>"
        )
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        f'xml:lang="{lang}"><voice name="{voice}">{inner}</voice></speak>'
    )
