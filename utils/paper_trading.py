"""
Paper Trading System.

Simulates trading for testing strategies without real money.
Enhanced with position management, stop loss/take profit, and short support.
"""

import json
import os
from datetime import datetime
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict

from config.settings import config


@dataclass
class Position:
    """Represents an open trading position."""
    symbol: str
    direction: str  # "LONG" or "SHORT"
    entry_price: float
    quantity: float
    entry_time: str
    stop_loss: float
    take_profit: float
    signal_score: float = 0.0
    margin_used: float = 0.0  # For shorts

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Position':
        return cls(**data)


class PaperTrading:
    """
    Paper trading simulator with position management.

    Supports:
    - Long and short positions
    - Stop loss and take profit
    - Position sizing based on signal strength
    - Trade logging with timestamps
    """

    def __init__(self, starting_balance: float = 10000):
        """
        Initialize paper trading.

        Args:
            starting_balance: Starting cash balance
        """
        self.starting_balance = starting_balance
        self.balance = starting_balance
        self.portfolio: Dict[str, float] = {}
        self.positions: Dict[str, Position] = {}
        self.trade_log: List[Dict[str, Any]] = []

        # Configuration
        self.max_position_pct = config.MAX_POSITION_PCT
        self.stop_loss_pct = config.STOP_LOSS_PCT
        self.take_profit_pct = config.TAKE_PROFIT_PCT

    # ==================== Original Methods (Preserved) ====================

    def buy(self, symbol: str, price: float, quantity: float) -> bool:
        """
        Execute a buy order (original method).

        Args:
            symbol: Asset symbol
            price: Current price
            quantity: Amount to buy

        Returns:
            True if successful, False otherwise
        """
        total_cost = price * quantity
        if self.balance >= total_cost:
            self.balance -= total_cost
            if symbol in self.portfolio:
                self.portfolio[symbol] += quantity
            else:
                self.portfolio[symbol] = quantity
            self.log_trade('buy', symbol, price, quantity)
            return True
        else:
            print("Insufficient balance to buy")
            return False

    def sell(self, symbol: str, price: float, quantity: float) -> bool:
        """
        Execute a sell order (original method).

        Args:
            symbol: Asset symbol
            price: Current price
            quantity: Amount to sell

        Returns:
            True if successful, False otherwise
        """
        if symbol in self.portfolio and self.portfolio[symbol] >= quantity:
            self.portfolio[symbol] -= quantity
            total_revenue = price * quantity
            self.balance += total_revenue
            self.log_trade('sell', symbol, price, quantity)
            return True
        else:
            print("Insufficient holdings to sell")
            return False

    def log_trade(self, action: str, symbol: str, price: float, quantity: float,
                  extra_data: Dict[str, Any] = None) -> None:
        """Log a trade with timestamp."""
        trade = {
            'action': action,
            'symbol': symbol,
            'price': price,
            'quantity': quantity,
            'timestamp': datetime.now().isoformat(),
            'balance_after': self.balance
        }
        if extra_data:
            trade.update(extra_data)

        self.trade_log.append(trade)
        self.save_log()

    def save_log(self) -> None:
        """Save trade log to file."""
        with open('paper_trading_log.json', 'w') as file:
            json.dump(self.trade_log, file, indent=4)

    def load_log(self) -> None:
        """Load trade log from file."""
        if os.path.exists('paper_trading_log.json'):
            with open('paper_trading_log.json', 'r') as file:
                self.trade_log = json.load(file)

    # ==================== Enhanced Methods ====================

    def open_position(
        self,
        symbol: str,
        direction: str,
        price: float,
        signal_strength: float = 1.0
    ) -> bool:
        """
        Open a new position based on signal.

        Args:
            symbol: Trading pair symbol
            direction: "LONG" or "SHORT"
            price: Entry price
            signal_strength: 0.0 to 1.0, affects position size

        Returns:
            True if position opened successfully
        """
        # Check if position already exists
        if symbol in self.positions:
            print(f"Position already open for {symbol}")
            return False

        # Calculate position size based on signal strength
        # Min 50%, max 100% of max_position_pct
        size_multiplier = 0.5 + 0.5 * min(max(signal_strength, 0), 1)
        position_value = self.balance * self.max_position_pct * size_multiplier
        quantity = position_value / price

        if direction.upper() == "LONG":
            return self._open_long(symbol, price, quantity, signal_strength)
        elif direction.upper() == "SHORT":
            return self._open_short(symbol, price, quantity, signal_strength)
        else:
            print(f"Invalid direction: {direction}")
            return False

    def _open_long(
        self,
        symbol: str,
        price: float,
        quantity: float,
        signal_strength: float
    ) -> bool:
        """Open a long position."""
        total_cost = price * quantity

        if self.balance < total_cost:
            print("Insufficient balance for long position")
            return False

        self.balance -= total_cost

        # Calculate SL/TP
        stop_loss = price * (1 - self.stop_loss_pct)
        take_profit = price * (1 + self.take_profit_pct)

        # Create position
        position = Position(
            symbol=symbol,
            direction="LONG",
            entry_price=price,
            quantity=quantity,
            entry_time=datetime.now().isoformat(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_score=signal_strength
        )

        self.positions[symbol] = position

        # Update portfolio
        if symbol in self.portfolio:
            self.portfolio[symbol] += quantity
        else:
            self.portfolio[symbol] = quantity

        # Log
        self.log_trade('open_long', symbol, price, quantity, {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'signal_strength': signal_strength
        })

        print(f"Opened LONG {symbol}: {quantity:.6f} @ ${price:,.2f}")
        print(f"  Stop Loss: ${stop_loss:,.2f} | Take Profit: ${take_profit:,.2f}")

        return True

    def _open_short(
        self,
        symbol: str,
        price: float,
        quantity: float,
        signal_strength: float
    ) -> bool:
        """
        Open a short position.

        For paper trading, we track the position without actual borrowing.
        Uses 50% margin requirement.
        """
        margin_required = price * quantity * 0.5  # 50% margin

        if self.balance < margin_required:
            print("Insufficient margin for short position")
            return False

        self.balance -= margin_required

        # Calculate SL/TP (inverted for shorts)
        stop_loss = price * (1 + self.stop_loss_pct)
        take_profit = price * (1 - self.take_profit_pct)

        # Create position
        position = Position(
            symbol=symbol,
            direction="SHORT",
            entry_price=price,
            quantity=quantity,
            entry_time=datetime.now().isoformat(),
            stop_loss=stop_loss,
            take_profit=take_profit,
            signal_score=signal_strength,
            margin_used=margin_required
        )

        self.positions[symbol] = position

        # Log
        self.log_trade('open_short', symbol, price, quantity, {
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'signal_strength': signal_strength,
            'margin_used': margin_required
        })

        print(f"Opened SHORT {symbol}: {quantity:.6f} @ ${price:,.2f}")
        print(f"  Stop Loss: ${stop_loss:,.2f} | Take Profit: ${take_profit:,.2f}")

        return True

    def check_stop_loss_take_profit(
        self,
        symbol: str,
        current_price: float
    ) -> Optional[str]:
        """
        Check if position should be closed due to SL/TP.

        Args:
            symbol: Position symbol
            current_price: Current market price

        Returns:
            Exit reason if should close, None otherwise
        """
        if symbol not in self.positions:
            return None

        pos = self.positions[symbol]

        if pos.direction == "LONG":
            if current_price <= pos.stop_loss:
                return "STOP_LOSS"
            elif current_price >= pos.take_profit:
                return "TAKE_PROFIT"

        elif pos.direction == "SHORT":
            if current_price >= pos.stop_loss:
                return "STOP_LOSS"
            elif current_price <= pos.take_profit:
                return "TAKE_PROFIT"

        return None

    def close_position(
        self,
        symbol: str,
        price: float,
        reason: str = "MANUAL"
    ) -> Optional[float]:
        """
        Close an open position.

        Args:
            symbol: Position symbol
            price: Exit price
            reason: Reason for closing

        Returns:
            P&L amount, or None if no position
        """
        if symbol not in self.positions:
            print(f"No position found for {symbol}")
            return None

        pos = self.positions[symbol]
        pnl = 0.0

        if pos.direction == "LONG":
            pnl = (price - pos.entry_price) * pos.quantity
            # Return capital + P&L
            self.balance += (pos.entry_price * pos.quantity) + pnl
            # Update portfolio
            if symbol in self.portfolio:
                self.portfolio[symbol] -= pos.quantity

        elif pos.direction == "SHORT":
            pnl = (pos.entry_price - price) * pos.quantity
            # Return margin + P&L
            self.balance += pos.margin_used + pnl

        pnl_pct = pnl / (pos.entry_price * pos.quantity) * 100

        # Log
        self.log_trade(f'close_{pos.direction.lower()}', symbol, price, pos.quantity, {
            'exit_reason': reason,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'entry_price': pos.entry_price
        })

        print(f"Closed {pos.direction} {symbol} @ ${price:,.2f}")
        print(f"  P&L: ${pnl:+,.2f} ({pnl_pct:+.2f}%) | Reason: {reason}")

        # Remove position
        del self.positions[symbol]

        return pnl

    def check_and_close_positions(self, prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Check all positions for SL/TP and close if triggered.

        Args:
            prices: Dict of symbol -> current price

        Returns:
            List of closed position results
        """
        closed = []

        for symbol in list(self.positions.keys()):
            if symbol not in prices:
                continue

            current_price = prices[symbol]
            exit_reason = self.check_stop_loss_take_profit(symbol, current_price)

            if exit_reason:
                pnl = self.close_position(symbol, current_price, exit_reason)
                closed.append({
                    'symbol': symbol,
                    'reason': exit_reason,
                    'pnl': pnl
                })

        return closed

    def get_equity(self, prices: Dict[str, float]) -> float:
        """
        Calculate total equity (balance + unrealized P&L).

        Args:
            prices: Dict of symbol -> current price

        Returns:
            Total equity value
        """
        equity = self.balance

        for symbol, pos in self.positions.items():
            current_price = prices.get(symbol, pos.entry_price)

            if pos.direction == "LONG":
                unrealized = (current_price - pos.entry_price) * pos.quantity
            else:  # SHORT
                unrealized = (pos.entry_price - current_price) * pos.quantity

            equity += unrealized

        return equity

    def get_status(self, prices: Dict[str, float] = None) -> Dict[str, Any]:
        """Get current trading status."""
        prices = prices or {}

        status = {
            'balance': self.balance,
            'starting_balance': self.starting_balance,
            'total_trades': len(self.trade_log),
            'open_positions': len(self.positions),
            'positions': {}
        }

        for symbol, pos in self.positions.items():
            current_price = prices.get(symbol, pos.entry_price)

            if pos.direction == "LONG":
                unrealized = (current_price - pos.entry_price) * pos.quantity
            else:
                unrealized = (pos.entry_price - current_price) * pos.quantity

            status['positions'][symbol] = {
                'direction': pos.direction,
                'entry_price': pos.entry_price,
                'current_price': current_price,
                'quantity': pos.quantity,
                'unrealized_pnl': unrealized,
                'stop_loss': pos.stop_loss,
                'take_profit': pos.take_profit
            }

        if prices:
            status['equity'] = self.get_equity(prices)

        return status

    def print_status(self, prices: Dict[str, float] = None) -> None:
        """Print formatted status."""
        status = self.get_status(prices)

        print("\n" + "=" * 50)
        print("PAPER TRADING STATUS")
        print("=" * 50)
        print(f"Cash Balance: ${status['balance']:,.2f}")
        print(f"Starting Balance: ${status['starting_balance']:,.2f}")

        if 'equity' in status:
            print(f"Total Equity: ${status['equity']:,.2f}")
            pnl = status['equity'] - status['starting_balance']
            print(f"Total P&L: ${pnl:+,.2f} ({pnl/status['starting_balance']*100:+.2f}%)")

        print(f"\nTotal Trades: {status['total_trades']}")
        print(f"Open Positions: {status['open_positions']}")

        if status['positions']:
            print("\nOpen Positions:")
            print("-" * 40)
            for symbol, pos_info in status['positions'].items():
                print(f"  {symbol} ({pos_info['direction']})")
                print(f"    Entry: ${pos_info['entry_price']:,.2f}")
                print(f"    Current: ${pos_info['current_price']:,.2f}")
                print(f"    Unrealized: ${pos_info['unrealized_pnl']:+,.2f}")

        print("=" * 50 + "\n")

    def save_state(self, filepath: str = 'paper_trading_state.json') -> None:
        """Save complete state to file."""
        state = {
            'balance': self.balance,
            'starting_balance': self.starting_balance,
            'portfolio': self.portfolio,
            'positions': {k: v.to_dict() for k, v in self.positions.items()},
            'trade_log': self.trade_log
        }
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=4)

    def load_state(self, filepath: str = 'paper_trading_state.json') -> bool:
        """Load complete state from file."""
        if not os.path.exists(filepath):
            return False

        with open(filepath, 'r') as f:
            state = json.load(f)

        self.balance = state.get('balance', self.starting_balance)
        self.starting_balance = state.get('starting_balance', self.starting_balance)
        self.portfolio = state.get('portfolio', {})
        self.trade_log = state.get('trade_log', [])

        # Reconstruct positions
        self.positions = {}
        for symbol, pos_data in state.get('positions', {}).items():
            self.positions[symbol] = Position.from_dict(pos_data)

        return True
