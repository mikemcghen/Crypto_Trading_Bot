"""
Performance Metrics for Backtesting.

Calculates standard trading performance metrics:
- Returns and P&L
- Sharpe Ratio
- Maximum Drawdown
- Win Rate
- Profit Factor
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Container for all performance metrics."""

    # Returns
    total_return_pct: float
    annualized_return_pct: float
    total_pnl: float

    # Risk-adjusted
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float

    # Drawdown
    max_drawdown_pct: float
    max_drawdown_duration_days: int

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float

    # Profit/Loss
    gross_profit: float
    gross_loss: float
    profit_factor: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float

    # Duration
    avg_trade_duration_hours: float

    def __str__(self) -> str:
        return self.to_string()

    def to_string(self) -> str:
        """Format metrics as readable string."""
        lines = [
            "=" * 50,
            "BACKTEST PERFORMANCE METRICS",
            "=" * 50,
            "",
            "RETURNS",
            f"  Total Return: {self.total_return_pct:.2%}",
            f"  Annualized Return: {self.annualized_return_pct:.2%}",
            f"  Total P&L: ${self.total_pnl:,.2f}",
            "",
            "RISK-ADJUSTED",
            f"  Sharpe Ratio: {self.sharpe_ratio:.2f}",
            f"  Sortino Ratio: {self.sortino_ratio:.2f}",
            f"  Calmar Ratio: {self.calmar_ratio:.2f}",
            "",
            "DRAWDOWN",
            f"  Max Drawdown: {self.max_drawdown_pct:.2%}",
            f"  Max DD Duration: {self.max_drawdown_duration_days} days",
            "",
            "TRADE STATISTICS",
            f"  Total Trades: {self.total_trades}",
            f"  Winning: {self.winning_trades} | Losing: {self.losing_trades}",
            f"  Win Rate: {self.win_rate:.2%}",
            "",
            "PROFIT & LOSS",
            f"  Gross Profit: ${self.gross_profit:,.2f}",
            f"  Gross Loss: ${self.gross_loss:,.2f}",
            f"  Profit Factor: {self.profit_factor:.2f}",
            f"  Avg Win: ${self.avg_win:,.2f} | Avg Loss: ${self.avg_loss:,.2f}",
            f"  Largest Win: ${self.largest_win:,.2f} | Largest Loss: ${self.largest_loss:,.2f}",
            "",
            "DURATION",
            f"  Avg Trade Duration: {self.avg_trade_duration_hours:.1f} hours",
            "=" * 50
        ]
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_return_pct': self.total_return_pct,
            'annualized_return_pct': self.annualized_return_pct,
            'total_pnl': self.total_pnl,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'calmar_ratio': self.calmar_ratio,
            'max_drawdown_pct': self.max_drawdown_pct,
            'max_drawdown_duration_days': self.max_drawdown_duration_days,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'gross_profit': self.gross_profit,
            'gross_loss': self.gross_loss,
            'profit_factor': self.profit_factor,
            'avg_win': self.avg_win,
            'avg_loss': self.avg_loss,
            'largest_win': self.largest_win,
            'largest_loss': self.largest_loss,
            'avg_trade_duration_hours': self.avg_trade_duration_hours
        }


def calculate_metrics(
    trades: List[Any],  # List of Trade objects
    equity_curve: pd.Series,
    initial_capital: float,
    trading_days_per_year: int = 365  # Crypto trades 24/7
) -> PerformanceMetrics:
    """
    Calculate all performance metrics from backtest results.

    Args:
        trades: List of completed Trade objects
        equity_curve: Series of equity values over time
        initial_capital: Starting capital
        trading_days_per_year: For annualization (365 for crypto)

    Returns:
        PerformanceMetrics object with all calculations
    """
    # Handle empty results
    if not trades or equity_curve.empty:
        return PerformanceMetrics(
            total_return_pct=0.0, annualized_return_pct=0.0, total_pnl=0.0,
            sharpe_ratio=0.0, sortino_ratio=0.0, calmar_ratio=0.0,
            max_drawdown_pct=0.0, max_drawdown_duration_days=0,
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
            gross_profit=0.0, gross_loss=0.0, profit_factor=0.0,
            avg_win=0.0, avg_loss=0.0, largest_win=0.0, largest_loss=0.0,
            avg_trade_duration_hours=0.0
        )

    # Calculate returns
    final_capital = equity_curve.iloc[-1]
    total_return = (final_capital - initial_capital) / initial_capital
    total_pnl = final_capital - initial_capital

    # Calculate annualized return
    num_days = (equity_curve.index[-1] - equity_curve.index[0]).days
    if num_days > 0:
        annualized_return = (1 + total_return) ** (trading_days_per_year / num_days) - 1
    else:
        annualized_return = 0.0

    # Calculate daily returns for Sharpe/Sortino
    daily_equity = equity_curve.resample('1D').last().dropna()
    daily_returns = daily_equity.pct_change().dropna()

    # Sharpe Ratio (assuming 0% risk-free rate for crypto)
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(trading_days_per_year)
    else:
        sharpe = 0.0

    # Sortino Ratio (only downside deviation)
    negative_returns = daily_returns[daily_returns < 0]
    if len(negative_returns) > 1:
        downside_std = negative_returns.std()
        sortino = (daily_returns.mean() / downside_std) * np.sqrt(trading_days_per_year) if downside_std > 0 else 0.0
    else:
        sortino = sharpe  # No downside, use Sharpe

    # Maximum Drawdown
    rolling_max = equity_curve.expanding().max()
    drawdown = (equity_curve - rolling_max) / rolling_max
    max_dd = drawdown.min()

    # Max drawdown duration
    in_drawdown = equity_curve < rolling_max
    dd_groups = (~in_drawdown).cumsum()
    dd_durations = in_drawdown.groupby(dd_groups).sum()
    max_dd_duration = int(dd_durations.max()) if len(dd_durations) > 0 else 0

    # Calmar Ratio (annualized return / max drawdown)
    calmar = abs(annualized_return / max_dd) if max_dd < 0 else 0.0

    # Trade statistics
    pnls = [t.pnl for t in trades]
    winning_trades = [t for t in trades if t.pnl > 0]
    losing_trades = [t for t in trades if t.pnl <= 0]

    win_rate = len(winning_trades) / len(trades) if trades else 0.0

    gross_profit = sum(t.pnl for t in winning_trades)
    gross_loss = abs(sum(t.pnl for t in losing_trades))

    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    avg_win = gross_profit / len(winning_trades) if winning_trades else 0.0
    avg_loss = gross_loss / len(losing_trades) if losing_trades else 0.0

    largest_win = max(pnls) if pnls else 0.0
    largest_loss = min(pnls) if pnls else 0.0

    # Average trade duration
    durations = []
    for t in trades:
        if t.exit_time and t.entry_time:
            duration = (t.exit_time - t.entry_time).total_seconds() / 3600  # Hours
            durations.append(duration)
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return PerformanceMetrics(
        total_return_pct=total_return,
        annualized_return_pct=annualized_return,
        total_pnl=total_pnl,
        sharpe_ratio=sharpe,
        sortino_ratio=sortino,
        calmar_ratio=calmar,
        max_drawdown_pct=max_dd,
        max_drawdown_duration_days=max_dd_duration,
        total_trades=len(trades),
        winning_trades=len(winning_trades),
        losing_trades=len(losing_trades),
        win_rate=win_rate,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        profit_factor=profit_factor,
        avg_win=avg_win,
        avg_loss=avg_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        avg_trade_duration_hours=avg_duration
    )
