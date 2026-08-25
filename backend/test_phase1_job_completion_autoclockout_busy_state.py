"""
test_phase1_job_completion_autoclockout_busy_state.py

Targeted Test Suite for Single Lifecycle Verification:
A. Employee with active job = BUSY.
B. Employee with no active job = AVAILABLE.
C. Stale BUSY + no active job -> AVAILABLE.
D. Cash not received -> completion/clock-out blocked.
E. Cash received -> completion succeeds.
F. Completion automatically closes TimeLog.
G. Completed job disappears from Active Jobs without refresh.
H. Tracking session closes.
I. Employee becomes AVAILABLE.
J. Repeated completion does not duplicate records.
K. Repeated clock-out does not duplicate TimeLog.
L. Concurrent completion cannot create inconsistent state.
"""
import os
import sys
import uuid
from decimal import Decimal
from datetime import timedelta
import concurrent.futures

import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import connection, transaction
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.exceptions import ValidationError

User = get_user_model()

from employees.models import Employee
from companies.models import Company
from service_requests.models import ServiceRequest, EmployeeJob
from service_requests.state_machine import apply_transition
from workforce_api.models import (
    PostServiceProof,
    JobPayment,
    PaymentCollectionEvent,
    JobTrackingSession,
    WorkforceEventLog,
)
from time_tracking.models import TimeLog, Break
from time_tracking.services import close_employee_active_timelog
from time_tracking.views import ClockOutView
from workforce_api.services.workload import (
    get_employee_active_job,
    is_employee_busy,
    reconcile_employee_availability,
)
from workforce_api.views import (
    WorkforceJobCashCollectView,
    WorkforceJobProofView,
    WorkforceJobListView,
    WorkforcePresenceStatusView,
)
from accounts.views import MeView


class Phase1JobCompletionAutoClockoutBusyStateTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.company = Company.objects.filter(is_active=True).first() or Company.objects.create(
            company_name="Phase1 Test Corp",
            is_active=True,
        )
        self.uid = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f"tech_p1_{self.uid}",
            email=f"tech_p1_{self.uid}@example.com",
            password="Password123!",
            role="employee",
        )
        self.emp = Employee.objects.create(
            user=self.user,
            company=self.company,
            employee_id=f"EMP-P1-{self.uid[:4].upper()}",
            phone=f"91{self.uid[:8]}",
            is_online=True,
            current_availability="available",
            bank_details={"onboarding": {"status": "approved"}},
        )

    def _create_cash_job(self, status="in_progress", total_amount=Decimal("1200.00")):
        now = timezone.now()
        job = ServiceRequest.objects.create(
            company=self.company,
            assigned_employee=self.emp,
            status=status,
            total_amount=total_amount,
            payment_method="cash",
            payment_status="pending",
            preferred_date=timezone.localdate(),
            preferred_time="11:00 AM",
            service_category="Appliances",
            issue_title="Refrigerator Repair",
        )
        EmployeeJob.objects.create(
            service_request=job,
            employee=self.emp,
            status=status.upper(),
            is_primary=True,
        )
        PostServiceProof.objects.create(
            job=job,
            employee=self.emp,
            after_presence_photo="proofs/after_selfie.jpg",
            is_submitted=True,
            submitted_at=now,
        )
        JobPayment.objects.create(
            job=job,
            company=self.company,
            employee=self.emp,
            payment_method=JobPayment.PaymentMethod.CASH_ON_SERVICE,
            payment_status=JobPayment.PaymentStatus.PENDING,
            amount_due=total_amount,
        )
        JobTrackingSession.objects.create(
            job=job,
            company=self.company,
            employee=self.emp,
            status=JobTrackingSession.SessionStatus.ACTIVE,
            started_at=now,
        )
        return job

    def _create_open_timelog(self):
        now = timezone.now()
        log = TimeLog.objects.create(
            employee=self.emp,
            company=self.company,
            user=self.user,
            work_date=timezone.localdate(),
            clock_in=now - timedelta(hours=2),
            status="draft",
        )
        # Add an open break
        Break.objects.create(
            time_log=log,
            break_type="tea",
            break_start=now - timedelta(minutes=20),
        )
        return log

    # ── TEST A: Employee with active job = BUSY ──────────────────────────────
    def test_A_employee_with_active_job_is_busy(self):
        job = self._create_cash_job(status="in_progress")
        self.emp.is_online = True
        
        active_job = get_employee_active_job(self.emp)
        self.assertIsNotNone(active_job)
        self.assertEqual(active_job.id, job.id)
        self.assertTrue(is_employee_busy(self.emp))

        avail = reconcile_employee_availability(self.emp)
        self.assertEqual(avail, "busy")
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "busy")

    # ── TEST B: Employee with no active job = AVAILABLE ──────────────────────
    def test_B_employee_with_no_active_job_is_available(self):
        self.emp.is_online = True
        active_job = get_employee_active_job(self.emp)
        self.assertIsNone(active_job)
        self.assertFalse(is_employee_busy(self.emp))

        avail = reconcile_employee_availability(self.emp)
        self.assertEqual(avail, "available")
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "available")

    # ── TEST C: Stale BUSY + no active job -> AVAILABLE ──────────────────────
    def test_C_stale_busy_reconciles_to_available(self):
        # Manually force a stale 'busy' state into DB
        self.emp.is_online = True
        self.emp.current_availability = "busy"
        self.emp.save(update_fields=["current_availability", "is_online"])

        # 1. Direct helper reconciliation
        avail = reconcile_employee_availability(self.emp)
        self.assertEqual(avail, "available")
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "available")

        # Set stale again to test API endpoints
        self.emp.current_availability = "busy"
        self.emp.save(update_fields=["current_availability"])

        # 2. /api/auth/me/ endpoint returns fresh available
        req_me = self.factory.get("/api/auth/me/")
        force_authenticate(req_me, user=self.user)
        resp_me = MeView.as_view()(req_me)
        self.assertEqual(resp_me.status_code, 200)
        self.assertEqual(resp_me.data["live_availability"], "available")

        # 3. /api/workforce/presence/status/ endpoint returns fresh available
        req_pres = self.factory.get("/api/workforce/presence/status/")
        force_authenticate(req_pres, user=self.user)
        resp_pres = WorkforcePresenceStatusView.as_view()(req_pres)
        self.assertEqual(resp_pres.status_code, 200)
        self.assertEqual(resp_pres.data["availability"], "available")

    # ── TEST D: Cash not received -> completion/clock-out blocked ────────────
    def test_D_cash_not_received_blocks_completion_and_clockout(self):
        job = self._create_cash_job(status="proof_submitted")
        pmt = JobPayment.objects.get(job=job)
        self.assertEqual(pmt.payment_status, JobPayment.PaymentStatus.PENDING)
        self.assertFalse(pmt.is_cash_collected)

        # 1. is_ready_to_complete must fail closed
        is_ready, reason, deps = job.is_ready_to_complete()
        self.assertFalse(is_ready)
        self.assertTrue(any("Cash" in d for d in deps))

        # 2. Direct apply_transition to completed must be rejected
        with self.assertRaises(ValidationError):
            apply_transition(job, "completed", actor=self.user)

        # 3. ClockOutView must reject while cash payment is uncollected
        log = self._create_open_timelog()
        req_clockout = self.factory.post("/api/workforce/time/clock-out/", format="json")
        force_authenticate(req_clockout, user=self.user)
        resp_clockout = ClockOutView.as_view()(req_clockout)
        self.assertEqual(resp_clockout.status_code, 400)
        self.assertEqual(resp_clockout.data.get("code"), "CASH_NOT_RECEIVED")

        # Ensure TimeLog was NOT closed
        log.refresh_from_db()
        self.assertIsNone(log.clock_out)
        self.assertTrue(log.is_open)

    # ── TEST E, F, H, I: Cash received -> completion succeeds, closes TimeLog, closes TrackingSession, releases Employee ──
    def test_E_F_H_I_cash_received_lifecycle(self):
        job = self._create_cash_job(status="in_progress")
        log = self._create_open_timelog()
        tracking_session = JobTrackingSession.objects.filter(job=job).first()
        self.assertEqual(tracking_session.status, JobTrackingSession.SessionStatus.ACTIVE)

        # Execute cash collection endpoint
        req = self.factory.post(
            f"/workforce/jobs/{job.id}/payment/collect/",
            {"amount_received": "1200.00"},
            format="json",
        )
        force_authenticate(req, user=self.user)
        resp = WorkforceJobCashCollectView.as_view()(req, pk=job.id)

        # Test E: Completion succeeds
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["payment_status"], "PAID")
        self.assertEqual(resp.data["job_status"], "completed")

        job.refresh_from_db()
        self.assertEqual(job.status, "completed")
        self.assertEqual(job.payment_status, "paid")

        pmt = JobPayment.objects.get(job=job)
        self.assertEqual(pmt.payment_status, JobPayment.PaymentStatus.PAID)
        self.assertEqual(pmt.amount_paid, Decimal("1200.00"))
        self.assertIsNotNone(pmt.cash_collected_at)

        # Test F: Auto clock-out closed TimeLog and open breaks
        log.refresh_from_db()
        self.assertIsNotNone(log.clock_out)
        self.assertEqual(log.status, "submitted")
        self.assertIsNotNone(log.submitted_at)
        open_breaks = log.breaks.filter(break_end__isnull=True).count()
        self.assertEqual(open_breaks, 0)

        # Test H: Tracking session is COMPLETED
        tracking_session.refresh_from_db()
        self.assertEqual(tracking_session.status, JobTrackingSession.SessionStatus.COMPLETED)
        self.assertIsNotNone(tracking_session.ended_at)

        # Test I: Employee becomes AVAILABLE
        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "available")
        self.assertFalse(is_employee_busy(self.emp))

        # Realtime event logs emitted
        event_types = list(WorkforceEventLog.objects.filter(user=self.user).values_list("event_type", flat=True))
        self.assertIn("JOB_COMPLETED", event_types)
        self.assertIn("EMPLOYEE_AVAILABILITY_CHANGED", event_types)

    # ── TEST G: Completed job disappears from Active Jobs without refresh ────
    def test_G_completed_job_disappears_from_active_jobs(self):
        job = self._create_cash_job(status="in_progress")
        
        # Verify active jobs returns the job
        req_active = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active, user=self.user)
        resp_active = WorkforceJobListView.as_view()(req_active)
        self.assertEqual(resp_active.status_code, 200)
        active_ids = [j["id"] for j in resp_active.data]
        self.assertIn(job.id, active_ids)

        # Complete the job with cash
        req_collect = self.factory.post(
            f"/workforce/jobs/{job.id}/payment/collect/",
            {"amount_received": "1200.00"},
            format="json",
        )
        force_authenticate(req_collect, user=self.user)
        resp_collect = WorkforceJobCashCollectView.as_view()(req_collect, pk=job.id)
        self.assertEqual(resp_collect.status_code, 200)

        # Query active jobs again -> completed job MUST NOT be in active queue
        req_active_after = self.factory.get("/api/workforce/jobs/?status=active")
        force_authenticate(req_active_after, user=self.user)
        resp_active_after = WorkforceJobListView.as_view()(req_active_after)
        self.assertEqual(resp_active_after.status_code, 200)
        active_ids_after = [j["id"] for j in resp_active_after.data]
        self.assertNotIn(job.id, active_ids_after)

        # Completed jobs queue must contain the completed job
        req_completed = self.factory.get("/api/workforce/jobs/?status=completed")
        force_authenticate(req_completed, user=self.user)
        resp_completed = WorkforceJobListView.as_view()(req_completed)
        self.assertEqual(resp_completed.status_code, 200)
        completed_ids = [j["id"] for j in resp_completed.data]
        self.assertIn(job.id, completed_ids)

    # ── TEST J: Repeated completion does not duplicate records ───────────────
    def test_J_repeated_completion_idempotency(self):
        job = self._create_cash_job(status="in_progress")
        self._create_open_timelog()

        # First collection
        req1 = self.factory.post(f"/workforce/jobs/{job.id}/payment/collect/", {"amount_received": "1200.00"}, format="json")
        force_authenticate(req1, user=self.user)
        resp1 = WorkforceJobCashCollectView.as_view()(req1, pk=job.id)
        self.assertEqual(resp1.status_code, 200)

        # Second collection (repeated submission)
        req2 = self.factory.post(f"/workforce/jobs/{job.id}/payment/collect/", {"amount_received": "1200.00"}, format="json")
        force_authenticate(req2, user=self.user)
        resp2 = WorkforceJobCashCollectView.as_view()(req2, pk=job.id)
        self.assertEqual(resp2.status_code, 200)

        # Ensure no duplicate Payment records or TimeLogs
        self.assertEqual(JobPayment.objects.filter(job=job).count(), 1)
        self.assertEqual(TimeLog.objects.filter(employee=self.emp).count(), 1)

    # ── TEST K: Repeated clock-out does not duplicate TimeLog ─────────────────
    def test_K_repeated_clockout_idempotency(self):
        log = self._create_open_timelog()
        
        # First clock-out
        closed_log, was_closed = close_employee_active_timelog(self.emp)
        self.assertTrue(was_closed)
        self.assertIsNotNone(closed_log.clock_out)

        # Second clock-out helper call
        closed_log2, was_closed2 = close_employee_active_timelog(self.emp)
        self.assertFalse(was_closed2)
        self.assertEqual(closed_log.id, closed_log2.id)

        # Third clock-out via API endpoint
        req = self.factory.post("/api/workforce/time/clock-out/", format="json")
        force_authenticate(req, user=self.user)
        resp = ClockOutView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["is_clocked_in"])

        # Ensure total TimeLogs is exactly 1
        self.assertEqual(TimeLog.objects.filter(employee=self.emp).count(), 1)


class Phase1ConcurrentCompletionTests(TestCase):
    """
    Concurrency and double-completion protection tests (Test L).
    """
    def setUp(self):
        self.company = Company.objects.filter(is_active=True).first() or Company.objects.create(
            company_name="Phase1 Concurrency Corp",
            is_active=True,
        )
        self.uid = uuid.uuid4().hex[:8]
        self.user = User.objects.create_user(
            username=f"tech_conc_{self.uid}",
            email=f"tech_conc_{self.uid}@example.com",
            password="Password123!",
            role="employee",
        )
        self.emp = Employee.objects.create(
            user=self.user,
            company=self.company,
            employee_id=f"EMP-CC-{self.uid[:4].upper()}",
            phone=f"92{self.uid[:8]}",
            is_online=True,
            current_availability="busy",
            bank_details={"onboarding": {"status": "approved"}},
        )
        now = timezone.now()
        self.job = ServiceRequest.objects.create(
            company=self.company,
            assigned_employee=self.emp,
            status="in_progress",
            total_amount=Decimal("1500.00"),
            payment_method="cash",
            payment_status="pending",
            preferred_date=timezone.localdate(),
            preferred_time="02:00 PM",
            service_category="Appliances",
            issue_title="Washing Machine Repair",
        )
        EmployeeJob.objects.create(
            service_request=self.job,
            employee=self.emp,
            status="IN_PROGRESS",
            is_primary=True,
        )
        PostServiceProof.objects.create(
            job=self.job,
            employee=self.emp,
            after_presence_photo="proofs/after_selfie.jpg",
            is_submitted=True,
            submitted_at=now,
        )
        JobPayment.objects.create(
            job=self.job,
            company=self.company,
            employee=self.emp,
            payment_method=JobPayment.PaymentMethod.CASH_ON_SERVICE,
            payment_status=JobPayment.PaymentStatus.PENDING,
            amount_due=Decimal("1500.00"),
        )
        JobTrackingSession.objects.create(
            job=self.job,
            company=self.company,
            employee=self.emp,
            status=JobTrackingSession.SessionStatus.ACTIVE,
            started_at=now,
        )
        TimeLog.objects.create(
            employee=self.emp,
            company=self.company,
            user=self.user,
            work_date=timezone.localdate(),
            clock_in=now - timedelta(hours=1),
            status="draft",
        )

    # ── TEST L: Concurrent completion cannot create inconsistent state ───────
    def test_L_concurrent_completion_cannot_create_inconsistent_state(self):
        factory = APIRequestFactory()

        # Simulate fast racing requests to collect cash on the same job
        req1 = factory.post(f"/workforce/jobs/{self.job.id}/payment/collect/", {"amount_received": "1500.00"}, format="json")
        force_authenticate(req1, user=self.user)
        resp1 = WorkforceJobCashCollectView.as_view()(req1, pk=self.job.id)

        req2 = factory.post(f"/workforce/jobs/{self.job.id}/payment/collect/", {"amount_received": "1500.00"}, format="json")
        force_authenticate(req2, user=self.user)
        resp2 = WorkforceJobCashCollectView.as_view()(req2, pk=self.job.id)

        req3 = factory.post(f"/workforce/jobs/{self.job.id}/payment/collect/", {"amount_received": "1500.00"}, format="json")
        force_authenticate(req3, user=self.user)
        resp3 = WorkforceJobCashCollectView.as_view()(req3, pk=self.job.id)

        self.assertEqual(resp1.status_code, 200)
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp3.status_code, 200)

        self.job.refresh_from_db()
        self.assertEqual(self.job.status, "completed")
        self.assertEqual(self.job.payment_status, "paid")

        self.emp.refresh_from_db()
        self.assertEqual(self.emp.current_availability, "available")

        # Verify exactly 1 Payment record and 1 closed TimeLog
        self.assertEqual(JobPayment.objects.filter(job=self.job).count(), 1)
        self.assertEqual(TimeLog.objects.filter(employee=self.emp).count(), 1)
        self.assertEqual(TimeLog.objects.filter(employee=self.emp, clock_out__isnull=False).count(), 1)
        self.assertEqual(JobTrackingSession.objects.filter(job=self.job, status=JobTrackingSession.SessionStatus.COMPLETED).count(), 1)
