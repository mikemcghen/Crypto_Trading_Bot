"""
Liquidation Signal Generator.

Generates contrarian signals based on liquidation cascades:
- Large long liquidations → Market swept longs → LONG signal (fade the sweep)
- Large short liquidations → Market swept shorts → SHORT signal

Rationale: Liquidation cascades are forced selling/buying that often
overshoots fair value. After the cascade exhausts, price tends to revert.
"""

from typing import Optional, Dict, Any

from .base_signal import BaseSignal, TradingSignal, SignalDirection
from config.settings import config


class LiquidationSignal(BaseSignal):
    """
    Contrarian signal based on liquidation cascades.

    Score contribution: Up to 2 points

    Triggers when:
    - Total liquidation volume > $10M (configurable)
    - Imbalance (one side > 30% more than other)
    """

    @property
    def name(self) -> str:
        return "liquidations"

    @property
    def max_score(self) -> float:
        return config.LIQUIDATION_MAX_SCORE

    def generate(self, data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate signal from liquidation data.

        Args:
            data: Market data dict containing 'liquidation_analysis'

        Returns:
            TradingSignal if significant liquidation imbalance, None otherwise
        """
        # Get pre-computed liquidation analysis from OKX collector
        liq_analysis = data.get('liquidation_analysis')

        if not liq_analysis:
            return None

        total_volume = liq_analysis.get('total_volume', 0)
        imbalance = liq_analysis.get('imbalance', 0)
        long_liqs = liq_analysis.get('long_liquidations', 0)
        short_liqs = liq_analysis.get('short_liquidations', 0)

        # Check if volume is significant
        if total_volume < config.LIQUIDATION_CLUSTER_USD:
            return None

        # Check if imbalance is significant
        if abs(imbalance) < config.LIQUIDATION_IMBALANCE_THRESHOLD:
            return None

        # More longs liquidated → LONG signal (contrarian)
        if imbalance > config.LIQUIDATION_IMBALANCE_THRESHOLD:
            strength = self._calculate_strength(imbalance, total_volume)

            return self._create_signal(
                direction=SignalDirection.LONG,
                strength=strength,
                raw_value=imbalance,
                threshold=config.LIQUIDATION_IMBALANCE_THRESHOLD,
                reasoning=(
                    f"Long liquidation cascade detected. "
                    f"${long_liqs/1e6:.1f}M longs liquidated vs ${short_liqs/1e6:.1f}M shorts. "
                    f"Imbalance: {imbalance:.1%}. "
                    f"Market likely swept weak longs - contrarian long opportunity."
                ),
                metadata={
                    'long_liquidations': long_liqs,
                    'short_liquidations': short_liqs,
                    'total_volume': total_volume,
                    'imbalance': imbalance
                }
            )

        # More shorts liquidated → SHORT signal (contrarian)
        elif imbalance < -config.LIQUIDATION_IMBALANCE_THRESHOLD:
            strength = self._calculate_strength(abs(imbalance), total_volume)

            return self._create_signal(
                direction=SignalDirection.SHORT,
                strength=strength,
                raw_value=imbalance,
                threshold=-config.LIQUIDATION_IMBALANCE_THRESHOLD,
                reasoning=(
                    f"Short liquidation cascade detected. "
                    f"${short_liqs/1e6:.1f}M shorts liquidated vs ${long_liqs/1e6:.1f}M longs. "
                    f"Imbalance: {imbalance:.1%}. "
                    f"Market likely squeezed weak shorts - contrarian short opportunity."
                ),
                metadata={
                    'long_liquidations': long_liqs,
                    'short_liquidations': short_liqs,
                    'total_volume': total_volume,
                    'imbalance': imbalance
                }
            )

        return None

    def _calculate_strength(self, imbalance: float, volume: float) -> float:
        """
        Calculate signal strength based on imbalance and volume.

        Higher imbalance and higher volume = stronger signal.

        Args:
            imbalance: Absolute imbalance ratio (0 to 1)
            volume: Total liquidation volume in USD

        Returns:
            Float from 0.5 to 1.0
        """
        # Base strength from imbalance (0.3 threshold = 0.5 strength)
        imbalance_factor = min(imbalance / 0.6, 1.0)  # Max at 60% imbalance

        # Bonus for higher volume (above $10M threshold)
        volume_factor = min(volume / (config.LIQUIDATION_CLUSTER_USD * 5), 1.0)

        # Combine factors
        strength = 0.5 * imbalance_factor + 0.5 * volume_factor

        return min(max(strength, 0.5), 1.0)

    def get_liquidation_status(self, data: Dict[str, Any]) -> str:
        """
        Get human-readable liquidation status.

        Returns one of:
        - "LONG_CASCADE"
        - "SHORT_CASCADE"
        - "BALANCED"
        - "LOW_VOLUME"
        - "UNKNOWN"
        """
        liq_analysis = data.get('liquidation_analysis')

        if not liq_analysis:
            return "UNKNOWN"

        total_volume = liq_analysis.get('total_volume', 0)
        imbalance = liq_analysis.get('imbalance', 0)

        if total_volume < config.LIQUIDATION_CLUSTER_USD:
            return "LOW_VOLUME"

        if imbalance > config.LIQUIDATION_IMBALANCE_THRESHOLD:
            return "LONG_CASCADE"
        elif imbalance < -config.LIQUIDATION_IMBALANCE_THRESHOLD:
            return "SHORT_CASCADE"
        else:
            return "BALANCED"
