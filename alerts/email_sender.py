"""
alerts/email_sender.py — SendGrid email delivery.

Per FR-22 through FR-26:
  - HTML game card template
  - Subject line per defined pattern
  - 'Get Tickets' CTA
  - Delivery logging
"""

import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TEMPLATE_PATH = Path(__file__).parent / "templates" / "alert_email.html"
FROM_EMAIL    = "alerts@yardgoatstracker.app"
FROM_NAME     = "Yard Goats Alerts"

PROMO_ICONS = {
    "giveaway":  "🎁",
    "fireworks": "🎆",
    "discount":  "💰",
    "theme":     "🎭",
    "heritage":  "⚾",
    "special":   "⭐",
}


def send_email(
    to_email: str,
    subject:  str,
    payload:  dict,
    dry_run:  bool = False,
    client=None,
) -> tuple[bool, str]:
    """
    Send an HTML alert email via SendGrid.

    Args:
        to_email: Recipient email address
        subject:  Email subject line (pre-formatted by engine.py)
        payload:  Alert payload dict from engine.build_alert_payload()
        dry_run:  If True, render but do not send
        client:   Optional pre-built SendGrid client (for tests)

    Returns:
        (success: bool, status_detail: str)
    """
    html_body = _render_template(payload)

    if dry_run:
        logger.info("[dry-run] Email to %s | Subject: %s", _mask(to_email), subject)
        return True, "dry_run"

    if client is not None:
        sg_client = client
    else:
        sg_client = _get_sendgrid_client()

    try:
        # Build message — handle missing sendgrid gracefully (test clients use duck typing)
        try:
            from sendgrid.helpers.mail import Mail, To, From, Subject, HtmlContent
            message = Mail(
                from_email=From(FROM_EMAIL, FROM_NAME),
                to_emails=To(to_email),
                subject=Subject(subject),
                html_content=HtmlContent(html_body),
            )
        except ImportError:
            # sendgrid not installed — pass dict; injectable clients handle it
            message = {"from": FROM_EMAIL, "to": to_email,
                       "subject": subject, "html": html_body}

        response = sg_client.send(message)
        status_code = response.status_code

        if 200 <= status_code < 300:
            logger.info("Email sent to %s (status=%d)", _mask(to_email), status_code)
            return True, f"http_{status_code}"
        else:
            logger.error(
                "Email failed for %s (status=%d): %s",
                _mask(to_email), status_code, response.body
            )
            return False, f"http_{status_code}"

    except Exception as exc:
        logger.error("Email exception for %s: %s", _mask(to_email), exc)
        return False, f"exception: {exc}"


def _render_template(payload: dict) -> str:
    """
    Minimal template renderer — replaces {{ var }} placeholders.
    """
    template = TEMPLATE_PATH.read_text()

    # Build promo list HTML
    if payload.get("promos"):
        items = ""
        for promo in payload["promos"]:
            pt   = promo["promo_type"]
            desc = promo["description"]
            items += f'<li class="badge-{pt}">{desc}</li>\n'
        promo_list = f"<ul>\n{items}</ul>"
    else:
        promo_list = '<p class="badge-tbd">Promotions TBD</p>'

    # Replace {{ var }} placeholders
    html = template
    replacements = {
        "day":          payload.get("day", ""),
        "display_date": payload.get("display_date", ""),
        "opponent":     payload.get("opponent", ""),
        "time":         payload.get("time", "TBD"),
        "promo_summary": payload.get("promo_summary", ""),
        "promo_list":   promo_list,
        "ticket_url":   payload.get("ticket_url", "#"),
    }
    for key, value in replacements.items():
        html = html.replace("{{ " + key + " }}", str(value))
        html = html.replace("{{" + key + "}}", str(value))

    return html


def _get_sendgrid_client():
    try:
        import sendgrid
    except ImportError:
        raise RuntimeError("sendgrid package not installed. Run: pip install sendgrid")
    api_key = os.environ.get("SENDGRID_API_KEY", "")
    if not api_key:
        raise RuntimeError("SENDGRID_API_KEY must be set")
    return sendgrid.SendGridAPIClient(api_key=api_key)


def _mask(email: str) -> str:
    """Mask email for safe logging e.g. al***@example.com."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    masked_local = local[:2] + "***" if len(local) > 2 else "***"
    return f"{masked_local}@{domain}"
