"""
Base collector class with rate limiting and error handling.
All API collectors inherit from this class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import requests
import time
import logging

from config.settings import config

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Abstract base class for all market structure data collectors.

    Provides:
    - Rate limiting to respect API limits
    - Session management for connection pooling
    - Standardized error handling
    - Common request patterns
    """

    def __init__(self, rate_limit_per_second: float = 1.0, timeout: int = None):
        """
        Initialize collector with rate limiting.

        Args:
            rate_limit_per_second: Maximum requests per second
            timeout: Request timeout in seconds
        """
        self.rate_limit_per_second = rate_limit_per_second
        self.timeout = timeout or config.API_TIMEOUT_SECONDS
        self.last_request_time: float = 0
        self.session = requests.Session()
        self.session.headers.update({
            'Accept': 'application/json',
            'User-Agent': 'CryptoTradingBot/1.0'
        })

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self.rate_limit_per_second <= 0:
            return

        elapsed = time.time() - self.last_request_time
        min_interval = 1.0 / self.rate_limit_per_second
        sleep_time = min_interval - elapsed

        if sleep_time > 0:
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _make_request(
        self,
        url: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP GET request with rate limiting and error handling.

        Args:
            url: API endpoint URL
            params: Query parameters
            headers: Additional headers

        Returns:
            Parsed JSON response

        Raises:
            Exception: On API error or timeout
        """
        self._rate_limit()

        try:
            response = self.session.get(
                url,
                params=params,
                headers=headers,
                timeout=self.timeout
            )

            if response.status_code != 200:
                error_msg = f"API Error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data}"
                except:
                    error_msg += f" - {response.text[:200]}"
                raise Exception(error_msg)

            return response.json()

        except requests.exceptions.Timeout:
            raise Exception(f"Request timeout after {self.timeout}s: {url}")
        except requests.exceptions.ConnectionError as e:
            raise Exception(f"Connection error: {url} - {e}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Return collector name for logging."""
        pass

    @abstractmethod
    def fetch_data(self, symbol: str = "BTCUSDT") -> pd.DataFrame:
        """
        Fetch data for a given symbol.

        Args:
            symbol: Trading pair symbol

        Returns:
            DataFrame with fetched data
        """
        pass

    def safe_fetch(self, symbol: str = "BTCUSDT") -> Optional[pd.DataFrame]:
        """
        Fetch data with error handling, returns None on failure.

        Use this for non-critical data sources where failure
        shouldn't stop the entire pipeline.
        """
        try:
            return self.fetch_data(symbol)
        except Exception as e:
            logger.warning(f"{self.name} fetch failed: {e}")
            return None

    def close(self) -> None:
        """Close the session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
