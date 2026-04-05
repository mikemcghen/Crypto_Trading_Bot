import os
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
from scripts.data_preprocessing import preprocess_data
from scripts.model_training import train_model
from scripts.make_predictions import make_predictions
from scripts.trade_execution import execute_trade
from utils.robinhood_api import fetch_real_time_data
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from scripts.data_collection import fetch_historical_data, fetch_sentiment_data

# Load environment variables
load_dotenv()

ACCESS_TOKEN = os.getenv('ROBINHOOD_ACCESS_TOKEN')
PRIVATE_KEY_BASE64 = os.getenv('ROBINHOOD_PRIVATE_KEY')
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

def main():
    # Validate environment variables
    if not all([ACCESS_TOKEN, PRIVATE_KEY_BASE64, NEWS_API_KEY]):
        print("Error: Missing required environment variables.")
        print("Please ensure .env file contains: ROBINHOOD_ACCESS_TOKEN, ROBINHOOD_PRIVATE_KEY, NEWS_API_KEY")
        return

    try:
        # Fetch historical data
        print("Fetching historical data...")
        historical_data = fetch_historical_data('bitcoin', '365')
        historical_data.to_csv('data/BTCUSD_historical_data.csv')

        # Dynamic date range for sentiment data (past year to today)
        to_date = datetime.now()
        from_date = to_date - timedelta(days=365)
        FROM_DATE = from_date.strftime('%Y-%m-%d')
        TO_DATE = to_date.strftime('%Y-%m-%d')

        # Fetch sentiment data
        print("Fetching sentiment data...")
        QUERY = 'Bitcoin'
        sentiment_data = fetch_sentiment_data(QUERY, FROM_DATE, TO_DATE, NEWS_API_KEY)
        sentiment_data.to_csv('data/sentiment_data.csv')

        # Preprocess data
        print("Preprocessing data...")
        scaled_features, target, scaler = preprocess_data()

        # Train the model
        print("Training model...")
        train_model()

        # Fetch new data and make predictions
        print("Fetching real-time data...")
        real_time_data = fetch_real_time_data('bitcoin')
        current_price = real_time_data['bitcoin']['usd']
        print(f"Current BTC price: ${current_price:,.2f}")

        # Fetch real-time sentiment data (past 24 hours)
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')

        print("Analyzing recent sentiment...")
        recent_news = fetch_sentiment_data(QUERY, yesterday, today, NEWS_API_KEY)

        if recent_news.empty or 'content' not in recent_news.columns:
            print("Warning: No recent news found, using neutral sentiment")
            average_sentiment = 0.0
        else:
            recent_sentiment = recent_news['content'].apply(
                lambda x: SentimentIntensityAnalyzer().polarity_scores(x)['compound']
            )
            average_sentiment = recent_sentiment.mean()

        print(f"Average sentiment score: {average_sentiment:.3f}")

        new_data = pd.DataFrame({
            'price': [current_price],
            'sentiment': [average_sentiment]
        })

        prediction = make_predictions(new_data)
        print(f"Predicted next price: ${prediction[0]:,.2f}")

        execute_trade(prediction, ACCESS_TOKEN)
        print("Trade execution complete.")

    except Exception as e:
        print(f"Error during execution: {e}")
        raise

if __name__ == '__main__':
    main()
