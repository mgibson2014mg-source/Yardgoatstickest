"""
tests/test_admin.py — Admin CLI and Recipient Management tests.
Covers admin/manage.py and admin/db.py.
Run: python tests/test_admin.py
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from admin.db import (
    init_db, get_conn, add_recipient, list_recipients,
    deactivate_recipient, reactivate_recipient, get_data_freshness
)
from admin.manage import build_parser, cmd_add, cmd_list, cmd_remove, cmd_restore, cmd_status


def make_tmp_db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    os.environ["YARDGOATS_DB"] = tmp.name
    init_db(Path(tmp.name))
    return Path(tmp.name)


def teardown_tmp_db(path):
    if "YARDGOATS_DB" in os.environ:
        del os.environ["YARDGOATS_DB"]
    import gc
    gc.collect() # Force cleanup of any lingering connections
    # On Windows, we sometimes need to wait a tiny bit or force more collection
    import time
    time.sleep(0.1)
    path.unlink(missing_ok=True)


class TestRecipientLogic(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_add_recipient_success(self):
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Alice", "+18605550001", "alice@test.com")
            self.assertIsNotNone(rid)
            rows = list_recipients(conn, active_only=False)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "Alice")
        # Connection closed by context manager

    def test_add_recipient_requires_contact(self):
        with get_conn(self.db_path) as conn:
            with self.assertRaises(ValueError):
                add_recipient(conn, "NoContact", None, None)

    def test_deactivate_and_reactivate(self):
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Bob", "+18605550002", None)
            
            # Deactivate
            ok = deactivate_recipient(conn, rid)
            self.assertTrue(ok)
            active_rows = list_recipients(conn, active_only=True)
            self.assertEqual(len(active_rows), 0)
            
            # Reactivate
            ok = reactivate_recipient(conn, rid)
            self.assertTrue(ok)
            active_rows = list_recipients(conn, active_only=True)
            self.assertEqual(len(active_rows), 1)

    def test_deactivate_missing_id_returns_false(self):
        with get_conn(self.db_path) as conn:
            ok = deactivate_recipient(conn, 999)
            self.assertFalse(ok)

    def test_list_active_vs_all(self):
        with get_conn(self.db_path) as conn:
            r1 = add_recipient(conn, "Active", "+18605550001", None)
            r2 = add_recipient(conn, "Inactive", None, "test@test.com")
            deactivate_recipient(conn, r2)
            
            active = list_recipients(conn, active_only=True)
            all_r = list_recipients(conn, active_only=False)
            
            self.assertEqual(len(active), 1)
            self.assertEqual(len(all_r), 2)


class TestAdminCLI(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()
        self.parser = build_parser()

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_cli_add_recipient(self):
        args = self.parser.parse_args(["add", "--name", "Charlie", "--phone", "+18605550003"])
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cmd_add(args)
            self.assertIn("Added recipient", fake_out.getvalue())
        
        with get_conn(self.db_path) as conn:
            rows = list_recipients(conn)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["name"], "Charlie")

    def test_cli_add_fails_without_contact(self):
        args = self.parser.parse_args(["add", "--name", "NoContact"])
        with patch('sys.stdout', new=StringIO()) as fake_out:
            with self.assertRaises(SystemExit):
                cmd_add(args)
            self.assertIn("ERROR", fake_out.getvalue())

    def test_cli_list_recipients(self):
        with get_conn(self.db_path) as conn:
            add_recipient(conn, "Dave", "+18605550004", None)
        
        args = self.parser.parse_args(["list"])
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cmd_list(args)
            output = fake_out.getvalue()
            self.assertIn("Dave", output)
            self.assertIn("ID", output)

    def test_cli_remove_recipient(self):
        with get_conn(self.db_path) as conn:
            rid = add_recipient(conn, "Eve", "+18605550005", None)
        
        args = self.parser.parse_args(["remove", "--id", str(rid)])
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cmd_remove(args)
            self.assertIn("Deactivated recipient", fake_out.getvalue())
        
        with get_conn(self.db_path) as conn:
            self.assertEqual(len(list_recipients(conn, active_only=True)), 0)

    def test_cli_status(self):
        with get_conn(self.db_path) as conn:
            add_recipient(conn, "Frank", "+18605550006", None)
        
        args = self.parser.parse_args(["status"])
        with patch('sys.stdout', new=StringIO()) as fake_out:
            cmd_status(args)
            output = fake_out.getvalue()
            self.assertIn("Active recipients : 1", output)
            self.assertIn("Total recipients  : 1", output)


class TestDBTransactions(unittest.TestCase):
    def setUp(self):
        self.db_path = make_tmp_db()

    def tearDown(self):
        teardown_tmp_db(self.db_path)

    def test_transaction_rollback_on_error(self):
        from admin.db import get_conn
        
        try:
            with get_conn(self.db_path) as conn:
                add_recipient(conn, "WillFail", "+18605559999", None)
                raise RuntimeError("Force crash")
        except RuntimeError:
            pass
        
        with get_conn(self.db_path) as conn:
            rows = list_recipients(conn, active_only=False)
            self.assertEqual(len(rows), 0, "Transaction should have rolled back")

    def test_init_db_creates_tables(self):
        # Create a new empty db
        new_db = Path(tempfile.mktemp(suffix=".db"))
        try:
            init_db(new_db)
            with get_conn(new_db) as conn:
                # Check for games table
                row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='games'").fetchone()
                self.assertIsNotNone(row)
            # Connection closed by context manager
        finally:
            import gc
            gc.collect()
            import time
            time.sleep(0.1)
            new_db.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
