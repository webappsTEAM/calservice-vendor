"""
Authorization on the three endpoints the driver app uses to advance a trip.

Being the assigned employee is not the same as belonging to the job's
tenant: an assignment can outlive a technician moving between companies,
and every one of these endpoints writes to a booking row SHARED with the
Customer app and fires a customer-facing event. WorkforceJobProofView
already verified both; the leg and stop endpoints checked only assignment.

Source-level, for the same reason as the estimation tests: ServiceRequest
here is an unmanaged mirror of a table another app owns, so there is no
local schema to build fixtures against.
"""
import re

from django.test import SimpleTestCase

SOURCE = "workforce_api/views.py"
DRIVER_TRIP_VIEWS = [
    "WorkforceJobLogisticsLegView",
    "WorkforceJobTripStopsView",
    "WorkforceJobProofView",
]


def _class_body(name):
    src = open(SOURCE, encoding="utf-8", errors="replace").read()
    lines = src.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(rf"class {name}\(", l))
    end = next(
        (i for i, l in enumerate(lines) if i > start and re.match(r"class \w+\(", l)),
        len(lines),
    )
    return "\n".join(lines[start:end])


class DriverTripEndpointAuthorizationTests(SimpleTestCase):
    def test_every_trip_endpoint_requires_an_approved_technician(self):
        for name in DRIVER_TRIP_VIEWS:
            self.assertIn("IsApprovedTechnician", _class_body(name), name)

    def test_every_trip_endpoint_checks_the_job_is_assigned_to_the_caller(self):
        for name in DRIVER_TRIP_VIEWS:
            self.assertIn("_authorize_job_actor", _class_body(name), name)

    def test_every_trip_endpoint_checks_tenancy(self):
        for name in DRIVER_TRIP_VIEWS:
            body = _class_body(name)
            self.assertIn(
                "_authorize_job_actor", body,
                f"{name} uses centralized actor and tenancy authorization",
            )

    def test_leg_and_stop_endpoints_refuse_non_logistics_jobs(self):
        for name in ("WorkforceJobLogisticsLegView", "WorkforceJobTripStopsView"):
            self.assertIn("LOGISTICS_SERVICE_CATEGORIES", _class_body(name), name)

    def test_leg_and_stop_endpoints_refuse_terminal_jobs(self):
        for name in ("WorkforceJobLogisticsLegView", "WorkforceJobTripStopsView"):
            body = _class_body(name)
            self.assertIn("_TERMINAL_STATUSES", body, name)
            for terminal in ("completed", "cancelled", "unable_to_complete"):
                self.assertIn(terminal, body, f"{name} / {terminal}")

    def test_proof_endpoint_gates_on_an_in_progress_job(self):
        # Its equivalent of a terminal guard: an allow-list rather than a
        # deny-list, which is the stricter of the two.
        body = _class_body("WorkforceJobProofView")
        self.assertIn('["in_progress", "proof_submitted"]', body)

    def test_the_tenant_rule_itself_is_what_these_endpoints_rely_on(self):
        from workforce_api.views import is_employee_authorized_for_job

        class E:
            def __init__(self, cid): self.company_id = cid

        class J:
            def __init__(self, cid): self.company_id = cid

        # A vendor technician may only touch their own company's jobs.
        self.assertTrue(is_employee_authorized_for_job(E(7), J(7)))
        self.assertFalse(is_employee_authorized_for_job(E(7), J(8)))
        self.assertFalse(is_employee_authorized_for_job(E(7), J(None)))
        # Solo/platform technicians handle platform jobs, not vendor ones.
        self.assertTrue(is_employee_authorized_for_job(E(None), J(None)))
        self.assertTrue(is_employee_authorized_for_job(E(1), J(1)))
        self.assertFalse(is_employee_authorized_for_job(E(1), J(9)))
        # Missing either side is never authorized.
        self.assertFalse(is_employee_authorized_for_job(None, J(1)))
        self.assertFalse(is_employee_authorized_for_job(E(1), None))

    def test_authorize_job_actor_rules(self):
        from unittest.mock import MagicMock, patch
        from workforce_api.views import _authorize_job_actor

        # 1. Unauthenticated
        req_unauth = MagicMock()
        req_unauth.user.is_authenticated = False
        is_auth, resp, emp, is_admin = _authorize_job_actor(req_unauth, MagicMock())
        self.assertFalse(is_auth)
        self.assertEqual(resp.status_code, 401)

        # 2. Admin when allow_admin=False
        req_admin = MagicMock()
        req_admin.user.is_authenticated = True
        req_admin.user.role = "COMPANY_ADMIN"
        with patch("workforce_api.views.is_admin_role", return_value=True):
            is_auth, resp, emp, is_admin = _authorize_job_actor(req_admin, MagicMock(), allow_admin=False)
            self.assertFalse(is_auth)
            self.assertEqual(resp.data.get("code"), "ADMIN_NOT_PERMITTED")

        # 3. Superuser admin
        req_super = MagicMock()
        req_super.user.is_authenticated = True
        req_super.user.is_superuser = True
        with patch("workforce_api.views.is_admin_role", return_value=True):
            is_auth, resp, emp, is_admin = _authorize_job_actor(req_super, MagicMock(), allow_admin=True)
            self.assertTrue(is_auth)
            self.assertIsNone(resp)
            self.assertTrue(is_admin)

        # 4. Vendor admin matching company
        req_vadmin = MagicMock()
        req_vadmin.user.is_authenticated = True
        req_vadmin.user.is_superuser = False
        company_mock = MagicMock(id=5)
        job_mock = MagicMock(company_id=5)
        with patch("workforce_api.views.is_admin_role", return_value=True), \
             patch("workforce_api.views.resolve_actor_company", return_value=company_mock):
            is_auth, resp, emp, is_admin = _authorize_job_actor(req_vadmin, job_mock, allow_admin=True)
            self.assertTrue(is_auth)
            self.assertIsNone(resp)
            self.assertTrue(is_admin)

        # 5. Vendor admin mismatched company (Cross-tenant)
        job_other = MagicMock(company_id=99)
        with patch("workforce_api.views.is_admin_role", return_value=True), \
             patch("workforce_api.views.resolve_actor_company", return_value=company_mock):
            is_auth, resp, emp, is_admin = _authorize_job_actor(req_vadmin, job_other, allow_admin=True)
            self.assertFalse(is_auth)
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.data.get("code"), "CROSS_TENANT_FORBIDDEN")

        # 6. Technician assigned and authorized
        req_tech = MagicMock()
        req_tech.user.is_authenticated = True
        req_tech.user.is_superuser = False
        emp_mock = MagicMock(id=42, company_id=5)
        req_tech.user.employee_profile = emp_mock
        job_assigned = MagicMock(company_id=5, assigned_employee_id=42, assigned_employee=emp_mock)
        with patch("workforce_api.views.is_admin_role", return_value=False):
            is_auth, resp, emp, is_admin = _authorize_job_actor(req_tech, job_assigned)
            self.assertTrue(is_auth)
            self.assertIsNone(resp)
            self.assertEqual(emp, emp_mock)
            self.assertFalse(is_admin)

        # 7. Technician unassigned
        job_unassigned = MagicMock(company_id=5, assigned_employee_id=999, assigned_employee=None)
        with patch("workforce_api.views.is_admin_role", return_value=False), \
             patch("service_requests.models.EmployeeJob.objects.filter") as ej_filter:
            ej_filter.return_value.exclude.return_value.exists.return_value = False
            is_auth, resp, emp, is_admin = _authorize_job_actor(
                req_tech, job_unassigned,
                not_assigned_msg="You are not assigned to this job.",
                not_assigned_code="UNAUTHORIZED_CANCELLATION"
            )
            self.assertFalse(is_auth)
            self.assertEqual(resp.status_code, 403)
            self.assertEqual(resp.data.get("code"), "UNAUTHORIZED_CANCELLATION")
            self.assertEqual(resp.data.get("error"), "You are not assigned to this job.")

    def test_stops_endpoint_uses_record_stop_progress_scalar_assignment(self):
        body = _class_body("WorkforceJobTripStopsView")
        self.assertIn("changed = record_stop_progress(", body)
        self.assertNotIn("stop, changed, error = record_stop_progress(", body)

    def test_logistics_leg_endpoint_returns_sequence(self):
        body = _class_body("WorkforceJobLogisticsLegView")
        self.assertIn("get_sequence_for_job", body)
        self.assertIn('"sequence": get_sequence_for_job(', body)

