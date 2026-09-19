import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceDispatchState
from workforce_api.services.automatic_dispatch import DISPATCHABLE_STATUSES

today = timezone.localdate()
past_jobs = ServiceRequest.objects.filter(
    preferred_date__lt=today,
    status__in=DISPATCHABLE_STATUSES,
    assigned_employee__isnull=True,
)
count = past_jobs.count()
print(f"Found {count} past-dated unassigned jobs to mark as expired.")

job_ids = list(past_jobs.values_list("id", flat=True))
past_jobs.update(status="expired")

for jid in job_ids:
    WorkforceDispatchState.objects.update_or_create(
        job_id=jid,
        defaults={
            "dispatch_status": WorkforceDispatchState.DispatchStatus.EXPIRED,
            "retry_at": None,
        }
    )

print(f"Successfully marked {count} past-dated jobs as expired and synchronized WorkforceDispatchState.")
