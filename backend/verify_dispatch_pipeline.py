"""
verify_dispatch_pipeline.py

Authoritative Production Verification Suite for CalTrack Workforce.
Covers all 11 mandatory criteria:
  - Scenario A: Normal Service (HVAC) -> Booking -> Dispatch -> Offer -> Active Jobs -> Accept -> Assigned
  - Scenario B: Packers & Movers -> Skill/Category matching -> Offer -> Accept
  - Scenario C: Goods & Transport -> Transport category matching -> Offer -> Accept
  - Scenario D: Marketplace Booking (company_id=NULL) -> Candidate discovery -> Offer -> Accept -> Atomically bind company
  - Scenario E: Late GPS Telemetry -> Reconsideration -> Offer
  - Scenario F: Missed Dispatch Trigger -> Periodic Sweep (dispatch_pending_jobs) -> Offer
  - Scenario G: Concurrent Dispatch Triggers -> Exactly 1 Active Offer
  - Scenario H: Missing GPS -> No coordinate fabrication -> Pending GPS log -> Redispatch on GPS arrival
  - Scenario I: Expired Offer Redispatch -> Self-healing (no permanent exclusion)
  - Scenario J: Numeric Category ID Resolution ("15") -> Database category matching
  - Scenario K: Employee Isolation -> Offer visible exclusively to targeted employee
"""
import os
import sys
import uuid
import threading
from datetime import timedelta

import django
from django.conf import settings
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
    django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.test import Client

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest, EmployeeJob, CatalogCategory, Service
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceSkill,
    WorkforceEmployeeSkill,
    WorkforceEmployeeSchedule,
)
from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    dispatch_job,
    get_eligible_candidates,
    reconsider_jobs_for_employee,
    dispatch_pending_jobs,
    DISPATCHABLE_STATUSES,
)
from workforce_api.services.workload import ACTIVE_QUEUE_STATUSES

User = get_user_model()

# Accurate coordinates (Bangalore center)
BOOKING_LAT = 12.9715987
BOOKING_LON = 77.5945627
EMP_LAT = 12.9780000
EMP_LON = 77.5975000

TRACKED_COMPANIES = set()
TRACKED_USERS = set()
TRACKED_JOBS = set()


def make_gps(lat=EMP_LAT, lon=EMP_LON, age_seconds=20):
    ts = (timezone.now() - timedelta(seconds=age_seconds)).isoformat()
    return {
        "latitude": lat,
        "longitude": lon,
        "accuracy": 5.0,
        "captured_at": ts,
        "updated_at": ts,
    }


def make_company(name_prefix="VerifyCo"):
    cname = f"{name_prefix}_{uuid.uuid4().hex[:6]}"
    co, _ = Company.objects.get_or_create(
        company_name=cname,
        defaults={"is_active": True}
    )
    TRACKED_COMPANIES.add(co.id)
    return co


def make_employee(company, service_names=None, with_gps=True):
    if service_names is None:
        service_names = [
            "HVAC", "AC Repair", "Electrical", "Plumbing", "Cleaning",
            "Pest Control", "Carpentry", "Packers and Movers", "Goods and Transport"
        ]
    uname = f"vtech_{uuid.uuid4().hex[:8]}"
    user = User.objects.create_user(
        username=uname,
        password="Pass@1234Secure",
        email=f"{uname}@testcorp.com",
        role="employee",
        company=company,
    )
    TRACKED_USERS.add(user.id)
    if with_gps:
        user.last_known_location = make_gps()
        user.save(update_fields=["last_known_location"])

    svcs = [{"name": s, "category": s, "status": "approved"} for s in service_names]
    emp = Employee.objects.create(
        user=user,
        employee_id=f"EMP-{uuid.uuid4().hex[:8].upper()}",
        company=company,
        is_active=True,
        is_online=True,
        current_availability="available",
        bank_details={
            "onboarding": {
                "status": "approved",
                "services": svcs,
                "documents": {},
            },
            "attendance": {"is_clocked_in": True},
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

    for s in service_names:
        sk, _ = WorkforceSkill.objects.get_or_create(company=company, name=s)
        WorkforceEmployeeSkill.objects.create(
            employee=emp,
            skill=sk,
            is_verified=True,
            proficiency_level="EXPERT",
        )

    return emp


def make_booking(company=None, service_category="HVAC", issue_title="AC Repair", status="new_request", latitude=BOOKING_LAT, longitude=BOOKING_LON):
    req_id = f"SR-VERIFY-{uuid.uuid4().hex[:8].upper()}"
    job = ServiceRequest.objects.create(
        company=company,
        request_id=req_id,
        service_category=service_category,
        issue_title=issue_title,
        customer_name="Verification Customer",
        phone="9999999999",
        address="Bangalore Central Hub",
        latitude=latitude,
        longitude=longitude,
        preferred_date=timezone.now().date(),
        preferred_time="10:00 AM",
        status=status,
    )
    TRACKED_JOBS.add(job.id)
    return job


def print_diagnostic(stage_title, data_dict):
    print(f"\n[{stage_title}]", flush=True)
    for k, v in data_dict.items():
        print(f"  - {k}: {v}", flush=True)


def run_scenario_a():
    print("\n" + "="*70)
    print("SCENARIO A — Normal Service (HVAC)")
    print("="*70)
    co = make_company("ScenarioA_Co")
    emp = make_employee(co, ["HVAC", "AC Repair"])

    job = make_booking(company=co, service_category="HVAC", issue_title="AC Repair")
    print_diagnostic("1. Booking Created", {
        "ServiceRequest ID": job.id,
        "Request ID": job.request_id,
        "Status": job.status,
        "Company ID": job.company_id,
        "Assigned Employee": job.assigned_employee_id,
        "Dispatchable Status": job.status in DISPATCHABLE_STATUSES,
    })

    ok, msg = reconcile_booking_for_dispatch(job)
    print_diagnostic("2. Dispatch Reconciled", {
        "Success": ok,
        "Message": msg,
    })
    assert ok, f"Dispatch failed: {msg}"

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    print_diagnostic("3. WorkforceJobOffer in DB", {
        "Offer ID": offer.id if offer else None,
        "Employee ID": offer.employee_id if offer else None,
        "Status": offer.status if offer else None,
        "Expires At": offer.expires_at.isoformat() if offer else None,
    })
    assert offer and offer.status == "OFFERED", "Offer was not created"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    data = resp.json()
    job_ids = [j["id"] for j in data]
    print_diagnostic("4. Active Jobs API Response", {
        "HTTP Status": resp.status_code,
        "Total Jobs Returned": len(data),
        "Job IDs in Response": job_ids,
        "Target Job Included": job.id in job_ids,
    })
    assert job.id in job_ids, "Target job not visible in employee Active Jobs API"

    accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    job.refresh_from_db()
    print_diagnostic("5. Job Accepted & Assigned", {
        "Accept HTTP Status": accept_resp.status_code,
        "Assigned Employee ID": job.assigned_employee_id,
        "Post-Accept Status": job.status,
        "Active Queue Valid": job.status in ACTIVE_QUEUE_STATUSES,
    })
    assert job.assigned_employee_id == emp.id, "Job not assigned to employee"
    print(">>> SCENARIO A PASSED SUCCESSFULLY!")


def run_scenario_b():
    print("\n" + "="*70)
    print("SCENARIO B — Packers & Movers")
    print("="*70)
    co = make_company("ScenarioB_Co")
    emp = make_employee(co, ["Packers and Movers"])

    job = make_booking(company=co, service_category="Packers and Movers", issue_title="House Shifting")
    ok, msg = reconcile_booking_for_dispatch(job)
    assert ok, f"Dispatch failed: {msg}"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    job_ids = [j["id"] for j in resp.json()]
    assert job.id in job_ids, "Packers & Movers job not in active list"

    accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    job.refresh_from_db()
    assert job.assigned_employee_id == emp.id
    print(">>> SCENARIO B PASSED SUCCESSFULLY!")


def run_scenario_c():
    print("\n" + "="*70)
    print("SCENARIO C — Goods & Transport")
    print("="*70)
    co = make_company("ScenarioC_Co")
    emp = make_employee(co, ["Goods and Transport"])

    job = make_booking(company=co, service_category="Goods and Transport", issue_title="Goods Transport")
    ok, msg = reconcile_booking_for_dispatch(job)
    assert ok, f"Dispatch failed: {msg}"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    job_ids = [j["id"] for j in resp.json()]
    assert job.id in job_ids, "Goods & Transport job not in active list"

    accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    job.refresh_from_db()
    assert job.assigned_employee_id == emp.id
    print(">>> SCENARIO C PASSED SUCCESSFULLY!")


def run_scenario_d():
    print("\n" + "="*70)
    print("SCENARIO D — Marketplace Booking (company_id = NULL)")
    print("="*70)
    co = make_company("ScenarioD_Vendor")
    emp = make_employee(co, ["Plumbing"])

    job = make_booking(company=None, service_category="Plumbing", issue_title="Pipe Leak Repair")
    print_diagnostic("1. Marketplace Booking Created", {
        "Job ID": job.id,
        "Company ID": job.company_id,
        "Status": job.status,
    })
    assert job.company_id is None, "Marketplace booking must have company_id=NULL"

    ok, msg = reconcile_booking_for_dispatch(job)
    print_diagnostic("2. Marketplace Dispatch Reconciled", {
        "Success": ok,
        "Message": msg,
    })
    assert ok, f"Marketplace dispatch failed: {msg}"

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    assert offer and offer.status == "OFFERED", "No offer created for vendor technician"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    job_ids = [j["id"] for j in resp.json()]
    assert job.id in job_ids, "Marketplace job not in vendor employee active jobs"

    accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    job.refresh_from_db()
    print_diagnostic("3. Marketplace Job Accepted & Company Bound", {
        "Assigned Employee ID": job.assigned_employee_id,
        "Bound Company ID": job.company_id,
        "Employee Company ID": emp.company_id,
    })
    assert job.assigned_employee_id == emp.id, "Job not assigned to employee"
    assert job.company_id == emp.company_id, "Marketplace booking was not bound to vendor company on accept"
    print(">>> SCENARIO D PASSED SUCCESSFULLY!")


def run_scenario_e():
    print("\n" + "="*70)
    print("SCENARIO E — No Employee Initially Eligible -> GPS/Online Arrives -> Reconciliation")
    print("="*70)
    co = make_company("ScenarioE_Co")
    # Employee created without GPS (offline / no telemetry)
    emp = make_employee(co, ["Electrical"], with_gps=False)

    job = make_booking(company=co, service_category="Electrical", issue_title="Wiring Fix")
    ok1, msg1 = reconcile_booking_for_dispatch(job)
    job.refresh_from_db()
    print_diagnostic("1. Initial Dispatch Without Eligible Employee", {
        "Dispatch Success": ok1,
        "Message": msg1,
        "Job Status": job.status,
        "Still Dispatchable": job.status in DISPATCHABLE_STATUSES,
    })
    assert job.status in DISPATCHABLE_STATUSES, "Job became non-dispatchable after initial empty candidate run"

    # Employee now gets fresh GPS and becomes eligible
    emp.user.last_known_location = make_gps()
    emp.user.save(update_fields=["last_known_location"])

    # Reconsider triggered
    reconsidered_count = reconsider_jobs_for_employee(emp)
    print_diagnostic("2. Reconsider Triggered on Fresh GPS", {
        "Dispatched Count": reconsidered_count,
    })

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    assert offer and offer.status == "OFFERED", "Offer not created after reconsideration"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    job_ids = [j["id"] for j in resp.json()]
    assert job.id in job_ids, "Job not found in Active Jobs after late GPS"
    print(">>> SCENARIO E PASSED SUCCESSFULLY!")


def run_scenario_f():
    print("\n" + "="*70)
    print("SCENARIO F — Missed Initial Dispatch -> Background Sweep Recovers")
    print("="*70)
    co = make_company("ScenarioF_Co")
    emp = make_employee(co, ["Cleaning"])

    # Create directly with bulk_create to bypass save() dispatch hook
    raw_job = ServiceRequest(
        company=co,
        request_id=f"SR-RAW-{uuid.uuid4().hex[:8].upper()}",
        service_category="Cleaning",
        issue_title="Deep Cleaning",
        customer_name="Sweep Customer",
        phone="9999999999",
        address="Bangalore Central",
        latitude=BOOKING_LAT,
        longitude=BOOKING_LON,
        preferred_date=timezone.now().date(),
        preferred_time="10:00 AM",
        status="new_request",
    )
    created = ServiceRequest.objects.bulk_create([raw_job])
    job = ServiceRequest.objects.get(pk=created[0].pk)

    assert WorkforceJobOffer.objects.filter(job=job).count() == 0, "Offer exists before sweep"

    # Run periodic reconciliation sweep
    results = dispatch_pending_jobs(company_id=co.id)
    print_diagnostic("1. Sweep Execution Results", results)
    assert results["dispatched_count"] >= 1, "Sweep did not dispatch the missed job"

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    assert offer and offer.status == "OFFERED", "Offer not found after sweep"

    client = Client()
    client.force_login(emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    job_ids = [j["id"] for j in resp.json()]
    assert job.id in job_ids, "Job not in Active Jobs after sweep"
    print(">>> SCENARIO F PASSED SUCCESSFULLY!")


def run_scenario_g():
    print("\n" + "="*70)
    print("SCENARIO G — Concurrent / Duplicate Triggers -> Exactly 1 Active Offer")
    print("="*70)
    co = make_company("ScenarioG_Co")
    emp = make_employee(co, ["Carpentry"])

    job = make_booking(company=co, service_category="Carpentry", issue_title="Door Lock Fix")

    errors = []
    def do_reconcile():
        from django.db import connection
        try:
            reconcile_booking_for_dispatch(job)
        except Exception as e:
            errors.append(str(e))
        finally:
            connection.close()

    threads = [threading.Thread(target=do_reconcile) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, f"Concurrent dispatch threw errors: {errors}"
    active_offers = WorkforceJobOffer.objects.filter(
        job=job,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__gt=timezone.now()
    ).count()

    print_diagnostic("1. Concurrent Dispatch Result", {
        "Threads Executed": len(threads),
        "Exceptions": errors,
        "Active Offers in DB": active_offers,
    })
    assert active_offers == 1, f"Expected 1 active offer, got {active_offers}"
    print(">>> SCENARIO G PASSED SUCCESSFULLY!")


def run_scenario_h():
    print("\n" + "="*70)
    print("SCENARIO H — Missing Coordinates (Zero Fabrication & Subsequent GPS Fix)")
    print("="*70)
    co = make_company("ScenarioH_Co")
    emp = make_employee(co, ["Appliance Repair"])

    # Create job without coordinates (address mentioning Hosur and Chennai)
    job = make_booking(
        company=co,
        service_category="Appliance Repair",
        issue_title="Refrigerator Repair",
        latitude=None,
        longitude=None,
    )
    job.address = "123 Hosur Road, Near Chennai Highway, Bangalore"
    job.save()

    ok, msg = reconcile_booking_for_dispatch(job)
    job.refresh_from_db()
    print_diagnostic("1. Missing GPS Booking Dispatched", {
        "Success": ok,
        "Message": msg,
        "Latitude": job.latitude,
        "Longitude": job.longitude,
        "Status": job.status,
    })
    assert not ok, "Dispatch should have failed due to missing GPS"
    assert job.latitude is None and job.longitude is None, "Coordinates must NEVER be fabricated!"
    assert job.status in DISPATCHABLE_STATUSES, "Job must remain in dispatchable status"

    # Now customer updates GPS coordinates
    job.latitude = BOOKING_LAT
    job.longitude = BOOKING_LON
    job.save(update_fields=["latitude", "longitude"])

    ok2, msg2 = reconcile_booking_for_dispatch(job)
    print_diagnostic("2. Subsequent GPS Fix Dispatched", {
        "Success": ok2,
        "Message": msg2,
    })
    assert ok2, f"Dispatch after GPS fix failed: {msg2}"

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    assert offer and offer.status == "OFFERED", "Offer should be created after GPS fix"
    print(">>> SCENARIO H PASSED SUCCESSFULLY!")


def run_scenario_i():
    print("\n" + "="*70)
    print("SCENARIO I — Expired Offer Redispatch (Self-Healing)")
    print("="*70)
    co = make_company("ScenarioI_Co")
    emp = make_employee(co, ["Painting"])

    job = make_booking(company=co, service_category="Painting", issue_title="Wall Painting")
    ok1, _ = reconcile_booking_for_dispatch(job)
    assert ok1

    offer1 = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    assert offer1 and offer1.status == "OFFERED"

    # Simulate offer expiration
    past_time = timezone.now() - timedelta(minutes=5)
    offer1.status = WorkforceJobOffer.Status.EXPIRED
    offer1.expires_at = past_time
    offer1.save(update_fields=["status", "expires_at"])

    # Now technician comes online or sends GPS -> job should be re-offered without permanent exclusion!
    reconciled_count = reconsider_jobs_for_employee(emp)
    print_diagnostic("1. Expired Offer Reconsidered", {
        "Reconsidered Jobs Count": reconciled_count,
    })

    # Check that a fresh OFFERED record was created
    new_offer = WorkforceJobOffer.objects.filter(
        job=job,
        employee=emp,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__gt=timezone.now()
    ).first()
    print_diagnostic("2. Fresh Offer After Expiry", {
        "New Offer ID": new_offer.id if new_offer else None,
        "Status": new_offer.status if new_offer else None,
    })
    assert new_offer is not None, "Technician was permanently excluded despite offer having expired!"
    print(">>> SCENARIO I PASSED SUCCESSFULLY!")


def run_scenario_j():
    print("\n" + "="*70)
    print("SCENARIO J — Numeric Category ID Resolution ('15' -> HVAC)")
    print("="*70)
    co = make_company("ScenarioJ_Co")
    emp = make_employee(co, ["HVAC", "AC Repair"])

    # Create CatalogCategory with ID 15 or name 'HVAC'
    cat, _ = CatalogCategory.objects.get_or_create(
        id=15,
        defaults={"name": "HVAC", "slug": "hvac", "is_active": True}
    )

    job = make_booking(company=co, service_category="15", issue_title="AC Gas Top Up")
    ok, msg = reconcile_booking_for_dispatch(job)
    print_diagnostic("1. Numeric ID Category Dispatched", {
        "Category": job.service_category,
        "Success": ok,
        "Message": msg,
    })
    assert ok, f"Failed to dispatch numeric category booking: {msg}"

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp).first()
    assert offer and offer.status == "OFFERED", "Offer not created for numeric category ID"
    print(">>> SCENARIO J PASSED SUCCESSFULLY!")


def run_scenario_k():
    print("\n" + "="*70)
    print("SCENARIO K — Employee Isolation (No Cross-Employee Leakage)")
    print("="*70)
    co = make_company("ScenarioK_Co")
    emp1 = make_employee(co, ["Plumbing"])
    emp2 = make_employee(co, ["Electrical"])

    job = make_booking(company=co, service_category="Plumbing", issue_title="Tap Repair")
    ok, msg = reconcile_booking_for_dispatch(job)
    assert ok, f"Dispatch failed: {msg}"

    offer = WorkforceJobOffer.objects.filter(job=job, employee=emp1).first()
    assert offer and offer.status == "OFFERED"
    assert WorkforceJobOffer.objects.filter(job=job, employee=emp2).count() == 0

    # Emp1 can see it in Active Jobs
    client1 = Client()
    client1.force_login(emp1.user)
    resp1 = client1.get("/api/workforce/jobs/?status=active")
    job_ids1 = [j["id"] for j in resp1.json()]
    assert job.id in job_ids1, "Emp1 should see their offer"

    # Emp2 MUST NOT see it in Active Jobs
    client2 = Client()
    client2.force_login(emp2.user)
    resp2 = client2.get("/api/workforce/jobs/?status=active")
    job_ids2 = [j["id"] for j in resp2.json()]
    assert job.id not in job_ids2, "Emp2 must NOT see another employee's exclusive offer!"
    print(">>> SCENARIO K PASSED SUCCESSFULLY!")


def cleanup_test_data():
    print("\n" + "="*70)
    print("CLEANING UP TEST DATA...")
    print("="*70)
    try:
        from workforce_api.models import (
            JobTrackingSession, PreServiceVerification, WorkforceEventLog,
            WorkforceEmployeeCompliance, WorkforceEmployeeSkill, WorkforceEmployeeSchedule,
            WorkforceSkill,
        )
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
            WorkforceEmployeeCompliance.objects.filter(employee_id__in=emp_ids).delete()
            Employee.objects.filter(id__in=emp_ids).delete()
            User.objects.filter(id__in=TRACKED_USERS).delete()

        if TRACKED_COMPANIES:
            WorkforceSkill.objects.filter(company_id__in=TRACKED_COMPANIES).delete()
            Company.objects.filter(id__in=TRACKED_COMPANIES).delete()

        print(f"Cleanup completed: purged {len(TRACKED_JOBS)} jobs, {len(TRACKED_USERS)} users, {len(TRACKED_COMPANIES)} companies.", flush=True)
    except Exception as e:
        print(f"Warning during cleanup: {e}", flush=True)


def run_all():
    print("\n" + "#"*70)
    print("STARTING COMPLETE REAL-FLOW DISPATCH VERIFICATION SUITE (ALL 11 CRITERIA)")
    print("#"*70)
    try:
        run_scenario_a()
        run_scenario_b()
        run_scenario_c()
        run_scenario_d()
        run_scenario_e()
        run_scenario_f()
        run_scenario_g()
        run_scenario_h()
        run_scenario_i()
        run_scenario_j()
        run_scenario_k()
        print("\n" + "#"*70)
        print("ALL 11 PRODUCTION SCENARIOS PASSED ON LIVE DATABASE!")
        print("#"*70 + "\n")
    finally:
        cleanup_test_data()


if __name__ == "__main__":
    run_all()
