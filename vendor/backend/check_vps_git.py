import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'cd /var/www/calservices/current-vendor && git log -n 1 --oneline 2>&1 || true';")
    cursor.execute("SELECT * FROM cmd_out;")
    print("VPS Git commit:", cursor.fetchall())
