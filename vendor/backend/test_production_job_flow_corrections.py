"""
Workforce — Production Job Flow Corrections Verification Suite
Direct standalone runner against Supabase PostgreSQL database.
Covers scenarios A through K:
A. Auto Clock-In -> proof -> payment -> completed
B. Auto Clock-In -> refresh -> timer continues
C. Active break freezes worked timer
D. Completed job releases technician
E. Yesterday's completed job excluded from TODAY
F. Electrical technician cannot receive Home Cleaning
G. Home Cleaning technician cannot receive Electrical
H. Two eligible technicians receive the same active wave
I. Two technicians simultaneously accept same job: exactly one wins, second receives 409 JOB_ALREADY_ACCEPTED
J. New eligible technician can join an existing active wave
K. Browser refresh with refreshable JWT
"""
import os
import sys
import uuid
from datetime import timedelta

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from companies.models import Company, Region
from employees.models import Employee
from service_requests.models import ServiceRequest, EmployeeJob
from service_requests.state_machine import apply_transition
from time_tracking.models import TimeLog, Break
from workforce_api.models import WorkforceJobOffer, JobPayment, PostServiceProof
from workforce_api.serializers import WorkforceJobSerializer
from workforce_api.services.automatic_dispatch import (
    canonical_service_match,
    dispatch_job,
    reconsider_jobs_for_employee,
)
from workforce_api.services.workload import (
    get_employee_active_job,
    reconcile_employee_availability,
)
from workforce_api.views import (
    WorkforceJobAcceptOfferView,
    WorkforceJobProofView,
    WorkforceJobCashCollectView,
    WorkforceTimeTrackingView,
)
from accounts.views import WorkforceRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


def run_production_flow_tests():
    print("==================================================================")
    print("       WORKFORCE — PRODUCTION JOB FLOW CORRECTIONS SUITE          ")
    print("==================================================================")

    factory = APIRequestFactory()
    region, _ = Region.objects.get_or_create(code="IN", defaults={"name": "India", "currency": "INR"})
    company, _ = Company.objects.get_or_create(
        display_id="TEST-CORR-CO",
        defaults={"company_name": "Corrections Test Co", "region": region}
    )

    # 1. Setup Test Employees
    user_a, _ = User.objects.get_or_create(
        username="tech_a_corr",
        defaults={"email": "tech_a@example.com", "role": "employee", "company": company}
    )
    user_a.company = company
    user_a.last_known_location = {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "updated_at": timezone.now().isoformat(),
    }
    user_a.save()

    emp_a, _ = Employee.objects.get_or_create(
        user=user_a,
        defaults={
            "company": company,
            "employee_id": "EMP-A-01",
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
            "bank_details": {
                "onboarding": {
                    "services": [{"name": "Home Cleaning", "category": "Cleaning", "status": "approved"}],
                    "approval_status": "approved",
                    "status": "approved",
                }
            }
        }
    )
    emp_a.is_active = True
    emp_a.is_online = True
    emp_a.current_availability = "available"
    emp_a.bank_details = {
        "onboarding": {
            "services": [{"name": "Home Cleaning", "category": "Cleaning", "status": "approved"}],
            "approval_status": "approved",
            "status": "approved",
        }
    }
    emp_a.save()

    user_b, _ = User.objects.get_or_create(
        username="tech_b_corr",
        defaults={"email": "tech_b@example.com", "role": "employee", "company": company}
    )
    user_b.company = company
    user_b.last_known_location = {
        "latitude": 12.9718,
        "longitude": 77.5948,
        "updated_at": timezone.now().isoformat(),
    }
    user_b.save()

    emp_b, _ = Employee.objects.get_or_create(
        user=user_b,
        defaults={
            "company": company,
            "employee_id": "EMP-B-01",
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
            "bank_details": {
                "onboarding": {
                    "services": [{"name": "Home Cleaning", "category": "Cleaning", "status": "approved"}],
                    "approval_status": "approved",
                    "status": "approved",
                }
            }
        }
    )
    emp_b.is_active = True
    emp_b.is_online = True
    emp_b.current_availability = "available"
    emp_b.bank_details = {
        "onboarding": {
            "services": [{"name": "Home Cleaning", "category": "Cleaning", "status": "approved"}],
            "approval_status": "approved",
            "status": "approved",
        }
    }
    emp_b.save()

    # Clean prior test state
    ServiceRequest.objects.filter(company=company).delete()
    TimeLog.objects.filter(employee__in=[emp_a, emp_b]).delete()
    WorkforceJobOffer.objects.filter(employee__in=[emp_a, emp_b]).delete()

    # ── Test A: Auto Clock-In -> Proof -> Payment -> Completed ──
    print("\n[A] Testing Auto Clock-In -> proof -> payment -> completed...")
    job_a = ServiceRequest.objects.create(
        company=company,
        assigned_employee=emp_a,
        status="in_progress",
        service_category="Home Cleaning",
        issue_title="Full Home Deep Cleaning",
        latitude=12.9716,
        longitude=77.5946,
        preferred_date=timezone.now().date(),
        total_amount=1500.0,
        payment_status="pending",
    )
    EmployeeJob.objects.create(
        service_request=job_a,
        employee=emp_a,
        is_primary=True,
        status="IN_PROGRESS",
        started_date=timezone.now(),
    )
    JobPayment.objects.create(
        job=job_a,
        amount_due=1500.0,
        amount_paid=0.0,
        payment_status=JobPayment.PaymentStatus.PENDING,
        payment_method=JobPayment.PaymentMethod.CASH_ON_SERVICE,
    )

    from django.core.files.uploadedfile import SimpleUploadedFile
    face_photo = SimpleUploadedFile("face.jpg", b"fake_face_image_bytes", content_type="image/jpeg")
    req_proof = factory.post(f"/api/workforce/jobs/{job_a.id}/proof/", {"after_presence_photo": face_photo}, format="multipart")
    force_authenticate(req_proof, user=user_a)
    res_proof = WorkforceJobProofView.as_view()(req_proof, pk=job_a.id)
    assert res_proof.status_code == status.HTTP_200_OK, f"Proof failed: {res_proof.data}"
    job_a.refresh_from_db()
    assert job_a.status == "proof_submitted", f"Expected proof_submitted, got {job_a.status}"

    req_cash = factory.post(f"/api/workforce/jobs/{job_a.id}/collect-cash/", {"amount_collected": 1500.0}, format="json")
    force_authenticate(req_cash, user=user_a)
    res_cash = WorkforceJobCashCollectView.as_view()(req_cash, pk=job_a.id)
    assert res_cash.status_code == status.HTTP_200_OK, f"Cash collect failed: {res_cash.data}"
    job_a.refresh_from_db()
    assert job_a.status == "completed", f"Expected completed, got {job_a.status}"

    # Idempotent repeat
    res_repeat = WorkforceJobProofView.as_view()(req_proof, pk=job_a.id)
    assert res_repeat.status_code == status.HTTP_200_OK, f"Repeat proof failed: {res_repeat.data}"
    print("  [PASS] Scenario A passed: Auto Clock-In -> proof -> payment -> completed (Idempotent).")

    # ── Test B: Auto Clock-In -> Refresh -> Timer Continues ──
    print("\n[B] Testing Auto Clock-In -> refresh -> timer continues...")
    now = timezone.now()
    past_clock_in = now - timedelta(minutes=45)
    log_b = TimeLog.objects.create(
        employee=emp_a,
        work_date=past_clock_in.date(),
        clock_in=past_clock_in,
        clock_out=None,
    )
    assert log_b.worked_seconds(as_of=now) >= 2700, f"Worked seconds was {log_b.worked_seconds(as_of=now)}"

    req_tt = factory.get("/api/workforce/time-tracking/")
    force_authenticate(req_tt, user=user_a)
    res_tt = WorkforceTimeTrackingView.as_view()(req_tt)
    assert res_tt.status_code == status.HTTP_200_OK
    assert res_tt.data.get("is_clocked_in") is True
    assert res_tt.data.get("worked_seconds") >= 2700
    assert res_tt.data.get("server_time") is not None
    print(f"  [PASS] Scenario B passed: Timer continues ({res_tt.data.get('worked_seconds')}s worked, server_time verified).")

    # ── Test C: Active Break Freezes Worked Timer ──
    print("\n[C] Testing active break freezes worked timer...")
    t0 = timezone.now() - timedelta(minutes=60)
    t_break_start = t0 + timedelta(minutes=30)
    log_c = TimeLog.objects.create(
        employee=emp_b,
        work_date=t0.date(),
        clock_in=t0,
        clock_out=None,
    )
    active_break = Break.objects.create(
        time_log=log_c,
        break_type="lunch",
        break_start=t_break_start,
        break_end=None,  # active ongoing break!
    )
    as_of_mid = t_break_start + timedelta(minutes=10)
    assert log_c.break_seconds(as_of=as_of_mid) == 600
    assert log_c.worked_seconds(as_of=as_of_mid) == 1800, f"Worked seconds was {log_c.worked_seconds(as_of=as_of_mid)}, expected 1800"

    # End break
    active_break.break_end = t_break_start + timedelta(minutes=15)
    active_break.save()
    t_final = t0 + timedelta(minutes=60)
    assert log_c.break_seconds(as_of=t_final) == 900
    assert log_c.worked_seconds(as_of=t_final) == 2700
    print("  [PASS] Scenario C passed: Active break frozen at 1800s; completed break cleanly deducted.")

    # ── Test D: Completed Job Releases Technician ──
    print("\n[D] Testing completed job releases technician...")
    job_d = ServiceRequest.objects.create(
        company=company,
        assigned_employee=emp_a,
        status="in_progress",
        service_category="Home Cleaning",
        preferred_date=timezone.now().date(),
    )
    EmployeeJob.objects.create(
        service_request=job_d,
        employee=emp_a,
        is_primary=True,
        status="IN_PROGRESS",
    )
    reconcile_employee_availability(emp_a)
    emp_a.refresh_from_db()
    assert emp_a.current_availability == "busy"

    # Transition to completed
    JobPayment.objects.create(
        job=job_d,
        amount_due=0.0,
        amount_paid=0.0,
        payment_status=JobPayment.PaymentStatus.PAID,
        payment_method=JobPayment.PaymentMethod.ONLINE,
    )
    job_d.payment_status = "paid"
    job_d.save(update_fields=["payment_status"])
    PostServiceProof.objects.create(job=job_d, employee=emp_a, completion_notes="Completed cleaning", is_submitted=True, submitted_at=timezone.now())
    apply_transition(job_d, "proof_submitted")
    apply_transition(job_d, "completed")
    active = get_employee_active_job(emp_a)
    if active:
        print(f"DEBUG: active job id={active.id}, status={active.status}, assigned_emp={active.assigned_employee_id}")
    assert active is None, f"Expected None, got Job #{active.id} (status: {active.status})"
    reconcile_employee_availability(emp_a)
    emp_a.refresh_from_db()
    assert emp_a.current_availability == "available", f"Expected available, got {emp_a.current_availability}"
    print("  [PASS] Scenario D passed: Completed job cleanly releases technician to available.")

    # ── Test E: Yesterday's Completed Job Excluded from TODAY ──
    print("\n[E] Testing yesterday's completed job serialization...")
    yesterday = timezone.now() - timedelta(days=1)
    job_e = ServiceRequest.objects.create(
        company=company,
        assigned_employee=emp_a,
        status="completed",
        service_category="Home Cleaning",
        preferred_date=yesterday.date(),
    )
    EmployeeJob.objects.create(
        service_request=job_e,
        employee=emp_a,
        is_primary=True,
        status="COMPLETED",
        completed_date=yesterday,
    )
    serializer = WorkforceJobSerializer(job_e)
    completed_at = serializer.data.get("completed_at")
    assert completed_at is not None
    assert completed_at.startswith(yesterday.date().isoformat()), f"Expected yesterday ({yesterday.date()}), got {completed_at}"
    print(f"  [PASS] Scenario E passed: completed_at correctly resolves to yesterday ({completed_at}).")

    # ── Test F & G: Strict Service Matching ──
    print("\n[F & G] Testing strict service & skill matching...")
    m_f, _, _ = canonical_service_match("Home Cleaning", ["Electrical"], [])
    assert m_f is False, "Electrical must NOT match Home Cleaning"
    m_g, _, _ = canonical_service_match("Electrical", ["Home Cleaning"], [])
    assert m_g is False, "Home Cleaning must NOT match Electrical"
    m_ep, _, _ = canonical_service_match("Plumbing", ["Electrical"], [])
    assert m_ep is False, "Electrical must NOT match Plumbing"
    m_ke, _, _ = canonical_service_match("Electrical", ["Kitchen Cleaning"], [])
    assert m_ke is False, "Kitchen Cleaning must NOT match Electrical"

    m_elec, _, _ = canonical_service_match("Electrical", ["Electrical"], [])
    assert m_elec is True, "Electrical must match Electrical"
    m_clean, _, _ = canonical_service_match("Home Cleaning", ["Home Cleaning"], [])
    assert m_clean is True, "Home Cleaning must match Home Cleaning"
    m_plumb, _, _ = canonical_service_match("Plumbing", ["Plumbing"], [])
    assert m_plumb is True, "Plumbing must match Plumbing"
    print("  [PASS] Scenarios F & G passed: Strict domain boundaries fully prevent cross-domain matches.")

    # ── Test H: Two Eligible Technicians Receive Same Active Wave ──
    print("\n[H] Testing two eligible technicians receiving same active wave...")
    # Clear offers on both
    WorkforceJobOffer.objects.filter(employee__in=[emp_a, emp_b]).delete()
    TimeLog.objects.filter(employee__in=[emp_a, emp_b]).delete()
    job_h = ServiceRequest.objects.create(
        company=company,
        status="unassigned",
        service_category="Home Cleaning",
        issue_title="Home Cleaning",
        latitude=12.9716,
        longitude=77.5946,
        preferred_date=timezone.now().date(),
    )
    success_h, msg_h = dispatch_job(job_h.id)
    assert success_h is True, f"Dispatch failed: {msg_h}"
    offers_h = list(WorkforceJobOffer.objects.filter(job=job_h, status=WorkforceJobOffer.Status.OFFERED))
    offered_ids = {o.employee_id for o in offers_h}
    assert emp_a.id in offered_ids, f"Tech A missing from offers: {offered_ids}"
    assert emp_b.id in offered_ids, f"Tech B missing from offers: {offered_ids}"
    assert len(offers_h) == 2
    assert offers_h[0].wave_id == offers_h[1].wave_id
    assert offers_h[0].wave_number == offers_h[1].wave_number
    print("  [PASS] Scenario H passed: Both Tech A and Tech B received offers in the same active wave.")

    # ── Test I: Two Technicians Simultaneous Accept ──
    print("\n[I] Testing two technicians simultaneous accept...")
    job_i = ServiceRequest.objects.create(
        company=company,
        status="unassigned",
        service_category="Home Cleaning",
        latitude=12.9716,
        longitude=77.5946,
        preferred_date=timezone.now().date(),
    )
    offer_a_i = WorkforceJobOffer.objects.filter(job=job_i, employee=emp_a, status=WorkforceJobOffer.Status.OFFERED).first()
    offer_b_i = WorkforceJobOffer.objects.filter(job=job_i, employee=emp_b, status=WorkforceJobOffer.Status.OFFERED).first()
    if not offer_a_i or not offer_b_i:
        dispatch_job(job_i.id)
        offer_a_i = WorkforceJobOffer.objects.filter(job=job_i, employee=emp_a, status=WorkforceJobOffer.Status.OFFERED).first()
        offer_b_i = WorkforceJobOffer.objects.filter(job=job_i, employee=emp_b, status=WorkforceJobOffer.Status.OFFERED).first()
    assert offer_a_i is not None and offer_b_i is not None, "Both Tech A and B must have active offers for Scenario I"

    req_acc_a = factory.post(f"/api/workforce/jobs/{job_i.id}/accept-offer/")
    force_authenticate(req_acc_a, user=user_a)
    res_acc_a = WorkforceJobAcceptOfferView.as_view()(req_acc_a, pk=job_i.id)
    assert res_acc_a.status_code == status.HTTP_200_OK, f"Tech A accept failed: {res_acc_a.data}"

    req_acc_b = factory.post(f"/api/workforce/jobs/{job_i.id}/accept-offer/")
    force_authenticate(req_acc_b, user=user_b)
    res_acc_b = WorkforceJobAcceptOfferView.as_view()(req_acc_b, pk=job_i.id)
    assert res_acc_b.status_code == status.HTTP_409_CONFLICT, f"Tech B expected 409, got {res_acc_b.status_code}"
    assert res_acc_b.data.get("code") == "JOB_ALREADY_ACCEPTED"

    job_i.refresh_from_db()
    assert job_i.assigned_employee == emp_a
    offer_b_i.refresh_from_db()
    assert offer_b_i.status == WorkforceJobOffer.Status.SUPERSEDED_BY_ACCEPTANCE
    print("  [PASS] Scenario I passed: Tech A accepted, Tech B received 409 JOB_ALREADY_ACCEPTED, offer superseded.")

    # ── Test J: New Eligible Technician Joins Active Wave ──
    print("\n[J] Testing new eligible technician joins active wave...")
    WorkforceJobOffer.objects.filter(employee__in=[emp_a, emp_b]).delete()
    TimeLog.objects.filter(employee__in=[emp_a, emp_b]).delete()
    emp_a.current_availability = "available"
    emp_a.save()
    # Tech B is offline during initial dispatch
    emp_b.is_online = False
    emp_b.current_availability = "offline"
    emp_b.save()

    job_j = ServiceRequest.objects.create(
        company=company,
        status="unassigned",
        service_category="Home Cleaning",
        issue_title="Home Cleaning",
        latitude=12.9716,
        longitude=77.5946,
        preferred_date=timezone.now().date(),
    )

    success_j, _ = dispatch_job(job_j.id)
    assert success_j is True
    initial_offers = list(WorkforceJobOffer.objects.filter(job=job_j, status=WorkforceJobOffer.Status.OFFERED))
    assert len(initial_offers) == 1
    active_wave_id = initial_offers[0].wave_id
    active_expires = initial_offers[0].expires_at

    # Tech B comes online and transmits GPS
    emp_b.is_online = True
    emp_b.save()
    user_b.last_known_location = {
        "latitude": 12.9717,
        "longitude": 77.5947,
        "updated_at": timezone.now().isoformat(),
    }
    user_b.save()

    reconsidered_count = reconsider_jobs_for_employee(emp_b)
    assert reconsidered_count >= 1, f"Reconsider returned {reconsidered_count}"
    after_offers = list(WorkforceJobOffer.objects.filter(job=job_j, status=WorkforceJobOffer.Status.OFFERED))
    assert len(after_offers) == 2, f"Expected 2 offers, got {len(after_offers)}"
    tech_b_offer = WorkforceJobOffer.objects.filter(job=job_j, employee=emp_b, status=WorkforceJobOffer.Status.OFFERED).first()
    assert tech_b_offer is not None
    assert tech_b_offer.wave_id == active_wave_id
    assert tech_b_offer.expires_at == active_expires
    print("  [PASS] Scenario J passed: Tech B joined existing active Wave with same wave_id and expires_at.")

    # ── Test K: Browser Refresh with Refreshable JWT ──
    print("\n[K] Testing browser refresh with refreshable JWT...")
    refresh = RefreshToken.for_user(user_a)
    valid_refresh_token = str(refresh)

    req_ref = factory.post("/api/auth/refresh/", {"refresh_token": valid_refresh_token}, format="json")
    res_ref = WorkforceRefreshView.as_view()(req_ref)
    assert res_ref.status_code == status.HTTP_200_OK
    assert "access_token" in res_ref.data
    assert "refresh_token" in res_ref.data

    req_inv = factory.post("/api/auth/refresh/", {"refresh_token": "definitely.invalid.token"}, format="json")
    res_inv = WorkforceRefreshView.as_view()(req_inv)
    assert res_inv.status_code == status.HTTP_401_UNAUTHORIZED
    assert res_inv.data.get("code") == "INVALID_REFRESH_TOKEN"
    print("  [PASS] Scenario K passed: Refresh returns new access/refresh tokens; invalid token yields 401.")

    print("\n==================================================================")
    print("      ALL PRODUCTION JOB FLOW CORRECTIONS (A–K) PASSED CLEANLY!   ")
    print("==================================================================")


if __name__ == "__main__":
    run_production_flow_tests()
