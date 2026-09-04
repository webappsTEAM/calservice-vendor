import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()

tables_to_check = [
    "service_requests_estimation",
    "service_requests_estimationfee",
    "service_requests_inspection",
    "service_requests_inspectionfinding",
    "service_requests_inspectionphoto",
    "service_requests_estimationquotation",
    "service_requests_estimationquotationitem",
    "settings_hub_invoice",
    "service_requests_payment",
    "service_requests_employeejob",
]

for t in tables_to_check:
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, [t])
    rows = cursor.fetchall()
    print(f"\n--- {t} ({len(rows)} columns) ---")
    for col, dtype, nullb in rows:
        print(f"  {col}: {dtype} (nullable={nullb})")
