"""
Signal Logger - Logs all trading signals to a CSV file for analysis.

Tracks:
- Timestamp
- Signal direction
- Total score
- Component scores
- Market conditions at signal time
"""

import csv
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional


class SignalLogger:
    """Logs trading signals to CSV for later analysis."""

    def __init__(self, log_dir: str = "logs"):
        """
        Initialize signal logger.

        Args:
            log_dir: Directory to store log files
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "signals.csv"
        self._ensure_header()

    def _ensure_header(self) -> None:
        """Create CSV header if file doesn't exist."""
        if not self.log_file.exists():
            with open(self.log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'timestamp',
                    'symbol',
                    'direction',
                    'total_score',
                    'is_valid',
                    'funding_score',
                    'liquidation_score',
                    'fear_greed_score',
                    'oi_confluence_score',
                    'funding_rate',
                    'fear_greed_value',
                    'liquidation_imbalance',
                    'funding_source',
                    'btc_price'
                ])

    def log_signal(
        self,
        signal: Any,
        market_summary: Dict[str, Any],
        btc_price: Optional[float] = None
    ) -> None:
        """
        Log a trading signal to CSV.

        Args:
            signal: TradingSignal object
            market_summary: Market data summary dict
            btc_price: Current BTC price (optional)
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Extract component scores from signal
        # signal.signals contains TradingSignal objects with .source and .score_contribution
        component_scores = {}
        if hasattr(signal, 'signals') and signal.signals:
            for s in signal.signals:
                component_scores[s.source] = s.score_contribution

        # Use signal.symbol if available, otherwise fall back to market_summary
        symbol = getattr(signal, 'symbol', market_summary.get('symbol', 'BTCUSDT'))

        row = [
            timestamp,
            symbol,
            signal.direction.name if signal.direction else 'NEUTRAL',
            signal.total_score,
            signal.is_valid,
            component_scores.get('funding_rate', component_scores.get('Funding Rate', 0.0)),
            component_scores.get('liquidation', component_scores.get('Liquidation', 0.0)),
            component_scores.get('fear_greed', component_scores.get('Fear & Greed', 0.0)),
            component_scores.get('oi_confluence', component_scores.get('OI + Funding Confluence', 0.0)),
            market_summary.get('funding_rate', 0.0),
            market_summary.get('fear_greed_value', 50),
            market_summary.get('liquidation_imbalance', 0.0),
            market_summary.get('funding_source', 'Unknown'),
            btc_price or 0.0
        ]

        with open(self.log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)

    def get_recent_signals(self, n: int = 10) -> list:
        """
        Get the N most recent logged signals.

        Args:
            n: Number of signals to return

        Returns:
            List of signal dicts
        """
        if not self.log_file.exists():
            return []

        signals = []
        with open(self.log_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            signals = list(reader)

        return signals[-n:] if signals else []

    def get_signal_stats(self) -> Dict[str, Any]:
        """
        Get statistics about logged signals.

        Returns:
            Dict with signal statistics
        """
        if not self.log_file.exists():
            return {'total_signals': 0}

        signals = []
        with open(self.log_file, 'r', newline='') as f:
            reader = csv.DictReader(f)
            signals = list(reader)

        if not signals:
            return {'total_signals': 0}

        valid_signals = [s for s in signals if s['is_valid'] == 'True']
        long_signals = [s for s in valid_signals if s['direction'] == 'LONG']
        short_signals = [s for s in valid_signals if s['direction'] == 'SHORT']

        return {
            'total_signals': len(signals),
            'valid_signals': len(valid_signals),
            'long_signals': len(long_signals),
            'short_signals': len(short_signals),
            'valid_rate': len(valid_signals) / len(signals) if signals else 0,
            'first_signal': signals[0]['timestamp'] if signals else None,
            'last_signal': signals[-1]['timestamp'] if signals else None
        }
