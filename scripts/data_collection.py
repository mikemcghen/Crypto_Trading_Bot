import requests
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Function to fetch historical price data
def fetch_historical_data(symbol, days='365'):
    url = f'https://api.coingecko.com/api/v3/coins/{symbol}/market_chart'
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily'
    }
    response = requests.get(url, params=params)

    # Check for successful response
    if response.status_code != 200:
        raise Exception(f"Error fetching data from CoinGecko API: {response.status_code} - {response.json()}")

    data = response.json()

    # Check if the 'prices' key is in the response
    if 'prices' not in data:
        raise KeyError(f"'prices' key not found in response data: {data}")

    prices = data['prices']
    df = pd.DataFrame(prices, columns=['timestamp', 'price'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

# Function to fetch sentiment data from NewsData.io
def fetch_sentiment_data(query, from_date, to_date, api_key):
    url = 'https://newsdata.io/api/1/news'
    params = {
        'apikey': api_key,
        'q': query,
        'language': 'en'
    }
    response = requests.get(url, params=params)

    # Check for successful response
    if response.status_code != 200:
        raise Exception(f"Error fetching data from NewsData.io API: {response.status_code} - {response.text}")

    data = response.json()
    articles = data.get('results', [])

    # Extract publication dates and content
    sentiment_data = []
    analyzer = SentimentIntensityAnalyzer()
    for article in articles:
        publication_date = article.get('pubDate', '')
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title} {description}"
        sentiment_score = analyzer.polarity_scores(content)['compound']
        sentiment_data.append({'date': publication_date, 'content': content, 'sentiment': sentiment_score})

    return pd.DataFrame(sentiment_data)
# Example usage
if __name__ == "__main__":
    # Fetch historical data (limited to the past 365 days)
    historical_data = fetch_historical_data('bitcoin', '365')
    historical_data.to_csv('data/BTCUSD_historical_data.csv')

    # Example parameters for sentiment data
    API_KEY = 'pub_462677e279a904d2685e6f71f66288842ccb2'
    QUERY = 'Bitcoin'
    FROM_DATE = '2023-01-01'
    TO_DATE = '2023-12-31'

    sentiment_data = fetch_sentiment_data(QUERY, FROM_DATE, TO_DATE, API_KEY)
    sentiment_data.to_csv('data/sentiment_data.csv')
