import requests
import time
import json
import base64
from typing import List, Dict
import nacl.signing
import nacl.encoding


def fetch_real_time_data(symbol, vs_currency='usd'):
    url = f'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': symbol,
        'vs_currencies': vs_currency
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def fetch_multi_coin_prices(coins: List[str], vs_currency: str = 'usd') -> Dict[str, float]:
    """
    Fetch prices for multiple coins in a single API call.

    Args:
        coins: List of coin symbols (e.g., ['BTC', 'ETH', 'SOL'])
        vs_currency: Currency to price against (default 'usd')

    Returns:
        Dict mapping coin symbol to price: {'BTC': 84000.0, 'ETH': 3200.0, ...}
    """
    from config.symbols import get_coingecko_id, SYMBOL_MAP

    # Build comma-separated list of CoinGecko IDs
    coingecko_ids = ','.join(get_coingecko_id(c) for c in coins)

    url = 'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': coingecko_ids,
        'vs_currencies': vs_currency
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    # Map CoinGecko IDs back to our coin symbols
    prices = {}
    for coin in coins:
        cg_id = get_coingecko_id(coin)
        if cg_id in data and vs_currency in data[cg_id]:
            prices[coin] = float(data[cg_id][vs_currency])
        else:
            prices[coin] = 0.0

    return prices


# Example usage
if __name__ == "__main__":
    real_time_data = fetch_real_time_data('bitcoin')
    print(real_time_data)

    # Test multi-coin fetch
    try:
        prices = fetch_multi_coin_prices(['BTC', 'ETH', 'SOL', 'DOGE'])
        print(f"Multi-coin prices: {prices}")
    except Exception as e:
        print(f"Multi-coin fetch error: {e}")


def place_order(symbol, quantity, price, side, access_token, private_key_base64):
    path = "/api/v1/crypto/trading/orders/"
    method = "POST"
    body = {
        "client_order_id": "unique_order_id",  # Replace with a unique ID for each order
        "side": side,
        "symbol": symbol,
        "type": "market",
        "market_order_config": {
            "asset_quantity": quantity
        }
    }
    body_json = json.dumps(body)

    # Create the message to sign
    current_timestamp = str(int(time.time()))
    message = f"{access_token}{current_timestamp}{path}{method}{body_json}"

    # Sign the message using pynacl
    private_key_bytes = base64.b64decode(private_key_base64)
    private_key = nacl.signing.SigningKey(private_key_bytes)
    signed_message = private_key.sign(message.encode("utf-8"))
    signature = signed_message.signature

    # Convert the signature to base64
    base64_signature = base64.b64encode(signature).decode("utf-8")

    headers = {
        "x-api-key": access_token,
        "x-signature": base64_signature,
        "Content-Type": "application/json"
    }

    response = requests.post(f"https://api.robinhood.com{path}", headers=headers, data=body_json)
    response.raise_for_status()
    return response.json()
