"""
alerts/sms.py — Twilio SMS delivery with retry logic.

Per architecture section 3.2 and reliability design 8.4:
  - Retry up to 3 times with exponential backoff
  - Log delivery status per FR-19
  - Message ≤ 320 chars per NFR-05
"""

import logging
import os
import time
from typing import Optional

logger = logging.getLogger(__name__)

MAX_RETRIES    = 3
RETRY_BASE_SEC = 2   # exponential: 2s, 4s, 8s


def send_sms(
    to_number: str,
    message:   str,
    dry_run:   bool = False,
    client=None,   # injectable Twilio client for testing
) -> tuple[bool, str]:
    """
    Send an SMS via Twilio.

    Args:
        to_number: E.164 phone number e.g. "+18605550001"
        message:   Message body (≤ 320 chars)
        dry_run:   If True, log but do not actually send
        client:    Optional pre-built Twilio client (for tests)

    Returns:
        (success: bool, status_detail: str)
    """
    if len(message) > 320:
        logger.warning("SMS message exceeds 320 chars (%d) — truncating", len(message))
        message = message[:317] + "..."

    if dry_run:
        logger.info("[dry-run] SMS to %s: %s", to_number, message[:60] + "...")
        return True, "dry_run"

    twilio_client = client or _get_twilio_client()
    from_number   = os.environ.get("TWILIO_FROM_NUMBER", "")

    if not from_number:
        logger.error("TWILIO_FROM_NUMBER not set")
        return False, "missing_config"

    last_error = ""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            msg = twilio_client.messages.create(
                body=message,
                from_=from_number,
                to=to_number,
            )
            logger.info(
                "SMS sent to %s (sid=%s, status=%s)",
                _mask(to_number), msg.sid, msg.status
            )
            return True, msg.status or "sent"

        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                wait = RETRY_BASE_SEC ** attempt
                logger.warning(
                    "SMS attempt %d/%d failed for %s: %s — retrying in %ds",
                    attempt, MAX_RETRIES, _mask(to_number), exc, wait
                )
                time.sleep(wait)
            else:
                logger.error(
                    "SMS failed after %d attempts for %s: %s",
                    MAX_RETRIES, _mask(to_number), exc
                )

    return False, f"failed: {last_error}"


def _get_twilio_client():
    """Build a Twilio client from environment variables."""
    try:
        from twilio.rest import Client
    except ImportError:
        raise RuntimeError(
            "twilio package not installed. Run: pip install twilio"
        )
    sid   = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN",  "")
    if not sid or not token:
        raise RuntimeError("TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set")
    return Client(sid, token)


def _mask(phone: str) -> str:
    """Mask phone number for safe logging e.g. +1860***1234."""
    if len(phone) < 6:
        return "***"
    return phone[:5] + "***" + phone[-4:]
