"""CSV loading and validation for the IPL 2026 dashboard."""

from pathlib import Path

import pandas as pd

from src.config import CURRENT_TEAMS, RETIRED_TEAMS, normalize_team_name
from src.lineage import SNAPSHOT_COLUMNS, parse_utc


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"

STATE_FILE = DATA_DIR / "ipl_2026_state.csv"
FIXTURES_FILE = DATA_DIR / "ipl_2026_fixtures.csv"
OVERRIDES_FILE = DATA_DIR / "team_strength_overrides.csv"


def _validate_teams(values, context):
    unknown = sorted({team for team in values if team and team not in CURRENT_TEAMS})
    if unknown:
        raise ValueError(f"Unknown team names in {context}: {', '.join(unknown)}")
    retired = sorted({str(team).strip() for team in values if str(team).strip() in RETIRED_TEAMS})
    if retired:
        raise ValueError(f"Retired teams are not allowed in current-season files: {', '.join(retired)}")


def _validate_snapshot_metadata(df, path):
    missing = [col for col in SNAPSHOT_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"{Path(path).name} is missing metadata columns: {', '.join(missing)}")
    if df[SNAPSHOT_COLUMNS].isna().any().any():
        raise ValueError(f"{Path(path).name} metadata columns cannot be blank")
    parse_utc(df.loc[0, "last_updated_utc"], Path(path).name)


def load_state(path=STATE_FILE):
    required = ["team", "matches", "wins", "losses", "no_results", "points", "nrr"]
    df = pd.read_csv(path)
    _validate_snapshot_metadata(df, path)
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

    df = df[required].copy()
    df["team"] = df["team"].map(normalize_team_name)
    _validate_teams(df["team"], path.name)

    duplicate_teams = sorted(df.loc[df["team"].duplicated(), "team"].unique())
    if duplicate_teams:
        raise ValueError(f"Duplicate teams in {path.name}: {', '.join(duplicate_teams)}")

    missing_teams = sorted(set(CURRENT_TEAMS) - set(df["team"]))
    if missing_teams:
        raise ValueError(f"{path.name} must include every IPL 2026 team: {', '.join(missing_teams)}")

    for col in ["matches", "wins", "losses", "no_results", "points"]:
        df[col] = pd.to_numeric(df[col], errors="raise").astype(int)
    df["nrr"] = pd.to_numeric(df["nrr"], errors="raise").astype(float)

    bad_matches = df[df["matches"] != df["wins"] + df["losses"] + df["no_results"]]
    if not bad_matches.empty:
        raise ValueError("State table has rows where matches != wins + losses + no_results")

    bad_points = df[df["points"] != df["wins"] * 2 + df["no_results"]]
    if not bad_points.empty:
        raise ValueError("State table has rows where points != wins * 2 + no_results")

    return df.sort_values(["points", "nrr"], ascending=False).reset_index(drop=True)


def load_fixtures(path=FIXTURES_FILE):
    required = [
        "match_no",
        "date",
        "team1",
        "team2",
        "venue",
        "city",
        "status",
        "winner",
        "team1_score",
        "team2_score",
    ]
    df = pd.read_csv(path)
    _validate_snapshot_metadata(df, path)
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

    df = df[required].copy()
    df["team1"] = df["team1"].map(normalize_team_name)
    df["team2"] = df["team2"].map(normalize_team_name)
    df["winner"] = df["winner"].map(normalize_team_name)
    _validate_teams(pd.concat([df["team1"], df["team2"], df["winner"]]), path.name)

    if (df["team1"] == df["team2"]).any():
        bad = df.loc[df["team1"] == df["team2"], "match_no"].tolist()
        raise ValueError(f"Fixture has the same team twice for match_no: {bad}")

    df["match_no"] = pd.to_numeric(df["match_no"], errors="raise").astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    if df["date"].isna().any():
        bad = df.loc[df["date"].isna(), "match_no"].tolist()
        raise ValueError(f"Fixtures have invalid dates for match_no: {bad}")

    df["status"] = df["status"].str.strip().str.lower()

    valid_statuses = {"completed", "scheduled"}
    invalid_statuses = sorted(set(df["status"]) - valid_statuses)
    if invalid_statuses:
        raise ValueError(f"Invalid fixture statuses: {', '.join(invalid_statuses)}")

    completed_without_winner = df[(df["status"] == "completed") & (df["winner"] == "")]
    if not completed_without_winner.empty:
        raise ValueError("Completed fixtures must include a winner")

    completed = df[df["status"] == "completed"]
    bad_winners = completed[~completed.apply(lambda row: row["winner"] in {row["team1"], row["team2"]}, axis=1)]
    if not bad_winners.empty:
        raise ValueError("Completed fixture winners must be one of team1/team2")

    for col in ["team1_score", "team2_score"]:
        parsed = pd.to_numeric(completed[col], errors="coerce")
        if parsed.isna().any():
            raise ValueError("Completed fixtures must include numeric team scores")
        df.loc[completed.index, col] = parsed.astype(int)

    return df.sort_values("match_no").reset_index(drop=True)


def load_overrides(path=OVERRIDES_FILE):
    defaults = pd.DataFrame({"team": CURRENT_TEAMS})
    if not Path(path).exists():
        defaults["batting_index"] = 1.0
        defaults["bowling_index"] = 1.0
        defaults["form_index"] = 1.0
        defaults["notes"] = ""
        return defaults

    df = pd.read_csv(path)
    _validate_snapshot_metadata(df, path)
    required = ["team", "batting_index", "bowling_index", "form_index", "notes"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(missing)}")

    df = df[required].copy()
    df["team"] = df["team"].map(normalize_team_name)
    _validate_teams(df["team"], Path(path).name)

    merged = defaults.merge(df, on="team", how="left")
    for col in ["batting_index", "bowling_index", "form_index"]:
        merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(1.0).clip(0.75, 1.25)
    merged["notes"] = merged["notes"].fillna("")
    return merged
