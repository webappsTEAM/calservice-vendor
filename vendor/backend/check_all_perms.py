import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'ls -la /var/www/calservices/current-vendor/backend/workforce_api/models.py /var/www/calservices/current-vendor/backend/workforce_api/views.py /var/www/calservices/current-vendor/backend/service_requests/models.py 2>&1 || true';")
    cursor.execute("SELECT * FROM cmd_out;")
    for r in cursor.fetchall():
        print(r[0])
