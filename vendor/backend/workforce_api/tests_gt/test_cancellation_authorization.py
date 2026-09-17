"""
Tests for WorkforceJobCancelAssignmentView authorization and state guards.
Verifies that:
1. Cancellation strictly requires an approved technician.
2. An unassigned technician is rejected with HTTP 403 and UNAUTHORIZED_CANCELLATION.
3. 5-minute cancellation window is strictly enforced (CANCELLATION_WINDOW_EXPIRED).
4. Cancellation is permitted only from 'accepted' or 'on_the_way' states.
"""
import re
from django.test import SimpleTestCase

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


class JobCancellationAuthorizationTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.body = _class_body("WorkforceJobCancelAssignmentView")

    def test_cancellation_requires_approved_technician(self):
        self.assertIn("IsApprovedTechnician", self.body)

    def test_cancellation_verifies_caller_is_assigned_employee(self):
        self.assertIn("job.assigned_employee != emp and not has_emp_job", self.body)
        self.assertIn("UNAUTHORIZED_CANCELLATION", self.body)
        self.assertIn("Unauthorized: You are not assigned to this job.", self.body)

    def test_cancellation_rejects_unassigned_caller_with_403(self):
        self.assertIn("status.HTTP_403_FORBIDDEN", self.body)

    def test_cancellation_enforces_5_minute_deadline(self):
        self.assertIn("cancellation_deadline", self.body)
        self.assertIn("CANCELLATION_WINDOW_EXPIRED", self.body)
        self.assertIn("The 5-minute cancellation window for this job has expired.", self.body)

    def test_cancellation_restricted_to_accepted_and_on_the_way_states(self):
        self.assertIn('job_obj.status not in ["accepted", "on_the_way"]', self.body)
        self.assertIn("CANCELLATION_NOT_ALLOWED_IN_CURRENT_STATE", self.body)

    def test_successful_cancellation_unassigns_employee_and_redispatches(self):
        self.assertIn("job_obj.assigned_employee = None", self.body)
        self.assertIn('apply_transition(job_obj, "redispatching"', self.body)
        self.assertIn('emp_job.status = "EMPLOYEE_CANCELLED"', self.body)
