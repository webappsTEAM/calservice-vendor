import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from workforce_api.models import WorkforceDispatchState, WorkforceEventLog
from workforce_api.services.automatic_dispatch import (
    dispatch_pending_jobs,
    compute_dispatch_retry_delay,
    get_or_create_dispatch_state,
)
from companies.models import Company
from service_requests.models import ServiceRequest
import uuid

co = Company.objects.create(company_name=f"debug_co_{uuid.uuid4().hex[:6]}", is_active=True)
sr = ServiceRequest.objects.create(
    company=co,
    customer_name="Test Customer",
    phone="+919876543210",
    service_category="Electrical",
    issue_title="Electrical Wiring Repair",
    status="confirmed",
    latitude=12.9715987,
    longitude=77.5945627,
    address="123 MG Road, Bangalore",
    preferred_date=timezone.localdate(),
)

events_init = list(WorkforceEventLog.objects.filter(payload__job_id=sr.id).values("id", "event_type", "created_at"))
state_init = WorkforceDispatchState.objects.filter(job=sr).values().first()
print("After create:")
print("  Events count:", len(events_init), events_init)
print("  State:", state_init)

for i in range(10):
    r = dispatch_pending_jobs(company_id=co.id)
    if r["dispatched_count"] > 0 or r["pending_jobs_found"] > 0:
        print(f"Sweep {i}:", r)

events_after = list(WorkforceEventLog.objects.filter(payload__job_id=sr.id).values("id", "event_type", "created_at"))
state_after = WorkforceDispatchState.objects.filter(job=sr).values().first()
print("After 10 sweeps:")
print("  Events count:", len(events_after), [e["event_type"] for e in events_after])
print("  State:", state_after)
