"""
test_phase2_packers_movers_discovery.py

Authoritative Test Suite for Phase 2: Packers & Movers Active Job Discovery & Visibility

REQUIRED TESTS:
A. Packers & Movers booking discovered.
B. Packers and Movers naming variant discovered.
C. Goods & Transport still discovered.
D. Repeated reconciliation creates no duplicates.
E. Missed realtime event is recovered.
F. Accepted Packers & Movers job appears in Active Jobs.
G. Active job remains visible without browser refresh.
H. Completed job is removed from Active Jobs.
I. No unrelated service categories regress.
"""

import os
import sys
import uuid
from decimal import Decimal

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

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
)
from time_tracking.models import TimeLog
from workforce_api.services.automatic_dispatch import (
    normalize_service_name,
    canonical_service_match,
    dispatch_job,
    dispatch_pending_jobs,
)
from workforce_api.services.workload import (
    get_employee_active_job,
    is_employee_busy,
    reconcile_employee_availability,
)
from workforce_api.views import (
    WorkforceJobListView,
    WorkforceJobAcceptOfferView,
    WorkforceJobCashCollectView,
)


class Phase2PackersMoversDiscoveryTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.uid = uuid.uuid4().hex[:8]
        self.company = Company.objects.create(
            company_name=f"Packers Movers Test Corp {self.uid}",
            is_active=True,
        )
        self.user = User.objects.create_user(
            username=f"tech_pm_{self.uid}",
            email=f"tech_pm_{self.uid}@example.com",
            password="Password123!",
            role="employee",
            last_known_location={
                "latitude": 12.9716,
                "longitude": 77.5946,
                "accuracy": 10.0,
                "updated_at": timezone.now().isoformat(),
            }
        )
        self.emp = Employee.objects.create(
            user=self.user,
            company=self.company,
            employee_id=f"EMP-PM-{self.uid[:4].upper()}",
            phone=f"94{self.uid[:8]}",
            is_online=True,
            current_availability="available",
            bank_details={
                "onboarding": {
                    "status": "approved",
                    "services": [
                        {"name": "Packers & Movers", "category": "Packers & Movers", "status": "approved"},
                        {"name": "Goods & Transport", "category": "Goods & Transport", "status": "approved"},
                        {"name": "HVAC", "category": "HVAC", "status": "approved"},
                        {"name": "Electrical", "category": "Electrical", "status": "approved"},
                    ]
                }
            },
        )

    def test_A_packers_and_movers_booking_discovered(self):
        """A. Packers & Movers standard booking is discovered and dispatched"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Packers & Movers",
            issue_title="2BHK House Relocation",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("4500.00"),
            payment_method="cash",
            payment_status="pending",
        )
        success, msg = dispatch_job(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")

        offer = WorkforceJobOffer.objects.filter(job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED).first()
        self.assertIsNotNone(offer, "Expected exclusive offer to be created for technician")

        req = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req, user=self.user)
        resp = WorkforceJobListView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(job.id, [j["id"] for j in resp.data])

    def test_B_packers_and_movers_naming_variants_discovered(self):
        """B. Packers and Movers naming variants (casing, whitespace, ampersand, slashes, slugs) are discovered"""
        variants = [
            ("Packers and Movers", "3BHK Shifting"),
            ("packers_movers", "Local moving service"),
            ("PACKERS & MOVERS", "Heavy Goods Moving"),
            ("Packers  &   Movers", "Villa Relocation"),
            ("Packers / Movers", "Intercity Moving"),
            ("house shifting", "Flat Relocation"),
            ("relocation", "Corporate Office Relocation"),
        ]

        for cat, title in variants:
            job = ServiceRequest.objects.create(
                company=self.company,
                status="confirmed",
                service_category=cat,
                issue_title=title,
                preferred_date=timezone.localdate(),
                preferred_time="10:00 AM",
                latitude=Decimal("12.9720"),
                longitude=Decimal("77.5950"),
                total_amount=Decimal("3500.00"),
                payment_method="cash",
                payment_status="pending",
            )
            success, msg = dispatch_job(job)
            self.assertTrue(success, f"Failed to dispatch variant '{cat}': {msg}")
            offer = WorkforceJobOffer.objects.filter(job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED).first()
            self.assertIsNotNone(offer, f"Expected offer for variant '{cat}'")

    def test_C_goods_and_transport_still_discovered(self):
        """C. Goods & Transport category and variants continue working seamlessly"""
        gt_variants = [
            ("Goods & Transport", "Cargo Logistics"),
            ("goods_transport_truck", "Heavy Truck Delivery"),
            ("goods_transport_two_wheeler", "Quick Courier"),
            ("Goods and Transport", "Commercial Freight"),
        ]
        for cat, title in gt_variants:
            job = ServiceRequest.objects.create(
                company=self.company,
                status="confirmed",
                service_category=cat,
                issue_title=title,
                preferred_date=timezone.localdate(),
                preferred_time="10:00 AM",
                latitude=Decimal("12.9720"),
                longitude=Decimal("77.5950"),
                total_amount=Decimal("2000.00"),
                payment_method="cash",
                payment_status="pending",
            )
            success, msg = dispatch_job(job)
            self.assertTrue(success, f"Failed to dispatch Goods & Transport variant '{cat}': {msg}")
            offer = WorkforceJobOffer.objects.filter(job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED).first()
            self.assertIsNotNone(offer, f"Expected offer for GT variant '{cat}'")

    def test_D_repeated_reconciliation_creates_no_duplicates(self):
        """D. Running reconciliation multiple times creates no duplicate offers or jobs"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Packers & Movers",
            issue_title="Duplication Test Shifting",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("4000.00"),
            payment_method="cash",
            payment_status="pending",
        )
        # Run reconciliation 3 times
        r1 = dispatch_pending_jobs(company_id=self.company.id)
        r2 = dispatch_pending_jobs(company_id=self.company.id)
        r3 = dispatch_pending_jobs(company_id=self.company.id)

        offer_count = WorkforceJobOffer.objects.filter(job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED).count()
        self.assertEqual(offer_count, 1, f"Expected exactly 1 active offer, found {offer_count}")

    def test_E_missed_realtime_event_is_recovered(self):
        """E. If a booking is created in database without immediate realtime trigger, reconciliation discovers it"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="new_request",
            service_category="Packers & Movers",
            issue_title="Late Night Booking Recovery",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("5000.00"),
            payment_method="cash",
            payment_status="pending",
        )
        # Clear existing offers to simulate a missed realtime event
        job.job_offers.all().delete()

        # Periodic / on-demand reconciliation discovers pending bookings
        res = dispatch_pending_jobs(company_id=self.company.id)
        self.assertGreaterEqual(res["dispatched_count"], 1)

        offer = WorkforceJobOffer.objects.filter(job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED).first()
        self.assertIsNotNone(offer, "Expected missed booking to be recovered and offered to technician")

    def test_F_accepted_packers_and_movers_job_appears_in_active_jobs(self):
        """F. Accepted Packers & Movers job appears in GET /api/workforce/jobs/?status=active"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Packers & Movers",
            issue_title="House Relocation Accept Test",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("4200.00"),
            payment_method="cash",
            payment_status="pending",
        )
        dispatch_job(job)

        # Accept the offer
        req_accept = self.factory.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
        force_authenticate(req_accept, user=self.user)
        resp_accept = WorkforceJobAcceptOfferView.as_view()(req_accept, pk=job.id)
        self.assertEqual(resp_accept.status_code, 200)

        # Query Active Jobs API
        req_active = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active, user=self.user)
        resp_active = WorkforceJobListView.as_view()(req_active)
        self.assertEqual(resp_active.status_code, 200)

        active_ids = [j["id"] for j in resp_active.data]
        self.assertIn(job.id, active_ids, "Accepted Packers & Movers job must be returned in active jobs API")

    def test_G_active_job_remains_visible_without_refresh(self):
        """G. Active job is returned with proper assignment indicators and payload structure"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Packers & Movers",
            issue_title="Zero Refresh Visibility Job",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("3800.00"),
            payment_method="cash",
            payment_status="pending",
        )
        dispatch_job(job)

        req_accept = self.factory.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
        force_authenticate(req_accept, user=self.user)
        WorkforceJobAcceptOfferView.as_view()(req_accept, pk=job.id)

        req_active = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active, user=self.user)
        resp_active = WorkforceJobListView.as_view()(req_active)
        self.assertEqual(resp_active.status_code, 200)

        active_job_data = next((j for j in resp_active.data if j["id"] == job.id), None)
        self.assertIsNotNone(active_job_data)
        self.assertEqual(active_job_data["status"], "accepted")
        self.assertTrue(active_job_data.get("is_accepted_by_current_employee") or active_job_data.get("is_assigned_to_current_employee"))

    def test_H_completed_job_is_removed_from_active_jobs(self):
        """H. Once job is completed, it is excluded from active jobs and employee is available"""
        now = timezone.now()
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Packers & Movers",
            issue_title="Full Cycle Shifting Job",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("6000.00"),
            payment_method="cash",
            payment_status="pending",
        )
        dispatch_job(job)

        # Accept
        req_accept = self.factory.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
        force_authenticate(req_accept, user=self.user)
        WorkforceJobAcceptOfferView.as_view()(req_accept, pk=job.id)

        # Pre-service verification
        PreServiceVerification.objects.create(
            job=job,
            employee=self.emp,
            geofence_passed=True,
            otp_verified=True,
            presence_photo="proofs/presence_pm.jpg",
            is_complete=True,
            completed_at=now,
        )

        # TimeLog clock-in
        TimeLog.objects.create(
            employee=self.emp,
            company=self.company,
            user=self.user,
            work_date=timezone.localdate(),
            clock_in=now,
            status="draft",
        )
        job.status = "in_progress"
        job.save(update_fields=["status"])

        # Post service proof
        PostServiceProof.objects.create(
            job=job,
            employee=self.emp,
            after_presence_photo="proofs/after_pm.jpg",
            is_submitted=True,
            submitted_at=now,
        )

        # Collect cash
        req_cash = self.factory.post(
            f"/api/workforce/jobs/{job.id}/payment/collect/",
            {"amount_received": "6000.00"},
            format="json",
        )
        force_authenticate(req_cash, user=self.user)
        resp_cash = WorkforceJobCashCollectView.as_view()(req_cash, pk=job.id)
        self.assertEqual(resp_cash.status_code, 200)

        # Verify active jobs excludes completed job
        req_active = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active, user=self.user)
        resp_active = WorkforceJobListView.as_view()(req_active)
        self.assertEqual(resp_active.status_code, 200)
        self.assertNotIn(job.id, [j["id"] for j in resp_active.data])

        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "available")
        self.assertFalse(is_employee_busy(self.emp))

    def test_I_no_unrelated_service_categories_regress(self):
        """I. Normal HVAC, Electrical, and Appliance categories continue to be discovered cleanly"""
        other_categories = [
            ("HVAC", "AC Repair and Gas Refill"),
            ("Electrical", "Switchboard Wiring"),
        ]
        for cat, title in other_categories:
            job = ServiceRequest.objects.create(
                company=self.company,
                status="confirmed",
                service_category=cat,
                issue_title=title,
                preferred_date=timezone.localdate(),
                preferred_time="10:00 AM",
                latitude=Decimal("12.9720"),
                longitude=Decimal("77.5950"),
                total_amount=Decimal("1200.00"),
                payment_method="cash",
                payment_status="pending",
            )
            success, msg = dispatch_job(job)
            self.assertTrue(success, f"Failed to dispatch category '{cat}': {msg}")
            offer = WorkforceJobOffer.objects.filter(job=job, employee=self.emp, status=WorkforceJobOffer.Status.OFFERED).first()
            self.assertIsNotNone(offer, f"Expected offer for category '{cat}'")
