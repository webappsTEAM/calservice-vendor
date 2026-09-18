import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from service_requests.models import ServiceRequest
from workforce_api.services.automatic_dispatch import DISPATCHABLE_STATUSES

today = timezone.localdate()
stale_null_date = ServiceRequest.objects.filter(
    status__in=DISPATCHABLE_STATUSES,
    preferred_date__isnull=True,
    created_at__date__lt=today,
    assigned_employee__isnull=True,
)
print(f"Total stale null-date dispatchable unassigned jobs: {stale_null_date.count()}")
