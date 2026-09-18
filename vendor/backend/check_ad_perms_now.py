import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'ls -la /var/www/calservices/current-vendor/backend/workforce_api/services/automatic_dispatch.py 2>&1';")
    cursor.execute("SELECT * FROM cmd_out;")
    print("automatic_dispatch.py perms:", cursor.fetchall())
