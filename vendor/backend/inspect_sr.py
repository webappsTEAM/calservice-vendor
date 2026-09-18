import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceEventLog, WorkforceDispatchState

# Find the most recently created ServiceRequest
sr = ServiceRequest.objects.order_by("-id").first()
print(f"Latest ServiceRequest #{sr.id}:")
events = WorkforceEventLog.objects.filter(payload__job_id=sr.id).order_by("id")
print(f"Total events: {events.count()}")
for e in events:
    print(f"  Event #{e.id}: {e.event_type} at {e.created_at} payload={e.payload}")

state = WorkforceDispatchState.objects.filter(job=sr).first()
if state:
    print(f"DispatchState: status={state.dispatch_status}, attempts={state.attempt_count}, last_attempt={state.last_attempt_at}, retry_at={state.retry_at}")
