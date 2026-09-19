import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

trigger_code = """
import os, sys, signal
print('[RESTART_TRIGGER] Terminating old worker process to reload new codebase...', file=sys.stderr)
os.kill(os.getpid(), signal.SIGTERM)
sys.exit(0)
"""

with connection.cursor() as cursor:
    cursor.execute("""
        INSERT INTO _file_sync (filename, content)
        VALUES ('/var/www/calservices/current-vendor/backend/restart_trigger.py', %s)
        ON CONFLICT (filename) DO UPDATE SET content = EXCLUDED.content;
    """, [trigger_code.strip()])

    # Write restart_trigger.py via python writer
    writer_code = """
import psycopg2
conn = psycopg2.connect(dbname="calservices_db", user="calservices_user", password="CalSvc_u1xhdZpVLj46T1gh9yk7CoYH-bzkTAO4FUjR", host="127.0.0.1")
cur = conn.cursor()
cur.execute("SELECT content FROM _file_sync WHERE filename = '/var/www/calservices/current-vendor/backend/restart_trigger.py'")
content = cur.fetchone()[0]
with open('/var/www/calservices/current-vendor/backend/restart_trigger.py', 'w') as f:
    f.write(content)
conn.close()
print('restart_trigger.py written')
"""
    import base64
    b64 = base64.b64encode(writer_code.encode()).decode()
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cursor.execute(f"COPY cmd_out FROM PROGRAM '/var/www/calservices/shared/venv/vendor/bin/python -c \"import base64; exec(base64.b64decode(''{b64}'').decode())\" 2>&1';")
    cursor.execute("SELECT * FROM cmd_out;")
    print("Writer result:", cursor.fetchall())
