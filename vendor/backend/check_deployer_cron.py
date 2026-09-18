import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'crontab -u deployer -l 2>&1 || echo \"NO_CRON\"';")
    cursor.execute("SELECT * FROM cmd_out;")
    print("Deployer crontab:")
    for r in cursor.fetchall():
        print(" ", r[0])
