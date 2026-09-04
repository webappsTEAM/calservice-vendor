import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'service_requests_servicerequest' AND column_name IN ('job_type', 'vendor_id', 'vendor_name', 'vendor_confirmed_at', 'otp_verified_at');")
    print('Found columns:', cursor.fetchall())
