import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'service_requests_servicerequest'
        ORDER BY ordinal_position;
    """)
    for row in cursor.fetchall():
        print(f"SR col: {row[0]} ({row[1]})")
