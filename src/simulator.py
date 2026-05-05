import pandas as pd
import numpy as np
import joblib
import os
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(BASE_DIR, 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'rf_model.pkl')
ENCODERS_PATH = os.path.join(MODEL_DIR, 'encoders.pkl')

def load_models():
    model = joblib.load(MODEL_PATH)
    encoders = joblib.load(ENCODERS_PATH)
    return model, encoders

# Core IPL Teams (using names mostly found in the dataset)
TEAMS = [
    'Chennai Super Kings', 'Mumbai Indians', 'Royal Challengers Bangalore', 
    'Kolkata Knight Riders', 'Delhi Capitals', 'Punjab Kings', 
    'Rajasthan Royals', 'Sunrisers Hyderabad', 'Gujarat Titans', 'Lucknow Super Giants'
]

# Base stats for 2026 based roughly on team historical profiles
# This is where deep domain knowledge comes in.
TEAM_STATS = {
    'Chennai Super Kings': {'scored': 175, 'conceded': 160},
    'Mumbai Indians': {'scored': 170, 'conceded': 165},
    'Royal Challengers Bangalore': {'scored': 185, 'conceded': 180},
    'Kolkata Knight Riders': {'scored': 168, 'conceded': 155},
    'Delhi Capitals': {'scored': 160, 'conceded': 165},
    'Punjab Kings': {'scored': 165, 'conceded': 170},
    'Rajasthan Royals': {'scored': 168, 'conceded': 162},
    'Sunrisers Hyderabad': {'scored': 180, 'conceded': 175}, # Factoring in their aggressive 2024 season
    'Gujarat Titans': {'scored': 170, 'conceded': 155},
    'Lucknow Super Giants': {'scored': 165, 'conceded': 160}
}

DEFAULT_CITY = "Mumbai"
DEFAULT_VENUE = "Wankhede Stadium"

def simulate_match(model, encoders, team1, team2):
    toss_winner = np.random.choice([team1, team2])
    toss_decision = 'field' 
    
    # Fallbacks in case a team name is slightly different in the encoder
    t1_enc = team1 if team1 in encoders['team1'].classes_ else 'Delhi Capitals'
    t2_enc = team2 if team2 in encoders['team2'].classes_ else 'Punjab Kings'
    tw_enc = toss_winner if toss_winner in encoders['toss_winner'].classes_ else t1_enc
    
    city = DEFAULT_CITY if DEFAULT_CITY in encoders['city'].classes_ else encoders['city'].classes_[0]
    venue = DEFAULT_VENUE if DEFAULT_VENUE in encoders['venue'].classes_ else encoders['venue'].classes_[0]
    td_enc = toss_decision if toss_decision in encoders['toss_decision'].classes_ else encoders['toss_decision'].classes_[0]
    
    input_data = pd.DataFrame([{
        'city': encoders['city'].transform([city])[0],
        'team1': encoders['team1'].transform([t1_enc])[0],
        'team2': encoders['team2'].transform([t2_enc])[0],
        'toss_winner': encoders['toss_winner'].transform([tw_enc])[0],
        'toss_decision': encoders['toss_decision'].transform([td_enc])[0],
        'venue': encoders['venue'].transform([venue])[0],
        'team1_last_5_scored': TEAM_STATS[team1]['scored'],
        'team1_last_5_conceded': TEAM_STATS[team1]['conceded'],
        'team2_last_5_scored': TEAM_STATS[team2]['scored'],
        'team2_last_5_conceded': TEAM_STATS[team2]['conceded']
    }])
    
    # Predict probabilities
    prob = model.predict_proba(input_data)[0]
    
    # Randomly choose winner weighted by predicted probability
    winner_idx = np.random.choice([0, 1], p=[prob[0], prob[1]])
    
    return team1 if winner_idx == 1 else team2

def run_tournament(model, encoders):
    points = {team: 0 for team in TEAMS}
    
    # Group Stage: Double Round Robin
    for i in range(len(TEAMS)):
        for j in range(i+1, len(TEAMS)):
            winner1 = simulate_match(model, encoders, TEAMS[i], TEAMS[j])
            points[winner1] += 2
            
            winner2 = simulate_match(model, encoders, TEAMS[j], TEAMS[i])
            points[winner2] += 2
            
    # Standings
    standings = sorted(points.items(), key=lambda x: x[1], reverse=True)
    top_4 = [team for team, pts in standings[:4]]
    
    # Playoffs
    q1_winner = simulate_match(model, encoders, top_4[0], top_4[1])
    q1_loser = top_4[1] if q1_winner == top_4[0] else top_4[0]
    
    elim_winner = simulate_match(model, encoders, top_4[2], top_4[3])
    q2_winner = simulate_match(model, encoders, q1_loser, elim_winner)
    
    champion = simulate_match(model, encoders, q1_winner, q2_winner)
    return champion

def monte_carlo_simulation(n_simulations=100):
    print("Loading models for simulation...", flush=True)
    model, encoders = load_models()
    
    print(f"Running {n_simulations} tournament simulations. This may take a moment...", flush=True)
    champions = []
    
    for i in range(n_simulations):
        if (i+1) % 20 == 0:
            print(f"Completed {i+1}/{n_simulations} simulated seasons...", flush=True)
        champ = run_tournament(model, encoders)
        champions.append(champ)
        
    print("\n" + "="*50, flush=True)
    print(" 🏆 IPL 2026 PROJECTED WINNER PROBABILITIES 🏆", flush=True)
    print("="*50, flush=True)
    
    counts = Counter(champions)
    for team, count in counts.most_common():
        win_prob = (count / n_simulations) * 100
        print(f"{team:<30} | {win_prob:>5.1f}% chance to win", flush=True)
        
if __name__ == "__main__":
    monte_carlo_simulation(100)
