"""
End-to-end proof of the estimation workflow.

Customer books a quotation service -> technician inspects on site -> quote is
built and sent -> customer approves -> SEVO admin approves -> work booking and
invoice are created -> customer pays -> job completes -> the provider's wallet
is credited.

Every assertion below is about behaviour that was reported broken or missing,
so a failure here is a real regression rather than a style complaint.
"""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import (
    JobPayment,
    PreServiceVerification,
    WalletAccount,
    WalletLedgerEntry,
    WorkforceInvoice,
    WorkforceQuote,
    WorkforceQuoteItem,
)
from workforce_api.services import invoice_service, quotation_service

User = get_user_model()


class EstimationWorkflowTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(company_name="Caldim Test Vendor")

        self.customer = User.objects.create_user(
            username="cust1", email="cust1@example.com", password="x", role="customer"
        )
        self.tech_user = User.objects.create_user(
            username="tech1", email="tech1@example.com", password="x", role="employee"
        )
        self.admin_user = User.objects.create_user(
            username="sevoadmin", email="admin@sevo.test", password="x", role="admin"
        )
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.technician = Employee.objects.create(
            user=self.tech_user, company=self.company, employee_id="EMP-T1"
        )

        self.job = ServiceRequest.objects.create(
            request_kind=ServiceRequest.RequestKind.ESTIMATION,
            company=self.company,
            customer=self.customer,
            customer_name="Test Customer",
            phone="9000000000",
            email="cust1@example.com",
            service_category="painting",
            issue_title="Interior Painting",
            description="2BHK repaint",
            address="1 Test Street",
            preferred_date=timezone.now().date(),
            preferred_time="10:00 AM",
            assigned_employee=self.technician,
            status="in_progress",
        )

        self.psv = PreServiceVerification.objects.create(
            job=self.job,
            employee=self.technician,
            geofence_passed=True,
            otp_verified=True,
            presence_photo="pre_service/presence/selfie.jpg",
            work_area_photo="pre_service/work_area/wall.jpg",
            is_complete=True,
        )

    # ------------------------------------------------------------------ #
    def _build_quote(self):
        allowed, detail = quotation_service.can_create_quote(self.job)
        self.assertTrue(allowed, f"pre-service gates should pass: {detail}")

        quote = WorkforceQuote.objects.create(
            job=self.job,
            technician=self.technician,
            company=self.company,
            customer=self.customer,
            title="Interior Painting Estimate",
            service_category="painting",
            service_name="Interior Painting",
        )
        WorkforceQuoteItem.objects.create(
            quote=quote, section="LABOUR", name="Painting labour",
            quantity=Decimal("10"), unit="sqft", unit_price=Decimal("100.00"),
            tax_rate=Decimal("18.00"),
        )
        quotation_service.recalculate_quote_totals(quote)
        quote.refresh_from_db()
        return quote

    # ------------------------------------------------------------------ #
    def test_quote_number_is_allocated_and_unique(self):
        q1 = self._build_quote()
        self.assertTrue(q1.quote_number.startswith("QT-"), q1.quote_number)

        q2 = WorkforceQuote.objects.create(job=self.job, technician=self.technician)
        self.assertNotEqual(q1.quote_number, q2.quote_number)

    def test_totals_are_computed_by_the_backend(self):
        quote = self._build_quote()
        self.assertEqual(quote.subtotal_amount, Decimal("1000.00"))
        self.assertEqual(quote.tax_amount, Decimal("180.00"))
        self.assertEqual(quote.total_amount, Decimal("1180.00"))
        self.assertEqual(quote.net_payable, Decimal("1180.00"))

    def test_revision_reuses_the_quote_number(self):
        """A v2 deliberately keeps the same number. This used to be impossible:
        quote_number was unique on its own, so REQUEST_CHANGES always 500ed."""
        quote = self._build_quote()
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()

        _, revised = quotation_service.record_customer_decision(
            quote.id, "REQUEST_CHANGES", notes="cheaper paint please"
        )
        quote.refresh_from_db()
        self.assertEqual(quote.status, WorkforceQuote.Status.SUPERSEDED)
        self.assertEqual(revised.quote_number, quote.quote_number)
        self.assertEqual(revised.quote_version, 2)
        self.assertEqual(revised.status, WorkforceQuote.Status.DRAFT)

    # ------------------------------------------------------------------ #
    def test_customer_acceptance_waits_for_sevo_admin(self):
        quote = self._build_quote()
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()

        quote, follow_on = quotation_service.record_customer_decision(
            quote.id, "ACCEPT", token=quote.decision_token
        )
        self.assertIsNone(follow_on, "work must NOT be created before admin approval")
        self.assertEqual(quote.status, WorkforceQuote.Status.PENDING_ADMIN_APPROVAL)
        self.assertIsNotNone(quote.submitted_for_approval_at)
        self.assertFalse(WorkforceInvoice.objects.exists())

        self.assertIn(quote, list(quotation_service.quotes_awaiting_admin_approval()))

    @override_settings(SEVO_REQUIRE_ADMIN_QUOTE_APPROVAL=False)
    def test_admin_gate_can_be_switched_off(self):
        quote = self._build_quote()
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        quote, work_job = quotation_service.record_customer_decision(
            quote.id, "ACCEPT", token=quote.decision_token
        )
        self.assertIsNotNone(work_job)
        self.assertEqual(quote.status, WorkforceQuote.Status.CONVERTED)

    # ------------------------------------------------------------------ #
    def _accepted_quote(self):
        quote = self._build_quote()
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        quote, _ = quotation_service.record_customer_decision(
            quote.id, "ACCEPT", token=quote.decision_token
        )
        return quote

    def test_admin_approval_creates_work_booking_and_invoice(self):
        quote = self._accepted_quote()
        quote, work_job, invoice = quotation_service.admin_review_quote(
            quote.id, self.admin_user, approve=True, notes="looks right"
        )

        self.assertEqual(quote.status, WorkforceQuote.Status.CONVERTED)
        self.assertIsNotNone(quote.admin_approved_at)
        self.assertEqual(quote.admin_approved_by_id, self.admin_user.id)

        self.assertEqual(work_job.request_kind, "WORK")
        self.assertEqual(work_job.parent_request_id, self.job.id)

        self.assertEqual(invoice.status, WorkforceInvoice.Status.ISSUED)
        self.assertEqual(invoice.total_amount, Decimal("1180.00"))
        self.assertEqual(invoice.balance_due, Decimal("1180.00"))
        self.assertTrue(invoice.invoice_number.startswith("INV-"))
        self.assertEqual(invoice.items.count(), 1)

        # The row that settlement reads. Absent before this change, which is
        # why converted jobs completed without anyone being paid.
        jp = JobPayment.objects.get(job=work_job)
        self.assertEqual(jp.amount_due, Decimal("1180.00"))

    def test_admin_approval_is_idempotent(self):
        quote = self._accepted_quote()
        _, job1, inv1 = quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)
        _, job2, inv2 = quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)
        self.assertEqual(job1.id, job2.id)
        self.assertEqual(inv1.id, inv2.id)
        self.assertEqual(WorkforceInvoice.objects.count(), 1)

    def test_admin_rejection_creates_nothing(self):
        quote = self._accepted_quote()
        quote, work_job, invoice = quotation_service.admin_review_quote(
            quote.id, self.admin_user, approve=False, reason="rate card mismatch"
        )
        self.assertEqual(quote.status, WorkforceQuote.Status.ADMIN_REJECTED)
        self.assertIsNone(work_job)
        self.assertIsNone(invoice)
        self.assertFalse(WorkforceInvoice.objects.exists())

    # ------------------------------------------------------------------ #
    def test_payment_is_idempotent_on_reference(self):
        quote = self._accepted_quote()
        _, _, invoice = quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)

        invoice, p1, created1 = invoice_service.record_invoice_payment(
            invoice, Decimal("1180.00"), method="ONLINE", reference="pay_ABC123"
        )
        invoice, p2, created2 = invoice_service.record_invoice_payment(
            invoice, Decimal("1180.00"), method="ONLINE", reference="pay_ABC123"
        )
        self.assertTrue(created1)
        self.assertFalse(created2, "a replayed gateway callback must not charge twice")
        self.assertEqual(p1.id, p2.id)
        self.assertEqual(invoice.amount_paid, Decimal("1180.00"))
        self.assertEqual(invoice.status, WorkforceInvoice.Status.PAID)

    def test_partial_payment_then_settlement(self):
        quote = self._accepted_quote()
        _, work_job, invoice = quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)

        invoice, _, _ = invoice_service.record_invoice_payment(
            invoice, Decimal("500.00"), method="UPI", reference="p1"
        )
        self.assertEqual(invoice.status, WorkforceInvoice.Status.PARTIALLY_PAID)
        self.assertEqual(invoice.balance_due, Decimal("680.00"))

        invoice, _, _ = invoice_service.record_invoice_payment(
            invoice, Decimal("680.00"), method="UPI", reference="p2"
        )
        self.assertEqual(invoice.status, WorkforceInvoice.Status.PAID)
        self.assertEqual(invoice.balance_due, Decimal("0.00"))

    def test_overpayment_is_refused(self):
        from django.core.exceptions import ValidationError
        quote = self._accepted_quote()
        _, _, invoice = quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)
        with self.assertRaises(ValidationError):
            invoice_service.record_invoice_payment(invoice, Decimal("5000.00"), reference="too-much")

    # ------------------------------------------------------------------ #
    def test_payment_reaches_the_provider_wallet(self):
        quote = self._accepted_quote()
        _, work_job, invoice = quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)

        invoice_service.record_invoice_payment(
            invoice, Decimal("1180.00"), method="ONLINE", reference="pay_WALLET"
        )

        # Job finishes -> settlement runs -> wallet credited.
        from workforce_api.services.commission import settle_completed_job
        work_job.status = "completed"
        work_job.save()
        entry = settle_completed_job(work_job)

        self.assertIsNotNone(entry)
        self.assertEqual(entry.entry_type, WalletLedgerEntry.EntryType.JOB_CREDIT)
        self.assertEqual(entry.gross_job_amount, Decimal("1180.00"))

        wallet = entry.wallet
        self.assertEqual(wallet.account_type, WalletAccount.AccountType.PROVIDER_HEAD)
        self.assertEqual(wallet.company_id, self.company.id)

        commission = WalletLedgerEntry.objects.get(
            job=work_job, entry_type=WalletLedgerEntry.EntryType.COMMISSION_DEBIT
        )
        self.assertEqual(entry.signed_amount + (-commission.signed_amount), Decimal("1180.00"))


class EstimationApiTests(EstimationWorkflowTests):
    """The same workflow, driven through HTTP the way the apps drive it."""

    def test_customer_decision_endpoint_and_admin_review_endpoint(self):
        quote = self._build_quote()
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()

        anon = APIClient()
        url = f"/api/workforce/quotes/decision/{quote.decision_token}/"

        resp = anon.get(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data["can_decide"])
        self.assertEqual(len(resp.data["items"]), 1)
        self.assertNotIn("decision_token", resp.data, "the token must never be echoed back")

        resp = anon.post(url, {"action": "ACCEPT"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data["awaiting_admin_approval"])

        self.assertEqual(anon.get("/api/workforce/quotes/decision/short/").status_code, 404)

        admin = APIClient()
        admin.force_authenticate(self.admin_user)

        resp = admin.get("/api/workforce/quotes/pending-approval/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual([q["id"] for q in resp.data], [quote.id])

        resp = admin.post(f"/api/workforce/quotes/{quote.id}/admin-review/",
                          {"action": "APPROVE"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertIsNotNone(resp.data["invoice"])
        invoice_id = resp.data["invoice"]["id"]

        resp = admin.post(f"/api/workforce/invoices/{invoice_id}/payments/",
                          {"amount": "1180.00", "method": "ONLINE", "reference": "pay_HTTP"},
                          format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data["invoice"]["status"], "PAID")

        # replay -> 200, not a second charge
        resp = admin.post(f"/api/workforce/invoices/{invoice_id}/payments/",
                          {"amount": "1180.00", "method": "ONLINE", "reference": "pay_HTTP"},
                          format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.data["duplicate"])

    def test_a_vendor_admin_cannot_approve_their_own_quote(self):
        quote = self._accepted_quote()
        vendor_admin = User.objects.create_user(
            username="vadmin", email="v@a.test", password="x", role="admin"
        )
        Employee.objects.create(user=vendor_admin, company=self.company, employee_id="EMP-A1")
        client = APIClient()
        client.force_authenticate(vendor_admin)
        resp = client.post(f"/api/workforce/quotes/{quote.id}/admin-review/",
                           {"action": "APPROVE"}, format="json")
        self.assertEqual(resp.status_code, 403, resp.content)

    def test_customer_sees_only_their_own_invoice(self):
        quote = self._accepted_quote()
        quotation_service.admin_review_quote(quote.id, self.admin_user, approve=True)

        client = APIClient()
        client.force_authenticate(self.customer)
        resp = client.get("/api/workforce/invoices/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.data), 1)

        stranger = User.objects.create_user(username="nosy", email="n@x.test", password="x")
        client.force_authenticate(stranger)
        resp = client.get("/api/workforce/invoices/")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.data, [])
