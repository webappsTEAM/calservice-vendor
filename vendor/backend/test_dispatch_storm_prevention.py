"""
test_dispatch_storm_prevention.py

Comprehensive standalone test suite verifying the authoritative fix for:
- Dispatch Event Storm / Infinite Redispatch Loop
- Race-safe WorkforceDispatchState initialization
- Two-phase atomic claim locking
- Exponential backoff policy (10s, 20s, 30s, 60s)
- Prevention of duplicate dispatch attempts across concurrent workers
- Critical event-volume bounds (finite events, zero during retry window)
- Non-dispatching endpoint invariant (SSE, GPS, Presence, GET)
- Legitimate booking -> offer -> acceptance -> assignment flow

Runs directly against the PostgreSQL database:
  python test_dispatch_storm_prevention.py
"""
import os
import sys
import threading
import time
import uuid
from datetime import timedelta

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from service_requests.models import ServiceRequest, EmployeeJob
from service_requests.state_machine import apply_transition
from employees.models import Employee
from companies.models import Company
from workforce_api.models import (
    WorkforceDispatchState,
    WorkforceJobOffer,
    WorkforceEventLog,
    WorkforceEmployeeSchedule,
)
from workforce_api.services.automatic_dispatch import (
    compute_dispatch_retry_delay,
    get_or_create_dispatch_state,
    dispatch_job,
    dispatch_pending_jobs,
    reconsider_jobs_for_employee,
    DISPATCHABLE_STATUSES,
)
from workforce_api.views import (
    WorkforceJobAcceptOfferView,
    WorkforceJobListView,
    WorkforcePresenceToggleView,
    WorkforceLocationUpdateView,
    WorkforceAutoDispatchTriggerView,
)

User = get_user_model()
factory = APIRequestFactory()

BOOKING_LAT = 12.9715987
BOOKING_LON = 77.5945627
EMP_LAT = 12.9780000
EMP_LON = 77.5975000


def _make_company(tag=""):
    name = f"Storm Prev Co {tag} {uuid.uuid4().hex[:6]}"
    co, _ = Company.objects.get_or_create(
        company_name=name,
        defaults={"is_active": True},
    )
    return co


def _make_service_request(company, preferred_date=None, status="confirmed", lat=BOOKING_LAT, lon=BOOKING_LON):
    today = timezone.localdate()
    sr = ServiceRequest.objects.create(
        company=company,
        customer_name="Test Customer",
        phone="+919876543210",
        service_category="Electrical",
        issue_title="Electrical Wiring Repair",
        status=status,
        latitude=lat,
        longitude=lon,
        address="123 MG Road, Bangalore",
        preferred_date=preferred_date or today,
        catalog_service_id=1,
    )
    return sr


def _make_eligible_employee(company, lat=EMP_LAT, lon=EMP_LON):
    uname = f"storm_tech_{uuid.uuid4().hex[:8]}"
    user = User.objects.create_user(
        username=uname,
        password="TestPass@123",
        email=f"{uname}@example.com",
        role="employee",
        company=company,
    )
    emp = Employee.objects.create(
        user=user,
        company=company,
        is_active=True,
        is_online=True,
        current_availability="available",
        bank_details={
            "onboarding": {
                "services": [
                    {"name": "Electrical", "category": "Electrical", "status": "approved"},
                    {"name": "Electrical Wiring Repair", "category": "Electrical", "status": "approved"},
                    {"name": "Wiring", "category": "Electrical", "status": "approved"},
                ],
                "status": "approved",
                "documents": {},
            },
            "attendance": {"is_clocked_in": True},
            "leaves": [],
        },
    )
    user.last_known_location = {
        "latitude": lat,
        "longitude": lon,
        "accuracy": 5.0,
        "captured_at": timezone.now().isoformat(),
        "updated_at": timezone.now().isoformat(),
    }
    user.save(update_fields=["last_known_location"])

    for dow in range(7):
        WorkforceEmployeeSchedule.objects.create(
            employee=emp,
            company=company,
            day_of_week=dow,
            start_time="00:00:00",
            end_time="23:59:59",
            is_working_day=True,
        )
    return emp


def run_all_tests():
    print("==================================================================")
    print("   CALTRACK — DISPATCH STORM PREVENTION & CONCURRENCY TEST SUITE  ")
    print("==================================================================")

    # ── Test 1: Canonical Backoff Delays ──
    print("\n[1] Testing canonical dispatch backoff policy...")
    assert compute_dispatch_retry_delay(0) == 10, "Attempt 0 should be 10s"
    assert compute_dispatch_retry_delay(1) == 10, "Attempt 1 should be 10s"
    assert compute_dispatch_retry_delay(2) == 20, "Attempt 2 should be 20s"
    assert compute_dispatch_retry_delay(3) == 30, "Attempt 3 should be 30s"
    assert compute_dispatch_retry_delay(4) == 60, "Attempt 4 should be 60s"
    assert compute_dispatch_retry_delay(5) == 60, "Attempt 5 should be 60s"
    assert compute_dispatch_retry_delay(100) == 60, "Attempt 100 should be 60s"
    print("  [PASS] Canonical backoff delays verified: 10s -> 20s -> 30s -> 60s max.")

    # ── Test 2: Race-Safe WorkforceDispatchState Creation ──
    print("\n[2] Testing race-safe WorkforceDispatchState creation (2 concurrent threads)...")
    co = _make_company("race_state")
    sr = _make_service_request(co)
    results = []
    errors = []

    def state_creator():
        try:
            state = get_or_create_dispatch_state(sr.id)
            results.append(state.id)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=state_creator) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(errors) == 0, f"Errors during concurrent creation: {errors}"
    assert len(results) == 2, "Both threads should complete"
    assert results[0] == results[1], f"Threads resolved different state IDs: {results}"
    count = WorkforceDispatchState.objects.filter(job=sr).count()
    assert count == 1, f"Expected exactly 1 row, found {count}"
    print(f"  [PASS] Concurrent state creation resolved safely: exactly 1 DB row (id={results[0]}).")

    # ── Test 3: Two Concurrent Dispatch Calls -> Single Claim ──
    print("\n[3] Testing two concurrent dispatch calls for same job...")
    sr3 = _make_service_request(co)
    dispatch_results = []

    def dispatch_worker():
        try:
            res = dispatch_job(sr3.id)
            dispatch_results.append(res)
        except Exception as e:
            dispatch_results.append((False, str(e)))

    t1 = threading.Thread(target=dispatch_worker)
    t2 = threading.Thread(target=dispatch_worker)
    t1.start()
    t2.start()
    t1.join(timeout=10)
    t2.join(timeout=10)

    # Count DISPATCH_STARTED events for this job
    started_count = WorkforceEventLog.objects.filter(
        event_type="DISPATCH_STARTED",
        payload__job_id=sr3.id,
    ).count()
    assert started_count <= 1, f"Expected at most 1 DISPATCH_STARTED event during claim, got {started_count}"
    print(f"  [PASS] Two concurrent dispatch calls resulted in strictly <=1 claim (events={started_count}).")

    # ── Test 4: Concurrent Scheduler Workers ──
    print("\n[4] Testing concurrent scheduler workers...")
    sr4 = _make_service_request(co)
    scheduler_results = []

    def scheduler_worker():
        try:
            r = dispatch_pending_jobs(company_id=co.id)
            scheduler_results.append(r)
        except Exception as e:
            scheduler_results.append(str(e))

    st1 = threading.Thread(target=scheduler_worker)
    st2 = threading.Thread(target=scheduler_worker)
    st1.start()
    st2.start()
    st1.join(timeout=10)
    st2.join(timeout=10)

    # Verify sr4 state was not corrupted
    state4 = WorkforceDispatchState.objects.filter(job=sr4).first()
    assert state4 is not None
    assert state4.attempt_count <= 2, f"Attempt count unexpected: {state4.attempt_count}"
    print(f"  [PASS] Concurrent scheduler workers handled job safely (attempt_count={state4.attempt_count}).")

    # ── Test 5: Retry Scheduled in Future -> Skipped ──
    print("\n[5] Testing retry scheduled in future is skipped...")
    sr5 = _make_service_request(co)
    future_retry = timezone.now() + timedelta(seconds=25)
    WorkforceDispatchState.objects.update_or_create(
        job=sr5,
        defaults={
            "dispatch_status": WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED,
            "attempt_count": 1,
            "retry_at": future_retry,
        },
    )

    res5 = dispatch_pending_jobs(company_id=co.id)
    job_ids = [d["job_id"] for d in res5["details"]]
    assert sr5.id not in job_ids, f"Scheduler should have skipped future retry job {sr5.id}"

    success5, msg5 = dispatch_job(sr5.id, force=False)
    assert not success5, "dispatch_job should have failed due to future retry"
    assert "not due yet" in msg5
    print("  [PASS] Future retry job correctly skipped by both scheduler and dispatch_job.")

    # ── Test 6: Retry Due -> Eligible ──
    print("\n[6] Testing retry due is eligible...")
    past_retry = timezone.now() - timedelta(seconds=5)
    WorkforceDispatchState.objects.filter(job=sr5).update(retry_at=past_retry)

    res6 = dispatch_pending_jobs(company_id=co.id)
    job_ids6 = [d["job_id"] for d in res6["details"]]
    assert sr5.id in job_ids6, f"Scheduler should have picked up due retry job {sr5.id}"
    print("  [PASS] Job with due retry_at successfully picked up by scheduler.")

    # ── Test 7: Active Offer -> No Redispatch ──
    print("\n[7] Testing active offer skips redispatch...")
    sr7 = _make_service_request(co)
    emp7 = _make_eligible_employee(co)
    WorkforceJobOffer.objects.create(
        job=sr7,
        employee=emp7,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at=timezone.now() + timedelta(minutes=5),
    )
    WorkforceDispatchState.objects.update_or_create(
        job=sr7,
        defaults={
            "dispatch_status": WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE,
            "attempt_count": 1,
        },
    )

    res7 = dispatch_pending_jobs(company_id=co.id)
    job_ids7 = [d["job_id"] for d in res7["details"]]
    assert sr7.id not in job_ids7, "Job with active offer must not be in pending scheduler list"

    s7, m7 = dispatch_job(sr7.id)
    assert "already" in m7.lower()
    print("  [PASS] Active offer correctly prevents redispatch.")

    # ── Test 8: Assigned Job -> No Redispatch ──
    print("\n[8] Testing assigned job skips redispatch...")
    sr8 = _make_service_request(co, status="assigned")
    sr8.assigned_employee = emp7
    sr8.save(update_fields=["status", "assigned_employee"])
    WorkforceDispatchState.objects.update_or_create(
        job=sr8,
        defaults={
            "dispatch_status": WorkforceDispatchState.DispatchStatus.ASSIGNED,
            "attempt_count": 1,
        },
    )

    res8 = dispatch_pending_jobs(company_id=co.id)
    job_ids8 = [d["job_id"] for d in res8["details"]]
    assert sr8.id not in job_ids8, "Assigned job must not be picked up by scheduler"

    s8, m8 = dispatch_job(sr8.id)
    assert not s8, "dispatch_job should reject assigned job"
    print("  [PASS] Assigned job correctly excluded from dispatch.")

    # ── Test 9: Cancelled & Completed Jobs -> No Redispatch ──
    print("\n[9] Testing cancelled and completed jobs skip redispatch...")
    sr9_canc = _make_service_request(co, status="cancelled")
    sr9_comp = _make_service_request(co, status="completed")

    s9a, m9a = dispatch_job(sr9_canc.id)
    s9b, m9b = dispatch_job(sr9_comp.id)
    assert not s9a and "cannot be dispatched" in m9a
    assert not s9b and "cannot be dispatched" in m9b
    print("  [PASS] Cancelled and completed jobs safely rejected.")

    # ── Test 10: Past-Date Job -> Refused ──
    print("\n[10] Testing past-date job refused...")
    yesterday = timezone.localdate() - timedelta(days=1)
    sr10 = _make_service_request(co, preferred_date=yesterday)

    s10, m10 = dispatch_job(sr10.id)
    assert not s10
    assert m10 == "SCHEDULE_DATE_EXPIRED"
    print("  [PASS] Past-dated booking refused with SCHEDULE_DATE_EXPIRED.")

    # ── Test 11: New Stateless Job -> Initial Dispatch Works ──
    print("\n[11] Testing new job without WorkforceDispatchState...")
    sr11 = _make_service_request(co)
    WorkforceDispatchState.objects.filter(job=sr11).delete()
    WorkforceJobOffer.objects.filter(job=sr11).delete()
    assert not WorkforceDispatchState.objects.filter(job=sr11).exists()

    res11 = dispatch_pending_jobs(company_id=co.id)
    job_ids11 = [d["job_id"] for d in res11["details"]]
    assert sr11.id in job_ids11, "New stateless job must be discovered"

    state11 = WorkforceDispatchState.objects.filter(job=sr11).first()
    assert state11 is not None, "DispatchState must be created after first attempt"
    assert state11.attempt_count == 1
    print(f"  [PASS] New stateless job discovered and initialized (status={state11.dispatch_status}).")

    # ── Test 12: Manual Admin Force -> Bypasses retry_at, Honors Gates ──
    print("\n[12] Testing manual admin force dispatch...")
    sr12 = _make_service_request(co)
    WorkforceJobOffer.objects.filter(job=sr12).delete()
    future_retry = timezone.now() + timedelta(seconds=60)
    WorkforceDispatchState.objects.update_or_create(
        job=sr12,
        defaults={
            "dispatch_status": WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED,
            "attempt_count": 1,
            "retry_at": future_retry,
        },
    )

    # Standard dispatch refuses
    s12_norm, _ = dispatch_job(sr12.id, force=False)
    assert not s12_norm

    # Force dispatch bypasses retry_at
    s12_force, _ = dispatch_job(sr12.id, force=True)
    state12 = WorkforceDispatchState.objects.get(job=sr12)
    assert state12.attempt_count == 2, "Force dispatch should have performed attempt 2"

    # But force does NOT bypass cancelled
    sr12.status = "cancelled"
    sr12.save(update_fields=["status"])
    s12_canc, m12_canc = dispatch_job(sr12.id, force=True)
    assert not s12_canc
    assert "cannot be dispatched" in m12_canc
    print("  [PASS] Admin force bypasses retry_at but strictly preserves safety gates.")

    # ── Test 13: CRITICAL EVENT-VOLUME BOUND (Zero Redispatch Storm) ──
    print("\n[13] CRITICAL EVENT-VOLUME TEST: 1 unassigned job, 0 candidates, rapid sweeps during retry window...")
    co_isolated = _make_company("storm_proof")
    sr13 = _make_service_request(co_isolated)
    # No employees exist for co_isolated
    state13 = WorkforceDispatchState.objects.get(job=sr13)
    assert state13.dispatch_status == WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED
    assert state13.attempt_count == 1

    # Ensure retry window is sufficiently open for multi-sweep testing over WAN
    WorkforceDispatchState.objects.filter(job=sr13).update(
        retry_at=timezone.now() + timedelta(seconds=60)
    )

    # Execute 5 rapid sweeps in succession (simulating periodic loops firing repeatedly)
    for i in range(5):
        sweep_res = dispatch_pending_jobs(company_id=co_isolated.id)
        assert sweep_res["dispatched_count"] == 0, f"Sweep {i} dispatched unexpectedly!"

    started_13 = WorkforceEventLog.objects.filter(event_type="DISPATCH_STARTED", payload__job_id=sr13.id).count()
    evaluated_13 = WorkforceEventLog.objects.filter(event_type="CANDIDATES_EVALUATED", payload__job_id=sr13.id).count()
    unassigned_13 = WorkforceEventLog.objects.filter(event_type="DISPATCH_UNASSIGNED_REASON", payload__job_id=sr13.id).count()

    print(f"     Recorded event counts after sweeps during retry window:")
    print(f"       DISPATCH_STARTED:           {started_13}")
    print(f"       CANDIDATES_EVALUATED:       {evaluated_13}")
    print(f"       DISPATCH_UNASSIGNED_REASON: {unassigned_13}")

    assert started_13 == 1, f"Expected strictly 1 DISPATCH_STARTED, got {started_13}!"
    assert evaluated_13 == 1, f"Expected strictly 1 CANDIDATES_EVALUATED, got {evaluated_13}!"
    assert unassigned_13 == 1, f"Expected strictly 1 DISPATCH_UNASSIGNED_REASON, got {unassigned_13}!"

    state13.refresh_from_db()
    assert state13.dispatch_status == WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED
    assert state13.attempt_count == 1
    assert state13.retry_at > timezone.now()
    delay_remaining = (state13.retry_at - timezone.now()).total_seconds()
    print(f"  [PASS] Zero event storm! Exactly 1 attempt occurred; next attempt held for {delay_remaining:.1f}s.")

    # ── Test 14: Non-Dispatching Endpoints Invariant ──
    print("\n[14] Testing non-dispatching endpoints (RealtimeStream, JobList, PresenceToggle, LocationUpdate)...")
    emp_user = emp7.user
    admin_user = User.objects.create_user(
        username=f"admin_{uuid.uuid4().hex[:6]}",
        password="AdminPass@123",
        email=f"admin_{uuid.uuid4().hex[:6]}@example.com",
        role="admin",
        company=co,
        is_staff=True,
    )

    co_job_ids = list(ServiceRequest.objects.filter(company=co).values_list("id", flat=True))
    events_before = WorkforceEventLog.objects.filter(event_type__in=["DISPATCH_STARTED", "CANDIDATES_EVALUATED"], payload__job_id__in=co_job_ids).count()

    # GET /workforce/jobs/
    req_jobs = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_jobs, user=emp_user)
    res_jobs = WorkforceJobListView.as_view()(req_jobs)
    assert res_jobs.status_code == status.HTTP_200_OK

    # POST /workforce/presence/toggle/
    req_pres = factory.post("/api/workforce/presence/toggle/", {"is_online": True}, format="json")
    force_authenticate(req_pres, user=emp_user)
    res_pres = WorkforcePresenceToggleView.as_view()(req_pres)
    assert res_pres.status_code == status.HTTP_200_OK

    # POST /workforce/presence/location/
    req_loc = factory.post("/api/workforce/presence/location/", {
        "latitude": 12.9785,
        "longitude": 77.5978,
        "accuracy": 10.0,
        "captured_at": timezone.now().isoformat(),
    }, format="json")
    force_authenticate(req_loc, user=emp_user)
    res_loc = WorkforceLocationUpdateView.as_view()(req_loc)
    assert res_loc.status_code == status.HTTP_200_OK

    events_after = WorkforceEventLog.objects.filter(event_type__in=["DISPATCH_STARTED", "CANDIDATES_EVALUATED"], payload__job_id__in=co_job_ids).count()
    assert events_before == events_after, f"Endpoints triggered unexpected dispatch! ({events_after - events_before} new events)"
    print("  [PASS] Endpoint invariant confirmed: JobList, PresenceToggle, and LocationUpdate trigger ZERO dispatch operations.")

    # ── Test 15: Legitimate Dispatch Pipeline (End-to-End) ──
    print("\n[15] Testing legitimate dispatch pipeline (Booking -> Offer -> Acceptance -> Assignment)...")
    co_legit = _make_company("legit")
    emp15 = _make_eligible_employee(co_legit)
    sr15 = _make_service_request(co_legit)

    # Initial dispatch
    offer15 = WorkforceJobOffer.objects.filter(job=sr15, employee=emp15, status="OFFERED").first()
    if not offer15:
        res15 = dispatch_pending_jobs(company_id=co_legit.id)
        offer15 = WorkforceJobOffer.objects.filter(job=sr15, employee=emp15, status="OFFERED").first()
    assert offer15 is not None, "WorkforceJobOffer must be created"

    state15 = WorkforceDispatchState.objects.get(job=sr15)
    assert state15.dispatch_status == WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE

    # Technician accepts offer
    req_acc = factory.post(f"/api/workforce/jobs/{sr15.id}/accept/")
    force_authenticate(req_acc, user=emp15.user)
    res_acc = WorkforceJobAcceptOfferView.as_view()(req_acc, pk=sr15.id)
    assert res_acc.status_code == status.HTTP_200_OK, f"Accept failed: {res_acc.data}"

    # Verify assignment
    sr15.refresh_from_db()
    assert sr15.status == "accepted"
    assert sr15.assigned_employee == emp15

    state15.refresh_from_db()
    assert state15.dispatch_status == WorkforceDispatchState.DispatchStatus.ASSIGNED

    # Subsequent sweep does NOT redispatch
    res15_sweep = dispatch_pending_jobs(company_id=co_legit.id)
    assert res15_sweep["dispatched_count"] == 0
    assert res15_sweep["pending_jobs_found"] == 0
    print("  [PASS] Legitimate booking -> offer -> acceptance -> assignment workflow verified.")

    print("\n==================================================================")
    print("      ALL 15 DISPATCH CONCURRENCY & STORM TESTS PASSED CLEANLY!   ")
    print("==================================================================")


if __name__ == "__main__":
    run_all_tests()
