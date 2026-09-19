import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'systemctl is-active workforce-dispatch-engine 2>&1 || true';")
    cursor.execute("SELECT * FROM cmd_out;")
    print("Service status:", cursor.fetchall())
