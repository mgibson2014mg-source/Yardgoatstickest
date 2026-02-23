"""
scraper/schedule.py — Fetch Hartford Yard Goats home schedule
via the MLB Stats API (statsapi.mlb.com).

Hartford Yard Goats:
  teamId  : 538
  sportId : 12  (Double-A)

API endpoint:
  https://statsapi.mlb.com/api/v1/schedule?sportId=12&teamId=538
    &startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&gameType=R
"""

import logging
from datetime import date, timedelta
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────
TEAM_ID   = 538          # Hartford Yard Goats
SPORT_ID  = 12           # Double-A (MiLB)
BASE_URL  = "https://statsapi.mlb.com/api/v1"
TICKET_BASE = "https://www.milb.com/hartford/tickets"

DAYS = {0:"Monday",1:"Tuesday",2:"Wednesday",3:"Thursday",
        4:"Friday",5:"Saturday",6:"Sunday"}

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; YardGoatsTracker/1.0; "
        "+https://github.com/user/yardgoats-tracker)"
    )
}

# ── Public API ────────────────────────────────────────────

def fetch_schedule(
    season: int,
    start_date: Optional[date] = None,
    end_date:   Optional[date] = None,
    session:    Optional[requests.Session] = None,
) -> list[dict]:
    """
    Fetch Yard Goats home games from the MLB Stats API.

    Returns a list of game dicts ready for db.upsert_game():
        game_date, day_of_week, start_time, opponent,
        is_home, ticket_url
    """
    if start_date is None:
        start_date = date(season, 4, 1)
    if end_date is None:
        end_date = date(season, 9, 30)

    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)

    params = {
        "sportId":   SPORT_ID,
        "teamId":    TEAM_ID,
        "startDate": start_date.isoformat(),
        "endDate":   end_date.isoformat(),
        "gameType":  "R",       # Regular season
        "hydrate":   "team",
    }

    try:
        resp = sess.get(f"{BASE_URL}/schedule", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("MLB Stats API request failed: %s", exc)
        raise

    return _parse_api_response(data)


def _parse_api_response(data: dict) -> list[dict]:
    """Parse the /schedule API response into game dicts."""
    games = []
    for date_entry in data.get("dates", []):
        for game in date_entry.get("games", []):
            parsed = _parse_game(game)
            if parsed:
                games.append(parsed)
    return games


def _parse_game(game: dict) -> Optional[dict]:
    """
    Extract a single game into a flat dict.
    Returns None if the game is not a Yard Goats home game.
    """
    try:
        teams = game.get("teams", {})
        home_team = teams.get("home", {})
        home_team_info = home_team.get("team", {})
        home_id = home_team_info.get("id")
        
        away_team = teams.get("away", {})
        away_team_info = away_team.get("team", {})
        away_id = away_team_info.get("id")

        if home_id is None or away_id is None:
            # Try fallback if fixture format is slightly different
            home_id = home_team.get("id")
            away_id = away_team.get("id")

        # Only process home games
        is_home = (home_id == TEAM_ID)
        if not is_home:
            return None  # away game — skip

        opponent_team = away_team_info.get("name") or away_team.get("name")

        # game_datetime is UTC ISO string e.g. "2026-04-10T23:05:00Z"
        game_dt_str = game.get("gameDate", "")
        game_date_str, start_time = _parse_datetime(game_dt_str)

        if not game_date_str:
            logger.warning("Could not parse game date: %s", game_dt_str)
            return None

        game_date = date.fromisoformat(game_date_str)
        dow = DAYS[game_date.weekday()]

        return {
            "game_date":   game_date_str,
            "day_of_week": dow,
            "start_time":  start_time,
            "opponent":    opponent_team,
            "is_home":     1,
            "ticket_url":  TICKET_BASE,
        }
    except (KeyError, ValueError, TypeError) as exc:
        logger.warning("Skipping malformed game entry: %s — %s", game.get("gamePk"), exc)
        return None


def _parse_datetime(dt_str: str) -> tuple[str, str]:
    """
    Parse ISO UTC datetime string into (YYYY-MM-DD, "H:MM PM") ET.
    MiLB games are typically 7:05 PM ET → stored as-is from the API.

    The API returns UTC. Eastern Time is UTC-4 (EDT, Apr-Sep).
    """
    if not dt_str:
        return "", ""
    try:
        # "2026-04-10T23:05:00Z"
        date_part, time_part = dt_str.rstrip("Z").split("T")
        # Convert UTC to ET (EDT = UTC-4 during baseball season)
        hour_utc, minute, *_ = [int(x) for x in time_part.split(":")]
        hour_et = (hour_utc - 4) % 24
        period  = "PM" if hour_et >= 12 else "AM"
        hour_12 = hour_et % 12 or 12
        time_et = f"{hour_12}:{minute:02d} {period}"
        return date_part, time_et
    except (ValueError, AttributeError):
        return dt_str[:10] if len(dt_str) >= 10 else "", ""
