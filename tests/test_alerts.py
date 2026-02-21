"""
tests/test_alerts.py — Phase 3 alert engine tests.
All external services mocked — no Twilio/SendGrid calls.
Run: python tests/test_alerts.py
"""

import os
import sys
import tempfile
import unittest
from datetime import date, timedelta, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def make_tmp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["YARDGOATS_DB"] = tmp.name
    from admin.db import init_db
    init_db(Path(tmp.name))
    return Path(tmp.name)


def teardown_tmp_db(path):
    if "YARDGOATS_DB" in os.environ:
        del os.environ["YARDGOATS_DB"]
    import gc
    gc.collect()
    import time
    time.sleep(0.3)
    path.unlink(missing_ok=True)


def insert_game(conn, game_date: str, dow: str, opponent="Sea Dogs",
                start_time="7:05 PM", ticket_url="https://milb.com/hartford/tickets"):
    from admin.db import upsert_game
    return upsert_game(conn, {
        "game_date": game_date, "day_of_week": dow, "start_time": start_time,
        "opponent": opponent, "is_home": 1, "ticket_url": ticket_url,
    })


def insert_recipient(conn, name="Alice", phone="+18605550001", email="alice@test.com"):
    from admin.db import add_recipient
    return add_recipient(conn, name, phone, email)


# ══════════════════════════════════════════════════════════
# ENGINE LOGIC TESTS
# ══════════════════════════════════════════════════════════
class TestEngineQualifyingGames(unittest.TestCase):
    def setUp(self):
        self.db = make_tmp_db()
        from admin.db import get_conn
        self.get_conn = get_conn

    def tearDown(self):
        teardown_tmp_db(self.db)

    def test_friday_qualifies(self):
        from alerts.engine import get_qualifying_games
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            games = get_qualifying_games(conn, date(2026, 4, 10))
        self.assertEqual(len(games), 1)

    def test_saturday_qualifies(self):
        from alerts.engine import get_qualifying_games
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-11", "Saturday")
            games = get_qualifying_games(conn, date(2026, 4, 11))
        self.assertEqual(len(games), 1)

    def test_sunday_qualifies(self):
        from alerts.engine import get_qualifying_games
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-12", "Sunday")
            games = get_qualifying_games(conn, date(2026, 4, 12))
        self.assertEqual(len(games), 1)

    def test_tuesday_does_not_qualify(self):
        from alerts.engine import get_qualifying_games
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-14", "Tuesday")
            games = get_qualifying_games(conn, date(2026, 4, 14))
        self.assertEqual(len(games), 0)

    def test_wednesday_does_not_qualify(self):
        from alerts.engine import get_qualifying_games
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-15", "Wednesday")
            games = get_qualifying_games(conn, date(2026, 4, 15))
        self.assertEqual(len(games), 0)

    def test_away_game_does_not_qualify(self):
        from alerts.engine import get_qualifying_games
        from admin.db import upsert_game
        with self.get_conn(self.db) as conn:
            upsert_game(conn, {
                "game_date": "2026-04-10", "day_of_week": "Friday",
                "start_time": "7:05 PM", "opponent": "Sea Dogs",
                "is_home": 0, "ticket_url": None,
            })
            games = get_qualifying_games(conn, date(2026, 4, 10))
        self.assertEqual(len(games), 0)

    def test_wrong_date_no_results(self):
        from alerts.engine import get_qualifying_games
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            games = get_qualifying_games(conn, date(2026, 4, 11))
        self.assertEqual(len(games), 0)


class TestBuildAlertPayload(unittest.TestCase):
    def setUp(self):
        self.db = make_tmp_db()
        from admin.db import get_conn, upsert_promotions
        self.get_conn = get_conn
        self.upsert_promotions = upsert_promotions

    def tearDown(self):
        teardown_tmp_db(self.db)

    def test_payload_all_fields_present(self):
        from alerts.engine import get_qualifying_games, build_alert_payload
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            games = get_qualifying_games(conn, date(2026, 4, 10))
        payload = build_alert_payload(games[0])
        required = {"game_id","game_date","display_date","day","time",
                    "opponent","ticket_url","promo_summary","promos","has_promos"}
        self.assertEqual(required, set(payload.keys()))

    def test_payload_tbd_when_no_promos(self):
        from alerts.engine import get_qualifying_games, build_alert_payload
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            games = get_qualifying_games(conn, date(2026, 4, 10))
        payload = build_alert_payload(games[0])
        self.assertFalse(payload["has_promos"])
        self.assertIn("TBD", payload["promo_summary"])

    def test_payload_includes_promos_when_present(self):
        from alerts.engine import get_qualifying_games, build_alert_payload
        with self.get_conn(self.db) as conn:
            gid = insert_game(conn, "2026-04-10", "Friday")
            self.upsert_promotions(conn, gid, [
                {"promo_type": "giveaway", "description": "Cowboy Hat"},
                {"promo_type": "fireworks", "description": "Post-game fireworks"},
            ])
            games = get_qualifying_games(conn, date(2026, 4, 10))
        payload = build_alert_payload(games[0])
        self.assertTrue(payload["has_promos"])
        self.assertEqual(len(payload["promos"]), 2)
        self.assertIn("🎁", payload["promo_summary"])
        self.assertIn("🎆", payload["promo_summary"])

    def test_display_date_formatted(self):
        from alerts.engine import get_qualifying_games, build_alert_payload
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            games = get_qualifying_games(conn, date(2026, 4, 10))
        payload = build_alert_payload(games[0])
        # Should be "Fri Apr 10" style
        # The engine uses .strftime("%a %b %d") which results in "Fri Apr 10"
        self.assertTrue(any(month in payload["display_date"] for month in ["Apr", "04"]))
        self.assertIn("10", payload["display_date"])


class TestSMSFormatting(unittest.TestCase):
    def _make_payload(self, with_promos=False):
        promos = [{"promo_type": "giveaway", "description": "Cowboy Hat Giveaway"}] if with_promos else []
        return {
            "day": "Friday", "display_date": "Fri Apr 10",
            "time": "7:05 PM", "opponent": "Portland Sea Dogs",
            "ticket_url": "https://milb.com/hartford/tickets",
            "promo_summary": "🎁 Cowboy Hat Giveaway" if with_promos else "Promotions TBD — check dashboard",
            "promos": promos, "has_promos": with_promos,
        }

    def test_sms_within_320_chars(self):
        from alerts.engine import format_sms_message
        msg = format_sms_message(self._make_payload())
        self.assertLessEqual(len(msg), 320)

    def test_sms_contains_game_info(self):
        from alerts.engine import format_sms_message
        msg = format_sms_message(self._make_payload())
        self.assertIn("Friday", msg)
        self.assertIn("Portland Sea Dogs", msg)
        self.assertIn("7:05 PM", msg)
        self.assertIn("milb.com", msg)

    def test_sms_tbd_when_no_promos(self):
        from alerts.engine import format_sms_message
        msg = format_sms_message(self._make_payload(with_promos=False))
        self.assertIn("TBD", msg)

    def test_sms_shows_promo_when_present(self):
        from alerts.engine import format_sms_message
        msg = format_sms_message(self._make_payload(with_promos=True))
        self.assertIn("Cowboy Hat", msg)

    def test_sms_truncates_if_over_320(self):
        from alerts.engine import format_sms_message
        long_payload = {
            **self._make_payload(),
            "promo_summary": "🎁 " + ("x" * 400),
        }
        msg = format_sms_message(long_payload)
        self.assertLessEqual(len(msg), 320)

    def test_sms_includes_stop_instruction(self):
        from alerts.engine import format_sms_message
        msg = format_sms_message(self._make_payload())
        self.assertIn("STOP", msg)


class TestEmailSubject(unittest.TestCase):
    def test_subject_with_promo(self):
        from alerts.engine import format_email_subject
        payload = {
            "day": "Friday", "display_date": "Fri Apr 10",
            "opponent": "Sea Dogs", "has_promos": True,
            "promos": [{"promo_type": "giveaway", "description": "Cowboy Hat Giveaway"}],
        }
        subject = format_email_subject(payload)
        self.assertIn("Friday", subject)
        self.assertIn("Sea Dogs", subject)
        self.assertIn("Cowboy Hat", subject)

    def test_subject_without_promo(self):
        from alerts.engine import format_email_subject
        payload = {
            "day": "Saturday", "display_date": "Sat Apr 11",
            "opponent": "Rumble Ponies", "has_promos": False, "promos": [],
        }
        subject = format_email_subject(payload)
        self.assertIn("Saturday", subject)
        self.assertIn("Rumble Ponies", subject)
        self.assertIn("Upcoming Game", subject)


class TestDataFreshness(unittest.TestCase):
    def setUp(self):
        self.db = make_tmp_db()
        from admin.db import get_conn
        self.get_conn = get_conn

    def tearDown(self):
        teardown_tmp_db(self.db)

    def test_empty_db_is_stale(self):
        from alerts.engine import check_data_freshness
        with self.get_conn(self.db) as conn:
            self.assertFalse(check_data_freshness(conn))

    def test_fresh_data_passes(self):
        from alerts.engine import check_data_freshness
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            # updated_at defaults to CURRENT_TIMESTAMP — should be fresh
            self.assertTrue(check_data_freshness(conn))

    def test_stale_data_fails(self):
        from alerts.engine import check_data_freshness
        from admin.db import upsert_game
        with self.get_conn(self.db) as conn:
            # Insert game with old updated_at timestamp (3 days ago)
            conn.execute("""
                INSERT INTO games (game_date, day_of_week, start_time, opponent,
                                   is_home, ticket_url, updated_at)
                VALUES ('2026-04-10','Friday','7:05 PM','Sea Dogs',1,NULL,
                        datetime('now','-3 days'))
            """)
            self.assertFalse(check_data_freshness(conn))


# ══════════════════════════════════════════════════════════
# SMS DELIVERY TESTS
# ══════════════════════════════════════════════════════════
class TestSMSDelivery(unittest.TestCase):
    def test_dry_run_returns_success(self):
        from alerts.sms import send_sms
        ok, detail = send_sms("+18605550001", "Test message", dry_run=True)
        self.assertTrue(ok)
        self.assertEqual(detail, "dry_run")

    def test_sends_via_mock_client(self):
        from alerts.sms import send_sms
        mock_msg = MagicMock()
        mock_msg.sid    = "SM123"
        mock_msg.status = "delivered"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg

        with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
            ok, detail = send_sms("+18605550001", "Hello", client=mock_client)
        self.assertTrue(ok)
        self.assertEqual(detail, "delivered")
        mock_client.messages.create.assert_called_once()

    def test_truncates_message_over_320(self):
        from alerts.sms import send_sms
        long_msg = "x" * 400
        mock_msg = MagicMock()
        mock_msg.sid = "SM999"
        mock_msg.status = "delivered"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg

        with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
            send_sms("+18605550001", long_msg, client=mock_client)

        sent_body = mock_client.messages.create.call_args[1]["body"]
        self.assertLessEqual(len(sent_body), 320)

    def test_retries_on_failure_then_succeeds(self):
        from alerts.sms import send_sms
        mock_msg = MagicMock()
        mock_msg.sid    = "SM456"
        mock_msg.status = "delivered"
        mock_client = MagicMock()
        # Fail twice, succeed on third attempt
        mock_client.messages.create.side_effect = [
            Exception("timeout"),
            Exception("timeout"),
            mock_msg,
        ]
        with patch("alerts.sms.time.sleep"):  # don't actually sleep in tests
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                ok, detail = send_sms("+18605550001", "Hello", client=mock_client)
        self.assertTrue(ok)
        self.assertEqual(mock_client.messages.create.call_count, 3)

    def test_returns_false_after_max_retries(self):
        from alerts.sms import send_sms
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("permanent failure")
        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                ok, detail = send_sms("+18605550001", "Hello", client=mock_client)
        self.assertFalse(ok)
        self.assertEqual(mock_client.messages.create.call_count, 3)

    def test_missing_from_number_returns_false(self):
        from alerts.sms import send_sms
        mock_client = MagicMock()
        env = {k: v for k, v in os.environ.items() if k != "TWILIO_FROM_NUMBER"}
        with patch.dict(os.environ, env, clear=True):
            ok, detail = send_sms("+18605550001", "Hello", client=mock_client)
        self.assertFalse(ok)

    def test_mask_phone_number(self):
        from alerts.sms import _mask
        self.assertEqual(_mask("+18605551234"), "+1860***1234")

    def test_dry_run_does_not_call_client(self):
        from alerts.sms import send_sms
        mock_client = MagicMock()
        send_sms("+18605550001", "Hello", dry_run=True, client=mock_client)
        mock_client.messages.create.assert_not_called()


# ══════════════════════════════════════════════════════════
# EMAIL DELIVERY TESTS
# ══════════════════════════════════════════════════════════
class TestEmailDelivery(unittest.TestCase):
    def _sample_payload(self, with_promos=True):
        return {
            "game_id": 1,
            "game_date": "2026-04-10",
            "display_date": "Fri Apr 10",
            "day": "Friday",
            "time": "7:05 PM",
            "opponent": "Portland Sea Dogs",
            "ticket_url": "https://milb.com/hartford/tickets",
            "promo_summary": "🎁 Cowboy Hat Giveaway | 🎆 Fireworks",
            "promos": [
                {"promo_type": "giveaway",  "description": "Cowboy Hat Giveaway"},
                {"promo_type": "fireworks", "description": "Post-game fireworks"},
            ] if with_promos else [],
            "has_promos": with_promos,
        }

    def test_dry_run_returns_success(self):
        from alerts.email_sender import send_email
        ok, detail = send_email(
            "alice@test.com", "Subject", self._sample_payload(), dry_run=True
        )
        self.assertTrue(ok)
        self.assertEqual(detail, "dry_run")

    def test_sends_via_mock_client(self):
        from alerts.email_sender import send_email
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.body = ""
        mock_client = MagicMock()
        mock_client.send.return_value = mock_response

        ok, detail = send_email(
            "alice@test.com", "Subject", self._sample_payload(), client=mock_client
        )
        self.assertTrue(ok)
        mock_client.send.assert_called_once()

    def test_returns_false_on_bad_status(self):
        from alerts.email_sender import send_email
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.body = "Internal error"
        mock_client = MagicMock()
        mock_client.send.return_value = mock_response

        ok, detail = send_email(
            "alice@test.com", "Subject", self._sample_payload(), client=mock_client
        )
        self.assertFalse(ok)

    def test_returns_false_on_exception(self):
        from alerts.email_sender import send_email
        mock_client = MagicMock()
        mock_client.send.side_effect = Exception("connection reset")
        ok, detail = send_email(
            "alice@test.com", "Subject", self._sample_payload(), client=mock_client
        )
        self.assertFalse(ok)

    def test_dry_run_does_not_call_client(self):
        from alerts.email_sender import send_email
        mock_client = MagicMock()
        send_email("alice@test.com", "Sub", self._sample_payload(),
                   dry_run=True, client=mock_client)
        mock_client.send.assert_not_called()

    def test_mask_email(self):
        from alerts.email_sender import _mask
        self.assertEqual(_mask("alice@test.com"), "al***@test.com")

    def test_mask_short_email(self):
        from alerts.email_sender import _mask
        self.assertEqual(_mask("a@b.com"), "***@b.com")

    def test_template_renders_game_info(self):
        from alerts.email_sender import _render_template
        html = _render_template(self._sample_payload())
        self.assertIn("Portland Sea Dogs", html)
        self.assertIn("7:05 PM", html)
        self.assertIn("Fri Apr 10", html)
        self.assertIn("milb.com", html)

    def test_template_renders_promo_badges(self):
        from alerts.email_sender import _render_template
        html = _render_template(self._sample_payload(with_promos=True))
        self.assertIn("Cowboy Hat Giveaway", html)
        self.assertIn("badge-giveaway", html)

    def test_template_renders_tbd_when_no_promos(self):
        from alerts.email_sender import _render_template
        html = _render_template(self._sample_payload(with_promos=False))
        self.assertIn("badge-tbd", html)
        self.assertIn("Promotions TBD", html)

    def test_template_contains_ticket_cta(self):
        from alerts.email_sender import _render_template
        html = _render_template(self._sample_payload())
        self.assertIn("Get Tickets", html)
        self.assertIn("milb.com/hartford/tickets", html)


# ══════════════════════════════════════════════════════════
# FULL PIPELINE INTEGRATION TESTS
# ══════════════════════════════════════════════════════════
class TestAlertPipeline(unittest.TestCase):
    def setUp(self):
        self.db = make_tmp_db()
        from admin.db import get_conn
        self.get_conn = get_conn
        # Friday game 5 days from "today" in tests
        self.today       = date(2026, 4, 5)   # Sunday
        self.game_date   = date(2026, 4, 10)  # Friday (today + 5)

    def tearDown(self):
        teardown_tmp_db(self.db)

    def _mock_sms(self, success=True):
        m = MagicMock()
        msg = MagicMock()
        msg.sid    = "SM_TEST"
        msg.status = "delivered" if success else "failed"
        if success:
            m.messages.create.return_value = msg
        else:
            m.messages.create.side_effect = Exception("fail")
        return m

    def _mock_email(self, status_code=202):
        m = MagicMock()
        resp = MagicMock()
        resp.status_code = status_code
        resp.body = ""
        m.send.return_value = resp
        return m

    def test_full_pipeline_sends_sms_and_email(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn, "Alice", "+18605550001", "alice@test.com")

        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                stats = run(
                    today=self.today,
                    dry_run=False,
                    sms_client=self._mock_sms(),
                    email_client=self._mock_email(),
                )

        self.assertEqual(stats["sms_sent"],   1)
        self.assertEqual(stats["email_sent"], 1)
        self.assertEqual(stats["sms_failed"], 0)

    def test_deduplication_prevents_double_send(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn, "Alice", "+18605550001", "alice@test.com")

        sms_client   = self._mock_sms()
        email_client = self._mock_email()

        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                run(today=self.today, sms_client=sms_client, email_client=email_client)
                # Run again — should be deduped
                stats2 = run(today=self.today, sms_client=sms_client, email_client=email_client)

        self.assertEqual(stats2["sms_sent"],  0)
        self.assertEqual(stats2["skipped"],   2)  # 1 SMS + 1 email skipped

    def test_dry_run_sends_nothing(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn, "Alice", "+18605550001", "alice@test.com")

        sms_client   = self._mock_sms()
        email_client = self._mock_email()

        stats = run(today=self.today, dry_run=True,
                    sms_client=sms_client, email_client=email_client)

        sms_client.messages.create.assert_not_called()
        email_client.send.assert_not_called()
        # dry_run counts as sent in stats
        self.assertEqual(stats["sms_sent"],   1)
        self.assertEqual(stats["email_sent"], 1)

    def test_no_games_returns_zero_stats(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_recipient(conn, "Alice", "+18605550001", "alice@test.com")
        stats = run(today=self.today)
        self.assertEqual(stats["games_checked"], 0)
        self.assertEqual(stats["alerts_sent"],   0)

    def test_no_recipients_returns_zero_stats(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
        stats = run(today=self.today)
        self.assertEqual(stats["alerts_sent"], 0)

    def test_tuesday_game_not_alerted(self):
        from alerts.main import run
        # today=Apr 7 (Wed), target=Apr 12 (Mon) — not a Fri/Sat/Sun
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-12", "Monday")
            insert_recipient(conn)
        stats = run(today=date(2026, 4, 7))
        self.assertEqual(stats["games_checked"], 0)

    def test_sms_failure_email_still_sends(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn, "Alice", "+18605550001", "alice@test.com")

        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                stats = run(
                    today=self.today,
                    sms_client=self._mock_sms(success=False),
                    email_client=self._mock_email(),
                )

        # Email still succeeds even when SMS fails
        self.assertEqual(stats["email_sent"], 1)
        self.assertEqual(stats["sms_failed"], 1)

    def test_phone_only_recipient_no_email_attempt(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn, "PhoneOnly", "+18605550001", None)

        email_client = self._mock_email()
        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                stats = run(today=self.today,
                            sms_client=self._mock_sms(),
                            email_client=email_client)

        email_client.send.assert_not_called()
        self.assertEqual(stats["sms_sent"], 1)

    def test_email_only_recipient_no_sms_attempt(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn, "EmailOnly", None, "email@test.com")

        sms_client = self._mock_sms()
        stats = run(today=self.today,
                    sms_client=sms_client,
                    email_client=self._mock_email())

        sms_client.messages.create.assert_not_called()
        self.assertEqual(stats["email_sent"], 1)

    def test_multiple_recipients_all_alerted(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            for i in range(5):
                insert_recipient(conn, f"Person{i}",
                                 f"+1860555{i:04d}", f"p{i}@test.com")

        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                stats = run(today=self.today,
                            sms_client=self._mock_sms(),
                            email_client=self._mock_email())

        self.assertEqual(stats["sms_sent"],   5)
        self.assertEqual(stats["email_sent"], 5)

    def test_stale_data_skips_all_alerts(self):
        from alerts.main import run
        with self.get_conn(self.db) as conn:
            # Insert stale game (3 days ago updated_at)
            conn.execute("""
                INSERT INTO games (game_date, day_of_week, start_time, opponent,
                                   is_home, ticket_url, updated_at)
                VALUES ('2026-04-10','Friday','7:05 PM','Sea Dogs',1,NULL,
                        datetime('now','-3 days'))
            """)
            insert_recipient(conn)

        sms_client = self._mock_sms()
        stats = run(today=self.today, sms_client=sms_client, email_client=self._mock_email())

        sms_client.messages.create.assert_not_called()
        self.assertEqual(stats["alerts_sent"], 0)

    def test_delivery_logged_to_db(self):
        from alerts.main import run
        from admin.db import get_alert_log
        with self.get_conn(self.db) as conn:
            insert_game(conn, "2026-04-10", "Friday")
            insert_recipient(conn)

        with patch("alerts.sms.time.sleep"):
            with patch.dict(os.environ, {"TWILIO_FROM_NUMBER": "+18605550000"}):
                run(today=self.today,
                    sms_client=self._mock_sms(),
                    email_client=self._mock_email())

        with self.get_conn(self.db) as conn:
            logs = get_alert_log(conn)
        # 1 SMS + 1 email = 2 log entries
        self.assertEqual(len(logs), 2)
        statuses = {l["status"] for l in logs}
        self.assertEqual(statuses, {"delivered"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
