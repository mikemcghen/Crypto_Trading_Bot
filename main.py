import pandas as pd
import requests
from scripts.data_preprocessing import preprocess_data
from scripts.model_training import train_model
from scripts.make_predictions import make_predictions
from scripts.trade_execution import execute_trade
from utils.robinhood_api import fetch_real_time_data
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from scripts.data_collection import fetch_historical_data, fetch_sentiment_data

# Provided API key
access_token = "3d564201-522d-4a95-a084-c8e109385937"
private_key_base64 = "03v2e0DVADUSQ7MLYzDrp3ClzQ0ZY0anGuAZMJaC6rI="
NEWS_API_KEY = 'pub_462677e279a904d2685e6f71f66288842ccb2'

def fetch_real_time_data(symbol, vs_currency='usd'):
    url = f'https://api.coingecko.com/api/v3/simple/price'
    params = {
        'ids': symbol,
        'vs_currencies': vs_currency
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()

def main():
    # Fetch historical data
    historical_data = fetch_historical_data('bitcoin', '365')
    historical_data.to_csv('data/BTCUSD_historical_data.csv')
    
    # Fetch sentiment data
    QUERY = 'Bitcoin'
    FROM_DATE = '2024-01-01'
    TO_DATE = '2024-06-11'
    sentiment_data = fetch_sentiment_data(QUERY, FROM_DATE, TO_DATE, NEWS_API_KEY)
    sentiment_data.to_csv('data/sentiment_data.csv')

    # Preprocess data
    scaled_features, target, scaler = preprocess_data()
    
    # Train the model (uncomment if not trained yet)
    train_model()
    
    # Fetch new data and make predictions
    real_time_data = fetch_real_time_data('bitcoin')
    current_price = real_time_data['bitcoin']['usd']
    
    # Fetch real-time sentiment data (you may want to use a specific news source or recent news)
    recent_news = fetch_sentiment_data(QUERY, '2024-06-10', '2024-06-11', NEWS_API_KEY)  # Example for recent 1-day news
    recent_sentiment = recent_news['content'].apply(lambda x: SentimentIntensityAnalyzer().polarity_scores(x)['compound'])
    average_sentiment = recent_sentiment.mean()

    new_data = pd.DataFrame({
        'price': [current_price],
        'sentiment': [average_sentiment]
    })

    prediction = make_predictions(new_data)
    execute_trade(prediction, access_token)

if __name__ == '__main__':
    main()
