import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT pid, usename, client_addr, client_port, state, query_start, query 
        FROM pg_stat_activity 
        WHERE query LIKE '%workforce_event_log%' AND pid <> pg_backend_pid();
    """)
    for r in cursor.fetchall():
        print(r)
