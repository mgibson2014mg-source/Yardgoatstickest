#!/usr/bin/env python3
"""
admin/manage.py — Recipient management CLI.

Usage:
  python manage.py add    --name "Jane" --phone "+18605551234" --email "jane@example.com"
  python manage.py list   [--all]
  python manage.py remove --id 3
  python manage.py restore --id 3
  python manage.py status
"""
import argparse
import sys
from pathlib import Path

# Allow running from any directory
sys.path.insert(0, str(Path(__file__).parent.parent))
from admin.db import get_conn, init_db, add_recipient, list_recipients, \
    deactivate_recipient, reactivate_recipient, get_data_freshness


def cmd_add(args):
    if not args.phone and not args.email:
        print("ERROR: Provide at least --phone or --email.")
        sys.exit(1)
    with get_conn() as conn:
        rid = add_recipient(conn, args.name, args.phone, args.email)
    print(f"✅ Added recipient id={rid}  name='{args.name}'  phone={args.phone or '—'}  email={args.email or '—'}")


def cmd_list(args):
    with get_conn() as conn:
        rows = list_recipients(conn, active_only=not args.all)
    if not rows:
        print("No recipients found.")
        return
    print(f"\n{'ID':<5} {'Name':<20} {'Phone':<16} {'Email':<30} {'Active'}")
    print("─" * 80)
    for r in rows:
        print(f"{r['id']:<5} {r['name']:<20} {r['phone'] or '—':<16} {r['email'] or '—':<30} {'✅' if r['active'] else '❌'}")
    print()


def cmd_remove(args):
    with get_conn() as conn:
        ok = deactivate_recipient(conn, args.id)
    if ok:
        print(f"✅ Deactivated recipient id={args.id}  (record kept for audit; use 'restore' to re-enable)")
    else:
        print(f"ERROR: No recipient found with id={args.id}")
        sys.exit(1)


def cmd_restore(args):
    with get_conn() as conn:
        ok = reactivate_recipient(conn, args.id)
    if ok:
        print(f"✅ Restored recipient id={args.id}")
    else:
        print(f"ERROR: No recipient found with id={args.id}")
        sys.exit(1)


def cmd_status(args):
    with get_conn() as conn:
        active = list_recipients(conn, active_only=True)
        all_r  = list_recipients(conn, active_only=False)
        freshness = get_data_freshness(conn)
    print("\n── Yard Goats Tracker Status ──────────────────")
    print(f"  Active recipients : {len(active)}")
    print(f"  Total recipients  : {len(all_r)}")
    print(f"  Last data refresh : {freshness or 'No data yet'}")
    print("───────────────────────────────────────────────\n")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="manage.py",
        description="Yard Goats Tracker — Admin CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # add
    p_add = sub.add_parser("add", help="Add a recipient")
    p_add.add_argument("--name",  required=True, help="Recipient display name")
    p_add.add_argument("--phone", default=None,  help="E.164 phone number e.g. +18605551234")
    p_add.add_argument("--email", default=None,  help="Email address")

    # list
    p_list = sub.add_parser("list", help="List recipients")
    p_list.add_argument("--all", action="store_true", help="Include inactive recipients")

    # remove
    p_remove = sub.add_parser("remove", help="Deactivate a recipient (soft delete)")
    p_remove.add_argument("--id", type=int, required=True, help="Recipient id")

    # restore
    p_restore = sub.add_parser("restore", help="Re-activate a deactivated recipient")
    p_restore.add_argument("--id", type=int, required=True, help="Recipient id")

    # status
    sub.add_parser("status", help="Show system status summary")

    return parser


def main():
    init_db()
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "add":     cmd_add,
        "list":    cmd_list,
        "remove":  cmd_remove,
        "restore": cmd_restore,
        "status":  cmd_status,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
