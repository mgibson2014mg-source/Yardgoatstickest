"""
scraper/main.py — Main entry point for the daily scrape job.
Called by GitHub Actions daily-scrape.yml.

Flow:
  1. Fetch schedule from MLB Stats API → upsert games table
  2. Scrape promotions page → upsert promotions table
  3. Log summary
  4. Exit 0 on success, 1 on failure (GitHub Actions interprets exit code)
"""

import logging
import sys
from datetime import date
from pathlib import Path

# Ensure project root is on path when run directly
sys.path.insert(0, str(Path(__file__).parent.parent))

from admin.db import init_db, get_conn, upsert_game, upsert_promotions, get_games_on_date
from scraper.schedule import fetch_schedule
from scraper.promotions import fetch_promotions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("scraper.main")


def run(season: int = None, dry_run: bool = False) -> bool:
    """
    Execute the full scrape pipeline.

    Args:
        season:  Year to scrape. Defaults to current year.
        dry_run: If True, fetch data but do not write to DB.

    Returns:
        True on success, False on failure.
    """
    if season is None:
        season = date.today().year

    logger.info("Starting scrape for %d season (dry_run=%s)", season, dry_run)

    # ── Step 1: Init DB ───────────────────────────────────
    if not dry_run:
        init_db()

    # ── Step 2: Fetch schedule ────────────────────────────
    try:
        games = fetch_schedule(season=season)
        logger.info("Fetched %d home games from MLB Stats API", len(games))
    except Exception as exc:
        logger.error("Schedule fetch failed: %s", exc)
        return False

    if not games:
        logger.warning("No games returned for season %d — check teamId/5388", season)
        return False

    # ── Step 3: Upsert games ──────────────────────────────
    if not dry_run:
        with get_conn() as conn:
            for game in games:
                upsert_game(conn, game)
        logger.info("Upserted %d games to database", len(games))
    else:
        for g in games[:3]:
            logger.info("  [dry-run] game: %s %s vs %s", g["game_date"], g["day_of_week"], g["opponent"])

    # ── Step 4: Fetch promotions ──────────────────────────
    try:
        promo_map = fetch_promotions()
        logger.info("Fetched promotions for %d game dates", len(promo_map))
    except Exception as exc:
        # Promotions failure is non-fatal — games still get alerts
        logger.warning("Promotions fetch failed (non-fatal): %s", exc)
        promo_map = {}

    # ── Step 5: Upsert promotions ─────────────────────────
    if not dry_run and promo_map:
        with get_conn() as conn:
            matched = 0
            for game_date_str, promos in promo_map.items():
                rows = get_games_on_date(conn, game_date_str)
                for row in rows:
                    upsert_promotions(conn, row["id"], promos)
                    matched += 1
            logger.info("Matched promotions to %d games", matched)

    logger.info("Scrape complete ✓")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Yard Goats schedule scraper")
    parser.add_argument("--season",  type=int, default=None, help="Season year (default: current year)")
    parser.add_argument("--dry-run", action="store_true",   help="Fetch but do not write to DB")
    args = parser.parse_args()

    success = run(season=args.season, dry_run=args.dry_run)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
