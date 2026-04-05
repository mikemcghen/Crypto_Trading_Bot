"""
Symbol mapping for multi-coin support.

Maps coin tickers to different API formats:
- trading: Exchange format (BTCUSDT)
- coingecko: CoinGecko API ID (bitcoin)
- okx: OKX perpetual format (BTC-USDT-SWAP)
"""

from typing import List, Dict

# Default watchlist - 8 coins across different tiers
WATCHLIST = ['BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'AVAX', 'LINK', 'PEPE']

SYMBOL_MAP: Dict[str, Dict[str, str]] = {
    'BTC': {
        'trading': 'BTCUSDT',
        'coingecko': 'bitcoin',
        'okx': 'BTC-USDT-SWAP',
    },
    'ETH': {
        'trading': 'ETHUSDT',
        'coingecko': 'ethereum',
        'okx': 'ETH-USDT-SWAP',
    },
    'SOL': {
        'trading': 'SOLUSDT',
        'coingecko': 'solana',
        'okx': 'SOL-USDT-SWAP',
    },
    'DOGE': {
        'trading': 'DOGEUSDT',
        'coingecko': 'dogecoin',
        'okx': 'DOGE-USDT-SWAP',
    },
    'XRP': {
        'trading': 'XRPUSDT',
        'coingecko': 'ripple',
        'okx': 'XRP-USDT-SWAP',
    },
    'AVAX': {
        'trading': 'AVAXUSDT',
        'coingecko': 'avalanche-2',
        'okx': 'AVAX-USDT-SWAP',
    },
    'LINK': {
        'trading': 'LINKUSDT',
        'coingecko': 'chainlink',
        'okx': 'LINK-USDT-SWAP',
    },
    'PEPE': {
        'trading': 'PEPEUSDT',
        'coingecko': 'pepe',
        'okx': 'PEPE-USDT-SWAP',
    },
}


def get_trading_symbol(coin: str) -> str:
    """Get exchange trading symbol (e.g., BTC -> BTCUSDT)."""
    if coin in SYMBOL_MAP:
        return SYMBOL_MAP[coin]['trading']
    # Fallback: assume it's already in trading format
    return coin if coin.endswith('USDT') else f"{coin}USDT"


def get_coingecko_id(coin: str) -> str:
    """Get CoinGecko API ID (e.g., BTC -> bitcoin)."""
    if coin in SYMBOL_MAP:
        return SYMBOL_MAP[coin]['coingecko']
    return coin.lower()


def get_okx_symbol(coin: str) -> str:
    """Get OKX perpetual symbol (e.g., BTC -> BTC-USDT-SWAP)."""
    if coin in SYMBOL_MAP:
        return SYMBOL_MAP[coin]['okx']
    return f"{coin}-USDT-SWAP"


def get_all_coingecko_ids(coins: List[str] = None) -> str:
    """Get comma-separated CoinGecko IDs for batch API call."""
    if coins is None:
        coins = WATCHLIST
    return ','.join(get_coingecko_id(c) for c in coins)


def coin_from_trading_symbol(trading_symbol: str) -> str:
    """Reverse lookup: BTCUSDT -> BTC."""
    for coin, data in SYMBOL_MAP.items():
        if data['trading'] == trading_symbol:
            return coin
    # Fallback: strip USDT suffix
    return trading_symbol.replace('USDT', '')
