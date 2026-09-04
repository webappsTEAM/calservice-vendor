import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_name LIKE '%estimation%';")
    print("Estimation tables in all schemas:", cursor.fetchall())
