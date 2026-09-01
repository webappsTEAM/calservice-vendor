"""
Workforce Phase 1 Verification Suite: Service Provider & Superadmin Foundation
Verifies all 13 architectural invariants (A through M) specified in Phase 1 requirements:

A. Existing superadmin login works.
B. SUPERADMIN can access:
   - independent employees
   - provider admins
   - provider employees
   - multiple providers
C. Provider Admin belongs to exactly one provider.
D. Provider Admin can access only their own provider.
E. Provider Admin cannot access:
   - another provider
   - independent employees
F. Independent employee can have company=NULL.
G. Provider employee can have company=<provider>.
H. Both employee types can log in through the same employee flow.
I. Existing Active Jobs behavior remains correct (explicit offer/assignment only; no company auto-visibility).
J. Existing dispatch behavior remains correct for:
   - independent employee
   - provider employee
   - Marketplace booking
   - provider booking
K. Existing onboarding remains functional.
L. Existing Admin functionality remains functional for SUPERADMIN.
M. Existing authentication/token refresh remains functional.
"""
import os
import sys
import uuid
from decimal import Decimal
import django

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from companies.models import Company
from employees.models import Employee
from accounts.models import User
from accounts.permissions import is_superadmin, is_service_provider_admin, is_workforce_admin, is_workforce_employee
from service_requests.models import ServiceRequest, EmployeeJob
from workforce_api.models import WorkforceJobOffer
from workforce_api.services.automatic_dispatch import get_booking_discovery_scope


def run_tests():
    client = APIClient()
    print("=" * 80)
    print("STARTING WORKFORCE PHASE 1 VERIFICATION SUITE")
    print("=" * 80)

    test_suffix = uuid.uuid4().hex[:6]

    # Use a transaction block that rolls back or clean up explicitly created records
    created_users = []
    created_employees = []
    created_companies = []
    created_jobs = []

    try:
        # Create test providers (companies)
        provider_a = Company.objects.create(
            company_name=f"Provider Alpha {test_suffix}",
            is_active=True,
        )
        created_companies.append(provider_a)

        provider_b = Company.objects.create(
            company_name=f"Provider Beta {test_suffix}",
            is_active=True,
        )
        created_companies.append(provider_b)

        # 1. Platform Superadmin User
        superadmin_user = User.objects.create_user(
            username=f"superadmin_{test_suffix}",
            email=f"superadmin_{test_suffix}@platform.com",
            password="StrongPassword123!",
            is_superuser=True,
            is_staff=True,
            role="superadmin",
        )
        created_users.append(superadmin_user)

        # 2. Service Provider Admin for Provider A
        provider_a_admin = User.objects.create_user(
            username=f"padmin_a_{test_suffix}",
            email=f"padmin_a_{test_suffix}@provider.com",
            password="StrongPassword123!",
            role="service_provider_admin",
            company=provider_a,
        )
        created_users.append(provider_a_admin)

        # 3. Independent Employee (company = NULL)
        indep_user = User.objects.create_user(
            username=f"indep_{test_suffix}",
            email=f"indep_{test_suffix}@tech.com",
            password="StrongPassword123!",
            role="employee",
        )
        created_users.append(indep_user)

        indep_emp = Employee.objects.create(
            user=indep_user,
            employee_id=f"IND-{test_suffix}",
            company=None,
            bank_details={
                "onboarding": {
                    "status": "approved",
                    "documents": {"id_proof": {"status": "approved"}},
                    "services": [
                        {"id": "svc_general", "name": "General Service", "status": "approved"},
                        {"id": "svc_ac", "name": "AC Repair", "status": "approved"},
                    ]
                }
            },
            is_active=True,
            is_online=True,
        )
        created_employees.append(indep_emp)

        # 4. Provider Employee (company = Provider A)
        prov_user = User.objects.create_user(
            username=f"prov_{test_suffix}",
            email=f"prov_{test_suffix}@alpha.com",
            password="StrongPassword123!",
            role="employee",
            company=provider_a,
        )
        created_users.append(prov_user)

        prov_emp = Employee.objects.create(
            user=prov_user,
            employee_id=f"PRV-{test_suffix}",
            company=provider_a,
            bank_details={
                "onboarding": {
                    "status": "approved",
                    "documents": {"id_proof": {"status": "approved"}},
                    "services": [
                        {"id": "svc_general", "name": "General Service", "status": "approved"},
                        {"id": "svc_ac", "name": "AC Repair", "status": "approved"},
                    ]
                }
            },
            is_active=True,
            is_online=True,
        )
        created_employees.append(prov_emp)

        # 5. Provider B Employee (company = Provider B)
        prov_b_user = User.objects.create_user(
            username=f"prov_b_{test_suffix}",
            email=f"prov_b_{test_suffix}@beta.com",
            password="StrongPassword123!",
            role="employee",
            company=provider_b,
        )
        created_users.append(prov_b_user)

        prov_b_emp = Employee.objects.create(
            user=prov_b_user,
            employee_id=f"PRVB-{test_suffix}",
            company=provider_b,
            bank_details={
                "onboarding": {
                    "status": "approved",
                    "documents": {"id_proof": {"status": "approved"}},
                    "services": [
                        {"id": "svc_general", "name": "General Service", "status": "approved"},
                        {"id": "svc_ac", "name": "AC Repair", "status": "approved"},
                    ]
                }
            },
            is_active=True,
            is_online=True,
        )
        created_employees.append(prov_b_emp)

        # ──────────────────────────────────────────────────────────────────────
        # A. Existing Superadmin Login Works
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST A] Verifying Superadmin Login...")
        login_resp = client.post("/api/auth/login/", {
            "identifier": superadmin_user.username,
            "password": "StrongPassword123!",
        }, format="json")
        assert login_resp.status_code == 200, f"Superadmin login failed: {login_resp.data}"
        assert login_resp.data["user"]["role"] == "superadmin", f"Expected role 'superadmin', got {login_resp.data['user']['role']}"
        assert login_resp.data["user"]["is_superadmin"] is True, "Expected is_superadmin=True"
        assert is_superadmin(superadmin_user) is True, "is_superadmin helper must be True"
        superadmin_token = login_resp.data["access_token"]
        print("  [PASS] Superadmin login succeeded with authoritative role='superadmin' and is_superadmin=True.")

        # ──────────────────────────────────────────────────────────────────────
        # B. SUPERADMIN Cross-Provider & Independent Access
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST B] Verifying SUPERADMIN Global Cross-Tenant Access...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {superadmin_token}")

        # Superadmin can view dossier of Independent Employee
        resp_indep = client.get(f"/api/workforce/admin/applications/{indep_emp.id}/")
        assert resp_indep.status_code == 200, f"Superadmin failed to access independent employee dossier: {resp_indep.data}"

        # Superadmin can view dossier of Provider A Employee
        resp_prov_a = client.get(f"/api/workforce/admin/applications/{prov_emp.id}/")
        assert resp_prov_a.status_code == 200, f"Superadmin failed to access Provider A employee dossier: {resp_prov_a.data}"

        # Superadmin can view dossier of Provider B Employee
        resp_prov_b = client.get(f"/api/workforce/admin/applications/{prov_b_emp.id}/")
        assert resp_prov_b.status_code == 200, f"Superadmin failed to access Provider B employee dossier: {resp_prov_b.data}"

        # Superadmin can list applications across all providers
        resp_all_apps = client.get("/api/workforce/admin/applications/")
        assert resp_all_apps.status_code == 200, f"Superadmin failed to list applications: {resp_all_apps.data}"
        listed_ids = {a["id"] for a in resp_all_apps.data}
        assert indep_emp.id in listed_ids, "Independent employee missing from superadmin list"
        assert prov_emp.id in listed_ids, "Provider A employee missing from superadmin list"
        assert prov_b_emp.id in listed_ids, "Provider B employee missing from superadmin list"
        print("  [PASS] Superadmin has global visibility across independent and multiple provider employees.")

        # ──────────────────────────────────────────────────────────────────────
        # C. Provider Admin Belongs to Exactly One Provider
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST C] Verifying Provider Admin Single-Provider Invariant...")
        assert provider_a_admin.company_id == provider_a.id, "Provider Admin must reference provider_a"
        assert provider_a_admin.provider.id == provider_a.id, "user.provider alias must equal user.company"
        assert is_service_provider_admin(provider_a_admin) is True, "is_service_provider_admin must be True"
        assert is_superadmin(provider_a_admin) is False, "Provider admin must NOT be superadmin"

        # Validate fail-closed when provider admin has no company
        from django.core.exceptions import ValidationError
        orphan_admin = User(username="orphan_admin", role="service_provider_admin", company=None)
        orphan_validated = False
        try:
            orphan_admin.validate_provider_admin()
        except ValidationError:
            orphan_validated = True
        assert orphan_validated, "Orphan provider admin must fail validation"
        print("  [PASS] Provider Admin strictly bound to exactly one provider; fail-closed validation verified.")

        # ──────────────────────────────────────────────────────────────────────
        # D & E. Provider Admin Scoping: Can Access Only Own Provider
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST D & E] Verifying Provider Admin Scoping & Isolation...")
        login_padmin = client.post("/api/auth/login/", {
            "identifier": provider_a_admin.username,
            "password": "StrongPassword123!",
        }, format="json")
        assert login_padmin.status_code == 200, f"Provider Admin login failed: {login_padmin.data}"
        assert login_padmin.data["user"]["role"] == "service_provider_admin", f"Expected role 'service_provider_admin', got {login_padmin.data['user']['role']}"
        assert login_padmin.data["user"]["is_provider_admin"] is True, "Expected is_provider_admin=True"
        assert login_padmin.data["user"]["is_superadmin"] is False, "Expected is_superadmin=False"
        assert login_padmin.data["user"]["provider_id"] == provider_a.id, "Expected provider_id equal to provider_a"
        padmin_token = login_padmin.data["access_token"]

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {padmin_token}")

        # Allowed: Access employee belonging to Provider A
        resp_own = client.get(f"/api/workforce/admin/applications/{prov_emp.id}/")
        assert resp_own.status_code == 200, f"Provider Admin failed to access own employee: {resp_own.data}"

        # Forbidden: Access employee belonging to Provider B
        resp_other = client.get(f"/api/workforce/admin/applications/{prov_b_emp.id}/")
        assert resp_other.status_code == 403, f"Provider Admin accessed Provider B employee! Status: {resp_other.status_code}"
        assert resp_other.data.get("code") == "CROSS_TENANT_FORBIDDEN", f"Expected CROSS_TENANT_FORBIDDEN, got {resp_other.data}"

        # Forbidden: Access Independent Employee (company = NULL)
        resp_indep_blocked = client.get(f"/api/workforce/admin/applications/{indep_emp.id}/")
        assert resp_indep_blocked.status_code == 403, f"Provider Admin accessed independent employee! Status: {resp_indep_blocked.status_code}"
        assert resp_indep_blocked.data.get("code") == "CROSS_TENANT_FORBIDDEN", f"Expected CROSS_TENANT_FORBIDDEN, got {resp_indep_blocked.data}"

        # List view strictly filtered to Provider A only
        resp_list_padmin = client.get("/api/workforce/admin/applications/")
        assert resp_list_padmin.status_code == 200
        padmin_emp_ids = {a["id"] for a in resp_list_padmin.data}
        assert prov_emp.id in padmin_emp_ids, "Own employee missing from Provider Admin list"
        assert prov_b_emp.id not in padmin_emp_ids, "Provider B employee leaked in Provider Admin list!"
        assert indep_emp.id not in padmin_emp_ids, "Independent employee leaked in Provider Admin list!"
        print("  [PASS] Provider Admin strictly restricted to own provider. Cross-provider and independent access blocked with HTTP 403 CROSS_TENANT_FORBIDDEN.")

        # ──────────────────────────────────────────────────────────────────────
        # F & G. Independent vs Provider Employee Company Relationships
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST F & G] Verifying Employee Ownership Models & Aliases...")
        assert indep_emp.company_id is None, "Independent employee company must be None"
        assert indep_emp.provider is None, "employee.provider alias must be None for independent tech"
        assert indep_emp.is_independent is True, "employee.is_independent must be True"

        assert prov_emp.company_id == provider_a.id, "Provider employee company must be provider_a"
        assert prov_emp.provider.id == provider_a.id, "employee.provider alias must be provider_a"
        assert prov_emp.is_independent is False, "employee.is_independent must be False for provider tech"
        print("  [PASS] Employee ownership verified: independent has company=None, provider tech has company=<provider>.")

        # ──────────────────────────────────────────────────────────────────────
        # H. Both Employee Types Use the Same Employee Login Flow
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST H] Verifying Unified Employee Login Flow...")
        # Independent Login
        indep_login = client.post("/api/auth/login/", {
            "identifier": indep_user.username,
            "password": "StrongPassword123!",
        }, format="json")
        assert indep_login.status_code == 200, f"Independent employee login failed: {indep_login.data}"
        assert indep_login.data["user"]["role"] == "employee"
        assert indep_login.data["user"]["company"] is None
        assert indep_login.data["user"]["provider_id"] is None
        indep_token = indep_login.data["access_token"]

        # Provider Employee Login
        prov_login = client.post("/api/auth/login/", {
            "identifier": prov_user.username,
            "password": "StrongPassword123!",
        }, format="json")
        assert prov_login.status_code == 200, f"Provider employee login failed: {prov_login.data}"
        assert prov_login.data["user"]["role"] == "employee"
        assert prov_login.data["user"]["company"] == provider_a.id
        assert prov_login.data["user"]["provider_id"] == provider_a.id
        prov_token = prov_login.data["access_token"]
        print("  [PASS] Both employee types authenticated via standard /auth/login/ without distinct flows.")

        # ──────────────────────────────────────────────────────────────────────
        # I. Authoritative Active Jobs Invariant: No Company Auto-Visibility
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST I] Verifying Authoritative Active Jobs Invariant...")
        # Create unassigned Marketplace Job (company=NULL)
        mkt_job = ServiceRequest.objects.create(
            customer_name=f"Customer MKT {test_suffix}",
            phone="9876543210",
            address="123 Market St",
            issue_title="AC Repair",
            service_category="AC Repair",
            preferred_date=timezone.now().date(),
            preferred_time="10:00 AM",
            company=None,
            status="pending",
            total_amount=Decimal("500.00"),
            technician_heading=0.0,
        )
        created_jobs.append(mkt_job)

        # Create unassigned Provider A Job (company=provider_a)
        prov_job = ServiceRequest.objects.create(
            customer_name=f"Customer Alpha {test_suffix}",
            phone="9876543211",
            address="456 Provider St",
            issue_title="AC Repair",
            service_category="AC Repair",
            preferred_date=timezone.now().date(),
            preferred_time="10:00 AM",
            company=provider_a,
            status="pending",
            total_amount=Decimal("750.00"),
            technician_heading=0.0,
        )
        created_jobs.append(prov_job)

        # Independent Tech calls /api/workforce/jobs/
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {indep_token}")
        indep_jobs_resp = client.get("/api/workforce/jobs/")
        assert indep_jobs_resp.status_code == 200
        indep_visible_ids = {j["id"] for j in indep_jobs_resp.data}
        assert mkt_job.id not in indep_visible_ids, "Marketplace job unexpectedly visible without offer/assignment!"
        assert prov_job.id not in indep_visible_ids, "Provider job unexpectedly visible to independent tech!"

        # Provider A Tech calls /api/workforce/jobs/
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {prov_token}")
        prov_jobs_resp = client.get("/api/workforce/jobs/")
        assert prov_jobs_resp.status_code == 200
        prov_visible_ids = {j["id"] for j in prov_jobs_resp.data}
        assert prov_job.id not in prov_visible_ids, "Provider job unexpectedly visible without explicit offer/assignment!"
        assert mkt_job.id not in prov_visible_ids, "Marketplace job unexpectedly visible without explicit offer/assignment!"

        # Now explicitly offer mkt_job to independent tech
        offer = WorkforceJobOffer.objects.create(
            job=mkt_job,
            employee=indep_emp,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {indep_token}")
        indep_offered_resp = client.get("/api/workforce/jobs/")
        offered_ids = {j["id"] for j in indep_offered_resp.data}
        assert mkt_job.id in offered_ids, "Explicitly offered job must appear in offered queue"
        offer.delete()
        print("  [PASS] Active Jobs Invariant preserved: Company membership NEVER leaks unoffered/unassigned jobs into active queue.")

        # ──────────────────────────────────────────────────────────────────────
        # J. Dispatch Compatibility: Candidate Discovery & Candidate Scope
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST J] Verifying Dispatch Compatibility for Independent and Provider Techs...")
        from workforce_api.services.automatic_dispatch import (
            get_eligible_candidates,
            check_candidate_eligibility,
        )

        # Discovery scope: independent employee discovers all marketplace jobs (company=None)
        indep_scope = get_booking_discovery_scope(None)
        assert indep_scope == django.db.models.Q(), "Independent discovery scope must discover all open jobs"

        # Coordinates setup
        mkt_job.latitude = 12.9716
        mkt_job.longitude = 77.5946
        mkt_job.save()

        prov_job.latitude = 12.9716
        prov_job.longitude = 77.5946
        prov_job.save()

        # Update technician last known locations so GPS radius matches
        loc = {"latitude": 12.9718, "longitude": 77.5948, "updated_at": timezone.now().isoformat()}
        indep_user.last_known_location = loc
        indep_user.save()
        prov_user.last_known_location = loc
        prov_user.save()
        prov_b_user.last_known_location = loc
        prov_b_user.save()

        # 1. Candidate evaluation for Marketplace Job (company=NULL)
        mkt_candidates = get_eligible_candidates(mkt_job, radius_km=50.0)
        mkt_cand_ids = {c["employee"].id for c in mkt_candidates}
        assert indep_emp.id in mkt_cand_ids, f"Independent employee #{indep_emp.id} must be eligible for Marketplace job"

        # 2. Candidate evaluation for Provider A Job (company=provider_a)
        # Should include Provider A employee, but strictly exclude Provider B and independent tech
        prov_candidates = get_eligible_candidates(prov_job, radius_km=50.0)
        prov_cand_ids = {c["employee"].id for c in prov_candidates}
        assert prov_emp.id in prov_cand_ids, "Provider A employee must be eligible for Provider A job"
        assert prov_b_emp.id not in prov_cand_ids, "Provider B employee must be excluded from Provider A job"
        assert indep_emp.id not in prov_cand_ids, "Independent employee must be excluded from Provider A job"

        # 3. Base candidate eligibility check for both independent and provider techs
        indep_ok, _, _ = check_candidate_eligibility(indep_emp, service_name="General Service", check_workload=False)
        assert indep_ok is True, "Independent technician base eligibility must pass"

        prov_ok, _, _ = check_candidate_eligibility(prov_emp, service_name="General Service", check_workload=False)
        assert prov_ok is True, "Provider technician base eligibility must pass"
        print("  [PASS] Dispatch scope and candidate filtering verified across independent and provider pairings.")

        # ──────────────────────────────────────────────────────────────────────
        # K. Existing Onboarding Lifecycle Functionality
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST K] Verifying Onboarding Functionality...")
        # Superadmin fetches candidate onboarding dossier
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {superadmin_token}")
        onboard_resp = client.get(f"/api/workforce/admin/applications/{indep_emp.id}/")
        assert onboard_resp.status_code == 200, f"Onboarding dossier fetch failed: {onboard_resp.data}"
        assert onboard_resp.data["registration_status"] == "approved"
        print("  [PASS] Existing onboarding retrieval and verification verified functional.")

        # ──────────────────────────────────────────────────────────────────────
        # L. Admin Functionality for Superadmin
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST L] Verifying Superadmin Full Platform Admin Functionality...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {superadmin_token}")
        admin_jobs_resp = client.get("/api/workforce/jobs/")
        assert admin_jobs_resp.status_code == 200, f"Superadmin /api/workforce/jobs/ failed: {admin_jobs_resp.data}"
        print("  [PASS] Existing Admin API functionality verified functional for SUPERADMIN.")

        # ──────────────────────────────────────────────────────────────────────
        # M. Authentication / Token Refresh Functionality
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST M] Verifying Token Refresh Functionality...")
        refresh_resp = client.post("/api/auth/refresh/", {
            "refresh": login_resp.data["refresh_token"],
        }, format="json")
        assert refresh_resp.status_code == 200, f"Token refresh failed: {refresh_resp.data}"
        assert "access_token" in refresh_resp.data or "token" in refresh_resp.data
        print("  [PASS] Authentication token refresh verified functional.")

        print("\n" + "=" * 80)
        print("ALL 13 PHASE 1 ARCHITECTURAL INVARIANTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        # Teardown test artifacts
        print("\nCleaning up test artifacts...")
        WorkforceJobOffer.objects.filter(employee__in=created_employees).delete()
        for j in created_jobs:
            ServiceRequest.objects.filter(pk=j.pk).delete()
        for e in created_employees:
            Employee.objects.filter(pk=e.pk).delete()
        for u in created_users:
            User.objects.filter(pk=u.pk).delete()
        for c in created_companies:
            Company.objects.filter(pk=c.pk).delete()
        print("Cleanup completed.")


if __name__ == "__main__":
    run_tests()
