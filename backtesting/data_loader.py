"""
Historical Data Loader for Backtesting.

Loads and prepares historical data for backtesting.
Can use real historical data or generate synthetic data
for indicators where historical data isn't available.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path


class HistoricalDataLoader:
    """
    Loads and prepares historical data for backtesting.

    Since free APIs have limited historical data for some indicators,
    this class can also generate synthetic data based on price movements
    for backtesting purposes.
    """

    def __init__(self, data_dir: str = "data"):
        """
        Initialize data loader.

        Args:
            data_dir: Directory containing historical data files
        """
        self.data_dir = Path(data_dir)

    def load_price_data(self, filepath: str = None) -> pd.DataFrame:
        """
        Load historical price data.

        Args:
            filepath: Path to CSV file. If None, uses default location.

        Returns:
            DataFrame with datetime index and 'price' column
        """
        if filepath is None:
            filepath = self.data_dir / "BTCUSD_historical_data.csv"

        df = pd.read_csv(filepath)

        # Handle different column naming conventions
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        elif 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)

        # Ensure we have a price column
        if 'price' not in df.columns and 'close' in df.columns:
            df['price'] = df['close']

        df.sort_index(inplace=True)

        return df

    def generate_synthetic_funding(
        self,
        price_data: pd.DataFrame,
        base_rate: float = 0.0001,
        momentum_factor: float = 0.5
    ) -> pd.DataFrame:
        """
        Generate synthetic funding rate data based on price momentum.

        Heuristic: Funding tends to be positive after rallies (crowded longs)
        and negative after dumps (crowded shorts).

        Args:
            price_data: DataFrame with 'price' column
            base_rate: Base funding rate
            momentum_factor: How much momentum affects funding

        Returns:
            DataFrame with 'fundingRate' column, indexed by 8-hour periods
        """
        # Calculate returns
        returns = price_data['price'].pct_change()

        # Calculate rolling momentum (24 periods ~ 24 hours if hourly data)
        momentum = returns.rolling(24, min_periods=1).mean()

        # Scale momentum to typical funding range (-0.003 to 0.003)
        funding = base_rate + momentum * momentum_factor * 0.01
        funding = funding.clip(-0.003, 0.003)

        # Resample to 8-hour periods (funding settlement frequency)
        funding_df = pd.DataFrame({'fundingRate': funding})
        funding_df = funding_df.resample('8h').last().dropna()

        return funding_df

    def generate_synthetic_fear_greed(
        self,
        price_data: pd.DataFrame,
        lookback_days: int = 30
    ) -> pd.DataFrame:
        """
        Generate synthetic Fear & Greed data based on price momentum.

        Heuristic: Fear during drawdowns, greed during rallies.

        Args:
            price_data: DataFrame with 'price' column
            lookback_days: Period for calculating momentum

        Returns:
            DataFrame with 'value' and 'value_classification' columns
        """
        # Calculate N-day return
        returns = price_data['price'].pct_change(lookback_days)

        # Normalize to 0-100 scale
        # Assume typical returns range from -50% to +100%
        fear_greed = 50 + (returns * 100)  # Scale factor
        fear_greed = fear_greed.clip(0, 100)

        # Classify
        def classify(value):
            if pd.isna(value):
                return "Unknown"
            if value < 25:
                return "Extreme Fear"
            elif value < 45:
                return "Fear"
            elif value < 55:
                return "Neutral"
            elif value < 75:
                return "Greed"
            else:
                return "Extreme Greed"

        df = pd.DataFrame({
            'value': fear_greed,
            'value_classification': fear_greed.apply(classify)
        })

        # Resample to daily (Fear & Greed is daily)
        df = df.resample('1d').last().dropna()

        return df

    def generate_synthetic_liquidations(
        self,
        price_data: pd.DataFrame,
        volatility_window: int = 24,
        base_volume: float = 5_000_000
    ) -> pd.DataFrame:
        """
        Generate synthetic liquidation data based on price volatility.

        Heuristic: More liquidations during volatile moves.
        Direction of liquidations opposite to price move direction.

        Args:
            price_data: DataFrame with 'price' column
            volatility_window: Window for calculating volatility
            base_volume: Base liquidation volume in USD

        Returns:
            DataFrame with liquidation analysis dict
        """
        returns = price_data['price'].pct_change()
        volatility = returns.rolling(volatility_window, min_periods=1).std()

        # Volume scales with volatility
        volume = base_volume * (1 + volatility * 50)

        # Imbalance: opposite to price direction
        # Big up move -> longs liquidated (shorts squeezed, then longs liquidated on reversal)
        # Simplify: use recent return direction
        rolling_return = returns.rolling(6, min_periods=1).mean()

        # Positive return -> shorts liquidated (negative imbalance)
        # Negative return -> longs liquidated (positive imbalance)
        imbalance = -rolling_return * 5  # Scale to -1 to 1
        imbalance = imbalance.clip(-0.6, 0.6)

        df = pd.DataFrame({
            'total_volume': volume.fillna(base_volume),
            'imbalance': imbalance.fillna(0),
            'long_liquidations': volume.fillna(base_volume) * (0.5 + imbalance.fillna(0) / 2),
            'short_liquidations': volume.fillna(base_volume) * (0.5 - imbalance.fillna(0) / 2)
        })

        return df

    def prepare_backtest_data(
        self,
        price_filepath: str = None,
        use_synthetic: bool = True
    ) -> Dict[str, pd.DataFrame]:
        """
        Prepare all data needed for backtesting.

        Args:
            price_filepath: Path to historical price data
            use_synthetic: Whether to generate synthetic indicator data

        Returns:
            Dict with all data needed by SignalAggregator
        """
        # Load price data
        price_data = self.load_price_data(price_filepath)

        result = {
            'price': price_data
        }

        if use_synthetic:
            # Generate synthetic data for backtesting
            result['binance_funding'] = self.generate_synthetic_funding(price_data)
            result['fear_greed'] = self.generate_synthetic_fear_greed(price_data)

            # For liquidations, we need to store analysis results
            liq_data = self.generate_synthetic_liquidations(price_data)
            result['liquidation_data'] = liq_data

        return result

    def align_data(
        self,
        data: Dict[str, pd.DataFrame],
        freq: str = '1h'
    ) -> pd.DataFrame:
        """
        Align all data to a common time index.

        Args:
            data: Dict of DataFrames with different frequencies
            freq: Target frequency for alignment

        Returns:
            Single DataFrame with all columns aligned
        """
        price = data['price'].resample(freq).last()

        aligned = pd.DataFrame(index=price.index)
        aligned['price'] = price['price']

        # Forward-fill lower frequency data
        if 'binance_funding' in data:
            funding = data['binance_funding'].resample(freq).ffill()
            aligned = aligned.join(funding, how='left')

        if 'fear_greed' in data:
            fg = data['fear_greed'].resample(freq).ffill()
            aligned = aligned.join(fg, how='left')

        if 'liquidation_data' in data:
            liq = data['liquidation_data'].resample(freq).ffill()
            aligned = aligned.join(liq, how='left')

        aligned.ffill(inplace=True)
        aligned.dropna(inplace=True)

        return aligned
