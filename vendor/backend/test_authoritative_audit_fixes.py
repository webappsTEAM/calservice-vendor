import os
import sys
import unittest
from decimal import Decimal
from datetime import date


# Setup django environment before importing Django apps / DRF
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
os.environ["CACHE_URL"] = "locmem://workforce-test-cache"
import django
django.setup()

from django.test import TestCase, override_settings
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status


from companies.models import Company, Region
from employees.models import Employee
from workforce_api.models import (
    VendorTechnicianRelationship,
    VendorRelievingRequest,
    WalletAccount,
    WalletLedgerEntry,
    GroceryOrder,
    GroceryOrderItem,
    VendorStore,
    InventoryItem,
    InventoryTransaction,
    FinancialLedgerEntry,
    JobPayment,
)
from service_requests.models import ServiceRequest
from vendor_wallet.models import (
    EmployeeWallet,
    EmployeeWalletTransaction,
    EmployeeWalletWithdrawal,
    EmployeePayoutAccount,
)
from vendor_wallet.constants import (
    WALLET_ACTIVE,
    WITHDRAWAL_REQUESTED,
    WITHDRAWAL_PROCESSING,
    WITHDRAWAL_COMPLETED,
    WITHDRAWAL_FAILED,
)
from workforce_api.services.vendor_network import VendorRelievingService
from workforce_api.services.commission import settle_completed_job, sync_employee_wallet_mirror
from workforce_api.views import (
    RelievingLegalSignoffView,
    VendorOrderStatusUpdateView,
    VendorOrderAcceptView,
    VendorOrderRejectView,
)
from vendor_wallet.views import (
    WalletSummaryView,
    WalletTransactionListView,
    AdminWithdrawalProcessView,
    AdminWithdrawalCompleteView,
    AdminWithdrawalFailView,
)

User = get_user_model()


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    SEVO_COMMISSION_DISPUTE_HOLD_HOURS=0,
)
class AuthoritativeAuditFixesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

        # Region & Companies
        cls.region, _ = Region.objects.get_or_create(
            code="IN", defaults={"name": "India", "currency": "INR"}
        )
        cls.company_a, _ = Company.objects.get_or_create(
            slug="audit-vendor-a",
            defaults={"company_name": "Vendor A Ltd", "is_active": True, "region": cls.region},
        )
        cls.company_a.business_type = "grocery_supplier"
        cls.company_a.selected_modules = ["grocery_supplier"]
        cls.company_a.save()

        cls.company_b, _ = Company.objects.get_or_create(
            slug="audit-vendor-b",
            defaults={"company_name": "Vendor B Ltd", "is_active": True, "region": cls.region},
        )


        # Users
        cls.superadmin, _ = User.objects.get_or_create(
            username="audit_superadmin",
            defaults={"email": "audit_superadmin@platform.test", "role": "admin", "is_superuser": True, "is_staff": True},
        )
        cls.superadmin.is_superuser = True
        cls.superadmin.is_staff = True
        cls.superadmin.save()

        cls.vendor_admin_a, _ = User.objects.get_or_create(
            username="audit_admin_a",
            defaults={"email": "audit_admin_a@vendor.test", "company": cls.company_a, "role": "admin", "is_staff": True},
        )
        cls.vendor_admin_a.company = cls.company_a
        cls.vendor_admin_a.role = "admin"
        cls.vendor_admin_a.save()

        cls.vendor_admin_b, _ = User.objects.get_or_create(
            username="audit_admin_b",
            defaults={"email": "audit_admin_b@vendor.test", "company": cls.company_b, "role": "admin", "is_staff": True},
        )
        cls.vendor_admin_b.company = cls.company_b
        cls.vendor_admin_b.role = "admin"
        cls.vendor_admin_b.save()

        cls.tech_user, _ = User.objects.get_or_create(
            username="audit_technician_1",
            defaults={"email": "audit_tech1@vendor.test", "company": cls.company_a, "role": "employee"},
        )
        cls.tech_user.company = cls.company_a
        cls.tech_user.role = "employee"
        cls.tech_user.save()

        cls.other_tech_user, _ = User.objects.get_or_create(
            username="audit_technician_2",
            defaults={"email": "audit_tech2@vendor.test", "company": cls.company_b, "role": "employee"},
        )
        cls.other_tech_user.company = cls.company_b
        cls.other_tech_user.role = "employee"
        cls.other_tech_user.save()


        # Employees
        cls.emp_tech, _ = Employee.objects.get_or_create(
            user=cls.tech_user,
            defaults={"company": cls.company_a, "employee_id": "AUD-EMP-001"},
        )
        cls.emp_tech.company = cls.company_a
        cls.emp_tech.save()

        cls.emp_admin_a, _ = Employee.objects.get_or_create(
            user=cls.vendor_admin_a,
            defaults={"company": cls.company_a, "employee_id": "AUD-ADM-001"},
        )
        cls.emp_admin_a.company = cls.company_a
        cls.emp_admin_a.save()

        cls.emp_admin_b, _ = Employee.objects.get_or_create(
            user=cls.vendor_admin_b,
            defaults={"company": cls.company_b, "employee_id": "AUD-ADM-002"},
        )
        cls.emp_admin_b.company = cls.company_b
        cls.emp_admin_b.save()

        cls.emp_other_tech, _ = Employee.objects.get_or_create(
            user=cls.other_tech_user,
            defaults={"company": cls.company_b, "employee_id": "AUD-EMP-002"},
        )
        cls.emp_other_tech.company = cls.company_b
        cls.emp_other_tech.save()

        # Relationship
        cls.rel_a, _ = VendorTechnicianRelationship.objects.get_or_create(
            vendor=cls.company_a,
            technician=cls.emp_tech,
            defaults={"status": VendorTechnicianRelationship.Status.ACTIVE},
        )
        cls.rel_a.status = VendorTechnicianRelationship.Status.ACTIVE
        cls.rel_a.save()

    def setUp(self):
        self.factory = self.__class__.factory


    # =========================================================================
    # 1. P1 — Relieving Legal Signoff Authorization
    # =========================================================================

    def test_relieving_signoff_cross_company_rejection(self):
        """Vendor B admin cannot sign off on Company A relieving request."""
        req = VendorRelievingRequest.objects.create(
            relationship=self.rel_a,
            technician=self.emp_tech,
            vendor=self.company_a,
            status=VendorRelievingRequest.Status.REQUESTED,
        )

        request = self.factory.post(
            f"/api/workforce/relieving-requests/{req.id}/signoff/",
            {"persona": "vendor"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_b)
        response = RelievingLegalSignoffView.as_view()(request, pk=req.id)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        req.refresh_from_db()
        self.assertFalse(req.vendor_signoff_ack)

    def test_relieving_signoff_technician_authorization(self):
        """Only the assigned technician can submit persona=technician signoff."""
        req = VendorRelievingRequest.objects.create(
            relationship=self.rel_a,
            technician=self.emp_tech,
            vendor=self.company_a,
            status=VendorRelievingRequest.Status.REQUESTED,
        )

        # Wrong technician tries to sign
        request = self.factory.post(
            f"/api/workforce/relieving-requests/{req.id}/signoff/",
            {"persona": "technician"},
            format="json",
        )
        force_authenticate(request, user=self.other_tech_user)
        response = RelievingLegalSignoffView.as_view()(request, pk=req.id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Correct technician signs
        force_authenticate(request, user=self.tech_user)
        response = RelievingLegalSignoffView.as_view()(request, pk=req.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertTrue(req.worker_signoff_ack)

    def test_relieving_signoff_authorized_vendor_admin(self):
        """Authorized Company A admin can execute persona=vendor signoff."""
        req = VendorRelievingRequest.objects.create(
            relationship=self.rel_a,
            technician=self.emp_tech,
            vendor=self.company_a,
            status=VendorRelievingRequest.Status.REQUESTED,
            worker_signoff_ack=True,
            sevo_approved_at=timezone.now(),
        )

        request = self.factory.post(
            f"/api/workforce/relieving-requests/{req.id}/signoff/",
            {"persona": "vendor"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        response = RelievingLegalSignoffView.as_view()(request, pk=req.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertTrue(req.vendor_signoff_ack)
        # Should finalize relieving:
        self.assertEqual(req.status, VendorRelievingRequest.Status.COMPLETED)
        self.rel_a.refresh_from_db()
        self.assertEqual(self.rel_a.status, VendorTechnicianRelationship.Status.RESIGNED)
        self.emp_tech.refresh_from_db()
        self.assertIsNone(self.emp_tech.company)
        # Check solo worker wallet provisioned:
        self.assertTrue(
            WalletAccount.objects.filter(
                employee=self.emp_tech, account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER
            ).exists()
        )


    def test_relieving_signoff_platform_superadmin_override(self):
        """Platform Superadmin has authorized platform override for vendor signoff."""
        req = VendorRelievingRequest.objects.create(
            relationship=self.rel_a,
            technician=self.emp_tech,
            vendor=self.company_a,
            status=VendorRelievingRequest.Status.REQUESTED,
        )

        request = self.factory.post(
            f"/api/workforce/relieving-requests/{req.id}/signoff/",
            {"persona": "vendor"},
            format="json",
        )
        force_authenticate(request, user=self.superadmin)
        response = RelievingLegalSignoffView.as_view()(request, pk=req.id)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertTrue(req.vendor_signoff_ack)

    # =========================================================================
    # 2. P1 — Grocery Order State Machine & Delivered Idempotency
    # =========================================================================

    def _create_grocery_order(self, initial_status=GroceryOrder.Status.ACCEPTED):
        store, _ = VendorStore.objects.get_or_create(
            company=self.company_a,
            defaults={
                "store_name": "Fresh Mart",
                "store_slug": f"fresh-mart-{int(timezone.now().timestamp() * 1000)}",
                "store_address": "123 Main St",
            },
        )

        inv = InventoryItem.objects.create(
            company=self.company_a,
            catalogue_service_id=int(timezone.now().timestamp() * 1000) % 1000000,
            catalogue_category_id=1,
            name_snapshot="Organic Apples",
            category_name_snapshot="Fruits",
            custom_price=Decimal("60.00"),
            quantity_in_stock=Decimal("10.000"),
            reserved_quantity=Decimal("2.000"),
        )
        order = GroceryOrder.objects.create(
            order_number=f"ORD-{int(timezone.now().timestamp() * 1000)}",
            customer_id="CUST-101",
            vendor_store=store,
            status=initial_status,
            subtotal=Decimal("120.00"),
            total_amount=Decimal("120.00"),
        )
        GroceryOrderItem.objects.create(
            order=order,
            inventory_item=inv,
            product_name_snapshot="Organic Apples",
            sku_snapshot="APP-001",
            unit_snapshot="kg",
            quantity=Decimal("2.000"),
            mrp_snapshot=Decimal("60.00"),
            regular_price_snapshot=Decimal("60.00"),
            final_unit_price=Decimal("60.00"),
            total_price=Decimal("120.00"),
        )

        return order, inv

    def test_grocery_state_machine_valid_progression(self):
        """Test strict linear progression: ACCEPTED -> PICKING -> PACKED -> OUT_FOR_DELIVERY -> DELIVERED."""
        order, inv = self._create_grocery_order(initial_status=GroceryOrder.Status.ACCEPTED)

        # 1. ACCEPTED -> PICKING
        request = self.factory.post(
            f"/api/workforce/orders/grocery/{order.id}/status/",
            {"status": "PICKING"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        res = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, GroceryOrder.Status.PICKING)

        # 2. PICKING -> PACKED
        request = self.factory.post(
            f"/api/workforce/orders/grocery/{order.id}/status/",
            {"status": "PACKED"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        res = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, GroceryOrder.Status.PACKED)

        # 3. PACKED -> OUT_FOR_DELIVERY
        request = self.factory.post(
            f"/api/workforce/orders/grocery/{order.id}/status/",
            {"status": "OUT_FOR_DELIVERY"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        res = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, GroceryOrder.Status.OUT_FOR_DELIVERY)

        # 4. OUT_FOR_DELIVERY -> DELIVERED
        request = self.factory.post(
            f"/api/workforce/orders/grocery/{order.id}/status/",
            {"status": "DELIVERED"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        res = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, GroceryOrder.Status.DELIVERED)

    def test_grocery_state_machine_illegal_skips_rejected(self):
        """Illegal skips like ACCEPTED -> DELIVERED or PICKING -> DELIVERED are strictly rejected."""
        order, _ = self._create_grocery_order(initial_status=GroceryOrder.Status.ACCEPTED)

        # Try ACCEPTED -> DELIVERED directly
        request = self.factory.post(
            f"/api/workforce/orders/grocery/{order.id}/status/",
            {"status": "DELIVERED"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        res = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Illegal status transition", res.data["error"])

        # Advance to PICKING
        order.status = GroceryOrder.Status.PICKING
        order.save()

        # Try PICKING -> DELIVERED directly
        res = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Illegal status transition", res.data["error"])

    def test_grocery_delivered_strict_idempotency(self):
        """Calling DELIVERED twice produces no duplicate stock deductions or financial ledger credits."""
        order, inv = self._create_grocery_order(initial_status=GroceryOrder.Status.OUT_FOR_DELIVERY)

        stock_before = inv.quantity_in_stock  # 10.000
        reserved_before = inv.reserved_quantity  # 2.000

        # First DELIVERED call
        request = self.factory.post(
            f"/api/workforce/orders/grocery/{order.id}/status/",
            {"status": "DELIVERED"},
            format="json",
        )
        force_authenticate(request, user=self.vendor_admin_a)
        res1 = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res1.status_code, status.HTTP_200_OK)

        order.refresh_from_db()
        inv.refresh_from_db()
        self.assertEqual(order.status, GroceryOrder.Status.DELIVERED)
        self.assertEqual(inv.quantity_in_stock, stock_before - Decimal("2.000"))  # 8.000
        self.assertEqual(inv.reserved_quantity, reserved_before - Decimal("2.000"))  # 0.000

        sale_txns_count = InventoryTransaction.objects.filter(
            reference_id=order.order_number, transaction_type=InventoryTransaction.TransactionType.SALE
        ).count()
        self.assertEqual(sale_txns_count, 1)

        ledger_entries_count = FinancialLedgerEntry.objects.filter(
            order=order, category=FinancialLedgerEntry.Category.SALE
        ).count()
        self.assertEqual(ledger_entries_count, 1)

        # Second IDENTICAL DELIVERED call (Idempotency test)
        res2 = VendorOrderStatusUpdateView.as_view()(request, pk=order.id)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)
        self.assertIn("already", res2.data["message"])

        inv.refresh_from_db()
        # Stock and reserved MUST NOT have been deducted a second time:
        self.assertEqual(inv.quantity_in_stock, Decimal("8.000"))
        self.assertEqual(inv.reserved_quantity, Decimal("0.000"))

        # Transactions & Ledgers MUST STILL be exactly 1:
        self.assertEqual(
            InventoryTransaction.objects.filter(
                reference_id=order.order_number, transaction_type=InventoryTransaction.TransactionType.SALE
            ).count(),
            1
        )
        self.assertEqual(
            FinancialLedgerEntry.objects.filter(
                order=order, category=FinancialLedgerEntry.Category.SALE
            ).count(),
            1
        )

    # =========================================================================
    # 3. P1 — Two Wallet Systems Reconciliation
    # =========================================================================

    def test_two_wallet_settle_job_and_retry_self_healing(self):
        """Settling a completed job credits WalletLedgerEntry and mirrors into EmployeeWallet. Retries self-heal."""
        emp_wallet, _ = EmployeeWallet.objects.get_or_create(
            employee=self.emp_tech,
            defaults={"company": self.company_a, "currency": "INR", "status": WALLET_ACTIVE},
        )
        emp_wallet.company = self.company_a
        emp_wallet.status = WALLET_ACTIVE
        emp_wallet.save()

        job = ServiceRequest.objects.create(
            request_id=f"SR-{int(timezone.now().timestamp() * 1000)}",
            service_category="plumbing",
            issue_title="Plumbing Job",
            address="123 Test St",
            preferred_date=date.today(),
            customer_name="John Customer",
            company=self.company_a,
            assigned_employee=self.emp_tech,
            status="completed",
        )


        JobPayment.objects.create(
            job=job,
            amount_due=Decimal("1000.00"),
            amount_paid=Decimal("1000.00"),
            payment_method=JobPayment.PaymentMethod.ONLINE,
        )

        # Initial settlement
        credit_entry = settle_completed_job(job)
        self.assertIsNotNone(credit_entry)

        # Verify WalletLedgerEntry in head wallet
        head_wallet = self.company_a.head_wallet
        self.assertTrue(WalletLedgerEntry.objects.filter(wallet=head_wallet, job=job).exists())

        # Verify EmployeeWallet mirror
        emp_wallet = EmployeeWallet.objects.get(employee=self.emp_tech)
        self.assertGreater(emp_wallet.pending_balance, Decimal("0.00"))
        txn = EmployeeWalletTransaction.objects.filter(wallet=emp_wallet, service_request_id=job.id).first()
        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, credit_entry.signed_amount)

        # Simulate mirror missing/deleted to test self-healing retry:
        balance_before = emp_wallet.pending_balance
        txn.delete()
        emp_wallet.pending_balance = balance_before - credit_entry.signed_amount
        emp_wallet.save()

        # Retry settle_completed_job:
        retry_entry = settle_completed_job(job)
        self.assertEqual(retry_entry.id, credit_entry.id)

        # Verify that retry self-healed and re-mirrored into EmployeeWallet:
        emp_wallet.refresh_from_db()
        self.assertEqual(emp_wallet.pending_balance, balance_before)
        healed_txn = EmployeeWalletTransaction.objects.filter(wallet=emp_wallet, service_request_id=job.id).first()
        self.assertIsNotNone(healed_txn)

    # =========================================================================
    # 4. P2 — Wallet GET Side Effects
    # =========================================================================

    def test_wallet_get_does_not_create_records_when_unprovisioned(self):
        """GET /workforce/wallet/ returns 404 for unprovisioned employee without creating DB rows."""
        unprov_user = User.objects.create_user(
            username="unprov_tech", email="unprov@example.com", password="password123", role="employee"
        )
        unprov_emp = Employee.objects.create(user=unprov_user, employee_id="UNPROV-01")

        self.assertFalse(EmployeeWallet.objects.filter(employee=unprov_emp).exists())

        # Repeated GET requests:
        for _ in range(3):
            request = self.factory.get("/api/workforce/wallet/")
            force_authenticate(request, user=unprov_user)
            response = WalletSummaryView.as_view()(request)
            self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify 0 rows created in database:
        self.assertFalse(EmployeeWallet.objects.filter(employee=unprov_emp).exists())

    def test_wallet_get_read_only_for_provisioned_wallet(self):
        """GET /workforce/wallet/ for provisioned wallet returns 200 and mutates zero records."""
        EmployeeWallet.objects.create(
            employee=self.emp_tech,
            company=self.company_a,
            currency="INR",
            status=WALLET_ACTIVE,
        )
        wallet_count_before = EmployeeWallet.objects.count()

        request = self.factory.get("/api/workforce/wallet/")
        force_authenticate(request, user=self.tech_user)
        response = WalletSummaryView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(EmployeeWallet.objects.count(), wallet_count_before)

    # =========================================================================
    # 5. P2 — Withdrawal Concurrency Serialization
    # =========================================================================

    def test_admin_withdrawal_process_complete_fail_serialization(self):
        """Test that AdminWithdrawalProcessView, CompleteView, and FailView are strictly serialized."""
        wallet = EmployeeWallet.objects.create(
            employee=self.emp_tech,
            company=self.company_a,
            available_balance=Decimal("1000.00"),
            currency="INR",
            status=WALLET_ACTIVE,
        )
        withdrawal = EmployeeWalletWithdrawal.objects.create(
            wallet=wallet,
            employee=self.emp_tech,
            amount=Decimal("500.00"),
            status=WITHDRAWAL_REQUESTED,
        )

        # 1. Process: REQUESTED -> PROCESSING
        req_process = self.factory.post(f"/api/workforce/admin/wallet/withdrawals/{withdrawal.id}/process/")
        force_authenticate(req_process, user=self.vendor_admin_a)
        res_proc = AdminWithdrawalProcessView.as_view()(req_process, pk=withdrawal.id)
        self.assertEqual(res_proc.status_code, status.HTTP_200_OK)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, WITHDRAWAL_PROCESSING)

        # Calling process AGAIN on already PROCESSING returns 409 Conflict:
        res_proc_again = AdminWithdrawalProcessView.as_view()(req_process, pk=withdrawal.id)
        self.assertEqual(res_proc_again.status_code, status.HTTP_409_CONFLICT)

        # 2. Complete: PROCESSING -> COMPLETED
        req_complete = self.factory.post(
            f"/api/workforce/admin/wallet/withdrawals/{withdrawal.id}/complete/",
            {"bank_transaction_id": "BANK-UTR-999"},
            format="json",
        )
        force_authenticate(req_complete, user=self.vendor_admin_a)
        res_comp = AdminWithdrawalCompleteView.as_view()(req_complete, pk=withdrawal.id)
        self.assertEqual(res_comp.status_code, status.HTTP_200_OK)
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, WITHDRAWAL_COMPLETED)

        # 3. Now try to Fail an ALREADY COMPLETED withdrawal:
        req_fail = self.factory.post(
            f"/api/workforce/admin/wallet/withdrawals/{withdrawal.id}/fail/",
            {"failure_reason": "Bank timeout"},
            format="json",
        )
        force_authenticate(req_fail, user=self.vendor_admin_a)
        res_fail = AdminWithdrawalFailView.as_view()(req_fail, pk=withdrawal.id)

        # MUST be rejected with 409 Conflict!
        self.assertEqual(res_fail.status_code, status.HTTP_409_CONFLICT)

        # Balance must NOT be refunded!
        wallet.refresh_from_db()
        self.assertEqual(wallet.available_balance, Decimal("1000.00"))
        # No refund reversal transaction:
        self.assertFalse(
            EmployeeWalletTransaction.objects.filter(reference_id=f"FAIL_{withdrawal.id}").exists()
        )

    def test_admin_withdrawal_fail_reverses_balance(self):
        """When a PROCESSING withdrawal fails, balance is correctly reversed exactly once."""
        wallet = EmployeeWallet.objects.create(
            employee=self.emp_tech,
            company=self.company_a,
            available_balance=Decimal("500.00"),
            total_withdrawn=Decimal("500.00"),
            currency="INR",
            status=WALLET_ACTIVE,
        )
        withdrawal = EmployeeWalletWithdrawal.objects.create(
            wallet=wallet,
            employee=self.emp_tech,
            amount=Decimal("500.00"),
            status=WITHDRAWAL_PROCESSING,
        )

        req_fail = self.factory.post(
            f"/api/workforce/admin/wallet/withdrawals/{withdrawal.id}/fail/",
            {"failure_reason": "Invalid account number"},
            format="json",
        )
        force_authenticate(req_fail, user=self.vendor_admin_a)
        res_fail = AdminWithdrawalFailView.as_view()(req_fail, pk=withdrawal.id)
        self.assertEqual(res_fail.status_code, status.HTTP_200_OK)

        withdrawal.refresh_from_db()
        wallet.refresh_from_db()
        self.assertEqual(withdrawal.status, WITHDRAWAL_FAILED)
        self.assertEqual(wallet.available_balance, Decimal("1000.00"))

        # Subsequent attempt to complete failed withdrawal must be rejected with 409:
        req_complete = self.factory.post(
            f"/api/workforce/admin/wallet/withdrawals/{withdrawal.id}/complete/",
            {"bank_transaction_id": "BANK-UTR-000"},
            format="json",
        )
        force_authenticate(req_complete, user=self.vendor_admin_a)
        res_comp = AdminWithdrawalCompleteView.as_view()(req_complete, pk=withdrawal.id)
        self.assertEqual(res_comp.status_code, status.HTTP_409_CONFLICT)


if __name__ == "__main__":
    unittest.main()

