"""
Base signal classes and data structures.

Defines the interface for all signal generators and the
data structures they produce.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any, Dict
import pandas as pd


class SignalDirection(Enum):
    """Direction of a trading signal."""
    LONG = 1      # Buy / Go long
    SHORT = -1    # Sell / Go short
    NEUTRAL = 0   # No action


@dataclass
class TradingSignal:
    """
    Represents a trading signal from a single indicator.

    Attributes:
        source: Name of the signal generator (e.g., "funding_rate")
        direction: LONG, SHORT, or NEUTRAL
        strength: Signal strength from 0.0 to 1.0
        score_contribution: Points contributed to total score
        timestamp: When the signal was generated
        raw_value: Original indicator value
        threshold_used: Threshold that triggered the signal
        reasoning: Human-readable explanation
        metadata: Additional data for debugging
    """
    source: str
    direction: SignalDirection
    strength: float
    score_contribution: float
    timestamp: pd.Timestamp
    raw_value: float
    threshold_used: float
    reasoning: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        direction_str = self.direction.name
        return (
            f"{self.source}: {direction_str} "
            f"(strength={self.strength:.2f}, score={self.score_contribution:.2f})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'source': self.source,
            'direction': self.direction.name,
            'strength': self.strength,
            'score_contribution': self.score_contribution,
            'timestamp': self.timestamp.isoformat(),
            'raw_value': self.raw_value,
            'threshold_used': self.threshold_used,
            'reasoning': self.reasoning,
            'metadata': self.metadata
        }


class BaseSignal(ABC):
    """
    Abstract base class for all signal generators.

    Each signal generator:
    1. Takes market data as input
    2. Evaluates against thresholds
    3. Returns a TradingSignal or None
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this signal type."""
        pass

    @property
    @abstractmethod
    def max_score(self) -> float:
        """Maximum score this signal can contribute."""
        pass

    @abstractmethod
    def generate(self, data: Dict[str, Any]) -> Optional[TradingSignal]:
        """
        Generate a trading signal from market data.

        Args:
            data: Market data dict from aggregator

        Returns:
            TradingSignal if conditions are met, None otherwise
        """
        pass

    def _create_signal(
        self,
        direction: SignalDirection,
        strength: float,
        raw_value: float,
        threshold: float,
        reasoning: str,
        metadata: Dict[str, Any] = None
    ) -> TradingSignal:
        """
        Helper to create a TradingSignal with common fields filled in.

        Args:
            direction: Signal direction
            strength: 0.0 to 1.0
            raw_value: The indicator value
            threshold: Threshold that triggered
            reasoning: Explanation
            metadata: Optional additional data
        """
        return TradingSignal(
            source=self.name,
            direction=direction,
            strength=min(max(strength, 0.0), 1.0),  # Clamp to [0, 1]
            score_contribution=min(max(strength, 0.0), 1.0) * self.max_score,
            timestamp=pd.Timestamp.now(),
            raw_value=raw_value,
            threshold_used=threshold,
            reasoning=reasoning,
            metadata=metadata or {}
        )
