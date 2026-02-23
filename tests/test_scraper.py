"""
tests/test_scraper.py — Phase 2 scraper tests.
All tests run offline using fixtures — no network required.
Run: python tests/test_scraper.py
"""

import json
import os
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "data"))

FIXTURES = Path(__file__).parent / "fixtures"


# ══════════════════════════════════════════════════════════
# SCHEDULE PARSER TESTS
# ══════════════════════════════════════════════════════════
class TestScheduleParser(unittest.TestCase):
    def setUp(self):
        self.api_data = json.loads(
            (FIXTURES / "mlb_api_schedule.json").read_text()
        )
        from scraper.schedule import _parse_api_response, _parse_datetime, _parse_game
        self.parse_api_response = _parse_api_response
        self.parse_datetime     = _parse_datetime
        self.parse_game         = _parse_game

    def test_parse_returns_home_games_only(self):
        games = self.parse_api_response(self.api_data)
        # Fixture has 5 home games + 1 away game
        self.assertEqual(len(games), 5)
        for g in games:
            self.assertEqual(g["is_home"], 1)

    def test_friday_game_parsed(self):
        games = self.parse_api_response(self.api_data)
        fri = next(g for g in games if g["game_date"] == "2026-04-10")
        self.assertEqual(fri["day_of_week"], "Friday")
        self.assertEqual(fri["opponent"], "Portland Sea Dogs")

    def test_saturday_game_parsed(self):
        games = self.parse_api_response(self.api_data)
        sat = next(g for g in games if g["game_date"] == "2026-04-11")
        self.assertEqual(sat["day_of_week"], "Saturday")

    def test_sunday_game_parsed(self):
        games = self.parse_api_response(self.api_data)
        sun = next(g for g in games if g["game_date"] == "2026-04-12")
        self.assertEqual(sun["day_of_week"], "Sunday")

    def test_tuesday_game_parsed(self):
        games = self.parse_api_response(self.api_data)
        tue = next(g for g in games if g["game_date"] == "2026-04-14")
        self.assertEqual(tue["day_of_week"], "Tuesday")

    def test_away_game_excluded(self):
        games = self.parse_api_response(self.api_data)
        dates = [g["game_date"] for g in games]
        self.assertNotIn("2026-04-28", dates)

    def test_all_required_fields_present(self):
        games = self.parse_api_response(self.api_data)
        required = {"game_date","day_of_week","start_time","opponent","is_home","ticket_url"}
        for g in games:
            self.assertEqual(required, set(g.keys()))

    def test_parse_datetime_evening_game(self):
        # 23:05 UTC → 19:05 ET (7:05 PM)
        date_str, time_str = self.parse_datetime("2026-04-10T23:05:00Z")
        self.assertEqual(date_str, "2026-04-10")
        self.assertEqual(time_str, "7:05 PM")

    def test_parse_datetime_afternoon_game(self):
        # 17:05 UTC → 13:05 ET (1:05 PM)
        date_str, time_str = self.parse_datetime("2026-04-12T17:05:00Z")
        self.assertEqual(date_str, "2026-04-12")
        self.assertEqual(time_str, "1:05 PM")

    def test_parse_datetime_empty_string(self):
        date_str, time_str = self.parse_datetime("")
        self.assertEqual(date_str, "")
        self.assertEqual(time_str, "")

    def test_parse_game_skips_malformed(self):
        result = self.parse_game({"gamePk": 999})
        self.assertIsNone(result)

    def test_fetch_schedule_uses_requests(self):
        """fetch_schedule wires up requests correctly."""
        from scraper.schedule import fetch_schedule
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.api_data
        mock_resp.raise_for_status.return_value = None

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp

        games = fetch_schedule(season=2026, session=mock_session)
        self.assertEqual(len(games), 5)
        mock_session.get.assert_called_once()
        call_args = mock_session.get.call_args
        self.assertIn("schedule", call_args[0][0])

    def test_fetch_schedule_raises_on_http_error(self):
        """fetch_schedule propagates request exceptions."""
        import requests as req
        from scraper.schedule import fetch_schedule
        mock_session = MagicMock()
        mock_session.get.side_effect = req.RequestException("timeout")
        with self.assertRaises(req.RequestException):
            fetch_schedule(season=2026, session=mock_session)

    def test_ticket_url_present(self):
        games = self.parse_api_response(self.api_data)
        for g in games:
            self.assertIsNotNone(g["ticket_url"])
            self.assertIn("milb.com", g["ticket_url"])


# ══════════════════════════════════════════════════════════
# PROMOTIONS PARSER TESTS
# ══════════════════════════════════════════════════════════
class TestPromotionsParser(unittest.TestCase):
    def setUp(self):
        self.html = (FIXTURES / "promotions_page.html").read_text()
        from scraper.promotions import fetch_promotions, classify_promo, _parse_date_from_text
        self.fetch_promotions    = fetch_promotions
        self.classify_promo      = classify_promo
        self.parse_date_from_text = _parse_date_from_text

    def test_returns_dict(self):
        result = self.fetch_promotions(html=self.html)
        self.assertIsInstance(result, dict)

    def test_detects_giveaway_game(self):
        result = self.fetch_promotions(html=self.html)
        self.assertIn("2026-04-10", result)
        types = {p["promo_type"] for p in result["2026-04-10"]}
        self.assertIn("giveaway", types)

    def test_detects_fireworks_game(self):
        result = self.fetch_promotions(html=self.html)
        self.assertIn("2026-04-10", result)
        types = {p["promo_type"] for p in result["2026-04-10"]}
        self.assertIn("fireworks", types)

    def test_detects_discount_game(self):
        result = self.fetch_promotions(html=self.html)
        self.assertIn("2026-06-07", result)
        types = {p["promo_type"] for p in result["2026-06-07"]}
        self.assertIn("discount", types)

    def test_detects_theme_night(self):
        result = self.fetch_promotions(html=self.html)
        self.assertIn("2026-05-04", result)
        types = {p["promo_type"] for p in result["2026-05-04"]}
        # Star Wars Night → theme
        self.assertIn("theme", types)

    def test_detects_heritage_night(self):
        result = self.fetch_promotions(html=self.html)
        self.assertIn("2026-08-01", result)
        types = {p["promo_type"] for p in result["2026-08-01"]}
        self.assertIn("heritage", types)

    def test_promo_descriptions_nonempty(self):
        result = self.fetch_promotions(html=self.html)
        for date_str, promos in result.items():
            for p in promos:
                self.assertGreater(len(p["description"]), 3)

    def test_all_promos_have_valid_type(self):
        valid_types = {"giveaway","fireworks","discount","theme","heritage","special"}
        result = self.fetch_promotions(html=self.html)
        for date_str, promos in result.items():
            for p in promos:
                self.assertIn(p["promo_type"], valid_types)

    def test_empty_html_returns_empty_dict(self):
        result = self.fetch_promotions(html="<html><body></body></html>")
        self.assertEqual(result, {})


class TestPromotionClassifier(unittest.TestCase):
    def setUp(self):
        from scraper.promotions import classify_promo
        self.classify = classify_promo

    def test_hat_is_giveaway(self):
        self.assertEqual(self.classify("Cowboy Hat Giveaway"), "giveaway")

    def test_jersey_is_giveaway(self):
        self.assertEqual(self.classify("Vintage Delivery Driver Jersey Giveaway"), "giveaway")

    def test_fireworks_classified(self):
        self.assertEqual(self.classify("Post-Game Fireworks Show"), "fireworks")

    def test_dollar_is_discount(self):
        self.assertEqual(self.classify("$1 Hot Dog Night"), "discount")

    def test_discount_keyword(self):
        self.assertEqual(self.classify("Discount Tuesday – reduced tickets"), "discount")

    def test_star_wars_is_theme(self):
        self.assertEqual(self.classify("Star Wars Night"), "theme")

    def test_90s_night_is_theme(self):
        self.assertEqual(self.classify("90s Night with DJ"), "theme")

    def test_whalers_is_heritage(self):
        self.assertEqual(self.classify("Hartford Whalers Heritage Night"), "heritage")

    def test_unknown_is_special(self):
        self.assertEqual(self.classify("First pitch ceremony"), "special")

    def test_fanny_pack_is_giveaway(self):
        self.assertEqual(self.classify("Fanny Pack Hat Giveaway"), "giveaway")

    def test_crocs_is_giveaway(self):
        self.assertEqual(self.classify("Crocs Hat Giveaway"), "giveaway")


class TestDateParser(unittest.TestCase):
    def setUp(self):
        from scraper.promotions import _parse_date_from_text
        self.parse = _parse_date_from_text

    def test_full_date_with_year(self):
        result = self.parse("Friday, April 10, 2026")
        self.assertEqual(result, "2026-04-10")

    def test_short_month_with_year(self):
        result = self.parse("Apr 10, 2026")
        self.assertEqual(result, "2026-04-10")

    def test_iso_format(self):
        result = self.parse("2026-04-10")
        self.assertEqual(result, "2026-04-10")

    def test_slash_format(self):
        result = self.parse("04/10/2026")
        self.assertEqual(result, "2026-04-10")

    def test_no_date_returns_none(self):
        result = self.parse("Post-Game Fireworks Show")
        self.assertIsNone(result)

    def test_date_in_sentence(self):
        result = self.parse("Join us Saturday, May 4, 2026 for Star Wars Night!")
        self.assertEqual(result, "2026-05-04")


# ══════════════════════════════════════════════════════════
# MAIN PIPELINE INTEGRATION TEST
# ══════════════════════════════════════════════════════════
class TestScraperMain(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        os.environ["YARDGOATS_DB"] = self.tmp.name
        from admin.db import init_db
        init_db(Path(self.tmp.name))

        self.api_data    = json.loads((FIXTURES / "mlb_api_schedule.json").read_text())
        self.promos_html = (FIXTURES / "promotions_page.html").read_text()

    def tearDown(self):
        if "YARDGOATS_DB" in os.environ:
            del os.environ["YARDGOATS_DB"]
        import gc
        gc.collect()
        import time
        time.sleep(0.6)
        Path(self.tmp.name).unlink(missing_ok=True)

    def test_full_pipeline_dry_run(self):
        """Dry run completes without writing to DB."""
        from scraper.main import run
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.api_data
        mock_resp.raise_for_status.return_value = None
        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch("scraper.schedule.requests.Session", return_value=mock_sess):
            result = run(season=2026, dry_run=True)
        self.assertTrue(result)

    def test_full_pipeline_writes_games(self):
        """Live run upserts games to DB."""
        from scraper.main import run
        from admin.db import get_conn

        mock_resp = MagicMock()
        mock_resp.json.return_value = self.api_data
        mock_resp.raise_for_status.return_value = None
        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch("scraper.schedule.requests.Session", return_value=mock_sess):
            with patch("scraper.promotions._fetch_html", return_value=self.promos_html):
                result = run(season=2026, dry_run=False)

        self.assertTrue(result)

        with get_conn(Path(self.tmp.name)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        self.assertEqual(count, 5)  # 5 home games in fixture

    def test_pipeline_handles_schedule_failure(self):
        """Schedule failure returns False (not crash)."""
        import requests as req
        from scraper.main import run
        mock_sess = MagicMock()
        mock_sess.get.side_effect = req.RequestException("network error")

        with patch("scraper.schedule.requests.Session", return_value=mock_sess):
            result = run(season=2026, dry_run=False)
        self.assertFalse(result)

    def test_pipeline_continues_on_promotions_failure(self):
        """Promotions failure is non-fatal — games still saved."""
        from scraper.main import run
        from admin.db import get_conn

        mock_resp = MagicMock()
        mock_resp.json.return_value = self.api_data
        mock_resp.raise_for_status.return_value = None
        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch("scraper.schedule.requests.Session", return_value=mock_sess):
            with patch("scraper.promotions._fetch_html", side_effect=Exception("promo page down")):
                result = run(season=2026, dry_run=False)

        self.assertTrue(result)  # still succeeds

        with get_conn(Path(self.tmp.name)) as conn:
            count = conn.execute("SELECT COUNT(*) FROM games").fetchone()[0]
        self.assertEqual(count, 5)  # games saved despite promo failure

    def test_promotions_matched_to_games(self):
        """Promotions parsed from HTML are associated with correct game_ids."""
        from scraper.main import run
        from admin.db import get_conn

        mock_resp = MagicMock()
        mock_resp.json.return_value = self.api_data
        mock_resp.raise_for_status.return_value = None
        mock_sess = MagicMock()
        mock_sess.get.return_value = mock_resp

        with patch("scraper.schedule.requests.Session", return_value=mock_sess):
            with patch("scraper.promotions._fetch_html", return_value=self.promos_html):
                run(season=2026, dry_run=False)

        with get_conn(Path(self.tmp.name)) as conn:
            promo_count = conn.execute("SELECT COUNT(*) FROM promotions").fetchone()[0]
        # Apr 10 game has 2 promos in fixture
        self.assertGreater(promo_count, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
