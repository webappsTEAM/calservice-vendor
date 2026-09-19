import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT pg_terminate_backend(1743276);")
    print("Terminated PID 1743276:", cursor.fetchone())
