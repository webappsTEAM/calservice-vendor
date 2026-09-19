import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT pid, usename, client_addr, client_port, application_name, state, backend_start, query_start, query
        FROM pg_stat_activity
        WHERE datname = current_database() AND pid <> pg_backend_pid();
    """)
    rows = cursor.fetchall()
    print(f"Total connections: {len(rows)}")
    for r in rows:
        print(f"PID {r[0]} | App: {r[4]} | IP: {r[2]}:{r[3]} | State: {r[5]} | Query: {str(r[8])[:100]}")
