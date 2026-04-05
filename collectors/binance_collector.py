"""
Binance Futures API Collector.

Fetches:
- Funding rates (historical and current)
- Open interest (current and historical)

No authentication required for public market data.
Rate limit: 500 requests per 5 minutes (~1.67/sec)
"""

import pandas as pd
from typing import Dict, Optional

from .base_collector import BaseCollector
from config.settings import config, APIEndpoints


class BinanceCollector(BaseCollector):
    """Collector for Binance Futures market data."""

    def __init__(self):
        super().__init__(rate_limit_per_second=config.BINANCE_RATE_LIMIT)

    @property
    def name(self) -> str:
        return "Binance"

    def fetch_funding_rate(
        self,
        symbol: str = "BTCUSDT",
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch historical funding rates.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            limit: Number of records (max 1000)

        Returns:
            DataFrame with columns: [symbol, fundingRate, fundingTime]
            Index: fundingTime (datetime)
        """
        params = {"symbol": symbol, "limit": limit}
        data = self._make_request(APIEndpoints.BINANCE_FUNDING_RATE, params)

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['fundingTime'] = pd.to_datetime(df['fundingTime'], unit='ms')
        df['fundingRate'] = df['fundingRate'].astype(float)
        df.set_index('fundingTime', inplace=True)
        df.sort_index(inplace=True)

        return df

    def fetch_open_interest(self, symbol: str = "BTCUSDT") -> pd.DataFrame:
        """
        Fetch current open interest.

        Args:
            symbol: Trading pair

        Returns:
            DataFrame with columns: [symbol, openInterest, time]
        """
        params = {"symbol": symbol}
        data = self._make_request(APIEndpoints.BINANCE_OPEN_INTEREST, params)

        df = pd.DataFrame([data])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df['openInterest'] = df['openInterest'].astype(float)

        return df

    def fetch_open_interest_history(
        self,
        symbol: str = "BTCUSDT",
        period: str = "5m",
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Fetch historical open interest.

        Args:
            symbol: Trading pair
            period: Time interval (5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d)
            limit: Number of records (max 500)

        Returns:
            DataFrame with columns: [symbol, sumOpenInterest, sumOpenInterestValue, timestamp]
            Index: timestamp (datetime)
        """
        params = {"symbol": symbol, "period": period, "limit": limit}

        try:
            data = self._make_request(APIEndpoints.BINANCE_OI_HISTORY, params)
        except Exception:
            # This endpoint may not be available for all symbols
            return pd.DataFrame()

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['sumOpenInterest'] = df['sumOpenInterest'].astype(float)
        df['sumOpenInterestValue'] = df['sumOpenInterestValue'].astype(float)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        return df

    def fetch_data(self, symbol: str = "BTCUSDT") -> Dict[str, pd.DataFrame]:
        """
        Fetch all available Binance data.

        Returns dict with:
        - 'funding_rate': Historical funding rates
        - 'open_interest': Current open interest
        - 'oi_history': Historical open interest (if available)
        """
        result = {}

        result['funding_rate'] = self.fetch_funding_rate(symbol)
        result['open_interest'] = self.fetch_open_interest(symbol)

        # OI history may fail for some symbols, handle gracefully
        oi_hist = self.safe_fetch_oi_history(symbol)
        if oi_hist is not None:
            result['oi_history'] = oi_hist

        return result

    def safe_fetch_oi_history(
        self,
        symbol: str = "BTCUSDT"
    ) -> Optional[pd.DataFrame]:
        """Fetch OI history with error handling."""
        try:
            return self.fetch_open_interest_history(symbol)
        except Exception:
            return None

    def get_current_funding_rate(self, symbol: str = "BTCUSDT") -> float:
        """Get the most recent funding rate."""
        df = self.fetch_funding_rate(symbol, limit=1)
        if df.empty:
            return 0.0
        return df['fundingRate'].iloc[-1]

    def get_funding_rate_average(
        self,
        symbol: str = "BTCUSDT",
        periods: int = 3
    ) -> float:
        """
        Get average funding rate over last N periods (8-hour each).

        Args:
            symbol: Trading pair
            periods: Number of funding periods to average

        Returns:
            Average funding rate
        """
        df = self.fetch_funding_rate(symbol, limit=periods)
        if df.empty:
            return 0.0
        return df['fundingRate'].mean()
