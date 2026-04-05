"""
Alternative.me Fear & Greed Index Collector.

The Fear & Greed Index measures crypto market sentiment on a 0-100 scale:
- 0-24: Extreme Fear
- 25-49: Fear
- 50-74: Greed
- 75-100: Extreme Greed

No authentication required.
Rate limit: Unlimited (be respectful, use 1 req/sec max)
"""

import pandas as pd
from typing import Optional

from .base_collector import BaseCollector
from config.settings import config, APIEndpoints


class FearGreedCollector(BaseCollector):
    """Collector for Crypto Fear & Greed Index."""

    def __init__(self):
        super().__init__(rate_limit_per_second=config.FEAR_GREED_RATE_LIMIT)

    @property
    def name(self) -> str:
        return "FearGreed"

    def fetch_data(
        self,
        limit: int = 30,
        symbol: str = None  # Ignored, but kept for interface compatibility
    ) -> pd.DataFrame:
        """
        Fetch Fear & Greed Index history.

        Args:
            limit: Number of days of history (0 = all available)
            symbol: Ignored (index is for overall crypto market)

        Returns:
            DataFrame with columns: [value, value_classification, timestamp]
            Index: timestamp (datetime)

        Value classifications:
        - "Extreme Fear" (0-24)
        - "Fear" (25-49)
        - "Neutral" (50)
        - "Greed" (51-74)
        - "Extreme Greed" (75-100)
        """
        params = {"limit": limit, "format": "json"}
        data = self._make_request(APIEndpoints.FEAR_GREED_INDEX, params)

        if 'data' not in data or not data['data']:
            return pd.DataFrame()

        df = pd.DataFrame(data['data'])

        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='s')
        df['value'] = df['value'].astype(int)

        # Sort by timestamp (most recent first in response, we want oldest first)
        df.sort_values('timestamp', inplace=True)
        df.set_index('timestamp', inplace=True)

        return df

    def get_current_value(self) -> Optional[int]:
        """
        Get the current Fear & Greed Index value.

        Returns:
            Integer 0-100, or None on error
        """
        df = self.fetch_data(limit=1)
        if df.empty:
            return None
        return int(df['value'].iloc[-1])

    def get_current_classification(self) -> Optional[str]:
        """
        Get the current sentiment classification.

        Returns:
            String classification or None on error
        """
        df = self.fetch_data(limit=1)
        if df.empty:
            return None
        return df['value_classification'].iloc[-1]

    def get_trend(self, days: int = 7) -> Optional[float]:
        """
        Calculate the trend in Fear & Greed over recent days.

        Args:
            days: Number of days to analyze

        Returns:
            Change per day (positive = moving toward greed)
            None on error
        """
        df = self.fetch_data(limit=days)
        if len(df) < 2:
            return None

        # Calculate average daily change
        values = df['value'].values
        daily_changes = [values[i] - values[i-1] for i in range(1, len(values))]

        return sum(daily_changes) / len(daily_changes)

    def is_extreme_fear(self, threshold: int = None) -> bool:
        """Check if current value is in extreme fear zone."""
        threshold = threshold or config.FEAR_EXTREME
        value = self.get_current_value()
        return value is not None and value <= threshold

    def is_extreme_greed(self, threshold: int = None) -> bool:
        """Check if current value is in extreme greed zone."""
        threshold = threshold or config.GREED_EXTREME
        value = self.get_current_value()
        return value is not None and value >= threshold

    def get_signal_strength(self) -> float:
        """
        Calculate signal strength based on how extreme the current reading is.

        Returns:
            Float from -1 (extreme greed, bearish) to +1 (extreme fear, bullish)
            0 if neutral or error
        """
        value = self.get_current_value()
        if value is None:
            return 0.0

        # Map 0-100 to signal strength
        # 50 = neutral (0 signal)
        # 0 = max bullish (+1)
        # 100 = max bearish (-1)

        if value <= config.FEAR_EXTREME:
            # Extreme fear zone - bullish signal
            # Scale from 0.5 to 1.0 based on how extreme
            strength = 0.5 + 0.5 * (config.FEAR_EXTREME - value) / config.FEAR_EXTREME
            return min(strength, 1.0)

        elif value >= config.GREED_EXTREME:
            # Extreme greed zone - bearish signal
            strength = 0.5 + 0.5 * (value - config.GREED_EXTREME) / (100 - config.GREED_EXTREME)
            return -min(strength, 1.0)

        elif value < 40:
            # Moderate fear - weak bullish
            return 0.25 * (40 - value) / 20

        elif value > 60:
            # Moderate greed - weak bearish
            return -0.25 * (value - 60) / 20

        else:
            # Neutral zone (40-60)
            return 0.0
