"""
Backtest Engine for Market Structure Strategy.

Simulates trading based on historical signal data with:
- Position management (entry, exit, sizing)
- Stop loss and take profit
- Transaction costs
- Performance tracking
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
import pandas as pd
import numpy as np

from signals.base_signal import SignalDirection
from signals.signal_aggregator import SignalAggregator, AggregatedSignal
from .metrics import calculate_metrics, PerformanceMetrics
from config.settings import config


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_capital: float = 10000.0
    position_size_pct: float = 0.10      # 10% of capital per trade
    max_positions: int = 1               # Max concurrent positions
    stop_loss_pct: float = 0.02          # 2% stop loss
    take_profit_pct: float = 0.04        # 4% take profit
    trading_fee_pct: float = 0.001       # 0.1% taker fee
    signal_threshold: float = 4.0        # Minimum signal score


@dataclass
class Trade:
    """Represents a single trade."""
    entry_time: pd.Timestamp
    exit_time: Optional[pd.Timestamp]
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    exit_price: Optional[float]
    size: float
    pnl: float = 0.0
    pnl_pct: float = 0.0
    exit_reason: str = ""
    signal_score: float = 0.0
    signals_used: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'entry_time': self.entry_time.isoformat() if self.entry_time else None,
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'size': self.size,
            'pnl': self.pnl,
            'pnl_pct': self.pnl_pct,
            'exit_reason': self.exit_reason,
            'signal_score': self.signal_score
        }


@dataclass
class BacktestResult:
    """Results from backtesting."""
    trades: List[Trade]
    equity_curve: pd.Series
    metrics: PerformanceMetrics
    config: BacktestConfig

    def print_summary(self) -> None:
        """Print performance summary."""
        print(self.metrics.to_string())

        print("\nTRADE HISTORY (last 10):")
        print("-" * 80)
        for trade in self.trades[-10:]:
            print(
                f"  {trade.entry_time.strftime('%Y-%m-%d %H:%M')} | "
                f"{trade.direction:5} | "
                f"Entry: ${trade.entry_price:,.0f} | "
                f"Exit: ${trade.exit_price:,.0f} | "
                f"P&L: ${trade.pnl:+,.2f} ({trade.pnl_pct:+.2%}) | "
                f"{trade.exit_reason}"
            )


class BacktestEngine:
    """
    Backtesting engine for market structure strategy.

    Simulates trading based on historical signal data.
    """

    def __init__(self, backtest_config: BacktestConfig = None):
        """
        Initialize backtest engine.

        Args:
            backtest_config: Configuration for backtest parameters
        """
        self.config = backtest_config or BacktestConfig()
        self.signal_aggregator = SignalAggregator(
            required_score=self.config.signal_threshold
        )

        # State
        self.trades: List[Trade] = []
        self.equity_curve: List[float] = []
        self.current_capital: float = self.config.initial_capital
        self.open_position: Optional[Trade] = None

    def run(self, aligned_data: pd.DataFrame) -> BacktestResult:
        """
        Run backtest on aligned historical data.

        Args:
            aligned_data: DataFrame with columns:
                - price: Current price
                - fundingRate: Funding rate
                - value: Fear & Greed value
                - value_classification: Fear & Greed classification
                - total_volume, imbalance: Liquidation data

        Returns:
            BacktestResult with all trades and metrics
        """
        # Reset state
        self.trades = []
        self.equity_curve = []
        self.current_capital = self.config.initial_capital
        self.open_position = None

        timestamps = []

        for i in range(len(aligned_data)):
            row = aligned_data.iloc[i]
            timestamp = aligned_data.index[i]
            current_price = row['price']

            timestamps.append(timestamp)

            # Check stop loss / take profit on open position
            if self.open_position:
                exit_reason = self._check_exits(current_price)
                if exit_reason:
                    self._exit_position(current_price, timestamp, exit_reason)

            # Skip if we have an open position (single position limit)
            if self.open_position:
                self._update_equity(current_price)
                continue

            # Generate signal for this point
            market_data = self._row_to_market_data(row, aligned_data, i)
            signal = self.signal_aggregator.aggregate(market_data)

            # Enter new position if valid signal
            if signal.is_valid:
                self._enter_position(signal, current_price, timestamp)

            # Update equity curve
            self._update_equity(current_price)

        # Close any remaining position at end
        if self.open_position:
            final_price = aligned_data['price'].iloc[-1]
            final_time = aligned_data.index[-1]
            self._exit_position(final_price, final_time, "END_OF_BACKTEST")

        # Create equity series
        equity_series = pd.Series(
            self.equity_curve,
            index=timestamps[:len(self.equity_curve)]
        )

        # Calculate metrics
        metrics = calculate_metrics(
            self.trades,
            equity_series,
            self.config.initial_capital
        )

        return BacktestResult(
            trades=self.trades,
            equity_curve=equity_series,
            metrics=metrics,
            config=self.config
        )

    def _row_to_market_data(
        self,
        row: pd.Series,
        full_data: pd.DataFrame,
        current_idx: int
    ) -> Dict[str, Any]:
        """
        Convert a data row to the market_data dict expected by SignalAggregator.
        """
        # Get lookback data for funding (last 3 periods ~ 24h)
        lookback = min(current_idx + 1, 10)
        funding_data = full_data.iloc[max(0, current_idx - lookback):current_idx + 1]

        market_data = {
            'timestamp': row.name
        }

        # Funding rate
        if 'fundingRate' in funding_data.columns:
            market_data['binance_funding'] = pd.DataFrame({
                'fundingRate': funding_data['fundingRate']
            })

        # Fear & Greed
        if 'value' in row and pd.notna(row['value']):
            market_data['fear_greed_current'] = int(row['value'])
            market_data['fear_greed'] = pd.DataFrame({
                'value': [row['value']],
                'value_classification': [row.get('value_classification', 'Unknown')]
            })

        # Liquidations
        if 'imbalance' in row and pd.notna(row['imbalance']):
            market_data['liquidation_analysis'] = {
                'total_volume': row.get('total_volume', 0),
                'imbalance': row['imbalance'],
                'long_liquidations': row.get('long_liquidations', 0),
                'short_liquidations': row.get('short_liquidations', 0)
            }

        return market_data

    def _enter_position(
        self,
        signal: AggregatedSignal,
        price: float,
        timestamp: pd.Timestamp
    ) -> None:
        """Enter a new position."""
        # Calculate position size
        position_value = self.current_capital * self.config.position_size_pct
        size = position_value / price

        # Apply entry fee
        fee = position_value * self.config.trading_fee_pct
        self.current_capital -= fee

        # Create trade
        self.open_position = Trade(
            entry_time=timestamp,
            exit_time=None,
            direction=signal.direction.name,
            entry_price=price,
            exit_price=None,
            size=size,
            signal_score=signal.total_score,
            signals_used=[s.source for s in signal.signals]
        )

    def _check_exits(self, current_price: float) -> Optional[str]:
        """Check if position should be closed due to SL/TP."""
        if not self.open_position:
            return None

        entry = self.open_position.entry_price

        if self.open_position.direction == "LONG":
            pnl_pct = (current_price - entry) / entry
            if pnl_pct <= -self.config.stop_loss_pct:
                return "STOP_LOSS"
            elif pnl_pct >= self.config.take_profit_pct:
                return "TAKE_PROFIT"

        elif self.open_position.direction == "SHORT":
            pnl_pct = (entry - current_price) / entry
            if pnl_pct <= -self.config.stop_loss_pct:
                return "STOP_LOSS"
            elif pnl_pct >= self.config.take_profit_pct:
                return "TAKE_PROFIT"

        return None

    def _exit_position(
        self,
        price: float,
        timestamp: pd.Timestamp,
        reason: str
    ) -> None:
        """Exit the current position."""
        if not self.open_position:
            return

        trade = self.open_position
        trade.exit_time = timestamp
        trade.exit_price = price
        trade.exit_reason = reason

        # Calculate P&L
        if trade.direction == "LONG":
            trade.pnl = (price - trade.entry_price) * trade.size
            trade.pnl_pct = (price - trade.entry_price) / trade.entry_price
        else:  # SHORT
            trade.pnl = (trade.entry_price - price) * trade.size
            trade.pnl_pct = (trade.entry_price - price) / trade.entry_price

        # Apply exit fee
        exit_value = price * trade.size
        fee = exit_value * self.config.trading_fee_pct
        trade.pnl -= fee

        # Update capital
        position_value = trade.entry_price * trade.size
        self.current_capital += position_value + trade.pnl

        # Record trade
        self.trades.append(trade)
        self.open_position = None

    def _update_equity(self, current_price: float) -> None:
        """Update equity curve with unrealized P&L."""
        unrealized = 0

        if self.open_position:
            pos = self.open_position
            if pos.direction == "LONG":
                unrealized = (current_price - pos.entry_price) * pos.size
            else:
                unrealized = (pos.entry_price - current_price) * pos.size

        self.equity_curve.append(self.current_capital + unrealized)
