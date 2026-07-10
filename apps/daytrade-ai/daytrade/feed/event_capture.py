"""급변 이벤트 타게팅 캡처 — 변동성/거래량/오더북 급변 구간만 선별 기록.

블라인드 캡처(고정 틱 수)는 잔잔한 구간을 잔뜩 담아 회귀셋이 희석된다. 본 모듈은
**트리거(급변)가 발생한 구간만** pre-roll(전) + post-roll(후) 윈도로 잘라 기록한다.

트리거(OR 결합):
  - |윈도 수익률| ≥ ret_bps   (window 틱 전 대비 mid 수익률)
  - volume_spike ≥ vol_spike  (운영 FeatureEngine 의 거래량 급증비, 0=비활성)
  - |obi_norm| ≥ obi_z        (OBI z-score 절대값, 0=비활성)

운영과 동일한 `FeatureEngine` 으로 트리거 피처를 계산해 train/serve 일관성을 유지한다.
오프라인(기존 CSV → 이벤트 CSV) 과 라이브(피드 스캔) 양쪽에 쓸 수 있다.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Iterable, Iterator

from ..features.engine import FeatureEngine
from ..types import MarketTick


@dataclass(frozen=True, slots=True)
class EventCaptureConfig:
    ret_bps: float = 5.0       # |윈도 수익률| 임계(bps). 0=비활성.
    window: int = 20           # 수익률 측정 윈도(틱)
    pre: int = 10              # 이벤트 전 프리롤(틱)
    post: int = 30             # 이벤트 후 포스트롤(틱)
    vol_spike: float = 0.0     # volume_spike 임계(0=비활성)
    obi_z: float = 0.0         # |obi_norm| 임계(0=비활성)
    depth: int = 10
    max_events: int = 0        # 0=무제한


def iter_event_ticks(
    source: Iterable[MarketTick], config: EventCaptureConfig | None = None
) -> Iterator[MarketTick]:
    """source 틱 스트림에서 이벤트 윈도(pre+event+post)에 속하는 틱만 순서대로 yield.

    동일 틱 중복 방출을 방지하고(emitted_upto), 이벤트가 겹치면 post 윈도를 연장(re-arm)한다.
    """
    cfg = config or EventCaptureConfig()
    fe = FeatureEngine(depth=cfg.depth)

    mids: deque[float] = deque(maxlen=cfg.window + 1)
    pre_buf: deque[tuple[int, MarketTick]] = deque(maxlen=max(cfg.pre, 0))
    armed = 0
    events = 0
    emitted_upto = -1

    for idx, tick in enumerate(source):
        fv = fe.update(tick)
        mid = tick.mid_price if tick.mid_price is not None else float(tick.last_price)
        mids.append(mid)

        ret_bps = 0.0
        if len(mids) > cfg.window and mids[0] > 0:
            ret_bps = (mids[-1] / mids[0] - 1.0) * 1e4

        budget_ok = cfg.max_events == 0 or events < cfg.max_events
        trig = budget_ok and (
            (cfg.ret_bps > 0 and abs(ret_bps) >= cfg.ret_bps)
            or (cfg.vol_spike > 0 and fv.volume_spike >= cfg.vol_spike)
            or (cfg.obi_z > 0 and abs(fv.obi_norm) >= cfg.obi_z)
        )

        if trig:
            if armed == 0:
                events += 1
            armed = cfg.post
            # pre-roll flush (아직 방출 안 된 것만)
            for j, tk in pre_buf:
                if j > emitted_upto:
                    yield tk
                    emitted_upto = j

        if armed > 0:
            if idx > emitted_upto:
                yield tick
                emitted_upto = idx
            armed -= 1

        if cfg.pre > 0:
            pre_buf.append((idx, tick))
