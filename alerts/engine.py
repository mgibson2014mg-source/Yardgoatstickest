"""
alerts/engine.py — Core alert engine logic.

Responsibilities:
  - Identify games that need alerts (5 days out, Fri/Sat/Sun, home)
  - Check data freshness (staleness guard per architecture NFR)
  - Build alert payloads (self-contained per FR-15)
  - Deduplicate via alerts_sent table (FR-13)
  - Coordinate SMS + email delivery
  - Log delivery status
"""

import logging
from datetime import date, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

ALERT_DAYS_AHEAD = 5
WEEKEND_DAYS = {"Friday", "Saturday", "Sunday"}
MAX_STALENESS_HOURS = 48


def get_qualifying_games(conn, target_date: date) -> list:
    """
    Return home games on target_date that are Fri/Sat/Sun.
    These are the games that should trigger alerts today
    (sent ALERT_DAYS_AHEAD before the game).
    """
    date_str = target_date.isoformat()
    rows = conn.execute(
        """SELECT g.*, GROUP_CONCAT(p.promo_type || ':' || COALESCE(p.description,''), '||') as promos_raw
           FROM games g
           LEFT JOIN promotions p ON p.game_id = g.id
           WHERE g.game_date = ? AND g.is_home = 1
           AND g.day_of_week IN ('Friday','Saturday','Sunday')
           GROUP BY g.id""",
        (date_str,)
    ).fetchall()
    return rows


def build_alert_payload(game_row) -> dict:
    """
    Build a self-contained alert payload from a game row.
    Per FR-14 and FR-15: complete context, no click-through required.
    """
    promos = _parse_promos(game_row["promos_raw"])

    if promos:
        promo_summary = _format_promo_summary(promos)
    else:
        promo_summary = "Promotions TBD — check dashboard for updates"

    game_date = game_row["game_date"]
    day       = game_row["day_of_week"]
    time_str  = game_row["start_time"] or "TBD"
    opponent  = game_row["opponent"]
    ticket_url = game_row["ticket_url"] or "https://www.milb.com/hartford/tickets"

    # Format date nicely e.g. "Fri Apr 10"
    from datetime import datetime
    try:
        dt = datetime.strptime(game_date, "%Y-%m-%d")
        # Windows uses %#d for no leading zero, Unix uses %-d
        import os
        fmt = "%a %b %#d" if os.name == 'nt' else "%a %b %-d"
        display_date = dt.strftime(fmt)
    except ValueError:
        display_date = game_date

    return {
        "game_id":     game_row["id"],
        "game_date":   game_date,
        "display_date": display_date,
        "day":         day,
        "time":        time_str,
        "opponent":    opponent,
        "ticket_url":  ticket_url,
        "promo_summary": promo_summary,
        "promos":      promos,
        "has_promos":  bool(promos),
    }


def check_data_freshness(conn) -> bool:
    """
    Return True if schedule data is fresh (updated within MAX_STALENESS_HOURS).
    Returns False if stale or absent — alert engine should skip sending.
    Per architecture section 8.2.
    """
    from datetime import datetime
    row = conn.execute("SELECT MAX(updated_at) as last_update FROM games").fetchone()
    if not row or not row["last_update"]:
        logger.warning("No game data found in database")
        return False

    last_update_str = row["last_update"]
    try:
        # SQLite CURRENT_TIMESTAMP format: "2026-04-10 23:05:00"
        last_update = datetime.strptime(last_update_str[:19], "%Y-%m-%d %H:%M:%S")
        age_hours = (datetime.utcnow() - last_update).total_seconds() / 3600
        if age_hours > MAX_STALENESS_HOURS:
            logger.warning(
                "Schedule data is stale (%.1f hours old, limit %d h) — skipping alerts",
                age_hours, MAX_STALENESS_HOURS
            )
            return False
        return True
    except ValueError:
        logger.warning("Could not parse last_update timestamp: %s", last_update_str)
        return False


def format_sms_message(payload: dict) -> str:
    """
    Format a self-contained SMS alert ≤ 320 chars per NFR-05.
    Pattern per architecture section 3.2.
    """
    msg = (
        f"🎯 Yard Goats {payload['day']} {payload['display_date']} @ {payload['time']}\n"
        f"vs {payload['opponent']}\n"
        f"{payload['promo_summary']}\n"
        f"Tickets: {payload['ticket_url']}\n"
        f"Reply STOP to unsubscribe"
    )
    if len(msg) > 320:
        # Truncate promo summary to fit
        budget = 320 - len(msg) + len(payload['promo_summary'])
        truncated = payload['promo_summary'][:budget - 3] + "..."
        msg = (
            f"🎯 Yard Goats {payload['day']} {payload['display_date']} @ {payload['time']}\n"
            f"vs {payload['opponent']}\n"
            f"{truncated}\n"
            f"Tickets: {payload['ticket_url']}\n"
            f"Reply STOP to unsubscribe"
        )
    return msg


def format_email_subject(payload: dict) -> str:
    """
    Format email subject per FR-24 pattern:
    '🎯 Yard Goats [Day] — [Date] vs [Opponent] | [Top Promo or Upcoming Game]'
    """
    if payload["has_promos"] and payload["promos"]:
        top_promo = payload["promos"][0]["description"]
        if len(top_promo) > 40:
            top_promo = top_promo[:37] + "..."
        label = top_promo
    else:
        label = "Upcoming Game"

    return (
        f"🎯 Yard Goats {payload['day']} — {payload['display_date']} "
        f"vs {payload['opponent']} | {label}"
    )


# ── Internal helpers ──────────────────────────────────────

def _parse_promos(promos_raw: Optional[str]) -> list[dict]:
    """Parse GROUP_CONCAT promo string back into list of dicts."""
    if not promos_raw:
        return []
    promos = []
    for item in promos_raw.split("||"):
        if ":" not in item:
            continue
        promo_type, _, description = item.partition(":")
        if promo_type.strip():
            promos.append({
                "promo_type":  promo_type.strip(),
                "description": description.strip(),
            })
    return promos


def _format_promo_summary(promos: list[dict]) -> str:
    """
    Format promos into a concise, human-readable summary.
    e.g. "🎁 Cowboy Hat Giveaway | 🎆 Post-Game Fireworks"
    """
    ICONS = {
        "giveaway":  "🎁",
        "fireworks": "🎆",
        "discount":  "💰",
        "theme":     "🎭",
        "heritage":  "⚾",
        "special":   "⭐",
    }
    parts = []
    for p in promos:
        icon = ICONS.get(p["promo_type"], "⭐")
        desc = p["description"]
        if len(desc) > 35:
            desc = desc[:32] + "..."
        parts.append(f"{icon} {desc}")
    return " | ".join(parts)
