"""Fetch and parse the public Cricbuzz IPL 2026 points table."""

from datetime import datetime, timezone
from html import unescape
import re
from urllib.request import Request, urlopen

import pandas as pd

from src.config import normalize_team_name


CRICBUZZ_POINTS_URL = "https://www.cricbuzz.com/cricket-series/9241/indian-premier-league-2026/points-table"


def fetch_points_html(url=CRICBUZZ_POINTS_URL):
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        return response.read().decode("utf-8", "ignore")


def parse_points_table(html, snapshot_id=None, source=CRICBUZZ_POINTS_URL):
    cleaned = unescape(html)
    pattern = re.compile(
        r'<div class="text-xs">(?P<team>[^<]+)(?:<!-- -->\s*)*(?:\(E\))?\s*</div></a></div>'
        r'<div class="flex justify-center items-center">(?P<matches>\d+)</div>'
        r'<div class="flex justify-center items-center">(?P<wins>\d+)</div>'
        r'<div class="flex justify-center items-center">(?P<losses>\d+)</div>'
        r'<div class="flex justify-center items-center">(?P<no_results>\d+)</div>'
        r'<div class="flex justify-center items-center">(?P<points>\d+)</div>'
        r'<div class="flex justify-center items-center">(?P<nrr>[+-]?\d+\.\d+)</div>',
        re.DOTALL,
    )
    now = datetime.now(timezone.utc).isoformat()
    snapshot_id = snapshot_id or f"cricbuzz-ipl-2026-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"
    rows = []
    for match in pattern.finditer(cleaned):
        rows.append(
            {
                "data_snapshot_id": snapshot_id,
                "source": source,
                "last_updated_utc": now,
                "team": normalize_team_name(match.group("team")),
                "matches": int(match.group("matches")),
                "wins": int(match.group("wins")),
                "losses": int(match.group("losses")),
                "no_results": int(match.group("no_results")),
                "points": int(match.group("points")),
                "nrr": float(match.group("nrr")),
            }
        )
    if len(rows) != 10:
        raise ValueError(f"Expected 10 IPL teams from Cricbuzz points table, found {len(rows)}")
    return pd.DataFrame(rows)


def fetch_points_table(url=CRICBUZZ_POINTS_URL):
    return parse_points_table(fetch_points_html(url), source=url)


if __name__ == "__main__":
    print(fetch_points_table().to_string(index=False))
