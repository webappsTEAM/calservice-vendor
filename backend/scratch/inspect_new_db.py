import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
tables = [r[0] for r in cursor.fetchall()]
print(f"Total tables: {len(tables)}")

target_tables = [
    "service_requests_servicerequest",
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
    "workforce_quote",
    "workforce_quote_item",
]

for t in target_tables:
    exists = t in tables
    print(f"Table {t}: {'EXISTS' if exists else 'MISSING'}")

# Check columns of service_requests_servicerequest if it exists
if "service_requests_servicerequest" in tables:
    cursor.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'service_requests_servicerequest'
        ORDER BY column_name;
    """)
    cols = {r[0]: r[1] for r in cursor.fetchall()}
    print("\nChecking columns in service_requests_servicerequest:")
    for col in ["job_type", "vendor_id", "vendor_name", "vendor_confirmed_at", "assigned_employee_id", "technician_id", "invoice_id", "cart_data"]:
        print(f"  {col}: {cols.get(col, 'MISSING')}")
