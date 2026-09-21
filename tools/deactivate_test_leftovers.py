#!/usr/bin/env python3
"""
tools/deactivate_test_leftovers.py

Reversible, non-destructive test leftover deactivator for the shared PostgreSQL database.
Performs strictly `is_active=False` updates without deleting any records or altering
companies, products, orders, or inventory.

Usage:
  # Dry-run categories only (default, safe, read-only)
  python tools/deactivate_test_leftovers.py

  # Dry-run categories and users
  python tools/deactivate_test_leftovers.py --include-users

  # Commit deactivation (creates automatic JSON backup in tools/backups/)
  python tools/deactivate_test_leftovers.py --commit
  python tools/deactivate_test_leftovers.py --include-users --commit

  # Revert / restore from a previous backup
  python tools/deactivate_test_leftovers.py --restore tools/backups/deactivated_<timestamp>.json
"""

import os
import sys
import json
import argparse
from datetime import datetime, timezone

# ── 1. Setup Django Environment ───────────────────────────────────────────────
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "vendor", "backend"))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Ensure SEVO_E2E_SQLITE_PATH is not set so we interact with PostgreSQL
if "SEVO_E2E_SQLITE_PATH" in os.environ:
    del os.environ["SEVO_E2E_SQLITE_PATH"]

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.db import connection, transaction
from django.contrib.auth import get_user_model
from companies.models import Company
from workforce_api.models import SellerHubCategory

User = get_user_model()

# ── 2. Guard Constants & Regular Expressions ───────────────────────────────────
CATEGORY_TIGHT_REGEX = r"^(groceries|oils)-[0-9a-f]{6}$"
USER_PATTERN_REGEX = r"^(seller_orders_a_|seller_orders_b_|orders_superadmin_)[0-9a-f]{6}$"
COMPANY_TIGHT_REGEX = r"^(organic-farms|daily-fresh)-[0-9a-f]{6}$"
LEGACY_USERNAMES = ["seller_orders_a", "seller_orders_b"]
LEGACY_COMPANY_IDS = [1308, 1309]

BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "backups"))


def print_db_banner():
    settings_dict = connection.settings_dict
    db_host = settings_dict.get("HOST") or "localhost"
    db_name = settings_dict.get("NAME") or "unknown"
    db_engine = settings_dict.get("ENGINE", "").split(".")[-1]
    print("=" * 80)
    print(f"DATABASE TARGET: {db_engine.upper()} @ {db_host} | DATABASE: {db_name}")
    print("=" * 80)


def restore_backup(backup_path):
    print_db_banner()
    if not os.path.exists(backup_path):
        print(f"[-] ERROR: Backup file not found: {backup_path}")
        sys.exit(1)

    with open(backup_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[*] Restoring from backup file: {backup_path}")
    print(f"[*] Timestamp: {data.get('timestamp')}")
    
    categories = data.get("categories", [])
    users = data.get("users", [])
    print(f"[*] Categories to restore: {len(categories)}")
    print(f"[*] Users to restore: {len(users)}")

    with transaction.atomic():
        restored_cats = 0
        for item in categories:
            cat_id = item["id"]
            prev_status = item.get("previous_is_active", True)
            updated = SellerHubCategory.objects.filter(id=cat_id).update(is_active=prev_status)
            restored_cats += updated

        restored_users = 0
        for item in users:
            user_id = item["id"]
            prev_status = item.get("previous_is_active", True)
            updated = User.objects.filter(id=user_id).update(is_active=prev_status)
            restored_users += updated

    print(f"[+] RESTORE SUCCESSFUL: Restored {restored_cats} categories and {restored_users} users.")


def main():
    parser = argparse.ArgumentParser(description="Reversible test leftover deactivation tool.")
    parser.add_argument("--commit", action="store_true", help="Apply updates to database. Defaults to dry-run.")
    parser.add_argument("--include-users", action="store_true", help="Include test users in deactivation.")
    parser.add_argument("--expect-categories", type=int, default=260, help="Expected matching active test categories (default: 260).")
    parser.add_argument("--expect-users", type=int, default=512, help="Expected matching active test users (default: 512).")
    parser.add_argument("--restore", type=str, help="Restore previously deactivated records from a backup JSON file.")

    args = parser.parse_args()

    if args.restore:
        restore_backup(args.restore)
        return

    print_db_banner()
    is_commit = args.commit
    print(f"MODE: {'*** COMMIT (WRITES ENABLED) ***' if is_commit else 'DRY RUN (READ ONLY - NO CHANGES)'}\n")

    # ─────────────────────────────────────────────────────────────────────────
    # A. Target Categories Evaluation
    # ─────────────────────────────────────────────────────────────────────────
    cat_qs = SellerHubCategory.objects.filter(
        slug__regex=CATEGORY_TIGHT_REGEX,
        is_active=True
    ).order_by("id")
    cat_count = cat_qs.count()

    print(f"[*] Target Categories Search (pattern: {CATEGORY_TIGHT_REGEX}, is_active=True):")
    print(f"    Found active matching test categories: {cat_count}")

    # Guard: Check against expected count
    if cat_count != args.expect_categories:
        print(f"[-] ABORT: Expected {args.expect_categories} categories but found {cat_count}.")
        sys.exit(1)

    # Safety Guard: Ensure 0 platform / marketplace mkt-* categories are matched
    mkt_overlap = SellerHubCategory.objects.filter(slug__startswith="mkt-", slug__regex=CATEGORY_TIGHT_REGEX).count()
    if mkt_overlap > 0:
        print(f"[-] CRITICAL GUARD VIOLATION: Matched {mkt_overlap} mkt-* marketplace categories. Aborting!")
        sys.exit(1)

    cat_list = list(cat_qs.values("id", "slug", "name", "is_active", "parent_id"))
    print(f"    Sample category IDs to deactivate: {[c['id'] for c in cat_list[:8]]} ... (total: {len(cat_list)})")

    # ─────────────────────────────────────────────────────────────────────────
    # B. Target Users Evaluation (if requested)
    # ─────────────────────────────────────────────────────────────────────────
    user_list = []
    user_qs = User.objects.none()
    if args.include_users:
        pattern_users_qs = User.objects.filter(
            username__regex=USER_PATTERN_REGEX,
            is_active=True
        )
        legacy_users_qs = User.objects.filter(
            username__in=LEGACY_USERNAMES,
            company_id__in=LEGACY_COMPANY_IDS,
            is_active=True
        )
        user_qs = (pattern_users_qs | legacy_users_qs).distinct().order_by("id")
        user_count = user_qs.count()

        print(f"\n[*] Target Users Search (--include-users enabled):")
        print(f"    Pattern: {USER_PATTERN_REGEX} + Legacy: {LEGACY_USERNAMES}")
        print(f"    Found active matching test users: {user_count}")

        # Guard: Check against expected count
        if user_count != args.expect_users:
            print(f"[-] ABORT: Expected {args.expect_users} users but found {user_count}.")
            sys.exit(1)

        # Strict User Safety Guards
        superusers = user_qs.filter(is_superuser=True).count()
        staff_users = user_qs.filter(is_staff=True).count()
        regular_users = user_qs.filter(is_superuser=False, is_staff=False).count()

        print(f"    User Breakdown -> Superusers: {superusers}, Staff: {staff_users}, Regular Sellers: {regular_users}")

        # Verify no user belongs to company_id == 1
        comp1_users = user_qs.filter(company_id=1).count()
        if comp1_users > 0:
            print(f"[-] CRITICAL GUARD VIOLATION: {comp1_users} users belong to company_id=1. Aborting!")
            sys.exit(1)

        # Verify all superusers strictly match orders_superadmin_ pattern
        invalid_superusers = user_qs.filter(is_superuser=True).exclude(username__regex=r"^orders_superadmin_[0-9a-f]{6}$").count()
        if invalid_superusers > 0:
            print(f"[-] CRITICAL GUARD VIOLATION: {invalid_superusers} superusers do not match test superadmin pattern. Aborting!")
            sys.exit(1)

        user_list = list(user_qs.values("id", "username", "email", "company_id", "is_active", "is_superuser", "is_staff"))
        print(f"    Sample user IDs to deactivate: {[u['id'] for u in user_list[:8]]} ... (total: {len(user_list)})")

    # ─────────────────────────────────────────────────────────────────────────
    # C. Execution / Commit / Backup
    # ─────────────────────────────────────────────────────────────────────────
    if not is_commit:
        print("\n" + "=" * 80)
        print("[+] DRY RUN COMPLETED SUCCESSFULLY: All checks and guards passed.")
        print(f"    - Categories ready to deactivate: {len(cat_list)}")
        print(f"    - Users ready to deactivate:      {len(user_list)}")
        print("    No database modifications were made.")
        print("    To apply deactivation, run with --commit.")
        print("=" * 80)
        return

    # Commit execution
    utc_now = datetime.now(timezone.utc)
    ts_str = utc_now.strftime("%Y%m%d_%H%M%S")
    os.makedirs(BACKUP_DIR, exist_ok=True)
    backup_file = os.path.join(BACKUP_DIR, f"deactivated_{ts_str}.json")

    backup_payload = {
        "timestamp": utc_now.isoformat(),
        "database": connection.settings_dict.get("NAME"),
        "host": connection.settings_dict.get("HOST"),
        "categories": [
            {
                "id": c["id"],
                "slug": c["slug"],
                "name": c["name"],
                "previous_is_active": c["is_active"],
            }
            for c in cat_list
        ],
        "users": [
            {
                "id": u["id"],
                "username": u["username"],
                "company_id": u["company_id"],
                "previous_is_active": u["is_active"],
            }
            for u in user_list
        ],
    }

    with open(backup_file, "w", encoding="utf-8") as f:
        json.dump(backup_payload, f, indent=2)

    print(f"\n[+] Created backup checkpoint: {backup_file}")

    with transaction.atomic():
        updated_cats = cat_qs.update(is_active=False)
        updated_users = 0
        if args.include_users and user_qs.exists():
            updated_users = user_qs.update(is_active=False)

    print("\n" + "=" * 80)
    print(f"[+] COMMIT SUCCESSFUL: Deactivated {updated_cats} categories and {updated_users} users.")
    print(f"[+] Backup file: {backup_file}")
    print(f"[+] To restore, run: python tools/deactivate_test_leftovers.py --restore {backup_file}")
    print("=" * 80)


if __name__ == "__main__":
    main()
