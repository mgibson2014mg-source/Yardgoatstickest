#!/usr/bin/env python3
"""
tests/run_tests.py — Self-contained test runner (no pytest required).
Uses Python stdlib unittest only.
Run: python tests/run_tests.py
"""
import os
import sys
import tempfile
import unittest
import sqlite3
from pathlib import Path
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))


def make_tmp_db():
    """Create a fresh temp DB, set env var, return path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["YARDGOATS_DB"] = tmp.name
    from admin.db import init_db
    init_db(Path(tmp.name))
    return Path(tmp.name)


def teardown_tmp_db(path):
    del os.environ["YARDGOATS_DB"]
    try:
        path.unlink()
    except Exception:
        pass


SAMPLE_GAME = {
    "game_date": "2026-04-10",
    "day_of_week": "Friday",
    "start_time": "7:05 PM",
    "opponent": "Portland Sea Dogs",
    "is_home": 1,
    "ticket_url": "https://milb.com/hartford/tickets",
}


# ══════════════════════════════════════════════════════════
# SCHEMA TESTS
# ══════════════════════════════════════════════════════════
class TestSchemaInit(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()
        from admin.db import get_conn
        self._get_conn = get_conn

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_all_tables_created(self):
        with self._get_conn(self.db_path) as conn:
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}
        self.assertIn("games", tables)
        self.assertIn("promotions", tables)
        self.assertIn("recipients", tables)
        self.assertIn("alerts_sent", tables)

    def test_indexes_created(self):
        with self._get_conn(self.db_path) as conn:
            indexes = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='index'"
            ).fetchall()}
        self.assertIn("idx_games_date", indexes)
        self.assertIn("idx_games_dow", indexes)

    def test_init_is_idempotent(self):
        from admin.db import init_db
        init_db(self.db_path)
        init_db(self.db_path)  # should not raise

    def test_foreign_keys_enabled(self):
        with self._get_conn(self.db_path) as conn:
            result = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        self.assertEqual(result, 1)


# ══════════════════════════════════════════════════════════
# GAME HELPER TESTS
# ══════════════════════════════════════════════════════════
class TestGameHelpers(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()
        from admin.db import get_conn, upsert_game, get_games_on_date, \
            get_weekend_games_on_date, get_data_freshness
        self.get_conn = get_conn
        self.upsert_game = upsert_game
        self.get_games_on_date = get_games_on_date
        self.get_weekend_games_on_date = get_weekend_games_on_date
        self.get_data_freshness = get_data_freshness

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_upsert_inserts_new_game(self):
        with self.get_conn(self.db_path) as conn:
            gid = self.upsert_game(conn, SAMPLE_GAME)
        self.assertIsInstance(gid, int)
        self.assertGreater(gid, 0)

    def test_upsert_updates_existing_game(self):
        with self.get_conn(self.db_path) as conn:
            gid1 = self.upsert_game(conn, SAMPLE_GAME)
            updated = {**SAMPLE_GAME, "opponent": "New Hampshire Fisher Cats"}
            gid2 = self.upsert_game(conn, updated)
            self.assertEqual(gid1, gid2)
            row = conn.execute("SELECT opponent FROM games WHERE id=?", (gid1,)).fetchone()
        self.assertEqual(row["opponent"], "New Hampshire Fisher Cats")

    def test_get_games_on_date_home_only(self):
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, SAMPLE_GAME)
            results = self.get_games_on_date(conn, "2026-04-10")
        self.assertEqual(len(results), 1)

    def test_get_games_excludes_away(self):
        away = {**SAMPLE_GAME, "game_date": "2026-04-11", "is_home": 0}
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, away)
            results = self.get_games_on_date(conn, "2026-04-11")
        self.assertEqual(len(results), 0)

    def test_weekend_includes_friday(self):
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, SAMPLE_GAME)
            results = self.get_weekend_games_on_date(conn, "2026-04-10")
        self.assertEqual(len(results), 1)

    def test_weekend_includes_saturday(self):
        sat = {**SAMPLE_GAME, "game_date": "2026-04-11", "day_of_week": "Saturday"}
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, sat)
            results = self.get_weekend_games_on_date(conn, "2026-04-11")
        self.assertEqual(len(results), 1)

    def test_weekend_includes_sunday(self):
        sun = {**SAMPLE_GAME, "game_date": "2026-04-12", "day_of_week": "Sunday"}
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, sun)
            results = self.get_weekend_games_on_date(conn, "2026-04-12")
        self.assertEqual(len(results), 1)

    def test_weekend_excludes_wednesday(self):
        wed = {**SAMPLE_GAME, "game_date": "2026-04-08", "day_of_week": "Wednesday"}
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, wed)
            results = self.get_weekend_games_on_date(conn, "2026-04-08")
        self.assertEqual(len(results), 0)

    def test_data_freshness_none_when_empty(self):
        with self.get_conn(self.db_path) as conn:
            ts = self.get_data_freshness(conn)
        self.assertIsNone(ts)

    def test_data_freshness_after_insert(self):
        with self.get_conn(self.db_path) as conn:
            self.upsert_game(conn, SAMPLE_GAME)
            ts = self.get_data_freshness(conn)
        self.assertIsNotNone(ts)


# ══════════════════════════════════════════════════════════
# PROMOTION TESTS
# ══════════════════════════════════════════════════════════
class TestPromotionHelpers(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()
        from admin.db import get_conn, upsert_game, upsert_promotions, get_promotions_for_game
        self.get_conn = get_conn
        self.upsert_game = upsert_game
        self.upsert_promotions = upsert_promotions
        self.get_promotions_for_game = get_promotions_for_game
        with self.get_conn(self.db_path) as conn:
            self.gid = self.upsert_game(conn, SAMPLE_GAME)

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_insert_two_promos(self):
        with self.get_conn(self.db_path) as conn:
            self.upsert_promotions(conn, self.gid, [
                {"promo_type": "giveaway",  "description": "Paddle"},
                {"promo_type": "fireworks", "description": "Post-game"},
            ])
            promos = self.get_promotions_for_game(conn, self.gid)
        self.assertEqual(len(promos), 2)

    def test_upsert_replaces_existing(self):
        with self.get_conn(self.db_path) as conn:
            self.upsert_promotions(conn, self.gid, [{"promo_type": "giveaway", "description": "Old"}])
            self.upsert_promotions(conn, self.gid, [{"promo_type": "discount", "description": "New"}])
            promos = self.get_promotions_for_game(conn, self.gid)
        self.assertEqual(len(promos), 1)
        self.assertEqual(promos[0]["promo_type"], "discount")

    def test_empty_list_clears_promos(self):
        with self.get_conn(self.db_path) as conn:
            self.upsert_promotions(conn, self.gid, [{"promo_type": "giveaway", "description": "X"}])
            self.upsert_promotions(conn, self.gid, [])
            promos = self.get_promotions_for_game(conn, self.gid)
        self.assertEqual(promos, [])

    def test_invalid_promo_type_raises(self):
        with self.get_conn(self.db_path) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                self.upsert_promotions(conn, self.gid, [{"promo_type": "INVALID", "description": "X"}])

    def test_valid_promo_types(self):
        valid = ["giveaway", "fireworks", "discount", "theme", "heritage", "special"]
        with self.get_conn(self.db_path) as conn:
            for pt in valid:
                self.upsert_promotions(conn, self.gid, [{"promo_type": pt, "description": "test"}])
                promos = self.get_promotions_for_game(conn, self.gid)
                self.assertEqual(promos[0]["promo_type"], pt)


# ══════════════════════════════════════════════════════════
# RECIPIENT TESTS
# ══════════════════════════════════════════════════════════
class TestRecipientHelpers(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()
        from admin.db import get_conn, add_recipient, list_recipients, \
            deactivate_recipient, reactivate_recipient
        self.get_conn = get_conn
        self.add_recipient = add_recipient
        self.list_recipients = list_recipients
        self.deactivate_recipient = deactivate_recipient
        self.reactivate_recipient = reactivate_recipient

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_add_with_both_channels(self):
        with self.get_conn(self.db_path) as conn:
            self.add_recipient(conn, "Alice", "+18601111111", "alice@test.com")
            rows = self.list_recipients(conn)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["name"], "Alice")

    def test_add_phone_only(self):
        with self.get_conn(self.db_path) as conn:
            self.add_recipient(conn, "Bob", "+18602222222", None)
            rows = self.list_recipients(conn)
        self.assertIsNone(rows[0]["email"])

    def test_add_email_only(self):
        with self.get_conn(self.db_path) as conn:
            self.add_recipient(conn, "Carol", None, "carol@test.com")
            rows = self.list_recipients(conn)
        self.assertIsNone(rows[0]["phone"])

    def test_no_contact_raises_value_error(self):
        with self.get_conn(self.db_path) as conn:
            with self.assertRaises(ValueError):
                self.add_recipient(conn, "Ghost", None, None)

    def test_active_only_filter(self):
        with self.get_conn(self.db_path) as conn:
            self.add_recipient(conn, "Active", "+1111", None)
            rid = self.add_recipient(conn, "Inactive", "+2222", None)
            self.deactivate_recipient(conn, rid)
            active = self.list_recipients(conn, active_only=True)
        self.assertEqual(len(active), 1)
        self.assertEqual(active[0]["name"], "Active")

    def test_list_all_includes_inactive(self):
        with self.get_conn(self.db_path) as conn:
            self.add_recipient(conn, "Active", "+1111", None)
            rid = self.add_recipient(conn, "Inactive", "+2222", None)
            self.deactivate_recipient(conn, rid)
            all_r = self.list_recipients(conn, active_only=False)
        self.assertEqual(len(all_r), 2)

    def test_deactivate_success(self):
        with self.get_conn(self.db_path) as conn:
            rid = self.add_recipient(conn, "Dave", "+3333", None)
            ok = self.deactivate_recipient(conn, rid)
            active = self.list_recipients(conn, active_only=True)
        self.assertTrue(ok)
        self.assertEqual(len(active), 0)

    def test_deactivate_nonexistent_returns_false(self):
        with self.get_conn(self.db_path) as conn:
            ok = self.deactivate_recipient(conn, 9999)
        self.assertFalse(ok)

    def test_reactivate_success(self):
        with self.get_conn(self.db_path) as conn:
            rid = self.add_recipient(conn, "Eve", "+4444", None)
            self.deactivate_recipient(conn, rid)
            ok = self.reactivate_recipient(conn, rid)
            active = self.list_recipients(conn, active_only=True)
        self.assertTrue(ok)
        self.assertEqual(len(active), 1)

    def test_supports_up_to_ten_recipients(self):
        """FR-34: system supports 1-10 recipients."""
        with self.get_conn(self.db_path) as conn:
            for i in range(10):
                self.add_recipient(conn, f"Person{i}", f"+1800{i:07d}", None)
            rows = self.list_recipients(conn)
        self.assertEqual(len(rows), 10)


# ══════════════════════════════════════════════════════════
# ALERT DEDUPLICATION TESTS
# ══════════════════════════════════════════════════════════
class TestAlertHelpers(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()
        from admin.db import get_conn, upsert_game, add_recipient, \
            log_alert, has_alert_been_sent, get_alert_log
        self.get_conn = get_conn
        self.log_alert = log_alert
        self.has_alert_been_sent = has_alert_been_sent
        self.get_alert_log = get_alert_log
        with self.get_conn(self.db_path) as conn:
            self.gid = upsert_game(conn, SAMPLE_GAME)
            self.rid = add_recipient(conn, "Alice", "+18001234567", "alice@test.com")

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_not_sent_initially(self):
        with self.get_conn(self.db_path) as conn:
            result = self.has_alert_been_sent(conn, self.gid, self.rid, "sms")
        self.assertFalse(result)

    def test_sent_after_log(self):
        with self.get_conn(self.db_path) as conn:
            self.log_alert(conn, self.gid, self.rid, "sms", "delivered")
            result = self.has_alert_been_sent(conn, self.gid, self.rid, "sms")
        self.assertTrue(result)

    def test_sms_and_email_independent(self):
        with self.get_conn(self.db_path) as conn:
            self.log_alert(conn, self.gid, self.rid, "sms", "delivered")
            email_sent = self.has_alert_been_sent(conn, self.gid, self.rid, "email")
        self.assertFalse(email_sent)

    def test_duplicate_log_upserts_status(self):
        with self.get_conn(self.db_path) as conn:
            self.log_alert(conn, self.gid, self.rid, "sms", "pending")
            self.log_alert(conn, self.gid, self.rid, "sms", "delivered")
            logs = self.get_alert_log(conn, self.gid)
        sms = [l for l in logs if l["channel"] == "sms"]
        self.assertEqual(len(sms), 1)
        self.assertEqual(sms[0]["status"], "delivered")

    def test_get_alert_log_filtered_by_game(self):
        from admin.db import upsert_game
        with self.get_conn(self.db_path) as conn:
            gid2 = upsert_game(conn, {
                **SAMPLE_GAME, "game_date": "2026-04-11", "day_of_week": "Saturday"
            })
            self.log_alert(conn, self.gid,  self.rid, "sms",   "delivered")
            self.log_alert(conn, gid2,       self.rid, "email", "delivered")
            logs = self.get_alert_log(conn, self.gid)
        self.assertEqual(len(logs), 1)

    def test_get_alert_log_all(self):
        from admin.db import upsert_game
        with self.get_conn(self.db_path) as conn:
            gid2 = upsert_game(conn, {
                **SAMPLE_GAME, "game_date": "2026-04-11", "day_of_week": "Saturday"
            })
            self.log_alert(conn, self.gid,  self.rid, "sms",   "delivered")
            self.log_alert(conn, gid2,       self.rid, "email", "delivered")
            logs = self.get_alert_log(conn)
        self.assertEqual(len(logs), 2)


# ══════════════════════════════════════════════════════════
# ADMIN CLI TESTS
# ══════════════════════════════════════════════════════════
class TestAdminCLI(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def _run(self, argv):
        from admin.manage import main
        with patch("sys.argv", ["manage.py"] + argv):
            with patch("sys.stdout", new_callable=StringIO) as mock_out:
                try:
                    main()
                except SystemExit as e:
                    return mock_out.getvalue(), e.code
                return mock_out.getvalue(), 0

    def test_add_and_list(self):
        out, code = self._run(["add", "--name", "Frank", "--phone", "+18605559999"])
        self.assertEqual(code, 0)
        self.assertIn("Added", out)
        self.assertIn("Frank", out)

        out, code = self._run(["list"])
        self.assertIn("Frank", out)

    def test_add_requires_phone_or_email(self):
        out, code = self._run(["add", "--name", "Ghost"])
        self.assertNotEqual(code, 0)

    def test_remove_deactivates(self):
        from admin.db import get_conn, add_recipient
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Hank", "+18885550001", None)
        out, code = self._run(["remove", "--id", str(rid)])
        self.assertEqual(code, 0)
        self.assertIn("Deactivated", out)

    def test_restore_reactivates(self):
        from admin.db import get_conn, add_recipient, deactivate_recipient
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Iris", "+18885550002", None)
            deactivate_recipient(conn, rid)
        out, code = self._run(["restore", "--id", str(rid)])
        self.assertEqual(code, 0)
        self.assertIn("Restored", out)

    def test_remove_nonexistent_exits_nonzero(self):
        out, code = self._run(["remove", "--id", "9999"])
        self.assertNotEqual(code, 0)

    def test_status_shows_summary(self):
        out, code = self._run(["status"])
        self.assertEqual(code, 0)
        self.assertIn("Active recipients", out)
        self.assertIn("Last data refresh", out)

    def test_list_all_shows_inactive(self):
        from admin.db import get_conn, add_recipient, deactivate_recipient
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Ivy", "+19995550001", None)
            deactivate_recipient(conn, rid)
        out, code = self._run(["list", "--all"])
        self.assertIn("Ivy", out)

    def test_list_active_hides_inactive(self):
        from admin.db import get_conn, add_recipient, deactivate_recipient
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Jack", "+19995550002", None)
            deactivate_recipient(conn, rid)
        out, code = self._run(["list"])
        self.assertNotIn("Jack", out)


# ══════════════════════════════════════════════════════════
# RUNNER
# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [
        TestSchemaInit,
        TestGameHelpers,
        TestPromotionHelpers,
        TestRecipientHelpers,
        TestAlertHelpers,
        TestAdminCLI,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
