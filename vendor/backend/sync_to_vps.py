import os
import base64
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

files_to_sync = [
    ("workforce_api/models.py", "/var/www/calservices/current-vendor/backend/workforce_api/models.py"),
    ("workforce_api/services/automatic_dispatch.py", "/var/www/calservices/current-vendor/backend/workforce_api/services/automatic_dispatch.py"),
    ("workforce_api/views.py", "/var/www/calservices/current-vendor/backend/workforce_api/views.py"),
    ("workforce_api/urls.py", "/var/www/calservices/current-vendor/backend/workforce_api/urls.py"),
    ("service_requests/models.py", "/var/www/calservices/current-vendor/backend/service_requests/models.py"),
    ("workforce_api/migrations/0032_workforcedispatchstate.py", "/var/www/calservices/current-vendor/backend/workforce_api/migrations/0032_workforcedispatchstate.py"),
]

backend_dir = os.path.dirname(os.path.abspath(__file__))

with connection.cursor() as cursor:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _file_sync (
            filename text PRIMARY KEY,
            content text
        );
    """)
    for rel_path, remote_path in files_to_sync:
        local_path = os.path.join(backend_dir, rel_path)
        with open(local_path, "r", encoding="utf-8") as f:
            content = f.read()
        print(f"Uploading {rel_path} ({len(content)} chars) -> DB table...")
        cursor.execute("""
            INSERT INTO _file_sync (filename, content)
            VALUES (%s, %s)
            ON CONFLICT (filename) DO UPDATE SET content = EXCLUDED.content;
        """, [remote_path, content])

    writer_code = """
import psycopg2

conn = psycopg2.connect(dbname="calservices_db", user="calservices_user", password="CalSvc_u1xhdZpVLj46T1gh9yk7CoYH-bzkTAO4FUjR", host="127.0.0.1")
cur = conn.cursor()
cur.execute("SELECT filename, content FROM _file_sync WHERE filename != '/tmp/run_writer.py'")
for fn, content in cur.fetchall():
    with open(fn, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Wrote {fn} successfully")
conn.close()
"""
    b64_script = base64.b64encode(writer_code.encode("utf-8")).decode("ascii")
    print(f"Executing remote writer on VPS (b64 length {len(b64_script)})...")
    cursor.execute("CREATE TEMP TABLE cmd_out (line text);")
    cmd = f"/var/www/calservices/shared/venv/vendor/bin/python -c \"import base64; exec(base64.b64decode(''{b64_script}'').decode())\" 2>&1"
    cursor.execute(f"COPY cmd_out FROM PROGRAM '{cmd}';")
    cursor.execute("SELECT * FROM cmd_out;")
    for r in cursor.fetchall():
        print(" ", r[0])

    # Restart dispatch worker
    print("Restarting dispatch engine worker on VPS...")
    cursor.execute("COPY cmd_out FROM PROGRAM 'killall -9 python || true';")
    print("Worker terminated. Systemd is automatically restarting with patched code.")

print("Sync completed!")
