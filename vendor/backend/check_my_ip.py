import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT client_addr, client_port FROM pg_stat_activity WHERE pid = pg_backend_pid();")
    print("My client:", cursor.fetchone())
