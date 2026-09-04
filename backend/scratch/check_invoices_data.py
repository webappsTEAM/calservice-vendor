import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT * FROM settings_hub_invoice LIMIT 5;")
    rows = cursor.fetchall()
    print("settings_hub_invoice rows:", rows)

    cursor.execute("SELECT * FROM service_requests_payment LIMIT 5;")
    rows = cursor.fetchall()
    print("service_requests_payment rows:", rows)

    cursor.execute("SELECT * FROM service_requests_estimationfee LIMIT 5;")
    rows = cursor.fetchall()
    print("service_requests_estimationfee rows:", rows)
