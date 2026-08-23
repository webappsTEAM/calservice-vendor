import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, name, customization FROM service_requests_service ORDER BY id;
    """)
    for s in cursor.fetchall():
        print(f"Service {s[0]}: {s[1]} -> customization: {s[2]}")
