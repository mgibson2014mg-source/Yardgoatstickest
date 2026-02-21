"""
db.py — SQLite connection and shared helpers.
Used by scraper, alerts engine, and admin CLI.
"""
import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager
from typing import Optional

# Default DB path — can be overridden via env var (useful in tests)
DEFAULT_DB_PATH = Path(__file__).parent.parent / "data" / "yardgoats.db"


def get_db_path() -> Path:
    return Path(os.environ.get("YARDGOATS_DB", str(DEFAULT_DB_PATH)))


def init_db(db_path: Optional[Path] = None) -> None:
    """Create all tables from schema.sql if they don't exist."""
    db_path = db_path or get_db_path()
    schema_path = Path(__file__).parent.parent / "data" / "schema.sql"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text())
        conn.commit()


@contextmanager
def get_conn(db_path: Optional[Path] = None):
    """Context manager yielding a sqlite3 connection with row_factory set."""
    db_path = db_path or get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Game helpers ─────────────────────────────────────────

def upsert_game(conn: sqlite3.Connection, game: dict) -> int:
    """
    Insert or update a game record keyed on game_date.
    Returns the game id.
    """
    conn.execute("""
        INSERT INTO games (game_date, day_of_week, start_time, opponent, is_home, ticket_url, updated_at)
        VALUES (:game_date, :day_of_week, :start_time, :opponent, :is_home, :ticket_url, CURRENT_TIMESTAMP)
        ON CONFLICT(game_date) DO UPDATE SET
            day_of_week = excluded.day_of_week,
            start_time  = excluded.start_time,
            opponent    = excluded.opponent,
            is_home     = excluded.is_home,
            ticket_url  = excluded.ticket_url,
            updated_at  = CURRENT_TIMESTAMP
    """, game)
    row = conn.execute("SELECT id FROM games WHERE game_date = ?", (game["game_date"],)).fetchone()
    return row["id"]


def get_games_on_date(conn: sqlite3.Connection, date_str: str) -> list:
    """Return all home games for a given YYYY-MM-DD date string."""
    return conn.execute(
        "SELECT * FROM games WHERE game_date = ? AND is_home = 1", (date_str,)
    ).fetchall()


def get_weekend_games_on_date(conn: sqlite3.Connection, date_str: str) -> list:
    """Return Fri/Sat/Sun home games for a given date."""
    return conn.execute(
        """SELECT * FROM games
           WHERE game_date = ? AND is_home = 1
           AND day_of_week IN ('Friday','Saturday','Sunday')""",
        (date_str,)
    ).fetchall()


def get_data_freshness(conn: sqlite3.Connection) -> Optional[str]:
    """Return the most recent updated_at timestamp across all games, or None."""
    row = conn.execute("SELECT MAX(updated_at) as last_update FROM games").fetchone()
    return row["last_update"] if row else None


# ── Promotion helpers ────────────────────────────────────

def upsert_promotions(conn: sqlite3.Connection, game_id: int, promos: list[dict]) -> None:
    """
    Replace all promotions for a game_id with the provided list.
    Each promo dict must have: promo_type, description.
    """
    conn.execute("DELETE FROM promotions WHERE game_id = ?", (game_id,))
    for promo in promos:
        conn.execute("""
            INSERT INTO promotions (game_id, promo_type, description)
            VALUES (?, ?, ?)
        """, (game_id, promo["promo_type"], promo.get("description", "")))


def get_promotions_for_game(conn: sqlite3.Connection, game_id: int) -> list:
    return conn.execute(
        "SELECT * FROM promotions WHERE game_id = ?", (game_id,)
    ).fetchall()


# ── Recipient helpers ────────────────────────────────────

def add_recipient(conn: sqlite3.Connection, name: str, phone: Optional[str], email: Optional[str]) -> int:
    if not phone and not email:
        raise ValueError("Recipient must have at least one of phone or email.")
    cursor = conn.execute(
        "INSERT INTO recipients (name, phone, email) VALUES (?, ?, ?)",
        (name, phone, email)
    )
    return cursor.lastrowid


def list_recipients(conn: sqlite3.Connection, active_only: bool = True) -> list:
    if active_only:
        return conn.execute("SELECT * FROM recipients WHERE active = 1").fetchall()
    return conn.execute("SELECT * FROM recipients").fetchall()


def deactivate_recipient(conn: sqlite3.Connection, recipient_id: int) -> bool:
    cursor = conn.execute(
        "UPDATE recipients SET active = 0 WHERE id = ?", (recipient_id,)
    )
    return cursor.rowcount > 0


def reactivate_recipient(conn: sqlite3.Connection, recipient_id: int) -> bool:
    cursor = conn.execute(
        "UPDATE recipients SET active = 1 WHERE id = ?", (recipient_id,)
    )
    return cursor.rowcount > 0


# ── Alert deduplication helpers ──────────────────────────

def has_alert_been_sent(conn: sqlite3.Connection, game_id: int, recipient_id: int, channel: str) -> bool:
    row = conn.execute(
        "SELECT id FROM alerts_sent WHERE game_id=? AND recipient_id=? AND channel=?",
        (game_id, recipient_id, channel)
    ).fetchone()
    return row is not None


def log_alert(conn: sqlite3.Connection, game_id: int, recipient_id: int, channel: str, status: str) -> int:
    cursor = conn.execute(
        """INSERT OR REPLACE INTO alerts_sent (game_id, recipient_id, channel, status, sent_at)
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (game_id, recipient_id, channel, status)
    )
    return cursor.lastrowid


def get_alert_log(conn: sqlite3.Connection, game_id: Optional[int] = None) -> list:
    if game_id:
        return conn.execute(
            "SELECT * FROM alerts_sent WHERE game_id = ? ORDER BY sent_at DESC", (game_id,)
        ).fetchall()
    return conn.execute("SELECT * FROM alerts_sent ORDER BY sent_at DESC").fetchall()
