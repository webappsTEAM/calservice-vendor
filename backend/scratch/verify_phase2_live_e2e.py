"""
verify_phase2_live_e2e.py

Live HTTP E2E verification for Phase 2 Packers & Movers Job Discovery against live Django server on 8001.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

import requests
import json
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from employees.models import Employee
from companies.models import Company
from service_requests.models import ServiceRequest
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()
BASE_URL = "http://127.0.0.1:8001"

# 1. Get or create a technician user
user = User.objects.filter(role="employee", username__startswith="tech_").first()
if not user:
    user = User.objects.create_user(
        username="tech_pm_live",
        email="tech_pm_live@example.com",
        password="Password123!",
        role="employee",
        last_known_location={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy": 10.0,
            "updated_at": timezone.now().isoformat(),
        }
    )
emp, _ = Employee.objects.get_or_create(
    user=user,
    defaults={
        "company": user.company or Company.objects.first(),
        "employee_id": f"EMP-PM-{user.id}",
        "phone": f"98765{user.id:05d}",
        "is_online": True,
        "current_availability": "available",
        "bank_details": {
            "onboarding": {
                "status": "approved",
                "services": [
                    {"name": "Packers & Movers", "category": "Packers & Movers", "status": "approved"},
                    {"name": "Goods & Transport", "category": "Goods & Transport", "status": "approved"},
                ]
            }
        }
    }
)
emp.is_online = True
emp.current_availability = "available"
emp.save()

# Ensure user location is fresh
user.last_known_location = {
    "latitude": 12.9716,
    "longitude": 77.5946,
    "accuracy": 10.0,
    "updated_at": timezone.now().isoformat(),
}
user.save()

# Create JWT token
refresh = RefreshToken.for_user(user)
access_token = str(refresh.access_token)
headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

# 2. Create Packers & Movers booking in database (Packers & Movers and slash variant)
job_pm = ServiceRequest.objects.create(
    company=emp.company,
    status="confirmed",
    service_category="Packers / Movers",
    issue_title="Live 3BHK Relocation Moving Task",
    preferred_date=timezone.localdate(),
    preferred_time="10:00 AM",
    latitude=Decimal("12.9720"),
    longitude=Decimal("77.5950"),
    total_amount=Decimal("4900.00"),
    payment_method="cash",
    payment_status="pending",
)
print(f"Created Job #{job_pm.id} ({job_pm.service_category})")

# 3. Query Active Jobs API via HTTP
session = requests.Session()
active_resp = session.get(f"{BASE_URL}/api/workforce/jobs/?status=active", headers=headers)
print("GET /api/workforce/jobs/?status=active status:", active_resp.status_code)
jobs_data = active_resp.json() if active_resp.status_code == 200 else []
active_ids = [j["id"] for j in jobs_data]
print(f"Active Jobs returned: {len(jobs_data)} jobs -> IDs: {active_ids}")
assert job_pm.id in active_ids, f"Job #{job_pm.id} was not returned in Active Jobs API!"
print(f"Job #{job_pm.id} successfully discovered and visible in Active Jobs API!")

# 4. Accept Job via HTTP
accept_resp = session.post(f"{BASE_URL}/api/workforce/jobs/{job_pm.id}/accept-offer/", headers=headers)
print(f"POST /api/workforce/jobs/{job_pm.id}/accept-offer/ status:", accept_resp.status_code, accept_resp.text[:120])
assert accept_resp.status_code == 200, f"Accept failed: {accept_resp.text}"

# 5. Query Active Jobs API again to confirm accepted state
active_resp2 = session.get(f"{BASE_URL}/api/workforce/jobs/?status=active", headers=headers)
jobs_data2 = active_resp2.json()
accepted_job = next((j for j in jobs_data2 if j["id"] == job_pm.id), None)
print(f"Accepted job status in Active Jobs: {accepted_job.get('status')}, is_accepted={accepted_job.get('is_accepted_by_current_employee')}")
assert accepted_job is not None and accepted_job["status"] == "accepted"

print("ALL LIVE HTTP E2E CHECKS PASSED PERFECTLY!")
