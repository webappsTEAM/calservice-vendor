"""
workforce_api/tests_gt/test_gt_concurrency_and_cancellation_hardening.py

Regression test suite verifying:
1. Offer acceptance on cancelled bookings produces deterministic HTTP 409 Conflict.
2. Cash settlement reconciliation acquires row-level locks and prevents duplicate cash clearance.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory

from workforce_api.models import WorkforceJobOffer
from workforce_api.services.cash_reconciliation import compute_outstanding_cash, record_cash_settlement
from workforce_api.views import WorkforceJobAcceptOfferView


class OfferAcceptanceCancellationRaceTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = WorkforceJobAcceptOfferView.as_view()

    @patch("django.db.transaction.atomic")
    @patch("workforce_api.views.is_employee_authorized_for_job", return_value=True)
    @patch("workforce_api.views.ServiceRequest.objects.filter")
    @patch("workforce_api.views.ServiceRequest.objects.select_for_update")
    @patch("workforce_api.views.Employee.objects.select_for_update")
    @patch("workforce_api.models.WorkforceJobOffer.objects.filter")
    def test_accept_offer_on_cancelled_booking_returns_409(
        self, mock_offer_filter, mock_emp_sfu, mock_sr_sfu, mock_sr_filter, mock_auth, mock_atomic
    ):
        """When a customer cancelled the booking, accepting the offer must cleanly return 409 Conflict."""
        job_mock = MagicMock()
        job_mock.id = 123
        job_mock.pk = 123
        job_mock.status = "cancelled"
        job_mock.assigned_employee = None

        emp_mock = MagicMock()
        emp_mock.pk = 45
        emp_mock.current_availability = "available"

        user_mock = MagicMock()
        user_mock.is_authenticated = True
        user_mock.employee_profile = emp_mock

        mock_sr_filter.return_value.first.return_value = job_mock
        mock_sr_sfu.return_value.filter.return_value.first.return_value = job_mock
        mock_emp_sfu.return_value.filter.return_value.first.return_value = emp_mock

        req = self.factory.post("/api/workforce/jobs/123/accept-offer/")
        req.user = user_mock

        response = self.view(req, pk=123)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.data.get("code"), "JOB_ALREADY_CANCELLED")
        mock_offer_filter.assert_called_once()
        mock_offer_filter.return_value.update.assert_called_once_with(
            status=WorkforceJobOffer.Status.CANCELLED,
            rejection_reason="Customer cancelled booking before offer acceptance."
        )


class CashSettlementConcurrencyLockingTests(SimpleTestCase):
    @patch("workforce_api.models.JobPayment.objects.filter")
    def test_compute_outstanding_cash_applies_select_for_update_when_requested(self, mock_payment_filter):
        mock_qs = MagicMock()
        mock_payment_filter.return_value = mock_qs
        mock_qs.select_for_update.return_value = []

        emp = SimpleNamespace(id=10)
        total, qs = compute_outstanding_cash(emp, lock=True)

        mock_qs.select_for_update.assert_called_once()
        self.assertEqual(total, Decimal("0.00"))

    @patch("django.db.transaction.atomic")
    @patch("employees.models.Employee.objects.select_for_update")
    @patch("workforce_api.services.cash_reconciliation.compute_outstanding_cash")
    @patch("workforce_api.models.CashSettlement.objects.create")
    @patch("workforce_api.models.JobPayment.objects.filter")
    def test_record_cash_settlement_locks_employee_and_payments(
        self, mock_payment_filter, mock_settlement_create, mock_compute, mock_emp_sfu, mock_atomic
    ):
        emp = SimpleNamespace(id=99)
        company = SimpleNamespace(id=1)
        user = SimpleNamespace(id=2)

        mock_emp_qs = MagicMock()
        mock_emp_sfu.return_value = mock_emp_qs
        mock_emp_qs.filter.return_value.first.return_value = emp

        mock_qs = MagicMock()
        mock_qs.values_list.return_value = [101, 102]
        mock_compute.return_value = (Decimal("500.00"), mock_qs)

        mock_settlement = SimpleNamespace(
            id=5,
            expected_amount=Decimal("500.00"),
            deposited_amount=Decimal("500.00"),
            discrepancy=Decimal("0.00")
        )
        mock_settlement_create.return_value = mock_settlement

        settlement = record_cash_settlement(
            employee=emp, company=company, deposited_amount="500.00", recorded_by=user
        )

        mock_emp_sfu.assert_called_once()
        mock_compute.assert_called_once_with(emp, lock=True)
        self.assertEqual(settlement.expected_amount, Decimal("500.00"))
        self.assertEqual(settlement.deposited_amount, Decimal("500.00"))
