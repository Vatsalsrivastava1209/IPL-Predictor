"""Shared constants for the IPL 2026 simulator."""

CURRENT_TEAMS = [
    "Chennai Super Kings",
    "Delhi Capitals",
    "Gujarat Titans",
    "Kolkata Knight Riders",
    "Lucknow Super Giants",
    "Mumbai Indians",
    "Punjab Kings",
    "Rajasthan Royals",
    "Royal Challengers Bengaluru",
    "Sunrisers Hyderabad",
]

TEAM_ALIASES = {
    "Delhi Daredevils": "Delhi Capitals",
    "Kings XI Punjab": "Punjab Kings",
    "Royal Challengers Bangalore": "Royal Challengers Bengaluru",
    "RCB": "Royal Challengers Bengaluru",
    "CSK": "Chennai Super Kings",
    "DC": "Delhi Capitals",
    "GT": "Gujarat Titans",
    "KKR": "Kolkata Knight Riders",
    "LSG": "Lucknow Super Giants",
    "MI": "Mumbai Indians",
    "PBKS": "Punjab Kings",
    "RR": "Rajasthan Royals",
    "SRH": "Sunrisers Hyderabad",
}

RETIRED_TEAMS = {
    "Deccan Chargers",
    "Gujarat Lions",
    "Kochi Tuskers Kerala",
    "Pune Warriors",
    "Rising Pune Supergiant",
    "Rising Pune Supergiants",
}

HOME_CITIES = {
    "Chennai Super Kings": {"Chennai"},
    "Delhi Capitals": {"Delhi"},
    "Gujarat Titans": {"Ahmedabad"},
    "Kolkata Knight Riders": {"Kolkata"},
    "Lucknow Super Giants": {"Lucknow"},
    "Mumbai Indians": {"Mumbai"},
    "Punjab Kings": {"Chandigarh", "Mohali", "Dharamsala", "Mullanpur"},
    "Rajasthan Royals": {"Jaipur", "Guwahati"},
    "Royal Challengers Bengaluru": {"Bengaluru", "Bangalore"},
    "Sunrisers Hyderabad": {"Hyderabad"},
}


def normalize_team_name(team):
    """Return a canonical current IPL team name, preserving blanks for optional fields."""
    if team is None:
        return ""
    value = str(team).strip()
    if not value or value.lower() == "nan":
        return ""
    return TEAM_ALIASES.get(value, value)


def is_current_team(team):
    return normalize_team_name(team) in CURRENT_TEAMS
