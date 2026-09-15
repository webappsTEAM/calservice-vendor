"""
test_phase1_real_production_flow_investigation.py

Authoritative Production Flow Diagnostic & Lifecycle Verification:
Tests all 4 real lifecycle categories:
A. Normal service (Appliances / AC / Electrical)
B. Packers & Movers
C. Goods & Transport
D. Completed Cash Job Lifecycle (End-to-End)
"""
import os
import sys
import uuid
from decimal import Decimal
from datetime import timedelta

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
    WorkforceEventLog,
)
from time_tracking.models import TimeLog, Break
from time_tracking.services import close_employee_active_timelog
from time_tracking.views import ClockInView, ClockOutView
from workforce_api.services.workload import (
    get_employee_active_job,
    is_employee_busy,
    reconcile_employee_availability,
)
from workforce_api.services.automatic_dispatch import (
    dispatch_job,
    dispatch_pending_jobs,
)
from workforce_api.views import (
    WorkforceJobListView,
    WorkforceJobAcceptOfferView,
    WorkforceJobCashCollectView,
    WorkforcePresenceStatusView,
)
from accounts.views import MeView


class Phase1RealProductionFlowInvestigationTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.company = Company.objects.filter(is_active=True).first() or Company.objects.create(
            company_name="Investigation Corp",
            is_active=True,
        )
        self.uid = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f"tech_inv_{self.uid}",
            email=f"tech_inv_{self.uid}@example.com",
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
            employee_id=f"EMP-INV-{self.uid[:4].upper()}",
            phone=f"93{self.uid[:8]}",
            is_online=True,
            current_availability="available",
            bank_details={
                "onboarding": {
                    "status": "approved",
                    "services": [
                        {"name": "Appliances", "category": "Appliances", "status": "approved"},
                        {"name": "Packers & Movers", "category": "Packers & Movers", "status": "approved"},
                        {"name": "Goods & Transport", "category": "Goods & Transport", "status": "approved"},
                    ]
                }
            },
        )

    def test_A_normal_service_discovery_dispatch_and_queue(self):
        """A. Normal Service discovery, dispatch, and appearance in active jobs API"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Appliances",
            issue_title="Refrigerator Repair",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("850.00"),
            payment_method="cash",
            payment_status="pending",
        )
        # Dispatch job
        success, msg = dispatch_job(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")

        # Query active jobs API for employee
        req = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req, user=self.user)
        resp = WorkforceJobListView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

        job_ids = [j["id"] for j in resp.data]
        self.assertIn(job.id, job_ids, "Normal service job not found in Active Jobs API")

    def test_B_packers_and_movers_discovery_dispatch_and_queue(self):
        """B. Packers & Movers discovery, dispatch, and appearance in active jobs API"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Packers & Movers",
            issue_title="House Shifting 2BHK",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("4500.00"),
            payment_method="cash",
            payment_status="pending",
        )
        # Dispatch job
        success, msg = dispatch_job(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")

        # Query active jobs API for employee
        req = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req, user=self.user)
        resp = WorkforceJobListView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

        job_ids = [j["id"] for j in resp.data]
        self.assertIn(job.id, job_ids, "Packers & Movers job not found in Active Jobs API")

    def test_C_goods_and_transport_discovery_dispatch_and_queue(self):
        """C. Goods & Transport discovery, dispatch, and appearance in active jobs API"""
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Goods & Transport",
            issue_title="Commercial Cargo Delivery",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("2200.00"),
            payment_method="cash",
            payment_status="pending",
        )
        # Dispatch job
        success, msg = dispatch_job(job)
        self.assertTrue(success, f"Dispatch failed: {msg}")

        # Query active jobs API for employee
        req = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req, user=self.user)
        resp = WorkforceJobListView.as_view()(req)
        self.assertEqual(resp.status_code, 200)

        job_ids = [j["id"] for j in resp.data]
        self.assertIn(job.id, job_ids, "Goods & Transport job not found in Active Jobs API")

    def test_D_complete_end_to_end_cash_lifecycle_and_synchronization(self):
        """
        D. Complete End-to-End Real Flow:
        Booking -> Offer -> Accept -> Pre-Service -> Auto Clock-In -> Busy -> Cash Collect ->
        Complete -> Auto Clock-Out -> Available -> Job Removed from Active Queue
        """
        now = timezone.now()
        job = ServiceRequest.objects.create(
            company=self.company,
            status="confirmed",
            service_category="Appliances",
            issue_title="Microwave Oven Diagnostics",
            preferred_date=timezone.localdate(),
            preferred_time="10:00 AM",
            latitude=Decimal("12.9720"),
            longitude=Decimal("77.5950"),
            total_amount=Decimal("950.00"),
            payment_method="cash",
            payment_status="pending",
        )

        # 1. Dispatch
        success, msg = dispatch_job(job)
        self.assertTrue(success)

        # 2. Accept offer
        req_accept = self.factory.post(f"/api/workforce/jobs/{job.id}/accept-offer/")
        force_authenticate(req_accept, user=self.user)
        resp_accept = WorkforceJobAcceptOfferView.as_view()(req_accept, pk=job.id)
        self.assertEqual(resp_accept.status_code, 200)

        job.refresh_from_db()
        self.assertEqual(job.status, "accepted")
        self.assertEqual(job.assigned_employee, self.emp)

        # 3. Complete PreServiceVerification (Arrival Geofence, OTP, Presence Photo)
        PreServiceVerification.objects.create(
            job=job,
            employee=self.emp,
            geofence_passed=True,
            otp_verified=True,
            presence_photo="proofs/presence_selfie.jpg",
            is_complete=True,
            completed_at=now,
        )

        # 4. Auto Clock-In Execution
        req_clockin = self.factory.post(
            "/api/workforce/time/clock-in/",
            {
                "job_id": job.id,
                "lat": 12.9720,
                "lon": 77.5950,
                "accuracy": 8.0,
                "address": "GPS Verified Site Arrival",
            },
            format="json",
        )
        force_authenticate(req_clockin, user=self.user)
        resp_clockin = ClockInView.as_view()(req_clockin)
        self.assertIn(resp_clockin.status_code, [200, 201])
        self.assertTrue(resp_clockin.data["is_clocked_in"])

        # 5. Verify Employee is Authoritatively BUSY
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "busy")
        self.assertTrue(is_employee_busy(self.emp))
        active_job = get_employee_active_job(self.emp)
        self.assertEqual(active_job.id, job.id)

        # Check Active Jobs API returns job as IN_PROGRESS
        req_active = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active, user=self.user)
        resp_active = WorkforceJobListView.as_view()(req_active)
        self.assertEqual(resp_active.status_code, 200)
        self.assertIn(job.id, [j["id"] for j in resp_active.data])

        # 6. Submit Post-Service Proof
        PostServiceProof.objects.create(
            job=job,
            employee=self.emp,
            after_presence_photo="proofs/after_selfie.jpg",
            is_submitted=True,
            submitted_at=now,
        )

        # 7. Collect Cash
        req_cash = self.factory.post(
            f"/workforce/jobs/{job.id}/payment/collect/",
            {"amount_received": "950.00"},
            format="json",
        )
        force_authenticate(req_cash, user=self.user)
        resp_cash = WorkforceJobCashCollectView.as_view()(req_cash, pk=job.id)
        self.assertEqual(resp_cash.status_code, 200)
        self.assertEqual(resp_cash.data["payment_status"], "PAID")
        self.assertEqual(resp_cash.data["job_status"], "completed")

        # 8. Verify Database State Post-Completion
        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.payment_status, "paid")

        pmt = JobPayment.objects.get(job=job)
        self.assertEqual(pmt.payment_status, JobPayment.PaymentStatus.PAID)
        self.assertEqual(pmt.amount_paid, Decimal("950.00"))
        self.assertIsNotNone(pmt.cash_collected_at)

        # 9. Verify Auto Clock-Out Closed TimeLog
        time_log = TimeLog.objects.get(employee=self.emp)
        self.assertIsNotNone(time_log.clock_out)
        self.assertEqual(time_log.status, "submitted")
        self.assertIsNotNone(time_log.submitted_at)

        # 10. Verify Tracking Session Closed
        session = JobTrackingSession.objects.filter(job=job).first()
        if session:
            self.assertEqual(session.status, JobTrackingSession.SessionStatus.COMPLETED)
            self.assertIsNotNone(session.ended_at)

        # 11. Verify Employee is Authoritatively AVAILABLE
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "available")
        self.assertFalse(is_employee_busy(self.emp))
        self.assertIsNone(get_employee_active_job(self.emp))

        # 12. Verify Active Jobs API Excludes Completed Job
        req_active_after = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active_after, user=self.user)
        resp_active_after = WorkforceJobListView.as_view()(req_active_after)
        self.assertEqual(resp_active_after.status_code, 200)
        self.assertNotIn(job.id, [j["id"] for j in resp_active_after.data])

        # 13. Verify Presence & Me APIs return AVAILABLE
        req_me = self.factory.get("/api/auth/me/")
        force_authenticate(req_me, user=self.user)
        resp_me = MeView.as_view()(req_me)
        self.assertEqual(resp_me.status_code, 200)
        self.assertEqual(resp_me.data["live_availability"], "available")

        req_pres = self.factory.get("/api/workforce/presence/status/")
        force_authenticate(req_pres, user=self.user)
        resp_pres = WorkforcePresenceStatusView.as_view()(req_pres)
        self.assertEqual(resp_pres.status_code, 200)
        self.assertEqual(resp_pres.data["availability"], "available")

        # 14. Print Diagnostic Table
        print("\n" + "=" * 80)
        print("DIAGNOSTIC CONSISTENCY REPORT:")
        print(f"JOB ID:                  {job.id}")
        print(f"SERVICE:                 {job.service_category}")
        print(f"SERVICE REQUEST STATUS:  {job.status}")
        print(f"EMPLOYEE JOB STATUS:     {EmployeeJob.objects.filter(service_request=job).values_list('status', flat=True).first()}")
        print(f"OFFER STATUS:            {WorkforceJobOffer.objects.filter(job=job).values_list('status', flat=True).first()}")
        print(f"TRACKING SESSION:        {session.status if session else 'NONE'}")
        print(f"TIMELOG:                 clock_in={time_log.clock_in.strftime('%H:%M:%S')}, clock_out={time_log.clock_out.strftime('%H:%M:%S')}, status={time_log.status}")
        print(f"PAYMENT:                 status={pmt.payment_status}, amount_paid=Rs.{pmt.amount_paid}")
        print(f"EMPLOYEE AVAILABILITY:   {self.emp.current_availability}")
        print(f"ACTIVE JOB API COUNT:    {len(resp_active_after.data)}")
        print(f"FRONTEND ACTIVE JOB:     {None}")
        print(f"FRONTEND BUSY:           {False}")
        print("=" * 80 + "\n")
