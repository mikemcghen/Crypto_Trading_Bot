from utils.paper_trading import PaperTrading
from utils.robinhood_api import fetch_real_time_data

def execute_trade(prediction, access_token):
    paper_trading = PaperTrading()
    paper_trading.load_log()
    real_time_data = fetch_real_time_data('bitcoin')
    current_price = real_time_data['bitcoin']['usd']

    if prediction[0] > current_price:
        paper_trading.buy('BTC', current_price, 0.01)
    elif prediction[0] < current_price:
        paper_trading.sell('BTC', current_price, 0.01)
