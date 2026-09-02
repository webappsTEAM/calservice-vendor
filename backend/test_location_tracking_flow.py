"""
test_location_tracking_flow.py

End-to-End Verification Test for Employee Location Persistence, Live Tracking,
Movement Detection, and Realtime Customer Stream Visibility.
"""
import os
import sys
import django
from decimal import Decimal
from datetime import timedelta

os.environ["DJANGO_SETTINGS_MODULE"] = "workforce_core.settings"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest, EmployeeJob
from workforce_api.models import (
    JobTrackingSession,
    JobLocationPoint,
    WorkforceEventLog,
    PreServiceVerification,
    WorkforceJobOffer,
)
from workforce_api.views import (
    WorkforceLocationUpdateView,
    WorkforceJobLiveTrackingView,
    WorkforceJobAcceptOfferView,
)

User = get_user_model()


def run_tests():
    print("=" * 70)
    print("LOCATION TRACKING & LIVE CUSTOMER VISIBILITY TEST SUITE")
    print("=" * 70)

    factory = APIRequestFactory()
    now = timezone.now()

    # ── SETUP FIXTURES ──
    company = Company.objects.first()
    if not company:
        company = Company.objects.create(company_name="CalTrack Test Ltd", slug="caltest")

    # Customer user
    cust_user = User.objects.filter(username="test_customer_loc@calservice.com").first()
    if not cust_user:
        cust_user = User.objects.create(
            username="test_customer_loc@calservice.com",
            email="test_customer_loc@calservice.com",
            first_name="Alice",
            last_name="Customer",
            role="customer",
            is_active=True,
        )

    # Tech user & profile
    tech_user = User.objects.filter(username="test_tech_loc@calservice.com").first()
    if not tech_user:
        tech_user = User.objects.create(
            username="test_tech_loc@calservice.com",
            email="test_tech_loc@calservice.com",
            first_name="Bob",
            last_name="Technician",
            role="technician",
            is_active=True,
        )
    tech_user.company = company
    tech_user.save()

    emp = Employee.objects.filter(user=tech_user).first()
    if not emp:
        emp = Employee.objects.filter(company=company, employee_id="EMP-TEST-001").first()
        if not emp:
            emp = Employee.objects.create(
                user=tech_user,
                employee_id="EMP-TEST-001",
                company=company,
                title="Master Technician",
                is_active=True,
                current_availability="busy",
                bank_details={"onboarding": {"status": "approved"}},
            )
        else:
            emp.user = tech_user
            emp.bank_details = {"onboarding": {"status": "approved"}}
            emp.is_active = True
            emp.current_availability = "busy"
            emp.save()
    else:
        emp.bank_details = {"onboarding": {"status": "approved"}}
        emp.is_active = True
        emp.current_availability = "busy"
        emp.save()

    # Customer Booking Location: 13.0827, 80.2707 (Chennai Central)
    cust_lat = 13.0827000
    cust_lon = 80.2707000

    job, _ = ServiceRequest.objects.get_or_create(
        request_id="REQ-LOC-TEST-001",
        defaults={
            "company": company,
            "customer": cust_user,
            "customer_name": "Alice Customer",
            "phone": "9876543210",
            "address": "Chennai Central Station",
            "preferred_date": now.date(),
            "preferred_time": "10:00:00",
            "latitude": cust_lat,
            "longitude": cust_lon,
            "status": "accepted",
            "assigned_employee": emp,
        }
    )
    job.status = "accepted"
    job.assigned_employee = emp
    job.customer = cust_user
    job.latitude = cust_lat
    job.longitude = cust_lon
    job.save()

    EmployeeJob.objects.update_or_create(
        service_request=job,
        employee=emp,
        defaults={"status": "ACCEPTED", "is_primary": True}
    )

    # Clean up old tracking data and location for this job
    tech_user.last_known_location = {}
    tech_user.save(update_fields=["last_known_location"])
    JobTrackingSession.objects.filter(job=job).delete()
    JobLocationPoint.objects.filter(job=job).delete()
    WorkforceEventLog.objects.filter(user=cust_user, event_type="JOB_LOCATION_UPDATE").delete()

    print("\n[TEST 1] Out-of-Range Coordinate Validation")
    view = WorkforceLocationUpdateView.as_view()
    req = factory.post("/workforce/presence/location/", {"latitude": 95.0, "longitude": 80.0}, format="json")
    force_authenticate(req, user=tech_user)
    res = view(req)
    assert res.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400, got {res.status_code}"
    print("  PASS: Rejects out-of-range latitude (>90).")

    print("\n[TEST 2] Technician Far Away (1.02 km) — Moving Towards Customer")
    # Position ~1.02 km away: 13.0735, 80.2707
    pos1_lat, pos1_lon = 13.0735000, 80.2707000
    t1 = now - timedelta(seconds=55)

    req = factory.post("/workforce/presence/location/", {
        "latitude": pos1_lat,
        "longitude": pos1_lon,
        "accuracy": 10.5,
        "speed": 8.5,  # 8.5 m/s (~30.6 km/h -> MOVING)
        "heading": 45.0,
        "captured_at": t1.isoformat(),
    }, format="json")
    force_authenticate(req, user=tech_user)
    res = view(req)
    assert res.status_code == status.HTTP_200_OK, f"Expected 200, got {res.status_code}"

    # Verify JobTrackingSession created
    active_session = JobTrackingSession.objects.filter(job=job, status="ACTIVE").first()
    assert active_session is not None, "Active JobTrackingSession was not created."
    assert active_session.movement_status == "MOVING", f"Expected MOVING, got {active_session.movement_status}"
    assert active_session.geofence_status == "OUTSIDE", f"Expected OUTSIDE (>1km), got {active_session.geofence_status}"
    print(f"  PASS: Session #{active_session.id} active. movement_status={active_session.movement_status}, geofence_status={active_session.geofence_status}")

    # Verify WorkforceEventLog generated for customer
    event = WorkforceEventLog.objects.filter(user=cust_user, event_type="JOB_LOCATION_UPDATE").order_by("-id").first()
    assert event is not None, "Realtime WorkforceEventLog was not created."
    p = event.payload
    assert p["movement_status"] == "MOVING"
    assert p["geofence_status"] == "OUTSIDE"
    assert p["distance_km"] >= 1.0
    assert p["employee_location"]["speed"] == 8.5
    assert p["employee_location"]["heading"] == 45.0
    print(f"  PASS: Event payload enriched. distance_km={p['distance_km']}, movement_status={p['movement_status']}")

    print("\n[TEST 3] Out-of-Order Packet Protection")
    older_time = t1 - timedelta(seconds=30)
    req = factory.post("/workforce/presence/location/", {
        "latitude": 13.0500,
        "longitude": 80.2700,
        "captured_at": older_time.isoformat(),
    }, format="json")
    force_authenticate(req, user=tech_user)
    res = view(req)
    assert res.data.get("ignored") is True, f"Expected ignored=True, got {res.data}"
    print("  PASS: Stale out-of-order GPS packet was safely ignored.")

    print("\n[TEST 4] Approaching Customer (<1.0 km) — Stationary at Traffic Light")
    # Position ~600m away: 13.0775, 80.2707 (delta 20s for 440m = 79 km/h)
    pos2_lat, pos2_lon = 13.0775000, 80.2707000
    t2 = now - timedelta(seconds=35)

    req = factory.post("/workforce/presence/location/", {
        "latitude": pos2_lat,
        "longitude": pos2_lon,
        "accuracy": 8.0,
        "speed": 0.1,  # 0.1 m/s -> STATIONARY
        "heading": 0.0,
        "captured_at": t2.isoformat(),
    }, format="json")
    force_authenticate(req, user=tech_user)
    res = view(req)
    assert res.status_code == status.HTTP_200_OK

    active_session.refresh_from_db()
    assert active_session.movement_status == "STATIONARY", f"Expected STATIONARY, got {active_session.movement_status}"
    assert active_session.geofence_status == "APPROACHING", f"Expected APPROACHING (<=1km), got {active_session.geofence_status}"
    print(f"  PASS: movement_status={active_session.movement_status}, geofence_status={active_session.geofence_status}")

    print("\n[TEST 5] Entering Geofence (150m) — Fix #1")
    # Position ~150m away: 13.0815, 80.2707 (delta 30s for 444m = 53 km/h)
    pos3_lat, pos3_lon = 13.0815000, 80.2707000
    t3 = now - timedelta(seconds=5)

    req = factory.post("/workforce/presence/location/", {
        "latitude": pos3_lat,
        "longitude": pos3_lon,
        "accuracy": 12.0,
        "speed": 2.0,
        "heading": 10.0,
        "captured_at": t3.isoformat(),
    }, format="json")
    force_authenticate(req, user=tech_user)
    res = view(req)
    assert res.status_code == status.HTTP_200_OK

    active_session.refresh_from_db()
    assert active_session.consecutive_arrival_fixes == 1, f"Expected 1 fix, got {active_session.consecutive_arrival_fixes}"
    assert active_session.geofence_status == "ARRIVING", f"Expected ARRIVING (<=250m), got {active_session.geofence_status}"
    print(f"  PASS: Fix 1 recorded. consecutive_arrival_fixes={active_session.consecutive_arrival_fixes}, geofence_status={active_session.geofence_status}")

    print("\n[TEST 6] Automatic Arrival (Fix #2 with >=2s separation) — OTP Generation & State Transition")
    # Simulate >=2s elapsed time for fix 2 confirmation
    active_session.last_fix_time = timezone.now() - timedelta(seconds=3)
    active_session.save()

    t4 = timezone.now()
    req = factory.post("/workforce/presence/location/", {
        "latitude": pos3_lat,
        "longitude": pos3_lon,
        "accuracy": 10.0,
        "speed": 0.0,
        "heading": 10.0,
        "captured_at": t4.isoformat(),
    }, format="json")
    force_authenticate(req, user=tech_user)
    res = view(req)
    assert res.status_code == status.HTTP_200_OK

    job.refresh_from_db()
    assert job.status == "arrived", f"Expected job status 'arrived', got '{job.status}'"
    psv = PreServiceVerification.objects.filter(job=job).first()
    assert psv is not None and psv.geofence_passed is True, "PreServiceVerification geofence_passed should be True."
    assert psv.otp_code, "Work start OTP was not generated."
    print(f"  PASS: Job #{job.id} automatically arrived! OTP={psv.otp_code}, geofence_passed={psv.geofence_passed}")

    active_session.refresh_from_db()
    assert active_session.geofence_status == "ARRIVED", f"Expected ARRIVED, got {active_session.geofence_status}"
    print(f"  PASS: Session geofence_status={active_session.geofence_status}")

    print("\n[TEST 7] WorkforceJobLiveTrackingView REST Endpoint Verification")
    track_view = WorkforceJobLiveTrackingView.as_view()
    req = factory.get(f"/workforce/jobs/{job.id}/live-tracking/")
    force_authenticate(req, user=cust_user)
    res = track_view(req, pk=job.id)
    assert res.status_code == status.HTTP_200_OK, f"Expected 200, got {res.status_code}"
    data = res.data
    assert data["job_id"] == job.id
    assert data["status"] == "ARRIVED"
    assert data["movement_status"] in ["STATIONARY", "UNKNOWN", "MOVING"]
    assert data["geofence_status"] == "ARRIVED"
    assert data["geofence_passed"] is True
    assert data["start_otp"] == psv.otp_code  # Customer can see the OTP
    assert data["assigned_technician"]["name"] == "Bob Technician"
    assert data["assigned_technician"]["location"]["latitude"] == pos3_lat
    print(f"  PASS: REST live-tracking returns full metadata: movement_status={data['movement_status']}, geofence_status={data['geofence_status']}, start_otp={data['start_otp']}")

    print("\n[TEST 8] Concurrency & Reassignment Safety on Acceptance")
    # Complete job 1 first so technician workload is free
    job.status = "completed"
    job.save()

    # Simulate offer accept for another job
    job2, _ = ServiceRequest.objects.get_or_create(
        request_id="REQ-LOC-TEST-002",
        defaults={
            "company": company,
            "customer": cust_user,
            "preferred_date": now.date(),
            "preferred_time": "10:00:00",
            "status": "pending",
            "latitude": cust_lat,
            "longitude": cust_lon,
        }
    )
    job2.status = "pending"
    job2.save()

    offer, _ = WorkforceJobOffer.objects.get_or_create(
        job=job2,
        employee=emp,
        defaults={
            "status": "OFFERED",
            "wave_number": 1,
            "expires_at": timezone.now() + timedelta(minutes=5),
        }
    )
    offer.status = "OFFERED"
    offer.expires_at = timezone.now() + timedelta(minutes=5)
    offer.save()

    accept_view = WorkforceJobAcceptOfferView.as_view()
    req = factory.post(f"/workforce/jobs/{job2.id}/accept-offer/")
    force_authenticate(req, user=tech_user)
    res = accept_view(req, pk=job2.id)
    assert res.status_code == status.HTTP_200_OK, f"Expected 200, got {res.status_code}: {res.data}"

    active_sessions = JobTrackingSession.objects.filter(job=job2, status="ACTIVE")
    assert active_sessions.count() == 1, f"Expected exactly 1 active session, got {active_sessions.count()}"
    print(f"  PASS: Exactly 1 active tracking session created for Job #{job2.id} upon acceptance.")

    print("\n" + "=" * 70)
    print("ALL 8 VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
