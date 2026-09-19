import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceDispatchState

sr = ServiceRequest.objects.get(id=5289)
print("Before:", sr.id, sr.status)
ServiceRequest.objects.filter(id=5289).update(status="expired")
WorkforceDispatchState.objects.update_or_create(
    job=sr,
    defaults={"dispatch_status": WorkforceDispatchState.DispatchStatus.EXPIRED, "retry_at": None}
)
print("Updated 5289 to expired")
