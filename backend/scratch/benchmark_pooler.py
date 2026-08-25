"""
benchmark_pooler.py - SAFETY GUARD REQUIRED

This script connects directly to Supabase PostgreSQL.
It will REFUSE to run unless ALLOW_REMOTE_STRESS_TEST=true is set explicitly.

Usage:
  $env:DB_USER = "postgres.yourproject"
  $env:DB_PASSWORD = "yourpassword"
  $env:DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
  $env:ALLOW_REMOTE_STRESS_TEST = "true"
  python benchmark_pooler.py
"""
import os
import psycopg2
import threading
import time

# PRODUCTION SAFETY GUARD - must be explicitly set to run
_allow = os.environ.get("ALLOW_REMOTE_STRESS_TEST", "").strip().lower()
if _allow != "true":
    print("\n[BLOCKED] benchmark_pooler.py targets live Supabase PostgreSQL.")
    print("To authorise: set ALLOW_REMOTE_STRESS_TEST=true")
    print("NEVER run this in production without explicit approval.\n")
    raise SystemExit(1)

# Credentials from environment only - NEVER hardcode these
_DB_NAME = os.environ.get("DB_NAME", "postgres")
_DB_USER = os.environ.get("DB_USER", "")
_DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
_DB_HOST = os.environ.get("DB_HOST", "")

if not _DB_USER or not _DB_PASSWORD or not _DB_HOST:
    print("\n[ERROR] Missing DB_USER, DB_PASSWORD, or DB_HOST environment variables.")
    raise SystemExit(1)


def test_concurrent(port, n_threads=30):
    results = []
    def worker(i):
        try:
            conn = psycopg2.connect(
                dbname=_DB_NAME, user=_DB_USER, password=_DB_PASSWORD,
                host=_DB_HOST, port=port, sslmode="require"
            )
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM accounts_user;")
                res = cur.fetchone()
            conn.close()
            results.append((i, True, res))
        except Exception as e:
            results.append((i, False, str(e)))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    t0 = time.time()
    for t in threads: t.start()
    for t in threads: t.join()
    t1 = time.time()

    successes = sum(1 for r in results if r[1])
    failures = sum(1 for r in results if not r[1])
    print(f"\n--- Port {port} with {n_threads} concurrent threads ({int((t1-t0)*1000)}ms) ---")
    print(f"Successes: {successes}, Failures: {failures}")
    if failures > 0:
        print(f"Sample failure: {[r[2] for r in results if not r[1]][0]}")


print("=== CONCURRENCY BENCHMARK: PORT 5432 vs PORT 6543 ===")
test_concurrent(5432, 25)
test_concurrent(6543, 25)
