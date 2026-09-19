import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT pg_read_file('/var/www/calservices/current-vendor/backend/workforce_api/services/automatic_dispatch.py', 0, 500);")
    print("Remote automatic_dispatch.py:", cursor.fetchone()[0])
