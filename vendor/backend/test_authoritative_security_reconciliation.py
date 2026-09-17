"""
test_authoritative_security_reconciliation.py

Comprehensive security, tenant isolation, and read-only /auth/me test suite:
1. Social Security Tenant Isolation:
   - WorkforceAdminSocialSecurityListView (Vendor-scoped vs Platform-wide)
   - WorkforceAdminSocialSecurityMarkRegisteredView (Same-tenant allowed, cross-tenant 403, superadmin platform-wide)
2. Cash Tenant Isolation:
   - AdminCashOutstandingView (Pre-auth tenant ownership check, cross-tenant 403)
   - AdminCashSettlementView (GET and POST tenant ownership verification, cross-tenant 403)
3. Read-Only /auth/me Idempotency:
   - Employee belongs to Vendor A -> company remains Vendor A across GET /auth/me
   - No company detachment
   - No user.company mutation
   - No unexpected WalletAccount or EmployeeWallet creation
4. Explicit Lifecycle & Wallet Provisioning:
   - Wallet provisioning occurs on explicit lifecycle events (finalize_relieving, untie_technician, signup)
   - GET /auth/me is purely read-only and idempotent
5. Cross-Tenant ID Rejection Permutations:
   - Vendor A Admin + Vendor B Employee ID -> 403
   - Vendor B Admin + Vendor A Employee ID -> 403
   - Vendor A Admin + Vendor B Registration ID -> 403
   - Vendor B Admin + Vendor A Registration ID -> 403
"""

import os
import sys
import django
from decimal import Decimal

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
os.environ["CACHE_URL"] = "locmem://workforce-test-cache"
django.setup()

import unittest
from datetime import date
from django.utils import timezone
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from companies.models import Company, Region
from employees.models import Employee
from accounts.views import MeView
from workforce_api.models import (
    SocialSecurityRegistration,
    VendorTechnicianRelationship,
    VendorRelievingRequest,
    WalletAccount,
)
from workforce_api.views import (
    WorkforceAdminSocialSecurityListView,
    WorkforceAdminSocialSecurityMarkRegisteredView,
    AdminCashOutstandingView,
    AdminCashSettlementView,
)
from workforce_api.services.vendor_network import (
    VendorInvitationService,
    VendorRelationshipService,
    VendorRelievingService,
)

@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
)
class TestAuthoritativeSecurityReconciliation(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.factory = APIRequestFactory()

        # 1. Regions and Companies
        cls.region, _ = Region.objects.get_or_create(
            code="IN", defaults={"name": "India", "currency": "INR"}
        )

        cls.platform_company, _ = Company.objects.get_or_create(
            slug="calservices-platform",
            defaults={"company_name": "CalServices Central", "is_active": True, "region": cls.region},
        )

        cls.vendor_a, _ = Company.objects.get_or_create(
            slug="sec-vendor-a",
            defaults={"company_name": "Vendor A Services", "is_active": True, "region": cls.region},
        )

        cls.vendor_b, _ = Company.objects.get_or_create(
            slug="sec-vendor-b",
            defaults={"company_name": "Vendor B Logistics", "is_active": True, "region": cls.region},
        )

        # 2. Users: Vendor A Admin, Vendor B Admin, Platform Superadmin
        cls.admin_a, _ = User.objects.get_or_create(
            username="sec_admin_a",
            defaults={
                "email": "admin_a@vendor.test",
                "role": "admin",
                "company": cls.vendor_a,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        cls.admin_a.company = cls.vendor_a
        cls.admin_a.role = "admin"
        cls.admin_a.is_superuser = False
        cls.admin_a.save()

        cls.admin_b, _ = User.objects.get_or_create(
            username="sec_admin_b",
            defaults={
                "email": "admin_b@vendor.test",
                "role": "admin",
                "company": cls.vendor_b,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        cls.admin_b.company = cls.vendor_b
        cls.admin_b.role = "admin"
        cls.admin_b.is_superuser = False
        cls.admin_b.save()

        cls.superadmin, _ = User.objects.get_or_create(
            username="sec_superadmin",
            defaults={
                "email": "superadmin@platform.test",
                "role": "superadmin",
                "is_superuser": True,
                "is_staff": True,
            },
        )
        cls.superadmin.is_superuser = True
        cls.superadmin.is_staff = True
        cls.superadmin.save()

        # 3. Employees: Employee A (Vendor A), Employee B (Vendor B)
        cls.user_emp_a, _ = User.objects.get_or_create(
            username="sec_worker_a",
            defaults={
                "email": "worker_a@vendor.test",
                "role": "employee",
                "company": cls.vendor_a,
            },
        )
        cls.user_emp_a.company = cls.vendor_a
        cls.user_emp_a.save()

        cls.emp_a, _ = Employee.objects.get_or_create(
            user=cls.user_emp_a,
            defaults={
                "company": cls.vendor_a,
                "employee_id": "EMP-SEC-A-001",
                "title": "Technician A",
            },
        )
        cls.emp_a.company = cls.vendor_a
        cls.emp_a.save()

        cls.user_emp_b, _ = User.objects.get_or_create(
            username="sec_worker_b",
            defaults={
                "email": "worker_b@vendor.test",
                "role": "employee",
                "company": cls.vendor_b,
            },
        )
        cls.user_emp_b.company = cls.vendor_b
        cls.user_emp_b.save()

        cls.emp_b, _ = Employee.objects.get_or_create(
            user=cls.user_emp_b,
            defaults={
                "company": cls.vendor_b,
                "employee_id": "EMP-SEC-B-001",
                "title": "Technician B",
            },
        )
        cls.emp_b.company = cls.vendor_b
        cls.emp_b.save()

        # 4. Social Security Registrations
        cls.ss_reg_a, _ = SocialSecurityRegistration.objects.update_or_create(
            employee=cls.emp_a,
            defaults={
                "days_worked_current_fy": 95,
                "financial_year_start": date(2026, 4, 1),
                "status": SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION,
            },
        )

        cls.ss_reg_b, _ = SocialSecurityRegistration.objects.update_or_create(
            employee=cls.emp_b,
            defaults={
                "days_worked_current_fy": 110,
                "financial_year_start": date(2026, 4, 1),
                "status": SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION,
            },
        )

    def setUp(self):
        # Reset registration statuses for predictable test executions
        self.ss_reg_a.status = SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION
        self.ss_reg_a.save()
        self.ss_reg_b.status = SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION
        self.ss_reg_b.save()

    # =========================================================================
    # FIX 1: SOCIAL SECURITY TENANT ISOLATION TESTS
    # =========================================================================

    def test_social_security_list_vendor_a_sees_only_own(self):
        """Vendor A admin only sees SocialSecurityRegistration for Vendor A employees."""
        req = self.factory.get("/workforce/admin/social-security/")
        force_authenticate(req, user=self.admin_a)
        resp = WorkforceAdminSocialSecurityListView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        returned_ids = [item["registration_id"] for item in resp.data["results"]]
        self.assertIn(self.ss_reg_a.id, returned_ids)
        self.assertNotIn(self.ss_reg_b.id, returned_ids)

    def test_social_security_list_vendor_b_sees_only_own(self):
        """Vendor B admin only sees SocialSecurityRegistration for Vendor B employees."""
        req = self.factory.get("/workforce/admin/social-security/")
        force_authenticate(req, user=self.admin_b)
        resp = WorkforceAdminSocialSecurityListView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        returned_ids = [item["registration_id"] for item in resp.data["results"]]
        self.assertIn(self.ss_reg_b.id, returned_ids)
        self.assertNotIn(self.ss_reg_a.id, returned_ids)

    def test_social_security_list_platform_superadmin_sees_all(self):
        """Platform Superadmin has legitimate platform-wide visibility."""
        req = self.factory.get("/workforce/admin/social-security/")
        force_authenticate(req, user=self.superadmin)
        resp = WorkforceAdminSocialSecurityListView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        returned_ids = [item["registration_id"] for item in resp.data["results"]]
        self.assertIn(self.ss_reg_a.id, returned_ids)
        self.assertIn(self.ss_reg_b.id, returned_ids)

    def test_social_security_mark_registered_same_company_allowed(self):
        """Vendor A admin can mark their own employee's registration as registered."""
        req = self.factory.post(
            "/workforce/admin/social-security/mark-registered/",
            {"registration_id": self.ss_reg_a.id, "portal_reference_id": "REF-VENDOR-A-001"},
            format="json",
        )
        force_authenticate(req, user=self.admin_a)
        resp = WorkforceAdminSocialSecurityMarkRegisteredView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.ss_reg_a.refresh_from_db()
        self.assertEqual(
            self.ss_reg_a.status,
            SocialSecurityRegistration.RegistrationStatus.REGISTERED,
        )
        self.assertEqual(self.ss_reg_a.portal_reference_id, "REF-VENDOR-A-001")

    def test_social_security_mark_registered_cross_company_rejected(self):
        """Vendor A admin attempting to mark Vendor B employee's registration is rejected with 403."""
        req = self.factory.post(
            "/workforce/admin/social-security/mark-registered/",
            {"registration_id": self.ss_reg_b.id, "portal_reference_id": "HACK-REF-001"},
            format="json",
        )
        force_authenticate(req, user=self.admin_a)
        resp = WorkforceAdminSocialSecurityMarkRegisteredView.as_view()(req)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "FORBIDDEN")
        # Ensure Vendor B data remains unaffected
        self.ss_reg_b.refresh_from_db()
        self.assertEqual(
            self.ss_reg_b.status,
            SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION,
        )

    def test_social_security_mark_registered_vendor_b_on_a_rejected(self):
        """Vendor B admin attempting to mark Vendor A employee's registration is rejected with 403."""
        req = self.factory.post(
            "/workforce/admin/social-security/mark-registered/",
            {"registration_id": self.ss_reg_a.id, "portal_reference_id": "HACK-REF-002"},
            format="json",
        )
        force_authenticate(req, user=self.admin_b)
        resp = WorkforceAdminSocialSecurityMarkRegisteredView.as_view()(req)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "FORBIDDEN")

    def test_social_security_mark_registered_superadmin_allowed(self):
        """Platform Superadmin can mark any company's registration as registered."""
        req = self.factory.post(
            "/workforce/admin/social-security/mark-registered/",
            {"registration_id": self.ss_reg_b.id, "portal_reference_id": "SEVO-GOV-CENTRAL-001"},
            format="json",
        )
        force_authenticate(req, user=self.superadmin)
        resp = WorkforceAdminSocialSecurityMarkRegisteredView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.ss_reg_b.refresh_from_db()
        self.assertEqual(
            self.ss_reg_b.status,
            SocialSecurityRegistration.RegistrationStatus.REGISTERED,
        )

    # =========================================================================
    # FIX 2: CASH TENANT ISOLATION TESTS
    # =========================================================================

    def test_cash_outstanding_vendor_a_inspects_own_allowed(self):
        """Vendor A admin can inspect cash outstanding for Vendor A employee."""
        req = self.factory.get(f"/workforce/admin/cash/outstanding/{self.emp_a.id}/")
        force_authenticate(req, user=self.admin_a)
        resp = AdminCashOutstandingView.as_view()(req, employee_id=self.emp_a.id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["employee_id"], self.emp_a.id)
        self.assertIn("outstanding_amount", resp.data)

    def test_cash_outstanding_vendor_a_inspects_vendor_b_rejected(self):
        """Vendor A admin cannot inspect cash outstanding for Vendor B employee (403)."""
        req = self.factory.get(f"/workforce/admin/cash/outstanding/{self.emp_b.id}/")
        force_authenticate(req, user=self.admin_a)
        resp = AdminCashOutstandingView.as_view()(req, employee_id=self.emp_b.id)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "FORBIDDEN")

    def test_cash_outstanding_vendor_b_inspects_vendor_a_rejected(self):
        """Vendor B admin cannot inspect cash outstanding for Vendor A employee (403)."""
        req = self.factory.get(f"/workforce/admin/cash/outstanding/{self.emp_a.id}/")
        force_authenticate(req, user=self.admin_b)
        resp = AdminCashOutstandingView.as_view()(req, employee_id=self.emp_a.id)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "FORBIDDEN")

    def test_cash_outstanding_superadmin_allowed(self):
        """Platform Superadmin can inspect cash outstanding for any employee."""
        req = self.factory.get(f"/workforce/admin/cash/outstanding/{self.emp_b.id}/")
        force_authenticate(req, user=self.superadmin)
        resp = AdminCashOutstandingView.as_view()(req, employee_id=self.emp_b.id)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["employee_id"], self.emp_b.id)

    def test_cash_settlement_vendor_a_settles_own_allowed(self):
        """Vendor A admin can record cash settlement for Vendor A employee."""
        req = self.factory.post(
            "/workforce/admin/cash/settlements/",
            {"employee_id": self.emp_a.id, "deposited_amount": "500.00", "notes": "Vendor A daily cash settle"},
            format="json",
        )
        force_authenticate(req, user=self.admin_a)
        resp = AdminCashSettlementView.as_view()(req)

        self.assertEqual(resp.status_code, 201)
        self.assertIn("id", resp.data)
        self.assertEqual(resp.data["deposited_amount"], "500.00")

    def test_cash_settlement_vendor_a_settles_vendor_b_rejected(self):
        """Vendor A admin cannot record cash settlement for Vendor B employee (403)."""
        req = self.factory.post(
            "/workforce/admin/cash/settlements/",
            {"employee_id": self.emp_b.id, "deposited_amount": "500.00", "notes": "Cross-company settlement attempt"},
            format="json",
        )
        force_authenticate(req, user=self.admin_a)
        resp = AdminCashSettlementView.as_view()(req)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "FORBIDDEN")

    def test_cash_settlement_vendor_b_settles_vendor_a_rejected(self):
        """Vendor B admin cannot record cash settlement for Vendor A employee (403)."""
        req = self.factory.post(
            "/workforce/admin/cash/settlements/",
            {"employee_id": self.emp_a.id, "deposited_amount": "300.00"},
            format="json",
        )
        force_authenticate(req, user=self.admin_b)
        resp = AdminCashSettlementView.as_view()(req)

        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.data.get("code"), "FORBIDDEN")

    def test_cash_settlement_superadmin_allowed(self):
        """Platform superadmin can record cash settlement across companies."""
        req = self.factory.post(
            "/workforce/admin/cash/settlements/",
            {"employee_id": self.emp_b.id, "deposited_amount": "250.00", "notes": "Superadmin audit settle"},
            format="json",
        )
        force_authenticate(req, user=self.superadmin)
        resp = AdminCashSettlementView.as_view()(req)

        self.assertEqual(resp.status_code, 201)
        self.assertIn("id", resp.data)
        self.assertEqual(resp.data["deposited_amount"], "250.00")

    # =========================================================================
    # FIX 3: /AUTH/ME READ-ONLY & IDEMPOTENCY TESTS
    # =========================================================================

    def test_auth_me_read_only_employee_belongs_to_vendor_a(self):
        """
        Employee belongs to Vendor A:
        Calling GET /auth/me must:
        - Succeed with 200
        - Report company as Vendor A
        - Retain employee.company and user.company as Vendor A
        - NOT detach company
        - NOT create any financial or wallet records
        """
        # Ensure clean initial state
        self.emp_a.company = self.vendor_a
        self.emp_a.save()
        self.user_emp_a.company = self.vendor_a
        self.user_emp_a.save()

        initial_wallet_count = WalletAccount.objects.filter(employee=self.emp_a).count()

        req = self.factory.get("/api/auth/me/")
        force_authenticate(req, user=self.user_emp_a)
        resp = MeView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["company"], self.vendor_a.id)
        self.assertEqual(resp.data["company_name"], self.vendor_a.company_name)
        self.assertTrue(resp.data["is_tied_worker"])
        self.assertFalse(resp.data["is_solo_worker"])

        # Verify DB is completely unmutated
        self.emp_a.refresh_from_db()
        self.assertEqual(self.emp_a.company_id, self.vendor_a.id)

        self.user_emp_a.refresh_from_db()
        self.assertEqual(self.user_emp_a.company_id, self.vendor_a.id)

        # Verify no wallet records were created by GET /auth/me
        new_wallet_count = WalletAccount.objects.filter(employee=self.emp_a).count()
        self.assertEqual(new_wallet_count, initial_wallet_count)

    def test_auth_me_no_active_relationship_does_not_detach_company(self):
        """
        An employee has company = Vendor A, but no active VendorTechnicianRelationship.
        Calling GET /auth/me must NOT mutate employee.company or user.company to None.
        """
        # Ensure no active relationship exists for emp_a
        VendorTechnicianRelationship.objects.filter(technician=self.emp_a).delete()

        self.emp_a.company = self.vendor_a
        self.emp_a.save()
        self.user_emp_a.company = self.vendor_a
        self.user_emp_a.save()

        req = self.factory.get("/api/auth/me/")
        force_authenticate(req, user=self.user_emp_a)
        resp = MeView.as_view()(req)

        self.assertEqual(resp.status_code, 200)

        # Crucial check: employee company must REMAIN Vendor A
        self.emp_a.refresh_from_db()
        self.assertEqual(self.emp_a.company_id, self.vendor_a.id)

        self.user_emp_a.refresh_from_db()
        self.assertEqual(self.user_emp_a.company_id, self.vendor_a.id)

    def test_auth_me_idempotency_multiple_calls(self):
        """Calling GET /auth/me 5 times in succession produces identical responses and zero mutations."""
        req1 = self.factory.get("/api/auth/me/")
        force_authenticate(req1, user=self.user_emp_a)
        resp1 = MeView.as_view()(req1)

        for _ in range(4):
            req = self.factory.get("/api/auth/me/")
            force_authenticate(req, user=self.user_emp_a)
            resp = MeView.as_view()(req)
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.data["company"], resp1.data["company"])
            self.assertEqual(resp.data["is_tied_worker"], resp1.data["is_tied_worker"])
            self.assertEqual(resp.data["is_solo_worker"], resp1.data["is_solo_worker"])

        self.emp_a.refresh_from_db()
        self.assertEqual(self.emp_a.company_id, self.vendor_a.id)

    def test_auth_me_solo_worker_profile(self):
        """Solo worker without company correctly reports is_solo_worker=True without DB side effects."""
        solo_user, _ = User.objects.get_or_create(
            username="sec_solo_tech_001",
            defaults={"email": "solo@freelance.test", "role": "employee", "company": None},
        )
        solo_user.company = None
        solo_user.save()

        solo_emp, _ = Employee.objects.get_or_create(
            user=solo_user,
            defaults={"company": None, "employee_id": "EMP-SOLO-001", "title": "Freelance AC Tech"},
        )
        solo_emp.company = None
        solo_emp.save()

        req = self.factory.get("/api/auth/me/")
        force_authenticate(req, user=solo_user)
        resp = MeView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertIsNone(resp.data["company"])
        self.assertFalse(resp.data["is_tied_worker"])
        self.assertTrue(resp.data["is_solo_worker"])

    # =========================================================================
    # WALLET PROVISIONING & EXPLICIT LIFECYCLE TESTS
    # =========================================================================

    def test_wallet_provisioning_on_relieving_lifecycle(self):
        """
        Wallet provisioning must happen at the explicit lifecycle point:
        VendorRelievingService.finalize_relieving.
        NOT during GET /auth/me.
        """
        # Create dedicated tech for relieving flow
        user_relieve, _ = User.objects.get_or_create(
            username="sec_worker_relieve",
            defaults={"email": "relieve_worker@vendor.test", "role": "employee", "company": self.vendor_a},
        )
        user_relieve.company = self.vendor_a
        user_relieve.save()

        emp_relieve, _ = Employee.objects.get_or_create(
            user=user_relieve,
            defaults={"company": self.vendor_a, "employee_id": "EMP-RELIEVE-TEST", "title": "Tech"},
        )
        emp_relieve.company = self.vendor_a
        emp_relieve.save()

        # Delete any pre-existing wallet
        WalletAccount.objects.filter(employee=emp_relieve).delete()

        # Create active relationship
        rel, _ = VendorTechnicianRelationship.objects.get_or_create(
            vendor=self.vendor_a,
            technician=emp_relieve,
            defaults={"status": VendorTechnicianRelationship.Status.ACTIVE},
        )
        rel.status = VendorTechnicianRelationship.Status.ACTIVE
        rel.save()

        # Calling GET /auth/me BEFORE relieving must NOT create a wallet
        req_before = self.factory.get("/api/auth/me/")
        force_authenticate(req_before, user=user_relieve)
        MeView.as_view()(req_before)

        has_wallet_before = WalletAccount.objects.filter(
            employee=emp_relieve, account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER
        ).exists()
        self.assertFalse(has_wallet_before, "GET /auth/me must not create a wallet!")

        # Execute formal relieving lifecycle
        req_resig = VendorRelievingService.submit_resignation(
            employee=emp_relieve,
            reason_category=VendorRelievingRequest.ReasonCategory.TRANSITION_TO_SOLO,
            notes="Formal resignation",
        )
        VendorRelievingService.vendor_approve_relieving(
            request_id=req_resig.id,
            vendor=self.vendor_a,
            settlement_notes="Cleared",
            actor=self.admin_a,
        )
        VendorRelievingService.sevo_approve_relieving(
            request_id=req_resig.id,
            audit_notes="Approved by SEVO audit",
            actor=self.superadmin,
        )

        # Now worker is relieved, unlinked, and wallet is provisioned by the lifecycle!
        emp_relieve.refresh_from_db()
        self.assertIsNone(emp_relieve.company_id)

        has_wallet_after = WalletAccount.objects.filter(
            employee=emp_relieve, account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER
        ).exists()
        self.assertTrue(has_wallet_after, "Relieving lifecycle must provision the solo worker wallet!")

    def test_wallet_provisioning_on_untie_technician(self):
        """VendorRelationshipService.untie_technician unlinks worker and provisions wallet."""
        user_untie, _ = User.objects.get_or_create(
            username="sec_worker_untie",
            defaults={"email": "untie_worker@vendor.test", "role": "employee", "company": self.vendor_b},
        )
        emp_untie, _ = Employee.objects.get_or_create(
            user=user_untie,
            defaults={"company": self.vendor_b, "employee_id": "EMP-UNTIE-TEST", "title": "Tech"},
        )
        WalletAccount.objects.filter(employee=emp_untie).delete()

        rel, _ = VendorTechnicianRelationship.objects.get_or_create(
            vendor=self.vendor_b,
            technician=emp_untie,
            defaults={"status": VendorTechnicianRelationship.Status.ACTIVE},
        )
        rel.status = VendorTechnicianRelationship.Status.ACTIVE
        rel.save()

        # Execute untie
        VendorRelationshipService.untie_technician(employee_id=emp_untie.id, actor=self.superadmin)

        emp_untie.refresh_from_db()
        self.assertIsNone(emp_untie.company_id)

        wallet_created = WalletAccount.objects.filter(
            employee=emp_untie, account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER
        ).exists()
        self.assertTrue(wallet_created, "untie_technician must provision solo worker wallet!")


if __name__ == "__main__":
    unittest.main()
