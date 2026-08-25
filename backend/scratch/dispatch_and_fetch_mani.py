import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_backend.settings")
django.setup()

from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer
from workforce_api.services.automatic_dispatch import reconcile_booking_for_dispatch
from django.test import Client

mani_emp = Employee.objects.filter(user__username="mani").first()
print(f"Mani S: Emp #{mani_emp.id}, User #{mani_emp.user.id}, Online={mani_emp.is_online}")

# Get pending jobs 4086, 4085, 4083, 4082, 4081, 4080
jobs = ServiceRequest.objects.filter(id__in=[4086, 4085, 4083, 4082, 4081, 4080])
for j in jobs:
    print(f"\n--- Reconciling Job #{j.id} ({j.service_category} - {j.issue_title}) ---")
    ok, msg = reconcile_booking_for_dispatch(j)
    print(f"Result: ok={ok}, msg='{msg}'")

# Check offers created for Mani S
offers = WorkforceJobOffer.objects.filter(employee=mani_emp, status="OFFERED")
print(f"\nTotal Active Offers for Mani S: {offers.count()}")
for o in offers:
    print(f"  - Offer #{o.id} for Job #{o.job_id} ({o.job.service_category}), Expires at: {o.expires_at}")

# Call Active Jobs API as Mani S
client = Client()
client.force_login(mani_emp.user)
resp = client.get("/api/workforce/jobs/?status=active")
print(f"\nActive Jobs API Status: {resp.status_code}")
data = resp.json()
print(f"Active Jobs Returned Count: {len(data)}")
for item in data:
    print(f"  * Job #{item.get('id')} - {item.get('service_title') or item.get('service_category')} - Status: {item.get('status')} - Offer: {item.get('active_offer') is not None}")
