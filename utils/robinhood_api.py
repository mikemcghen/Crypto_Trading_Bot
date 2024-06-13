import requests
import time
import json
import base64
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

# Example usage
real_time_data = fetch_real_time_data('bitcoin')
print(real_time_data)


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
