"""Ingest live CricAPI results into the manual CSV source of truth."""

from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from src.data_loader import FIXTURES_FILE, STATE_FILE
from src.live_cricket_api import fetch_ipl_live_matches


def _metadata(snapshot_id, source):
    return {
        "data_snapshot_id": snapshot_id,
        "source": source,
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
    }


def _same_match(fixture, live_match):
    teams_fixture = {fixture["team1"], fixture["team2"]}
    teams_live = {live_match.team1, live_match.team2}
    if teams_fixture != teams_live:
        return False
    fixture_date = pd.to_datetime(fixture["date"]).date()
    if live_match.date is None:
        return True
    return abs((fixture_date - live_match.date.date()).days) <= 1


def _score_for_fixture_team(fixture_team, live_match):
    if fixture_team == live_match.team1:
        return live_match.team1_score
    if fixture_team == live_match.team2:
        return live_match.team2_score
    return None


def _nrr_delta(winner_score, loser_score):
    if winner_score is None or loser_score is None:
        return 0.0
    return max(0.03, min(0.45, (winner_score - loser_score) / 120.0))


def apply_live_matches(state, fixtures, live_matches, snapshot_id, source="CricAPI live ingest"):
    state = state.copy()
    fixtures = fixtures.copy()
    updates = []

    for live_match in live_matches:
        if live_match.status != "completed" or not live_match.winner:
            continue

        candidates = fixtures[fixtures.apply(lambda row: _same_match(row, live_match), axis=1)]
        if candidates.empty:
            continue

        fixture_idx = candidates.index[0]
        fixture = fixtures.loc[fixture_idx]
        was_completed = str(fixture["status"]).lower() == "completed"
        team1_score = _score_for_fixture_team(fixture["team1"], live_match)
        team2_score = _score_for_fixture_team(fixture["team2"], live_match)

        fixtures.loc[fixture_idx, "status"] = "completed"
        fixtures.loc[fixture_idx, "winner"] = live_match.winner
        fixtures.loc[fixture_idx, "team1_score"] = team1_score
        fixtures.loc[fixture_idx, "team2_score"] = team2_score
        if live_match.venue:
            fixtures.loc[fixture_idx, "venue"] = live_match.venue

        if not was_completed:
            loser = fixture["team2"] if live_match.winner == fixture["team1"] else fixture["team1"]
            winner_score = team1_score if live_match.winner == fixture["team1"] else team2_score
            loser_score = team2_score if live_match.winner == fixture["team1"] else team1_score
            nrr_move = _nrr_delta(winner_score, loser_score)

            state.loc[state["team"] == live_match.winner, "matches"] += 1
            state.loc[state["team"] == live_match.winner, "wins"] += 1
            state.loc[state["team"] == live_match.winner, "points"] += 2
            state.loc[state["team"] == live_match.winner, "nrr"] = (
                state.loc[state["team"] == live_match.winner, "nrr"].astype(float) + nrr_move
            )

            state.loc[state["team"] == loser, "matches"] += 1
            state.loc[state["team"] == loser, "losses"] += 1
            state.loc[state["team"] == loser, "nrr"] = (
                state.loc[state["team"] == loser, "nrr"].astype(float) - nrr_move
            )

        updates.append(
            {
                "match_no": int(fixture["match_no"]),
                "team1": fixture["team1"],
                "team2": fixture["team2"],
                "winner": live_match.winner,
                "was_completed": was_completed,
                "source_status": live_match.source_status,
            }
        )

    meta = _metadata(snapshot_id, source)
    for key, value in meta.items():
        state[key] = value
        fixtures[key] = value

    return state, fixtures, pd.DataFrame(updates)


def ingest_live_data(apply=False):
    live_matches = fetch_ipl_live_matches()
    state = pd.read_csv(STATE_FILE)
    fixtures = pd.read_csv(FIXTURES_FILE)
    snapshot_id = f"ipl-live-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    updated_state, updated_fixtures, updates = apply_live_matches(state, fixtures, live_matches, snapshot_id)
    if apply:
        updated_state.to_csv(STATE_FILE, index=False)
        updated_fixtures.to_csv(FIXTURES_FILE, index=False)
    return updates


def main():
    parser = ArgumentParser(description="Fetch CricAPI IPL results and update local CSVs.")
    parser.add_argument("--apply", action="store_true", help="Write updates to CSV files. Without this, run in dry-run mode.")
    args = parser.parse_args()
    try:
        updates = ingest_live_data(apply=args.apply)
    except ValueError as exc:
        print(f"Live ingest skipped: {exc}")
        print("Set CRICAPI_KEY in your shell, then rerun this command.")
        return
    mode = "applied" if args.apply else "dry-run"
    print(f"Live ingest {mode}. Matched completed results: {len(updates)}")
    if not updates.empty:
        print(updates.to_string(index=False))


if __name__ == "__main__":
    main()
