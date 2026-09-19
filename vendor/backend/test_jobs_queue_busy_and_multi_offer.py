"""
backend/test_jobs_queue_busy_and_multi_offer.py
Verification suite for CalTrack Employee Jobs, Incoming Offers, and Realtime Job Queue.

Validates:
1. Dual-purpose eligibility: can_receive_offer vs can_accept_offer.
2. Busy technician with active job CAN receive incoming offers.
3. Multiple offers (e.g. 5 jobs) all appear for the technician.
4. WorkforceJobListView returns both active job and all 5 incoming offers.
5. WorkforceJobAcceptOfferView returns 409 EMPLOYEE_ALREADY_BUSY while active job exists,
   and does NOT mutate or corrupt the offer status (remains OFFERED).
6. Completing active job allows acceptance; offer transitions to ACCEPTED.
7. WorkforceJobRejectOfferView declines offer immediately and removes from active list.
"""

import os
import sys
import uuid
import django

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from datetime import timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer, WorkforceEventLog
from workforce_api.services.automatic_dispatch import (
    check_candidate_eligibility,
    can_receive_offer,
    can_accept_offer,
    dispatch_job,
)
from workforce_api.views import (
    WorkforceJobListView,
    WorkforceJobAcceptOfferView,
    WorkforceJobRejectOfferView,
)

User = get_user_model()


def setup_test_environment():
    """Create test company, category, service, and technician."""
    unique_suffix = uuid.uuid4().hex[:8]
    company = Company.objects.filter(slug__in=["calservices", "caldim-platform"]).first()
    if not company:
        company = Company.objects.first()
    if not company:
        company, _ = Company.objects.get_or_create(
            slug="caltrack-test-co",
            defaults={"company_name": "CalTrack Test Company", "is_active": True}
        )

    user, _ = User.objects.get_or_create(
        username=f"tech_busy_test_{unique_suffix}",
        defaults={
            "email": f"tech_{unique_suffix}@caltrack.com",
            "first_name": "Ravi",
            "last_name": "Kumar",
            "is_active": True,
        }
    )
    user.set_password("SecurePass123!")
    user.save()

    emp, _ = Employee.objects.get_or_create(
        user=user,
        defaults={
            "company": company,
            "employee_id": f"EMP-{unique_suffix.upper()}",
            "phone": "9876543210",
            "is_online": True,
            "current_availability": "available",
        }
    )
    emp.is_online = True
    emp.current_availability = "available"

    emp.bank_details = {
        "onboarding": {
            "status": "approved",
            "services": [
                {"name": "Pipe Repair Test", "category": "plumbing-test", "status": "approved"},
                {"name": "Plumbing Test", "category": "plumbing-test", "status": "approved"}
            ],
            "documents": {
                "id_proof": {"status": "approved"},
                "address_proof": {"status": "approved"}
            }
        }
    }
    emp.save(update_fields=["bank_details"])

    return company, emp, "plumbing-test"


def run_tests():
    print("\n" + "=" * 70)
    print("RUNNING CALTRACK JOBS & INCOMING OFFERS TEST SUITE")
    print("=" * 70)

    company, emp, category_slug = setup_test_environment()
    factory = APIRequestFactory()
    today = timezone.localdate()
    now = timezone.now()

    # Step 1: Create an active job assigned to this technician
    active_sr = ServiceRequest.objects.create(
        customer=None,
        service_category=category_slug,
        issue_title="Active Pipe Leak Emergency",
        description="Emergency water leak fix in progress",
        preferred_date=today,
        address="100 MG Road, Bangalore",
        latitude=12.9720,
        longitude=77.5950,
        assigned_employee=emp,
        status="in_progress",
        company=company,
    )
    emp.current_availability = "busy"
    emp.save(update_fields=["current_availability"])

    print(f"\n[SETUP] Active Job created: SR #{active_sr.id} (status: {active_sr.status})")
    print(f"[SETUP] Technician #{emp.id} is_online={emp.is_online}, availability={emp.current_availability}")

    # Test 1: Dual-purpose eligibility checks
    print("\n--- TEST 1: Dual-purpose eligibility engine ---")
    can_recv, r_recv, _ = check_candidate_eligibility(emp, active_sr, purpose="offer_reception")
    can_acc, r_acc, _ = check_candidate_eligibility(emp, active_sr, purpose="acceptance")

    print(f"  • check_candidate_eligibility(purpose='offer_reception'): {can_recv} ({r_recv})")
    print(f"  • check_candidate_eligibility(purpose='acceptance'): {can_acc} ({r_acc})")

    assert can_recv is True, f"Expected offer_reception eligibility to be True, got {r_recv}"
    assert can_acc is False, f"Expected acceptance eligibility to be False, got {r_acc}"
    recv_ok, recv_reason = can_receive_offer(emp, active_sr)
    acc_ok, acc_reason = can_accept_offer(emp, active_sr)
    assert recv_ok is True, f"can_receive_offer returned False: {recv_reason}"
    assert acc_ok is False, f"can_accept_offer should be False for busy technician: {acc_reason}"
    print("  [PASS] Gate 7/9 correctly distinguishes offer reception vs acceptance for busy technician.")

    # Test 2: Create 5 incoming offers for today
    print("\n--- TEST 2: Multi-offer dispatch (5 incoming offers) ---")
    offers = []
    incoming_srs = []
    for i in range(1, 6):
        sr = ServiceRequest.objects.create(
            customer=None,
            service_category=category_slug,
            issue_title=f"Incoming Service Offer #{i}",
            preferred_date=today,
            address=f"Location {i}, Bangalore",
            latitude=12.9718 + (i * 0.001),
            longitude=77.5948 + (i * 0.001),
            status="assigned",
            company=company,
        )
        offer = WorkforceJobOffer.objects.create(
            job=sr,
            employee=emp,
            status="OFFERED",
            offered_at=now,
            expires_at=now + timedelta(minutes=15),
        )
        incoming_srs.append(sr)
        offers.append(offer)

    print(f"  • Created 5 concurrent unexpired offers for technician #{emp.id}")
    assert len(offers) == 5
    print("  [PASS] Multiple offers registered in database.")

    # Test 3: WorkforceJobListView query returns active job AND all 5 offers
    print("\n--- TEST 3: WorkforceJobListView query visibility ---")
    request = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(request, user=emp.user)
    view = WorkforceJobListView.as_view()
    response = view(request)

    assert response.status_code == status.HTTP_200_OK, f"Expected 200, got {response.status_code}"
    returned_jobs = response.data if isinstance(response.data, list) else response.data.get("results", [])
    returned_ids = {j["id"] for j in returned_jobs}

    print(f"  • WorkforceJobListView returned {len(returned_jobs)} jobs: {sorted(list(returned_ids))}")
    assert active_sr.id in returned_ids, f"Active job #{active_sr.id} missing from response!"
    for sr in incoming_srs:
        assert sr.id in returned_ids, f"Incoming offer job #{sr.id} missing from response!"

    print("  [PASS] Active job and ALL 5 incoming offers returned simultaneously in response.")

    # Test 4: Attempt to accept an incoming offer while active job exists -> 409 EMPLOYEE_ALREADY_BUSY
    print("\n--- TEST 4: Acceptance blocking while on active job (409) & Offer preservation ---")
    target_sr = incoming_srs[0]
    target_offer = offers[0]

    accept_req = factory.post(f"/api/workforce/jobs/{target_sr.id}/accept-offer/")
    force_authenticate(accept_req, user=emp.user)
    accept_view = WorkforceJobAcceptOfferView.as_view()
    accept_resp = accept_view(accept_req, pk=target_sr.id)

    print(f"  • Accept offer response code: {accept_resp.status_code}")
    print(f"  • Accept offer payload: {accept_resp.data}")

    assert accept_resp.status_code == status.HTTP_409_CONFLICT, f"Expected 409, got {accept_resp.status_code}"
    assert accept_resp.data.get("code") == "EMPLOYEE_ALREADY_BUSY", f"Expected EMPLOYEE_ALREADY_BUSY, got {accept_resp.data.get('code')}"

    # Verify offer status was NOT mutated to ACCEPTED
    target_offer.refresh_from_db()
    print(f"  • Offer #{target_offer.id} status in DB after 409: {target_offer.status}")
    assert target_offer.status == "OFFERED", f"Expected OFFERED, but got {target_offer.status}! Offer was corrupted!"
    print("  [PASS] Offer correctly blocked with 409 and preserved in OFFERED state.")

    # Test 5: Complete active job -> Now acceptance succeeds!
    print("\n--- TEST 5: Complete active job & verify successful acceptance ---")
    active_sr.status = "completed"
    active_sr.save(update_fields=["status"])
    emp.current_availability = "available"
    emp.save(update_fields=["current_availability"])

    # Create competing offer for another technician on target_sr to verify SUPERSEDED_BY_ACCEPTANCE
    other_u_id = uuid.uuid4().hex[:6]
    other_user, _ = User.objects.get_or_create(
        username=f"other_tech_{other_u_id}",
        defaults={"email": f"other_{other_u_id}@caltrack.com", "first_name": "Test", "last_name": "Other"}
    )
    other_emp, _ = Employee.objects.get_or_create(
        user=other_user,
        defaults={"company": company, "employee_id": f"EMP-{other_u_id.upper()}"}
    )
    competing_offer = WorkforceJobOffer.objects.create(
        job=target_sr,
        employee=other_emp,
        status="OFFERED",
        offered_at=now,
        expires_at=now + timedelta(minutes=15),
    )

    accept_req2 = factory.post(f"/api/workforce/jobs/{target_sr.id}/accept-offer/")
    force_authenticate(accept_req2, user=emp.user)
    accept_resp2 = accept_view(accept_req2, pk=target_sr.id)

    print(f"  • Accept response after completion: {accept_resp2.status_code}")
    assert accept_resp2.status_code == status.HTTP_200_OK, f"Expected 200 OK, got {accept_resp2.data}"

    target_offer.refresh_from_db()
    target_sr.refresh_from_db()
    competing_offer.refresh_from_db()

    print(f"  • Accepted offer status: {target_offer.status}")
    print(f"  • Job assigned employee: {target_sr.assigned_employee_id}")
    print(f"  • Competing offer status: {competing_offer.status}")

    assert target_offer.status == "ACCEPTED", f"Expected ACCEPTED, got {target_offer.status}"
    assert target_sr.assigned_employee == emp, "Job was not assigned to technician!"
    assert competing_offer.status == "SUPERSEDED_BY_ACCEPTANCE", f"Expected SUPERSEDED_BY_ACCEPTANCE, got {competing_offer.status}"
    print("  [PASS] Acceptance succeeds once active job completes; competing offers superseded.")

    # Test 6: Reject an offer -> transitions to REJECTED and disappears from active list
    print("\n--- TEST 6: WorkforceJobRejectOfferView decline flow ---")
    declined_sr = incoming_srs[1]
    declined_offer = offers[1]

    reject_req = factory.post(f"/api/workforce/jobs/{declined_sr.id}/reject-offer/", {"reason": "Distance too far"})
    force_authenticate(reject_req, user=emp.user)
    reject_view = WorkforceJobRejectOfferView.as_view()
    reject_resp = reject_view(reject_req, pk=declined_sr.id)

    assert reject_resp.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT], f"Expected 200, got {reject_resp.status_code}"

    declined_offer.refresh_from_db()
    print(f"  • Declined offer #{declined_offer.id} status in DB: {declined_offer.status}")
    assert declined_offer.status == "REJECTED", f"Expected REJECTED, got {declined_offer.status}"

    # Verify declined offer is omitted from active job list
    list_req = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(list_req, user=emp.user)
    list_resp = view(list_req)
    current_active_ids = {j["id"] for j in list_resp.data}
    print(f"  • Jobs in active queue after decline: {current_active_ids}")
    assert declined_sr.id not in current_active_ids, f"Declined job #{declined_sr.id} should NOT be in active queue!"
    print("  [PASS] Offer decline immediately updates status and removes from active queue.")

    print("\n" + "=" * 70)
    print("ALL 6 TESTS PASSED SUCCESSFULLY! ZERO ERRORS DETECTED.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_tests()
