from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class DataConfig:
    stock_path: str = 'data/stock_1m.parquet'
    market_path: Optional[str] = 'data/market_1m.parquet'
    datetime_col: str = 'datetime'


@dataclass
class SignalConfig:
    breakout_window: int = 20
    vol_window: int = 20
    min_breakout_strength: float = 0.0
    min_vol_ratio: float = 3.0
    min_turnover_1m: float = 1e8
    max_spread_pct: Optional[float] = 0.002


@dataclass
class LabelConfig:
    horizon_bars: int = 20
    take_profit: float = 0.007
    stop_loss: float = 0.0035
    entry_col: str = 'close'


@dataclass
class TrainConfig:
    target_col: str = 'y'
    train_end: str = '2025-01-01'
    valid_end: str = '2025-07-01'
    random_state: int = 42
    thresholds: List[float] = field(default_factory=lambda: [0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80])


@dataclass
class BacktestConfig:
    score_threshold: float = 0.65
    fee_rate: float = 0.00015
    slippage_rate: float = 0.00030
    max_positions: int = 3
    max_positions_per_symbol: int = 1
    min_score_rank: int = 3
    use_next_bar_open: bool = False
    enforce_time_exit_bars: int = 20
    initial_capital: float = 100_000_000
    risk_per_trade: float = 0.01


@dataclass
class KRFilterConfig:
    enable_time_filter: bool = True
    start_time: str = '09:05:00'
    end_time: str = '15:10:00'
    exclude_lunch: bool = False
    lunch_start: str = '11:30:00'
    lunch_end: str = '13:00:00'

    min_day_turnover: float = 5e9
    min_prev20d_avg_turnover: float = 3e9

    exclude_etf: bool = True
    exclude_spac: bool = True
    exclude_penny: bool = False
    min_price: float = 1000

    use_vi_filter: bool = True
    vi_column: str = 'is_vi'
    halt_column: str = 'is_halt'
    warning_column: str = 'is_warning'


@dataclass
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ''
    chat_id: str = ''


@dataclass
class LiveConfig:
    poll_interval_sec: int = 10
    score_threshold: float = 0.65
    max_positions: int = 3
    max_positions_per_symbol: int = 1
    max_order_per_cycle: int = 2
    risk_per_trade: float = 0.01
    stop_loss: float = 0.0035
    take_profit: float = 0.007
    time_exit_bars: int = 20
    dry_run: bool = True
    entry_order_type: str = 'limit'
    use_market_on_emergency: bool = True


@dataclass
class BrokerConfig:
    broker_name: str = 'kis'   # 'kis' or 'kiwoom'

    # 한국투자
    kis_app_key: str = ''
    kis_app_secret: str = ''
    kis_account_no: str = ''
    kis_product_code: str = '01'
    kis_base_url: str = 'https://openapi.koreainvestment.com:9443'

    # 키움
    kiwoom_user_id: str = ''
    kiwoom_mock: bool = True


FEATURE_COLS = [
    'ret_1m', 'ret_3m', 'ret_5m', 'ret_10m', 'ret_from_open',
    'dist_from_intraday_high_20m', 'breakout_strength_20m',
    'vol_ratio_1m_20m', 'vol_ratio_3m_20m',
    'turnover_1m', 'turnover_ratio_1m_20m',
    'range_pct_1m', 'range_pct_5m',
    'body_ratio_1m', 'upper_wick_ratio_1m', 'lower_wick_ratio_1m',
    'spread_pct', 'bid_ask_imbalance', 'buy_exec_ratio', 'mkt_ret_1m'
]
