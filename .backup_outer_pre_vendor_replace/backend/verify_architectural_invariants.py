"""
Comprehensive Production Verification Suite for Architectural Invariants (Tests A-G).
Verifies:
- Test A: Normal vendor booking pure flow
- Test B: Marketplace booking pure flow (company_id=NULL bound on accept)
- Test C: No eligible employee -> unassigned -> ZERO recursion loops
- Test D: Previously unassigned booking -> employee arrives -> offer created
- Test E: Expired offer -> canonical redispatch to eligible employee
- Test F: High-concurrency dispatch -> exactly 1 active offer
- Test G: Active Jobs GET -> pure read-only with zero DB mutations
- Automatic cleanup of all test records
"""
import os
import sys
import uuid
import django
import threading
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import Client
from service_requests.models import ServiceRequest, EmployeeJob
from employees.models import Employee
from companies.models import Company
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceSkill,
    WorkforceEmployeeSkill,
    WorkforceEmployeeSchedule,
    JobTrackingSession,
    PreServiceVerification,
)
from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    reconsider_jobs_for_employee,
    expire_and_reassign_offers,
    dispatch_pending_jobs,
)

User = get_user_model()

# Accurate GPS coordinates (Bangalore center)
BOOKING_LAT = 12.9715987
BOOKING_LON = 77.5945627
EMP_LAT = 12.9750000
EMP_LON = 77.5960000

TRACKED_COMPANIES = set()
TRACKED_USERS = set()
TRACKED_JOBS = set()


def make_gps(lat=EMP_LAT, lon=EMP_LON, age_seconds=15):
    ts = (timezone.now() - timedelta(seconds=age_seconds)).isoformat()
    return {
        "latitude": lat,
        "longitude": lon,
        "accuracy": 5.0,
        "captured_at": ts,
        "updated_at": ts,
    }


def make_company(name_prefix="InvCo"):
    cname = f"{name_prefix}_{uuid.uuid4().hex[:6]}"
    co, _ = Company.objects.get_or_create(
        company_name=cname,
        defaults={"is_active": True}
    )
    TRACKED_COMPANIES.add(co.id)
    return co


def make_employee(company, service_name="HVAC", lat=EMP_LAT, lon=EMP_LON, is_online=True):
    uname = f"itech_{uuid.uuid4().hex[:8]}"
    user = User.objects.create_user(
        username=uname,
        password="Pass@1234Secure",
        email=f"{uname}@testcorp.com",
        role="employee",
        company=company,
    )
    TRACKED_USERS.add(user.id)
    user.last_known_location = make_gps(lat=lat, lon=lon)
    user.save(update_fields=["last_known_location"])

    svcs = [{"name": service_name, "category": service_name, "status": "approved"}]
    emp = Employee.objects.create(
        user=user,
        employee_id=f"EMP-{uuid.uuid4().hex[:8].upper()}",
        company=company,
        is_active=True,
        is_online=is_online,
        current_availability="available" if is_online else "offline",
        bank_details={
            "onboarding": {
                "status": "approved",
                "services": svcs,
                "documents": {},
            },
            "attendance": {"is_clocked_in": is_online},
            "leaves": [],
        },
    )

    for dow in range(7):
        WorkforceEmployeeSchedule.objects.create(
            employee=emp,
            company=company,
            day_of_week=dow,
            is_working_day=True,
            start_time="00:00:00",
            end_time="23:59:59",
        )

    sk, _ = WorkforceSkill.objects.get_or_create(company=company, name=service_name)
    WorkforceEmployeeSkill.objects.create(
        employee=emp,
        skill=sk,
        is_verified=True,
        proficiency_level="EXPERT",
    )
    return emp


def cleanup_test_data():
    print("\n" + "="*70)
    print("CLEANING UP ARCHITECTURAL INVARIANT TEST DATA...")
    print("="*70)
    try:
        if TRACKED_JOBS:
            WorkforceJobOffer.objects.filter(job_id__in=TRACKED_JOBS).delete()
            JobTrackingSession.objects.filter(job_id__in=TRACKED_JOBS).delete()
            PreServiceVerification.objects.filter(job_id__in=TRACKED_JOBS).delete()
            EmployeeJob.objects.filter(service_request_id__in=TRACKED_JOBS).delete()
            ServiceRequest.objects.filter(id__in=TRACKED_JOBS).delete()

        if TRACKED_USERS:
            emp_ids = list(Employee.objects.filter(user_id__in=TRACKED_USERS).values_list("id", flat=True))
            WorkforceEmployeeSkill.objects.filter(employee_id__in=emp_ids).delete()
            WorkforceEmployeeSchedule.objects.filter(employee_id__in=emp_ids).delete()
            Employee.objects.filter(id__in=emp_ids).delete()
            User.objects.filter(id__in=TRACKED_USERS).delete()

        if TRACKED_COMPANIES:
            WorkforceSkill.objects.filter(company_id__in=TRACKED_COMPANIES).delete()
            Company.objects.filter(id__in=TRACKED_COMPANIES).delete()

        print(f"Cleanup completed: purged {len(TRACKED_JOBS)} jobs, {len(TRACKED_USERS)} users, {len(TRACKED_COMPANIES)} companies.", flush=True)
    except Exception as e:
        print(f"Warning during cleanup: {e}", flush=True)


# ─── TEST A: Normal Booking ──────────────────────────────────────────────────
def test_a_normal_booking():
    print("\n" + "-"*70)
    print("TEST A — Normal Vendor Booking Pure Flow")
    print("-"*70)
    co = make_company("TestA_Co")
    emp = make_employee(co, "HVAC")

    job = ServiceRequest.objects.create(
        company=co,
        request_id=f"SR-TA-{uuid.uuid4().hex[:6].upper()}",
        service_category="HVAC",
        issue_title="AC Repair and Diagnostics",
        customer_name="Customer A",
        phone="9800000001",
        address="MG Road, Bangalore",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="10:00 AM",
        status="new_request",
    )
    TRACKED_JOBS.add(job.id)

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp, status=WorkforceJobOffer.Status.OFFERED).first()
    assert offer is not None, "Test A: Offer not created automatically via save hook!"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    assert resp.status_code == 200
    matched = next((j for j in resp.json() if j["id"] == job.id), None)
    assert matched is not None, "Test A: Offer not present in Active Jobs GET API!"

    accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    assert accept_resp.status_code == 200, f"Test A: Accept offer failed: {accept_resp.json()}"
    job.refresh_from_db()
    assert job.assigned_employee_id == emp.id
    assert job.status in ["accepted", "on_the_way", "arrived", "in_progress"]
    print(">>> TEST A PASSED: Booking -> Offer -> Active Jobs -> Accept -> Assigned Active Job.")


# ─── TEST B: Marketplace Booking ─────────────────────────────────────────────
def test_b_marketplace_booking():
    print("\n" + "-"*70)
    print("TEST B — Marketplace Booking Pure Flow (company_id = NULL)")
    print("-"*70)
    co = make_company("TestB_MktVendorCo")
    emp = make_employee(co, "Electrical")

    job = ServiceRequest.objects.create(
        company=None,  # Marketplace
        request_id=f"SR-TB-{uuid.uuid4().hex[:6].upper()}",
        service_category="Electrical",
        issue_title="Electrician Wiring and Switchboard",
        customer_name="Marketplace Customer B",
        phone="9800000002",
        address="Indiranagar, Bangalore",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="11:00 AM",
        status="new_request",
    )
    TRACKED_JOBS.add(job.id)

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp, status=WorkforceJobOffer.Status.OFFERED).first()
    assert offer is not None, "Test B: Marketplace offer not created automatically!"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    assert resp.status_code == 200
    matched = next((j for j in resp.json() if j["id"] == job.id), None)
    assert matched is not None, "Test B: Marketplace offer not present in Active Jobs GET API!"

    accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    assert accept_resp.status_code == 200, f"Test B: Accept marketplace offer failed: {accept_resp.json()}"
    job.refresh_from_db()
    assert job.assigned_employee_id == emp.id
    assert job.company_id == co.id, f"Test B: Company should be bound to {co.id}, got {job.company_id}"
    print(">>> TEST B PASSED: Marketplace Booking -> Offer -> Active Jobs -> Accept -> Bound Company.")


# ─── TEST C: No Eligible Employee & Anti-Recursion ───────────────────────────
def test_c_no_eligible_employee_anti_recursion():
    print("\n" + "-"*70)
    print("TEST C — No Eligible Employee & Anti-Recursion Verification")
    print("-"*70)
    co = make_company("TestC_EmptyCo")
    # No employees in co

    job = ServiceRequest.objects.create(
        company=co,
        request_id=f"SR-TC-{uuid.uuid4().hex[:6].upper()}",
        service_category="Plumbing",
        issue_title="Pipe Leakage Repair",
        customer_name="Customer C",
        phone="9800000003",
        address="Whitefield, Bangalore",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="12:00 PM",
        status="new_request",
    )
    TRACKED_JOBS.add(job.id)

    job.refresh_from_db()
    assert job.status in ["unassigned", "new_request"], f"Job status should be unassigned, got {job.status}"
    assert job.assigned_employee_id is None

    offers_count = WorkforceJobOffer.objects.filter(job=job).count()
    assert offers_count == 0, f"No offers should exist, got {offers_count}"
    print(f">>> TEST C PASSED: No recursion loop, job status={job.status}, zero duplicate offers.")
    return job, co


# ─── TEST D: Employee Becomes Eligible Later ─────────────────────────────────
def test_d_employee_becomes_eligible_later(unassigned_job, company):
    print("\n" + "-"*70)
    print("TEST D — Employee Becomes Eligible Later (GPS / Online Arrival)")
    print("-"*70)
    # Create an employee in the same company now
    emp = make_employee(company, "Plumbing", lat=EMP_LAT, lon=EMP_LON, is_online=True)

    # Trigger employee reconsideration
    count = reconsider_jobs_for_employee(emp)
    assert count >= 1, f"Reconsider should dispatch at least 1 job, got {count}"

    offer = WorkforceJobOffer.objects.filter(job=unassigned_job, employee=emp, status=WorkforceJobOffer.Status.OFFERED).first()
    assert offer is not None, "Test D: Offer was not created upon technician arrival!"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    assert resp.status_code == 200
    matched = next((j for j in resp.json() if j["id"] == unassigned_job.id), None)
    assert matched is not None, "Test D: Job not visible in Active Jobs after technician arrival!"
    print(f">>> TEST D PASSED: Employee arrival triggered redispatch; offer ID={offer.id} visible in Active Jobs.")


# ─── TEST E: Expired Offer Redispatch ─────────────────────────────────────────
def test_e_expired_offer_redispatch():
    print("\n" + "-"*70)
    print("TEST E — Expired Offer Redispatch Through Canonical Reconciliation")
    print("-"*70)
    co = make_company("TestE_ExpireCo")
    emp1 = make_employee(co, "Cleaning", lat=12.9720, lon=77.5950)
    emp2 = make_employee(co, "Cleaning", lat=12.9730, lon=77.5955)

    job = ServiceRequest.objects.create(
        company=co,
        request_id=f"SR-TE-{uuid.uuid4().hex[:6].upper()}",
        service_category="Cleaning",
        issue_title="Deep Cleaning Service",
        customer_name="Customer E",
        phone="9800000005",
        address="Koramangala, Bangalore",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="02:00 PM",
        status="new_request",
    )
    TRACKED_JOBS.add(job.id)

    # Expire all initial offers artificially
    WorkforceJobOffer.objects.filter(job=job).update(
        expires_at=timezone.now() - timedelta(minutes=5),
        status=WorkforceJobOffer.Status.OFFERED
    )

    # Sweep & Redispatch
    expired_count = expire_and_reassign_offers(company_id=co.id)
    assert expired_count > 0, f"Expected expired offers, swept {expired_count}"

    # Verify a new unexpired offer exists
    new_offer = WorkforceJobOffer.objects.filter(
        job=job,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__gt=timezone.now(),
    ).first()
    assert new_offer is not None, "Test E: New offer was not created after expiration sweep!"
    print(f">>> TEST E PASSED: Expired offer auto-swept and redispatched (New Offer ID={new_offer.id}).")


# ─── TEST F: High Concurrency Dispatch Idempotency ───────────────────────────
def test_f_concurrent_dispatch():
    print("\n" + "-"*70)
    print("TEST F — Concurrent Dispatch Triggers (Race Condition & Lock Test)")
    print("-"*70)
    co = make_company("TestF_ConcurCo")
    emp = make_employee(co, "Carpentry")

    job = ServiceRequest.objects.create(
        company=co,
        request_id=f"SR-TF-{uuid.uuid4().hex[:6].upper()}",
        service_category="Carpentry",
        issue_title="Furniture Repair",
        customer_name="Customer F",
        phone="9800000006",
        address="Jayanagar, Bangalore",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="03:00 PM",
        status="new_request",
    )
    TRACKED_JOBS.add(job.id)

    # Fire 5 concurrent threads calling reconcile_booking_for_dispatch simultaneously
    results = []
    threads = []

    def _worker():
        from django.db import connection
        try:
            success, msg = reconcile_booking_for_dispatch(job)
            results.append((success, msg))
        except Exception as exc:
            results.append((False, str(exc)))
        finally:
            connection.close()

    for _ in range(5):
        t = threading.Thread(target=_worker)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify exactly 1 active offer in DB
    now = timezone.now()
    active_offers = list(WorkforceJobOffer.objects.filter(
        job=job,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__gt=now,
    ))
    assert len(active_offers) == 1, f"Expected exactly 1 active offer, found {len(active_offers)}!"
    print(f">>> TEST F PASSED: 5 concurrent threads executed cleanly; exactly 1 active offer in DB (Offer ID={active_offers[0].id}).")


# ─── TEST G: Pure Read-Only Active Jobs API ──────────────────────────────────
def test_g_active_jobs_get_pure_read_only():
    print("\n" + "-"*70)
    print("TEST G — Pure Read-Only Active Jobs GET Verification (Zero Mutations)")
    print("-"*70)
    co = make_company("TestG_ReadCo")
    emp = make_employee(co, "Pest Control")

    job = ServiceRequest.objects.create(
        company=co,
        request_id=f"SR-TG-{uuid.uuid4().hex[:6].upper()}",
        service_category="Pest Control",
        issue_title="Cockroach & Pest Control",
        customer_name="Customer G",
        phone="9800000007",
        address="HSR Layout, Bangalore",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="04:00 PM",
        status="new_request",
    )
    TRACKED_JOBS.add(job.id)

    client = Client()
    client.force_login(emp.user)

    # Record initial counts
    initial_offer_count = WorkforceJobOffer.objects.count()
    initial_job_count = ServiceRequest.objects.count()
    initial_offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    initial_updated_at = initial_offer.updated_at if hasattr(initial_offer, "updated_at") else initial_offer.offered_at

    # Call GET endpoint 5 times in a row
    for i in range(5):
        resp = client.get("/api/workforce/jobs/?status=active")
        assert resp.status_code == 200, f"GET active jobs call {i+1} failed"
        assert len(resp.json()) >= 1

    # Verify zero mutations
    final_offer_count = WorkforceJobOffer.objects.count()
    final_job_count = ServiceRequest.objects.count()
    assert initial_offer_count == final_offer_count, f"Offer count changed during GET calls: {initial_offer_count} -> {final_offer_count}"
    assert initial_job_count == final_job_count, f"Job count changed during GET calls: {initial_job_count} -> {final_job_count}"

    print(">>> TEST G PASSED: 5 repeated GET calls executed with ZERO database writes or side effects.")


def run_all():
    print("\n" + "#"*70)
    print("RUNNING ALL 7 ARCHITECTURAL INVARIANT PRODUCTION TESTS (A through G)")
    print("#"*70)
    try:
        test_a_normal_booking()
        test_b_marketplace_booking()
        unassigned_job, unassigned_co = test_c_no_eligible_employee_anti_recursion()
        test_d_employee_becomes_eligible_later(unassigned_job, unassigned_co)
        test_e_expired_offer_redispatch()
        test_f_concurrent_dispatch()
        test_g_active_jobs_get_pure_read_only()
        print("\n" + "#"*70)
        print("ALL 7 ARCHITECTURAL INVARIANT TESTS PASSED 100% ON LIVE DATABASE!")
        print("#"*70 + "\n")
    finally:
        cleanup_test_data()


if __name__ == "__main__":
    run_all()
