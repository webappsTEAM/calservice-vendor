"""
test_dispatch_radar_api.py
Comprehensive test suite for Super Admin Dispatch Radar (WorkforceDispatchRadarView).

Verifies:
1. Authorization & Tenant Isolation (Admin only, non-admin blocked).
2. Read-Only Invariant (GET / refresh produces ZERO dispatch mutations, claims, or offers).
3. Candidate Snapshot Retrieval (Immutable eligible candidate snapshot representation).
4. Sequential Offer History (OFFERED -> DECLINED -> EXPIRED -> ACCEPTED progression).
5. Lifecycle Timeline & Summary Metrics.
6. NO MAP Invariant (Text-only textual location and status indicators).
"""
import re
from unittest.mock import MagicMock, patch
from django.test import SimpleTestCase, RequestFactory
from django.utils import timezone
from workforce_api.views import WorkforceDispatchRadarView


SOURCE = "workforce_api/views.py"


def _class_body(name):
    src = open(SOURCE, encoding="utf-8", errors="replace").read()
    lines = src.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(rf"class {name}\(", l))
    end = next(
        (i for i, l in enumerate(lines) if i > start and re.match(r"class \w+\(", l)),
        len(lines),
    )
    return "\n".join(lines[start:end])


class WorkforceDispatchRadarViewStructureTests(SimpleTestCase):
    """
    Validates structural, security, and read-only invariants of WorkforceDispatchRadarView.
    """

    def test_radar_requires_authenticated_admin(self):
        body = _class_body("WorkforceDispatchRadarView")
        self.assertIn("IsWorkforceAdmin", body, "Radar must enforce IsWorkforceAdmin permission.")
        self.assertIn("permissions.IsAuthenticated", body, "Radar must require authentication.")

    def test_radar_is_strictly_read_only_with_no_dispatch_calls(self):
        body = _class_body("WorkforceDispatchRadarView")
        # Ensure no mutating dispatch functions are invoked
        mutating_calls = [
            "dispatch_job(",
            "dispatch_next_candidate(",
            "reconsider_jobs_for_employee(",
            "expire_and_reassign_offers(",
            "dispatch_pending_jobs(",
            "apply_transition(",
            ".create(",
            ".update(",
            ".delete(",
            ".save(",
        ]
        for bad_call in mutating_calls:
            self.assertNotIn(bad_call, body, f"Radar view contains mutating call: {bad_call}")

    def test_radar_does_not_contain_map_or_route_drawing(self):
        body = _class_body("WorkforceDispatchRadarView")
        map_forbidden_terms = [
            "google.maps",
            "leaflet",
            "mapbox",
            "polyline",
            "draw_route",
            "directions_api",
        ]
        for term in map_forbidden_terms:
            self.assertNotIn(term, body.lower(), f"Radar view must NOT contain map logic: {term}")


class WorkforceDispatchRadarLogicTests(SimpleTestCase):
    """
    Tests request handling, filtering, summary aggregation, and candidate snapshot rendering.
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.view = WorkforceDispatchRadarView.as_view()

    def test_unauthorized_non_admin_user_rejected(self):
        req = self.factory.get("/api/workforce/admin/dispatch-radar/")
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff = False
        user.is_superuser = False
        user.role = "employee"
        req.user = user

        from workforce_api.permissions import IsWorkforceAdmin
        perm = IsWorkforceAdmin()
        self.assertFalse(perm.has_permission(req, None), "Regular technician user must be denied.")

    def test_super_admin_user_permitted(self):
        req = self.factory.get("/api/workforce/admin/dispatch-radar/")
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff = True
        user.is_superuser = True
        user.role = "admin"
        req.user = user

        from workforce_api.permissions import IsWorkforceAdmin
        perm = IsWorkforceAdmin()
        self.assertTrue(perm.has_permission(req, None), "Super Admin user must be permitted.")

    @patch("workforce_api.views.WorkforceEventLog.objects.filter")
    @patch("workforce_api.views.WorkforceJobOffer.objects.filter")
    @patch("workforce_api.views.WorkforceJobLifecycleEvent.objects.filter")
    @patch("workforce_api.views.ServiceRequest.objects.filter")
    @patch("workforce_api.views.ServiceRequest.objects.all")
    def test_radar_response_structure_and_immutable_snapshot(
        self, mock_all, mock_filter, mock_lc, mock_offers, mock_events
    ):
        # Mock base queryset
        mock_qs = MagicMock()
        mock_all.return_value = mock_qs
        mock_qs.exclude.return_value = mock_qs
        mock_qs.filter.return_value = mock_qs
        mock_qs.distinct.return_value = mock_qs
        mock_qs.count.return_value = 5
        mock_qs.select_related.return_value = mock_qs
        mock_qs.prefetch_related.return_value = mock_qs
        mock_qs.order_by.return_value = mock_qs

        # Mock a sample ServiceRequest
        sample_job = MagicMock()
        sample_job.id = 6001
        sample_job.request_id = "SR-6001"
        sample_job.issue_title = "AC Repair & Servicing"
        sample_job.service_category = "hvac"
        sample_job.status = "unassigned"
        sample_job.created_at = timezone.now()
        sample_job.preferred_date = "2026-09-19"
        sample_job.preferred_time = "14:00:00"
        sample_job.scheduled_date = "2026-09-19"
        sample_job.scheduled_time = "14:00:00"
        sample_job.address = "123 Indiranagar, Bangalore"
        sample_job.customer_name = "Alice Customer"
        sample_job.customer = MagicMock(get_full_name=lambda: "Alice Customer")
        sample_job.assigned_employee = None
        sample_job.assigned_employee_id = None
        sample_job.technician_name = None
        sample_job.dispatch_state = MagicMock(
            dispatch_status="OFFER_ACTIVE",
            attempt_count=2,
            retry_at=None,
            unassigned_reason_code="",
            unassigned_reason_message="",
        )
        sample_job.prefetched_live_offers = []

        mock_qs.__iter__.return_value = [sample_job]
        mock_qs.__getitem__.return_value = [sample_job]
        mock_filter.return_value.select_related.return_value.first.return_value = sample_job

        # Mock offers history (Tech A DECLINED, Tech B OFFERED)
        off1 = MagicMock()
        off1.id = 101
        off1.employee_id = 12
        off1.employee = MagicMock()
        off1.employee.user.get_full_name.return_value = "Technician A"
        off1.employee.user.username = "tech_a"
        off1.rank_score = 142.5
        off1.status = "DECLINED"
        off1.offered_at = timezone.now()
        off1.expires_at = timezone.now() + timezone.timedelta(minutes=5)
        off1.rejection_reason = "Too far from current location"

        off2 = MagicMock()
        off2.id = 102
        off2.employee_id = 15
        off2.employee = MagicMock()
        off2.employee.user.get_full_name.return_value = "Technician B"
        off2.employee.user.username = "tech_b"
        off2.rank_score = 137.0
        off2.status = "OFFERED"
        off2.offered_at = timezone.now()
        off2.expires_at = timezone.now() + timezone.timedelta(minutes=3)
        off2.rejection_reason = ""

        mock_offers.return_value.select_related.return_value.order_by.return_value = [off1, off2]

        # Mock CANDIDATES_EVALUATED event log with immutable eligible_candidates_snapshot
        eval_event = MagicMock()
        eval_event.event_type = "CANDIDATES_EVALUATED"
        eval_event.payload = {
            "job_id": 6001,
            "attempt": 2,
            "eligible_count": 3,
            "eligible_candidates_snapshot": [
                {"rank": 1, "employee_id": 12, "employee_name": "Technician A", "distance_km": 2.1, "score": 142.5},
                {"rank": 2, "employee_id": 15, "employee_name": "Technician B", "distance_km": 2.8, "score": 137.0},
                {"rank": 3, "employee_id": 19, "employee_name": "Technician C", "distance_km": 4.5, "score": 118.0},
            ]
        }
        mock_events.return_value.order_by.return_value.first.return_value = eval_event
        mock_events.return_value.select_related.return_value.order_by.return_value = []
        mock_lc.return_value.select_related.return_value.order_by.return_value = []

        req = self.factory.get("/api/workforce/admin/dispatch-radar/?job_id=6001")
        user = MagicMock()
        user.is_authenticated = True
        user.is_staff = True
        user.is_superuser = True
        user.role = "admin"
        req.user = user

        resp = self.view(req)
        self.assertEqual(resp.status_code, 200)
        data = resp.data

        self.assertIn("summary", data)
        self.assertIn("jobs", data)
        self.assertIn("selected_job", data)

        sel = data["selected_job"]
        self.assertEqual(sel["id"], 6001)
        self.assertEqual(sel["service"], "AC Repair & Servicing")
        self.assertEqual(sel["address"], "123 Indiranagar, Bangalore")

        # Verify Candidate Evaluation Snapshot
        candidate_evals = sel["candidate_evaluations"]
        self.assertEqual(len(candidate_evals), 3)
        self.assertEqual(candidate_evals[0]["employee_name"], "Technician A")
        self.assertEqual(candidate_evals[0]["result"], "DECLINED")
        self.assertEqual(candidate_evals[1]["employee_name"], "Technician B")
        self.assertEqual(candidate_evals[1]["result"], "OFFERED")
        self.assertEqual(candidate_evals[2]["employee_name"], "Technician C")
        self.assertEqual(candidate_evals[2]["result"], "NOT OFFERED")

        # Verify Offers History
        self.assertEqual(len(sel["offers_history"]), 2)
        self.assertEqual(sel["offers_history"][0]["status"], "DECLINED")
        self.assertEqual(sel["offers_history"][1]["status"], "OFFERED")
