"""
scraper/promotions.py — Scrape Hartford Yard Goats promotions calendar.

Source: https://www.milb.com/hartford/tickets/promotions

The promotions page is server-rendered HTML. Each game's promotions
are listed in sections that include the date and a list of promo items.

Promotion type classification is keyword-based — built to be updated
as new event types emerge during the season.
"""

import logging
import re
from datetime import date, datetime
from typing import Optional

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PROMOS_URL = "https://www.milb.com/hartford/tickets/promotions"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# ── Keyword → promo_type mapping (order matters — first match wins) ──
PROMO_RULES: list[tuple[list[str], str]] = [
    (["giveaway", "give away", "hat", "shirt", "jersey", "bobblehead",
      "tote", "bag", "paddle", "crocs", "fanny pack", "cowboy"],   "giveaway"),
    (["fireworks", "firework"],                                      "fireworks"),
    (["dollar", "$1", "discount", "deal", "buck", "cheap",
      "happy hour", "value"],                                        "discount"),
    (["negro league", "whalers", "alumni", "heritage"],              "heritage"),
    (["star wars", "pajama", "country", "90s", "unicorn",
      "night", "theme", "celebration", "pride",
      "jersey retirement", "boy band"],                              "theme"),
]

# ── Public API ────────────────────────────────────────────

def fetch_promotions(
    html: Optional[str] = None,
    session: Optional[requests.Session] = None,
) -> dict[str, list[dict]]:
    """
    Scrape the promotions page.

    Returns dict keyed by game_date (YYYY-MM-DD) → list of promo dicts:
        { promo_type: str, description: str }

    Pass `html` directly to bypass HTTP (used in tests).
    """
    if html is None:
        html = _fetch_html(session)

    soup = BeautifulSoup(html, "html.parser")
    result = _parse_promotions(soup)
    return result if result is not None else {}


def classify_promo(description: str) -> str:
    """
    Classify a promotion description string into a promo_type.
    Falls back to 'special' if no keyword matches.
    """
    text = description.lower()
    for keywords, promo_type in PROMO_RULES:
        if any(kw in text for kw in keywords):
            return promo_type
    return "special"


# ── Internal ──────────────────────────────────────────────

def _fetch_html(session: Optional[requests.Session] = None) -> str:
    sess = session or requests.Session()
    sess.headers.update(DEFAULT_HEADERS)
    try:
        resp = sess.get(PROMOS_URL, timeout=20)
        resp.raise_for_status()
        return resp.text
    except requests.RequestException as exc:
        logger.error("Failed to fetch promotions page: %s", exc)
        raise


def _parse_promotions(soup: BeautifulSoup) -> dict[str, list[dict]]:
    """
    Parse the promotions page HTML.
    """
    result: dict[str, list[dict]] = {}

    # Check for table rows (common in both real site and our test fixture)
    rows = soup.find_all("tr")
    if rows:
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                date_text = cols[0].get_text(strip=True)
                desc_text = cols[1].get_text(strip=True)
                
                game_date = _parse_date_from_text(date_text)
                if game_date:
                    if game_date not in result:
                        result[game_date] = []
                    
                    # Split multiple promos in one description
                    descriptions = [d.strip() for d in desc_text.split("&")]
                    for d in descriptions:
                        result[game_date].append({
                            "promo_type": classify_promo(d),
                            "description": d
                        })
        if result:
            return result

    # Strategy 1: Look for structured promotion containers


def _extract_date_from_element(element) -> Optional[str]:
    """Try to find a date string within an HTML element."""
    text = element.get_text(" ", strip=True)
    return _parse_date_from_text(text)


def _parse_date_from_text(text: str) -> Optional[str]:
    """
    Extract a YYYY-MM-DD date from a text string.
    Handles patterns like:
      "Friday, April 10"     → uses current/next season year
      "Apr 10, 2026"
      "April 10, 2026"
      "04/10/2026"
      "04/10/26"
    """
    current_year = datetime.now().year
    patterns = [
        # "April 10, 2026" or "Friday, April 10, 2026"
        (r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*"
         r"(\w+ \d{1,2},?\s*\d{4})",
         "%B %d, %Y"),
        # "Apr 10, 2026"
        (r"(\w{3} \d{1,2},?\s*\d{4})", "%b %d, %Y"),
        # "April 10" (no year — assume upcoming season)
        (r"(\w+ \d{1,2})(?!\s*,?\s*\d{4})", "%B %d"),
        # "04/10/2026"
        (r"(\d{1,2}/\d{1,2}/\d{4})", "%m/%d/%Y"),
        # "2026-04-10"
        (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),
    ]

    for pattern, fmt in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            raw = match.group(1).strip().rstrip(",")
            # Normalize spaces
            raw = re.sub(r"\s+", " ", raw)
            try:
                if "%Y" not in fmt:
                    # No year in format — append current season year
                    raw = f"{raw}, {current_year}"
                    fmt = fmt + ", %Y"
                parsed = datetime.strptime(raw, fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
    return None


def _extract_promos_from_element(element) -> list[dict]:
    """Extract promotion descriptions from an HTML element."""
    promos = []
    # Look for list items, paragraphs, or span text within the section
    candidates = (
        element.find_all("li") or
        element.find_all("p") or
        [element]
    )
    for candidate in candidates:
        text = candidate.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 4 or len(text) > 200:
            continue
        # Skip pure date strings
        if _parse_date_from_text(text) and len(text) < 20:
            continue
        promo_type = classify_promo(text)
        promos.append({"promo_type": promo_type, "description": text})
    return promos


def _parse_by_text_scan(soup: BeautifulSoup) -> dict[str, list[dict]]:
    """
    Fallback parser: walk all text nodes, collect date anchors,
    associate following text items as promotions.
    """
    result: dict[str, list[dict]] = {}
    current_date = None

    for element in soup.find_all(["h1","h2","h3","h4","h5","p","li","div","span"]):
        # Skip deeply nested duplicates — only process leaf-ish nodes
        if element.find(["h1","h2","h3","h4","h5"]):
            continue
        text = element.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if not text or len(text) > 250:
            continue

        # Check if this element contains a date
        date_str = _parse_date_from_text(text)
        if date_str:
            current_date = date_str
            continue

        # Associate text with current date as a promotion
        if current_date and 4 <= len(text) <= 200:
            # Skip navigation noise
            if any(nav in text.lower() for nav in
                   ["schedule", "tickets", "roster", "standings",
                    "copyright", "privacy", "follow us", "social"]):
                continue
            promo_type = classify_promo(text)
            if current_date not in result:
                result[current_date] = []
            result[current_date].append({
                "promo_type":  promo_type,
                "description": text,
            })

    return result
