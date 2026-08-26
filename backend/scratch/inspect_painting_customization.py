import os
import sys
import json
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT id, name, customization FROM service_requests_service WHERE id >= 90 ORDER BY id;
    """)
    for s in cursor.fetchall():
        print(f"Service {s[0]}: {s[1]}")
        print("  Keys:", list(s[2].keys()) if isinstance(s[2], dict) else s[2])
        if isinstance(s[2], dict):
            for k, v in s[2].items():
                if isinstance(v, (dict, list)):
                    print(f"    {k}: {type(v)} with {len(v)} items")
                else:
                    print(f"    {k}: {v}")
