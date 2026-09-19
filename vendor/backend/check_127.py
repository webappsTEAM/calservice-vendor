import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT pid, usename, client_addr, client_port, state, query 
        FROM pg_stat_activity 
        WHERE client_addr = '127.0.0.1';
    """)
    for r in cursor.fetchall():
        print(r)
