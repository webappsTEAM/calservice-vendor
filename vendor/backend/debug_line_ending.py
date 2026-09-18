import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT pg_read_file('/var/www/calservices/current-vendor/backend/service_requests/models.py');")
    content = cursor.fetchone()[0]

print("Has \\r\\n:", "\r\n" in content)
print("Has \\n:", "\n" in content)
for i, line in enumerate(content.splitlines()):
    if "def save(" in line:
        print(f"Line {i}: repr={repr(line)}")
