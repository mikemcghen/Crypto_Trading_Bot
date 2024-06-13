from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
import joblib
from scripts.data_preprocessing import preprocess_data

def train_model():
    # Load and preprocess data
    scaled_features, target, scaler = preprocess_data()
    
    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(scaled_features, target, test_size=0.2, random_state=42)
    
    # Train the model
    model = LinearRegression()
    model.fit(X_train, y_train)
    
    # Save the model
    joblib.dump(model, 'models/linear_model.pkl')
    joblib.dump(scaler, 'models/scaler.pkl')
    
    # Evaluate the model
    print(f"Model Score: {model.score(X_test, y_test)}")

if __name__ == '__main__':
    train_model()
