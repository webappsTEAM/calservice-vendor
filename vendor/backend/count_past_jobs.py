import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from service_requests.models import ServiceRequest
from workforce_api.services.automatic_dispatch import DISPATCHABLE_STATUSES

today = timezone.localdate()
past_jobs = ServiceRequest.objects.filter(
    status__in=DISPATCHABLE_STATUSES,
    preferred_date__lt=today,
    assigned_employee__isnull=True,
)
print(f"Total past-dated dispatchable unassigned jobs: {past_jobs.count()}")
for j in past_jobs[:10]:
    print(f"  Job #{j.id}: status={j.status} date={j.preferred_date} category={j.service_category}")
