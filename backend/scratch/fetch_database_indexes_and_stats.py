"""
fetch_database_indexes_and_stats.py

Database Telemetry & Index Verification Suite for CalTrack Workforce.

Queries PostgreSQL catalog views directly for:
1. Cumulative index scans (idx_scan) since PostgreSQL statistics reset
2. Actual index byte sizes (pg_relation_size)
3. Buffer cache hit ratio (pg_statio_user_indexes)
4. Table disk storage (pg_stat_user_tables)
5. Statistics reset timestamp (pg_stat_database.stats_reset)
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


def fetch_database_telemetry():
    print("=" * 95)
    print(" CALTRACK WORKFORCE & SUPABASE — DATABASE TELEMETRY & INDEX VERIFICATION")
    print("=" * 95)

    db_engine = connection.vendor
    print(f"Connected Database Engine: {db_engine.upper()}")

    if db_engine == "postgresql":
        with connection.cursor() as cur:
            # 0. Database statistics reset timestamp
            cur.execute("""
                SELECT
                    stats_reset,
                    pg_size_pretty(pg_database_size(current_database()))
                FROM pg_stat_database
                WHERE datname = current_database();
            """)
            db_row = cur.fetchone()
            stats_reset = db_row[0] if db_row else "Unknown"
            db_size = db_row[1] if db_row else "Unknown"
            print(f"Database Name             : {connection.settings_dict.get('NAME')}")
            print(f"Total Database Size       : {db_size}")
            print(f"Statistics Reset Timestamp: {stats_reset}")
            print("Note: 'Cumulative Scans' reflects index usage since the above timestamp (not API count).")

            # 1. Fetch user indexes with actual sizes and cumulative scans
            cur.execute("""
                SELECT
                    schemaname,
                    relname AS table_name,
                    indexrelname AS index_name,
                    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
                    pg_size_pretty(pg_total_relation_size(relid)) AS total_table_size,
                    idx_scan AS cumulative_scans,
                    idx_tup_read AS tuples_read,
                    idx_tup_fetch AS tuples_fetched
                FROM pg_stat_user_indexes
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC, relname ASC;
            """)
            indexes = cur.fetchall()

            print(f"\n[1] ACTIVE INDEXES ({len(indexes)} Total Indexes in public schema):")
            print("-" * 95)
            print(f"{'Table':<32} {'Index Name':<35} {'Index Size':<12} {'Cumul. Scans':<14}")
            print("-" * 95)
            for idx in indexes:
                schema, table, index_name, idx_size, tbl_size, scans, tup_read, tup_fetch = idx
                print(f"{table[:30]:<32} {index_name[:33]:<35} {idx_size:<12} {scans or 0:<14}")

            # 2. Buffer Cache Hit Ratio
            cur.execute("""
                SELECT
                    sum(idx_blks_hit) AS hits,
                    sum(idx_blks_read) AS reads,
                    ROUND(100.0 * sum(idx_blks_hit) / NULLIF(sum(idx_blks_hit) + sum(idx_blks_read), 0), 2) AS hit_ratio
                FROM pg_statio_user_indexes;
            """)
            cache_stats = cur.fetchone()
            hits, reads, hit_ratio = cache_stats
            print("\n[2] DATABASE BUFFER CACHE I/O:")
            print("-" * 95)
            print(f"Index Buffer Cache Hits : {hits or 0:,}")
            print(f"Index Disk Blocks Read  : {reads or 0:,}")
            print(f"Buffer Cache Hit Ratio  : {hit_ratio if hit_ratio is not None else 100.0}%")

            # 3. Table Disk Storage Breakdown
            cur.execute("""
                SELECT
                    relname AS table_name,
                    pg_size_pretty(pg_relation_size(relid)) AS data_size,
                    pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size,
                    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY pg_total_relation_size(relid) DESC
                LIMIT 15;
            """)
            tables = cur.fetchall()
            print("\n[3] TABLE DISK STORAGE (Top 15 Tables):")
            print("-" * 95)
            print(f"{'Table Name':<35} {'Data Size':<15} {'Index Size':<15} {'Total Size':<15}")
            print("-" * 95)
            for tbl in tables:
                t_name, d_size, i_size, tot_size = tbl
                print(f"{t_name[:33]:<35} {d_size:<15} {i_size:<15} {tot_size:<15}")

    else:
        # SQLite fallback
        with connection.cursor() as cur:
            cur.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL;")
            indexes = cur.fetchall()
            print(f"\n[1] ACTIVE INDEXES ({len(indexes)} Total Indexes in SQLite schema):")
            print("-" * 95)
            for idx in indexes:
                name, tbl = idx
                print(f"- {name} on {tbl}")
        print("\nNote: PostgreSQL I/O buffer statistics require a PostgreSQL connection.")

    print("=" * 95)


if __name__ == "__main__":
    fetch_database_telemetry()
