import pandas as pd

from src.live_cricket_api import normalize_cric_score, normalize_current_matches
from src.live_ingest import apply_live_matches


def test_normalize_current_matches_extracts_completed_ipl_result():
    payload = {
        "data": [
            {
                "id": "abc",
                "name": "Indian Premier League",
                "dateTimeGMT": "2026-05-17T14:00:00Z",
                "teams": ["Punjab Kings", "Royal Challengers Bangalore"],
                "venue": "HPCA Stadium",
                "matchEnded": True,
                "matchWinner": "Royal Challengers Bangalore",
                "status": "Royal Challengers Bangalore won by 6 wickets",
                "score": [
                    {"inning": "Punjab Kings Inning 1", "r": 172},
                    {"inning": "Royal Challengers Bangalore Inning 1", "r": 176},
                ],
            }
        ]
    }
    matches = normalize_current_matches(payload)
    assert len(matches) == 1
    assert matches[0].winner == "Royal Challengers Bengaluru"
    assert matches[0].team1_score == 172
    assert matches[0].team2_score == 176


def test_normalize_cric_score_extracts_status_winner():
    payload = {
        "data": [
            {
                "id": "abc",
                "series": "IPL 2026",
                "dateTimeGMT": "2026-05-17T14:00:00Z",
                "t1": "Punjab Kings",
                "t2": "RCB",
                "t1s": "172/7 (20)",
                "t2s": "176/4 (19.2)",
                "ms": "result",
                "status": "Royal Challengers Bengaluru won by 6 wickets",
            }
        ]
    }
    matches = normalize_cric_score(payload)
    assert len(matches) == 1
    assert matches[0].winner == "Royal Challengers Bengaluru"
    assert matches[0].team2_score == 176


def test_apply_live_matches_updates_fixture_and_state_once():
    state = pd.DataFrame(
        [
            {
                "data_snapshot_id": "test",
                "source": "unit",
                "last_updated_utc": "2026-05-16T00:00:00+00:00",
                "team": "Punjab Kings",
                "matches": 12,
                "wins": 8,
                "losses": 3,
                "no_results": 1,
                "points": 17,
                "nrr": 0.57,
            },
            {
                "data_snapshot_id": "test",
                "source": "unit",
                "last_updated_utc": "2026-05-16T00:00:00+00:00",
                "team": "Royal Challengers Bengaluru",
                "matches": 12,
                "wins": 9,
                "losses": 3,
                "no_results": 0,
                "points": 18,
                "nrr": 0.74,
            },
        ]
    )
    fixtures = pd.DataFrame(
        [
            {
                "data_snapshot_id": "test",
                "source": "unit",
                "last_updated_utc": "2026-05-16T00:00:00+00:00",
                "match_no": 61,
                "date": "2026-05-17",
                "team1": "Punjab Kings",
                "team2": "Royal Challengers Bengaluru",
                "venue": "HPCA Stadium",
                "city": "Dharamsala",
                "status": "scheduled",
                "winner": "",
                "team1_score": "",
                "team2_score": "",
            }
        ]
    )
    live_match = normalize_cric_score(
        {
            "data": [
                {
                    "id": "abc",
                    "series": "IPL 2026",
                    "dateTimeGMT": "2026-05-17T14:00:00Z",
                    "t1": "Punjab Kings",
                    "t2": "RCB",
                    "t1s": "172/7 (20)",
                    "t2s": "176/4 (19.2)",
                    "ms": "result",
                    "status": "Royal Challengers Bengaluru won by 6 wickets",
                }
            ]
        }
    )[0]

    updated_state, updated_fixtures, updates = apply_live_matches(state, fixtures, [live_match], "after-61")
    rcb = updated_state[updated_state["team"] == "Royal Challengers Bengaluru"].iloc[0]
    pbks = updated_state[updated_state["team"] == "Punjab Kings"].iloc[0]
    assert updated_fixtures.iloc[0]["status"] == "completed"
    assert updated_fixtures.iloc[0]["winner"] == "Royal Challengers Bengaluru"
    assert rcb["points"] == 20
    assert rcb["matches"] == 13
    assert pbks["losses"] == 4
    assert len(updates) == 1
