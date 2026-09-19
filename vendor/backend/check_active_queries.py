import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT pid, usename, state, wait_event_type, wait_event, age(now(), query_start), substring(query from 1 for 100)
        FROM pg_stat_activity 
        WHERE state != 'idle' AND pid != pg_backend_pid()
        ORDER BY query_start;
    """)
    rows = cursor.fetchall()
    print(f"Active non-idle queries count: {len(rows)}")
    for r in rows:
        print(" ", r)
