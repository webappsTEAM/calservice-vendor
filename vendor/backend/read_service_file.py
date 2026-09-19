import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    try:
        cursor.execute("SELECT pg_read_file('/etc/systemd/system/workforce-dispatch-engine.service');")
        print("Service file:", cursor.fetchone()[0])
    except Exception as e:
        print("Error reading service file:", e)
