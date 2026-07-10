"""브리지 통역 파이프라인 — 엔진 주입 경계.

브리지 로직(레그·세그먼트·주입)을 실제 STT/MT/TTS 엔진과 분리한다. PoC/테스트는
`StubPipeline`(결정적, 외부 의존 0)을 쓰고, 운영은 기존 STT→MT→TTS 어댑터를 끼운다
(`backend/llm` voice 파이프라인 재사용, [`TELEPHONY_T0_FEASIBILITY.md`] T2).
"""

from __future__ import annotations

from typing import Callable, Optional, Protocol


class BridgePipeline(Protocol):
    """세그먼트 PCM → (전사, 번역, 합성 PCM) 변환 경계."""

    def transcribe(self, samples: list[int], *, language: str) -> str: ...

    def translate(self, text: str, *, from_lang: str, to_lang: str) -> str: ...

    def synthesize(self, text: str, *, language: str) -> list[int]: ...


class StubPipeline:
    """결정적 스텁 — 실엔진 없이 콜 플로우만 검증.

    transcribe: 샘플 수 기반 토큰("seg<frames>"), translate: 접두사 부착,
    synthesize: 텍스트 길이에 비례한 더미 PCM. 주입 가능한 콜백으로 동작 커스터마이즈.
    """

    def __init__(
        self,
        transcribe_fn: Optional[Callable[[list[int], str], str]] = None,
        translate_fn: Optional[Callable[[str, str, str], str]] = None,
        synthesize_fn: Optional[Callable[[str, str], list[int]]] = None,
    ) -> None:
        self._t = transcribe_fn
        self._m = translate_fn
        self._s = synthesize_fn

    def transcribe(self, samples: list[int], *, language: str) -> str:
        if self._t:
            return self._t(samples, language)
        return f"utt[{language}:{len(samples)}]"

    def translate(self, text: str, *, from_lang: str, to_lang: str) -> str:
        if self._m:
            return self._m(text, from_lang, to_lang)
        return f"{to_lang}<-{from_lang}:{text}"

    def synthesize(self, text: str, *, language: str) -> list[int]:
        if self._s:
            return self._s(text, language)
        # 텍스트 1자당 더미 80샘플(5ms@16k)로 합성 PCM 모사.
        return [0] * (max(1, len(text)) * 80)
