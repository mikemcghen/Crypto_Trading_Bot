"""
Centralized configuration for market structure trading bot.
All thresholds and parameters in one place for easy tuning.
"""

from dataclasses import dataclass


@dataclass
class TradingConfig:
    # Signal score thresholds
    REQUIRED_SIGNAL_SCORE: float = 2.5  # Lowered from 4.0 to generate more signals
    MAX_POSSIBLE_SCORE: float = 8.0

    # Funding rate thresholds (per 8-hour period)
    FUNDING_EXTREME_LONG: float = 0.001      # 0.1% - longs paying, crowded long
    FUNDING_EXTREME_SHORT: float = -0.0005   # -0.05% - shorts paying, crowded short
    FUNDING_MAX_SCORE: float = 2.0

    # Fear & Greed Index thresholds (0-100 scale)
    FEAR_EXTREME: int = 20                   # Below = extreme fear
    GREED_EXTREME: int = 80                  # Above = extreme greed
    FEAR_GREED_MAX_SCORE: float = 1.5

    # Liquidation thresholds
    LIQUIDATION_CLUSTER_USD: float = 10_000_000  # $10M minimum
    LIQUIDATION_IMBALANCE_THRESHOLD: float = 0.3  # 30% imbalance
    LIQUIDATION_MAX_SCORE: float = 2.0

    # Open Interest + Funding confluence
    OI_CHANGE_THRESHOLD: float = 0.05        # 5% OI change
    OI_CONFLUENCE_MAX_SCORE: float = 1.5

    # Position sizing
    MAX_POSITION_PCT: float = 0.10           # 10% of portfolio per trade
    MAX_POSITIONS: int = 3                   # Maximum concurrent positions
    MIN_POSITION_PCT: float = 0.05           # Minimum 5% even with weak signal

    # Risk management
    STOP_LOSS_PCT: float = 0.02              # 2% stop loss
    TAKE_PROFIT_PCT: float = 0.04            # 4% take profit (2:1 R:R)
    MAX_DAILY_LOSS_PCT: float = 0.06         # 6% max daily drawdown

    # API rate limiting (requests per second)
    BINANCE_RATE_LIMIT: float = 1.5          # Conservative (actual: 1.67/s)
    OKX_RATE_LIMIT: float = 8.0              # Conservative (actual: 10/s)
    BYBIT_RATE_LIMIT: float = 8.0            # Conservative (actual: 10/s)
    FEAR_GREED_RATE_LIMIT: float = 1.0       # Be respectful

    # Timeouts
    API_TIMEOUT_SECONDS: int = 30

    # Backtesting defaults
    BACKTEST_INITIAL_CAPITAL: float = 10000.0
    BACKTEST_TRADING_FEE_PCT: float = 0.001  # 0.1% taker fee


# API Endpoints
class APIEndpoints:
    # Binance Futures
    BINANCE_BASE = "https://fapi.binance.com"
    BINANCE_FUNDING_RATE = f"{BINANCE_BASE}/fapi/v1/fundingRate"
    BINANCE_OPEN_INTEREST = f"{BINANCE_BASE}/fapi/v1/openInterest"
    BINANCE_OI_HISTORY = f"{BINANCE_BASE}/futures/data/openInterestHist"

    # OKX
    OKX_BASE = "https://www.okx.com"
    OKX_LIQUIDATIONS = f"{OKX_BASE}/api/v5/public/liquidation-orders"
    OKX_FUNDING_RATE = f"{OKX_BASE}/api/v5/public/funding-rate"

    # Bybit (backup)
    BYBIT_BASE = "https://api.bybit.com"
    BYBIT_FUNDING_RATE = f"{BYBIT_BASE}/v5/market/funding/history"
    BYBIT_OPEN_INTEREST = f"{BYBIT_BASE}/v5/market/open-interest"

    # Alternative.me
    FEAR_GREED_INDEX = "https://api.alternative.me/fng/"

    # CoinGecko (existing)
    COINGECKO_PRICE = "https://api.coingecko.com/api/v3/simple/price"


# Singleton config instance
config = TradingConfig()
