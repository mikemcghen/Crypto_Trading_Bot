"""
OKX API Collector.

Fetches:
- Liquidation orders (key differentiator - not available on Binance public API)
- Funding rates (backup/confirmation)

No authentication required for public endpoints.
Rate limit: 20 requests per 2 seconds (~10/sec)
"""

import pandas as pd
from typing import Dict, Optional
from datetime import datetime, timedelta

from .base_collector import BaseCollector
from config.settings import config, APIEndpoints


class OKXCollector(BaseCollector):
    """Collector for OKX market data, specializing in liquidation data."""

    def __init__(self):
        super().__init__(rate_limit_per_second=config.OKX_RATE_LIMIT)

    @property
    def name(self) -> str:
        return "OKX"

    def _convert_symbol(self, symbol: str) -> str:
        """
        Convert standard symbol format to OKX format.

        BTCUSDT -> BTC-USDT-SWAP
        """
        if "-SWAP" in symbol:
            return symbol

        # Handle common formats
        if "USDT" in symbol:
            base = symbol.replace("USDT", "")
            return f"{base}-USDT-SWAP"
        elif "USD" in symbol:
            base = symbol.replace("USD", "")
            return f"{base}-USD-SWAP"

        return f"{symbol}-USDT-SWAP"

    def fetch_liquidations(
        self,
        symbol: str = "BTCUSDT",
        state: str = "filled",
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Fetch recent liquidation orders.

        Args:
            symbol: Trading pair (will be converted to OKX format)
            state: Order state - "filled" for completed liquidations
            limit: Not directly supported, API returns recent data

        Returns:
            DataFrame with columns: [ts, side, sz, bkPx, posSide]
            - ts: Timestamp
            - side: 'buy' (short liquidated) or 'sell' (long liquidated)
            - sz: Size in contracts
            - bkPx: Bankruptcy price
            - posSide: Position side that was liquidated
        """
        inst_id = self._convert_symbol(symbol)

        params = {
            "instType": "SWAP",
            "instId": inst_id,
            "state": state
        }

        try:
            data = self._make_request(APIEndpoints.OKX_LIQUIDATIONS, params)
        except Exception as e:
            # Liquidation endpoint can be empty or error during low activity
            return pd.DataFrame()

        if 'data' not in data or not data['data']:
            return pd.DataFrame()

        # OKX returns nested structure with details array
        all_details = []
        for item in data['data']:
            if 'details' in item:
                for detail in item['details']:
                    detail['instId'] = item.get('instId', inst_id)
                    all_details.append(detail)

        if not all_details:
            return pd.DataFrame()

        df = pd.DataFrame(all_details)

        # Convert types
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts'].astype(int), unit='ms')
        if 'sz' in df.columns:
            df['sz'] = pd.to_numeric(df['sz'], errors='coerce')
        if 'bkPx' in df.columns:
            df['bkPx'] = pd.to_numeric(df['bkPx'], errors='coerce')

        df.sort_values('ts', ascending=False, inplace=True)

        return df

    def fetch_funding_rate(self, symbol: str = "BTCUSDT") -> pd.DataFrame:
        """
        Fetch current funding rate from OKX.

        Returns:
            DataFrame with columns: [instId, fundingRate, fundingTime, nextFundingRate, nextFundingTime]
        """
        inst_id = self._convert_symbol(symbol)
        params = {"instId": inst_id}

        data = self._make_request(APIEndpoints.OKX_FUNDING_RATE, params)

        if 'data' not in data or not data['data']:
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])

        if 'fundingRate' in df.columns:
            df['fundingRate'] = df['fundingRate'].astype(float)
        if 'fundingTime' in df.columns:
            df['fundingTime'] = pd.to_datetime(df['fundingTime'].astype(int), unit='ms')
        if 'nextFundingTime' in df.columns:
            df['nextFundingTime'] = pd.to_datetime(df['nextFundingTime'].astype(int), unit='ms')

        return df

    def fetch_data(self, symbol: str = "BTCUSDT") -> Dict[str, pd.DataFrame]:
        """
        Fetch all available OKX data.

        Returns dict with:
        - 'liquidations': Recent liquidation orders
        - 'funding_rate': Current funding rate
        """
        return {
            'liquidations': self.fetch_liquidations(symbol),
            'funding_rate': self.fetch_funding_rate(symbol)
        }

    def analyze_liquidations(
        self,
        symbol: str = "BTCUSDT",
        lookback_minutes: int = 60
    ) -> Dict[str, float]:
        """
        Analyze recent liquidations for trading signals.

        Args:
            symbol: Trading pair
            lookback_minutes: Time window to analyze

        Returns:
            Dict with:
            - 'long_liquidations': Total long liquidation volume
            - 'short_liquidations': Total short liquidation volume
            - 'imbalance': -1 to +1 (positive = more longs liquidated)
            - 'total_volume': Total liquidation volume
        """
        df = self.fetch_liquidations(symbol)

        if df.empty:
            return {
                'long_liquidations': 0.0,
                'short_liquidations': 0.0,
                'imbalance': 0.0,
                'total_volume': 0.0
            }

        # Filter to lookback window
        cutoff = datetime.now() - timedelta(minutes=lookback_minutes)
        recent = df[df['ts'] > cutoff] if 'ts' in df.columns else df

        if recent.empty:
            return {
                'long_liquidations': 0.0,
                'short_liquidations': 0.0,
                'imbalance': 0.0,
                'total_volume': 0.0
            }

        # side='sell' means longs were liquidated (forced to sell)
        # side='buy' means shorts were liquidated (forced to buy)
        long_liqs = recent[recent['side'] == 'sell']['sz'].sum() if 'side' in recent.columns else 0
        short_liqs = recent[recent['side'] == 'buy']['sz'].sum() if 'side' in recent.columns else 0

        total = long_liqs + short_liqs

        if total == 0:
            imbalance = 0.0
        else:
            # Positive imbalance = more longs liquidated (contrarian = go long)
            imbalance = (long_liqs - short_liqs) / total

        return {
            'long_liquidations': float(long_liqs),
            'short_liquidations': float(short_liqs),
            'imbalance': float(imbalance),
            'total_volume': float(total)
        }
