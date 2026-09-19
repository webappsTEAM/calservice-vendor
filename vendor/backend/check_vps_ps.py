import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute("COPY cmd_out FROM PROGRAM 'ps aux | grep python | grep dispatch || echo \"NONE\"';")
    cursor.execute("SELECT * FROM cmd_out;")
    print("Running dispatch processes:")
    for r in cursor.fetchall():
        print(" ", r[0])
