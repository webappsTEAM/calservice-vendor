"""
test_gt_hardening_vendor.py

Vendor / Workforce Dispatch Hardening Verification Suite.
Verifies:
1. Vendor dispatch cannot dispatch rejected bookings (status='rejected').
2. Vendor dispatch cannot dispatch prohibited cargo bookings (cargo_safety_status='rejected').
3. Vendor dispatch cannot dispatch cancelled or completed bookings.
"""

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from workforce_api.services.automatic_dispatch import dispatch_job, _dispatch_job_locked


class VendorDispatchHardeningTests(unittest.TestCase):
    """Verifies that rejected bookings cannot be dispatched."""

    @patch("django.db.transaction.atomic")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_rejected_status_cannot_be_dispatched(self, mock_select, mock_atomic):
        """A booking with status='rejected' must be immediately refused by dispatch."""
        mock_job = MagicMock()
        mock_job.id = 9991
        mock_job.status = "rejected"
        mock_job.assigned_employee = None
        mock_select.return_value.filter.return_value.first.return_value = mock_job

        success, msg = _dispatch_job_locked(9991, 1800, None)
        self.assertFalse(success)
        self.assertIn("rejected", msg.lower())
        self.assertIn("cannot be dispatched", msg.lower())

    @patch("django.db.transaction.atomic")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_prohibited_cargo_cannot_be_dispatched(self, mock_select, mock_atomic):
        """A booking with cargo_safety_status='rejected' must be refused by dispatch."""
        mock_job = MagicMock()
        mock_job.id = 9992
        mock_job.status = "new_request"
        mock_job.cargo_safety_status = "rejected"
        mock_job.assigned_employee = None
        mock_select.return_value.filter.return_value.first.return_value = mock_job

        success, msg = _dispatch_job_locked(9992, 1800, None)
        self.assertFalse(success)
        self.assertIn("prohibited cargo", msg.lower())
        self.assertIn("cannot be dispatched", msg.lower())

    @patch("django.db.transaction.atomic")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_cancelled_status_cannot_be_dispatched(self, mock_select, mock_atomic):
        """A booking with status='cancelled' cannot be dispatched."""
        mock_job = MagicMock()
        mock_job.id = 9993
        mock_job.status = "cancelled"
        mock_job.assigned_employee = None
        mock_select.return_value.filter.return_value.first.return_value = mock_job

        success, msg = _dispatch_job_locked(9993, 1800, None)
        self.assertFalse(success)
        self.assertIn("cancelled", msg.lower())

    @patch("django.db.transaction.atomic")
    @patch("service_requests.models.ServiceRequest.objects.select_for_update")
    def test_completed_status_cannot_be_dispatched(self, mock_select, mock_atomic):
        """A booking with status='completed' cannot be dispatched."""
        mock_job = MagicMock()
        mock_job.id = 9994
        mock_job.status = "completed"
        mock_job.assigned_employee = None
        mock_select.return_value.filter.return_value.first.return_value = mock_job

        success, msg = _dispatch_job_locked(9994, 1800, None)
        self.assertFalse(success)
        self.assertIn("completed", msg.lower())


from rest_framework.test import APIRequestFactory, force_authenticate
from workforce_api.views import WorkforceCustomerBookingQuoteView


class VendorCustomerQuoteSecurityTests(unittest.TestCase):
    """
    Verifies that WorkforceCustomerBookingQuoteView requires authentication or tracking token,
    and strictly prevents Customer A from viewing Customer B's quotation.
    """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WorkforceCustomerBookingQuoteView.as_view()

    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_unauthenticated_without_token_returns_401(self, mock_sr_filter):
        mock_job = MagicMock()
        mock_job.id = 501
        mock_job.tracking_token = "valid-tracking-token-uuid"
        mock_sr_filter.return_value.first.return_value = mock_job

        req = self.factory.get("/api/workforce/customer/bookings/501/quote/")
        resp = self.view(req, booking_id="501")
        self.assertEqual(resp.status_code, 401)
        self.assertIn("authentication required", resp.data["error"].lower())

    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_unauthenticated_with_wrong_token_returns_403(self, mock_sr_filter):
        mock_job = MagicMock()
        mock_job.id = 501
        mock_job.tracking_token = "valid-tracking-token-uuid"
        mock_sr_filter.return_value.first.return_value = mock_job

        req = self.factory.get("/api/workforce/customer/bookings/501/quote/?token=wrong-token-uuid")
        resp = self.view(req, booking_id="501")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("invalid tracking token", resp.data["error"].lower())

    @patch("service_requests.models.Estimation.objects.filter")
    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_unauthenticated_with_valid_token_returns_200(self, mock_sr_filter, mock_est_filter):
        mock_job = MagicMock()
        mock_job.id = 501
        mock_job.tracking_token = "valid-tracking-token-uuid"
        mock_sr_filter.return_value.first.return_value = mock_job

        mock_est = MagicMock()
        mock_quote = MagicMock()
        mock_quote.id = 99
        mock_quote.quote_ref = "EST-99"
        mock_quote.version = 1
        mock_quote.status = "APPROVED"
        mock_quote.subtotal = 1000.0
        mock_quote.tax_amount = 180.0
        mock_quote.discount_amount = 0.0
        mock_quote.total_amount = 1180.0
        mock_quote.valid_until = None
        mock_quote.notes = ""
        mock_quote.items.all.return_value = []
        mock_est.quotations.order_by.return_value.first.return_value = mock_quote
        mock_est_filter.return_value.first.return_value = mock_est

        req = self.factory.get("/api/workforce/customer/bookings/501/quote/?token=valid-tracking-token-uuid")
        resp = self.view(req, booking_id="501")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["quote_id"], 99)

    @patch("service_requests.models.Estimation.objects.filter")
    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_customer_owner_can_access_own_quote(self, mock_sr_filter, mock_est_filter):
        mock_user = MagicMock()
        mock_user.id = 42
        mock_user.pk = 42
        mock_user.is_authenticated = True
        mock_user.is_superuser = False
        mock_user.is_staff = False
        mock_user.role = "customer"
        mock_user.company_id = None
        del mock_user.employee_profile

        mock_job = MagicMock()
        mock_job.id = 501
        mock_job.customer_id = 42
        mock_job.tracking_token = "valid-tracking-token-uuid"
        mock_job.company_id = 1
        mock_job.assigned_employee_id = 999
        mock_sr_filter.return_value.first.return_value = mock_job

        mock_est = MagicMock()
        mock_quote = MagicMock()
        mock_quote.id = 99
        mock_quote.quote_ref = "EST-99"
        mock_quote.version = 1
        mock_quote.status = "APPROVED"
        mock_quote.subtotal = 1000.0
        mock_quote.tax_amount = 180.0
        mock_quote.discount_amount = 0.0
        mock_quote.total_amount = 1180.0
        mock_quote.valid_until = None
        mock_quote.notes = ""
        mock_quote.items.all.return_value = []
        mock_est.quotations.order_by.return_value.first.return_value = mock_quote
        mock_est_filter.return_value.first.return_value = mock_est

        req = self.factory.get("/api/workforce/customer/bookings/501/quote/")
        force_authenticate(req, user=mock_user)
        resp = self.view(req, booking_id="501")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["quote_id"], 99)

    @patch("service_requests.models.ServiceRequest.objects.filter")
    def test_customer_a_cannot_access_customer_b_quote(self, mock_sr_filter):
        # Customer A (id=101) attempts to access Customer B's job (customer_id=202)
        mock_user_a = MagicMock()
        mock_user_a.id = 101
        mock_user_a.pk = 101
        mock_user_a.is_authenticated = True
        mock_user_a.is_superuser = False
        mock_user_a.is_staff = False
        mock_user_a.role = "customer"
        mock_user_a.company_id = None
        del mock_user_a.employee_profile

        mock_job_b = MagicMock()
        mock_job_b.id = 502
        mock_job_b.customer_id = 202
        mock_job_b.tracking_token = "job-b-tracking-uuid"
        mock_job_b.company_id = 1
        mock_job_b.assigned_employee_id = 999
        mock_sr_filter.return_value.first.return_value = mock_job_b

        req = self.factory.get("/api/workforce/customer/bookings/502/quote/")
        force_authenticate(req, user=mock_user_a)
        resp = self.view(req, booking_id="502")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("not authorized", resp.data["error"].lower())


if __name__ == "__main__":
    unittest.main()

