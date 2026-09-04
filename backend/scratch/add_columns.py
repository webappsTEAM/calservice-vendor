import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        ALTER TABLE service_requests_servicerequest 
        ADD COLUMN IF NOT EXISTS job_type VARCHAR(50) DEFAULT 'SERVICE',
        ADD COLUMN IF NOT EXISTS vendor_id VARCHAR(100) DEFAULT '',
        ADD COLUMN IF NOT EXISTS vendor_name VARCHAR(200) DEFAULT '',
        ADD COLUMN IF NOT EXISTS vendor_confirmed_at TIMESTAMP WITH TIME ZONE;
    """)
    print("Columns added successfully!")
