import pandas as pd
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MODEL_DIR = os.path.join(BASE_DIR, 'models')
ENGINEERED_DATA_FILE = os.path.join(DATA_DIR, 'engineered_matches.csv')

def train_model():
    print("Loading engineered data...")
    df = pd.read_csv(ENGINEERED_DATA_FILE)
    
    # Categorical columns to encode
    cat_cols = ['city', 'team1', 'team2', 'toss_winner', 'toss_decision', 'venue']
    
    # We will store our encoders so we can transform user input later
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df[col] = le.fit_transform(df[col])
        encoders[col] = le
        
    # X and y
    X = df.drop('team1_win', axis=1)
    y = df['team1_win']
    
    print("Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    print("Training Random Forest Classifier on new features...")
    # More trees, slightly deeper to capture complex relationships
    model = RandomForestClassifier(n_estimators=200, random_state=42, max_depth=12)
    model.fit(X_train, y_train)
    
    print("Evaluating model...")
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Accuracy: {accuracy * 100:.2f}%")
    print(classification_report(y_test, y_pred))
    
    # Feature importances
    importances = model.feature_importances_
    for name, imp in zip(X.columns, importances):
        print(f"{name}: {imp:.4f}")
    
    # Ensure models directory exists
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    # Save the model and encoders
    model_path = os.path.join(MODEL_DIR, 'rf_model.pkl')
    encoders_path = os.path.join(MODEL_DIR, 'encoders.pkl')
    
    joblib.dump(model, model_path)
    joblib.dump(encoders, encoders_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_model()
