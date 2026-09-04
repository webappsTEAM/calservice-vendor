import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    for tbl in ['settings_hub_invoice', 'service_requests_estimationfee', 'service_requests_payment', 'service_requests_estimation', 'service_requests_estimationquotation']:
        cursor.execute(f"""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = '{tbl}'
            ORDER BY ordinal_position;
        """)
        print(f'=== {tbl} ===')
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")

