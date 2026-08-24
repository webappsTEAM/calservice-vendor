import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.db import connection

tables = [
    'workforce_quote',
    'workforce_painting_quote',
    'workforce_mason_quote',
    'workforce_quote_item',
    'workforce_quote_photo',
    'workforce_quote_phase',
    'workforce_quote_measurement',
]

with connection.cursor() as cursor:
    for tbl in tables:
        cursor.execute(f"""
            SELECT column_name, data_type, is_nullable, column_default 
            FROM information_schema.columns 
            WHERE table_name = '{tbl}'
            ORDER BY ordinal_position;
        """)
        cols = cursor.fetchall()
        print(f"\n=== {tbl} columns ===")
        for col in cols:
            print(f"  {col[0]}: {col[1]} (nullable={col[2]}, default={col[3]})")
