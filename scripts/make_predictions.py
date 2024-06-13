import joblib
import pandas as pd

def make_predictions(new_data):
    model = joblib.load('models/linear_model.pkl')
    scaler = joblib.load('models/scaler.pkl')
    scaled_data = scaler.transform(new_data)
    predictions = model.predict(scaled_data)
    return predictions
