import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT pg_read_file('/var/www/calservices/current-vendor/backend/service_requests/models.py');")
    content = cursor.fetchone()[0]
    for line in content.splitlines():
        if "def save(" in line or "restart_trigger" in line:
            print("Found line:", line)
