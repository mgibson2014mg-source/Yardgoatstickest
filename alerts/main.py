"""
alerts/main.py — Main entry point for the daily alert job.
Called by GitHub Actions daily-alerts.yml at 09:00 UTC.

Flow:
  1. Check data freshness (staleness guard)
  2. Find games exactly 5 days from today that are Fri/Sat/Sun home games
  3. For each game × each active recipient:
     a. Check dedup (skip if already alerted)
     b. Send SMS (if recipient has phone)
     c. Send email (if recipient has email)
     d. Log delivery status
  4. Commit delivery log (handled by GitHub Actions workflow)
"""

import logging
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from admin.db import (
    init_db, get_conn, list_recipients,
    has_alert_been_sent, log_alert
)
from alerts.engine import (
    get_qualifying_games, build_alert_payload,
    check_data_freshness, format_sms_message, format_email_subject
)
from alerts.sms import send_sms
from alerts.email_sender import send_email

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("alerts.main")


def run(
    today:   date   = None,
    dry_run: bool   = False,
    sms_client=None,
    email_client=None,
) -> dict:
    """
    Execute the full alert pipeline for a given day.

    Args:
        today:        Reference date (defaults to date.today())
        dry_run:      If True, build payloads but do not send or log
        sms_client:   Injectable Twilio client (for tests)
        email_client: Injectable SendGrid client (for tests)

    Returns:
        Summary dict: { games_checked, alerts_sent, sms_sent,
                        email_sent, sms_failed, email_failed, skipped }
    """
    if today is None:
        today = date.today()

    target_date = today + timedelta(days=5)
    logger.info(
        "Alert run: today=%s, alerting for games on %s (dry_run=%s)",
        today, target_date, dry_run
    )

    stats = {
        "games_checked": 0,
        "alerts_sent":   0,
        "sms_sent":      0,
        "email_sent":    0,
        "sms_failed":    0,
        "email_failed":  0,
        "skipped":       0,
    }

    init_db()

    with get_conn() as conn:
        # ── Staleness guard ───────────────────────────────
        if not check_data_freshness(conn):
            logger.warning("Stale data — skipping alert run")
            return stats

        # ── Find qualifying games ─────────────────────────
        games = get_qualifying_games(conn, target_date)
        stats["games_checked"] = len(games)

        if not games:
            logger.info("No qualifying games on %s — nothing to send", target_date)
            return stats

        # ── Get active recipients ─────────────────────────
        recipients = list_recipients(conn, active_only=True)
        if not recipients:
            logger.warning("No active recipients configured")
            return stats

        logger.info(
            "Found %d game(s) on %s, %d recipient(s)",
            len(games), target_date, len(recipients)
        )

        # ── Send alerts ───────────────────────────────────
        for game in games:
            payload = build_alert_payload(game)
            subject = format_email_subject(payload)
            sms_msg = format_sms_message(payload)

            logger.info(
                "Processing: %s vs %s | %s",
                payload["game_date"], payload["opponent"], payload["promo_summary"][:50]
            )

            for recipient in recipients:
                rid     = recipient["id"]
                gid     = payload["game_id"]
                r_name  = recipient["name"]

                # ── SMS ───────────────────────────────────
                if recipient["phone"]:
                    if not dry_run and has_alert_been_sent(conn, gid, rid, "sms"):
                        logger.debug("SMS already sent: game=%d recipient=%d", gid, rid)
                        stats["skipped"] += 1
                    else:
                        success, detail = send_sms(
                            to_number=recipient["phone"],
                            message=sms_msg,
                            dry_run=dry_run,
                            client=sms_client,
                        )
                        status = "delivered" if success else "failed"
                        if not dry_run:
                            log_alert(conn, gid, rid, "sms", status)
                        if success:
                            stats["sms_sent"] += 1
                            stats["alerts_sent"] += 1
                            logger.info("SMS ✓ → %s", r_name)
                        else:
                            stats["sms_failed"] += 1
                            logger.error("SMS ✗ → %s: %s", r_name, detail)

                # ── Email ─────────────────────────────────
                if recipient["email"]:
                    if not dry_run and has_alert_been_sent(conn, gid, rid, "email"):
                        logger.debug("Email already sent: game=%d recipient=%d", gid, rid)
                        stats["skipped"] += 1
                    else:
                        success, detail = send_email(
                            to_email=recipient["email"],
                            subject=subject,
                            payload=payload,
                            dry_run=dry_run,
                            client=email_client,
                        )
                        status = "delivered" if success else "failed"
                        if not dry_run:
                            log_alert(conn, gid, rid, "email", status)
                        if success:
                            stats["email_sent"] += 1
                            stats["alerts_sent"] += 1
                            logger.info("Email ✓ → %s", r_name)
                        else:
                            stats["email_failed"] += 1
                            logger.error("Email ✗ → %s: %s", r_name, detail)

    logger.info(
        "Alert run complete — sent=%d sms=%d email=%d failed=%d skipped=%d",
        stats["alerts_sent"], stats["sms_sent"], stats["email_sent"],
        stats["sms_failed"] + stats["email_failed"], stats["skipped"]
    )
    return stats


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Yard Goats alert engine")
    parser.add_argument("--dry-run", action="store_true", help="Send no messages, log only")
    parser.add_argument("--date",    default=None, help="Override today's date YYYY-MM-DD")
    args = parser.parse_args()

    today = None
    if args.date:
        from datetime import datetime
        today = datetime.strptime(args.date, "%Y-%m-%d").date()

    stats = run(today=today, dry_run=args.dry_run)

    total_failed = stats["sms_failed"] + stats["email_failed"]
    sys.exit(1 if total_failed > 0 and stats["alerts_sent"] == 0 else 0)


if __name__ == "__main__":
    main()
