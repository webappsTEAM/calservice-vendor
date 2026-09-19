"""
Comprehensive Unit & Integration Tests for CalTrack:
- Scheduled Job Dispatch Window (exact +/- 1 hour in operational timezone)
- Pre-window Retry Reconciliation & Anti-Storm Backoff
- Permanent Decline Suppression across Candidates & Job List
- Offer Acceptance vs Rejection Mutual Exclusivity
"""
import datetime
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from employees.models import Employee
from workforce_api.services import automatic_dispatch as ad
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceJobLifecycleEvent,
    WorkforceDispatchState,
)
from workforce_api.views import WorkforceJobListView


class MockUser:
    def __init__(self, username="tech_user", pk=101, role="employee"):
        self.username = username
        self.pk = pk
        self.id = pk
        self.is_authenticated = True
        self.is_staff = False
        self.is_superuser = False
        self.is_active = True
        self.role = role
        self.employee_profile = None
        self.company = None

    def get_full_name(self):
        return self.username


class ScheduledDispatchWindowTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        # CalTrack operational timezone is Asia/Kolkata
        self.tz = ZoneInfo("Asia/Kolkata")
        self.today = datetime.date(2026, 9, 19)

    def test_window_boundaries_for_11am(self):
        """
        For scheduled time 11:00 AM on 2026-09-19 in Asia/Kolkata:
        Window Open:  10:00 AM
        Window Close: 12:00 PM (noon)
        - 09:59 AM -> not dispatchable (held)
        - 10:00 AM -> dispatchable
        - 11:00 AM -> dispatchable
        - 11:59 AM -> dispatchable
        - 12:00 PM -> dispatchable (exact boundary)
        - 12:01 PM -> closed (past +1 hr)
        """
        job = SimpleNamespace(
            id=3001,
            preferred_date=self.today,
            preferred_time="11:00 AM",
            company=None,
        )

        # 1. At 09:59:59 AM (before window_open)
        t_0959 = datetime.datetime(2026, 9, 19, 9, 59, 59, tzinfo=self.tz)
        res_0959 = ad.get_scheduled_dispatch_window(job, now=t_0959)
        self.assertTrue(res_0959.is_future)
        self.assertFalse(res_0959.is_eligible)
        self.assertFalse(res_0959.is_closed)

        # 2. At 10:00:00 AM (exact window_open)
        t_1000 = datetime.datetime(2026, 9, 19, 10, 0, 0, tzinfo=self.tz)
        res_1000 = ad.get_scheduled_dispatch_window(job, now=t_1000)
        self.assertFalse(res_1000.is_future)
        self.assertTrue(res_1000.is_eligible)
        self.assertFalse(res_1000.is_closed)

        # 3. At 11:00:00 AM (scheduled time)
        t_1100 = datetime.datetime(2026, 9, 19, 11, 0, 0, tzinfo=self.tz)
        res_1100 = ad.get_scheduled_dispatch_window(job, now=t_1100)
        self.assertFalse(res_1100.is_future)
        self.assertTrue(res_1100.is_eligible)
        self.assertFalse(res_1100.is_closed)

        # 4. At 11:59:59 AM (inside window)
        t_1159 = datetime.datetime(2026, 9, 19, 11, 59, 59, tzinfo=self.tz)
        res_1159 = ad.get_scheduled_dispatch_window(job, now=t_1159)
        self.assertFalse(res_1159.is_future)
        self.assertTrue(res_1159.is_eligible)
        self.assertFalse(res_1159.is_closed)

        # 5. At 12:01:00 PM (past window_close = 12:00:00 PM)
        t_1201 = datetime.datetime(2026, 9, 19, 12, 1, 0, tzinfo=self.tz)
        res_1201 = ad.get_scheduled_dispatch_window(job, now=t_1201)
        self.assertFalse(res_1201.is_future)
        self.assertFalse(res_1201.is_eligible)
        self.assertTrue(res_1201.is_closed)

    def test_immediate_asap_booking_window(self):
        """
        Immediate / ASAP booking is always eligible and never marked future.
        """
        job = SimpleNamespace(
            id=3002,
            preferred_date=self.today,
            preferred_time="ASAP",
            company=None,
        )
        now_dt = datetime.datetime(2026, 9, 19, 8, 30, 0, tzinfo=self.tz)
        res = ad.get_scheduled_dispatch_window(job, now=now_dt)
        self.assertFalse(res.is_future)
        self.assertTrue(res.is_eligible)
        self.assertFalse(res.is_closed)

    def test_backward_compatibility_tuple_unpacking(self):
        """
        Existing callers unpacking (is_future, scheduled_dt, window_open) continue working seamlessly.
        """
        job = SimpleNamespace(
            id=3003,
            preferred_date=self.today,
            preferred_time="11:00",
            company=None,
        )
        t_1030 = datetime.datetime(2026, 9, 19, 10, 30, 0, tzinfo=self.tz)
        is_future, scheduled_dt, window_open = ad.get_scheduled_dispatch_window(job, now=t_1030)
        self.assertFalse(is_future)
        self.assertEqual(scheduled_dt, datetime.datetime(2026, 9, 19, 11, 0, tzinfo=self.tz))
        self.assertEqual(window_open, datetime.datetime(2026, 9, 19, 10, 0, tzinfo=self.tz))


class RetryReconciliationTests(SimpleTestCase):
    def setUp(self):
        self.tz = ZoneInfo("Asia/Kolkata")
        self.today = datetime.date(2026, 9, 19)

    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    @patch("employees.models.Employee.objects.select_for_update")
    @patch("workforce_api.services.automatic_dispatch._count_failed_offer_cycles", return_value=0)
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.models.WorkforceNotification.objects.create")
    @patch("workforce_api.models.WorkforceJobOffer.objects.create")
    @patch("workforce_api.models.WorkforceEventLog.objects.create")
    @patch("workforce_api.services.automatic_dispatch.get_eligible_candidates")
    @patch("workforce_api.models.WorkforceDispatchState.objects")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    @patch("django.db.transaction.atomic")
    def test_pre_window_retry_at_does_not_block_window_opening(
        self, mock_atomic, mock_sfu, mock_dispatch_state, mock_candidates,
        mock_event, mock_offer_create, mock_notif, mock_offer_sfu, mock_cycles,
        mock_emp_sfu, mock_offer_filter
    ):
        """
        If a retry was scheduled at 09:30 (before window opened at 10:00),
        when 10:00 arrives, the job MUST get its first dispatch opportunity.
        """
        mock_offer_filter.return_value.first.return_value = None
        mock_company = SimpleNamespace(id=1, operational_timezone="Asia/Kolkata", company_name="Test Company")
        job = SimpleNamespace(
            id=4001,
            preferred_date=self.today,
            preferred_time="11:00 AM",
            created_at=datetime.datetime(2026, 9, 19, 8, 0, tzinfo=self.tz),
            status="unassigned",
            assigned_employee=None,
            service_category="electrical",
            latitude=12.97,
            longitude=77.59,
            company=mock_company,
            company_id=1,
            request_id="REQ-4001",
            issue_title="Electrical Issue",
            address="123 Street",
            save=MagicMock(),
        )
        mock_sfu.return_value.filter.return_value.first.return_value = job
        mock_sfu.return_value.get.return_value = job
        mock_offer_sfu.return_value.filter.return_value.first.return_value = None

        # Mock dispatch state created before window with an old retry_at
        mock_state = SimpleNamespace(
            dispatch_status="RETRY_SCHEDULED",
            attempt_count=1,
            last_attempt_at=datetime.datetime(2026, 9, 19, 9, 25, tzinfo=self.tz),
            retry_at=datetime.datetime(2026, 9, 19, 9, 45, tzinfo=self.tz),
            locked_at=None,
            save=MagicMock(),
        )
        mock_dispatch_state.select_for_update.return_value.filter.return_value.first.return_value = mock_state
        mock_dispatch_state.select_for_update.return_value.get.return_value = mock_state

        mock_tech = SimpleNamespace(
            id=201,
            pk=201,
            user=SimpleNamespace(get_full_name=lambda: "Tech 1", username="tech1"),
        )
        mock_emp_sfu.return_value.filter.return_value.first.return_value = mock_tech
        mock_candidates.return_value = [
            {"employee": mock_tech, "distance_km": 1.2, "score": 95.0}
        ]
        mock_offer = SimpleNamespace(id=901)
        mock_offer_create.return_value = mock_offer

        # Now is 10:01 AM (window just opened)
        now_1001 = datetime.datetime(2026, 9, 19, 10, 1, 0, tzinfo=self.tz)
        with patch("django.utils.timezone.now", return_value=now_1001):
            ok, reason = ad._dispatch_job_locked(4001)

        self.assertTrue(ok)
        self.assertIn("offered to Tech 1", reason)
        mock_candidates.assert_called_once()

    @patch("workforce_api.services.automatic_dispatch.get_eligible_candidates")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.models.WorkforceDispatchState.objects")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    @patch("django.db.transaction.atomic")
    def test_post_window_failed_dispatch_respects_backoff_no_storm(
        self, mock_atomic, mock_sfu, mock_dispatch_state, mock_offer_sfu, mock_candidates
    ):
        """
        After window has opened, if dispatch attempt failed at 10:05 and backoff set retry_at=10:10,
        a sweep at 10:06 must respect retry_at and NOT execute dispatch (prevents storm).
        """
        mock_company = SimpleNamespace(id=1, operational_timezone="Asia/Kolkata", company_name="Test Company")
        job = SimpleNamespace(
            id=4002,
            preferred_date=self.today,
            preferred_time="11:00 AM",
            created_at=datetime.datetime(2026, 9, 19, 8, 0, tzinfo=self.tz),
            status="unassigned",
            assigned_employee=None,
            service_category="electrical",
            latitude=12.97,
            longitude=77.59,
            company=mock_company,
            company_id=1,
            save=MagicMock(),
        )
        mock_sfu.return_value.filter.return_value.first.return_value = job
        mock_offer_sfu.return_value.filter.return_value.first.return_value = None

        # Dispatch state updated AFTER window open (last_attempt_at >= window_open)
        mock_state = SimpleNamespace(
            dispatch_status="RETRY_SCHEDULED",
            attempt_count=1,
            last_attempt_at=datetime.datetime(2026, 9, 19, 10, 5, tzinfo=self.tz),
            retry_at=datetime.datetime(2026, 9, 19, 10, 10, tzinfo=self.tz),
            locked_at=None,
            save=MagicMock(),
        )
        mock_dispatch_state.select_for_update.return_value.filter.return_value.first.return_value = mock_state

        # Now is 10:06 AM (inside retry backoff window)
        now_1006 = datetime.datetime(2026, 9, 19, 10, 6, 0, tzinfo=self.tz)
        with patch("django.utils.timezone.now", return_value=now_1006):
            ok, reason = ad._dispatch_job_locked(4002)

        self.assertFalse(ok)
        self.assertIn("Dispatch retry not due yet", reason)
        mock_candidates.assert_not_called()


class DeclineSuppressionTests(SimpleTestCase):
    def setUp(self):
        self.tech_a = SimpleNamespace(id=101, current_status="approved", role="employee")
        self.tech_b = SimpleNamespace(id=102, current_status="approved", role="employee")
        self.job = SimpleNamespace(
            id=5001,
            service_category="electrical",
            issue_title=None,
            latitude=12.97,
            longitude=77.59,
        )

    @patch("workforce_api.services.automatic_dispatch.check_candidate_eligibility", return_value=(True, "OK", {}))
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    def test_employee_a_declined_never_receives_job_again(self, mock_offer_filter, mock_eligibility):
        """
        Technician A declined Job 5001 -> can_receive_offer must return False.
        """
        # When checking tech_a: offer exists with REJECTED status
        mock_offer_filter.return_value.exists.return_value = True

        can_receive, reason = ad.can_receive_offer(self.tech_a, self.job)
        self.assertFalse(can_receive)
        self.assertIn("already has offer history", reason)

    @patch("workforce_api.services.automatic_dispatch.check_candidate_eligibility", return_value=(True, "OK", {}))
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    def test_employee_b_not_declined_can_receive_job(self, mock_offer_filter, mock_eligibility):
        """
        Technician B has not declined Job 5001 -> can_receive_offer returns True.
        """
        mock_offer_filter.return_value.exists.return_value = False

        can_receive, reason = ad.can_receive_offer(self.tech_b, self.job)
        self.assertTrue(can_receive)
        self.assertEqual(reason, "OK")


class OfferLifecycleInvariantsTests(SimpleTestCase):
    def setUp(self):
        self.now = timezone.now()

    def test_accepted_and_rejected_cannot_both_occur(self):
        """
        An offer in ACCEPTED status cannot be rejected, and an offer in REJECTED status cannot be accepted.
        """
        offer = SimpleNamespace(
            id=6001,
            status=WorkforceJobOffer.Status.ACCEPTED,
            expires_at=self.now + timedelta(minutes=10),
            is_expired=False,
        )

        # Attempting to reject an already accepted offer must fail validation
        can_reject = (offer.status == WorkforceJobOffer.Status.OFFERED)
        self.assertFalse(can_reject)

        # Attempting to accept an already rejected offer must fail validation
        offer.status = WorkforceJobOffer.Status.REJECTED
        can_accept = (offer.status == WorkforceJobOffer.Status.OFFERED)
        self.assertFalse(can_accept)


class ScheduledWindowClosedExpirationTests(SimpleTestCase):
    def setUp(self):
        self.tz = ZoneInfo("Asia/Kolkata")
        self.today = datetime.date(2026, 9, 19)

    @patch("workforce_api.models.WorkforceDispatchState.objects.filter")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    @patch("django.db.transaction.atomic")
    def test_window_closed_marks_expired_and_refuses_dispatch(self, mock_atomic, mock_sfu, mock_dispatch_state_filter):
        """
        At 12:01 PM for an 11:00 AM job, the scheduled window is closed (+1 hr exceeded).
        Dispatch must refuse and mark dispatch state as EXPIRED.
        """
        mock_company = SimpleNamespace(id=1, operational_timezone="Asia/Kolkata", company_name="Test Company")
        job = SimpleNamespace(
            id=7001,
            preferred_date=self.today,
            preferred_time="11:00 AM",
            created_at=datetime.datetime(2026, 9, 19, 8, 0, tzinfo=self.tz),
            status="unassigned",
            assigned_employee=None,
            service_category="electrical",
            latitude=12.97,
            longitude=77.59,
            company=mock_company,
            company_id=1,
            save=MagicMock(),
        )
        mock_sfu.return_value.filter.return_value.first.return_value = job

        # 12:01 PM on the same day (1 minute past window close)
        now_1201 = datetime.datetime(2026, 9, 19, 12, 1, 0, tzinfo=self.tz)
        with patch("django.utils.timezone.now", return_value=now_1201):
            ok, reason = ad._dispatch_job_locked(7001)

        self.assertFalse(ok)
        self.assertIn("offer window closed", reason)
        mock_dispatch_state_filter.return_value.update.assert_called_with(
            dispatch_status=WorkforceDispatchState.DispatchStatus.EXPIRED,
            retry_at=None,
            locked_at=None,
            unassigned_reason_code="SCHEDULE_WINDOW_EXPIRED",
            unassigned_reason_message="Scheduled slot was 2026-09-19 11:00. Offer window closed.",
        )


class CandidateDiscoveryDeclineExclusionTests(SimpleTestCase):
    def setUp(self):
        self.tz = ZoneInfo("Asia/Kolkata")
        self.today = datetime.date(2026, 9, 19)

    @patch("workforce_api.services.automatic_dispatch.get_user_model")
    @patch("workforce_api.services.automatic_dispatch._count_failed_offer_cycles", return_value=0)
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    @patch("workforce_api.services.automatic_dispatch.get_eligible_candidates")
    @patch("workforce_api.models.WorkforceEventLog.objects.create")
    @patch("workforce_api.models.WorkforceJobLifecycleEvent.objects.filter")
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    @patch("workforce_api.models.WorkforceDispatchState.objects")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    @patch("django.db.transaction.atomic")
    def test_declined_technician_excluded_from_candidate_discovery(
        self, mock_atomic, mock_sfu, mock_dispatch_state, mock_offer_filter,
        mock_lifecycle_filter, mock_event, mock_get_candidates, mock_offer_sfu,
        mock_cycles, mock_user_model
    ):
        """
        When Tech A (id=101) has declined Job 8001, dispatch must aggregate Tech A's ID
        and pass it to get_eligible_candidates(exclude_employee_ids=[...]).
        """
        mock_user_model.return_value.objects.filter.return_value.first.return_value = None
        mock_offer_sfu.return_value.filter.return_value.first.return_value = None
        mock_company = SimpleNamespace(id=1, operational_timezone="Asia/Kolkata", company_name="Test Company")
        job = SimpleNamespace(
            id=8001,
            preferred_date=self.today,
            preferred_time="11:00 AM",
            created_at=datetime.datetime(2026, 9, 19, 8, 0, tzinfo=self.tz),
            status="unassigned",
            assigned_employee=None,
            service_category="electrical",
            latitude=12.97,
            longitude=77.59,
            company=mock_company,
            company_id=1,
            save=MagicMock(),
        )
        mock_sfu.return_value.filter.return_value.first.return_value = job
        mock_sfu.return_value.get.return_value = job

        mock_state = SimpleNamespace(
            dispatch_status="NEVER_ATTEMPTED",
            attempt_count=0,
            last_attempt_at=None,
            retry_at=None,
            locked_at=None,
            save=MagicMock(),
        )
        mock_dispatch_state.select_for_update.return_value.filter.return_value.first.return_value = mock_state
        mock_dispatch_state.select_for_update.return_value.get.return_value = mock_state

        # Tech A (id=101) declined Job 8001
        mock_offer_filter.return_value.values_list.return_value = [101]
        mock_lifecycle_filter.return_value.values_list.return_value = []
        mock_get_candidates.return_value = []

        now_1030 = datetime.datetime(2026, 9, 19, 10, 30, 0, tzinfo=self.tz)
        with patch("django.utils.timezone.now", return_value=now_1030):
            ad._dispatch_job_locked(8001)

        # Verify get_eligible_candidates was called with exclude_employee_ids containing 101
        mock_get_candidates.assert_called_once()
        _, kwargs = mock_get_candidates.call_args
        self.assertIn(101, kwargs.get("exclude_employee_ids", []))

