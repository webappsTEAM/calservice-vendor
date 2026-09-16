"""
Tests for WorkforceJobLiveTrackingView and WorkforceTechnicianFeedbackView authorization.
Verifies that cross-service internal calls from the Customer platform are accepted without 401.
"""
from django.test import SimpleTestCase, override_settings
from django.test.client import RequestFactory
from workforce_api.permissions import IsInternalWorkforceCaller
from workforce_api.views import WorkforceJobLiveTrackingView, WorkforceTechnicianFeedbackView


class TrackingAndFeedbackAuthorizationTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.perm = IsInternalWorkforceCaller()

    def test_internal_caller_accepts_webhook_secret(self):
        with override_settings(WORKFORCE_WEBHOOK_SECRET="test-secret-123"):
            req = self.rf.get("/api/workforce/jobs/1/live-tracking/", HTTP_AUTHORIZATION="Bearer test-secret-123")
            self.assertTrue(self.perm.has_permission(req, None))

    def test_internal_caller_accepts_api_key(self):
        with override_settings(WORKFORCE_API_KEY="wf_integration_key_default"):
            req = self.rf.get("/api/workforce/jobs/1/live-tracking/", HTTP_AUTHORIZATION="Bearer wf_integration_key_default")
            self.assertTrue(self.perm.has_permission(req, None))

    def test_internal_caller_accepts_calservices_source_header_in_debug(self):
        with override_settings(DEBUG=True):
            req = self.rf.get("/api/workforce/jobs/1/live-tracking/", HTTP_X_CALSERVICES_SOURCE="calservices-platform")
            self.assertTrue(self.perm.has_permission(req, None))

    def test_internal_caller_rejects_invalid_token_without_source(self):
        with override_settings(WORKFORCE_WEBHOOK_SECRET="secret", WORKFORCE_API_KEY="key", DEBUG=False):
            req = self.rf.get("/api/workforce/jobs/1/live-tracking/", HTTP_AUTHORIZATION="Bearer wrong-token")
            self.assertFalse(self.perm.has_permission(req, None))

    def test_tracking_view_permissions_include_internal_caller(self):
        perms = WorkforceJobLiveTrackingView.permission_classes
        holder = perms[0]
        self.assertIn(IsInternalWorkforceCaller, [getattr(holder, "op1_class", None), getattr(holder, "op2_class", None)])

    def test_technician_feedback_view_permissions_include_internal_caller(self):
        perms = WorkforceTechnicianFeedbackView.permission_classes
        holder = perms[0]
        self.assertIn(IsInternalWorkforceCaller, [getattr(holder, "op1_class", None), getattr(holder, "op2_class", None)])
