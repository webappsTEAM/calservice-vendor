"""
backend/debug_test_a_b.py

Targeted Diagnostic Test for TEST A/B ONLY with explicit step-by-step timing
and diagnostic logging to isolate any blocking call.
"""

import os
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

print("[DIAGNOSTIC] Step 1: Initializing Django...")
t0 = time.time()
import django
django.setup()
print(f"[DIAGNOSTIC] Django setup completed in {time.time() - t0:.2f}s")

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest, EmployeeJob
from workforce_api.models import JobTrackingSession, JobLocationPoint, WorkforceEventLog
from workforce_api.services.realtime import (
    get_redis_client,
    get_job_current_location,
    set_job_current_location,
)
from workforce_api.views import (
    WorkforceLocationUpdateView,
    WorkforceJobLiveTrackingView,
)

User = get_user_model()
factory = APIRequestFactory()

def run_debug_test():
    print("[DIAGNOSTIC] Step 2: Testing Redis client directly...")
    t_red = time.time()
    client = get_redis_client()
    if not client:
        print("[DIAGNOSTIC] ERROR: get_redis_client() returned None!")
        return
    ping_res = client.ping()
    print(f"[DIAGNOSTIC] Redis ping: {ping_res} in {time.time() - t_red:.3f}s")

    print("[DIAGNOSTIC] Step 3: Setting up test fixtures...")
    t_fix = time.time()
    now = timezone.now()
    company = Company.objects.first()
    if not company:
        company = Company.objects.create(company_name="CalTrack Stage2 Ltd", slug="calstage2")

    cust_user, _ = User.objects.get_or_create(
        username="cust_stage2_test@calservice.com",
        defaults={
            "email": "cust_stage2_test@calservice.com",
            "first_name": "Maya",
            "last_name": "Customer",
            "role": "customer",
            "is_active": True,
        }
    )

    tech_user, _ = User.objects.get_or_create(
        username="tech_stage2_test@calservice.com",
        defaults={
            "email": "tech_stage2_test@calservice.com",
            "first_name": "Vikram",
            "last_name": "Technician",
            "role": "technician",
            "is_active": True,
        }
    )
    tech_user.company = company
    tech_user.save()

    emp = Employee.objects.filter(user=tech_user).first()
    if not emp:
        emp = Employee.objects.filter(company=company, employee_id=f"EMP-STAGE2-{tech_user.id}").first()
        if not emp:
            emp = Employee.objects.create(
                user=tech_user,
                employee_id=f"EMP-STAGE2-{tech_user.id}",
                company=company,
                title="Senior Service Pro",
                is_active=True,
                is_online=True,
                current_availability="busy",  # Assigned to active job
                bank_details={"onboarding": {"status": "approved"}},
            )
        else:
            emp.user = tech_user
            emp.is_active = True
            emp.is_online = True
            emp.current_availability = "busy"
            emp.bank_details = {"onboarding": {"status": "approved"}}
            emp.save()
    else:
        emp.is_active = True
        emp.is_online = True
        emp.current_availability = "busy"
        emp.bank_details = {"onboarding": {"status": "approved"}}
        emp.save()

    job, _ = ServiceRequest.objects.get_or_create(
        request_id="REQ-STAGE2-001",
        defaults={
            "company": company,
            "customer": cust_user,
            "customer_name": "Maya Customer",
            "phone": "9876543299",
            "address": "MG Road, Bangalore",
            "preferred_date": now.date(),
            "preferred_time": "10:00:00",
            "latitude": 12.9750000,
            "longitude": 77.6050000,
            "status": "on_the_way",
            "assigned_employee": emp,
        }
    )
    job.status = "on_the_way"
    job.assigned_employee = emp
    job.customer = cust_user
    job.latitude = 12.9750000
    job.longitude = 77.6050000
    job.save()

    EmployeeJob.objects.update_or_create(
        service_request=job,
        employee=emp,
        defaults={"status": "ASSIGNED", "is_primary": True}
    )

    # Clean up Redis key
    client.delete(f"job_location:{job.id}")
    print(f"[DIAGNOSTIC] Fixtures setup completed in {time.time() - t_fix:.2f}s")

    print("[DIAGNOSTIC] Step 4: Preparing GPS request payload...")
    loc_payload = {
        "latitude": 12.9716000,
        "longitude": 77.5946000,
        "accuracy": 8.0,
        "speed": 22.0,
        "heading": 110.0,
        "captured_at": timezone.now().isoformat(),
    }

    print("START GPS REQUEST")
    req = factory.post("/workforce/presence/location/", loc_payload, format="json")
    print("[DIAGNOSTIC] Step 5: Authenticating test request...")
    force_authenticate(req, user=tech_user)

    print("REQUEST SENT")
    t_call = time.time()
    loc_view = WorkforceLocationUpdateView.as_view()
    
    print("[DIAGNOSTIC] Step 6: Calling WorkforceLocationUpdateView.as_view()(req)...")
    res = loc_view(req)
    print(f"RESPONSE RECEIVED (HTTP {res.status_code} in {time.time() - t_call:.3f}s)")

    print("[DIAGNOSTIC] Step 7: Reading Redis current location...")
    t_get = time.time()
    redis_loc = get_job_current_location(job.id)
    print(f"REDIS LOCATION READ in {time.time() - t_get:.3f}s: {redis_loc}")

    if redis_loc and abs(redis_loc.get("latitude", 0) - 12.9716000) < 0.0001:
        print("REDIS LOCATION WRITTEN")
        print("TEST A PASSED")
    else:
        print(f"[DIAGNOSTIC] ERROR: Redis location mismatch or not written! Data: {redis_loc}")

if __name__ == "__main__":
    run_debug_test()
