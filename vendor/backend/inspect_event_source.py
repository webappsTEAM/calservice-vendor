import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from workforce_api.models import WorkforceEventLog

events = WorkforceEventLog.objects.filter(id__gte=4441200).order_by("id")[:10]
for e in events:
    print(f"Event #{e.id}: {e.event_type} at {e.created_at} fields={e.__dict__}")
