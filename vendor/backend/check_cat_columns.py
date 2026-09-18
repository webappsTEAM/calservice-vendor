import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'service_requests_catalogcategory'
        ORDER BY ordinal_position;
    """)
    cols = cursor.fetchall()
    print("Columns in service_requests_catalogcategory:")
    for col in cols:
        print(f" - {col[0]}: {col[1]} (Nullable: {col[2]})")
