import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;")
    tbls = [r[0] for r in cursor.fetchall()]
    print("All tables count:", len(tbls))
    est_tbls = [t for t in tbls if "est" in t or "insp" in t or "quot" in t]
    print("Estimation/inspection tables:", est_tbls)
