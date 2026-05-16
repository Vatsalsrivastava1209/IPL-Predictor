"""Tiny CSV observability layer for a portfolio-grade data product."""

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "outputs"
EVENT_LOG = OUTPUT_DIR / "app_events.csv"
RUN_LOG = OUTPUT_DIR / "simulation_runs.csv"
PROBABILITY_HISTORY = OUTPUT_DIR / "probability_history.csv"


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


def _append_csv(path, row):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame([row])
    write_header = not Path(path).exists()
    df.to_csv(path, mode="a", index=False, header=write_header)


def new_session_id():
    return uuid4().hex


def log_event(event_name, **payload):
    row = {
        "event_name": event_name,
        "event_timestamp_utc": utc_now_iso(),
        **payload,
    }
    _append_csv(EVENT_LOG, row)


def log_simulation_run(
    *,
    run_id,
    data_snapshot_hash,
    n_simulations,
    seed,
    runtime_ms,
    success,
    error_type="",
    locked_match_no="",
    locked_winner="",
    top_team="",
    top_champion_pct="",
):
    _append_csv(
        RUN_LOG,
        {
            "run_id": run_id,
            "run_timestamp_utc": utc_now_iso(),
            "data_snapshot_hash": data_snapshot_hash,
            "n_simulations": n_simulations,
            "seed": seed,
            "runtime_ms": round(runtime_ms, 2),
            "success": bool(success),
            "error_type": error_type,
            "locked_match_no": locked_match_no,
            "locked_winner": locked_winner,
            "top_team": top_team,
            "top_champion_pct": top_champion_pct,
        },
    )


def log_probability_history(run_id, data_snapshot_hash, probabilities):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history = probabilities.copy()
    history.insert(0, "run_id", run_id)
    history.insert(1, "recorded_at_utc", utc_now_iso())
    history.insert(2, "data_snapshot_hash", data_snapshot_hash)
    write_header = not PROBABILITY_HISTORY.exists()
    history.to_csv(PROBABILITY_HISTORY, mode="a", index=False, header=write_header)
