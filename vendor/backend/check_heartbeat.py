import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from workforce_api.models import WorkforceEventLog

evs = WorkforceEventLog.objects.filter(payload__has_key="last_heartbeat")
for e in evs:
    print("Heartbeat event:", e.id, e.event_type, e.payload)
