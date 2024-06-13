import pandas as pd
from sklearn.preprocessing import MinMaxScaler

def preprocess_data():
    # Load historical price data
    historical_data = pd.read_csv('data/BTCUSD_historical_data.csv', parse_dates=['timestamp'], index_col='timestamp')
    
    # Load sentiment data
    sentiment_data = pd.read_csv('data/sentiment_data.csv', parse_dates=['date'], index_col='date')
    
    # Ensure both DataFrames have their date columns as datetime and set as indexes
    historical_data.index = pd.to_datetime(historical_data.index)
    sentiment_data.index = pd.to_datetime(sentiment_data.index)
    
    # Sort indexes
    historical_data = historical_data.sort_index()
    sentiment_data = sentiment_data.sort_index()
    
    # Merge datasets on date
    merged_data = pd.merge_asof(historical_data, sentiment_data, left_index=True, right_index=True, direction='backward')
    
    # Select features and target
    features = merged_data[['price', 'sentiment']]
    target = merged_data['price'].shift(-1).dropna()  # Predict next closing price
    features = features[:-1]  # Remove last row to match target length
    
    # Handle NaN values by filling with 0 or dropping (choose one method)
    features = features.fillna(0)  # Method 1: Fill NaNs with 0
    # features = features.dropna()  # Method 2: Drop rows with NaNs

    # Normalize the features
    scaler = MinMaxScaler()
    scaled_features = scaler.fit_transform(features)
    
    return scaled_features, target, scaler
