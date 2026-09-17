import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    reconsider_jobs_for_employee,
    dispatch_pending_jobs,
)
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

User = get_user_model()
u = User.objects.filter(username="gk").first()
emp = u.employee_profile

print(f"Technician: id={emp.id}, name={emp.user.get_full_name()}, online={emp.is_online}, company={emp.company_id}")

# Ensure employee is online
emp.is_online = True
emp.save(update_fields=["is_online"])

# Trigger dispatch reconciliation for pending jobs in this company
res = dispatch_pending_jobs(emp.company_id)
print("dispatch_pending_jobs result:", res)

recons = reconsider_jobs_for_employee(emp)
print("reconsider_jobs_for_employee result:", recons)

# Now check API response for gk
client = APIClient()
client.force_authenticate(user=u)
res_api = client.get("/api/workforce/jobs/?status=all")
print(f"API /api/workforce/jobs/?status=all count: {len(res_api.data)}")
for j in res_api.data:
    print(f"  Job #{j['id']} ({j['request_id']}): status={j['status']}, title={j.get('service_title')}")
