"""Explainable IPL team ratings used by the Monte Carlo simulator."""

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from src.config import CURRENT_TEAMS, HOME_CITIES, is_current_team, normalize_team_name


BASE_ELO = 1500.0


@dataclass(frozen=True)
class TeamRating:
    team: str
    elo: float
    batting_index: float
    bowling_index: float
    form_index: float
    nrr: float


def _season_end_year(season):
    text = str(season)
    parts = text.replace("/", "-").split("-")
    year = parts[-1]
    if len(year) == 2:
        return int("20" + year)
    return int(year)


def _recency_weight(season):
    year = _season_end_year(season)
    if year >= 2024:
        return 1.0
    if year >= 2022:
        return 0.8
    if year >= 2020:
        return 0.55
    if year >= 2017:
        return 0.35
    return 0.2


def _expected_score(elo_a, elo_b):
    return 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400.0))


def _apply_elo(ratings, team_a, team_b, winner, k_factor):
    expected_a = _expected_score(ratings[team_a], ratings[team_b])
    score_a = 1.0 if winner == team_a else 0.0
    change = k_factor * (score_a - expected_a)
    ratings[team_a] += change
    ratings[team_b] -= change


def build_historical_elo(matches_path):
    ratings = {team: BASE_ELO for team in CURRENT_TEAMS}
    path = Path(matches_path)
    if not path.exists():
        return ratings

    matches = pd.read_csv(path, low_memory=False)
    if "date" in matches.columns:
        matches["date"] = pd.to_datetime(matches["date"], errors="coerce")
        matches = matches.sort_values("date")

    for _, row in matches.iterrows():
        team1 = normalize_team_name(row.get("team1"))
        team2 = normalize_team_name(row.get("team2"))
        winner = normalize_team_name(row.get("winner"))
        result = str(row.get("result", "")).lower()

        if result == "no result" or not all(map(is_current_team, [team1, team2, winner])):
            continue

        k = 22.0 * _recency_weight(row.get("season", 2008))
        _apply_elo(ratings, team1, team2, winner, k)

    return ratings


def apply_completed_2026_matches(ratings, fixtures):
    updated = dict(ratings)
    completed = fixtures[fixtures["status"] == "completed"]
    for _, row in completed.iterrows():
        winner = row["winner"]
        if not winner:
            continue
        _apply_elo(updated, row["team1"], row["team2"], winner, 34.0)
    return updated


def build_team_ratings(state, fixtures, overrides, historical_matches_path):
    elo = build_historical_elo(historical_matches_path)
    elo = apply_completed_2026_matches(elo, fixtures)

    state_by_team = state.set_index("team")
    overrides_by_team = overrides.set_index("team")
    ratings = {}
    for team in CURRENT_TEAMS:
        nrr = float(state_by_team.loc[team, "nrr"])
        override = overrides_by_team.loc[team]
        ratings[team] = TeamRating(
            team=team,
            elo=elo.get(team, BASE_ELO),
            batting_index=float(override["batting_index"]),
            bowling_index=float(override["bowling_index"]),
            form_index=float(override["form_index"]),
            nrr=nrr,
        )
    return ratings


def match_win_probability(team1, team2, ratings, city="", venue="", toss_winner="", toss_decision=""):
    r1 = ratings[team1]
    r2 = ratings[team2]

    diff = r1.elo - r2.elo
    diff += (r1.batting_index - r2.bowling_index) * 85.0
    diff -= (r2.batting_index - r1.bowling_index) * 85.0
    diff += (r1.form_index - r2.form_index) * 70.0
    diff += (r1.nrr - r2.nrr) * 18.0

    city_value = str(city)
    venue_value = str(venue)
    for home_city in HOME_CITIES.get(team1, set()):
        if home_city in city_value or home_city in venue_value:
            diff += 28.0
    for home_city in HOME_CITIES.get(team2, set()):
        if home_city in city_value or home_city in venue_value:
            diff -= 28.0

    if toss_winner:
        toss_bonus = 10.0 if str(toss_decision).lower() == "field" else 4.0
        if toss_winner == team1:
            diff += toss_bonus
        elif toss_winner == team2:
            diff -= toss_bonus

    probability = 1.0 / (1.0 + 10 ** (-diff / 400.0))
    return float(np.clip(probability, 0.12, 0.88))
