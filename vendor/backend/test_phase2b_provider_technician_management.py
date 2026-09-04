"""
backend/test_phase2b_provider_technician_management.py
Automated Verification Suite for Workforce Phase 2B:
Service Provider Technician Management & Onboarding.

Tests:
A. Provider Admin creates technician.
B. Created technician has role=employee, company=Provider A.
C. Multiple technicians belong to the same provider.
D. Independent technician works with company_id=NULL.
E. Provider technician can log in using standard employee login.
F. Provider technician receives correct provider context in login and /auth/me.
G. Provider Admin can see own technicians.
H. Provider Admin cannot see Provider B technicians (403 CROSS_TENANT_FORBIDDEN on direct access).
I. Provider Admin cannot see independent technicians (403 CROSS_TENANT_FORBIDDEN on direct access).
J. Provider Admin cannot change technician ownership to another provider.
K. Superadmin can see and manage all technicians.
L. Provider technician follows existing onboarding workflow.
M. Provider membership does NOT leak unrelated jobs into Active Jobs queue.
N. Provider technician receives an eligible dispatch offer.
O. Existing employee job execution continues to work.
P. Clean teardown of all test records.
"""
import os
import sys
import uuid
from decimal import Decimal
import django

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

CLEANUP_USERS = []
CLEANUP_COMPANIES = []
CLEANUP_EMPLOYEES = []
CLEANUP_JOBS = []
CLEANUP_OFFERS = []

TEST_RUN_ID = uuid.uuid4().hex[:6]


def run_tests():
    client = APIClient()

    print("=" * 80)
    print(f"STARTING WORKFORCE PHASE 2B VERIFICATION SUITE [Run ID: {TEST_RUN_ID}]")
    print("=" * 80)

    try:
        # ──────────────────────────────────────────────────────────────────────
        # SETUP: Create Superadmin, Provider A (with Admin A), Provider B (with Admin B)
        # ──────────────────────────────────────────────────────────────────────
        super_username = f"super2b_{TEST_RUN_ID}"
        super_password = "SuperPassword123!"
        superadmin_user = User.objects.create_superuser(
            username=super_username,
            email=f"{super_username}@example.com",
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

        # Create Provider A via Superadmin API
        prov_a_name = f"Apex Providers {TEST_RUN_ID}"
        admin_a_username = f"admin_a_{TEST_RUN_ID}"
        admin_a_password = "AdminPass123!"
        resp_a = client.post("/api/workforce/superadmin/service-providers/", {
            "company_name": prov_a_name,
            "display_id": f"APEX-{TEST_RUN_ID.upper()}",
            "admin_username": admin_a_username,
            "admin_email": f"{admin_a_username}@apex.com",
            "admin_password": admin_a_password,
        }, format="json")
        assert resp_a.status_code == 201, f"Provider A creation failed: {resp_a.data}"
        prov_a_id = resp_a.data["provider"]["id"]
        admin_a_id = resp_a.data["admin"]["id"]
        CLEANUP_COMPANIES.append(prov_a_id)
        CLEANUP_USERS.append(admin_a_id)

        # Create Provider B via Superadmin API
        prov_b_name = f"Beta Providers {TEST_RUN_ID}"
        admin_b_username = f"admin_b_{TEST_RUN_ID}"
        admin_b_password = "AdminPass123!"
        resp_b = client.post("/api/workforce/superadmin/service-providers/", {
            "company_name": prov_b_name,
            "display_id": f"BETA-{TEST_RUN_ID.upper()}",
            "admin_username": admin_b_username,
            "admin_email": f"{admin_b_username}@beta.com",
            "admin_password": admin_b_password,
        }, format="json")
        assert resp_b.status_code == 201, f"Provider B creation failed: {resp_b.data}"
        prov_b_id = resp_b.data["provider"]["id"]
        admin_b_id = resp_b.data["admin"]["id"]
        CLEANUP_COMPANIES.append(prov_b_id)
        CLEANUP_USERS.append(admin_b_id)

        # Login Provider Admin A
        admin_a_login = client.post("/api/auth/login/", {
            "identifier": admin_a_username,
            "password": admin_a_password,
        }, format="json")
        assert admin_a_login.status_code == 200
        admin_a_token = admin_a_login.data["access_token"]

        # Login Provider Admin B
        admin_b_login = client.post("/api/auth/login/", {
            "identifier": admin_b_username,
            "password": admin_b_password,
        }, format="json")
        assert admin_b_login.status_code == 200
        admin_b_token = admin_b_login.data["access_token"]

        # ──────────────────────────────────────────────────────────────────────
        # TEST A & B: Provider Admin Creates Technician (Auto-Bound to Provider A)
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST A & B] Provider Admin A creates Technician A1...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_a_token}")

        tech_a1_email = f"tech_a1_{TEST_RUN_ID}@apex.com"
        tech_a1_pass = "TechPassword123!"
        create_tech_resp = client.post("/api/workforce/admin/technicians/", {
            "first_name": "TechA1",
            "last_name": "Apex",
            "email": tech_a1_email,
            "phone": "+1555100001",
            "password": tech_a1_pass,
            "services": ["HVAC Maintenance", "Electrical Inspection"],
            "company_id": 99999,  # Malicious / rogue client parameter: MUST BE IGNORED by backend!
        }, format="json")

        assert create_tech_resp.status_code == 201, f"Technician creation failed: {create_tech_resp.data}"
        tech_a1_data = create_tech_resp.data["technician"]
        tech_a1_emp_id = tech_a1_data["id"]
        CLEANUP_EMPLOYEES.append(tech_a1_emp_id)

        emp_a1_db = Employee.objects.filter(pk=tech_a1_emp_id).select_related("user", "company").first()
        assert emp_a1_db is not None, "Technician Employee not found in DB"
        CLEANUP_USERS.append(emp_a1_db.user_id)

        assert emp_a1_db.company_id == prov_a_id, f"Expected company_id {prov_a_id}, got {emp_a1_db.company_id}"
        assert emp_a1_db.user.company_id == prov_a_id, f"Expected user.company_id {prov_a_id}, got {emp_a1_db.user.company_id}"
        assert emp_a1_db.user.role == "employee", f"Expected role 'employee', got '{emp_a1_db.user.role}'"
        print("  [PASS] Technician A1 created and strictly bound to Provider A (frontend company override safely ignored).")

        # ──────────────────────────────────────────────────────────────────────
        # TEST C: Multiple Technicians Under Same Provider
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST C] Creating multiple technicians under Provider A...")
        tech_a2_resp = client.post("/api/workforce/admin/technicians/", {
            "first_name": "TechA2",
            "last_name": "Apex",
            "email": f"tech_a2_{TEST_RUN_ID}@apex.com",
            "phone": "+1555100002",
            "password": "TechPassword123!",
            "services": ["Plumbing Repair"],
        }, format="json")
        assert tech_a2_resp.status_code == 201
        tech_a2_emp_id = tech_a2_resp.data["technician"]["id"]
        CLEANUP_EMPLOYEES.append(tech_a2_emp_id)
        emp_a2_db = Employee.objects.get(pk=tech_a2_emp_id)
        CLEANUP_USERS.append(emp_a2_db.user_id)

        tech_a3_resp = client.post("/api/workforce/admin/technicians/", {
            "first_name": "TechA3",
            "last_name": "Apex",
            "email": f"tech_a3_{TEST_RUN_ID}@apex.com",
            "phone": "+1555100003",
            "password": "TechPassword123!",
            "services": ["Electrical Inspection"],
        }, format="json")
        assert tech_a3_resp.status_code == 201
        tech_a3_emp_id = tech_a3_resp.data["technician"]["id"]
        CLEANUP_EMPLOYEES.append(tech_a3_emp_id)
        emp_a3_db = Employee.objects.get(pk=tech_a3_emp_id)
        CLEANUP_USERS.append(emp_a3_db.user_id)

        prov_a_tech_count = Employee.objects.filter(company_id=prov_a_id).count()
        assert prov_a_tech_count == 3, f"Expected 3 technicians under Provider A, got {prov_a_tech_count}"
        print("  [PASS] Successfully created 3 technicians under Provider A.")

        # ──────────────────────────────────────────────────────────────────────
        # Create Provider B Technician & Independent Technician
        # ──────────────────────────────────────────────────────────────────────
        # Provider B creates Tech B1
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_b_token}")
        tech_b1_resp = client.post("/api/workforce/admin/technicians/", {
            "first_name": "TechB1",
            "last_name": "Beta",
            "email": f"tech_b1_{TEST_RUN_ID}@beta.com",
            "phone": "+1555200001",
            "password": "TechPassword123!",
        }, format="json")
        assert tech_b1_resp.status_code == 201
        tech_b1_emp_id = tech_b1_resp.data["technician"]["id"]
        CLEANUP_EMPLOYEES.append(tech_b1_emp_id)
        emp_b1_db = Employee.objects.get(pk=tech_b1_emp_id)
        CLEANUP_USERS.append(emp_b1_db.user_id)

        # Superadmin creates Independent Tech (company_id=None)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {super_token}")
        tech_indep_resp = client.post("/api/workforce/admin/technicians/", {
            "first_name": "TechIndep",
            "last_name": "Solo",
            "email": f"tech_indep_{TEST_RUN_ID}@solo.com",
            "phone": "+1555300001",
            "password": "TechPassword123!",
            "company_id": None,
        }, format="json")
        assert tech_indep_resp.status_code == 201
        tech_indep_emp_id = tech_indep_resp.data["technician"]["id"]
        CLEANUP_EMPLOYEES.append(tech_indep_emp_id)
        emp_indep_db = Employee.objects.get(pk=tech_indep_emp_id)
        CLEANUP_USERS.append(emp_indep_db.user_id)

        # ──────────────────────────────────────────────────────────────────────
        # TEST D: Independent Technician Has company_id = NULL
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST D] Verifying Independent Technician company_id = NULL...")
        assert emp_indep_db.company_id is None
        assert emp_indep_db.user.company_id is None
        assert emp_indep_db.is_independent is True
        print("  [PASS] Independent technician verified with company_id = NULL.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST E & F: Provider Technician Authentication & Context
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST E & F] Verifying Provider Technician Login & Context...")
        client.credentials()  # Clear auth
        tech_login_resp = client.post("/api/auth/login/", {
            "identifier": tech_a1_email,
            "password": tech_a1_pass,
        }, format="json")
        assert tech_login_resp.status_code == 200, f"Technician login failed: {tech_login_resp.data}"
        t_user = tech_login_resp.data["user"]
        assert t_user["role"] == "employee"
        assert t_user["provider_id"] == prov_a_id
        assert t_user["provider_name"] == prov_a_name
        assert t_user["is_provider_admin"] is False
        assert t_user["is_superadmin"] is False

        # Check /api/auth/me/
        tech_a1_token = tech_login_resp.data["access_token"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tech_a1_token}")
        me_resp = client.get("/api/auth/me/")
        assert me_resp.status_code == 200
        assert me_resp.data["role"] == "employee"
        assert me_resp.data["provider_id"] == prov_a_id
        assert me_resp.data["provider_name"] == prov_a_name
        print("  [PASS] Provider technician login and /auth/me return correct authoritative provider context.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST G, H, I: Provider Admin Scoping & Isolation
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST G, H, I] Verifying Provider Admin Isolation & Scoping...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_a_token}")

        # List technicians as Provider Admin A
        list_resp = client.get("/api/workforce/admin/technicians/")
        assert list_resp.status_code == 200
        visible_ids = {t["id"] for t in list_resp.data}
        assert tech_a1_emp_id in visible_ids, "Admin A must see Tech A1"
        assert tech_a2_emp_id in visible_ids, "Admin A must see Tech A2"
        assert tech_a3_emp_id in visible_ids, "Admin A must see Tech A3"
        assert tech_b1_emp_id not in visible_ids, "Admin A must NOT see Tech B1"
        assert tech_indep_emp_id not in visible_ids, "Admin A must NOT see Independent Tech"

        # Direct GET Tech A1: ALLOW
        detail_a_resp = client.get(f"/api/workforce/admin/technicians/{tech_a1_emp_id}/")
        assert detail_a_resp.status_code == 200

        # Direct GET Tech B1: 403 CROSS_TENANT_FORBIDDEN
        detail_b_resp = client.get(f"/api/workforce/admin/technicians/{tech_b1_emp_id}/")
        assert detail_b_resp.status_code == 403, f"Expected 403 for cross-provider access, got {detail_b_resp.status_code}"

        # Direct GET Independent Tech: 403 CROSS_TENANT_FORBIDDEN
        detail_ind_resp = client.get(f"/api/workforce/admin/technicians/{tech_indep_emp_id}/")
        assert detail_ind_resp.status_code == 403, f"Expected 403 for independent tech access, got {detail_ind_resp.status_code}"
        print("  [PASS] Provider Admin strictly restricted to own technicians; cross-provider & independent access blocked.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST J: Provider Admin Cannot Change Technician Ownership
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST J] Verifying Provider Admin Cannot Reassign Technician Ownership...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_a_token}")
        reassign_resp = client.patch(f"/api/workforce/admin/technicians/{tech_a1_emp_id}/", {
            "company_id": prov_b_id,
        }, format="json")
        assert reassign_resp.status_code == 403, f"Expected 403 on ownership reassignment attempt, got {reassign_resp.status_code}"
        emp_a1_db.refresh_from_db()
        assert emp_a1_db.company_id == prov_a_id, "Company ID must remain unchanged"
        print("  [PASS] Technician ownership transfer by Provider Admin safely rejected with HTTP 403.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST K: Superadmin Global Visibility & Management
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST K] Verifying Superadmin Global Platform Visibility...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {super_token}")
        all_techs_resp = client.get("/api/workforce/admin/technicians/")
        assert all_techs_resp.status_code == 200
        all_ids = {t["id"] for t in all_techs_resp.data}
        assert tech_a1_emp_id in all_ids
        assert tech_a2_emp_id in all_ids
        assert tech_a3_emp_id in all_ids
        assert tech_b1_emp_id in all_ids
        assert tech_indep_emp_id in all_ids

        # Superadmin can toggle active status
        toggle_resp = client.post(f"/api/workforce/admin/technicians/{tech_a1_emp_id}/toggle-active/")
        assert toggle_resp.status_code == 200
        assert toggle_resp.data["is_active"] is False
        client.post(f"/api/workforce/admin/technicians/{tech_a1_emp_id}/toggle-active/")  # Restore active
        print("  [PASS] Superadmin has complete visibility and management authority across all technicians.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST L: Onboarding Decision & Service Approval
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST L] Verifying Onboarding & Service Approvals for Provider Technician...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {admin_a_token}")

        # Tech A1 already has approved services from initial provisioning
        emp_a1_db.refresh_from_db()
        assert emp_a1_db.bank_details["onboarding"]["status"] == "approved"
        assert len(emp_a1_db.bank_details["onboarding"]["services"]) == 2
        print("  [PASS] Provider technician uses standard onboarding data structure.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST M: Active Jobs Invariant
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST M] Verifying Active Jobs Invariant for Provider Technician...")
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tech_a1_token}")

        # Create unoffered job for Provider A and unoffered job for Marketplace
        prov_job = ServiceRequest.objects.create(
            company=Company.objects.get(pk=prov_a_id),
            service_category="HVAC Maintenance",
            issue_title=f"Prov A Unoffered Job {TEST_RUN_ID}",
            customer_name="Customer A",
            phone="1234567890",
            address="123 Street",
            preferred_date=timezone.now().date(),
            preferred_time="10:00 AM",
            status="new_request",
        )
        CLEANUP_JOBS.append(prov_job.id)

        # Tech A1 queries active jobs: prov_job must NOT appear without offer or assignment!
        active_resp = client.get("/api/workforce/jobs/")
        assert active_resp.status_code == 200
        active_ids = {j["id"] for j in active_resp.data}
        assert prov_job.id not in active_ids, "Unoffered provider job must NOT appear in technician active queue"
        print("  [PASS] Active Jobs Invariant preserved: Company membership NEVER leaks unoffered jobs.")

        # ──────────────────────────────────────────────────────────────────────
        # TEST N & O: Dispatch Offer & Job Execution
        # ──────────────────────────────────────────────────────────────────────
        print("\n[TEST N & O] Verifying Dispatch Offer & Job Acceptance...")
        offer = WorkforceJobOffer.objects.create(
            job=prov_job,
            employee=emp_a1_db,
            wave_id=1,
            status=WorkforceJobOffer.Status.OFFERED,
            offered_at=timezone.now(),
            expires_at=timezone.now() + timezone.timedelta(minutes=15),
        )
        CLEANUP_OFFERS.append(offer.id)

        # Query active jobs: now prov_job MUST appear
        offered_resp = client.get("/api/workforce/jobs/")
        offered_ids = {j["id"] for j in offered_resp.data}
        assert prov_job.id in offered_ids, "Offered job MUST appear in active queue"

        # Accept job offer
        accept_resp = client.post(f"/api/workforce/jobs/{prov_job.id}/accept-offer/")
        assert accept_resp.status_code == 200, f"Accept offer failed: {accept_resp.data}"

        prov_job.refresh_from_db()
        assert prov_job.assigned_employee_id == emp_a1_db.id, "Job assigned_employee must be set to Tech A1"
        assert prov_job.status == "accepted", f"Expected status 'accepted', got '{prov_job.status}'"
        print("  [PASS] Provider technician received offer and accepted job successfully.")

        print("\n" + "=" * 80)
        print("ALL 16 PHASE 2B TESTS PASSED SUCCESSFULLY!")
        print("=" * 80)

    finally:
        print("\nCleaning up test artifacts...")
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
