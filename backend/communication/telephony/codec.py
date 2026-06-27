"""전화 T1 실통화 준비 — 전화망 코덱 계층 (G.711 ↔ PCM16, 8k ↔ 16k 리샘플).

[`TELEPHONY_BRIDGE_DESIGN.md`](../../../docs/worldlinco-v2/TELEPHONY_BRIDGE_DESIGN.md) T1/T2.
실 캐리어/CPaaS 미디어는 **G.711 μ-law(PCMU, 북미/일본) 또는 A-law(PCMA, 유럽 등) 8kHz**
가 표준이고, 통역 엔진(STT/MT/TTS)은 **PCM16 16kHz mono** 를 기대한다. 이 모듈이 그 경계를
변환한다 — 전송 어댑터(`transport.py`)가 캐리어 프레임을 엔진 도메인으로 올리고 다시 내린다.

**순수 파이썬**(Python 3.13에서 `audioop` 표준 모듈이 제거됨 → 외부 의존 없이 자체 구현).
디코드는 G.711(Sun/CCITT) 레퍼런스, 인코드는 디코드 레벨에 대한 **최근접 코드**(이분 탐색)로
인코드↔디코드 왕복 일관성을 보장한다. 리샘플은 선형 보간(PoC; 실서버는 폴리페이즈로 정밀화).
"""

from __future__ import annotations

import bisect
from typing import List, Sequence

_INT16_MIN = -32768
_INT16_MAX = 32767


def _clamp16(v: int) -> int:
    return _INT16_MIN if v < _INT16_MIN else _INT16_MAX if v > _INT16_MAX else v


# --- G.711 μ-law (PCMU) -------------------------------------------------------

_BIAS = 0x84  # 132


def _ulaw2linear(u_val: int) -> int:
    """μ-law 코드(0..255) → PCM16 (Sun/CCITT 레퍼런스)."""

    u_val = ~u_val & 0xFF
    t = ((u_val & 0x0F) << 3) + _BIAS
    t <<= (u_val & 0x70) >> 4
    return (_BIAS - t) if (u_val & 0x80) else (t - _BIAS)


def _alaw2linear(a_val: int) -> int:
    """A-law 코드(0..255) → PCM16 (Sun/CCITT 레퍼런스)."""

    a_val ^= 0x55
    t = (a_val & 0x0F) << 4
    seg = (a_val & 0x70) >> 4
    if seg == 0:
        t += 8
    elif seg == 1:
        t += 0x108
    else:
        t = (t + 0x108) << (seg - 1)
    return t if (a_val & 0x80) else -t


def _build_encode_index(decode_table: Sequence[int]):
    """디코드 레벨 → 최근접 코드 역인덱스(정렬 레벨 + 대응 코드)."""

    pairs = sorted((level, code) for code, level in enumerate(decode_table))
    levels = [p[0] for p in pairs]
    codes = [p[1] for p in pairs]
    return levels, codes


_ULAW_DECODE: List[int] = [_ulaw2linear(b) for b in range(256)]
_ALAW_DECODE: List[int] = [_alaw2linear(b) for b in range(256)]
_ULAW_LEVELS, _ULAW_CODES = _build_encode_index(_ULAW_DECODE)
_ALAW_LEVELS, _ALAW_CODES = _build_encode_index(_ALAW_DECODE)


def _nearest_code(sample: int, levels: List[int], codes: List[int]) -> int:
    """PCM16 샘플 → 최근접 디코드 레벨의 코드(이분 탐색)."""

    sample = _clamp16(sample)
    i = bisect.bisect_left(levels, sample)
    if i <= 0:
        return codes[0]
    if i >= len(levels):
        return codes[-1]
    lo, hi = levels[i - 1], levels[i]
    return codes[i - 1] if (sample - lo) <= (hi - sample) else codes[i]


def ulaw_to_pcm16(data: bytes) -> List[int]:
    """G.711 μ-law 바이트 → PCM16 샘플 리스트."""

    return [_ULAW_DECODE[b] for b in data]


def pcm16_to_ulaw(samples: Sequence[int]) -> bytes:
    """PCM16 샘플 → G.711 μ-law 바이트."""

    return bytes(_nearest_code(int(s), _ULAW_LEVELS, _ULAW_CODES) for s in samples)


def alaw_to_pcm16(data: bytes) -> List[int]:
    """G.711 A-law 바이트 → PCM16 샘플 리스트."""

    return [_ALAW_DECODE[b] for b in data]


def pcm16_to_alaw(samples: Sequence[int]) -> bytes:
    """PCM16 샘플 → G.711 A-law 바이트."""

    return bytes(_nearest_code(int(s), _ALAW_LEVELS, _ALAW_CODES) for s in samples)


# --- 리샘플 (선형 보간) -------------------------------------------------------

def resample_pcm16(samples: Sequence[int], from_rate: int, to_rate: int) -> List[int]:
    """PCM16 선형 리샘플(8k↔16k 등). PoC 품질 — 실서버는 폴리페이즈/FIR 권장."""

    if from_rate == to_rate or not samples:
        return [int(s) for s in samples]
    n_in = len(samples)
    n_out = max(1, int(round(n_in * to_rate / from_rate)))
    ratio = from_rate / to_rate
    out: List[int] = []
    for i in range(n_out):
        src = i * ratio
        i0 = int(src)
        if i0 >= n_in - 1:
            out.append(_clamp16(int(samples[n_in - 1])))
            continue
        frac = src - i0
        s0 = samples[i0]
        s1 = samples[i0 + 1]
        out.append(_clamp16(int(round(s0 + (s1 - s0) * frac))))
    return out


# --- 캐리어(8k G.711) ↔ 엔진(16k PCM16) 편의 함수 ---------------------------

CARRIER_RATE = 8000
ENGINE_RATE = 16000


def ulaw8k_to_pcm16_engine(data: bytes, *, engine_rate: int = ENGINE_RATE) -> List[int]:
    """캐리어 μ-law 8kHz → 엔진 PCM16(16kHz 기본)."""

    return resample_pcm16(ulaw_to_pcm16(data), CARRIER_RATE, engine_rate)


def pcm16_engine_to_ulaw8k(samples: Sequence[int], *, engine_rate: int = ENGINE_RATE) -> bytes:
    """엔진 PCM16(16kHz 기본) → 캐리어 μ-law 8kHz."""

    return pcm16_to_ulaw(resample_pcm16(samples, engine_rate, CARRIER_RATE))
