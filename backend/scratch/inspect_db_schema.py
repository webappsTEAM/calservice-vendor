import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'service_requests_servicerequest'
        ORDER BY ordinal_position;
    """)
    cols = cursor.fetchall()
    print("=== service_requests_servicerequest columns ===")
    for col in cols:
        print(f"  {col[0]}: {col[1]} (nullable={col[2]}, default={col[3]})")

    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default 
        FROM information_schema.columns 
        WHERE table_name = 'service_requests_service'
        ORDER BY ordinal_position;
    """)
    cols = cursor.fetchall()
    print("\n=== service_requests_service columns ===")
    for col in cols:
        print(f"  {col[0]}: {col[1]} (nullable={col[2]}, default={col[3]})")

    cursor.execute("""
        SELECT id, name, category_id, is_active FROM service_requests_service ORDER BY id;
    """)
    services = cursor.fetchall()
    print("\n=== Services in database ===")
    for s in services:
        print(f"  ID {s[0]}: {s[1]} (cat_id={s[2]}, active={s[3]})")

    cursor.execute("""
        SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND (table_name LIKE '%quote%' OR table_name LIKE '%estimate%');
    """)
    quote_tables = cursor.fetchall()
    print("\n=== Existing quote/estimate tables ===")
    for t in quote_tables:
        print(f"  {t[0]}")
