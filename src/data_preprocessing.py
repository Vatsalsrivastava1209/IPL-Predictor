import pandas as pd
import numpy as np
import os

# Define file paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MATCHES_FILE = os.path.join(DATA_DIR, 'matches.csv')
DELIVERIES_FILE = os.path.join(DATA_DIR, 'deliveries.csv')
PROCESSED_DATA_FILE = os.path.join(DATA_DIR, 'processed_matches.csv')

def load_data():
    """Loads the raw IPL data."""
    if not os.path.exists(MATCHES_FILE) or not os.path.exists(DELIVERIES_FILE):
        raise FileNotFoundError(f"Please download the IPL dataset and place matches.csv and deliveries.csv in {DATA_DIR}")
    
    print("Loading datasets...")
    matches = pd.read_csv(MATCHES_FILE)
    deliveries = pd.read_csv(DELIVERIES_FILE)
    return matches, deliveries

def clean_data(matches):
    """Cleans the matches dataset (handling missing values, standardizing team names)."""
    print("Cleaning data...")
    
    # Drop matches with no result
    matches = matches[matches['result'] != 'no result']
    
    # Standardize team names (e.g., Rising Pune Supergiants, Delhi Daredevils -> Delhi Capitals)
    team_mapping = {
        'Delhi Daredevils': 'Delhi Capitals',
        'Kings XI Punjab': 'Punjab Kings',
        'Deccan Chargers': 'Sunrisers Hyderabad',
        'Pune Warriors': 'Rising Pune Supergiant',
        'Rising Pune Supergiants': 'Rising Pune Supergiant',
        'Gujarat Lions': 'Gujarat Titans' # Note: Simplification for historical continuity, though legally distinct
    }
    
    matches['team1'] = matches['team1'].replace(team_mapping)
    matches['team2'] = matches['team2'].replace(team_mapping)
    matches['winner'] = matches['winner'].replace(team_mapping)
    matches['toss_winner'] = matches['toss_winner'].replace(team_mapping)
    
    return matches

def extract_features(matches):
    """Extracts features for our ML model."""
    print("Extracting features...")
    
    # Target variable: 1 if team1 wins, 0 if team2 wins
    matches['team1_win'] = (matches['team1'] == matches['winner']).astype(int)
    
    # Feature: Did the team that won the toss win the match?
    matches['toss_winner_is_winner'] = (matches['toss_winner'] == matches['winner']).astype(int)
    
    # Select our baseline features
    features = ['city', 'team1', 'team2', 'toss_winner', 'toss_decision', 'venue', 'team1_win']
    model_data = matches[features].dropna()
    
    return model_data

if __name__ == "__main__":
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    try:
        matches, deliveries = load_data()
        cleaned_matches = clean_data(matches)
        model_data = extract_features(cleaned_matches)
        
        # Save processed data
        model_data.to_csv(PROCESSED_DATA_FILE, index=False)
        print(f"Data preprocessing complete. Saved to {PROCESSED_DATA_FILE}")
        
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("Please download the Kaggle dataset first.")
