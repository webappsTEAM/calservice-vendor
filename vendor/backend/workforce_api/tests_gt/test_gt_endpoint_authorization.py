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
            self.assertIn("assigned_employee != emp", _class_body(name), name)

    def test_every_trip_endpoint_checks_tenancy(self):
        for name in DRIVER_TRIP_VIEWS:
            body = _class_body(name)
            self.assertIn(
                "is_employee_authorized_for_job", body,
                f"{name} lets an assignment stand in for tenancy",
            )
            self.assertIn("CROSS_TENANT_FORBIDDEN", body, name)

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
