"""
verify_all_11_indexes.py

Direct verification of the 8 Workforce migration indexes and 3 shared indexes against live PostgreSQL.
"""
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

TARGET_WORKFORCE_INDEXES = [
    ("workforce_notification", "idx_workforce_notification_recipient_created"),
    ("workforce_job_offer", "idx_workforcejoboffer_employee_status_expires"),
    ("workforce_job_offer", "idx_workforcejoboffer_job_employee"),
    ("workforce_job_lifecycle_event", "idx_workforcejob_lifecycle_job_emp_type"),
    ("workforce_work_extension", "idx_workforceworkextension_job_created"),
    ("workforce_job_payment", "idx_jobpayment_job_id"),
    ("workforce_employee_compliance", "idx_workforce_compliance_emp_req"),
    ("workforce_notification", "idx_workforce_notification_recipient_unread"),
]

TARGET_SHARED_INDEXES = [
    ("service_requests_servicerequest", "idx_sr_company_status_created"),
    ("service_requests_servicerequest", "idx_sr_assigned_employee_status"),
    ("employees_employee", "idx_employee_company_active"),
]

def verify():
    with connection.cursor() as cur:
        # DB Info
        cur.execute("""
            SELECT
                current_database(),
                pg_size_pretty(pg_database_size(current_database())),
                stats_reset
            FROM pg_stat_database
            WHERE datname = current_database();
        """)
        dbname, dbsize, stats_reset = cur.fetchone()
        print(f"DATABASE: {dbname} | TOTAL SIZE: {dbsize} | STATS RESET: {stats_reset}")
        print("=" * 110)

        # 1. Verify 8 Workforce indexes
        print("A. 8 WORKFORCE MIGRATION INDEXES (0014_performance_indexes):")
        print(f"{'Table':<32} {'Index Name':<45} {'Physical Existence':<20} {'Size':<12} {'idx_scan':<10} {'idx_tup_read':<12} {'idx_tup_fetch':<12}")
        print("-" * 145)
        for tbl, idx in TARGET_WORKFORCE_INDEXES:
            cur.execute("""
                SELECT
                    i.indexrelname,
                    pg_size_pretty(pg_relation_size(i.indexrelid)),
                    i.idx_scan,
                    i.idx_tup_read,
                    i.idx_tup_fetch
                FROM pg_stat_user_indexes i
                WHERE i.relname = %s AND i.indexrelname = %s;
            """, [tbl, idx])
            row = cur.fetchone()
            if row:
                print(f"{tbl:<32} {idx:<45} {'EXISTS (VERIFIED)':<20} {row[1]:<12} {row[2]:<10} {row[3]:<12} {row[4]:<12}")
            else:
                # Check pg_indexes in case pg_stat_user_indexes hasn't populated it
                cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = %s AND indexname = %s;", [tbl, idx])
                pg_idx = cur.fetchone()
                if pg_idx:
                    print(f"{tbl:<32} {idx:<45} {'EXISTS (pg_indexes)':<20} {'N/A':<12} {0:<10} {0:<12} {0:<12}")
                else:
                    print(f"{tbl:<32} {idx:<45} {'NOT FOUND':<20} {'N/A':<12} {'N/A':<10} {'N/A':<12} {'N/A':<12}")

        print("\n" + "=" * 110)
        # 2. Verify 3 Shared indexes
        print("B. 3 SHARED SUPABASE INDEXES (service_requests_servicerequest & employees_employee):")
        print(f"{'Table':<32} {'Index Name':<45} {'Physical Existence':<20} {'Size':<12} {'idx_scan':<10}")
        print("-" * 110)
        for tbl, idx in TARGET_SHARED_INDEXES:
            cur.execute("""
                SELECT
                    i.indexrelname,
                    pg_size_pretty(pg_relation_size(i.indexrelid)),
                    i.idx_scan
                FROM pg_stat_user_indexes i
                WHERE i.relname = %s AND i.indexrelname = %s;
            """, [tbl, idx])
            row = cur.fetchone()
            if row:
                print(f"{tbl:<32} {idx:<45} {'EXISTS (VERIFIED)':<20} {row[1]:<12} {row[2]:<10}")
            else:
                cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = %s AND indexname = %s;", [tbl, idx])
                pg_idx = cur.fetchone()
                if pg_idx:
                    print(f"{tbl:<32} {idx:<45} {'EXISTS (pg_indexes)':<20} {'N/A':<12} {0:<10}")
                else:
                    print(f"{tbl:<32} {idx:<45} {'NOT PRESENT':<20} {'N/A':<12} {'N/A':<10}")

        # Also list ALL existing indexes on the 2 shared tables so we know what is already indexed:
        print("\n" + "=" * 110)
        print("C. ALL EXISTING INDEXES ON SHARED TABLES:")
        for tbl in ["service_requests_servicerequest", "employees_employee"]:
            print(f"\nExisting indexes on {tbl}:")
            cur.execute("SELECT indexname, indexdef FROM pg_indexes WHERE tablename = %s ORDER BY indexname;", [tbl])
            for i_name, i_def in cur.fetchall():
                print(f"  • {i_name}: {i_def}")

if __name__ == "__main__":
    verify()
