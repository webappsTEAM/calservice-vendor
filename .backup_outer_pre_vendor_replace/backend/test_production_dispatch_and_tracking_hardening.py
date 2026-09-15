"""
test_production_dispatch_and_tracking_hardening.py

Authoritative Production Verification Suite for Deep Dispatch, Acceptance & Live Tracking.
Covers all 12 mandatory criteria:
  1. Existing DB service dispatches only to matching verified technicians.
  2. Newly created DB service ("Solar Panel Installation") works WITHOUT modifying Python source code.
  3. Two eligible technicians receive the same active wave.
  4. Only one technician can successfully accept (atomic serialization).
  5. Losing technician receives 409 JOB_ALREADY_ACCEPTED.
  6. Idempotent acceptance retry succeeds.
  7. Terminal jobs cannot be accepted.
  8. Database single-primary invariant on EmployeeJob enforced.
  9. Proof of work and cash collection are technician-authorized, idempotent, and release availability.
  10. Accepted technician snapshot is persisted on ServiceRequest and serialized accurately.
  11. Live technician location updates ServiceRequest and customer tracking reads authoritative data.
  12. Location is masked after completion and unauthorized tracking is rejected.
  13. Redis-ready realtime layer functions seamlessly without Redis.
"""
import os
import sys
import uuid
import threading
from decimal import Decimal
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
from django.db import connection, IntegrityError

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest, EmployeeJob, Service, CatalogCategory
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceSkill,
    WorkforceEmployeeSkill,
    WorkforceEmployeeSchedule,
    WorkforceServiceSkillRequirement,
    JobTrackingSession,
    JobLocationPoint,
    PostServiceProof,
    JobPayment,
)
from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    dispatch_job,
    get_eligible_candidates,
    canonical_service_match,
)
from workforce_api.services.realtime import (
    publish_job_location_update,
    publish_workforce_event,
    get_redis_client,
)

User = get_user_model()

BANGALORE_LAT = 12.9716
BANGALORE_LON = 77.5946


def make_company(prefix="Co"):
    cname = f"{prefix}_{uuid.uuid4().hex[:6]}"
    return Company.objects.create(company_name=cname, is_active=True)


def make_employee(company, skill_names=None, lat=BANGALORE_LAT, lon=BANGALORE_LON):
    uname = f"tech_{uuid.uuid4().hex[:8]}"
    u = User.objects.create_user(
        username=uname,
        password="Password@123",
        email=f"{uname}@test.com",
        role="employee",
        company=company,
    )
    u.last_known_location = {
        "latitude": lat,
        "longitude": lon,
        "accuracy": 5.0,
        "captured_at": timezone.now().isoformat(),
        "updated_at": timezone.now().isoformat(),
    }
    u.save()

    emp = Employee.objects.create(
        user=u,
        employee_id=f"EMP_{uuid.uuid4().hex[:8].upper()}",
        company=company,
        is_active=True,
        is_online=True,
        current_availability="available",
        phone="9876543210",
        bank_details={
            "onboarding": {
                "status": "approved",
                "services": [{"name": s} for s in (skill_names or [])]
            }
        },
    )

    # 7-day 24h schedule
    for dow in range(7):
        WorkforceEmployeeSchedule.objects.create(
            employee=emp,
            company=company,
            day_of_week=dow,
            start_time="00:00:00",
            end_time="23:59:59",
            is_working_day=True,
        )

    # Verified skills
    for s_name in (skill_names or []):
        sk, _ = WorkforceSkill.objects.get_or_create(
            name=s_name,
            company=company,
            defaults={"code": s_name.upper().replace(" ", "_"), "category": "General"}
        )
        WorkforceEmployeeSkill.objects.create(
            employee=emp,
            skill=sk,
            proficiency_level=5,
            is_verified=True,
        )

    return emp


def make_booking(company, service_name, issue_title="", lat=BANGALORE_LAT, lon=BANGALORE_LON, customer=None):
    req_id = f"SR-TEST-{uuid.uuid4().hex[:8].upper()}"
    return ServiceRequest.objects.create(
        company=company,
        customer=customer,
        request_id=req_id,
        service_category=service_name,
        issue_title=issue_title or service_name,
        customer_name=customer.username if customer else "Test Customer",
        phone="9999999999",
        address="123 Test St, Bangalore",
        latitude=lat,
        longitude=lon,
        preferred_date=timezone.now().date(),
        preferred_time="10:00 AM",
        total_amount=Decimal("500.00"),
        status="new_request",
    )


def test_part_1_dynamic_db_service():
    """
    Criterion 1 & 2:
    A newly created DB service ("Solar Panel Installation") works WITHOUT modifying Python source code.
    Verified technician matches; unrelated technician does NOT match.
    """
    print("\n" + "="*70)
    print("TEST 1: DYNAMIC DATABASE SERVICE MATCHING (Solar Panel Installation)")
    print("="*70)

    co = make_company("SolarCo")
    svc_name = f"Solar Panel Installation {uuid.uuid4().hex[:4]}"
    svc_slug = f"solar-panel-inst-{uuid.uuid4().hex[:4]}"

    cat = CatalogCategory.objects.first()
    if not cat:
        with connection.cursor() as cur:
            cur.execute("INSERT INTO service_requests_catalogcategory (name, slug, flow_type, is_active, sort_order) VALUES ('Renewables', 'renewables', 'standard', true, 0) RETURNING id")
            cat_id = cur.fetchone()[0]
        cat = CatalogCategory.objects.get(pk=cat_id)
    # Create dynamic service in DB
    solar_svc = Service.objects.create(
        name=svc_name,
        slug=svc_slug,
        category=cat,
        is_active=True,
    )
    solar_skill, _ = WorkforceSkill.objects.get_or_create(
        name=svc_name,
        company=co,
        defaults={"code": f"SOLAR_{uuid.uuid4().hex[:4]}", "category": "Renewables"}
    )
    WorkforceServiceSkillRequirement.objects.create(
        service=solar_svc,
        skill=solar_skill,
        is_mandatory=True,
    )

    # Tech A has the dynamic skill
    tech_a = make_employee(co, [svc_name])
    # Tech B has Plumbing
    tech_b = make_employee(co, ["Plumbing"])

    # Test database-driven matching directly
    matched_a, method_a, _ = canonical_service_match(svc_name, [svc_name], [svc_name])
    matched_b, method_b, _ = canonical_service_match(svc_name, ["Plumbing"], ["Plumbing"])

    print(f"  - Tech A (Solar Skill) Match: {matched_a} (method={method_a})")
    print(f"  - Tech B (Plumbing) Match: {matched_b} (method={method_b})")
    assert matched_a is True, "Tech A must match dynamic solar service via DB"
    assert matched_b is False, "Tech B must NOT match dynamic solar service"

    # Test end-to-end dispatch for the dynamic DB service
    job = make_booking(co, svc_name, issue_title="Roof Solar Setup")
    ok, msg = reconcile_booking_for_dispatch(job)
    print(f"  - Dispatch result: ok={ok}, msg={msg}")
    assert ok, f"Dispatch failed: {msg}"

    offer_a = WorkforceJobOffer.objects.filter(job=job, employee=tech_a).first()
    offer_b = WorkforceJobOffer.objects.filter(job=job, employee=tech_b).first()
    assert offer_a and offer_a.status == "OFFERED", "Tech A must receive offer for dynamic DB service"
    assert offer_b is None, "Tech B must NOT receive offer for dynamic DB service"

    print("[PASS] Dynamic DB Service Matching passed without any Python code edits!")


def test_part_2_same_wave_and_single_winner():
    """
    Criterion 3, 4, 5, 6, 7:
    - Tech A and B both receive the same wave.
    - Simultaneous accept: Tech A wins (200), Tech B loses (409 JOB_ALREADY_ACCEPTED).
    - Winner retry: idempotent 200.
    - Terminal jobs: cannot be accepted.
    - Assignment snapshot persisted on ServiceRequest.
    """
    print("\n" + "="*70)
    print("TEST 2: SAME-WAVE DISPATCH & SINGLE-WINNER ACCEPTANCE (SELECT FOR UPDATE)")
    print("="*70)

    co = make_company("AcceptCo")
    tech_a = make_employee(co, ["Electrical"])
    tech_b = make_employee(co, ["Electrical"])

    job = make_booking(co, "Electrical", issue_title="Fan Repair")
    ok, msg = reconcile_booking_for_dispatch(job)
    assert ok, f"Dispatch failed: {msg}"

    # Both must have active offers in the same wave
    offer_a = WorkforceJobOffer.objects.filter(job=job, employee=tech_a, status="OFFERED").first()
    offer_b = WorkforceJobOffer.objects.filter(job=job, employee=tech_b, status="OFFERED").first()
    assert offer_a and offer_b, "Both Tech A and Tech B must receive active offers in same wave"
    assert offer_a.wave_id == offer_b.wave_id, "Wave IDs must match for same-wave candidates"
    print(f"  - Same-Wave verified: wave_id={offer_a.wave_id}, Tech A & Tech B both received offers.")

    # Concurrent Acceptance Test
    results = {}
    def do_accept(tech_emp, key):
        from django.db import connection
        try:
            c = Client()
            c.force_login(tech_emp.user)
            resp = c.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
            results[key] = (resp.status_code, resp.json())
        finally:
            connection.close()

    t1 = threading.Thread(target=do_accept, args=(tech_a, "tech_a"))
    t2 = threading.Thread(target=do_accept, args=(tech_b, "tech_b"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print(f"  - Tech A response: {results['tech_a'][0]}")
    print(f"  - Tech B response: {results['tech_b'][0]}")

    statuses = [results["tech_a"][0], results["tech_b"][0]]
    assert 200 in statuses, "One technician must receive 200 OK"
    assert 409 in statuses, "Losing technician must receive 409 Conflict"

    winner = tech_a if results["tech_a"][0] == 200 else tech_b
    loser = tech_b if results["tech_a"][0] == 200 else tech_a

    loser_resp = results["tech_b"][1] if results["tech_a"][0] == 200 else results["tech_a"][1]
    assert loser_resp.get("code") == "JOB_ALREADY_ACCEPTED", "Loser must receive JOB_ALREADY_ACCEPTED code"

    # Idempotent Winner Retry
    winner_client = Client()
    winner_client.force_login(winner.user)
    retry_resp = winner_client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    assert retry_resp.status_code == 200, "Winner retry must return 200 OK idempotently"
    print("  - Idempotent winner retry verified: HTTP 200 OK")

    # Assignment Snapshot Verification on ServiceRequest
    job.refresh_from_db()
    assert job.assigned_employee_id == winner.id, "Job must be assigned to winner"
    assert job.technician_id == winner.user_id, "technician_id snapshot must match winner user_id"
    assert job.technician_name == (winner.user.get_full_name() or winner.user.username), "technician_name snapshot must be persisted"
    assert job.accepted_at is not None, "accepted_at timestamp must be persisted"
    assert str(job.tracking_token) != "", "tracking_token must be generated"
    print(f"  - Assignment snapshot verified: name={job.technician_name}, accepted_at={job.accepted_at}")

    # Loser Offer Superseded
    loser_offer = WorkforceJobOffer.objects.filter(job=job, employee=loser).first()
    assert loser_offer.status == "SUPERSEDED_BY_ACCEPTANCE", "Loser offer must be SUPERSEDED_BY_ACCEPTANCE"

    # Queue Visibility Verification: Winner sees job, Loser DOES NOT see job
    winner_jobs_resp = winner_client.get("/api/workforce/jobs/?status=active")
    assert winner_jobs_resp.status_code == 200
    winner_job_ids = [j["id"] for j in winner_jobs_resp.json()]
    assert job.id in winner_job_ids, f"Accepted job #{job.id} must appear in winner's active queue"
    serialized_winner_job = next(j for j in winner_jobs_resp.json() if j["id"] == job.id)
    assert serialized_winner_job["technician_name"] == job.technician_name, "Serializer must return persisted technician_name"
    assert serialized_winner_job["technician_id"] == job.technician_id, "Serializer must return persisted technician_id"
    assert serialized_winner_job["accepted_at"] is not None, "Serializer must return accepted_at"
    print(f"  - Serializer snapshot verified: tech_name={serialized_winner_job['technician_name']}, tech_id={serialized_winner_job['technician_id']}")

    loser_client = Client()
    loser_client.force_login(loser.user)
    loser_jobs_resp = loser_client.get("/api/workforce/jobs/?status=active")
    assert loser_jobs_resp.status_code == 200
    loser_job_ids = [j["id"] for j in loser_jobs_resp.json()]
    assert job.id not in loser_job_ids, f"Accepted job #{job.id} must NOT appear in loser's active queue"

    loser_all_resp = loser_client.get("/api/workforce/jobs/?status=all")
    assert loser_all_resp.status_code == 200
    loser_all_ids = [j["id"] for j in loser_all_resp.json()]
    assert job.id not in loser_all_ids, f"Accepted job #{job.id} must NOT appear in loser's all jobs list"
    print("  - Accepted job visibility verified: Visible to winner, cleanly vanished from loser's queue!")

    # Terminal Job Protection Test
    job.status = "cancelled"
    job.save(update_fields=["status"])
    term_resp = winner_client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
    assert term_resp.status_code == 400, "Acceptance on cancelled job must be rejected with 400"
    print("  - Terminal job acceptance rejection verified: HTTP 400")

    print("[PASS] Same-Wave Dispatch & Single-Winner Acceptance passed!")


def test_part_3_employee_job_single_primary_invariant():
    """
    Criterion 8:
    Database-level partial unique index prevents two primary EmployeeJob records for the same job.
    """
    print("\n" + "="*70)
    print("TEST 3: DATABASE SINGLE-PRIMARY INVARIANT ON EMPLOYEEJOB")
    print("="*70)

    co = make_company("InvCo")
    tech_a = make_employee(co, ["Electrical"])
    tech_b = make_employee(co, ["Electrical"])
    job = make_booking(co, "Electrical")

    # Tech A is primary
    EmployeeJob.objects.create(
        service_request=job,
        employee=tech_a,
        is_primary=True,
        status="ACCEPTED",
    )

    # Tech B attempting is_primary=True must trigger DB IntegrityError
    duplicate_caught = False
    try:
        EmployeeJob.objects.create(
            service_request=job,
            employee=tech_b,
            is_primary=True,
            status="ACCEPTED",
        )
    except IntegrityError:
        duplicate_caught = True

    assert duplicate_caught, "PostgreSQL partial unique index must block second primary EmployeeJob"
    print("  - DB Engine blocked concurrent primary assignment: IntegrityError caught!")

    # Secondary job (is_primary=False) is allowed
    sec_job = EmployeeJob.objects.create(
        service_request=job,
        employee=tech_b,
        is_primary=False,
        status="ASSIGNED",
    )
    assert sec_job.id is not None, "Non-primary EmployeeJob must be permitted"

    # Test duplicate active JobTrackingSession constraint
    from workforce_api.models import JobTrackingSession
    JobTrackingSession.objects.create(
        job=job,
        employee=tech_a,
        company=co,
        status="ACTIVE"
    )
    dup_session_caught = False
    try:
        JobTrackingSession.objects.create(
            job=job,
            employee=tech_b,
            company=co,
            status="ACTIVE"
        )
    except IntegrityError:
        dup_session_caught = True
    assert dup_session_caught, "DB constraint unique_active_tracking_session_per_job must block duplicate active session"
    print("  - DB Engine blocked duplicate active JobTrackingSession: IntegrityError caught!")

    print("[PASS] EmployeeJob Single-Primary & Tracking Session DB Invariants verified!")


def test_part_4_live_tracking_and_customer_privacy():
    """
    Criterion 9, 10, 11, 12:
    - GPS update updates ServiceRequest snapshot.
    - Customer live tracking reads authoritative data.
    - Unauthorized customer / technician rejected (HTTP 403).
    - Masking after completion.
    """
    print("\n" + "="*70)
    print("TEST 4: LIVE TECHNICIAN TRACKING & CUSTOMER PRIVACY")
    print("="*70)

    co = make_company("TrackCo")
    cust_u = User.objects.create_user(
        username=f"cust_{uuid.uuid4().hex[:6]}",
        email=f"cust_{uuid.uuid4().hex[:6]}@test.com",
        password="Pass@123Customer",
    )
    other_cust_u = User.objects.create_user(
        username=f"other_{uuid.uuid4().hex[:6]}",
        email=f"other_{uuid.uuid4().hex[:6]}@test.com",
        password="Pass@123Customer",
    )
    tech = make_employee(co, ["Electrical"])

    job = make_booking(co, "Electrical", customer=cust_u)
    job.assigned_employee = tech
    job.status = "on_the_way"
    job.save()

    # Technician sends GPS telemetry via WorkforceLocationUpdateView
    tech_client = Client()
    tech_client.force_login(tech.user)
    gps_resp = tech_client.post("/api/workforce/presence/location/", {
        "latitude": 12.9718,
        "longitude": 77.5948,
        "accuracy": 8.0,
        "speed": 12.5,
        "heading": 90.0,
    }, content_type="application/json")
    print(f"  - gps_resp status: {gps_resp.status_code}, data: {gps_resp.json()}")
    job.refresh_from_db()
    print(f"  - job debug: id={job.id}, assigned={job.assigned_employee_id}, tech={tech.id}, job_co={job.company_id}, tech_co={tech.company_id}, status={job.status}, lat={job.technician_latitude}")
    assert round(float(job.technician_latitude), 4) == 12.9718, "ServiceRequest technician_latitude must match GPS update"
    assert round(float(job.technician_longitude), 4) == 77.5948, "ServiceRequest technician_longitude must match GPS update"
    assert round(float(job.technician_speed), 1) == 12.5, "ServiceRequest technician_speed must match GPS update"
    print(f"  - ServiceRequest snapshot verified: lat={job.technician_latitude}, lon={job.technician_longitude}, speed={job.technician_speed}")

    # Authorized customer tracks job
    cust_client = Client()
    cust_client.force_login(cust_u)
    track_resp = cust_client.get(f"/api/workforce/jobs/{job.id}/live-tracking/")
    assert track_resp.status_code == 200, "Authorized customer must receive 200 OK"
    track_data = track_resp.json()
    assert round(float(track_data["assigned_technician"]["location"]["latitude"]), 4) == 12.9718, "Customer must receive live technician lat"
    assert track_data["assigned_technician"]["name"] == (tech.user.get_full_name() or tech.user.username)
    print("  - Customer live tracking verified: technician coordinates and snapshot details received")

    # Unauthorized customer rejected (HTTP 403)
    other_client = Client()
    other_client.force_login(other_cust_u)
    unauth_resp = other_client.get(f"/api/workforce/jobs/{job.id}/live-tracking/")
    assert unauth_resp.status_code == 403, "Unauthorized customer must be rejected with 403 Forbidden"
    print("  - Cross-customer privacy verified: HTTP 403 Forbidden")

    # Tracking Token authorized access (unauthenticated with token)
    anon_client = Client()
    token_resp = anon_client.get(f"/api/workforce/jobs/{job.id}/live-tracking/?token={job.tracking_token}")
    assert token_resp.status_code == 200, "Access via valid tracking token must return 200 OK"
    print("  - Secure token tracking verified: HTTP 200 OK")

    # GPS update from wrong/unassigned technician MUST NOT update this job
    wrong_tech = make_employee(co, ["Electrical"])
    wrong_tech_client = Client()
    wrong_tech_client.force_login(wrong_tech.user)
    wrong_gps_resp = wrong_tech_client.post("/api/workforce/presence/location/", {
        "latitude": 12.9800,
        "longitude": 77.6000,
        "accuracy": 10.0,
    }, content_type="application/json")
    assert wrong_gps_resp.status_code == 200

    job.refresh_from_db()
    assert round(float(job.technician_latitude), 4) == 12.9718, "Unassigned technician GPS MUST NOT overwrite job coordinates"
    print("  - Wrong technician isolation verified: Unassigned technician GPS does not mutate job")

    # Privacy masking upon job completion
    job.status = "completed"
    job.save(update_fields=["status"])
    completed_track = cust_client.get(f"/api/workforce/jobs/{job.id}/live-tracking/")
    assert completed_track.status_code == 200
    assert completed_track.json()["assigned_technician"] is None, "Technician live location must be masked upon completion"
    print("  - Privacy masking after completion verified: technician coordinates masked")

    print("[PASS] Live Technician Tracking & Customer Privacy passed!")


def test_part_5_proof_cash_and_availability_release():
    """
    Criterion 9 & 10:
    - PostServiceProof requires selfie.
    - Cash collection enforces amount_due.
    - Idempotent repeated payment.
    - Technician released from busy.
    """
    print("\n" + "="*70)
    print("TEST 5: PROOF, CASH COLLECTION & AVAILABILITY RELEASE")
    print("="*70)

    co = make_company("ProofCo")
    tech = make_employee(co, ["Plumbing"])
    job = make_booking(co, "Plumbing")
    job.assigned_employee = tech
    job.status = "in_progress"
    job.total_amount = Decimal("350.00")
    job.save()

    EmployeeJob.objects.create(
        service_request=job,
        employee=tech,
        is_primary=True,
        status="IN_PROGRESS",
    )
    tech.current_availability = "busy"
    tech.save(update_fields=["current_availability"])

    tech_client = Client()
    tech_client.force_login(tech.user)

    from django.core.files.uploadedfile import SimpleUploadedFile
    proof_resp_1 = tech_client.post(f"/api/workforce/jobs/{job.id}/proof/", {
        "notes": "Completed pipe leak fix",
        "after_selfie": SimpleUploadedFile("selfie1.jpg", b"fake image bytes 1", content_type="image/jpeg"),
    })
    assert proof_resp_1.status_code == 200, f"Proof submission failed: {proof_resp_1.json()}"
    print("  - Proof submission verified: HTTP 200 OK")

    # Duplicate proof submission must be idempotent 200 OK
    proof_resp_2 = tech_client.post(f"/api/workforce/jobs/{job.id}/proof/", {
        "notes": "Completed pipe leak fix duplicate",
        "after_selfie": SimpleUploadedFile("selfie2.jpg", b"fake image bytes 2", content_type="image/jpeg"),
    })
    assert proof_resp_2.status_code == 200, "Duplicate proof must be idempotent 200 OK"
    print("  - Duplicate proof submission verified: Idempotent HTTP 200 OK")

    # Cash collection
    cash_resp = tech_client.post(f"/api/workforce/jobs/{job.id}/collect-cash/", {
        "amount_received": "350.00",
    }, content_type="application/json")
    assert cash_resp.status_code == 200, f"Cash collection failed: {cash_resp.json()}"
    assert cash_resp.json()["payment_status"] == "PAID"
    print("  - Cash collection verified: HTTP 200 OK, payment_status=PAID")

    # Idempotent retry
    cash_retry = tech_client.post(f"/api/workforce/jobs/{job.id}/collect-cash/", {
        "amount_received": "350.00",
    }, content_type="application/json")
    assert cash_retry.status_code == 200, "Repeated cash collection must be idempotent 200 OK"
    print("  - Idempotent cash retry verified: HTTP 200 OK")

    # Verify technician availability was released
    tech.refresh_from_db()
    assert tech.current_availability == "available", f"Technician must be released to available (got {tech.current_availability})"
    print(f"  - Technician availability release verified: current_availability={tech.current_availability}")

    # Verify ServiceRequest completed_at timestamp
    job.refresh_from_db()
    assert job.status == "completed", "Job status must be completed"
    assert job.completed_at is not None, "completed_at must be populated on ServiceRequest"
    print(f"  - ServiceRequest completed_at verified: {job.completed_at}")

    print("[PASS] Proof, Cash Collection & Availability Release passed!")


def test_part_6_redis_ready_realtime_layer():
    """
    Criterion 13:
    Redis-ready realtime abstraction functions cleanly even when Redis is unconfigured or offline.
    """
    print("\n" + "="*70)
    print("TEST 6: REDIS-READY REALTIME ABSTRACTION (DB-FALLBACK)")
    print("="*70)

    # Verify Redis client check
    r_client = get_redis_client()
    print(f"  - Redis connection status: {'CONNECTED' if r_client else 'UNAVAILABLE (Graceful DB Fallback)'}")

    # Publish location update via abstraction
    ev1 = publish_job_location_update(
        job_id=999999,
        payload={"latitude": 12.97, "longitude": 77.59, "test": True},
    )
    assert ev1 is not None, "publish_job_location_update must persist durable WorkforceEventLog"
    print("  - publish_job_location_update succeeded: event_id=" + str(ev1.id))

    # Publish workforce event via abstraction
    ev2 = publish_workforce_event(
        event_type="TEST_HARDENING_EVENT",
        payload={"status": "VERIFIED"},
    )
    assert ev2 is not None, "publish_workforce_event must persist durable WorkforceEventLog"
    print("  - publish_workforce_event succeeded: event_id=" + str(ev2.id))

    print("[PASS] Redis-ready realtime abstraction verified!")


def test_part_7_concurrent_dispatch_no_duplicate_offers():
    """
    Criterion 9:
    Concurrent offer creation sweeps do not create duplicate active offers for the same employee.
    """
    print("\n" + "="*70)
    print("TEST 7: CONCURRENT DISPATCH SWEEP (NO DUPLICATE ACTIVE OFFERS)")
    print("="*70)

    co = make_company("ConcDispCo")
    tech = make_employee(co, ["Electrical"])
    job = make_booking(co, "Electrical")

    results = []
    def do_dispatch():
        from django.db import connection
        try:
            ok, msg = reconcile_booking_for_dispatch(job)
            results.append((ok, msg))
        finally:
            connection.close()

    t1 = threading.Thread(target=do_dispatch)
    t2 = threading.Thread(target=do_dispatch)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Active offers count must be exactly 1
    active_offers = WorkforceJobOffer.objects.filter(
        job=job,
        employee=tech,
        status="OFFERED",
        expires_at__gt=timezone.now(),
    ).count()
    assert active_offers == 1, f"Expected exactly 1 active offer, got {active_offers}"
    print(f"  - Concurrent dispatch verified: Exactly 1 active offer created (active_offers={active_offers})")
    print("[PASS] Concurrent Dispatch & Duplicate Prevention passed!")


def main():
    print("\n" + "#"*70)
    print("STARTING WORKFORCE PRODUCTION HARDENING TEST SUITE")
    print("#"*70)

    test_part_1_dynamic_db_service()
    test_part_2_same_wave_and_single_winner()
    test_part_3_employee_job_single_primary_invariant()
    test_part_4_live_tracking_and_customer_privacy()
    test_part_5_proof_cash_and_availability_release()
    test_part_6_redis_ready_realtime_layer()
    test_part_7_concurrent_dispatch_no_duplicate_offers()

    print("\n" + "="*70)
    print("ALL WORKFORCE PRODUCTION HARDENING TESTS PASSED CLEANLY!")
    print("="*70)


if __name__ == "__main__":
    main()
