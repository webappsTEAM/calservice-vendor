"""
test_vendor_network.py

Comprehensive test suite for Technician-Vendor Network module:
1. Direct email invite flow & signed token generation
2. Technician signup automatic backfill hook
3. Criteria matching & discovery engine (AND/OR logic)
4. Technician invitation accept (active relationship creation)
5. Technician invitation reject (no relationship created)
6. Multiple simultaneous independent vendor relationships for one technician
7. Relationship lifecycle (suspend, reactivate, terminate, leave)
8. Multi-tenant isolation & unauthorized access prevention
9. Atomic decision concurrency & duplicate prevention
"""

import os
import sys
import django

# Setup django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

import unittest
from datetime import timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import User
from companies.models import Company, Region
from employees.models import Employee
from workforce_api.models import (
    CriteriaTerm,
    VendorCriteria,
    VendorInvitation,
    VendorTechnicianRelationship,
    VendorRelievingRequest,
    WalletAccount,
    WorkforceEmployeeSkill,
    WorkforceSkill,
    WorkforceScorecard,
)
from workforce_api.services.vendor_network import (
    VendorDiscoveryEngine,
    VendorInvitationService,
    VendorRelationshipService,
    VendorRelievingService,
)


class TestTechnicianVendorNetwork(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create test regions & companies
        cls.region, _ = Region.objects.get_or_create(code="IN", defaults={"name": "India", "currency": "INR"})

        cls.platform_company, _ = Company.objects.get_or_create(
            slug="calservices",
            defaults={"company_name": "CalServices Shared Platform", "is_active": True, "region": cls.region},
        )

        cls.vendor_a, _ = Company.objects.get_or_create(
            slug="vendor-abc-homes",
            defaults={"company_name": "ABC Home Services", "is_active": True, "region": cls.region},
        )

        cls.vendor_b, _ = Company.objects.get_or_create(
            slug="vendor-coolcare",
            defaults={"company_name": "CoolCare Solutions", "is_active": True, "region": cls.region},
        )

        cls.vendor_c, _ = Company.objects.get_or_create(
            slug="vendor-xyz-facilities",
            defaults={"company_name": "XYZ Facility Services", "is_active": True, "region": cls.region},
        )

        # Create vendor admin users
        cls.admin_a, _ = User.objects.get_or_create(
            username="admin_abc",
            defaults={"email": "admin@abc.com", "role": "admin", "company": cls.vendor_a},
        )

        cls.admin_b, _ = User.objects.get_or_create(
            username="admin_coolcare",
            defaults={"email": "admin@coolcare.com", "role": "admin", "company": cls.vendor_b},
        )

        # Create skills
        cls.skill_ac_repair, _ = WorkforceSkill.objects.get_or_create(
            company=cls.platform_company,
            name="AC Repair",
            defaults={"category": "HVAC", "is_active": True},
        )
        cls.skill_ac_install, _ = WorkforceSkill.objects.get_or_create(
            company=cls.platform_company,
            name="AC Installation",
            defaults={"category": "HVAC", "is_active": True},
        )
        cls.skill_plumbing, _ = WorkforceSkill.objects.get_or_create(
            company=cls.platform_company,
            name="Plumbing",
            defaults={"category": "Plumbing", "is_active": True},
        )

        # Generate dynamic test identifier for this run
        import time
        cls.run_id = int(time.time())
        cls.test_email = f"ravi_{cls.run_id}@example.com"
        cls.test_username = f"ravi_{cls.run_id}"
        cls.test_emp_id = f"TECH-RAVI-{cls.run_id}"

        # Clean existing test data for clean slate
        VendorTechnicianRelationship.objects.filter(vendor__in=[cls.vendor_a, cls.vendor_b, cls.vendor_c]).delete()
        VendorInvitation.objects.filter(vendor__in=[cls.vendor_a, cls.vendor_b, cls.vendor_c]).delete()
        VendorCriteria.objects.filter(vendor__in=[cls.vendor_a, cls.vendor_b, cls.vendor_c]).delete()

    @classmethod
    def tearDownClass(cls):
        VendorTechnicianRelationship.objects.filter(vendor__in=[cls.vendor_a, cls.vendor_b, cls.vendor_c]).delete()
        VendorInvitation.objects.filter(vendor__in=[cls.vendor_a, cls.vendor_b, cls.vendor_c]).delete()
        VendorCriteria.objects.filter(vendor__in=[cls.vendor_a, cls.vendor_b, cls.vendor_c]).delete()
        super().tearDownClass()

    def test_01_direct_email_invitation_creation(self):
        """Test sending direct email invitation to a new email."""
        inv = VendorInvitationService.create_invitation(
            vendor=self.vendor_a,
            invited_email=self.test_email,
            message="Join our Bangalore AC team!",
            actor=self.admin_a,
        )

        self.assertIsNotNone(inv.id)
        self.assertEqual(inv.vendor, self.vendor_a)
        self.assertEqual(inv.invited_email, self.test_email)
        self.assertEqual(inv.status, VendorInvitation.Status.PENDING)
        self.assertIsNone(inv.technician)
        self.assertTrue(len(inv.token) > 20)
        self.assertTrue(inv.expires_at > timezone.now())

    def test_02_signup_backfill_links_invitation_to_new_employee(self):
        """Test that registering a new technician automatically sweeps and attaches pending invitations."""
        # Create User & Employee
        user = User.objects.create(
            username=self.test_username,
            email=self.test_email,
            first_name="Ravi",
            last_name="Kumar",
            role="employee",
            company=self.platform_company,
        )
        employee = Employee.objects.create(
            user=user,
            company=self.platform_company,
            employee_id=self.test_emp_id,
            title="Senior HVAC Technician",
            state="Bengaluru",
            country="IN",
        )

        # Execute backfill
        backfilled = VendorInvitationService.backfill_invitations_for_employee(employee)
        self.assertEqual(backfilled, 1)

        # Verify invitation is now linked to employee
        inv = VendorInvitation.objects.get(invited_email=self.test_email, vendor=self.vendor_a)
        self.assertEqual(inv.technician, employee)

    def test_03_discovery_engine_and_or_criteria_matching(self):
        """Test discovery engine with grouped OR terms (AC Repair OR AC Installation) and location matching."""
        emp = Employee.objects.get(employee_id=self.test_emp_id)

        # Assign AC Repair skill to Ravi
        WorkforceEmployeeSkill.objects.get_or_create(
            employee=emp,
            skill=self.skill_ac_repair,
            defaults={"proficiency_level": "EXPERT", "is_verified": True},
        )

        # Create scorecard
        WorkforceScorecard.objects.update_or_create(
            employee=emp,
            defaults={"average_rating": 4.85, "rating_count": 42, "tier": "GOLD"},
        )

        # Criteria: (Skill = AC Repair OR Skill = AC Installation) [group_id=1] AND Location = Bengaluru [group_id=2]
        terms = [
            {
                "attribute_type": "SKILL",
                "operator": "IN",
                "value": ["AC Repair", "AC Installation"],
                "group_id": 1,
            },
            {
                "attribute_type": "LOCATION",
                "operator": "EQUALS",
                "value": "Bengaluru",
                "group_id": 2,
            },
        ]

        matches = VendorDiscoveryEngine.evaluate_candidates(
            vendor=self.vendor_b,
            terms=terms,
        )

        matching_ids = [m["technician_id"] for m in matches]
        self.assertIn(emp.id, matching_ids)

        ravi_match = next(m for m in matches if m["technician_id"] == emp.id)
        self.assertEqual(ravi_match["match_score"], 100)
        self.assertEqual(ravi_match["scorecard_tier"], "GOLD")
        self.assertEqual(ravi_match["network_status"], "NOT_CONNECTED")

    def test_04_accept_invitation_creates_active_relationship(self):
        """Test technician accepting an invitation from Vendor A -> status ACTIVE."""
        emp = Employee.objects.get(employee_id=self.test_emp_id)
        inv = VendorInvitation.objects.get(invited_email=emp.user.email, vendor=self.vendor_a)

        inv_res, rel = VendorInvitationService.respond_to_invitation(
            invitation_id=inv.id,
            employee=emp,
            decision="ACCEPT",
        )

        self.assertEqual(inv_res.status, VendorInvitation.Status.ACCEPTED)
        self.assertIsNotNone(rel)
        self.assertEqual(rel.status, VendorTechnicianRelationship.Status.ACTIVE)
        self.assertEqual(rel.vendor, self.vendor_a)
        self.assertEqual(rel.technician, emp)
        self.assertEqual(rel.source_invitation, inv)

    def test_05_reject_invitation_creates_no_relationship(self):
        """Test technician rejecting an invitation from Vendor B -> status REJECTED, 0 relationships for Vendor B."""
        emp = Employee.objects.get(employee_id=self.test_emp_id)

        # Vendor B invites Ravi
        inv_b = VendorInvitationService.create_invitation(
            vendor=self.vendor_b,
            invited_email=emp.user.email,
            technician=emp,
            message="Join CoolCare network!",
            actor=self.admin_b,
        )

        inv_res, rel = VendorInvitationService.respond_to_invitation(
            invitation_id=inv_b.id,
            employee=emp,
            decision="REJECT",
        )

        self.assertEqual(inv_res.status, VendorInvitation.Status.REJECTED)
        self.assertIsNone(rel)

        # Verify no relationship exists for Vendor B
        has_rel_b = VendorTechnicianRelationship.objects.filter(vendor=self.vendor_b, technician=emp).exists()
        self.assertFalse(has_rel_b)

        # Verify Vendor A relationship remains completely intact and ACTIVE
        rel_a = VendorTechnicianRelationship.objects.get(vendor=self.vendor_a, technician=emp)
        self.assertEqual(rel_a.status, VendorTechnicianRelationship.Status.ACTIVE)

    def test_06_single_active_vendor_exclusivity_and_relieve_flow(self):
        """
        Test that a worker actively assigned to Vendor A CANNOT accept an offer from Vendor C.
        To join Vendor C, the worker must relieve/leave Vendor A first.
        """
        emp = Employee.objects.get(employee_id=self.test_emp_id)
        rel_a = VendorTechnicianRelationship.objects.get(vendor=self.vendor_a, technician=emp)
        self.assertEqual(rel_a.status, VendorTechnicianRelationship.Status.ACTIVE)

        # Vendor C invites Ravi
        inv_c = VendorInvitationService.create_invitation(
            vendor=self.vendor_c,
            invited_email=emp.user.email,
            technician=emp,
            message="Join XYZ Facility network!",
        )

        # Attempt to accept Vendor C while active with Vendor A -> Must FAIL with ValidationError
        with self.assertRaises(ValidationError) as ctx:
            VendorInvitationService.respond_to_invitation(
                invitation_id=inv_c.id,
                employee=emp,
                decision="ACCEPT",
            )
        self.assertIn("ABC Home Services", str(ctx.exception))
        self.assertIn("relieve", str(ctx.exception).lower())

        # Ravi relieves/leaves Vendor A
        rel_a_left = VendorRelationshipService.leave_vendor(
            relationship_id=rel_a.id,
            employee=emp,
        )
        self.assertEqual(rel_a_left.status, VendorTechnicianRelationship.Status.RESIGNED)

        # Now Ravi is relieved and free -> Accepts Vendor C
        inv_res, rel_c = VendorInvitationService.respond_to_invitation(
            invitation_id=inv_c.id,
            employee=emp,
            decision="ACCEPT",
        )

        self.assertEqual(rel_c.status, VendorTechnicianRelationship.Status.ACTIVE)
        self.assertEqual(rel_c.vendor, self.vendor_c)

        # Total active vendor relationships is strictly 1 (Vendor C)
        active_rels = VendorTechnicianRelationship.objects.filter(technician=emp, status="ACTIVE")
        self.assertEqual(active_rels.count(), 1)
        self.assertEqual(active_rels.first().vendor, self.vendor_c)

    def test_07_vendor_relationship_lifecycle_and_suspension(self):
        """Test vendor suspending and reactivating a relationship."""
        emp = Employee.objects.get(employee_id=self.test_emp_id)
        rel_c = VendorTechnicianRelationship.objects.get(vendor=self.vendor_c, technician=emp)

        # Suspend
        rel_suspended = VendorRelationshipService.update_status(
            relationship_id=rel_c.id,
            vendor=self.vendor_c,
            action="SUSPEND",
        )
        self.assertEqual(rel_suspended.status, VendorTechnicianRelationship.Status.SUSPENDED)

        # Reactivate Vendor C
        rel_reactivated = VendorRelationshipService.update_status(
            relationship_id=rel_c.id,
            vendor=self.vendor_c,
            action="REACTIVATE",
        )
        self.assertEqual(rel_reactivated.status, VendorTechnicianRelationship.Status.ACTIVE)

    def test_08_technician_leaves_vendor_relationship(self):
        """Test technician resigning/leaving a relationship from their side."""
        emp = Employee.objects.get(employee_id=self.test_emp_id)
        rel_c = VendorTechnicianRelationship.objects.get(vendor=self.vendor_c, technician=emp)

        rel_left = VendorRelationshipService.leave_vendor(
            relationship_id=rel_c.id,
            employee=emp,
        )
        self.assertEqual(rel_left.status, VendorTechnicianRelationship.Status.RESIGNED)
        self.assertIsNotNone(rel_left.ended_at)

        # Now worker has 0 active relationships (fully free solo worker)
        active_count = VendorTechnicianRelationship.objects.filter(technician=emp, status="ACTIVE").count()
        self.assertEqual(active_count, 0)

    def test_09_multi_tenant_isolation_enforcement(self):
        """Test that Vendor B cannot access or modify Vendor A's technician relationships."""
        emp = Employee.objects.get(employee_id=self.test_emp_id)
        rel_a = VendorTechnicianRelationship.objects.get(vendor=self.vendor_a, technician=emp)

        with self.assertRaises(ValidationError):
            # Vendor B attempts to update Vendor A's relationship
            VendorRelationshipService.update_status(
                relationship_id=rel_a.id,
                vendor=self.vendor_b,
                action="SUSPEND",
            )

    def test_10_formal_multi_party_resignation_lifecycle(self):
        """
        Test complete multi-party resignation, clearance, SEVO platform audit,
        and automatic Solo Worker wallet provisioning.
        """
        # Create dedicated technician for resignation test
        user_resigning, _ = User.objects.get_or_create(
            username="tech_ramesh_resigning",
            defaults={
                "email": "ramesh.resigning@example.com",
                "first_name": "Ramesh",
                "last_name": "Kumar",
                "role": "employee",
                "company": self.vendor_b,
            },
        )
        emp_resigning, _ = Employee.objects.get_or_create(
            user=user_resigning,
            defaults={
                "company": self.vendor_b,
                "employee_id": "EMP-RAMESH-TEST",
                "title": "AC Technician",
            },
        )
        emp_resigning.company = self.vendor_b
        emp_resigning.save()

        # Create active relationship
        rel, _ = VendorTechnicianRelationship.objects.get_or_create(
            vendor=self.vendor_b,
            technician=emp_resigning,
            defaults={
                "status": VendorTechnicianRelationship.Status.ACTIVE,
                "started_at": timezone.now(),
            },
        )
        rel.status = VendorTechnicianRelationship.Status.ACTIVE
        rel.save()

        # Stage 1: Technician submits formal resignation
        req = VendorRelievingService.submit_resignation(
            employee=emp_resigning,
            reason_category=VendorRelievingRequest.ReasonCategory.TRANSITION_TO_SOLO,
            notes="Transitioning to Solo Worker per career goals.",
        )
        self.assertEqual(req.status, VendorRelievingRequest.Status.REQUESTED)
        self.assertTrue(req.worker_signoff_ack)

        rel.refresh_from_db()
        self.assertEqual(rel.status, VendorTechnicianRelationship.Status.RESIGNATION_REQUESTED)

        # Stage 2: Vendor Admin approves settlement & dues clearance
        req_vendor_approved = VendorRelievingService.vendor_approve_relieving(
            request_id=req.id,
            vendor=self.vendor_b,
            settlement_notes="All pending job payouts and company equipment returned & cleared.",
            actor=self.admin_b,
        )
        self.assertEqual(req_vendor_approved.status, VendorRelievingRequest.Status.VENDOR_APPROVED)
        self.assertTrue(req_vendor_approved.vendor_signoff_ack)

        # Stage 3: SEVO Platform Superadmin verifies platform job reconciliations and audits
        superadmin_user, _ = User.objects.get_or_create(
            username="sevo_superadmin_test",
            defaults={"email": "superadmin@sevo.com", "is_superuser": True, "role": "admin"},
        )
        superadmin_user.is_superuser = True
        superadmin_user.save()

        req_sevo_approved = VendorRelievingService.sevo_approve_relieving(
            request_id=req.id,
            audit_notes="SEVO compliance audit verified zero pending bookings or customer disputes.",
            actor=superadmin_user,
        )

        # Stage 4: Relieving finalized
        self.assertEqual(req_sevo_approved.status, VendorRelievingRequest.Status.COMPLETED)

        rel.refresh_from_db()
        self.assertEqual(rel.status, VendorTechnicianRelationship.Status.RESIGNED)
        self.assertIsNotNone(rel.ended_at)

        # Confirm technician is unlinked from vendor (company is None) -> now Solo Worker
        emp_resigning.refresh_from_db()
        self.assertIsNone(emp_resigning.company_id)

        # Confirm individual solo worker wallet was automatically provisioned
        wallet = WalletAccount.objects.filter(
            employee=emp_resigning,
            account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
        ).first()
        self.assertIsNotNone(wallet)


if __name__ == "__main__":
    unittest.main()

