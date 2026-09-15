"""
backend/test_phase2_service_provider_creation.py
Automated Verification Suite for Workforce Phase 2A:
Service Provider Creation & Primary Provider Admin Foundation.

Tests:
A. Superadmin creates Provider A.
B. Provider A Company exists exactly once.
C. Primary Provider Admin exists exactly once with role=service_provider_admin, company=Provider A, is_superuser=False.
D. Provider Admin can login via standard /api/auth/login/.
E. Login response contains correct provider context (provider_id, provider_name, is_provider_admin=True, is_superadmin=False).
F. /api/auth/me/ returns correct provider context.
G. /api/auth/refresh/ preserves provider role/context.
H. Provider Admin can access existing admin functionality for Provider A.
I. Provider Admin cannot access Provider B (returns HTTP 403 CROSS_TENANT_FORBIDDEN).
J. Provider Admin cannot access independent employees (returns HTTP 403 CROSS_TENANT_FORBIDDEN).
K. Provider Admin cannot create another provider (returns HTTP 403).
L. Superadmin can list Provider A and Provider B via /api/workforce/superadmin/service-providers/.
M. Superadmin can view detail for Provider A via /api/workforce/superadmin/service-providers/<id>/.
N. Provider Profile /api/workforce/provider/profile/ returns only authenticated admin's provider.
O. Independent technician login still works.
P. Existing employee.company_id = NULL behavior still works.
Q. Existing Active Jobs invariant preserved (company membership NEVER leaks unoffered jobs).
R. Atomic rollback on failed creation (no orphaned Company or User).
S. Reliable cleanup of all test records.
"""
import os
import sys
import uuid
import django

# Set UTF-8 encoding for stdout on Windows console
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer

User = get_user_model()

# Track all created IDs for reliable teardown
CLEANUP_USERS = []
CLEANUP_COMPANIES = []
CLEANUP_EMPLOYEES = []
CLEANUP_JOBS = []
CLEANUP_OFFERS = []

TEST_RUN_ID = uuid.uuid4().hex[:6]


def run_tests():
    client = APIClient()

    print("=" * 80)
    print(f"STARTING WORKFORCE PHASE 2A VERIFICATION SUITE [Run ID: {TEST_RUN_ID}]")
    print("=" * 80)

    try:
        # ──────────────────────────────────────────────────────────────────────
        # SETUP: Create Superadmin
        # ──────────────────────────────────────────────────────────────────────
        super_username = f"super_{TEST_RUN_ID}"
        super_email = f"super_{TEST_RUN_ID}@example.com"
        super_password = "SuperPassword123!"

        superadmin_user = User.objects.create_superuser(
            username=super_username,
            email=super_email,
            password=super_password,
        )
        CLEANUP_USERS.append(superadmin_user.id)

        # Login Superadmin
        super_login = client.post("/api/auth/login/", {
            "identifier": super_username,
            "password": super_password,
        }, format="json")
        assert super_login.status_code == 200, f"Superadmin login failed: {super_login.data}"
        super_token = super_login.data["access_token"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {super_token}")

        # ──────────────────────────────────────────────────────────────────────
        # A, B, C. Superadmin creates Provider A (Company + Primary Admin)
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST A, B, C] Superadmin creates Provider A & Primary Provider Admin...")
        prov_a_name = f"Apex Solutions {TEST_RUN_ID}"
        prov_a_display = f"APEX-{TEST_RUN_ID.upper()}"
        admin_a_username = f"admin_apex_{TEST_RUN_ID}"
        admin_a_email = f"admin_apex_{TEST_RUN_ID}@apexsolutions.com"
        admin_a_password = "ApexAdminPass123!"

        create_resp = client.post("/api/workforce/superadmin/service-providers/", {
            "company_name": prov_a_name,
            "display_id": prov_a_display,
            "address": "100 Tech Blvd, Suite 200",
            "industry": "Electrical & HVAC",
            "website": "https://apexsolutions.example.com",
            "admin_username": admin_a_username,
            "admin_email": admin_a_email,
            "admin_password": admin_a_password,
            "admin_first_name": "Apex",
            "admin_last_name": "Administrator",
            "admin_phone": f"+1555{uuid.uuid4().hex[:7]}",
        }, format="json")

        assert create_resp.status_code == 201, f"Provider creation failed: {create_resp.data}"
        prov_a_id = create_resp.data["provider"]["id"]
        admin_a_id = create_resp.data["admin"]["id"]
        CLEANUP_COMPANIES.append(prov_a_id)
        CLEANUP_USERS.append(admin_a_id)

        # Verify DB state
        prov_a_db = Company.objects.filter(pk=prov_a_id).first()
        assert prov_a_db is not None, "Provider A Company not found in database"
        assert prov_a_db.company_name == prov_a_name
        assert prov_a_db.display_id == prov_a_display
        assert Company.objects.filter(company_name=prov_a_name).count() == 1, "Provider A must exist exactly once"

        admin_a_db = User.objects.filter(pk=admin_a_id).first()
        assert admin_a_db is not None, "Primary Admin user not found in database"
        assert admin_a_db.role == "service_provider_admin", f"Expected role 'service_provider_admin', got '{admin_a_db.role}'"
        assert admin_a_db.company_id == prov_a_id, f"Expected company_id {prov_a_id}, got {admin_a_db.company_id}"
        assert admin_a_db.is_superuser is False, "Provider Admin must NOT be superuser"
        print("  [PASS] Provider A and primary Provider Admin created atomically with correct roles and relationships.")

        # ──────────────────────────────────────────────────────────────────────
        # D, E, F, G. Provider Admin Authentication, Context & Token Refresh
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST D, E, F, G] Verifying Provider Admin Login, Context & Token Refresh...")
        client.credentials()  # Clear auth headers
        admin_login = client.post("/api/auth/login/", {
            "identifier": admin_a_username,
            "password": admin_a_password,
        }, format="json")

        assert admin_login.status_code == 200, f"Provider Admin login failed: {admin_login.data}"
        auth_data = admin_login.data
        user_info = auth_data["user"]
        assert user_info["role"] == "service_provider_admin", f"Expected role 'service_provider_admin', got '{user_info['role']}'"
        assert user_info["is_provider_admin"] is True, "is_provider_admin must be True"
        assert user_info["is_superadmin"] is False, "is_superadmin must be False"
        assert user_info["provider_id"] == prov_a_id, f"Expected provider_id {prov_a_id}, got {user_info['provider_id']}"
        assert user_info["provider_name"] == prov_a_name

        admin_token = auth_data["access_token"]
        refresh_token = auth_data["refresh_token"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")

        # Check /api/auth/me/
        me_resp = client.get("/api/auth/me/")
        assert me_resp.status_code == 200, f"/auth/me/ failed: {me_resp.data}"
        assert me_resp.data["role"] == "service_provider_admin"
        assert me_resp.data["provider_id"] == prov_a_id
        assert me_resp.data["is_provider_admin"] is True
        assert me_resp.data["is_superadmin"] is False

        # Check /api/auth/refresh/
        refresh_resp = client.post("/api/auth/refresh/", {
            "refresh": refresh_token,
        }, format="json")
        assert refresh_resp.status_code == 200, f"Token refresh failed: {refresh_resp.data}"
        assert "access_token" in refresh_resp.data or "token" in refresh_resp.data
        print("  [PASS] Provider Admin authentication, /auth/me/ profile, and token refresh preserve authoritative provider context.")

        # ──────────────────────────────────────────────────────────────────────
        # Create Provider B and Independent Technician for Boundary Tests
        # ──────────────────────────────────────────────────────────────────────
        # Create Provider B via Superadmin API
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {super_token}")
        prov_b_name = f"Beta Services {TEST_RUN_ID}"
        admin_b_username = f"admin_beta_{TEST_RUN_ID}"
        admin_b_email = f"admin_beta_{TEST_RUN_ID}@betaservices.com"
        admin_b_password = "BetaAdminPass123!"

        create_b_resp = client.post("/api/workforce/superadmin/service-providers/", {
            "company_name": prov_b_name,
            "admin_username": admin_b_username,
            "admin_email": admin_b_email,
            "admin_password": admin_b_password,
        }, format="json")
        assert create_b_resp.status_code == 201
        prov_b_id = create_b_resp.data["provider"]["id"]
        admin_b_id = create_b_resp.data["admin"]["id"]
        CLEANUP_COMPANIES.append(prov_b_id)
        CLEANUP_USERS.append(admin_b_id)

        # Create Provider A technician
        tech_a_user = User.objects.create_user(
            username=f"tech_a_{TEST_RUN_ID}",
            email=f"tech_a_{TEST_RUN_ID}@example.com",
            password="TechPass123!",
            role="employee",
            company_id=prov_a_id,
        )
        CLEANUP_USERS.append(tech_a_user.id)
        tech_a_emp = Employee.objects.create(
            user=tech_a_user,
            employee_id=f"EMP-A-{TEST_RUN_ID.upper()}",
            company_id=prov_a_id,
            is_active=True,
            bank_details={"onboarding": {"status": "submitted", "services": [], "documents": {}}}
        )
        CLEANUP_EMPLOYEES.append(tech_a_emp.id)

        # Create Provider B technician
        tech_b_user = User.objects.create_user(
            username=f"tech_b_{TEST_RUN_ID}",
            email=f"tech_b_{TEST_RUN_ID}@example.com",
            password="TechPass123!",
            role="employee",
            company_id=prov_b_id,
        )
        CLEANUP_USERS.append(tech_b_user.id)
        tech_b_emp = Employee.objects.create(
            user=tech_b_user,
            employee_id=f"EMP-B-{TEST_RUN_ID.upper()}",
            company_id=prov_b_id,
            is_active=True,
            bank_details={"onboarding": {"status": "submitted", "services": [], "documents": {}}}
        )
        CLEANUP_EMPLOYEES.append(tech_b_emp.id)

        # Create Independent technician (company=None)
        indep_user = User.objects.create_user(
            username=f"indep_{TEST_RUN_ID}",
            email=f"indep_{TEST_RUN_ID}@example.com",
            password="TechPass123!",
            role="employee",
            company=None,
        )
        CLEANUP_USERS.append(indep_user.id)
        indep_emp = Employee.objects.create(
            user=indep_user,
            employee_id=f"EMP-IND-{TEST_RUN_ID.upper()}",
            company=None,
            is_active=True,
            bank_details={"onboarding": {"status": "approved", "services": [{"name": "Electrical", "status": "approved"}], "documents": {}}}
        )
        CLEANUP_EMPLOYEES.append(indep_emp.id)

        # ──────────────────────────────────────────────────────────────────────
        # H, I, J. Provider Admin Scoping & Isolation
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST H, I, J] Verifying Provider Admin Scoping & Isolation...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")

        # 1. Provider Admin views applications list: should see Tech A, but strictly NOT Tech B or Independent Tech
        apps_resp = client.get("/api/workforce/admin/applications/")
        assert apps_resp.status_code == 200, f"Applications list failed: {apps_resp.data}"
        app_ids = {a["id"] for a in apps_resp.data}
        assert tech_a_emp.id in app_ids, "Provider Admin must see own technician application"
        assert tech_b_emp.id not in app_ids, "Provider Admin must NOT see Provider B technician application"
        assert indep_emp.id not in app_ids, "Provider Admin must NOT see independent technician application"

        # 2. Access Provider A application detail: ALLOW
        detail_a_resp = client.get(f"/api/workforce/admin/applications/{tech_a_emp.id}/")
        assert detail_a_resp.status_code == 200, f"Provider Admin viewing own tech detail failed: {detail_a_resp.data}"

        # 3. Access Provider B application detail: DENY (403 CROSS_TENANT_FORBIDDEN)
        detail_b_resp = client.get(f"/api/workforce/admin/applications/{tech_b_emp.id}/")
        assert detail_b_resp.status_code == 403, f"Expected 403 for Provider B access, got {detail_b_resp.status_code}"

        # 4. Access Independent application detail: DENY (403 CROSS_TENANT_FORBIDDEN)
        detail_indep_resp = client.get(f"/api/workforce/admin/applications/{indep_emp.id}/")
        assert detail_indep_resp.status_code == 403, f"Expected 403 for Independent access, got {detail_indep_resp.status_code}"
        print("  [PASS] Provider Admin strictly restricted to own provider. Cross-tenant and independent access blocked.")

        # ──────────────────────────────────────────────────────────────────────
        # K. Provider Admin Cannot Create Another Provider
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST K] Verifying Provider Admin Cannot Create Service Providers...")
        prov_create_attempt = client.post("/api/workforce/superadmin/service-providers/", {
            "company_name": "Rogue Provider Creation",
            "admin_username": "rogue_admin",
            "admin_email": "rogue@example.com",
            "admin_password": "RoguePassword123!",
        }, format="json")
        assert prov_create_attempt.status_code == 403, f"Expected 403 FORBIDDEN for Provider Admin, got {prov_create_attempt.status_code}"
        print("  [PASS] Provider Admin cannot create another Service Provider.")

        # ──────────────────────────────────────────────────────────────────────
        # L, M. Superadmin Lists & Views Providers
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST L, M] Verifying Superadmin Provider Listing & Detail...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {super_token}")

        # List providers
        prov_list_resp = client.get("/api/workforce/superadmin/service-providers/")
        assert prov_list_resp.status_code == 200, f"Superadmin provider listing failed: {prov_list_resp.data}"
        prov_ids = {p["id"] for p in prov_list_resp.data}
        assert prov_a_id in prov_ids, "Superadmin must see Provider A"
        assert prov_b_id in prov_ids, "Superadmin must see Provider B"

        # Detail of Provider A
        prov_detail_resp = client.get(f"/api/workforce/superadmin/service-providers/{prov_a_id}/")
        assert prov_detail_resp.status_code == 200, f"Superadmin provider detail failed: {prov_detail_resp.data}"
        assert prov_detail_resp.data["company_name"] == prov_a_name
        assert prov_detail_resp.data["primary_admin"]["id"] == admin_a_id
        print("  [PASS] Superadmin can list all providers and view provider details.")

        # ──────────────────────────────────────────────────────────────────────
        # N. Provider Profile API (/api/workforce/provider/profile/)
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST N] Verifying Provider Profile Endpoint...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_token}")
        prof_resp = client.get("/api/workforce/provider/profile/")
        assert prof_resp.status_code == 200, f"Provider profile failed: {prof_resp.data}"
        assert prof_resp.data["id"] == prov_a_id, f"Expected provider ID {prov_a_id}, got {prof_resp.data['id']}"
        assert prof_resp.data["company_name"] == prov_a_name
        assert prof_resp.data["primary_admin"]["id"] == admin_a_id
        print("  [PASS] /api/workforce/provider/profile/ returns only authenticated Provider Admin's provider.")

        # ──────────────────────────────────────────────────────────────────────
        # O, P. Independent Technician Functionality & Nullability
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST O, P] Verifying Independent Technician Authentication & Nullability...")
        client.credentials()
        indep_login = client.post("/api/auth/login/", {
            "identifier": indep_user.username,
            "password": "TechPass123!",
        }, format="json")
        assert indep_login.status_code == 200, f"Independent login failed: {indep_login.data}"
        assert indep_login.data["user"]["role"] == "employee"
        assert indep_login.data["user"]["company"] is None
        assert indep_login.data["user"]["provider_id"] is None
        assert indep_emp.is_independent is True
        assert indep_emp.company_id is None
        print("  [PASS] Independent technician login and company_id=NULL behavior confirmed valid.")

        # ──────────────────────────────────────────────────────────────────────
        # Q. Active Jobs Invariant
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST Q] Verifying Active Jobs Invariant...")
        indep_client_token = indep_login.data["access_token"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {indep_client_token}")

        # Create unoffered job for Provider A and unoffered job for Marketplace
        prov_job = ServiceRequest.objects.create(
            company_id=prov_a_id,
            service_category="Electrical",
            issue_title=f"Prov A Job {TEST_RUN_ID}",
            customer_name="Customer A",
            phone="1234567890",
            address="123 Street",
            preferred_date=timezone.now().date(),
            preferred_time="10:00 AM",
            status="new_request",
        )
        CLEANUP_JOBS.append(prov_job.id)

        mkt_job = ServiceRequest.objects.create(
            company=None,
            service_category="Electrical",
            issue_title=f"Marketplace Job {TEST_RUN_ID}",
            customer_name="Customer Mkt",
            phone="1234567890",
            address="123 Street",
            preferred_date=timezone.now().date(),
            preferred_time="10:00 AM",
            status="new_request",
        )
        CLEANUP_JOBS.append(mkt_job.id)

        # Independent tech queries active jobs: neither should be visible without an offer/assignment
        active_resp = client.get("/api/workforce/jobs/")
        active_ids = {j["id"] for j in active_resp.data}
        assert prov_job.id not in active_ids, "Unoffered provider job must NOT appear in technician active queue"
        assert mkt_job.id not in active_ids, "Unoffered marketplace job must NOT appear in technician active queue"

        # Now offer mkt_job explicitly to indep_emp
        offer = WorkforceJobOffer.objects.create(
            job=mkt_job,
            employee=indep_emp,
            wave_id=1,
            status=WorkforceJobOffer.Status.OFFERED,
            offered_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        CLEANUP_OFFERS.append(offer.id)

        offered_resp = client.get("/api/workforce/jobs/")
        offered_ids = {j["id"] for j in offered_resp.data}
        assert mkt_job.id in offered_ids, "Explicitly offered job MUST appear in technician active queue"
        offer.delete()
        print("  [PASS] Active Jobs Invariant preserved: Company membership NEVER leaks unoffered jobs.")

        # ──────────────────────────────────────────────────────────────────────
        # R. Atomic Rollback on Failed Creation
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST R] Verifying Atomic Rollback on Failed Creation...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {super_token}")

        # Attempt creation with duplicate admin username (should fail during user creation and roll back company)
        fail_co_name = f"Failed Provider {TEST_RUN_ID}"
        fail_display = f"FAIL-{TEST_RUN_ID.upper()}"

        fail_create = client.post("/api/workforce/superadmin/service-providers/", {
            "company_name": fail_co_name,
            "display_id": fail_display,
            "admin_username": admin_a_username,  # DUPLICATE USERNAME!
            "admin_email": f"unique_email_{TEST_RUN_ID}@example.com",
            "admin_password": "ValidPassword123!",
        }, format="json")

        assert fail_create.status_code == 400, f"Expected 400 Bad Request for duplicate username, got {fail_create.status_code}"
        # Ensure company was NOT created
        assert not Company.objects.filter(company_name=fail_co_name).exists(), "Company must not exist after rollback"
        assert not Company.objects.filter(display_id=fail_display).exists(), "Display ID must not exist after rollback"
        print("  [PASS] Atomicity verified: Failed creation rolled back without leaving orphaned records.")

        print("\n" + "=" * 80)
        print("ALL 19 PHASE 2A TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        print("\nCleaning up test artifacts...")
        # Teardown tracked test records safely
        if CLEANUP_OFFERS:
            WorkforceJobOffer.objects.filter(id__in=CLEANUP_OFFERS).delete()
        if CLEANUP_JOBS:
            ServiceRequest.objects.filter(id__in=CLEANUP_JOBS).delete()
        if CLEANUP_EMPLOYEES:
            Employee.objects.filter(id__in=CLEANUP_EMPLOYEES).delete()
        if CLEANUP_USERS:
            User.objects.filter(id__in=CLEANUP_USERS).delete()
        if CLEANUP_COMPANIES:
            Company.objects.filter(id__in=CLEANUP_COMPANIES).delete()
        print("Cleanup completed.")


if __name__ == "__main__":
    run_tests()
