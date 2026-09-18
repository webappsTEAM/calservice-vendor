import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db.models import Q
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer
from workforce_api.services.workload import get_employee_active_job, ACTIVE_QUEUE_STATUSES
from employees.models import Employee

u = User = get_user_model().objects.get(username="technician01")
emp = Employee.objects.get(user=u)

print("emp.id:", emp.id)
now = timezone.now()
active_job = get_employee_active_job(emp.id)
print("has_active_job:", bool(active_job))

today = timezone.localdate()
print("today:", today)

offers = WorkforceJobOffer.objects.filter(employee=emp, status="OFFERED")
print("Total OFFERED offers for emp:", offers.count())
for o in offers:
    print(f"Offer #{o.id}: job_id={o.job_id}, status={o.status}, expires_at={o.expires_at} (now={now}, expired? {o.expires_at <= now})")
    j = o.job
    print(f"   job preferred_date={j.preferred_date}, created_at.date={j.created_at.date()}")

offered_job_ids_qs = WorkforceJobOffer.objects.filter(
    employee=emp,
    status="OFFERED",
    expires_at__gt=now,
).filter(
    Q(job__preferred_date=today) |
    Q(job__preferred_date__isnull=True, job__created_at__date=today)
).values("job_id")

print("offered_job_ids_qs count:", offered_job_ids_qs.count())
print("offered_job_ids:", list(offered_job_ids_qs))

assigned_active_qs = Q(
    status__in=ACTIVE_QUEUE_STATUSES,
    assigned_employee=emp,
)
completed_qs = Q(
    assigned_employee=emp,
    status__in=["completed", "cancelled"]
)
offered_qs = Q(
    id__in=offered_job_ids_qs
)

qs = ServiceRequest.objects.filter(
    assigned_active_qs | completed_qs | offered_qs
)
print("Base qs count:", qs.count())
print("Base qs ids:", list(qs.values_list("id", flat=True)))

if emp.company:
    print("emp.company:", emp.company_id, emp.company.slug)
    if emp.company.id == 1 or getattr(emp.company, "slug", "") in ("calservices", "caldim-engineering-pvt-ltd", "caldim-platform", "caldim-services"):
        pass
    else:
        qs = qs.filter(Q(company=emp.company) | Q(assigned_employee=emp) | Q(id__in=offered_job_ids_qs) | Q(company__isnull=True))
        print("After company filter:", qs.count())
else:
    print("emp.company is None!")
