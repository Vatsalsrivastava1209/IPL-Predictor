from pathlib import Path

import pytest

from src.config import normalize_team_name
from src.data_loader import load_fixtures, load_state

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_team_normalization_keeps_only_intended_aliases():
    assert normalize_team_name("Royal Challengers Bangalore") == "Royal Challengers Bengaluru"
    assert normalize_team_name("Kings XI Punjab") == "Punjab Kings"
    assert normalize_team_name("Gujarat Lions") == "Gujarat Lions"


def test_fixture_loader_rejects_unknown_teams():
    path = FIXTURES_DIR / "bad_unknown_team_fixtures.csv"
    with pytest.raises(ValueError, match="Unknown team"):
        load_fixtures(path)


def test_fixture_loader_rejects_invalid_dates():
    path = FIXTURES_DIR / "bad_date_fixtures.csv"
    with pytest.raises(ValueError, match="invalid dates"):
        load_fixtures(path)


def test_completed_fixture_winner_must_be_one_of_match_teams():
    path = FIXTURES_DIR / "bad_completed_winner_fixtures.csv"
    with pytest.raises(ValueError, match="winners must be one of team1/team2"):
        load_fixtures(path)


def test_state_loader_validates_points_arithmetic():
    path = FIXTURES_DIR / "bad_points_state.csv"
    with pytest.raises(ValueError, match="points != wins"):
        load_state(path)
