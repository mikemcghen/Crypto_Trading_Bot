"""
Signal Aggregator.

Combines signals from all generators into a final trading decision.
Uses a score-based system requiring minimum confluence before trading.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd

from .base_signal import SignalDirection, TradingSignal
from .funding_signal import FundingRateSignal
from .liquidation_signal import LiquidationSignal
from .fear_greed_signal import FearGreedSignal
from config.settings import config


@dataclass
class AggregatedSignal:
    """
    Combined signal from all sources.

    Attributes:
        symbol: Coin symbol this signal is for (e.g., 'BTC')
        direction: Final signal direction (LONG, SHORT, NEUTRAL)
        total_score: Combined score from all signals
        required_score: Minimum score needed to trade
        is_valid: Whether score meets threshold
        signals: List of individual signals that contributed
        long_score: Total score for long signals
        short_score: Total score for short signals
        timestamp: When analysis was performed
        summary: Human-readable summary
    """
    symbol: str
    direction: SignalDirection
    total_score: float
    required_score: float
    is_valid: bool
    signals: List[TradingSignal]
    long_score: float
    short_score: float
    timestamp: pd.Timestamp
    summary: str

    def __str__(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"AggregatedSignal({self.symbol}, {self.direction.name}, "
            f"score={self.total_score:.2f}/{self.required_score}, {status})"
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'direction': self.direction.name,
            'total_score': self.total_score,
            'required_score': self.required_score,
            'is_valid': self.is_valid,
            'long_score': self.long_score,
            'short_score': self.short_score,
            'timestamp': self.timestamp.isoformat(),
            'signals': [s.to_dict() for s in self.signals],
            'summary': self.summary
        }


class SignalAggregator:
    """
    Combines signals from multiple sources into a trading decision.

    Score System:
    - Funding Rate: 0-2 points
    - Liquidations: 0-2 points
    - Fear & Greed: 0-1.5 points

    Maximum possible: 5.5 points (without OI confluence)
    Trading threshold: 4 points (configurable)
    """

    def __init__(self, required_score: float = None):
        """
        Initialize with all signal generators.

        Args:
            required_score: Minimum score to generate valid signal
        """
        self.required_score = required_score or config.REQUIRED_SIGNAL_SCORE

        # Initialize signal generators
        self.funding_signal = FundingRateSignal()
        self.liquidation_signal = LiquidationSignal()
        self.fear_greed_signal = FearGreedSignal()

    def aggregate(self, market_data: Dict[str, Any], symbol: str = "BTC") -> AggregatedSignal:
        """
        Aggregate all signals into a trading decision.

        Args:
            market_data: Dict containing DataFrames from all collectors
            symbol: Coin symbol being analyzed (e.g., 'BTC', 'ETH')

        Returns:
            AggregatedSignal with combined analysis
        """
        signals: List[TradingSignal] = []
        timestamp = pd.Timestamp.now()

        # Generate individual signals
        funding_sig = self.funding_signal.generate(market_data)
        if funding_sig:
            signals.append(funding_sig)

        liq_sig = self.liquidation_signal.generate(market_data)
        if liq_sig:
            signals.append(liq_sig)

        fg_sig = self.fear_greed_signal.generate(market_data)
        if fg_sig:
            signals.append(fg_sig)

        # Calculate scores by direction
        long_score = sum(
            s.score_contribution for s in signals
            if s.direction == SignalDirection.LONG
        )
        short_score = sum(
            s.score_contribution for s in signals
            if s.direction == SignalDirection.SHORT
        )

        # Determine final direction
        # Net score approach: direction with higher score wins if it meets threshold
        if long_score >= self.required_score and long_score > short_score:
            direction = SignalDirection.LONG
            total_score = long_score
        elif short_score >= self.required_score and short_score > long_score:
            direction = SignalDirection.SHORT
            total_score = short_score
        else:
            direction = SignalDirection.NEUTRAL
            total_score = max(long_score, short_score)

        is_valid = total_score >= self.required_score

        # Build summary
        summary = self._build_summary(
            symbol, direction, total_score, long_score, short_score, signals, is_valid
        )

        return AggregatedSignal(
            symbol=symbol,
            direction=direction,
            total_score=total_score,
            required_score=self.required_score,
            is_valid=is_valid,
            signals=signals,
            long_score=long_score,
            short_score=short_score,
            timestamp=timestamp,
            summary=summary
        )

    def _build_summary(
        self,
        symbol: str,
        direction: SignalDirection,
        total_score: float,
        long_score: float,
        short_score: float,
        signals: List[TradingSignal],
        is_valid: bool
    ) -> str:
        """Build human-readable summary of the analysis."""
        lines = [
            "=" * 60,
            f"SIGNAL AGGREGATION SUMMARY - {symbol}",
            "=" * 60,
            "",
            f"Symbol: {symbol}",
            f"Direction: {direction.name}",
            f"Total Score: {total_score:.2f} / {self.required_score} required",
            f"Valid Signal: {'YES' if is_valid else 'NO'}",
            "",
            f"Long Score:  {long_score:.2f}",
            f"Short Score: {short_score:.2f}",
            "",
            "Individual Signals:",
            "-" * 40
        ]

        if signals:
            for sig in signals:
                lines.append(
                    f"  [{sig.direction.name:5}] {sig.source}: "
                    f"+{sig.score_contribution:.2f} pts (strength: {sig.strength:.2f})"
                )
                lines.append(f"          {sig.reasoning[:70]}...")
        else:
            lines.append("  No signals triggered")

        lines.append("-" * 40)

        if is_valid:
            lines.append(f"\nRECOMMENDATION: {direction.name} position")
        else:
            lines.append("\nRECOMMENDATION: No trade (insufficient confluence)")

        lines.append("=" * 60)

        return "\n".join(lines)

    def get_signal_breakdown(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed breakdown of all signal statuses.

        Useful for debugging and monitoring.

        Returns:
            Dict with status of each signal type
        """
        return {
            'funding': self.funding_signal.get_funding_status(market_data),
            'liquidations': self.liquidation_signal.get_liquidation_status(market_data),
            'fear_greed': self.fear_greed_signal.get_sentiment_status(market_data)
        }

    def analyze_and_print(self, market_data: Dict[str, Any]) -> AggregatedSignal:
        """Aggregate signals and print the summary."""
        signal = self.aggregate(market_data)
        print(signal.summary)
        return signal
