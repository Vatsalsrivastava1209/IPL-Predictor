# IPL 2026 Champion Predictor Model Card

## Purpose
Estimate IPL 2026 playoff and title probabilities for a public, interactive dashboard. The output is a probability distribution, not a guaranteed prediction.

## Inputs
- Current manual points table: `data/ipl_2026_state.csv`
- Remaining manual fixtures: `data/ipl_2026_fixtures.csv`
- Manual strength assumptions: `data/team_strength_overrides.csv`
- Historical IPL matches: `data/matches.csv`
- Optional CricAPI live result ingest through `src.live_ingest`

Every manual CSV includes `data_snapshot_id`, `source`, and `last_updated_utc` so runs can be traced to a specific input snapshot.

## Method
- Historical matches create a background Elo prior for current IPL teams.
- Current 2026 completed fixtures update that Elo more strongly.
- Match probabilities combine Elo, NRR, batting index, bowling index, form index, and venue/home-city effect.
- Monte Carlo simulation runs the remaining league fixtures, sorts the table by points and NRR, then simulates the IPL playoff bracket.

## Outputs
- Top 4 probability
- Top 2 probability
- Finalist probability
- Champion probability
- What-if title/playoff deltas

## Validation
Use `python -m src.backtest` to create:
- `outputs/backtest_predictions.csv`
- `outputs/backtest_calibration.csv`
- `reports/backtest_summary.md`

Primary validation metrics:
- Brier score
- Log loss
- Calibration by probability bucket
- Upset rate
- Accuracy

## Limitations
- Manual strength overrides are subjective and must be audited through snapshot metadata and notes.
- Player injuries, toss, exact playing XI, weather, and innings-level matchups are not fully modeled.
- NRR changes are approximated during simulation.
- The current backtest evaluates match probabilities, not full-season champion probabilities.

## Update Process
After each match:
1. Run `python -m src.live_ingest` to preview live API matches.
2. Run `python -m src.live_ingest --apply` if the match is correctly matched.
3. Manually review the points table and NRR.
4. Update manual overrides only if team assumptions changed.
5. Run the app or `python -m src.simulator`.
6. Review `outputs/simulation_runs.csv` and `outputs/probability_history.csv`.
