import pandas as pd

from src.config import CURRENT_TEAMS
from src.rating_engine import TeamRating, match_win_probability
from src.simulator import run_monte_carlo, sort_table


def _state():
    rows = []
    for idx, team in enumerate(CURRENT_TEAMS):
        rows.append(
            {
                "team": team,
                "matches": 0,
                "wins": 0,
                "losses": 0,
                "no_results": 0,
                "points": 20 - idx,
                "nrr": 1.0 - idx / 10,
            }
        )
    return pd.DataFrame(rows)


def _overrides():
    return pd.DataFrame(
        {
            "team": CURRENT_TEAMS,
            "batting_index": [1.0] * len(CURRENT_TEAMS),
            "bowling_index": [1.0] * len(CURRENT_TEAMS),
            "form_index": [1.0] * len(CURRENT_TEAMS),
            "notes": [""] * len(CURRENT_TEAMS),
        }
    )


def test_tied_points_sort_by_nrr():
    table = {
        "A": {"points": 10, "nrr": 0.2, "wins": 5},
        "B": {"points": 10, "nrr": 0.8, "wins": 4},
    }
    assert sort_table(table)[0][0] == "B"


def test_stronger_elo_team_has_higher_probability():
    ratings = {
        "Mumbai Indians": TeamRating("Mumbai Indians", 1600, 1.0, 1.0, 1.0, 0.0),
        "Chennai Super Kings": TeamRating("Chennai Super Kings", 1450, 1.0, 1.0, 1.0, 0.0),
    }
    assert match_win_probability("Mumbai Indians", "Chennai Super Kings", ratings) > 0.5


def test_neutral_swap_is_symmetric_with_equal_inputs():
    ratings = {
        "Mumbai Indians": TeamRating("Mumbai Indians", 1500, 1.0, 1.0, 1.0, 0.0),
        "Chennai Super Kings": TeamRating("Chennai Super Kings", 1500, 1.0, 1.0, 1.0, 0.0),
    }
    p1 = match_win_probability("Mumbai Indians", "Chennai Super Kings", ratings)
    p2 = match_win_probability("Chennai Super Kings", "Mumbai Indians", ratings)
    assert abs((p1 + p2) - 1.0) < 0.001


def test_locked_what_if_changes_selected_team_odds():
    fixtures = pd.DataFrame(
        [
            {
                "match_no": 1,
                "date": pd.Timestamp("2026-05-20"),
                "team1": CURRENT_TEAMS[8],
                "team2": CURRENT_TEAMS[9],
                "venue": "Neutral",
                "city": "Neutral",
                "status": "scheduled",
                "winner": "",
                "team1_score": "",
                "team2_score": "",
            }
        ]
    )
    missing_history = "tests/fixtures/missing_history.csv"
    base = run_monte_carlo(300, state=_state(), fixtures=fixtures, overrides=_overrides(), historical_matches_path=missing_history, seed=7)
    locked = run_monte_carlo(
        300,
        state=_state(),
        fixtures=fixtures,
        overrides=_overrides(),
        historical_matches_path=missing_history,
        locked_match_no=1,
        locked_winner=CURRENT_TEAMS[8],
        seed=7,
    )
    base_value = base.probabilities.loc[base.probabilities["team"] == CURRENT_TEAMS[8], "top4_pct"].iloc[0]
    locked_value = locked.probabilities.loc[locked.probabilities["team"] == CURRENT_TEAMS[8], "top4_pct"].iloc[0]
    assert locked_value >= base_value


def test_probabilities_are_valid():
    fixtures = pd.DataFrame(columns=["match_no", "date", "team1", "team2", "venue", "city", "status", "winner", "team1_score", "team2_score"])
    result = run_monte_carlo(500, state=_state(), fixtures=fixtures, overrides=_overrides(), historical_matches_path="tests/fixtures/missing_history.csv")
    assert len(result.probabilities) == len(CURRENT_TEAMS)
    assert abs(result.probabilities["champion_pct"].sum() - 100) < 0.001
