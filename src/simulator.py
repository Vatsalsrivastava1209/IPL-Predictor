"""Monte Carlo simulator for the IPL 2026 probability dashboard."""

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from uuid import uuid4

import numpy as np
import pandas as pd

from src.config import CURRENT_TEAMS
from src.data_loader import DATA_DIR, load_fixtures, load_overrides, load_state
from src.lineage import data_snapshot_hash
from src.observability import log_probability_history, log_simulation_run
from src.rating_engine import build_team_ratings, match_win_probability


HISTORICAL_MATCHES_FILE = DATA_DIR / "matches.csv"


@dataclass(frozen=True)
class SimulationOutput:
    run_id: str
    data_snapshot_hash: str
    runtime_ms: float
    probabilities: pd.DataFrame
    current_table: pd.DataFrame
    fixtures: pd.DataFrame
    ratings: dict
    x_summary: str


def sort_table(table):
    return sorted(
        table.items(),
        key=lambda item: (item[1]["points"], item[1]["nrr"], item[1].get("wins", 0)),
        reverse=True,
    )


def _initial_table(state):
    table = {}
    for _, row in state.iterrows():
        table[row["team"]] = {
            "points": int(row["points"]),
            "nrr": float(row["nrr"]),
            "wins": int(row["wins"]),
            "matches": int(row["matches"]),
        }
    return table


def _apply_result(table, team1, team2, winner, rng, p_team1):
    loser = team2 if winner == team1 else team1
    confidence = abs(p_team1 - 0.5)
    margin = float(rng.uniform(0.03, 0.18) + confidence * 0.22)

    table[winner]["points"] += 2
    table[winner]["wins"] += 1
    table[winner]["matches"] += 1
    table[loser]["matches"] += 1
    table[winner]["nrr"] += margin
    table[loser]["nrr"] -= margin


def _simulate_match(team1, team2, row, ratings, rng, forced_winner=None):
    p_team1 = match_win_probability(
        team1,
        team2,
        ratings,
        city=row.get("city", ""),
        venue=row.get("venue", ""),
    )
    if forced_winner:
        return forced_winner, p_team1
    winner = team1 if rng.random() < p_team1 else team2
    return winner, p_team1


def _simulate_playoff_match(team1, team2, ratings, rng):
    p_team1 = match_win_probability(team1, team2, ratings)
    return team1 if rng.random() < p_team1 else team2


def _simulate_one_season(state, fixtures, ratings, rng, locked_match_no=None, locked_winner=None):
    table = _initial_table(state)
    remaining = fixtures[fixtures["status"] == "scheduled"]

    for _, row in remaining.iterrows():
        forced = locked_winner if int(row["match_no"]) == locked_match_no else None
        winner, p_team1 = _simulate_match(row["team1"], row["team2"], row, ratings, rng, forced)
        _apply_result(table, row["team1"], row["team2"], winner, rng, p_team1)

    standings = sort_table(table)
    top_4 = [team for team, _ in standings[:4]]
    top_2 = [team for team, _ in standings[:2]]

    q1_winner = _simulate_playoff_match(top_4[0], top_4[1], ratings, rng)
    q1_loser = top_4[1] if q1_winner == top_4[0] else top_4[0]
    eliminator_winner = _simulate_playoff_match(top_4[2], top_4[3], ratings, rng)
    q2_winner = _simulate_playoff_match(q1_loser, eliminator_winner, ratings, rng)
    champion = _simulate_playoff_match(q1_winner, q2_winner, ratings, rng)

    return top_4, top_2, [q1_winner, q2_winner], champion


def run_monte_carlo(
    n_simulations=10_000,
    state=None,
    fixtures=None,
    overrides=None,
    historical_matches_path=HISTORICAL_MATCHES_FILE,
    locked_match_no=None,
    locked_winner=None,
    seed=42,
    persist=False,
):
    started = perf_counter()
    run_id = uuid4().hex
    snapshot_hash = data_snapshot_hash() if state is None and fixtures is None and overrides is None else "in-memory"

    state = load_state() if state is None else state
    fixtures = load_fixtures() if fixtures is None else fixtures
    overrides = load_overrides() if overrides is None else overrides

    try:
        if locked_match_no is not None:
            match = fixtures.loc[fixtures["match_no"] == int(locked_match_no)]
            if match.empty:
                raise ValueError(f"No fixture found for match_no={locked_match_no}")
            allowed = {match.iloc[0]["team1"], match.iloc[0]["team2"]}
            if locked_winner not in allowed:
                raise ValueError("Locked winner must be one of the selected fixture teams")

        ratings = build_team_ratings(state, fixtures, overrides, Path(historical_matches_path))
        rng = np.random.default_rng(seed)

        counters = {
            team: {"top4": 0, "top2": 0, "final": 0, "champion": 0}
            for team in CURRENT_TEAMS
        }

        for _ in range(int(n_simulations)):
            top_4, top_2, finalists, champion = _simulate_one_season(
                state,
                fixtures,
                ratings,
                rng,
                locked_match_no=locked_match_no,
                locked_winner=locked_winner,
            )
            for team in top_4:
                counters[team]["top4"] += 1
            for team in top_2:
                counters[team]["top2"] += 1
            for team in finalists:
                counters[team]["final"] += 1
            counters[champion]["champion"] += 1

        rows = []
        for team, values in counters.items():
            rows.append(
                {
                    "team": team,
                    "top4_pct": values["top4"] / n_simulations * 100,
                    "top2_pct": values["top2"] / n_simulations * 100,
                    "final_pct": values["final"] / n_simulations * 100,
                    "champion_pct": values["champion"] / n_simulations * 100,
                    "elo": ratings[team].elo,
                }
            )

        probabilities = pd.DataFrame(rows).sort_values("champion_pct", ascending=False).reset_index(drop=True)
        leader = probabilities.iloc[0]
        runtime_ms = (perf_counter() - started) * 1000
        x_summary = (
            f"IPL 2026 simulation update: {leader['team']} leads the title race at "
            f"{leader['champion_pct']:.1f}% across {n_simulations:,} Monte Carlo seasons. "
            f"Top 4 odds: {leader['top4_pct']:.1f}%."
        )
        if persist:
            log_simulation_run(
                run_id=run_id,
                data_snapshot_hash=snapshot_hash,
                n_simulations=n_simulations,
                seed=seed,
                runtime_ms=runtime_ms,
                success=True,
                locked_match_no=locked_match_no or "",
                locked_winner=locked_winner or "",
                top_team=leader["team"],
                top_champion_pct=round(float(leader["champion_pct"]), 3),
            )
            if locked_match_no is None:
                log_probability_history(run_id, snapshot_hash, probabilities)
        return SimulationOutput(run_id, snapshot_hash, runtime_ms, probabilities, state, fixtures, ratings, x_summary)
    except Exception as exc:
        runtime_ms = (perf_counter() - started) * 1000
        if persist:
            log_simulation_run(
                run_id=run_id,
                data_snapshot_hash=snapshot_hash,
                n_simulations=n_simulations,
                seed=seed,
                runtime_ms=runtime_ms,
                success=False,
                error_type=type(exc).__name__,
                locked_match_no=locked_match_no or "",
                locked_winner=locked_winner or "",
            )
        raise


def compare_what_if(match_no, n_simulations=5_000, persist=False):
    fixtures = load_fixtures()
    match = fixtures.loc[fixtures["match_no"] == int(match_no)]
    if match.empty:
        raise ValueError(f"No fixture found for match_no={match_no}")
    row = match.iloc[0]
    base = run_monte_carlo(n_simulations=n_simulations, persist=persist)
    team1_case = run_monte_carlo(n_simulations=n_simulations, locked_match_no=match_no, locked_winner=row["team1"], persist=persist)
    team2_case = run_monte_carlo(n_simulations=n_simulations, locked_match_no=match_no, locked_winner=row["team2"], persist=persist)
    return base, team1_case, team2_case


if __name__ == "__main__":
    result = run_monte_carlo(n_simulations=10_000)
    print(result.probabilities.to_string(index=False))
