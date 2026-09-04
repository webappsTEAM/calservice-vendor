import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

print("DB Name:", connection.settings_dict["NAME"])
print("DB User:", connection.settings_dict["USER"])
print("DB Host:", connection.settings_dict["HOST"])
print("DB Port:", connection.settings_dict["PORT"])

with connection.cursor() as cursor:
    cursor.execute("SHOW search_path;")
    print("search_path:", cursor.fetchall())
    cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name = 'service_requests_estimation';")
    print("Table search:", cursor.fetchall())
