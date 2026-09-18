import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT conname, pg_get_constraintdef(oid) 
        FROM pg_constraint 
        WHERE conrelid = 'service_requests_servicerequest'::regclass AND contype = 'c';
    """)
    for r in cursor.fetchall():
        print(r)
