#!/usr/bin/env python
"""
backend/test_estimation_employee_jobs_visibility.py

Verifies that estimation leads:
1. Appear in the technician's active jobs and offers queues.
2. Have NO expiration timer: they remain visible and offerable indefinitely until accepted or declined.
3. Are never expired by automatic dispatch sweeps (expire_and_reassign_offers).
4. Can be accepted without OFFER_EXPIRED rejections.
5. Can be declined, which properly dismisses the estimation offer from the declining technician's queue.
6. Remain visible across all active progression lifecycle states (technician_on_the_way, arrived, inspection, quote sent, approved, etc.).
"""
import os
import sys
from decimal import Decimal
from datetime import timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from rest_framework.test import APIRequestFactory, force_authenticate
from django.utils import timezone
from django.contrib.auth import get_user_model
from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest, Estimation, EstimationFee, EmployeeJob
from workforce_api.models import WorkforceJobOffer
from workforce_api.views import WorkforceJobListView, WorkforceJobAcceptOfferView, WorkforceJobRejectOfferView
from workforce_api.services.workload import ACTIVE_QUEUE_STATUSES
from workforce_api.services.automatic_dispatch import expire_and_reassign_offers

User = get_user_model()

def run_verification():
    print("=" * 75)
    print("  VERIFY ESTIMATION NON-EXPIRING DISPATCH & EMPLOYEE QUEUE VISIBILITY")
    print("=" * 75)

    # 1. Setup Company and Technicians
    company, _ = Company.objects.get_or_create(
        slug="test-est-co",
        defaults={"company_name": "Test Estimation Co", "is_active": True}
    )

    tech_user, _ = User.objects.get_or_create(
        username="tech_est_test",
        defaults={"first_name": "Test", "last_name": "Technician", "role": "employee", "is_active": True}
    )
    tech_emp, _ = Employee.objects.get_or_create(
        user=tech_user,
        defaults={
            "company": company,
            "employee_id": "EMP-TEST-EST-01",
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
            "bank_details": {"onboarding": {"status": "approved"}},
        }
    )
    tech_emp.company = company
    tech_emp.is_active = True
    tech_emp.is_online = True
    tech_emp.current_availability = "available"
    tech_emp.bank_details = {"onboarding": {"status": "approved"}}
    tech_emp.save()

    # Clean up prior test records
    ServiceRequest.objects.filter(request_id__in=["TEST-EST-OFFER-01", "TEST-EST-DECLINE-01", "TEST-EST-QUEUE-01"]).delete()

    factory = APIRequestFactory()

    # ── TEST 1: Estimation Offer Non-Expiration & Queue Presence ──
    print("\n[Step 1] Creating Estimation Booking in OFFERED state...")
    sr_offer = ServiceRequest.objects.create(
        request_id="TEST-EST-OFFER-01",
        company=company,
        service_category="HVAC & Air Conditioning",
        issue_title="AC Inspection & Estimation",
        description="AC not cooling, inspection required.",
        preferred_date=timezone.now().date(),
        preferred_time="11:00 AM - 02:00 PM",
        job_type="ESTIMATION",
        request_kind="estimation",
        start_otp="991122",
        total_amount=Decimal("199.00"),
        status="unassigned",
    )
    est_offer = Estimation.objects.create(
        service_request=sr_offer,
        ac_type="SPLIT",
        ac_brand="Voltas",
        ac_capacity="1.5_TON",
        customer_symptom="No cooling",
        status="REQUESTED",
    )
    EstimationFee.objects.create(
        estimation=est_offer,
        amount=Decimal("199.00"),
        status="PENDING",
    )

    # Create an offer whose original timestamp would be considered "expired" under standard 5-minute rules
    past_time = timezone.now() - timedelta(minutes=30)
    offer = WorkforceJobOffer.objects.create(
        job=sr_offer,
        employee=tech_emp,
        status="OFFERED",
        rank_score=95.0,
        offered_at=past_time,
        expires_at=past_time,  # Intentionally past time to test estimation non-expiry bypass
    )

    print("  -> Offer created with past timestamp (simulating elapsed time).")

    # Run auto-expiry sweep
    expired_count = expire_and_reassign_offers()
    offer.refresh_from_db()
    assert offer.status == "OFFERED", f"Expected offer to remain OFFERED, got {offer.status}!"
    print(f"  [PASS] expire_and_reassign_offers did not expire the estimation offer (status={offer.status}).")

    # Fetch technician jobs list
    req = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req, user=tech_user)
    view = WorkforceJobListView.as_view()
    resp = view(req)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    job_data = next((j for j in resp.data if j["id"] == sr_offer.id), None)
    assert job_data is not None, "Offered estimation job not visible in technician jobs list!"
    assert job_data.get("is_offer") is True, f"Expected is_offer=True, got {job_data.get('is_offer')}"
    assert job_data.get("offer_status") == "OFFERED", f"Expected offer_status='OFFERED', got {job_data.get('offer_status')}"
    assert job_data.get("offer_expires_at") is None, f"Expected offer_expires_at=None (no countdown timer), got {job_data.get('offer_expires_at')}"
    assert job_data.get("active_offer", {}).get("expires_at") is None, f"Expected active_offer.expires_at=None, got {job_data.get('active_offer')}"
    assert job_data.get("estimation_details") is not None, "Expected estimation_details to be present."
    print("  [PASS] Estimation offer displays correctly without expiration countdown in technician queue.")

    # ── TEST 2: Accept Estimation Offer ──
    print("\n[Step 2] Testing Technician Accept Offer for Estimation...")
    accept_view = WorkforceJobAcceptOfferView.as_view()
    acc_req = factory.post(f"/api/workforce/jobs/{sr_offer.id}/accept-offer/")
    force_authenticate(acc_req, user=tech_user)
    acc_resp = accept_view(acc_req, pk=sr_offer.id)
    assert acc_resp.status_code == 200, f"Accept failed with {acc_resp.status_code}: {acc_resp.data}"
    
    sr_offer.refresh_from_db()
    assert sr_offer.assigned_employee == tech_emp, "Technician was not assigned to the estimation job!"
    assert sr_offer.status == "accepted", f"Expected status='accepted', got {sr_offer.status}"
    print(f"  [PASS] Estimation offer accepted successfully (status={sr_offer.status}, assigned={tech_emp.employee_id}).")

    # ── TEST 3: Full Progression Lifecycle Queue Visibility on Accepted Job ──
    print("\n[Step 3] Testing Visibility Across Entire Estimation & Execution Progression Lifecycle...")
    estimation_statuses = [
        "technician_assigned",
        "technician_on_the_way",
        "technician_arrived",
        "inspection_in_progress",
        "inspection_completed",
        "quotation_sent",
        "customer_approved",
        "converted_to_job",
        "in_progress",
        "proof_submitted",
    ]

    for st in estimation_statuses:
        assert st in ACTIVE_QUEUE_STATUSES, f"Status '{st}' missing from ACTIVE_QUEUE_STATUSES!"
        sr_offer.status = st
        sr_offer.save(update_fields=["status"])
        req_st = factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_st, user=tech_user)
        resp_st = view(req_st)
        st_found = next((j for j in resp_st.data if j["id"] == sr_offer.id), None)
        assert st_found is not None, f"Estimation job not visible at status '{st}'!"
        print(f"  [PASS] Visibility verified at status '{st}'.")

    # Complete sr_offer so tech becomes available for next offer
    sr_offer.status = "completed"
    sr_offer.save(update_fields=["status"])
    tech_emp.current_availability = "available"
    tech_emp.save(update_fields=["current_availability"])

    # ── TEST 4: Decline / Reject Estimation Offer Flow ──
    print("\n[Step 4] Testing Technician Decline Flow for another Estimation...")
    sr_decline = ServiceRequest.objects.create(
        request_id="TEST-EST-DECLINE-01",
        company=company,
        service_category="HVAC & Air Conditioning",
        issue_title="AC Noise Inspection",
        description="Loud grinding noise.",
        preferred_date=timezone.now().date(),
        preferred_time="03:00 PM - 06:00 PM",
        job_type="ESTIMATION",
        request_kind="estimation",
        start_otp="112233",
        total_amount=Decimal("199.00"),
        status="unassigned",
    )
    est_decline = Estimation.objects.create(
        service_request=sr_decline,
        ac_type="WINDOW",
        ac_brand="LG",
        ac_capacity="1.0_TON",
        customer_symptom="Loud noise",
        status="REQUESTED",
    )
    EstimationFee.objects.create(
        estimation=est_decline,
        amount=Decimal("199.00"),
        status="PENDING",
    )
    offer_decline = WorkforceJobOffer.objects.create(
        job=sr_decline,
        employee=tech_emp,
        status="OFFERED",
        rank_score=90.0,
        expires_at=timezone.now() + timedelta(days=365),
    )

    # Verify visible prior to decline
    req_dec = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_dec, user=tech_user)
    resp_before = view(req_dec)
    found_before = next((j for j in resp_before.data if j["id"] == sr_decline.id), None)
    assert found_before is not None, "Estimation job should be visible before decline."
    assert found_before.get("is_offer") is True

    # Technician rejects offer
    reject_view = WorkforceJobRejectOfferView.as_view()
    rej_req = factory.post(f"/api/workforce/jobs/{sr_decline.id}/reject-offer/", {"reason": "Technician unavailable"})
    force_authenticate(rej_req, user=tech_user)
    rej_resp = reject_view(rej_req, pk=sr_decline.id)
    assert rej_resp.status_code == 200, f"Reject failed with {rej_resp.status_code}: {rej_resp.data}"

    offer_decline.refresh_from_db()
    assert offer_decline.status == "REJECTED", f"Expected offer status='REJECTED', got {offer_decline.status}"

    # Verify NO LONGER visible in technician active jobs list after decline
    resp_after = view(req_dec)
    found_after = next((j for j in resp_after.data if j["id"] == sr_decline.id), None)
    assert found_after is None, "Declined estimation job should NO LONGER appear in technician active jobs list!"
    print("  [PASS] Declining the estimation offer successfully removes it from technician view.")

    # Cleanup test records
    print("\n[Step 5] Cleaning up test records...")
    EstimationFee.objects.filter(estimation__service_request__in=[sr_offer, sr_decline]).delete()
    Estimation.objects.filter(service_request__in=[sr_offer, sr_decline]).delete()
    WorkforceJobOffer.objects.filter(job__in=[sr_offer, sr_decline]).delete()
    EmployeeJob.objects.filter(service_request__in=[sr_offer, sr_decline]).delete()
    sr_offer.delete()
    sr_decline.delete()
    tech_emp.is_active = False
    tech_emp.save()

    print("\n" + "=" * 75)
    print("  ALL ESTIMATION DISPATCH, EXPIRY & QUEUE CHECKS PASSED 100%!")
    print("=" * 75)

if __name__ == "__main__":
    run_verification()
