"""Market Feed — 시장 데이터 수신 계층(설계서 §1 Market Feed / Ingest 대응).

실환경의 DPDK/ITCH 커널바이패스는 이 개발 환경에서 불가하므로, 동일한 인터페이스
(``MarketFeed``)를 두고 ① 합성 시뮬레이션 피드와 ② CSV 리플레이 피드를 제공한다.
실거래소/브로커 웹소켓 피드는 ``MarketFeed`` 를 구현해 끼우면 된다(어댑터 지점).
"""
from .base import MarketFeed
from .simulated import SimulatedFeed
from .replay import CsvReplayFeed
from .binance import BinanceFeed
from .upbit import UpbitFeed
from .alpaca import AlpacaFeed
from .memory import ListFeed
from .recorder import RecordingFeed, write_ticks_csv

__all__ = [
    "MarketFeed",
    "SimulatedFeed",
    "CsvReplayFeed",
    "BinanceFeed",
    "UpbitFeed",
    "AlpacaFeed",
    "ListFeed",
    "RecordingFeed",
    "write_ticks_csv",
]
