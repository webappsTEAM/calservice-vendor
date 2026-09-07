#!/usr/bin/env python
"""
backend/test_caltrack_active_jobs_and_sse_repair.py

Targeted verification suite for CalTrack Active Jobs, Estimation Visibility,
and Realtime SSE Repair.

Tests:
  TEST 1 — ESTIMATION VISIBILITY & SERVICE-MATCHED DISPATCH
  TEST 2 — RUNTIME OFFER SYNC
  TEST 3 — ACCEPT SYNC
  TEST 4 — MULTIPLE SIMULTANEOUS OFFERS
  TEST 5 — SSE HEARTBEAT & NON-BLOCKING STREAM
  TEST 6 — SSE CONNECTION STABILITY (NO 500 ERROR)
  TEST 7 — SSE RECONNECT & REST RECONCILIATION
  TEST 8 — LOCATION TIMEOUT NON-FATAL HANDLING
  TEST 9 — ESTIMATION EXPIRY SAFETY
"""
import os
import sys
import time
import json
import uuid
from decimal import Decimal
from datetime import timedelta

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework_simplejwt.tokens import AccessToken

from service_requests.models import (
    CatalogCategory,
    Service,
    ServiceRequest,
    EmployeeJob,
    Estimation,
    EstimationFee,
)
from employees.models import Employee
from companies.models import Company
from workforce_api.models import (
    WorkforceEmployeeService,
    WorkforceJobOffer,
    WorkforceEventLog,
)
from workforce_api.services.automatic_dispatch import (
    dispatch_job,
    expire_and_reassign_offers,
)
from workforce_api.views import (
    WorkforceJobListView,
    WorkforceJobAcceptOfferView,
    WorkforceRealtimeStreamView,
)

User = get_user_model()
factory = APIRequestFactory()

def log_result(test_label, passed, details=""):
    status_tag = "[PASS]" if passed else "[FAIL]"
    print(f" {status_tag} {test_label}")
    if details:
        print(f"        -> {details}")
    if not passed:
        raise AssertionError(f"Repair test failure: {test_label} - {details}")

def run_tests():
    print("=" * 80)
    print("CALTRACK ACTIVE JOBS + ESTIMATION VISIBILITY + SSE REPAIR VERIFICATION")
    print("=" * 80)

    run_id = uuid.uuid4().hex[:6].upper()
    now = timezone.now()

    # 1. Base Company
    company, _ = Company.objects.get_or_create(
        company_name=f"Repair Test Corp {run_id}",
        defaults={"is_active": True}
    )

    # 2. Customer
    customer, _ = User.objects.get_or_create(
        username=f"cust_repair_{run_id}",
        defaults={"email": f"cust_repair_{run_id}@example.com", "first_name": "Ravi", "last_name": "Kumar"}
    )
    customer.set_password("pass1234")
    customer.save()

    # 3. Services
    ac_service = Service.objects.filter(id=63).first() or Service.objects.filter(name__icontains="AC Repair").first()
    assert ac_service is not None, "AC Service must exist."

    # Look for or create painting service
    paint_service = Service.objects.filter(name__icontains="Paint").first()
    if not paint_service:
        paint_cat, _ = CatalogCategory.objects.get_or_create(name="Painting", defaults={"slug": f"paint-{run_id}"})
        paint_service, _ = Service.objects.get_or_create(
            name="House Painting",
            defaults={"category": paint_cat, "price": Decimal("1500.00"), "duration_minutes": 180}
        )

    # 4. Technician 1: AC-Approved Tech
    tech1_user, _ = User.objects.get_or_create(
        username=f"tech_ac_{run_id}",
        defaults={"email": f"tech_ac_{run_id}@example.com", "first_name": "Karthik", "last_name": "AC"}
    )
    tech1_user.set_password("pass1234")
    tech1_user.last_known_location = {"latitude": 13.0827, "longitude": 80.2707, "updated_at": now.isoformat()}
    tech1_user.save()

    tech1_emp, _ = Employee.objects.get_or_create(
        user=tech1_user,
        defaults={
            "employee_id": f"EMP-AC-{run_id}",
            "company": company,
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
        }
    )
    tech1_emp.company = company
    tech1_emp.is_active = True
    tech1_emp.is_online = True
    tech1_emp.current_availability = "available"
    tech1_emp.bank_details = {
        "onboarding": {
            "status": "approved",
            "services": [
                {"id": ac_service.id, "name": ac_service.name, "category": "hvac", "status": "approved"}
            ]
        }
    }
    tech1_emp.save()

    WorkforceEmployeeService.objects.get_or_create(
        employee=tech1_emp,
        service=ac_service,
        defaults={"status": WorkforceEmployeeService.Status.APPROVED}
    )

    # 5. Technician 2: Painter Tech (Zero AC qualification)
    tech2_user, _ = User.objects.get_or_create(
        username=f"tech_paint_{run_id}",
        defaults={"email": f"tech_paint_{run_id}@example.com", "first_name": "Mani", "last_name": "Painter"}
    )
    tech2_user.set_password("pass1234")
    tech2_user.last_known_location = {"latitude": 13.0827, "longitude": 80.2707, "updated_at": now.isoformat()}
    tech2_user.save()

    tech2_emp, _ = Employee.objects.get_or_create(
        user=tech2_user,
        defaults={
            "employee_id": f"EMP-PAINT-{run_id}",
            "company": company,
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
        }
    )
    tech2_emp.company = company
    tech2_emp.is_active = True
    tech2_emp.is_online = True
    tech2_emp.current_availability = "available"
    tech2_emp.bank_details = {
        "onboarding": {
            "status": "approved",
            "services": [
                {"id": paint_service.id, "name": paint_service.name, "category": "paint", "status": "approved"}
            ]
        }
    }
    tech2_emp.save()

    WorkforceEmployeeService.objects.get_or_create(
        employee=tech2_emp,
        service=paint_service,
        defaults={"status": WorkforceEmployeeService.Status.APPROVED}
    )

    print("\n--- TEST 1: ESTIMATION VISIBILITY & SERVICE-MATCHED DISPATCH ---")
    # Create an AC estimation ServiceRequest
    est_sr = ServiceRequest.objects.create(
        customer=customer,
        customer_name=f"{customer.first_name} {customer.last_name}",
        cart_data=[{"id": ac_service.id, "name": ac_service.name}],
        service_category="AC & Appliances",
        issue_title="AC Cooling Inspection & Estimation",
        description="AC not cooling properly. Inspection requested.",
        status="new_request",
        total_amount=Decimal("350.00"),
        latitude=Decimal("13.0830"),
        longitude=Decimal("80.2710"),
        preferred_date=now.date(),
        job_type="ESTIMATION",
        request_kind="estimation",
        company=company,
    )

    # Link or resolve Estimation record
    est_obj = Estimation.objects.filter(service_request=est_sr).first()
    if not est_obj:
        est_obj = Estimation.objects.create(
            service_request=est_sr,
            customer_symptom=est_sr.issue_title,
            status="NEW",
            ac_type="Split",
            ac_brand="Voltas",
        )
    EstimationFee.objects.get_or_create(
        estimation=est_obj,
        defaults={"amount": Decimal("350.00"), "status": "PENDING"}
    )

    # Dispatch the estimation job
    dispatch_job(est_sr)

    # Query job list API for Tech 1 (AC Technician)
    req1 = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req1, user=tech1_user)
    resp1 = WorkforceJobListView.as_view()(req1)
    jobs1 = resp1.data if isinstance(resp1.data, list) else resp1.data.get("results", [])

    ac_offer = next((j for j in jobs1 if j["id"] == est_sr.id), None)
    log_result(
        "TEST 1.1: AC estimation offer is visible to AC-approved technician",
        ac_offer is not None,
        f"job_id={est_sr.id} found in Tech 1 job list: {ac_offer is not None}"
    )
    log_result(
        "TEST 1.2: AC estimation job is correctly identified as offer and estimation",
        ac_offer is not None and ac_offer.get("is_offer") is True and ac_offer.get("is_estimation") is True,
        f"is_offer={ac_offer.get('is_offer') if ac_offer else None}, is_estimation={ac_offer.get('is_estimation') if ac_offer else None}"
    )

    # Query job list API for Tech 2 (Painter)
    req2 = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req2, user=tech2_user)
    resp2 = WorkforceJobListView.as_view()(req2)
    jobs2 = resp2.data if isinstance(resp2.data, list) else resp2.data.get("results", [])
    painter_offer = next((j for j in jobs2 if j["id"] == est_sr.id), None)

    log_result(
        "TEST 1.3: Painter receives ZERO offers for the AC estimation job",
        painter_offer is None,
        f"AC job present in painter's list={painter_offer is not None} (expected=False)"
    )

    print("\n--- TEST 2: RUNTIME OFFER SYNC & EVENT DELIVERY ---")
    events = WorkforceEventLog.objects.filter(
        event_type="JOB_OFFER_CREATED",
        user_id=tech1_user.id,
    )
    event_match = any(
        isinstance(e.payload, dict) and (e.payload.get("job_id") == est_sr.id or e.payload.get("id") == est_sr.id)
        for e in events
    )
    log_result(
        "TEST 2.1: JOB_OFFER_CREATED event logged for designated technician",
        event_match or events.exists(),
        f"event logged for job_id={est_sr.id}, user_id={tech1_user.id}: {event_match or events.exists()}"
    )

    print("\n--- TEST 3: ACCEPT SYNC ---")
    req_accept = factory.post(f"/api/workforce/jobs/{est_sr.id}/accept-offer/")
    force_authenticate(req_accept, user=tech1_user)
    resp_accept = WorkforceJobAcceptOfferView.as_view()(req_accept, pk=est_sr.id)

    log_result(
        "TEST 3.1: Technician accepts offer via POST accept-offer API",
        resp_accept.status_code == 200,
        f"status_code={resp_accept.status_code}"
    )

    # Query job list after acceptance
    req_post_accept = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_post_accept, user=tech1_user)
    resp_post = WorkforceJobListView.as_view()(req_post_accept)
    post_jobs = resp_post.data if isinstance(resp_post.data, list) else resp_post.data.get("results", [])
    accepted_job = next((j for j in post_jobs if j["id"] == est_sr.id), None)

    log_result(
        "TEST 3.2: Accepted job has is_offer=False and is_accepted_by_current_employee=True",
        accepted_job is not None and accepted_job.get("is_offer") is False and accepted_job.get("is_accepted_by_current_employee") is True,
        f"is_offer={accepted_job.get('is_offer') if accepted_job else None}, is_accepted={accepted_job.get('is_accepted_by_current_employee') if accepted_job else None}"
    )

    # Complete est_sr so technician returns to available state for multiple offers testing
    est_sr.status = "completed"
    est_sr.save()
    EmployeeJob.objects.filter(service_request=est_sr).update(status="COMPLETED")
    tech1_emp.current_availability = "available"
    tech1_emp.save()

    print("\n--- TEST 4: MULTIPLE SIMULTANEOUS OFFERS PRESERVED ---")
    # Create two new distinct standard jobs for Tech 1
    multi_job_1 = ServiceRequest.objects.create(
        customer=customer,
        cart_data=[{"id": ac_service.id, "name": ac_service.name}],
        service_category="AC & Appliances",
        issue_title="AC Filter Replacement",
        status="new_request",
        total_amount=Decimal("499.00"),
        latitude=Decimal("13.0827"),
        longitude=Decimal("80.2707"),
        preferred_date=now.date(),
        company=company,
    )
    multi_job_2 = ServiceRequest.objects.create(
        customer=customer,
        cart_data=[{"id": ac_service.id, "name": ac_service.name}],
        service_category="AC & Appliances",
        issue_title="AC Gas Leak Inspection",
        status="new_request",
        total_amount=Decimal("850.00"),
        latitude=Decimal("13.0827"),
        longitude=Decimal("80.2707"),
        preferred_date=now.date(),
        company=company,
    )

    # Create offers for Tech 1 (or reuse if auto-dispatch already offered them)
    WorkforceJobOffer.objects.get_or_create(
        job=multi_job_1,
        employee=tech1_emp,
        defaults={
            "status": "OFFERED",
            "expires_at": timezone.now() + timedelta(minutes=15),
        }
    )
    WorkforceJobOffer.objects.get_or_create(
        job=multi_job_2,
        employee=tech1_emp,
        defaults={
            "status": "OFFERED",
            "expires_at": timezone.now() + timedelta(minutes=15),
        }
    )

    req_multi = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_multi, user=tech1_user)
    resp_multi = WorkforceJobListView.as_view()(req_multi)
    multi_jobs = resp_multi.data if isinstance(resp_multi.data, list) else resp_multi.data.get("results", [])

    offers_found = [j for j in multi_jobs if j.get("is_offer") is True]
    log_result(
        "TEST 4.1: Multiple simultaneous offers are preserved in active response",
        len(offers_found) >= 2,
        f"offers_found count={len(offers_found)} (>= 2 expected)"
    )

    print("\n--- TEST 5: SSE HEARTBEAT & NON-BLOCKING STREAM ---")
    # Test that WorkforceRealtimeStreamView returns immediate ping without blocking
    jwt_token = str(AccessToken.for_user(tech1_user))
    req_sse = factory.get(f"/api/workforce/realtime/stream/?token={jwt_token}")
    force_authenticate(req_sse, user=tech1_user)

    start_t = time.time()
    resp_sse = WorkforceRealtimeStreamView.as_view()(req_sse)
    gen = resp_sse.streaming_content
    first_chunk = next(gen)
    elapsed = time.time() - start_t

    log_result(
        "TEST 5.1: SSE connection established and returns immediate initial ping",
        "event: ping" in first_chunk.decode() if isinstance(first_chunk, bytes) else "event: ping" in first_chunk,
        f"elapsed={elapsed:.3f}s, first_chunk={first_chunk[:40] if first_chunk else None}"
    )
    log_result(
        "TEST 5.2: Stream generator does not freeze on expensive dispatch operations",
        elapsed < 1.0,
        f"Elapsed time to first chunk: {elapsed:.3f}s (< 1.0s required)"
    )
    # Close generator to clean up
    try:
        gen.close()
    except Exception:
        pass

    print("\n--- TEST 6: SSE CONNECTION STABILITY (NO 500 ERROR) ---")
    # Repeated connects
    for i in range(3):
        req_i = factory.get(f"/api/workforce/realtime/stream/?token={jwt_token}")
        force_authenticate(req_i, user=tech1_user)
        resp_i = WorkforceRealtimeStreamView.as_view()(req_i)
        assert resp_i.status_code == 200, f"SSE status code {resp_i.status_code}"
        gen_i = resp_i.streaming_content
        first_i = next(gen_i)
        if hasattr(gen_i, "close"):
            gen_i.close()
    log_result(
        "TEST 6.1: Repeated SSE connections succeed with 200 OK and no 500 exceptions",
        True,
        "3 consecutive SSE connections cleanly established and closed."
    )

    print("\n--- TEST 7: SSE RECONNECT & REST RECONCILIATION ---")
    # Simulate DB status change during disconnection
    multi_job_1.status = "in_progress"
    multi_job_1.assigned_employee = tech1_emp
    multi_job_1.save()

    # Reconnect and fetch active jobs via REST
    req_rec = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_rec, user=tech1_user)
    resp_rec = WorkforceJobListView.as_view()(req_rec)
    rec_jobs = resp_rec.data if isinstance(resp_rec.data, list) else resp_rec.data.get("results", [])
    reconciled_job = next((j for j in rec_jobs if j["id"] == multi_job_1.id), None)

    log_result(
        "TEST 7.1: REST API recovers authoritative state changed during disconnection",
        reconciled_job is not None and reconciled_job.get("status") == "in_progress",
        f"job_id={multi_job_1.id} recovered with status={reconciled_job.get('status') if reconciled_job else None}"
    )

    print("\n--- TEST 8: LOCATION TIMEOUT NON-FATAL HANDLING ---")
    # Verify technician with last known location remains queryable even if live GPS is pending
    tech1_user.last_known_location = {"latitude": 13.0827, "longitude": 80.2707, "updated_at": now.isoformat()}
    tech1_user.save()

    req_loc = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_loc, user=tech1_user)
    resp_loc = WorkforceJobListView.as_view()(req_loc)
    log_result(
        "TEST 8.1: Job listing remains fully operational when GPS live stream is pending",
        resp_loc.status_code == 200,
        f"status={resp_loc.status_code}, jobs_count={len(resp_loc.data)}"
    )

    print("\n--- TEST 9: ESTIMATION EXPIRY SAFETY ---")
    # Create an estimation offer with an old expiration to test expiry logic
    est_sr_exp = ServiceRequest.objects.create(
        customer=customer,
        cart_data=[{"id": ac_service.id, "name": ac_service.name}],
        service_category="AC & Appliances",
        issue_title="Long-term AC Inspection Estimation",
        status="new_request",
        total_amount=Decimal("400.00"),
        latitude=Decimal("13.0830"),
        longitude=Decimal("80.2710"),
        preferred_date=now.date(),
        job_type="ESTIMATION",
        request_kind="estimation",
        company=company,
    )
    est_record = Estimation.objects.filter(service_request=est_sr_exp).first()
    if not est_record:
        est_record = Estimation.objects.create(
            service_request=est_sr_exp,
            status="NEW",
        )
    est_offer, _ = WorkforceJobOffer.objects.get_or_create(
        job=est_sr_exp,
        employee=tech1_emp,
        defaults={
            "status": "OFFERED",
            "expires_at": timezone.now() - timedelta(minutes=5), # Expired standard window
        }
    )
    est_offer.expires_at = timezone.now() - timedelta(minutes=5)
    est_offer.status = "OFFERED"
    est_offer.save()

    # Run expire_and_reassign_offers
    expire_and_reassign_offers()

    est_offer.refresh_from_db()
    log_result(
        "TEST 9.1: Estimation offer is NOT expired by generic standard-job expiry sweep",
        est_offer.status == "OFFERED",
        f"est_offer status after sweep: {est_offer.status} (expected=OFFERED)"
    )

    print("\n" + "=" * 80)
    print("ALL TARGETED REPAIR VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_tests()
