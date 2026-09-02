"""
test_supabase_ports.py - SAFETY GUARD REQUIRED

Tests Supabase pooler port connectivity (5432 session mode vs 6543 transaction mode).

REQUIRED: ALLOW_REMOTE_STRESS_TEST=true
REQUIRED: DB_USER, DB_PASSWORD, DB_HOST env vars (NEVER hardcode credentials)

Usage:
  $env:DB_USER = "postgres.yourproject"
  $env:DB_PASSWORD = "yourpassword"
  $env:DB_HOST = "aws-0-ap-south-1.pooler.supabase.com"
  $env:ALLOW_REMOTE_STRESS_TEST = "true"
  python test_supabase_ports.py
"""
import psycopg2
import os

# PRODUCTION SAFETY GUARD
_allow = os.environ.get("ALLOW_REMOTE_STRESS_TEST", "").strip().lower()
if _allow != "true":
    print("\n[BLOCKED] test_supabase_ports.py targets live Supabase PostgreSQL.")
    print("To authorise: set ALLOW_REMOTE_STRESS_TEST=true")
    raise SystemExit(1)

_DB_NAME = os.environ.get("DB_NAME", "postgres")
_DB_USER = os.environ.get("DB_USER", "")
_DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
_DB_HOST = os.environ.get("DB_HOST", "")

if not _DB_USER or not _DB_PASSWORD or not _DB_HOST:
    print("\n[ERROR] Missing DB_USER, DB_PASSWORD, or DB_HOST environment variables.")
    raise SystemExit(1)

print("=== TESTING SUPABASE POOLER PORTS ===")

for port, label in [(5432, "Session mode"), (6543, "Transaction mode")]:
    try:
        conn = psycopg2.connect(
            dbname=_DB_NAME, user=_DB_USER, password=_DB_PASSWORD,
            host=_DB_HOST, port=port, sslmode="require"
        )
        print(f"[PORT {port}] Connected successfully in {label}")
        if port == 6543:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) FROM accounts_user;")
                row = cur.fetchone()
                print(f"[PORT {port}] Executed query: {row}")
        conn.close()
    except Exception as e:
        print(f"[PORT {port}] Connection failed: {e}")
