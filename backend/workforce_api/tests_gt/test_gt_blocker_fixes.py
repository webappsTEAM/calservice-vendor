"""
Tests for the three Vendor GT blocker fixes:
1. Critical Security: WorkforceVerificationSuiteView locked to IsAdminUser and disabled in production.
2. Multi-Stop Completion Gate: ServiceRequest.is_ready_to_complete() rejects incomplete TripStops.
3. Scheduled GT Dispatch: get_scheduled_dispatch_window() holds future bookings outside lead window.
"""
import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from workforce_api.views import WorkforceVerificationSuiteView
from workforce_api.services import automatic_dispatch as ad
from service_requests.models import ServiceRequest


class MockUser:
    def __init__(self, username="user", pk=1, is_authenticated=True, is_staff=False, is_superuser=False, role="user"):
        self.username = username
        self.pk = pk
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff
        self.is_superuser = is_superuser
        self.role = role


# ─── 1. Critical Security Regression Tests ────────────────────────────────────

class WorkforceVerificationSuiteSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WorkforceVerificationSuiteView.as_view()

    def test_unauthenticated_request_is_rejected(self):
        req = self.factory.get("/api/workforce/test-verification-suite/")
        resp = self.view(req)
        self.assertIn(resp.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_normal_employee_is_rejected(self):
        req = self.factory.get("/api/workforce/test-verification-suite/")
        user = MockUser(username="technician_bob", pk=101, is_authenticated=True, is_staff=False, role="employee")
        force_authenticate(req, user=user)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_normal_vendor_manager_is_rejected(self):
        req = self.factory.get("/api/workforce/test-verification-suite/")
        user = MockUser(username="vendor_mgr", pk=102, is_authenticated=True, is_staff=False, role="manager")
        force_authenticate(req, user=user)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(DEBUG=False)
    def test_production_non_superuser_admin_is_blocked_with_specific_code(self):
        req = self.factory.get("/api/workforce/test-verification-suite/")
        user = MockUser(username="staff_admin", pk=1, is_authenticated=True, is_staff=True, is_superuser=False)
        force_authenticate(req, user=user)
        resp = self.view(req)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(resp.data.get("code"), "DISABLED_IN_PRODUCTION")

    @override_settings(DEBUG=True)
    def test_authorized_staff_admin_in_debug_allowed(self):
        req = self.factory.get("/api/workforce/test-verification-suite/?suite=nonexistent")
        user = MockUser(username="staff_admin", pk=1, is_authenticated=True, is_staff=True, is_superuser=False)
        force_authenticate(req, user=user)
        with patch("run_master_customer_marketplace_handover_verification.run_master_handover_audit", create=True) as mock_audit:
            mock_audit.return_value = {"passed": 1, "failed": 0}
            resp = self.view(req)
            self.assertNotEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
            self.assertNotEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


# ─── 2. Multi-Stop Completion Gate Tests ──────────────────────────────────────

class MultiStopCompletionGateTests(SimpleTestCase):
    def _create_mock_job(self):
        job = ServiceRequest()
        job.id = 999
        job.cart_data = []
        job.payment_status = "PAID"
        job._state.fields_cache["post_service_proof"] = SimpleNamespace(is_submitted=True)
        job._state.fields_cache["payment_record"] = SimpleNamespace(payment_status="PAID", payment_method="ONLINE")
        return job

    def _mock_queryset(self, items):
        mock_qs = MagicMock()
        mock_qs.exists.return_value = len(items) > 0
        mock_qs.__iter__.return_value = iter(items)
        return mock_qs

    @patch("service_requests.models.TripStop.objects.filter")
    @patch("workforce_api.models.WorkforceWorkExtension.objects.filter")
    def test_booking_without_trip_stops_allowed_to_complete(self, mock_ext, mock_stops):
        mock_ext.return_value = []
        mock_stops.return_value = self._mock_queryset([])

        job = self._create_mock_job()
        is_ready, reason, deps = job.is_ready_to_complete()
        self.assertTrue(is_ready, f"Failed: {reason}")
        self.assertEqual(len(deps), 0)

    @patch("service_requests.models.TripStop.objects.filter")
    @patch("workforce_api.models.WorkforceWorkExtension.objects.filter")
    def test_non_gt_booking_with_empty_trip_stops_allowed(self, mock_ext, mock_stops):
        mock_ext.return_value = []
        mock_stops.return_value = self._mock_queryset([])

        job = self._create_mock_job()
        is_ready, reason, deps = job.is_ready_to_complete()
        self.assertTrue(is_ready, f"Failed: {reason}")

    @patch("service_requests.models.TripStop.objects.filter")
    @patch("workforce_api.models.WorkforceWorkExtension.objects.filter")
    def test_multi_stop_all_completed_allowed(self, mock_ext, mock_stops):
        mock_ext.return_value = []

        now = timezone.now()
        stop1 = SimpleNamespace(sequence=1, stop_type="PICKUP", completed_at=now)
        stop2 = SimpleNamespace(sequence=2, stop_type="WAYPOINT", completed_at=now)
        stop3 = SimpleNamespace(sequence=3, stop_type="DROP", completed_at=now)
        mock_stops.return_value = self._mock_queryset([stop1, stop2, stop3])

        job = self._create_mock_job()
        is_ready, reason, deps = job.is_ready_to_complete()
        self.assertTrue(is_ready, f"Failed: {reason}")
        self.assertEqual(len(deps), 0)

    @patch("service_requests.models.TripStop.objects.filter")
    @patch("workforce_api.models.WorkforceWorkExtension.objects.filter")
    def test_multi_stop_one_waypoint_incomplete_rejected(self, mock_ext, mock_stops):
        mock_ext.return_value = []

        now = timezone.now()
        stop1 = SimpleNamespace(sequence=1, stop_type="PICKUP", completed_at=now)
        stop2 = SimpleNamespace(sequence=2, stop_type="WAYPOINT", completed_at=None)
        stop3 = SimpleNamespace(sequence=3, stop_type="DROP", completed_at=now)
        mock_stops.return_value = self._mock_queryset([stop1, stop2, stop3])

        job = self._create_mock_job()
        is_ready, reason, deps = job.is_ready_to_complete()
        self.assertFalse(is_ready)
        self.assertTrue(any("Stop #2 (WAYPOINT)" in d for d in deps))
        self.assertIn("Stop #2 (WAYPOINT)", reason)

    @patch("service_requests.models.TripStop.objects.filter")
    @patch("workforce_api.models.WorkforceWorkExtension.objects.filter")
    def test_multi_stop_multiple_incomplete_stops_rejected(self, mock_ext, mock_stops):
        mock_ext.return_value = []

        now = timezone.now()
        stop1 = SimpleNamespace(sequence=1, stop_type="PICKUP", completed_at=now)
        stop2 = SimpleNamespace(sequence=2, stop_type="WAYPOINT", completed_at=None)
        stop3 = SimpleNamespace(sequence=3, stop_type="DROP", completed_at=None)
        mock_stops.return_value = self._mock_queryset([stop1, stop2, stop3])

        job = self._create_mock_job()
        is_ready, reason, deps = job.is_ready_to_complete()
        self.assertFalse(is_ready)
        self.assertTrue(any("Stop #2" in d and "Stop #3" in d for d in deps))


# ─── 3. Scheduled GT Dispatch Safety Gate Tests ───────────────────────────────

class ScheduledDispatchSafetyGateTests(SimpleTestCase):
    def test_immediate_job_with_no_preferred_date_dispatches_immediately(self):
        job = SimpleNamespace(
            service_category="goods_transport_truck",
            preferred_date=None,
            preferred_time=None,
        )
        is_future, sched_dt, win_open = ad.get_scheduled_dispatch_window(job)
        self.assertFalse(is_future)
        self.assertIsNone(sched_dt)
        self.assertIsNone(win_open)

    def test_immediate_job_today_with_no_slot_dispatches_immediately(self):
        now = timezone.localtime()
        job = SimpleNamespace(
            service_category="goods_transport_truck",
            preferred_date=now.date(),
            preferred_time="",
        )
        is_future, sched_dt, win_open = ad.get_scheduled_dispatch_window(job, now=now)
        self.assertFalse(is_future)

    def test_immediate_job_today_with_asap_dispatches_immediately(self):
        now = timezone.localtime()
        job = SimpleNamespace(
            service_category="goods_transport_two_wheeler",
            preferred_date=now.date(),
            preferred_time="ASAP",
        )
        is_future, sched_dt, win_open = ad.get_scheduled_dispatch_window(job, now=now)
        self.assertFalse(is_future)

    def test_same_day_job_within_lead_window_dispatches_immediately(self):
        tz = timezone.get_current_timezone()
        ref_now = timezone.make_aware(datetime.datetime(2026, 9, 8, 14, 0), tz)
        slot_str = "14:20"  # 20 minutes ahead (< 45 min lead time)

        job = SimpleNamespace(
            service_category="goods_transport_truck",
            preferred_date=ref_now.date(),
            preferred_time=slot_str,
        )
        is_future, sched_dt, win_open = ad.get_scheduled_dispatch_window(job, now=ref_now)
        self.assertFalse(is_future, "Job within 45 min lead window must dispatch immediately")

    def test_same_day_job_outside_lead_window_is_held(self):
        tz = timezone.get_current_timezone()
        ref_now = timezone.make_aware(datetime.datetime(2026, 9, 8, 10, 0), tz)
        slot_str = "14:00"

        job = SimpleNamespace(
            service_category="goods_transport_truck",
            preferred_date=ref_now.date(),
            preferred_time=slot_str,
        )
        is_future, sched_dt, win_open = ad.get_scheduled_dispatch_window(job, now=ref_now)
        self.assertTrue(is_future, "Job 4 hours away must be held from immediate dispatch")
        self.assertEqual(win_open, timezone.make_aware(datetime.datetime(2026, 9, 8, 13, 15), tz))

    def test_future_day_job_is_held(self):
        tz = timezone.get_current_timezone()
        ref_now = timezone.make_aware(datetime.datetime(2026, 9, 8, 10, 0), tz)
        tomorrow = ref_now.date() + datetime.timedelta(days=1)

        job = SimpleNamespace(
            service_category="goods_transport_truck",
            preferred_date=tomorrow,
            preferred_time="10:00 AM",
        )
        is_future, sched_dt, win_open = ad.get_scheduled_dispatch_window(job, now=ref_now)
        self.assertTrue(is_future, "Job scheduled for tomorrow must be held")

    def test_packers_movers_uses_120_minute_lead_window(self):
        tz = timezone.get_current_timezone()
        ref_now = timezone.make_aware(datetime.datetime(2026, 9, 8, 10, 0), tz)

        job_held = SimpleNamespace(
            service_category="packers_movers",
            preferred_date=ref_now.date(),
            preferred_time="13:00",
        )
        is_future_a, _, win_open_a = ad.get_scheduled_dispatch_window(job_held, now=ref_now)
        self.assertTrue(is_future_a)
        self.assertEqual(win_open_a, timezone.make_aware(datetime.datetime(2026, 9, 8, 11, 0), tz))

        job_active = SimpleNamespace(
            service_category="packers_movers",
            preferred_date=ref_now.date(),
            preferred_time="11:30",
        )
        is_future_b, _, _ = ad.get_scheduled_dispatch_window(job_active, now=ref_now)
        self.assertFalse(is_future_b)

    def test_slot_parser_handles_diverse_formats(self):
        self.assertEqual(ad.parse_preferred_slot_time("10:00"), datetime.time(10, 0))
        self.assertEqual(ad.parse_preferred_slot_time("10:00 - 12:00"), datetime.time(10, 0))
        self.assertEqual(ad.parse_preferred_slot_time("10:00 AM"), datetime.time(10, 0))
        self.assertEqual(ad.parse_preferred_slot_time("2:30 PM"), datetime.time(14, 30))
        self.assertEqual(ad.parse_preferred_slot_time("02:30 PM - 04:30 PM"), datetime.time(14, 30))
        self.assertIsNone(ad.parse_preferred_slot_time("ASAP"))
        self.assertIsNone(ad.parse_preferred_slot_time(""))
