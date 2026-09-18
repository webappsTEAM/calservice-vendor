import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'pkill -9 -f dispatch_pending_workforce_jobs 2>&1 || true';")
    cursor.execute("COPY cmd_out FROM PROGRAM 'pkill -9 -f manage.py 2>&1 || true';")
    cursor.execute("COPY cmd_out FROM PROGRAM 'ps aux | grep dispatch 2>&1 || true';")
    cursor.execute("SELECT * FROM cmd_out;")
    for r in cursor.fetchall():
        print(r[0])
