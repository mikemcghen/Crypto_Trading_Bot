"""
Bybit API Collector (Fallback for Binance).

Fetches:
- Funding rates (historical and current)
- Open interest (current and historical)

No authentication required for public market data.
Rate limit: 10 requests per second
"""

import pandas as pd
from typing import Dict, Optional

from .base_collector import BaseCollector
from config.settings import config, APIEndpoints


class BybitCollector(BaseCollector):
    """Collector for Bybit market data - fallback when Binance is blocked."""

    def __init__(self):
        super().__init__(rate_limit_per_second=config.BYBIT_RATE_LIMIT)

    @property
    def name(self) -> str:
        return "Bybit"

    def fetch_funding_rate(
        self,
        symbol: str = "BTCUSDT",
        category: str = "linear",
        limit: int = 200
    ) -> pd.DataFrame:
        """
        Fetch historical funding rates.

        Args:
            symbol: Trading pair (e.g., "BTCUSDT")
            category: Contract type ("linear" for USDT perps)
            limit: Number of records (max 200)

        Returns:
            DataFrame with columns: [symbol, fundingRate, fundingRateTimestamp]
            Index: fundingRateTimestamp (datetime)
        """
        params = {
            "category": category,
            "symbol": symbol,
            "limit": limit
        }

        data = self._make_request(APIEndpoints.BYBIT_FUNDING_RATE, params)

        result = data.get('result', {}).get('list', [])

        if not result:
            return pd.DataFrame()

        df = pd.DataFrame(result)

        # Convert timestamp and funding rate
        df['fundingRateTimestamp'] = pd.to_datetime(
            df['fundingRateTimestamp'].astype(int), unit='ms'
        )
        df['fundingRate'] = df['fundingRate'].astype(float)

        # Rename to match Binance format for compatibility
        df = df.rename(columns={'fundingRateTimestamp': 'fundingTime'})
        df.set_index('fundingTime', inplace=True)
        df.sort_index(inplace=True)

        return df

    def fetch_open_interest(
        self,
        symbol: str = "BTCUSDT",
        category: str = "linear",
        interval_time: str = "5min",
        limit: int = 200
    ) -> pd.DataFrame:
        """
        Fetch historical open interest.

        Args:
            symbol: Trading pair
            category: Contract type
            interval_time: Time interval (5min, 15min, 30min, 1h, 4h, 1d)
            limit: Number of records (max 200)

        Returns:
            DataFrame with columns: [openInterest, timestamp]
            Index: timestamp (datetime)
        """
        params = {
            "category": category,
            "symbol": symbol,
            "intervalTime": interval_time,
            "limit": limit
        }

        data = self._make_request(APIEndpoints.BYBIT_OPEN_INTEREST, params)

        result = data.get('result', {}).get('list', [])

        if not result:
            return pd.DataFrame()

        df = pd.DataFrame(result)

        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
        df['openInterest'] = df['openInterest'].astype(float)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)

        return df

    def fetch_data(self, symbol: str = "BTCUSDT") -> Dict[str, pd.DataFrame]:
        """
        Fetch all available Bybit data.

        Returns dict with:
        - 'funding_rate': Historical funding rates
        - 'open_interest': Historical open interest
        """
        return {
            'funding_rate': self.fetch_funding_rate(symbol),
            'open_interest': self.fetch_open_interest(symbol)
        }

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
