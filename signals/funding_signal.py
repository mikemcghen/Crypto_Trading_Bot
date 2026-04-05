"""
Funding Rate Signal Generator.

Generates contrarian signals based on funding rate extremes:
- High positive funding (longs paying shorts) → SHORT signal
- High negative funding (shorts paying longs) → LONG signal

Rationale: Extreme funding indicates crowded positioning.
Crowded trades tend to unwind, creating price moves opposite
to the crowd's position.
"""

from typing import Optional, Dict, Any
import pandas as pd

from .base_signal import BaseSignal, TradingSignal, SignalDirection
from config.settings import config


class FundingRateSignal(BaseSignal):
    """
    Contrarian signal based on funding rate extremes.

    Score contribution: Up to 2 points

    Thresholds (configurable in config.settings):
    - Extreme long: > 0.1% per 8h (0.001)
    - Extreme short: < -0.05% per 8h (-0.0005)
    """

    @property
    def name(self) -> str:
        return "funding_rate"

    @property
    def max_score(self) -> float:
        return config.FUNDING_MAX_SCORE

    def generate(self, data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate signal from funding rate data.

        Args:
            data: Market data dict containing 'binance_funding' DataFrame

        Returns:
            TradingSignal if funding is extreme, None otherwise
        """
        # Get funding data
        funding_df = data.get('binance_funding')

        if funding_df is None or funding_df.empty:
            return None

        if 'fundingRate' not in funding_df.columns:
            return None

        # Get latest and average funding
        latest_rate = float(funding_df['fundingRate'].iloc[-1])

        # Calculate 24h average (3 funding periods)
        avg_rate = float(funding_df['fundingRate'].tail(3).mean())

        # Check for extreme positive funding (crowded longs → SHORT)
        if latest_rate > config.FUNDING_EXTREME_LONG:
            strength = self._calculate_strength(
                latest_rate,
                config.FUNDING_EXTREME_LONG,
                multiplier=2.0
            )

            return self._create_signal(
                direction=SignalDirection.SHORT,
                strength=strength,
                raw_value=latest_rate,
                threshold=config.FUNDING_EXTREME_LONG,
                reasoning=(
                    f"Funding rate {latest_rate:.4%} exceeds threshold {config.FUNDING_EXTREME_LONG:.4%}. "
                    f"Longs paying {latest_rate * 3 * 100:.2f}%/day premium. "
                    f"24h avg: {avg_rate:.4%}. Crowded long positioning detected."
                ),
                metadata={
                    'latest_rate': latest_rate,
                    'avg_24h': avg_rate,
                    'annualized_cost': latest_rate * 3 * 365 * 100  # % per year
                }
            )

        # Check for extreme negative funding (crowded shorts → LONG)
        elif latest_rate < config.FUNDING_EXTREME_SHORT:
            strength = self._calculate_strength(
                abs(latest_rate),
                abs(config.FUNDING_EXTREME_SHORT),
                multiplier=2.0
            )

            return self._create_signal(
                direction=SignalDirection.LONG,
                strength=strength,
                raw_value=latest_rate,
                threshold=config.FUNDING_EXTREME_SHORT,
                reasoning=(
                    f"Funding rate {latest_rate:.4%} below threshold {config.FUNDING_EXTREME_SHORT:.4%}. "
                    f"Shorts paying {abs(latest_rate) * 3 * 100:.2f}%/day premium. "
                    f"24h avg: {avg_rate:.4%}. Crowded short positioning detected."
                ),
                metadata={
                    'latest_rate': latest_rate,
                    'avg_24h': avg_rate,
                    'annualized_cost': abs(latest_rate) * 3 * 365 * 100
                }
            )

        return None

    def _calculate_strength(
        self,
        value: float,
        threshold: float,
        multiplier: float = 2.0
    ) -> float:
        """
        Calculate signal strength based on how far value exceeds threshold.

        Strength scales linearly from 0.5 (at threshold) to 1.0 (at 2x threshold).

        Args:
            value: The actual funding rate (absolute value)
            threshold: The extreme threshold
            multiplier: How many times threshold for max strength

        Returns:
            Float from 0.5 to 1.0
        """
        if threshold == 0:
            return 0.5

        # Ratio of how much we exceed threshold
        ratio = value / threshold

        # Scale: 1.0x threshold = 0.5 strength, 2.0x threshold = 1.0 strength
        strength = 0.5 + 0.5 * min((ratio - 1.0) / (multiplier - 1.0), 1.0)

        return min(max(strength, 0.5), 1.0)

    def get_funding_status(self, data: Dict[str, Any]) -> str:
        """
        Get human-readable funding rate status.

        Returns one of:
        - "EXTREME_POSITIVE"
        - "POSITIVE"
        - "NEUTRAL"
        - "NEGATIVE"
        - "EXTREME_NEGATIVE"
        - "UNKNOWN"
        """
        funding_df = data.get('binance_funding')

        if funding_df is None or funding_df.empty:
            return "UNKNOWN"

        latest_rate = float(funding_df['fundingRate'].iloc[-1])

        if latest_rate > config.FUNDING_EXTREME_LONG:
            return "EXTREME_POSITIVE"
        elif latest_rate > 0.0003:  # 0.03%
            return "POSITIVE"
        elif latest_rate < config.FUNDING_EXTREME_SHORT:
            return "EXTREME_NEGATIVE"
        elif latest_rate < -0.0001:  # -0.01%
            return "NEGATIVE"
        else:
            return "NEUTRAL"
