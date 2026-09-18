import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from django.db.models import Q
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer, WorkforceDispatchState

today = timezone.localdate()
now = timezone.now()

qs = ServiceRequest.objects.filter(
    status__in=["unassigned", "confirmed", "draft", "new_request", "redispatching", "searching"],
    assigned_employee__isnull=True,
    latitude__isnull=False,
    longitude__isnull=False,
).filter(
    Q(preferred_date=today) |
    Q(preferred_date__isnull=True, created_at__date=today)
)

print(f"Total dispatchable today: {qs.count()}")
for j in qs.order_by("-created_at")[:15]:
    offers_cnt = WorkforceJobOffer.objects.filter(job=j).count()
    active_offers = WorkforceJobOffer.objects.filter(job=j, status="OFFERED", expires_at__gt=now).count()
    state = WorkforceDispatchState.objects.filter(job_id=j.id).first()
    st_name = state.dispatch_status if state else "NO_STATE"
    retry = state.retry_at if state else None
    print(f"Job #{j.id} ({j.request_id}): status={j.status} cat={j.service_category} total_offers={offers_cnt} live_offers={active_offers} state={st_name} retry={retry}")
