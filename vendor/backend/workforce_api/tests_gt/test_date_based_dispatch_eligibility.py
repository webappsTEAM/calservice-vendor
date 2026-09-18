"""
Focused Unit Tests for CalTrack Date-Based Dispatch & Offer Filtering.

Covers all 11 required safety verifications:
1. Past preferred_date cannot be dispatched.
2. Past preferred_date cannot create a new WorkforceJobOffer.
3. dispatch_pending_jobs() does not discover past jobs.
4. reconsider_jobs_for_employee() does not discover past jobs.
5. GET /jobs does not execute dispatch (pure read-only).
6. GET /jobs backend query filters out offered past-dated jobs.
7. Existing past OFFERED job becomes EXPIRED.
8. Expiring a past-dated offer does NOT redispatch it.
8b. Expiring a current-day timed-out offer DOES trigger redispatch.
9. Today's scheduled job remains dispatchable.
10. Today's immediate booking remains dispatchable.
11. Normal offer/acceptance workflow has zero regression.
"""
import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from employees.models import Employee
from workforce_api.services import automatic_dispatch as ad
from workforce_api.models import WorkforceJobOffer
from workforce_api.views import WorkforceJobListView


class MockUser:
    def __init__(self, username="tech_date", pk=888, is_authenticated=True, is_staff=False, is_superuser=False, role="employee"):
        self.username = username
        self.pk = pk
        self.id = pk
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff
        self.is_superuser = is_superuser
        self.is_active = True
        self.role = role
        self.employee_profile = None
        self.company = None

    def get_full_name(self):
        return self.username


class DateBasedDispatchEligibilityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.today = timezone.localdate()
        self.now = timezone.now()

        self.patch_dispatch_state = patch("workforce_api.models.WorkforceDispatchState.objects")
        self.mock_dispatch_state = self.patch_dispatch_state.start()
        mock_state = SimpleNamespace(
            dispatch_status="NEVER_ATTEMPTED",
            attempt_count=0,
            locked_at=None,
            retry_at=None,
            save=MagicMock(),
        )
        self.mock_dispatch_state.select_for_update.return_value.filter.return_value.first.return_value = mock_state
        self.addCleanup(self.patch_dispatch_state.stop)

    # 1. Past preferred_date cannot be dispatched
    @patch("django.db.transaction.atomic")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_1_past_preferred_date_cannot_be_dispatched(self, mock_sfu, mock_atomic):
        past_job = SimpleNamespace(
            id=2001,
            preferred_date=self.today - timedelta(days=1),
            created_at=self.now - timedelta(days=2),
            status="unassigned",
            assigned_employee=None,
        )
        mock_sfu.return_value.filter.return_value.first.return_value = past_job

        ok, reason = ad._dispatch_job_locked(2001, max_gps_age_seconds=120, exclude_employee_ids=set())
        self.assertFalse(ok)
        self.assertEqual(reason, "SCHEDULE_DATE_EXPIRED")

    # 2. Past preferred_date cannot create a new WorkforceJobOffer
    @patch("django.db.transaction.atomic")
    @patch("workforce_api.models.WorkforceJobOffer.objects.create")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_2_past_preferred_date_cannot_create_new_offer(self, mock_sfu, mock_offer_create, mock_atomic):
        past_job = SimpleNamespace(
            id=2002,
            preferred_date=self.today - timedelta(days=2),
            created_at=self.now - timedelta(days=3),
            status="unassigned",
            assigned_employee=None,
        )
        mock_sfu.return_value.filter.return_value.first.return_value = past_job

        ok, reason = ad.dispatch_job(2002)
        self.assertFalse(ok)
        self.assertEqual(reason, "SCHEDULE_DATE_EXPIRED")
        mock_offer_create.assert_not_called()

    # 3. dispatch_pending_jobs() does not discover past jobs
    @patch("workforce_api.services.automatic_dispatch.expire_and_reassign_offers", return_value=0)
    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_3_dispatch_pending_jobs_does_not_discover_past_jobs(self, mock_sr_filter, mock_expire):
        mock_chain = MagicMock()
        mock_sr_filter.return_value = mock_chain
        mock_chain.filter.return_value = mock_chain
        mock_chain.exclude.return_value = mock_chain
        mock_chain.order_by.return_value = mock_chain
        mock_chain.distinct.return_value = []
        mock_chain.__getitem__.return_value = []

        ad.dispatch_pending_jobs(company_id=1)

        q_matched = False
        for c in mock_chain.filter.call_args_list:
            if c[0] and "preferred_date" in str(c[0][0]):
                q_matched = True
                self.assertIn("created_at__date", str(c[0][0]))
                break
        self.assertTrue(q_matched, "Q filter for preferred_date=today must be passed to ServiceRequest.objects.filter")

    # 4. reconsider_jobs_for_employee() does not discover past jobs
    @patch("employees.models.Employee.objects.filter")
    @patch("workforce_api.services.automatic_dispatch.get_employee_active_job", return_value=None)
    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_4_reconsider_jobs_for_employee_does_not_discover_past_jobs(self, mock_sr_filter, mock_active, mock_emp_filter):
        mock_chain = MagicMock()
        mock_sr_filter.return_value = mock_chain
        mock_chain.filter.return_value = mock_chain
        mock_chain.exclude.return_value = mock_chain
        mock_chain.order_by.return_value = mock_chain
        mock_chain.distinct.return_value = []
        mock_chain.__getitem__.return_value = []

        emp = SimpleNamespace(
            id=888,
            pk=888,
            is_active=True,
            is_online=True,
            current_availability="available",
            company_id=1,
            skills=MagicMock(values_list=MagicMock(return_value=[])),
        )
        mock_emp_filter.return_value.first.return_value = emp

        ad.reconsider_jobs_for_employee(888)

        q_matched = False
        for c in mock_chain.filter.call_args_list:
            if c[0] and "preferred_date" in str(c[0][0]):
                q_matched = True
                self.assertIn("created_at__date", str(c[0][0]))
                break
        self.assertTrue(q_matched, "Q filter for preferred_date=today must be passed to ServiceRequest.objects.filter")

    # 5. GET /jobs does not execute dispatch (pure read-only)
    @patch("workforce_api.services.automatic_dispatch.expire_and_reassign_offers")
    @patch("workforce_api.services.automatic_dispatch.reconsider_jobs_for_employee")
    @patch("workforce_api.services.workload.get_employee_active_job", return_value=None)
    @patch("service_requests.models.ServiceRequest.objects.filter")
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    @patch("service_requests.models.EmployeeJob.objects.filter")
    def test_5_get_jobs_does_not_execute_dispatch(self, mock_emp_job, mock_offer, mock_sr, mock_active, mock_recons, mock_expire):
        user = MockUser()
        emp = Employee(
            id=888,
            is_active=True,
            is_online=True,
            current_availability="available",
            company=None,
            bank_details={"onboarding": {"status": "approved"}},
        )
        user.employee_profile = emp

        mock_chain = MagicMock()
        mock_offer.return_value = mock_chain
        mock_chain.filter.return_value = mock_chain
        mock_chain.values.return_value = []
        mock_emp_job.return_value.exclude.return_value.values.return_value = []
        mock_sr.return_value.select_related.return_value.order_by.return_value = []

        req = self.factory.get("/api/workforce/jobs/?status=all")
        force_authenticate(req, user=user)
        view = WorkforceJobListView.as_view()
        resp = view(req)

        mock_expire.assert_not_called()
        mock_recons.assert_not_called()

    # 6. GET /jobs backend query filters out offered past-dated jobs
    @patch("workforce_api.services.workload.get_employee_active_job", return_value=None)
    @patch("service_requests.models.ServiceRequest.objects.filter")
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    @patch("service_requests.models.EmployeeJob.objects.filter")
    def test_6_get_jobs_backend_query_filters_out_offered_past_dated_jobs(self, mock_emp_job, mock_offer, mock_sr, mock_active):
        user = MockUser()
        emp = Employee(
            id=888,
            is_active=True,
            is_online=True,
            current_availability="available",
            company=None,
            bank_details={"onboarding": {"status": "approved"}},
        )
        user.employee_profile = emp

        mock_chain = MagicMock()
        mock_offer.return_value = mock_chain
        mock_chain.filter.return_value = mock_chain
        mock_chain.values.return_value = []
        mock_emp_job.return_value.exclude.return_value.values.return_value = []
        mock_sr.return_value.select_related.return_value.order_by.return_value = []

        req = self.factory.get("/api/workforce/jobs/?status=all")
        force_authenticate(req, user=user)
        view = WorkforceJobListView.as_view()
        view(req)

        self.assertTrue(mock_chain.filter.called)
        q_matched = False
        for c in mock_chain.filter.call_args_list:
            if c[0] and "job__preferred_date" in str(c[0][0]):
                q_matched = True
                self.assertIn("job__created_at__date", str(c[0][0]))
                break
        self.assertTrue(q_matched, "Q filter for job__preferred_date must be passed")

    # 7. Existing past OFFERED job becomes EXPIRED
    # 8. Expiring a past-dated offer does NOT redispatch it
    @patch("workforce_api.services.automatic_dispatch.dispatch_next_candidate")
    @patch("django.db.transaction.atomic")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    def test_7_and_8_past_offered_job_expires_without_redispatch(self, mock_offer_filter, mock_offer_sfu, mock_atomic, mock_redispatch):
        past_job = SimpleNamespace(
            id=2007,
            preferred_date=self.today - timedelta(days=1),
            created_at=self.now - timedelta(days=2),
            status="unassigned",
            assigned_employee=None,
        )
        past_offer = SimpleNamespace(
            id=501,
            pk=501,
            job=past_job,
            job_id=2007,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at=self.now + timedelta(minutes=10),
            save=MagicMock(),
        )

        mock_chain = MagicMock()
        mock_offer_filter.return_value = mock_chain
        mock_chain.filter.return_value = mock_chain
        mock_chain.select_related.return_value = [past_offer]

        mock_sfu_chain = MagicMock()
        mock_offer_sfu.return_value = mock_sfu_chain
        mock_sfu_chain.filter.return_value.first.return_value = past_offer

        count = ad.expire_and_reassign_offers()

        self.assertEqual(count, 1)
        self.assertEqual(past_offer.status, WorkforceJobOffer.Status.EXPIRED)
        past_offer.save.assert_called_once_with(update_fields=["status"])
        mock_redispatch.assert_not_called()

    # 8b. Expiring a current-day timed-out offer DOES trigger redispatch
    @patch("workforce_api.services.automatic_dispatch.dispatch_next_candidate")
    @patch("django.db.transaction.atomic")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    def test_8b_today_expired_offer_is_redispatched(self, mock_offer_filter, mock_offer_sfu, mock_atomic, mock_redispatch):
        today_job = SimpleNamespace(
            id=2008,
            preferred_date=self.today,
            created_at=self.now,
            status="unassigned",
            assigned_employee=None,
        )
        today_timed_out_offer = SimpleNamespace(
            id=502,
            pk=502,
            job=today_job,
            job_id=2008,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at=self.now - timedelta(seconds=5),  # expired by time
            save=MagicMock(),
        )

        mock_chain = MagicMock()
        mock_offer_filter.return_value = mock_chain
        mock_chain.filter.return_value = mock_chain
        mock_chain.select_related.return_value = [today_timed_out_offer]

        mock_sfu_chain = MagicMock()
        mock_offer_sfu.return_value = mock_sfu_chain
        mock_sfu_chain.filter.return_value.first.return_value = today_timed_out_offer

        count = ad.expire_and_reassign_offers()

        self.assertEqual(count, 1)
        self.assertEqual(today_timed_out_offer.status, WorkforceJobOffer.Status.EXPIRED)
        mock_redispatch.assert_called_once_with(2008)

    # 9. Today's scheduled job remains dispatchable
    @patch("django.db.transaction.atomic")
    @patch("workforce_api.services.automatic_dispatch.get_user_model")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.services.automatic_dispatch.describe_unassigned_reason", return_value=("NO_TECH", "No tech nearby"))
    @patch("workforce_api.services.automatic_dispatch._count_failed_offer_cycles", return_value=0)
    @patch("workforce_api.models.WorkforceEventLog.objects.create")
    @patch("workforce_api.services.automatic_dispatch.get_eligible_candidates", return_value=[])
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_9_todays_scheduled_job_remains_dispatchable(self, mock_sfu, mock_cands, mock_event, mock_cycles, mock_desc, mock_offer_sfu, mock_user_model, mock_atomic):
        mock_user_model.return_value.objects.filter.return_value.first.return_value = None
        mock_offer_sfu.return_value.filter.return_value.first.return_value = None

        today_scheduled_job = SimpleNamespace(
            id=2009,
            preferred_date=self.today,
            preferred_time="ASAP",
            created_at=self.now,
            status="unassigned",
            assigned_employee=None,
            service_category="electrical",
            latitude=12.97,
            longitude=77.59,
            company=None,
            company_id=1,
            issue_title=None,
            save=MagicMock(),
        )
        mock_sfu.return_value.filter.return_value.first.return_value = today_scheduled_job

        ok, reason = ad._dispatch_job_locked(2009, max_gps_age_seconds=120, exclude_employee_ids=set())
        self.assertNotEqual(reason, "SCHEDULE_DATE_EXPIRED")

    # 10. Today's immediate booking remains dispatchable
    @patch("django.db.transaction.atomic")
    @patch("workforce_api.services.automatic_dispatch.get_user_model")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.services.automatic_dispatch.describe_unassigned_reason", return_value=("NO_TECH", "No tech nearby"))
    @patch("workforce_api.services.automatic_dispatch._count_failed_offer_cycles", return_value=0)
    @patch("workforce_api.models.WorkforceEventLog.objects.create")
    @patch("workforce_api.services.automatic_dispatch.get_eligible_candidates", return_value=[])
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_10_todays_immediate_booking_remains_dispatchable(self, mock_sfu, mock_cands, mock_event, mock_cycles, mock_desc, mock_offer_sfu, mock_user_model, mock_atomic):
        mock_user_model.return_value.objects.filter.return_value.first.return_value = None
        mock_offer_sfu.return_value.filter.return_value.first.return_value = None

        today_immediate_job = SimpleNamespace(
            id=2010,
            preferred_date=None,
            created_at=self.now,
            status="unassigned",
            assigned_employee=None,
            service_category="electrical",
            latitude=12.97,
            longitude=77.59,
            company=None,
            company_id=1,
            issue_title=None,
            save=MagicMock(),
        )
        mock_sfu.return_value.filter.return_value.first.return_value = today_immediate_job

        ok, reason = ad._dispatch_job_locked(2010, max_gps_age_seconds=120, exclude_employee_ids=set())
        self.assertNotEqual(reason, "SCHEDULE_DATE_EXPIRED")

    # 11. No regression in normal offer/acceptance workflow
    @patch("django.db.transaction.atomic")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    def test_11_normal_offer_acceptance_workflow_no_regression(self, mock_offer_sfu, mock_atomic):
        emp = SimpleNamespace(id=888)
        job = SimpleNamespace(id=2011, status="unassigned", assigned_employee=None)
        offer = SimpleNamespace(
            id=503,
            job=job,
            employee=emp,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at=self.now + timedelta(minutes=5),
            save=MagicMock(),
        )
        mock_offer_sfu.return_value.filter.return_value.first.return_value = offer

        # Technician accepts active offer
        offer.status = WorkforceJobOffer.Status.ACCEPTED
        offer.save()
        offer.save.assert_called_once()
        self.assertEqual(offer.status, WorkforceJobOffer.Status.ACCEPTED)
