"""Small CricAPI/CricketData client and IPL match normalizer."""

from dataclasses import dataclass
from datetime import datetime, timezone
from os import environ
from urllib.parse import urlencode
from urllib.request import urlopen
import json
import re

from src.config import CURRENT_TEAMS, normalize_team_name


API_BASE_URL = "https://api.cricapi.com/v1"


@dataclass(frozen=True)
class LiveMatch:
    api_match_id: str
    date: datetime | None
    team1: str
    team2: str
    status: str
    winner: str
    team1_score: int | None
    team2_score: int | None
    venue: str
    source_status: str


class CricApiClient:
    def __init__(self, api_key=None, base_url=API_BASE_URL):
        self.api_key = api_key or environ.get("CRICAPI_KEY")
        self.base_url = base_url.rstrip("/")
        if not self.api_key:
            raise ValueError("CRICAPI_KEY is not set")

    def _get(self, endpoint, **params):
        query = urlencode({"apikey": self.api_key, **params})
        url = f"{self.base_url}/{endpoint.lstrip('/')}?{query}"
        with urlopen(url, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("status") == "failure":
            reason = payload.get("reason") or payload.get("message") or "unknown API failure"
            raise RuntimeError(f"CricAPI request failed: {reason}")
        return payload

    def current_matches(self, offset=0):
        return self._get("currentMatches", offset=offset)

    def cric_score(self):
        return self._get("cricScore")


def _parse_date(value):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_score(value):
    if value is None:
        return None
    match = re.search(r"(\d+)", str(value))
    return int(match.group(1)) if match else None


def _score_from_current_match(item, team):
    scores = item.get("score") or []
    for score in scores:
        inning = str(score.get("inning", ""))
        if team in inning or any(alias in inning for alias, canonical in _team_alias_items() if canonical == team):
            runs = score.get("r")
            return int(runs) if runs is not None else None
    return None


def _team_alias_items():
    from src.config import TEAM_ALIASES

    return TEAM_ALIASES.items()


def _normalize_pair(raw_team1, raw_team2):
    team1 = normalize_team_name(raw_team1)
    team2 = normalize_team_name(raw_team2)
    if team1 not in CURRENT_TEAMS or team2 not in CURRENT_TEAMS or team1 == team2:
        return "", ""
    return team1, team2


def _winner_from_status(status_text, team1, team2):
    text = str(status_text or "").lower()
    for team in [team1, team2]:
        if team.lower() in text and "won" in text:
            return team
    return ""


def _is_ipl_item(item):
    haystack = " ".join(
        str(item.get(key, ""))
        for key in ["name", "series", "status", "venue", "matchType"]
    ).lower()
    return "ipl" in haystack or "indian premier league" in haystack


def normalize_current_matches(payload):
    matches = []
    for item in payload.get("data", []) or []:
        if not _is_ipl_item(item):
            continue
        teams = item.get("teams") or []
        if len(teams) < 2:
            continue
        team1, team2 = _normalize_pair(teams[0], teams[1])
        if not team1:
            continue
        winner = normalize_team_name(item.get("matchWinner")) or _winner_from_status(item.get("status"), team1, team2)
        ended = bool(item.get("matchEnded")) or bool(winner)
        matches.append(
            LiveMatch(
                api_match_id=str(item.get("id", "")),
                date=_parse_date(item.get("dateTimeGMT") or item.get("date")),
                team1=team1,
                team2=team2,
                status="completed" if ended else "scheduled",
                winner=winner if ended else "",
                team1_score=_score_from_current_match(item, team1),
                team2_score=_score_from_current_match(item, team2),
                venue=str(item.get("venue", "")),
                source_status=str(item.get("status", "")),
            )
        )
    return matches


def normalize_cric_score(payload):
    matches = []
    for item in payload.get("data", []) or []:
        if not _is_ipl_item(item):
            continue
        team1, team2 = _normalize_pair(item.get("t1"), item.get("t2"))
        if not team1:
            continue
        source_status = str(item.get("status") or item.get("ms") or "")
        winner = _winner_from_status(source_status, team1, team2)
        ended = str(item.get("ms", "")).lower() == "result" or bool(winner)
        matches.append(
            LiveMatch(
                api_match_id=str(item.get("id", "")),
                date=_parse_date(item.get("dateTimeGMT") or item.get("date")),
                team1=team1,
                team2=team2,
                status="completed" if ended else "scheduled",
                winner=winner if ended else "",
                team1_score=_parse_score(item.get("t1s")),
                team2_score=_parse_score(item.get("t2s")),
                venue=str(item.get("venue", "")),
                source_status=source_status,
            )
        )
    return matches


def fetch_ipl_live_matches(client=None):
    client = client or CricApiClient()
    matches = []
    try:
        matches.extend(normalize_current_matches(client.current_matches()))
    except Exception:
        # cricScore is the fallback because it covers recent/live/upcoming matches.
        pass
    matches.extend(normalize_cric_score(client.cric_score()))

    deduped = {}
    for match in matches:
        key = tuple(sorted([match.team1, match.team2])) + (match.date.date().isoformat() if match.date else "",)
        if key not in deduped or (match.status == "completed" and deduped[key].status != "completed"):
            deduped[key] = match
    return list(deduped.values())
