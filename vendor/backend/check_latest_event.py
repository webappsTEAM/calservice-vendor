import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from workforce_api.models import WorkforceEventLog

latest = WorkforceEventLog.objects.order_by("-id").first()
now = timezone.now()
age = (now - latest.created_at).total_seconds()
print(f"Latest Event #{latest.id}: {latest.event_type} created at {latest.created_at} ({age:.1f}s ago) payload={latest.payload}")
