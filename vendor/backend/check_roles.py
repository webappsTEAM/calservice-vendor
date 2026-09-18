import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT rolname, rolsuper, rolinherit, rolcreaterole, rolcreatedb, rolcanlogin, rolreplication 
        FROM pg_roles 
        WHERE rolname = CURRENT_USER;
    """)
    print("User roles:", cursor.fetchall())
