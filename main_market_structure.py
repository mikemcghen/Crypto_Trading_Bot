#!/usr/bin/env python3
"""
Market Structure Trading Bot - Main Entry Point

This bot trades based on market structure signals:
- Funding rate extremes (contrarian)
- Liquidation cascades (fade the sweep)
- Fear & Greed Index (contrarian)

Supports multi-coin analysis: BTC, ETH, SOL, DOGE, XRP, AVAX, LINK, PEPE
Only trades when multiple signals align (score >= threshold).
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from collectors.aggregator import MarketDataAggregator
from signals.signal_aggregator import SignalAggregator, AggregatedSignal
from utils.paper_trading import PaperTrading
from utils.robinhood_api import fetch_real_time_data, fetch_multi_coin_prices
from utils.signal_logger import SignalLogger
from config.symbols import WATCHLIST, get_trading_symbol, coin_from_trading_symbol
from config.settings import config

# Initialize signal logger
signal_logger = SignalLogger()


def run_analysis(symbol: str = "BTCUSDT", coin: str = None, price: float = None) -> AggregatedSignal:
    """
    Run market structure analysis for a single coin.

    Args:
        symbol: Trading pair to analyze (e.g., BTCUSDT)
        coin: Short coin name (e.g., BTC). If None, derived from symbol.
        price: Current price (optional, for logging)

    Returns:
        AggregatedSignal with analysis results
    """
    if coin is None:
        coin = coin_from_trading_symbol(symbol)

    print("\n" + "=" * 60)
    print(f"MARKET STRUCTURE ANALYSIS - {coin}")
    print(f"Symbol: {symbol}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Fetch market data
    print("\nFetching market data...")
    with MarketDataAggregator() as aggregator:
        market_data = aggregator.fetch_all(symbol)
        market_summary = aggregator.get_summary(symbol)
        aggregator.print_summary(symbol)

    # Generate signals (pass coin symbol)
    print("\nAnalyzing signals...")
    signal_agg = SignalAggregator()
    signal = signal_agg.aggregate(market_data, symbol=coin)
    print(signal.summary)

    # Log the signal
    signal_logger.log_signal(signal, market_summary, price)
    print(f"\nSignal logged to logs/signals.csv")

    return signal


def run_multi_coin_analysis(coins: List[str] = None) -> Dict[str, AggregatedSignal]:
    """
    Run market structure analysis for multiple coins.

    Args:
        coins: List of coin symbols to analyze. Defaults to WATCHLIST.

    Returns:
        Dict mapping coin symbol to AggregatedSignal
    """
    if coins is None:
        coins = WATCHLIST

    print("\n" + "=" * 60)
    print("MULTI-COIN MARKET STRUCTURE ANALYSIS")
    print(f"Watchlist: {', '.join(coins)}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Fetch prices for all coins
    print("\nFetching prices...")
    try:
        prices = fetch_multi_coin_prices(coins)
        for coin, price in prices.items():
            print(f"  {coin}: ${price:,.2f}")
    except Exception as e:
        print(f"Error fetching prices: {e}")
        prices = {c: 0.0 for c in coins}

    signals = {}
    signal_agg = SignalAggregator()

    # Analyze each coin
    for coin in coins:
        trading_symbol = get_trading_symbol(coin)
        print(f"\n{'='*40}")
        print(f"Analyzing {coin} ({trading_symbol})...")
        print(f"{'='*40}")

        try:
            with MarketDataAggregator() as aggregator:
                market_data = aggregator.fetch_all(trading_symbol)
                market_summary = aggregator.get_summary(trading_symbol)

            signal = signal_agg.aggregate(market_data, symbol=coin)
            signals[coin] = signal

            # Log each signal
            signal_logger.log_signal(signal, market_summary, prices.get(coin))

            # Print compact summary
            status = "VALID" if signal.is_valid else "---"
            direction = signal.direction.name if signal.is_valid else "NEUTRAL"
            print(f"  Score: {signal.total_score:.2f} | Direction: {direction} | {status}")

        except Exception as e:
            print(f"  Error analyzing {coin}: {e}")

    # Print ranked summary
    print("\n" + "=" * 60)
    print("SIGNAL RANKING (by score)")
    print("=" * 60)

    ranked = sorted(signals.items(), key=lambda x: x[1].total_score, reverse=True)
    for i, (coin, sig) in enumerate(ranked, 1):
        valid = "VALID" if sig.is_valid else ""
        print(f"  {i}. {coin:6} | Score: {sig.total_score:.2f} | {sig.direction.name:7} {valid}")

    valid_signals = [(c, s) for c, s in ranked if s.is_valid]
    print(f"\nValid signals: {len(valid_signals)} / {len(coins)}")

    return signals


def run_multi_coin_trading(coins: List[str] = None, dry_run: bool = True) -> None:
    """
    Run trading bot for multiple coins.

    Args:
        coins: List of coins to trade. Defaults to WATCHLIST.
        dry_run: If True, only analyze without trading
    """
    if coins is None:
        coins = WATCHLIST

    # Initialize paper trading
    paper_trader = PaperTrading(starting_balance=10000)
    paper_trader.load_log()

    # Fetch prices for all coins
    print("\nFetching prices...")
    try:
        prices = fetch_multi_coin_prices(coins)
        for coin, price in prices.items():
            print(f"  {coin}: ${price:,.2f}")
    except Exception as e:
        print(f"Error fetching prices: {e}")
        return

    # Check existing positions for SL/TP
    print("\nChecking existing positions...")
    closed = paper_trader.check_and_close_positions(prices)
    for c in closed:
        print(f"  Closed {c.get('symbol', 'position')}: {c['reason']} | P&L: ${c['pnl']:+,.2f}")

    # Analyze all coins
    signals = run_multi_coin_analysis(coins)

    # Rank signals and trade the best ones
    ranked = sorted(signals.items(), key=lambda x: x[1].total_score, reverse=True)
    valid_signals = [(c, s) for c, s in ranked if s.is_valid]

    print("\n" + "=" * 60)
    print("TRADE EXECUTION")
    print("=" * 60)

    current_positions = len(paper_trader.positions)
    max_positions = config.MAX_POSITIONS

    if current_positions >= max_positions:
        print(f"Max positions reached ({current_positions}/{max_positions}). No new trades.")
    elif not valid_signals:
        print("No valid signals. No trades to execute.")
    else:
        for coin, signal in valid_signals:
            if len(paper_trader.positions) >= max_positions:
                print(f"Max positions reached. Stopping.")
                break

            if coin in paper_trader.positions:
                print(f"  {coin}: Already have position, skipping")
                continue

            price = prices.get(coin, 0)
            if price <= 0:
                print(f"  {coin}: Invalid price, skipping")
                continue

            strength = signal.total_score / config.MAX_POSSIBLE_SCORE

            if dry_run:
                print(f"  [DRY RUN] Would open {signal.direction.name} {coin} @ ${price:,.2f}")
            else:
                print(f"  Opening {signal.direction.name} {coin} @ ${price:,.2f}...")
                paper_trader.open_position(
                    symbol=coin,
                    direction=signal.direction.name,
                    price=price,
                    signal_strength=strength
                )

    # Print final status
    paper_trader.print_status(prices)


def run_trading_bot(symbol: str = "BTCUSDT", dry_run: bool = True) -> None:
    """
    Run the trading bot.

    Args:
        symbol: Trading pair
        dry_run: If True, only analyze without trading
    """
    # Initialize paper trading
    paper_trader = PaperTrading(starting_balance=10000)
    paper_trader.load_log()

    # Get current BTC price for position checking
    try:
        real_time = fetch_real_time_data('bitcoin')
        current_price = real_time['bitcoin']['usd']
    except Exception as e:
        print(f"Error fetching price: {e}")
        return

    print(f"\nCurrent BTC Price: ${current_price:,.2f}")

    # Check existing positions for SL/TP
    closed = paper_trader.check_and_close_positions({'BTC': current_price})
    for c in closed:
        print(f"Closed position: {c['reason']} | P&L: ${c['pnl']:+,.2f}")

    # Run analysis
    signal = run_analysis(symbol, btc_price=current_price)

    # Execute trade if valid signal and not dry run
    if signal.is_valid and not dry_run:
        # Check if we already have a position
        if 'BTC' in paper_trader.positions:
            print("\nPosition already open, skipping new entry")
        else:
            # Calculate signal strength for position sizing
            strength = signal.total_score / 8.0  # Normalize to 0-1

            print(f"\nOpening {signal.direction.name} position...")
            paper_trader.open_position(
                symbol='BTC',
                direction=signal.direction.name,
                price=current_price,
                signal_strength=strength
            )
    elif signal.is_valid and dry_run:
        print(f"\n[DRY RUN] Would open {signal.direction.name} position")
    else:
        print("\nNo valid signal - no trade executed")

    # Print status
    paper_trader.print_status({'BTC': current_price})


def run_backtest() -> None:
    """Run backtest on historical data."""
    from backtesting.backtest_engine import BacktestEngine, BacktestConfig
    from backtesting.data_loader import HistoricalDataLoader

    print("\n" + "=" * 60)
    print("RUNNING BACKTEST")
    print("=" * 60)

    # Load and prepare data
    print("\nLoading historical data...")
    loader = HistoricalDataLoader()

    try:
        data = loader.prepare_backtest_data(use_synthetic=True)
    except FileNotFoundError:
        print("Error: Historical data file not found.")
        print("Please ensure data/BTCUSD_historical_data.csv exists.")
        return

    # Align data
    print("Aligning data...")
    aligned = loader.align_data(data, freq='1h')
    print(f"Data range: {aligned.index[0]} to {aligned.index[-1]}")
    print(f"Total periods: {len(aligned)}")

    # Configure backtest
    config = BacktestConfig(
        initial_capital=10000,
        position_size_pct=0.10,
        stop_loss_pct=0.02,
        take_profit_pct=0.04,
        signal_threshold=4.0
    )

    # Run backtest
    print("\nRunning backtest...")
    engine = BacktestEngine(config)
    result = engine.run(aligned)

    # Print results
    result.print_summary()


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Market Structure Trading Bot',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main_market_structure.py --analyze                    # Analyze single coin (BTC)
  python main_market_structure.py --analyze --all-coins        # Analyze all 8 coins
  python main_market_structure.py --analyze --coins BTC,ETH    # Analyze specific coins
  python main_market_structure.py --trade --all-coins          # Trade all coins (paper)
  python main_market_structure.py --trade --dry-run --all-coins  # Simulate multi-coin
  python main_market_structure.py --backtest                   # Run backtest
        """
    )

    parser.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='Run market structure analysis'
    )
    parser.add_argument(
        '--trade', '-t',
        action='store_true',
        help='Run trading bot (paper trading)'
    )
    parser.add_argument(
        '--backtest', '-b',
        action='store_true',
        help='Run backtest on historical data'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simulate trading without executing'
    )
    parser.add_argument(
        '--symbol', '-s',
        default='BTCUSDT',
        help='Single trading symbol (default: BTCUSDT)'
    )
    parser.add_argument(
        '--coins', '-c',
        default=None,
        help='Comma-separated coin list (e.g., BTC,ETH,SOL). Overrides --symbol.'
    )
    parser.add_argument(
        '--all-coins',
        action='store_true',
        help='Analyze all coins in watchlist (BTC,ETH,SOL,DOGE,XRP,AVAX,LINK,PEPE)'
    )

    args = parser.parse_args()

    # Parse coin list
    if args.coins:
        args.coin_list = [c.strip().upper() for c in args.coins.split(',')]
    elif args.all_coins:
        args.coin_list = WATCHLIST
    else:
        args.coin_list = None  # Single symbol mode

    # Default to analysis if no mode specified
    if not any([args.analyze, args.trade, args.backtest]):
        args.analyze = True

    # Determine what we're analyzing
    if args.coin_list:
        symbol_display = f"{len(args.coin_list)} coins: {', '.join(args.coin_list[:4])}{'...' if len(args.coin_list) > 4 else ''}"
    else:
        symbol_display = args.symbol

    print("\n" + "=" * 60)
    print("  MARKET STRUCTURE TRADING BOT")
    print("=" * 60)
    print(f"  Mode: {'Analyze' if args.analyze else 'Trade' if args.trade else 'Backtest'}")
    print(f"  Symbols: {symbol_display}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    try:
        if args.backtest:
            run_backtest()
        elif args.trade:
            if args.coin_list:
                run_multi_coin_trading(args.coin_list, dry_run=args.dry_run)
            else:
                run_trading_bot(args.symbol, dry_run=args.dry_run)
        else:
            if args.coin_list:
                run_multi_coin_analysis(args.coin_list)
            else:
                run_analysis(args.symbol)

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        raise


if __name__ == '__main__':
    main()
