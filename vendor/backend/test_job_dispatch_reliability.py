"""
test_job_dispatch_reliability.py

Focused end-to-end dispatch reliability test suite.

Verifies the complete pipeline:
  Customer booking -> reconcile_booking_for_dispatch() -> WorkforceJobOffer ->
  GET /api/workforce/jobs/?status=active -> Employee accepts -> Assignment confirmed

Test cases:
  A. Normal vendor booking dispatch
  B. Marketplace booking (company_id=NULL) dispatch
  C. Packers & Movers
  D. Goods & Transport
  E. Booking created before employee has GPS -> GPS arrives -> dispatch
  F. Missed initial dispatch -> periodic reconciliation sweep recovers it
  G. Reconciliation runs multiple times -> exactly one active offer (idempotent)
  H. Concurrent reconciliation attempts -> exactly one active offer
  I. Active Jobs API returns the dispatched job
  J. Completed job does NOT appear in Active Jobs
  K. Expired offer does NOT appear in Active Jobs
  L. Employee from a different company cannot see another company's offer
  M. Full real DB flow: booking -> offer -> accept -> assignment (4 categories)

Requirements:
  - All assertions against real DB state.
  - No mocking of dispatch internals.
  - Runs via: python manage.py test test_job_dispatch_reliability --verbosity=2
"""
import threading
import uuid
from datetime import timedelta

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.auth import get_user_model

from service_requests.models import ServiceRequest
from employees.models import Employee
from companies.models import Company
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceEmployeeSchedule,
    WorkforceSkill,
    WorkforceEmployeeSkill,
    WorkforceComplianceRequirement,
    WorkforceEmployeeCompliance,
)
from workforce_api.services.automatic_dispatch import (
    DISPATCHABLE_STATUSES,
    reconcile_booking_for_dispatch,
    dispatch_pending_jobs,
    reconsider_jobs_for_employee,
)
from workforce_api.services.workload import ACTIVE_QUEUE_STATUSES

User = get_user_model()

# ─── Test coordinate constants ─────────────────────────────────────────────────
# Booking location (Bangalore Central)
BOOKING_LAT = 12.9715987
BOOKING_LON = 77.5945627
# Employee location ~0.7 km from booking — well within Wave 1 (0-1 km)
EMP_LAT = 12.9780000
EMP_LON = 77.5975000
GPS_AGE_SECONDS = 20   # Fresh GPS — well within MAX_GPS_AGE_SECONDS


def _make_fresh_gps(lat=EMP_LAT, lon=EMP_LON, age_s=GPS_AGE_SECONDS):
    captured = (timezone.now() - timedelta(seconds=age_s)).isoformat()
    return {
        "latitude": lat,
        "longitude": lon,
        "accuracy": 5.0,
        "captured_at": captured,
        "updated_at": captured,
    }


def _make_company(tag=""):
    """Create a Company for test isolation. Uses company_name (the actual DB column)."""
    name = f"Dispatch Test Co {tag} {uuid.uuid4().hex[:6]}"
    co, _ = Company.objects.get_or_create(
        company_name=name,
        defaults={"is_active": True},
    )
    return co


def _make_employee(company, services=None, lat=EMP_LAT, lon=EMP_LON, with_gps=True):
    """
    Creates a fully onboarding-approved employee who satisfies all 9 eligibility gates:
      Gate 1: is_active=True
      Gate 2: onboarding.status='approved'
      Gate 3: no rejected/pending documents (empty documents dict)
      Gate 4: no mandatory compliance with EXPIRED/REJECTED status (compliance not created here,
               so no blocking records exist — compliance gate passes when no EXPIRED/REJECTED exists)
      Gate 5: schedule set to all 7 days 00:00-23:59
      Gate 6: service listed as approved in bank_details.onboarding.services
      Gate 7: is_online=True
      Gate 8: no active leave (empty leaves list)
      Gate 9: no active job (new employee)
    """
    if services is None:
        services = [
            "HVAC", "AC Repair", "Electrical", "Plumbing", "Cleaning",
            "Pest Control", "Carpentry", "Refrigerator", "Washing Machine",
            "Packers and Movers", "Goods and Transport", "TV and Display",
        ]

    uname = f"rd_tech_{uuid.uuid4().hex[:10]}"
    user = User.objects.create_user(
        username=uname,
        password="TestPass@2024",
        email=f"{uname}@example.com",
        role="employee",
        company=company,
    )

    if with_gps:
        user.last_known_location = _make_fresh_gps(lat, lon)
        user.save(update_fields=["last_known_location"])

    service_entries = [{"name": s, "category": s, "status": "approved"} for s in services]
    emp = Employee.objects.create(
        user=user,
        company=company,
        is_active=True,
        is_online=True,
        current_availability="available",
        bank_details={
            "onboarding": {
                "status": "approved",
                "services": service_entries,
                "documents": {},
            },
            "attendance": {"is_clocked_in": True},
            "leaves": [],
        },
    )

    # Gate 5: Working schedule — all 7 days, full day
    for dow in range(7):
        WorkforceEmployeeSchedule.objects.create(
            employee=emp,
            company=company,
            day_of_week=dow,
            is_working_day=True,
            start_time="00:00:00",
            end_time="23:59:59",
        )

    # Gate 6: Verified skills
    for svc in services:
        skill, _ = WorkforceSkill.objects.get_or_create(company=company, name=svc)
        WorkforceEmployeeSkill.objects.create(
            employee=emp,
            skill=skill,
            is_verified=True,
            proficiency_level="EXPERT",
        )

    return emp


def _make_booking_raw(company=None, status="new_request",
                       service_category="HVAC", issue_title="Test Job",
                       lat=BOOKING_LAT, lon=BOOKING_LON):
    """
    Creates a ServiceRequest via bulk_create to bypass the save() on_commit hook.
    This gives each test full control over WHEN dispatch is triggered.
    """
    job = ServiceRequest(
        status=status,
        service_category=service_category,
        issue_title=issue_title,
        address="Dispatch Test Address, Bangalore",
        latitude=lat,
        longitude=lon,
        preferred_date=timezone.now().date(),
        preferred_time="10:00 AM",
        company=company,
        customer_name="Dispatch Test Customer",
        phone="9000000000",
        request_id=f"SR-RD-{uuid.uuid4().hex[:8].upper()}",
    )
    created = ServiceRequest.objects.bulk_create([job])
    return ServiceRequest.objects.get(pk=created[0].pk)


# ═══════════════════════════════════════════════════════════════════════════════
# A. Normal vendor booking dispatch
# ═══════════════════════════════════════════════════════════════════════════════
class TestA_NormalVendorDispatch(TestCase):
    def setUp(self):
        self.company = _make_company("A")
        self.emp = _make_employee(self.company, services=["HVAC", "AC Repair"])

    def test_a1_dispatch_creates_offer(self):
        """Booking creation triggers offer for eligible employee."""
        job = _make_booking_raw(company=self.company, service_category="HVAC")
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")
        offer = WorkforceJobOffer.objects.filter(
            job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED,
        ).first()
        self.assertIsNotNone(offer, "Offer must be created for eligible employee.")
        self.assertGreater(offer.expires_at, timezone.now(), "Offer must not be expired.")

    def test_a2_received_status_in_dispatchable_statuses(self):
        """'received' must be in DISPATCHABLE_STATUSES so Marketplace bookings dispatch."""
        self.assertIn("received", DISPATCHABLE_STATUSES,
                      "'received' must be in DISPATCHABLE_STATUSES.")

    def test_a3_received_status_booking_dispatches(self):
        """Booking with status 'received' (Marketplace) must dispatch."""
        job = _make_booking_raw(company=self.company, status="received", service_category="HVAC")
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"'received' status booking not dispatched: {msg}")


# ═══════════════════════════════════════════════════════════════════════════════
# B. Marketplace booking (company_id=NULL) dispatch
# ═══════════════════════════════════════════════════════════════════════════════
class TestB_MarketplaceDispatch(TestCase):
    def setUp(self):
        self.company = _make_company("B")
        self.emp = _make_employee(self.company, services=["Plumbing"])

    def test_b1_null_company_booking_dispatched_to_vendor_employee(self):
        """Marketplace booking (company_id=NULL) dispatches to vendor employees."""
        job = _make_booking_raw(company=None, status="new_request", service_category="Plumbing")
        self.assertIsNone(job.company_id)
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"Marketplace booking not dispatched: {msg}")
        offer = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).first()
        self.assertIsNotNone(offer, "Offer must be created for Marketplace booking.")

    def test_b2_reconsider_finds_marketplace_booking(self):
        """reconsider_jobs_for_employee must include Marketplace (NULL company) bookings."""
        job = _make_booking_raw(company=None, status="new_request", service_category="Plumbing",
                                 issue_title="Tap Repair")
        count = reconsider_jobs_for_employee(self.emp)
        offer = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).first()
        self.assertIsNotNone(
            offer,
            "reconsider_jobs_for_employee must dispatch Marketplace (NULL company) bookings."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# C. Packers & Movers
# ═══════════════════════════════════════════════════════════════════════════════
class TestC_PackersMovers(TestCase):
    def setUp(self):
        self.company = _make_company("C")
        self.emp = _make_employee(self.company, services=["Packers and Movers"])

    def test_c1_packers_movers_dispatches(self):
        job = _make_booking_raw(
            company=self.company, status="new_request",
            service_category="Packers and Movers", issue_title="House Shifting",
        )
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"Packers & Movers dispatch failed: {msg}")
        offer_count = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).count()
        self.assertGreaterEqual(offer_count, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# D. Goods & Transport
# ═══════════════════════════════════════════════════════════════════════════════
class TestD_GoodsTransport(TestCase):
    def setUp(self):
        self.company = _make_company("D")
        self.emp = _make_employee(self.company, services=["Goods and Transport"])

    def test_d1_goods_transport_dispatches(self):
        job = _make_booking_raw(
            company=self.company, status="new_request",
            service_category="Goods and Transport", issue_title="Goods Transport",
        )
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"Goods & Transport dispatch failed: {msg}")
        offer_count = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).count()
        self.assertGreaterEqual(offer_count, 1)


# ═══════════════════════════════════════════════════════════════════════════════
# E. Booking exists before employee has GPS -> GPS arrives -> dispatch
# ═══════════════════════════════════════════════════════════════════════════════
class TestE_LateGPS(TestCase):
    def setUp(self):
        self.company = _make_company("E")
        self.emp = _make_employee(self.company, services=["Electrical"], with_gps=False)

    def test_e1_late_gps_triggers_dispatch_via_reconsider(self):
        # Confirm no GPS
        loc = getattr(self.emp.user, "last_known_location", None) or {}
        self.assertFalse(loc.get("latitude"), "Employee must start without GPS.")

        job = _make_booking_raw(company=self.company, service_category="Electrical",
                                 issue_title="Fan Repair")

        # First reconcile — no eligible employee (no GPS) — should fail
        reconcile_booking_for_dispatch(job)
        offer_before = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).count()

        # Employee gets fresh GPS
        self.emp.user.last_known_location = _make_fresh_gps()
        self.emp.user.save(update_fields=["last_known_location"])

        # reconsider picks up the job
        reconsider_jobs_for_employee(self.emp)

        offer_after = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).count()
        self.assertGreater(offer_after, 0,
                            "Offer must exist after employee gets GPS and reconsider runs.")


# ═══════════════════════════════════════════════════════════════════════════════
# F. Missed dispatch -> reconciliation sweep recovers
# ═══════════════════════════════════════════════════════════════════════════════
class TestF_MissedDispatch(TestCase):
    def setUp(self):
        self.company = _make_company("F")
        self.emp = _make_employee(self.company, services=["Cleaning"])

    def test_f1_reconciliation_finds_missed_booking(self):
        job = _make_booking_raw(company=self.company, service_category="Cleaning",
                                 issue_title="Full House Cleaning")
        # Simulate missed on_commit: no dispatch called at all
        self.assertEqual(WorkforceJobOffer.objects.filter(job=job).count(), 0,
                          "No offer should exist before reconciliation.")

        result = dispatch_pending_jobs(company_id=self.company.id)
        self.assertGreaterEqual(result["dispatched_count"], 1,
                                 f"Reconciliation failed to dispatch missed booking: {result}")

        offer = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).first()
        self.assertIsNotNone(offer, "Offer must exist after reconciliation sweep.")


# ═══════════════════════════════════════════════════════════════════════════════
# G. Idempotent reconciliation -> exactly one active offer
# ═══════════════════════════════════════════════════════════════════════════════
class TestG_IdempotentDispatch(TestCase):
    def setUp(self):
        self.company = _make_company("G")
        self.emp = _make_employee(self.company, services=["Pest Control"])

    def test_g1_repeated_reconcile_one_offer(self):
        job = _make_booking_raw(company=self.company, service_category="Pest Control",
                                 issue_title="Cockroach Control")
        for _ in range(4):
            reconcile_booking_for_dispatch(job)

        active_offers = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED, expires_at__gt=timezone.now(),
        ).count()
        self.assertEqual(active_offers, 1,
                         f"Expected exactly 1 active offer after 4 reconcile calls, got {active_offers}.")


# ═══════════════════════════════════════════════════════════════════════════════
# H. Concurrent reconciliation -> exactly one active offer
# ═══════════════════════════════════════════════════════════════════════════════
class TestH_ConcurrentDispatch(TestCase):
    def setUp(self):
        self.company = _make_company("H")
        self.emp = _make_employee(self.company, services=["Carpentry"])

    def test_h1_concurrent_dispatch_one_offer(self):
        job = _make_booking_raw(company=self.company, service_category="Carpentry",
                                 issue_title="Door Repair")
        errors = []

        def _run():
            try:
                reconcile_booking_for_dispatch(job)
            except Exception as exc:
                errors.append(str(exc))

        threads = [threading.Thread(target=_run) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertFalse(errors, f"Concurrent dispatch raised exceptions: {errors}")

        active_offers = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED, expires_at__gt=timezone.now(),
        ).count()
        self.assertEqual(active_offers, 1,
                         f"Expected 1 active offer after concurrent dispatch, got {active_offers}.")


# ═══════════════════════════════════════════════════════════════════════════════
# I. Active Jobs API returns the dispatched job
# ═══════════════════════════════════════════════════════════════════════════════
class TestI_ActiveJobsApiReturnsJob(TestCase):
    def setUp(self):
        self.company = _make_company("I")
        self.emp = _make_employee(self.company, services=["Refrigerator"])

    def test_i1_active_jobs_api_shows_offered_job(self):
        job = _make_booking_raw(company=self.company, service_category="Refrigerator",
                                 issue_title="Fridge Repair")
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")

        client = Client()
        self.assertTrue(
            client.login(username=self.emp.user.username, password="TestPass@2024"),
            "Employee login failed."
        )
        response = client.get("/api/workforce/jobs/?status=active")
        self.assertEqual(response.status_code, 200)
        job_ids = [j["id"] for j in response.json()]
        self.assertIn(job.id, job_ids,
                      f"Job #{job.id} not in Active Jobs response. Got IDs: {job_ids}")


# ═══════════════════════════════════════════════════════════════════════════════
# J. Completed job does NOT appear in Active Jobs
# ═══════════════════════════════════════════════════════════════════════════════
class TestJ_CompletedJobNotInActive(TestCase):
    def setUp(self):
        self.company = _make_company("J")
        self.emp = _make_employee(self.company, services=["Washing Machine"])

    def test_j1_completed_job_excluded(self):
        job = _make_booking_raw(company=self.company, service_category="Washing Machine",
                                 issue_title="Washer Repair")
        ServiceRequest.objects.filter(pk=job.pk).update(
            assigned_employee=self.emp, status="completed",
        )

        client = Client()
        client.login(username=self.emp.user.username, password="TestPass@2024")
        response = client.get("/api/workforce/jobs/?status=active")
        self.assertEqual(response.status_code, 200)
        job_ids = [j["id"] for j in response.json()]
        self.assertNotIn(job.id, job_ids, "Completed job must NOT appear in Active Jobs.")


# ═══════════════════════════════════════════════════════════════════════════════
# K. Expired offer does NOT appear in Active Jobs
# ═══════════════════════════════════════════════════════════════════════════════
class TestK_ExpiredOfferNotInActive(TestCase):
    def setUp(self):
        self.company = _make_company("K")
        self.emp = _make_employee(self.company, services=["TV and Display"])

    def test_k1_expired_offer_excluded(self):
        job = _make_booking_raw(company=self.company, status="unassigned",
                                 service_category="TV and Display", issue_title="TV Repair")
        past = timezone.now() - timedelta(minutes=5)
        WorkforceJobOffer.objects.create(
            job=job,
            employee=self.emp,
            status=WorkforceJobOffer.Status.EXPIRED,
            wave_id=uuid.uuid4(),
            wave_number=1,
            offered_at=past - timedelta(minutes=2),
            expires_at=past,
        )

        client = Client()
        client.login(username=self.emp.user.username, password="TestPass@2024")
        response = client.get("/api/workforce/jobs/?status=active")
        self.assertEqual(response.status_code, 200)
        job_ids = [j["id"] for j in response.json()]
        self.assertNotIn(job.id, job_ids,
                         "Job with only an expired offer must NOT appear in Active Jobs.")


# ═══════════════════════════════════════════════════════════════════════════════
# L. Tenant isolation — employee from another company cannot see another offer
# ═══════════════════════════════════════════════════════════════════════════════
class TestL_TenantIsolation(TestCase):
    def setUp(self):
        self.company_a = _make_company("L-A")
        self.company_b = _make_company("L-B")
        self.emp_a = _make_employee(self.company_a, services=["HVAC"])
        self.emp_b = _make_employee(self.company_b, services=["HVAC"])

    def test_l1_employee_b_cannot_see_company_a_job(self):
        job = _make_booking_raw(company=self.company_a, service_category="HVAC",
                                 issue_title="AC Service")
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")

        offer = WorkforceJobOffer.objects.filter(
            job=job, status=WorkforceJobOffer.Status.OFFERED,
        ).first()
        self.assertIsNotNone(offer)
        # Must be dispatched to emp_a (Company A), not emp_b
        self.assertEqual(offer.employee.company_id, self.company_a.id,
                         "Offer must belong to Company A's employee.")

        # emp_b (Company B) must NOT see this job
        client = Client()
        client.login(username=self.emp_b.user.username, password="TestPass@2024")
        response = client.get("/api/workforce/jobs/?status=active")
        self.assertEqual(response.status_code, 200)
        job_ids = [j["id"] for j in response.json()]
        self.assertNotIn(job.id, job_ids,
                         "Employee from a different company must NOT see another company's job.")


# ═══════════════════════════════════════════════════════════════════════════════
# M. Full real DB flow: booking -> offer -> accept -> assignment
# ═══════════════════════════════════════════════════════════════════════════════
class TestM_FullRealDbFlow(TestCase):
    """
    Verifies the complete dispatch and acceptance lifecycle against real DB state.
    Covers: Normal HVAC, Packers & Movers, Goods & Transport, Marketplace (NULL company).
    """

    def _run_full_flow(self, company, emp, service_category, issue_title, marketplace=False):
        booking_company = None if marketplace else company
        job = _make_booking_raw(
            company=booking_company, status="new_request",
            service_category=service_category, issue_title=issue_title,
        )

        # Step 1: Dispatch
        success, msg = reconcile_booking_for_dispatch(job)
        self.assertTrue(success, f"[{issue_title}] Dispatch failed: {msg}")

        # Step 2: Offer exists for the employee
        offer = WorkforceJobOffer.objects.filter(
            job=job, employee=emp,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=timezone.now(),
        ).first()
        self.assertIsNotNone(offer, f"[{issue_title}] No active offer for employee #{emp.id}.")

        # Step 3: Active Jobs API shows the job
        client = Client()
        self.assertTrue(
            client.login(username=emp.user.username, password="TestPass@2024"),
            f"[{issue_title}] Employee login failed."
        )
        response = client.get("/api/workforce/jobs/?status=active")
        self.assertEqual(response.status_code, 200)
        job_ids = [j["id"] for j in response.json()]
        self.assertIn(job.id, job_ids,
                      f"[{issue_title}] Job not in Active Jobs. IDs: {job_ids}")

        # Step 4: Employee accepts the offer
        accept_resp = client.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
        self.assertIn(accept_resp.status_code, [200, 201],
                      f"[{issue_title}] Accept failed ({accept_resp.status_code}): {accept_resp.content}")

        # Step 5: Assignment confirmed in DB
        job.refresh_from_db()
        self.assertEqual(job.assigned_employee_id, emp.id,
                         f"[{issue_title}] Job must be assigned to the accepting employee.")
        self.assertIn(job.status, ACTIVE_QUEUE_STATUSES,
                      f"[{issue_title}] Post-accept status '{job.status}' not in ACTIVE_QUEUE_STATUSES.")

        return job

    def test_m1_normal_hvac(self):
        company = _make_company("M1")
        emp = _make_employee(company, services=["HVAC"])
        self._run_full_flow(company, emp, "HVAC", "AC Not Cooling")

    def test_m2_packers_and_movers(self):
        company = _make_company("M2")
        emp = _make_employee(company, services=["Packers and Movers"])
        self._run_full_flow(company, emp, "Packers and Movers", "House Shifting")

    def test_m3_goods_and_transport(self):
        company = _make_company("M3")
        emp = _make_employee(company, services=["Goods and Transport"])
        self._run_full_flow(company, emp, "Goods and Transport", "Goods Transport")

    def test_m4_marketplace_null_company(self):
        """Marketplace: company_id=NULL. After accept, company is bound to employee's company."""
        company = _make_company("M4")
        emp = _make_employee(company, services=["Plumbing"])
        job = self._run_full_flow(company, emp, "Plumbing", "Pipe Leak Repair", marketplace=True)
        job.refresh_from_db()
        self.assertEqual(
            job.company_id, company.id,
            "After accepting a Marketplace booking, company_id must be bound to the employee's company."
        )
