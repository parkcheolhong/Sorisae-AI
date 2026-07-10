"""고속 로컬 타임시리즈 저장 — KDB+/q 의 경량 대안(설계서 §8 데이터 계층).

KDB+ 는 금융권 표준 초고속 컬럼형 타임시리즈 DB 이나 상용·외부 의존이다. 본 모듈은
**의존성 없는 고정폭 바이너리 틱 스토어**(`TickStore`)로 동일한 핵심 가치(틱 무손실 저장 +
시간 범위 O(log n) 슬라이스)를 제공한다. CSV 대비 파싱 비용이 없고(struct 언팩) 파일이 작으며,
타임스탬프 정렬을 전제로 이진 탐색 범위질의를 지원한다 — 백테스트/리서치 데이터 적재 가속.

파티셔닝은 KDB+ 관례를 따라 **스토어 1개 = 종목 1개**(헤더에 심볼 고정)로 둔다.
"""
from .recorder import RollingTickStoreWriter, StoreRecordingFeed
from .tickstore import (
    TickStore,
    TickStoreFeed,
    TickStoreWriter,
    csv_to_store,
    write_ticks_store,
)

__all__ = [
    "TickStore",
    "TickStoreWriter",
    "TickStoreFeed",
    "write_ticks_store",
    "csv_to_store",
    "RollingTickStoreWriter",
    "StoreRecordingFeed",
]
