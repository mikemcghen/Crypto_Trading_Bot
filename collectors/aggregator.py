"""
Market Data Aggregator.

Combines data from all collectors into a unified structure
for signal generation.
"""

import pandas as pd
from typing import Dict, Optional, Any
import logging

from .binance_collector import BinanceCollector
from .bybit_collector import BybitCollector
from .okx_collector import OKXCollector
from .fear_greed_collector import FearGreedCollector

logger = logging.getLogger(__name__)


class MarketDataAggregator:
    """
    Aggregates market structure data from multiple sources.

    Fetches and combines:
    - Funding rates (Binance primary, Bybit fallback)
    - Open interest (Binance primary, Bybit fallback)
    - Liquidations (OKX)
    - Fear & Greed Index (Alternative.me)
    """

    def __init__(self):
        """Initialize all collectors."""
        self.binance = BinanceCollector()
        self.bybit = BybitCollector()
        self.okx = OKXCollector()
        self.fear_greed = FearGreedCollector()

    def fetch_all(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Fetch data from all sources.

        Args:
            symbol: Trading pair symbol

        Returns:
            Dict containing all market data:
            {
                'binance_funding': DataFrame,
                'binance_oi': DataFrame,
                'okx_liquidations': DataFrame,
                'okx_funding': DataFrame,
                'fear_greed': DataFrame,
                'liquidation_analysis': Dict,
                'timestamp': Timestamp,
                'funding_source': str  # Which exchange provided funding data
            }
        """
        data = {
            'timestamp': pd.Timestamp.now(),
            'symbol': symbol,
            'funding_source': None
        }

        # Try Binance first (primary source for funding and OI)
        binance_success = False
        logger.info("Fetching Binance data...")
        try:
            binance_data = self.binance.fetch_data(symbol)
            data['binance_funding'] = binance_data.get('funding_rate', pd.DataFrame())
            data['binance_oi'] = binance_data.get('open_interest', pd.DataFrame())
            if 'oi_history' in binance_data:
                data['binance_oi_history'] = binance_data['oi_history']

            # Check if we actually got data
            if not data['binance_funding'].empty:
                binance_success = True
                data['funding_source'] = 'Binance'
                logger.info("Binance data fetched successfully")

        except Exception as e:
            logger.warning(f"Binance fetch failed: {e}")
            data['binance_funding'] = pd.DataFrame()
            data['binance_oi'] = pd.DataFrame()

        # If Binance failed, try Bybit as fallback
        if not binance_success:
            logger.info("Trying Bybit as fallback...")
            try:
                bybit_data = self.bybit.fetch_data(symbol)
                bybit_funding = bybit_data.get('funding_rate', pd.DataFrame())
                bybit_oi = bybit_data.get('open_interest', pd.DataFrame())

                if not bybit_funding.empty:
                    # Use Bybit data in place of Binance
                    data['binance_funding'] = bybit_funding
                    data['funding_source'] = 'Bybit'
                    binance_success = True
                    logger.info("Using Bybit funding rate data")

                if not bybit_oi.empty:
                    data['binance_oi'] = bybit_oi
                    logger.info("Using Bybit open interest data")

            except Exception as e:
                logger.warning(f"Bybit fallback also failed: {e}")

        # If both Binance and Bybit failed, try OKX funding as last resort
        if not binance_success:
            logger.info("Trying OKX funding as final fallback...")
            try:
                okx_funding = self.okx.fetch_funding_rate(symbol)
                if not okx_funding.empty and 'fundingRate' in okx_funding.columns:
                    data['binance_funding'] = okx_funding
                    data['funding_source'] = 'OKX'
                    logger.info("Using OKX funding rate data")
            except Exception as e:
                logger.warning(f"OKX funding fallback failed: {e}")

        # OKX data (primary source for liquidations)
        logger.info("Fetching OKX data...")
        try:
            data['okx_liquidations'] = self.okx.fetch_liquidations(symbol)
            data['okx_funding'] = self.okx.fetch_funding_rate(symbol)
            data['liquidation_analysis'] = self.okx.analyze_liquidations(symbol)
        except Exception as e:
            logger.warning(f"OKX fetch failed: {e}")
            data['okx_liquidations'] = pd.DataFrame()
            data['okx_funding'] = pd.DataFrame()
            data['liquidation_analysis'] = {
                'long_liquidations': 0.0,
                'short_liquidations': 0.0,
                'imbalance': 0.0,
                'total_volume': 0.0
            }

        # Fear & Greed Index
        logger.info("Fetching Fear & Greed Index...")
        try:
            data['fear_greed'] = self.fear_greed.fetch_data(limit=7)
            data['fear_greed_current'] = self.fear_greed.get_current_value()
            data['fear_greed_signal'] = self.fear_greed.get_signal_strength()
        except Exception as e:
            logger.warning(f"Fear & Greed fetch failed: {e}")
            data['fear_greed'] = pd.DataFrame()
            data['fear_greed_current'] = None
            data['fear_greed_signal'] = 0.0

        logger.info("Data aggregation complete")
        return data

    def get_summary(self, symbol: str = "BTCUSDT") -> Dict[str, Any]:
        """
        Get a simplified summary of current market conditions.

        Returns:
            Dict with key metrics:
            {
                'funding_rate': float,
                'open_interest': float,
                'fear_greed_value': int,
                'fear_greed_class': str,
                'liquidation_imbalance': float,
                'liquidation_volume': float,
                'funding_source': str
            }
        """
        data = self.fetch_all(symbol)

        summary = {
            'symbol': symbol,
            'timestamp': data['timestamp'],
            'funding_source': data.get('funding_source', 'Unknown')
        }

        # Funding rate
        if not data['binance_funding'].empty:
            summary['funding_rate'] = float(data['binance_funding']['fundingRate'].iloc[-1])
        else:
            summary['funding_rate'] = 0.0

        # Open interest
        if not data['binance_oi'].empty:
            summary['open_interest'] = float(data['binance_oi']['openInterest'].iloc[0])
        else:
            summary['open_interest'] = 0.0

        # Fear & Greed
        summary['fear_greed_value'] = data.get('fear_greed_current', 50)
        if not data['fear_greed'].empty:
            summary['fear_greed_class'] = data['fear_greed']['value_classification'].iloc[-1]
        else:
            summary['fear_greed_class'] = 'Unknown'

        # Liquidations
        liq_analysis = data.get('liquidation_analysis', {})
        summary['liquidation_imbalance'] = liq_analysis.get('imbalance', 0.0)
        summary['liquidation_volume'] = liq_analysis.get('total_volume', 0.0)

        return summary

    def print_summary(self, symbol: str = "BTCUSDT") -> None:
        """Print a formatted summary of market conditions."""
        summary = self.get_summary(symbol)

        print("\n" + "=" * 50)
        print(f"MARKET STRUCTURE SUMMARY - {summary['symbol']}")
        print(f"Time: {summary['timestamp']}")
        print(f"Data Source: {summary['funding_source'] or 'N/A'}")
        print("=" * 50)

        # Funding rate
        fr = summary['funding_rate']
        fr_pct = fr * 100
        fr_status = "EXTREME HIGH" if fr > 0.001 else "EXTREME LOW" if fr < -0.0005 else "NORMAL"
        print(f"\nFunding Rate: {fr_pct:.4f}% ({fr_status})")

        # Open Interest
        oi = summary['open_interest']
        print(f"Open Interest: {oi:,.0f} contracts")

        # Fear & Greed
        fg = summary['fear_greed_value'] or 50
        fg_class = summary['fear_greed_class']
        print(f"Fear & Greed: {fg} ({fg_class})")

        # Liquidations
        liq_imb = summary['liquidation_imbalance']
        liq_vol = summary['liquidation_volume']
        liq_dir = "LONG LIQUIDATIONS" if liq_imb > 0.2 else "SHORT LIQUIDATIONS" if liq_imb < -0.2 else "BALANCED"
        print(f"Liquidations: {liq_vol:,.0f} contracts ({liq_dir})")

        print("=" * 50 + "\n")

    def close(self) -> None:
        """Close all collector sessions."""
        self.binance.close()
        self.bybit.close()
        self.okx.close()
        self.fear_greed.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
