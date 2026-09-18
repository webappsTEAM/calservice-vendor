import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'rm -f /var/www/calservices/current-vendor/backend/restart_trigger.py';")
    cursor.execute("DELETE FROM _file_sync WHERE filename = '/var/www/calservices/current-vendor/backend/restart_trigger.py';")
    print("Cleaned up restart_trigger.py")
