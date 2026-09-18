import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_name LIKE '%celery%' OR table_name LIKE '%cron%' OR table_name LIKE '%periodic%';
    """)
    tables = [r[0] for r in cursor.fetchall()]
    print("Related tables:", tables)
    
    if "django_celery_beat_periodictask" in tables:
        cursor.execute("""
            SELECT name, task, enabled, last_run_at FROM django_celery_beat_periodictask;
        """)
        for r in cursor.fetchall():
            print("Celery Task:", r)
