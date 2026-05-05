# IPL 2026 Winner Prediction & Simulation

This project predicts the outcome of IPL matches and runs a Monte Carlo simulation to forecast the winner of the IPL 2026 tournament.

## Project Structure
- `data/`: Place your raw Kaggle CSV datasets here (`matches.csv`, `deliveries.csv`).
- `src/`: Contains all the Python scripts for preprocessing, modeling, and simulation.
- `notebooks/`: Jupyter notebooks for exploratory data analysis (EDA).
- `app.py`: The Streamlit dashboard application.

## Setup Instructions
1. Install dependencies: `pip install -r requirements.txt`
2. Download the IPL dataset from Kaggle and place the CSV files in the `data/` folder.
   - Recommended dataset: [IPL Complete Dataset (2008 - 2024)](https://www.kaggle.com/datasets/patrickb1912/ipl-complete-dataset-20082020)
3. Run the data preprocessing script.
4. Train the model.
5. Run the Streamlit app: `streamlit run app.py`
