"""
verify_real_production_flow_live.py

Executes the REAL database + REAL HTTP API lifecycle for:
1. Packers & Movers Booking
2. Goods & Transport Booking
3. Auto Clock-In (via pre-service verification)
4. Cash Payment Collection + Automatic Clock-Out + Status Transition to COMPLETED
5. Realtime Reconciled Availability and Active Job Removal
"""

import os
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

import uuid
import requests
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

from employees.models import Employee
from companies.models import Company
from service_requests.models import ServiceRequest, EmployeeJob
from workforce_api.models import (
    WorkforceJobOffer,
    PreServiceVerification,
    PostServiceProof,
    JobPayment,
    JobTrackingSession,
    WorkforceEventLog,
)
from time_tracking.models import TimeLog, Break
from workforce_api.services.automatic_dispatch import dispatch_job, dispatch_pending_jobs
from workforce_api.services.workload import get_employee_active_job, is_employee_busy, reconcile_employee_availability

BASE_URL = "http://127.0.0.1:8001"

def run_real_flow():
    print("=" * 80)
    print("STARTING REAL PRODUCTION FLOW VERIFICATION")
    print("=" * 80)

    # 1. Setup real test technician in DB
    company = Company.objects.filter(is_active=True).first()
    if not company:
        company = Company.objects.create(company_name="Live Flow Company", is_active=True)

    uid = uuid.uuid4().hex[:6]
    username = f"tech_live_{uid}"
    user = User.objects.create_user(
        username=username,
        email=f"{username}@example.com",
        password="LivePassword123!",
        role="employee",
        first_name="Rajesh",
        last_name="Kumar",
        last_known_location={
            "latitude": 12.9716,
            "longitude": 77.5946,
            "accuracy": 10.0,
            "updated_at": timezone.now().isoformat(),
        }
    )

    emp = Employee.objects.create(
        user=user,
        company=company,
        employee_id=f"EMP-LIVE-{uid.upper()}",
        phone=f"98{uid.ljust(8, '0')[:8]}",
        is_online=True,
        current_availability="available",
        bank_details={
            "onboarding": {
                "status": "approved",
                "services": [
                    {"name": "Packers & Movers", "category": "Packers & Movers", "status": "approved"},
                    {"name": "Goods & Transport", "category": "Goods & Transport", "status": "approved"},
                    {"name": "Appliances", "category": "Appliances", "status": "approved"},
                ]
            }
        }
    )

    # Generate real JWT token for HTTP requests
    token = str(RefreshToken.for_user(user).access_token)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    results = {}

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 1: PACKERS & MOVERS REAL FLOW
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [STEP 1] TESTING PACKERS & MOVERS BOOKING ---")
    pm_booking = ServiceRequest.objects.create(
        company=company,
        status="confirmed",
        service_category="Packers & Movers",
        issue_title="2BHK House Relocation & Shifting",
        preferred_date=timezone.localdate(),
        preferred_time="11:00 AM",
        latitude=Decimal("12.9720"),
        longitude=Decimal("77.5950"),
        total_amount=Decimal("4800.00"),
        payment_method="cash",
        payment_status="pending",
    )
    print(f"Created Packers & Movers Booking ID #{pm_booking.id} ({pm_booking.service_category})")

    # Dispatch discovery
    success, msg = dispatch_job(pm_booking)
    print(f"Dispatch Job #{pm_booking.id}: success={success}, msg={msg}")
    
    # Verify Offer Created
    pm_offer = WorkforceJobOffer.objects.filter(job=pm_booking, employee=emp).first()
    if pm_offer:
        print(f"Offer created in DB: Offer #{pm_offer.id}, status={pm_offer.status}, expires_at={pm_offer.expires_at}")
        results["PACKERS_MOVERS_OFFER_CREATED"] = "PASS"
    else:
        print("ERROR: No offer created for Packers & Movers!")
        results["PACKERS_MOVERS_OFFER_CREATED"] = "FAIL"

    # Employee queries active jobs API via real HTTP
    resp_active = requests.get(f"{BASE_URL}/api/workforce/jobs/?status=active", headers=headers)
    print(f"GET /api/workforce/jobs/?status=active -> HTTP {resp_active.status_code}")
    active_list = resp_active.json() if resp_active.status_code == 200 else []
    pm_in_active = any(j.get("id") == pm_booking.id for j in active_list)
    print(f"Packers & Movers Booking #{pm_booking.id} present in GET /jobs/?status=active: {pm_in_active}")
    results["PACKERS_MOVERS_ACTIVE_DISPLAY"] = "PASS" if pm_in_active else "FAIL"

    # Employee accepts Packers & Movers offer via real HTTP
    resp_accept = requests.post(f"{BASE_URL}/api/workforce/jobs/{pm_booking.id}/accept-offer/", headers=headers)
    print(f"POST /api/workforce/jobs/{pm_booking.id}/accept-offer/ -> HTTP {resp_accept.status_code}")
    pm_booking.refresh_from_db()
    emp.refresh_from_db()
    print(f"Post-Accept: Job Status={pm_booking.status}, Assigned={pm_booking.assigned_employee_id}, Emp Availability={emp.current_availability}")
    results["PACKERS_MOVERS_ACCEPT"] = "PASS" if pm_booking.status == "accepted" and pm_booking.assigned_employee == emp else "FAIL"
    results["PACKERS_MOVERS"] = "PASS" if results["PACKERS_MOVERS_OFFER_CREATED"] == "PASS" and results["PACKERS_MOVERS_ACTIVE_DISPLAY"] == "PASS" and results["PACKERS_MOVERS_ACCEPT"] == "PASS" else "FAIL"

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 2: AUTO CLOCK-IN FLOW (ON PACKERS & MOVERS JOB)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [STEP 2] TESTING AUTO CLOCK-IN FLOW ---")
    # Complete pre-service verification
    psv = PreServiceVerification.objects.create(
        job=pm_booking,
        employee=emp,
        geofence_passed=True,
        otp_verified=True,
        presence_photo="proofs/presence_selfie_pm.jpg",
        is_complete=True,
        completed_at=timezone.now(),
    )
    print(f"PreServiceVerification created: is_complete={psv.is_complete}, geofence={psv.geofence_passed}, otp={psv.otp_verified}")

    # Auto Clock-In via real HTTP endpoint (using verified last known location / coordinates)
    resp_clockin = requests.post(
        f"{BASE_URL}/api/workforce/time/clock-in/",
        headers=headers,
        json={
            "job_id": pm_booking.id,
            "lat": 12.9720,
            "lon": 77.5950,
            "accuracy": 8.0,
            "address": "123 Indiranagar 100ft Rd, Bangalore",
        }
    )
    print(f"POST /api/workforce/time/clock-in/ -> HTTP {resp_clockin.status_code}")
    clockin_data = resp_clockin.json() if resp_clockin.status_code in [200, 201] else {}
    print(f"Clock-in response: {clockin_data.get('message')}, is_clocked_in={clockin_data.get('is_clocked_in')}")

    # Check TimeLog in DB
    timelog = TimeLog.objects.filter(employee=emp, clock_out__isnull=True).first()
    if timelog:
        print(f"TimeLog created in DB: id=#{timelog.id}, clock_in={timelog.clock_in}, status={timelog.status}")
        results["AUTO_CLOCK_IN"] = "PASS"
    else:
        print("ERROR: TimeLog not found with clock_in!")
        results["AUTO_CLOCK_IN"] = "FAIL"

    # Verify technician is BUSY
    emp.refresh_from_db()
    pm_booking.refresh_from_db()
    print(f"Tech Availability={emp.current_availability}, Job Status={pm_booking.status}")
    results["TECH_BUSY_ON_JOB"] = "PASS" if emp.current_availability == "busy" and pm_booking.status == "in_progress" else "FAIL"

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 3: CASH COLLECTION & AUTO CLOCK-OUT & COMPLETION
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [STEP 3] TESTING CASH COLLECTION & AUTO CLOCK-OUT ---")
    # Add PostServiceProof
    PostServiceProof.objects.create(
        job=pm_booking,
        employee=emp,
        after_presence_photo="proofs/after_selfie_pm.jpg",
        is_submitted=True,
        submitted_at=timezone.now(),
    )

    # Collect Cash via real HTTP
    resp_cash = requests.post(
        f"{BASE_URL}/api/workforce/jobs/{pm_booking.id}/payment/collect/",
        headers=headers,
        json={"amount_received": "4800.00"}
    )
    print(f"POST /api/workforce/jobs/{pm_booking.id}/payment/collect/ -> HTTP {resp_cash.status_code}")
    cash_data = resp_cash.json() if resp_cash.status_code == 200 else {}
    print(f"Cash response: {cash_data}")

    # Verify JobPayment in DB
    pmt = JobPayment.objects.filter(job=pm_booking).first()
    if pmt and pmt.payment_status == JobPayment.PaymentStatus.PAID:
        print(f"JobPayment in DB: status={pmt.payment_status}, amount_paid={pmt.amount_paid}")
        results["CASH_PAYMENT_PERSISTED"] = "PASS"
    else:
        print(f"ERROR: JobPayment status is {getattr(pmt, 'payment_status', 'NONE')}")
        results["CASH_PAYMENT_PERSISTED"] = "FAIL"

    # Verify Job Completed
    pm_booking.refresh_from_db()
    print(f"Job #{pm_booking.id} DB Status={pm_booking.status}")
    results["JOB_COMPLETED"] = "PASS" if pm_booking.status == "completed" else "FAIL"

    # Verify Auto Clock-Out in DB
    timelog.refresh_from_db()
    if timelog.clock_out is not None and timelog.status == "submitted":
        print(f"TimeLog closed: clock_out={timelog.clock_out}, status={timelog.status}")
        results["AUTO_CLOCK_OUT"] = "PASS"
    else:
        print(f"ERROR: TimeLog clock_out is {timelog.clock_out}")
        results["AUTO_CLOCK_OUT"] = "FAIL"

    # Verify Availability Reconciled to AVAILABLE
    emp.refresh_from_db()
    print(f"Employee Availability in DB={emp.current_availability}, is_busy={is_employee_busy(emp)}")
    results["BUSY_TO_AVAILABLE"] = "PASS" if emp.current_availability == "available" and not is_employee_busy(emp) else "FAIL"

    # Verify Active Jobs API excludes completed job
    resp_active_post = requests.get(f"{BASE_URL}/api/workforce/jobs/?status=active", headers=headers)
    active_post_list = resp_active_post.json() if resp_active_post.status_code == 200 else []
    pm_in_active_post = any(j.get("id") == pm_booking.id for j in active_post_list)
    print(f"Active Jobs list length={len(active_post_list)}, contains completed job #{pm_booking.id}: {pm_in_active_post}")
    results["ACTIVE_JOB_REMOVED"] = "PASS" if not pm_in_active_post else "FAIL"

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 4: GOODS & TRANSPORT REAL FLOW
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [STEP 4] TESTING GOODS & TRANSPORT BOOKING ---")
    gt_booking = ServiceRequest.objects.create(
        company=company,
        status="confirmed",
        service_category="Goods & Transport",
        issue_title="Commercial Cargo Delivery",
        preferred_date=timezone.localdate(),
        preferred_time="02:00 PM",
        latitude=Decimal("12.9720"),
        longitude=Decimal("77.5950"),
        total_amount=Decimal("2500.00"),
        payment_method="cash",
        payment_status="pending",
    )
    print(f"Created Goods & Transport Booking ID #{gt_booking.id} ({gt_booking.service_category})")

    # Dispatch discovery
    success_gt, msg_gt = dispatch_job(gt_booking)
    print(f"Dispatch Job #{gt_booking.id}: success={success_gt}, msg={msg_gt}")

    # Verify Offer Created
    gt_offer = WorkforceJobOffer.objects.filter(job=gt_booking, employee=emp).first()
    if gt_offer:
        print(f"Offer created in DB: Offer #{gt_offer.id}, status={gt_offer.status}")
        results["GOODS_TRANSPORT_OFFER_CREATED"] = "PASS"
    else:
        print("ERROR: No offer created for Goods & Transport!")
        results["GOODS_TRANSPORT_OFFER_CREATED"] = "FAIL"

    # Query active jobs API via real HTTP
    resp_gt_active = requests.get(f"{BASE_URL}/api/workforce/jobs/?status=active", headers=headers)
    gt_active_list = resp_gt_active.json() if resp_gt_active.status_code == 200 else []
    gt_in_active = any(j.get("id") == gt_booking.id for j in gt_active_list)
    print(f"Goods & Transport Booking #{gt_booking.id} present in GET /jobs/?status=active: {gt_in_active}")
    results["GOODS_TRANSPORT_ACTIVE_DISPLAY"] = "PASS" if gt_in_active else "FAIL"

    # Employee accepts Goods & Transport offer via real HTTP
    resp_gt_accept = requests.post(f"{BASE_URL}/api/workforce/jobs/{gt_booking.id}/accept-offer/", headers=headers)
    gt_booking.refresh_from_db()
    emp.refresh_from_db()
    print(f"Post-Accept: Job Status={gt_booking.status}, Assigned={gt_booking.assigned_employee_id}, Emp Availability={emp.current_availability}")
    results["GOODS_TRANSPORT_ACCEPT"] = "PASS" if gt_booking.status == "accepted" and gt_booking.assigned_employee == emp else "FAIL"
    results["GOODS_TRANSPORT"] = "PASS" if results["GOODS_TRANSPORT_OFFER_CREATED"] == "PASS" and results["GOODS_TRANSPORT_ACTIVE_DISPLAY"] == "PASS" and results["GOODS_TRANSPORT_ACCEPT"] == "PASS" else "FAIL"

    # ─────────────────────────────────────────────────────────────────────────
    # STEP 5: PRESENCE / AUTH ME API REALTIME RECONCILIATION CHECK
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- [STEP 5] TESTING PRESENCE & ME API RECONCILIATION ---")
    resp_me = requests.get(f"{BASE_URL}/api/auth/me/", headers=headers)
    me_data = resp_me.json() if resp_me.status_code == 200 else {}
    print(f"GET /api/auth/me/ -> live_availability: {me_data.get('live_availability')}")

    resp_pres = requests.get(f"{BASE_URL}/api/workforce/presence/status/", headers=headers)
    pres_data = resp_pres.json() if resp_pres.status_code == 200 else {}
    print(f"GET /api/workforce/presence/status/ -> availability: {pres_data.get('availability')}")

    results["REALTIME_API_RECONCILIATION"] = "PASS" if resp_me.status_code == 200 and resp_pres.status_code == 200 else "FAIL"

    # ─────────────────────────────────────────────────────────────────────────
    # FINAL SUMMARY REPORT
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("FINAL REAL PRODUCTION FLOW VERIFICATION SUMMARY")
    print("=" * 80)
    print(f"PACKERS & MOVERS (Job #{pm_booking.id}):        {results.get('PACKERS_MOVERS', 'FAIL')}")
    print(f"GOODS & TRANSPORT (Job #{gt_booking.id}):       {results.get('GOODS_TRANSPORT', 'FAIL')}")
    print(f"OFFER CREATED:                            {results.get('PACKERS_MOVERS_OFFER_CREATED', 'FAIL')}")
    print(f"ACTIVE JOB DISPLAY:                       {results.get('PACKERS_MOVERS_ACTIVE_DISPLAY', 'FAIL')}")
    print(f"AUTO CLOCK-IN:                            {results.get('AUTO_CLOCK_IN', 'FAIL')}")
    print(f"CASH PAYMENT PERSISTED:                   {results.get('CASH_PAYMENT_PERSISTED', 'FAIL')}")
    print(f"AUTO CLOCK-OUT:                           {results.get('AUTO_CLOCK_OUT', 'FAIL')}")
    print(f"JOB COMPLETED:                            {results.get('JOB_COMPLETED', 'FAIL')}")
    print(f"BUSY -> AVAILABLE:                        {results.get('BUSY_TO_AVAILABLE', 'FAIL')}")
    print(f"ACTIVE JOB REMOVED:                       {results.get('ACTIVE_JOB_REMOVED', 'FAIL')}")
    print(f"REALTIME API UPDATE:                      {results.get('REALTIME_API_RECONCILIATION', 'FAIL')}")
    print("=" * 80)

    return results

if __name__ == "__main__":
    run_real_flow()
