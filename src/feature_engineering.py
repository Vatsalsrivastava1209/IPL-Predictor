import pandas as pd
import os
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, 'data')
MATCHES_FILE = os.path.join(DATA_DIR, 'matches.csv')
DELIVERIES_FILE = os.path.join(DATA_DIR, 'deliveries.csv')
ENGINEERED_DATA_FILE = os.path.join(DATA_DIR, 'engineered_matches.csv')

def standardize_teams(df, cols):
    team_mapping = {
        'Delhi Daredevils': 'Delhi Capitals',
        'Kings XI Punjab': 'Punjab Kings',
        'Deccan Chargers': 'Sunrisers Hyderabad',
        'Pune Warriors': 'Rising Pune Supergiant',
        'Rising Pune Supergiants': 'Rising Pune Supergiant',
        'Gujarat Lions': 'Gujarat Titans'
    }
    for col in cols:
        df[col] = df[col].replace(team_mapping)
    return df

def create_features():
    print("Loading data...")
    matches = pd.read_csv(MATCHES_FILE, low_memory=False)
    deliveries = pd.read_csv(DELIVERIES_FILE, low_memory=False)
    
    print("Standardizing team names...")
    matches = standardize_teams(matches, ['team1', 'team2', 'winner', 'toss_winner'])
    deliveries = standardize_teams(deliveries, ['batting_team', 'bowling_team'])
    
    # Sort matches by date to ensure chronologically correct rolling averages
    matches['date'] = pd.to_datetime(matches['date'])
    matches = matches.sort_values('date').reset_index(drop=True)
    
    print("Calculating match totals...")
    match_totals = deliveries.groupby(['match_id', 'batting_team'])['total_runs'].sum().reset_index()
    
    print("Calculating rolling team form (last 5 matches)...")
    engineered_matches = []
    team_history = {}
    
    for idx, row in matches.iterrows():
        match_id = row['id']
        team1 = row['team1']
        team2 = row['team2']
        
        # Initialize if not exists
        if team1 not in team_history: team_history[team1] = {'scored': [], 'conceded': []}
        if team2 not in team_history: team_history[team2] = {'scored': [], 'conceded': []}
        
        # Calculate features (average of last 5)
        # We default to 160 runs if the team has no history
        t1_scored = np.mean(team_history[team1]['scored'][-5:]) if len(team_history[team1]['scored']) > 0 else 160
        t1_conceded = np.mean(team_history[team1]['conceded'][-5:]) if len(team_history[team1]['conceded']) > 0 else 160
        
        t2_scored = np.mean(team_history[team2]['scored'][-5:]) if len(team_history[team2]['scored']) > 0 else 160
        t2_conceded = np.mean(team_history[team2]['conceded'][-5:]) if len(team_history[team2]['conceded']) > 0 else 160
        
        row_dict = row.to_dict()
        row_dict['team1_last_5_scored'] = round(t1_scored, 2)
        row_dict['team1_last_5_conceded'] = round(t1_conceded, 2)
        row_dict['team2_last_5_scored'] = round(t2_scored, 2)
        row_dict['team2_last_5_conceded'] = round(t2_conceded, 2)
        
        engineered_matches.append(row_dict)
        
        # Now update history for the NEXT match
        t1_match_runs = match_totals[(match_totals['match_id'] == match_id) & (match_totals['batting_team'] == team1)]['total_runs']
        t2_match_runs = match_totals[(match_totals['match_id'] == match_id) & (match_totals['batting_team'] == team2)]['total_runs']
        
        r1 = t1_match_runs.values[0] if len(t1_match_runs) > 0 else 0
        r2 = t2_match_runs.values[0] if len(t2_match_runs) > 0 else 0
        
        if r1 > 0 and r2 > 0: # Only append if the match had innings for both teams
            team_history[team1]['scored'].append(r1)
            team_history[team1]['conceded'].append(r2)
            team_history[team2]['scored'].append(r2)
            team_history[team2]['conceded'].append(r1)

    print("Saving engineered features...")
    df_engineered = pd.DataFrame(engineered_matches)
    
    # Drop rows without result
    df_engineered = df_engineered[df_engineered['result'] != 'no result']
    
    # Target variable
    df_engineered['team1_win'] = (df_engineered['team1'] == df_engineered['winner']).astype(int)
    
    # Clean features
    features = ['city', 'team1', 'team2', 'toss_winner', 'toss_decision', 'venue', 
                'team1_last_5_scored', 'team1_last_5_conceded', 
                'team2_last_5_scored', 'team2_last_5_conceded', 'team1_win']
                
    model_data = df_engineered[features].dropna()
    model_data.to_csv(ENGINEERED_DATA_FILE, index=False)
    print(f"Done! Saved to {ENGINEERED_DATA_FILE}")

if __name__ == "__main__":
    create_features()
