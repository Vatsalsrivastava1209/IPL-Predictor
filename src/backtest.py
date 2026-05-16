"""Historical match-level backtest for the Elo probability engine."""

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from src.config import CURRENT_TEAMS, is_current_team, normalize_team_name
from src.rating_engine import BASE_ELO, _apply_elo, _expected_score


BASE_DIR = Path(__file__).resolve().parents[1]
MATCHES_FILE = BASE_DIR / "data" / "matches.csv"
OUTPUT_DIR = BASE_DIR / "outputs"
REPORT_DIR = BASE_DIR / "reports"


def _season_end_year(season):
    text = str(season)
    parts = text.replace("/", "-").split("-")
    year = parts[-1]
    return int("20" + year) if len(year) == 2 else int(year)


def _k_factor(year):
    if year >= 2024:
        return 28.0
    if year >= 2022:
        return 24.0
    if year >= 2020:
        return 20.0
    return 16.0


def _calibration_table(predictions):
    df = predictions.copy()
    df["bucket"] = pd.cut(
        df["predicted_prob_team1"],
        bins=[0, 0.2, 0.4, 0.6, 0.8, 1],
        labels=["0-20%", "20-40%", "40-60%", "60-80%", "80-100%"],
        include_lowest=True,
    )
    return (
        df.groupby("bucket", observed=False)
        .agg(matches=("actual_team1_win", "size"), avg_prediction=("predicted_prob_team1", "mean"), actual_win_rate=("actual_team1_win", "mean"))
        .reset_index()
    )


def run_backtest(start_year=2021, end_year=2024):
    matches = pd.read_csv(MATCHES_FILE, low_memory=False)
    matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
    matches = matches.dropna(subset=["date"]).sort_values("date")

    ratings = {team: BASE_ELO for team in CURRENT_TEAMS}
    rows = []

    for _, row in matches.iterrows():
        team1 = normalize_team_name(row.get("team1"))
        team2 = normalize_team_name(row.get("team2"))
        winner = normalize_team_name(row.get("winner"))
        result = str(row.get("result", "")).lower()
        year = _season_end_year(row.get("season"))

        if result == "no result" or not all(map(is_current_team, [team1, team2, winner])):
            continue

        prediction = _expected_score(ratings[team1], ratings[team2])
        actual = 1 if winner == team1 else 0

        if start_year <= year <= end_year:
            rows.append(
                {
                    "season": row.get("season"),
                    "date": row["date"].date().isoformat(),
                    "team1": team1,
                    "team2": team2,
                    "winner": winner,
                    "predicted_prob_team1": prediction,
                    "actual_team1_win": actual,
                }
            )

        _apply_elo(ratings, team1, team2, winner, _k_factor(year))

    predictions = pd.DataFrame(rows)
    if predictions.empty:
        raise ValueError("No backtest predictions were produced")

    y_true = predictions["actual_team1_win"]
    y_prob = predictions["predicted_prob_team1"].clip(0.001, 0.999)
    y_pred = (y_prob >= 0.5).astype(int)
    metrics = {
        "start_year": start_year,
        "end_year": end_year,
        "matches": int(len(predictions)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "brier_score": float(brier_score_loss(y_true, y_prob)),
        "log_loss": float(log_loss(y_true, y_prob)),
        "upset_rate": float(((y_prob >= 0.5).astype(int) != y_true).mean()),
    }
    calibration = _calibration_table(predictions)
    return predictions, metrics, calibration


def write_backtest_report(start_year=2021, end_year=2024):
    predictions, metrics, calibration = run_backtest(start_year, end_year)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    predictions.to_csv(OUTPUT_DIR / "backtest_predictions.csv", index=False)
    calibration.to_csv(OUTPUT_DIR / "backtest_calibration.csv", index=False)

    report = [
        "# IPL Predictor Backtest",
        "",
        f"Window: {metrics['start_year']}-{metrics['end_year']}",
        f"Matches evaluated: {metrics['matches']}",
        "",
        "## Metrics",
        f"- Accuracy: {metrics['accuracy']:.3f}",
        f"- Brier score: {metrics['brier_score']:.3f}",
        f"- Log loss: {metrics['log_loss']:.3f}",
        f"- Upset rate: {metrics['upset_rate']:.3f}",
        "",
        "## Calibration",
        "```text",
        calibration.to_string(index=False),
        "```",
        "",
        "## Notes",
        "- This backtest evaluates match winner probabilities, not full-season champion odds.",
        "- Retired teams are excluded so validation is aligned with the current-season simulator.",
        "- The result should be used to compare model variants over time.",
    ]
    report_path = REPORT_DIR / "backtest_summary.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    return metrics


if __name__ == "__main__":
    metrics = write_backtest_report()
    print(metrics)
