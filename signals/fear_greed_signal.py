"""
Fear & Greed Index Signal Generator.

Generates contrarian signals based on sentiment extremes:
- Extreme Fear (0-20) → LONG signal (buy when others are fearful)
- Extreme Greed (80-100) → SHORT signal (sell when others are greedy)

Rationale: Extreme sentiment often marks local tops and bottoms.
The crowd is usually wrong at extremes.
"""

from typing import Optional, Dict, Any

from .base_signal import BaseSignal, TradingSignal, SignalDirection
from config.settings import config


class FearGreedSignal(BaseSignal):
    """
    Contrarian signal based on Fear & Greed Index extremes.

    Score contribution: Up to 1.5 points

    Thresholds (configurable in config.settings):
    - Extreme Fear: <= 20
    - Extreme Greed: >= 80
    """

    @property
    def name(self) -> str:
        return "fear_greed"

    @property
    def max_score(self) -> float:
        return config.FEAR_GREED_MAX_SCORE

    def generate(self, data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate signal from Fear & Greed Index.

        Args:
            data: Market data dict containing 'fear_greed_current' and 'fear_greed' DataFrame

        Returns:
            TradingSignal if sentiment is extreme, None otherwise
        """
        # Get current Fear & Greed value
        current_value = data.get('fear_greed_current')

        if current_value is None:
            # Try to get from DataFrame
            fear_greed_df = data.get('fear_greed')
            if fear_greed_df is None or fear_greed_df.empty:
                return None
            current_value = int(fear_greed_df['value'].iloc[-1])

        # Get classification
        fear_greed_df = data.get('fear_greed')
        classification = "Unknown"
        if fear_greed_df is not None and not fear_greed_df.empty:
            classification = fear_greed_df['value_classification'].iloc[-1]

        # Check for Extreme Fear → LONG signal
        if current_value <= config.FEAR_EXTREME:
            strength = self._calculate_fear_strength(current_value)

            return self._create_signal(
                direction=SignalDirection.LONG,
                strength=strength,
                raw_value=float(current_value),
                threshold=float(config.FEAR_EXTREME),
                reasoning=(
                    f"Fear & Greed Index at {current_value} ({classification}). "
                    f"Extreme fear historically precedes market bottoms. "
                    f"'Be greedy when others are fearful.'"
                ),
                metadata={
                    'value': current_value,
                    'classification': classification,
                    'threshold': config.FEAR_EXTREME
                }
            )

        # Check for Extreme Greed → SHORT signal
        elif current_value >= config.GREED_EXTREME:
            strength = self._calculate_greed_strength(current_value)

            return self._create_signal(
                direction=SignalDirection.SHORT,
                strength=strength,
                raw_value=float(current_value),
                threshold=float(config.GREED_EXTREME),
                reasoning=(
                    f"Fear & Greed Index at {current_value} ({classification}). "
                    f"Extreme greed historically precedes market corrections. "
                    f"'Be fearful when others are greedy.'"
                ),
                metadata={
                    'value': current_value,
                    'classification': classification,
                    'threshold': config.GREED_EXTREME
                }
            )

        return None

    def _calculate_fear_strength(self, value: int) -> float:
        """
        Calculate signal strength for fear signals.

        Lower value = more extreme fear = stronger signal.
        20 = 0.5 strength, 0 = 1.0 strength

        Args:
            value: Fear & Greed value (0-20)

        Returns:
            Float from 0.5 to 1.0
        """
        if value >= config.FEAR_EXTREME:
            return 0.5

        # Linear scale from threshold to 0
        strength = 0.5 + 0.5 * (config.FEAR_EXTREME - value) / config.FEAR_EXTREME

        return min(max(strength, 0.5), 1.0)

    def _calculate_greed_strength(self, value: int) -> float:
        """
        Calculate signal strength for greed signals.

        Higher value = more extreme greed = stronger signal.
        80 = 0.5 strength, 100 = 1.0 strength

        Args:
            value: Fear & Greed value (80-100)

        Returns:
            Float from 0.5 to 1.0
        """
        if value <= config.GREED_EXTREME:
            return 0.5

        # Linear scale from threshold to 100
        max_greed = 100
        strength = 0.5 + 0.5 * (value - config.GREED_EXTREME) / (max_greed - config.GREED_EXTREME)

        return min(max(strength, 0.5), 1.0)

    def get_sentiment_status(self, data: Dict[str, Any]) -> str:
        """
        Get human-readable sentiment status.

        Returns one of:
        - "EXTREME_FEAR"
        - "FEAR"
        - "NEUTRAL"
        - "GREED"
        - "EXTREME_GREED"
        - "UNKNOWN"
        """
        current_value = data.get('fear_greed_current')

        if current_value is None:
            return "UNKNOWN"

        if current_value <= config.FEAR_EXTREME:
            return "EXTREME_FEAR"
        elif current_value < 40:
            return "FEAR"
        elif current_value <= 60:
            return "NEUTRAL"
        elif current_value < config.GREED_EXTREME:
            return "GREED"
        else:
            return "EXTREME_GREED"
