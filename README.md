# IPL 2026 Champion Predictor

A Streamlit dashboard for IPL 2026 playoff and title probabilities. The main engine is an explainable Hybrid Elo + Monte Carlo simulator, not the old Random Forest demo.

## What It Shows
- Top 4 probability
- Top 2 probability
- Finalist probability
- Champion probability
- What-if impact for one upcoming match
- X-ready summary text and CSV export

## Data Source
The dashboard supports live ingestion with manual CSV fallback.

- `data/ipl_2026_state.csv`: current table snapshot
- `data/ipl_2026_fixtures.csv`: remaining league fixtures
- `data/team_strength_overrides.csv`: optional human adjustments for batting, bowling, and form

Each manual CSV includes:
- `data_snapshot_id`
- `source`
- `last_updated_utc`

Update those files after each match. The app hashes the CSV contents and automatically reruns cached simulations when the snapshot changes.

## Live API Mode
The live layer uses CricAPI/CricketData and never stores your key in the repo.

For the deployed app, put the key in **GitHub repository secrets**, not in code:

```text
Repository Settings -> Secrets and variables -> Actions -> New repository secret
Name: CRICAPI_KEY
Value: your API key
```

The workflow in `.github/workflows/daily-live-ingest.yml` runs once per day and can also be triggered manually from GitHub Actions.

Set your key in the shell:
```bash
set CRICAPI_KEY=your_key_here
```

PowerShell:
```powershell
$env:CRICAPI_KEY="your_key_here"
```

Dry-run live ingest:
```bash
python -m src.live_ingest
```

Apply matched completed results to the CSVs:
```bash
python -m src.live_ingest --apply
```

Live mode updates matched fixtures and adjusts the local points table when a scheduled fixture becomes completed. Manual CSVs remain the source of truth and fallback.

On Streamlit Cloud, users do not run `python -m src.live_ingest --apply`. The deployed app only reads the latest committed CSV snapshot. GitHub Actions performs the refresh and commits changes.

## After-Match Update Workflow
1. Mark the completed fixture as `completed`.
2. Fill `winner`, `team1_score`, and `team2_score`.
3. Update the table in `ipl_2026_state.csv`.
4. Update `data_snapshot_id` and `last_updated_utc`.
5. Open the app and review the new odds.
6. Check `outputs/probability_history.csv` to see how title odds moved.

## Multi-Year Use
The same architecture can be reused every IPL season:
- create new season state and fixture CSVs
- update `data_snapshot_id` naming
- keep the historical `matches.csv` as the Elo prior
- run simulations after each match

The current file names are IPL 2026-specific, but the engine is intentionally CSV-driven so it can be generalized later.

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Run Tests
```bash
pytest
```

## Backtest
```bash
python -m src.backtest
```

This writes:
- `outputs/backtest_predictions.csv`
- `outputs/backtest_calibration.csv`
- `reports/backtest_summary.md`

## Run Logs
When the dashboard runs simulations with persistence enabled, it writes:
- `outputs/simulation_runs.csv`
- `outputs/probability_history.csv`
- `outputs/app_events.csv`

## Methodology
Historical IPL matches are used only as an Elo prior. Current season state, NRR, manual strength overrides, and remaining fixtures carry the public-facing prediction. The output is probabilistic: it estimates ranges, not guaranteed winners.

The old model files in `models/` are kept as a historical baseline artifact. They are not required for the dashboard to run.

See `reports/model_card.md` for assumptions, validation, limitations, and update process.
