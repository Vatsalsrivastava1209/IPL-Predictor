import streamlit as st
import pandas as pd
import joblib
import os
import sys
from collections import Counter

# Set up page
st.set_page_config(page_title="IPL 2026 Winner Predictor", layout="wide")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'models')
MODEL_PATH = os.path.join(MODEL_DIR, 'rf_model.pkl')
ENCODERS_PATH = os.path.join(MODEL_DIR, 'encoders.pkl')

# Allow importing from src
sys.path.append(BASE_DIR)
from src.simulator import run_tournament

def load_models():
    try:
        model = joblib.load(MODEL_PATH)
        encoders = joblib.load(ENCODERS_PATH)
        return model, encoders
    except FileNotFoundError:
        st.error("Model files not found. Please run src/model.py first.")
        return None, None

model, encoders = load_models()

st.title("IPL 2026 AI Predictor")
st.markdown("Predict individual match winners or run a full simulation of the 2026 tournament.")

if model and encoders:
    # --- TAB 1: Match Predictor ---
    st.header("Match Predictor")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Match Details")
        team1 = st.selectbox("Select Team 1", options=encoders['team1'].classes_)
        
        # Filter team2 to not include team1
        team2_options = [t for t in encoders['team2'].classes_ if t != team1]
        team2 = st.selectbox("Select Team 2", options=team2_options)
        
    with col2:
        st.subheader("Conditions")
        venue = st.selectbox("Select Venue", options=encoders['venue'].classes_)
        city_options = encoders['city'].classes_
        city = st.selectbox("Select City", options=city_options)
        
        toss_winner = st.selectbox("Toss Winner", options=[team1, team2])
        toss_decision = st.selectbox("Toss Decision", options=encoders['toss_decision'].classes_)

    st.subheader("Recent Form (Last 5 Matches)")
    st.markdown("Adjust these sliders based on how well the teams have been playing recently.")
    col3, col4 = st.columns(2)
    with col3:
        t1_scored = st.slider(f"{team1} Avg Scored", 100, 250, 160)
        t1_conceded = st.slider(f"{team1} Avg Conceded", 100, 250, 160)
    with col4:
        t2_scored = st.slider(f"{team2} Avg Scored", 100, 250, 160)
        t2_conceded = st.slider(f"{team2} Avg Conceded", 100, 250, 160)

    if st.button("Predict Match Winner"):
        # Prepare input data
        try:
            input_data = pd.DataFrame([{
                'city': city,
                'team1': team1,
                'team2': team2,
                'toss_winner': toss_winner,
                'toss_decision': toss_decision,
                'venue': venue,
                'team1_last_5_scored': t1_scored,
                'team1_last_5_conceded': t1_conceded,
                'team2_last_5_scored': t2_scored,
                'team2_last_5_conceded': t2_conceded
            }])
            
            # Encode categorical features
            for col in ['city', 'team1', 'team2', 'toss_winner', 'toss_decision', 'venue']:
                input_data[col] = encoders[col].transform(input_data[col])
                
            # Predict
            prediction = model.predict(input_data)[0]
            probability = model.predict_proba(input_data)[0]
            
            winner = team1 if prediction == 1 else team2
            win_prob = probability[1] if prediction == 1 else probability[0]
            
            st.success(f"**Predicted Winner: {winner}**")
            st.info(f"Probability of winning: {win_prob * 100:.1f}%")
            st.progress(float(win_prob))
            
        except ValueError as e:
            st.error(f"Error making prediction: The model hasn't seen this combination before. Try another venue/city.")

    # --- TAB 2: Tournament Simulator ---
    st.markdown("---")
    st.header("Simulate IPL 2026 Champion")
    st.markdown("Run a Monte Carlo simulation of the entire 74-match season to see who is mathematically most likely to lift the trophy.")
    
    if st.button("Run Simulation (100 Seasons)"):
        with st.spinner("Simulating 7,400 matches... This takes about 10-15 seconds."):
            champions = []
            progress_bar = st.progress(0)
            
            for i in range(100):
                champ = run_tournament(model, encoders)
                champions.append(champ)
                progress_bar.progress((i + 1) / 100)
                
            counts = Counter(champions)
            
            st.subheader("Simulation Results")
            res_df = pd.DataFrame(counts.items(), columns=["Team", "Win Probability (%)"])
            res_df = res_df.sort_values(by="Win Probability (%)", ascending=False)
            
            top_team = res_df.iloc[0]["Team"]
            
            st.success(f"**Projected IPL 2026 Winner: {top_team}**")
            
            # Show a bar chart
            st.bar_chart(res_df.set_index("Team"))
