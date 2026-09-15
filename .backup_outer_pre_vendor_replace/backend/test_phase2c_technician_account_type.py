"""
test_phase2c_technician_account_type.py
Rigorously tests Workforce Phase 2C — Technician Account Type Selection & Provider Association.

Invariants tested:
A. Public Service Providers List: Only active providers, safe fields.
B. Inactive providers are excluded from public listing.
C. Public Service Providers Search filtering (?search=).
D. Independent Technician Signup: company=NULL, is_independent=True, association_status=INDEPENDENT.
E. Provider Technician Signup: company=NULL, is_independent=True, association_status=PENDING.
F. Provider Technician Signup creates WorkforceProviderJoinRequest with status=PENDING.
G. Signup with non-existent provider fails with 400 INVALID_SERVICE_PROVIDER.
H. Signup with inactive provider fails with 400 INVALID_SERVICE_PROVIDER.
I. Provider Admin A application queue includes pending join requests for Provider A.
J. Provider Admin A application queue excludes Independent techs and Provider B join requests.
K. Superadmin application queue has global visibility across all providers and independent techs.
L. Provider Admin A detail view of Provider A join request candidate succeeds.
M. Provider Admin B detail view of Provider A candidate fails with 403 CROSS_TENANT_FORBIDDEN.
N. Provider Admin A approves join request -> atomically assigns User.company=Provider A, Employee.company=Provider A.
O. Provider Admin A rejects join request -> keeps User.company=NULL, Employee.company=NULL, status=REJECTED.
P. Provider Admin B cannot decide Provider A join request (403 CROSS_TENANT_FORBIDDEN).
Q. Full Application Approval with pending join request atomically approves join request and assigns company.
R. Login and /auth/me/ endpoints return correct association_status, requested_provider_id, and is_independent flags.
"""
import os
import sys
import uuid
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

from companies.models import Company, Region
from employees.models import Employee
from accounts.models import User
from workforce_api.models import WorkforceProviderJoinRequest, WorkforceServiceCatalog



def get_unique_suffix():
    return uuid.uuid4().hex[:8]


def create_region():
    region, _ = Region.objects.get_or_create(
        code="US",
        defaults={
            "name": "United States",
            "currency": "USD",
            "currency_symbol": "$",
        }
    )
    return region



def create_provider(name="Acme Service Corp", is_active=True):
    suffix = get_unique_suffix()
    region = create_region()
    return Company.objects.create(
        company_name=f"{name} {suffix}",
        display_id=f"PROV-{suffix[:6].upper()}",
        slug=f"acme-{suffix}",
        industry="Home Maintenance",
        primary_country="US",
        region=region,
        is_active=is_active,
    )


def create_provider_admin(company, username="provadmin"):
    suffix = get_unique_suffix()
    user = User.objects.create_user(
        username=f"{username}_{suffix}",
        email=f"{username}_{suffix}@testprovider.com",
        password="ValidPassword123!",
        role="service_provider_admin",
        company=company,
        is_staff=True,
    )
    return user


def create_superadmin():
    suffix = get_unique_suffix()
    user = User.objects.create_superuser(
        username=f"superadmin_{suffix}",
        email=f"superadmin_{suffix}@workforce.test",
        password="ValidPassword123!",
        role="superadmin",
    )
    return user


def run_tests():
    client = APIClient()
    print("=" * 80)
    print("WORKFORCE PHASE 2C: TECHNICIAN ACCOUNT TYPE & PROVIDER ASSOCIATION AUDIT")
    print("=" * 80)

    passed = 0
    total = 18

    # ── Test A: Public Service Providers List ────────────────────────────────
    print("\n[TEST A] Public Service Providers List returns active providers with safe fields")
    active_prov = create_provider(name="Solar Pros Alpha", is_active=True)
    resp = client.get("/api/workforce/service-providers/public/")
    assert resp.status_code == status.HTTP_200_OK, f"Expected 200, got {resp.status_code}"
    data = resp.json()
    assert isinstance(data, list)
    prov_entry = next((p for p in data if p["id"] == active_prov.id), None)
    assert prov_entry is not None, "Active provider not found in public list"
    assert prov_entry["company_name"] == active_prov.company_name
    assert prov_entry["display_id"] == active_prov.display_id
    assert prov_entry["slug"] == active_prov.slug
    assert prov_entry["industry"] == "Home Maintenance"
    assert "admin_password" not in prov_entry
    assert "bank_details" not in prov_entry
    print("  -> PASSED: Active provider returned with safe public fields only.")
    passed += 1

    # ── Test B: Inactive Providers Excluded ──────────────────────────────────
    print("\n[TEST B] Inactive Service Providers are excluded from public list")
    inactive_prov = create_provider(name="Inactive Omega", is_active=False)
    resp = client.get("/api/workforce/service-providers/public/")
    data = resp.json()
    assert not any(p["id"] == inactive_prov.id for p in data), "Inactive provider appeared in public list!"
    print("  -> PASSED: Inactive providers strictly excluded.")
    passed += 1

    # ── Test C: Public Provider Search Filter ────────────────────────────────
    print("\n[TEST C] Public Service Provider search query filtering")
    search_term = active_prov.slug
    resp = client.get(f"/api/workforce/service-providers/public/?search={search_term}")
    data = resp.json()
    assert len(data) >= 1
    assert any(p["id"] == active_prov.id for p in data)
    print(f"  -> PASSED: Search by '{search_term}' returned matching provider.")
    passed += 1

    # ── Test D: Independent Technician Signup ───────────────────────────────
    print("\n[TEST D] Independent Technician Signup -> company=NULL, is_independent=True")
    suffix_ind = get_unique_suffix()
    ind_email = f"indie_{suffix_ind}@example.com"
    resp = client.post("/api/workforce/signup/", {
        "first_name": "Indie",
        "last_name": "Tech",
        "email": ind_email,
        "mobile_number": f"12345{suffix_ind[:5]}",
        "password": "ValidPassword123!",
        "account_type": "independent",
    }, format="json")
    assert resp.status_code == status.HTTP_201_CREATED, f"Signup failed: {resp.data}"
    ind_res = resp.json()
    assert ind_res["user"]["company_id"] is None
    assert ind_res["user"]["is_independent"] is True
    assert ind_res["user"]["association_status"] == "INDEPENDENT"

    # Verify DB state
    user_ind = User.objects.get(email=ind_email)
    emp_ind = Employee.objects.get(user=user_ind)
    assert user_ind.company_id is None
    assert emp_ind.company_id is None
    assert emp_ind.bank_details["onboarding"]["account_type"] == "independent"
    assert emp_ind.bank_details["onboarding"]["join_request"] is None
    print("  -> PASSED: Independent technician created with company=NULL.")
    passed += 1

    # ── Test E: Provider Technician Signup Pending State ────────────────────
    print("\n[TEST E] Provider Technician Signup -> company=NULL, association_status=PENDING")
    prov_alpha = create_provider(name="Apex Solutions Alpha")
    suffix_p = get_unique_suffix()
    prov_tech_email = f"apprentice_{suffix_p}@example.com"
    resp = client.post("/api/workforce/signup/", {
        "first_name": "Apprentice",
        "last_name": "Tech",
        "email": prov_tech_email,
        "mobile_number": f"98765{suffix_p[:5]}",
        "password": "ValidPassword123!",
        "account_type": "provider",
        "provider_id": prov_alpha.id,
    }, format="json")
    assert resp.status_code == status.HTTP_201_CREATED, f"Signup failed: {resp.data}"
    prov_res = resp.json()
    assert prov_res["user"]["company_id"] is None, "CRITICAL: company_id must NOT be assigned on signup!"
    assert prov_res["user"]["is_independent"] is True
    assert prov_res["user"]["association_status"] == "PENDING"
    assert prov_res["user"]["requested_provider_id"] == prov_alpha.id
    assert prov_res["user"]["requested_provider_name"] == prov_alpha.company_name

    user_p = User.objects.get(email=prov_tech_email)
    emp_p = Employee.objects.get(user=user_p)
    assert user_p.company_id is None
    assert emp_p.company_id is None
    print("  -> PASSED: Provider technician created with company=NULL awaiting approval.")
    passed += 1

    # ── Test F: WorkforceProviderJoinRequest Created ────────────────────────
    print("\n[TEST F] WorkforceProviderJoinRequest created with status=PENDING")
    join_req = WorkforceProviderJoinRequest.objects.filter(technician=emp_p, provider=prov_alpha).first()
    assert join_req is not None, "Join request record was not created in DB!"
    assert join_req.status == WorkforceProviderJoinRequest.Status.PENDING
    assert emp_p.bank_details["onboarding"]["join_request"]["status"] == "PENDING"
    assert emp_p.bank_details["onboarding"]["join_request"]["provider_id"] == prov_alpha.id
    print("  -> PASSED: Join request record verified in DB and bank_details.")
    passed += 1

    # ── Test G: Signup with Non-Existent Provider ───────────────────────────
    print("\n[TEST G] Signup with non-existent provider fails with 400 INVALID_SERVICE_PROVIDER")
    suffix_inv = get_unique_suffix()
    resp = client.post("/api/workforce/signup/", {
        "first_name": "Invalid",
        "last_name": "ProviderTech",
        "email": f"inv_{suffix_inv}@example.com",
        "mobile_number": f"55555{suffix_inv[:5]}",
        "password": "ValidPassword123!",
        "account_type": "provider",
        "provider_id": 999999,
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("code") == "INVALID_SERVICE_PROVIDER"
    print("  -> PASSED: Non-existent provider rejected with 400 INVALID_SERVICE_PROVIDER.")
    passed += 1

    # ── Test H: Signup with Inactive Provider ────────────────────────────────
    print("\n[TEST H] Signup with inactive provider fails with 400 INVALID_SERVICE_PROVIDER")
    suffix_inact = get_unique_suffix()
    resp = client.post("/api/workforce/signup/", {
        "first_name": "Inactive",
        "last_name": "Candidate",
        "email": f"inact_{suffix_inact}@example.com",
        "mobile_number": f"77777{suffix_inact[:5]}",
        "password": "ValidPassword123!",
        "account_type": "provider",
        "provider_id": inactive_prov.id,
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert resp.json().get("code") == "INVALID_SERVICE_PROVIDER"
    print("  -> PASSED: Inactive provider rejected with 400 INVALID_SERVICE_PROVIDER.")
    passed += 1

    # ── Test I: Provider Admin Application Queue Visibility ──────────────────
    print("\n[TEST I] Provider Admin A application queue includes pending join requests for Provider A")
    admin_alpha = create_provider_admin(prov_alpha, username="admin_alpha")
    client.force_authenticate(user=admin_alpha)
    resp = client.get("/api/workforce/admin/applications/")
    assert resp.status_code == status.HTTP_200_OK
    ids = [app["id"] for app in resp.json()]
    assert emp_p.id in ids, "Pending join request candidate must be visible in target provider's queue"
    print("  -> PASSED: Candidate with pending join request visible to target Provider Admin.")
    passed += 1

    # ── Test J: Queue Isolation from other Providers and Independents ───────
    print("\n[TEST J] Provider Admin A queue excludes Independent techs and Provider B join requests")
    prov_beta = create_provider(name="Provider Beta")
    admin_beta = create_provider_admin(prov_beta, username="admin_beta")

    # Create candidate requesting Provider Beta
    suffix_beta = get_unique_suffix()
    client.force_authenticate(user=None)
    resp = client.post("/api/workforce/signup/", {
        "first_name": "BetaTech",
        "last_name": "Candidate",
        "email": f"betatech_{suffix_beta}@example.com",
        "mobile_number": f"88888{suffix_beta[:5]}",
        "password": "ValidPassword123!",
        "account_type": "provider",
        "provider_id": prov_beta.id,
    }, format="json")
    emp_beta = Employee.objects.get(user__email=f"betatech_{suffix_beta}@example.com")

    # Provider Admin Alpha checks queue
    client.force_authenticate(user=admin_alpha)
    resp = client.get("/api/workforce/admin/applications/")
    alpha_ids = [app["id"] for app in resp.json()]
    assert emp_p.id in alpha_ids
    assert emp_beta.id not in alpha_ids, "Provider A queue leaked Provider B join request!"
    assert emp_ind.id not in alpha_ids, "Provider A queue leaked Independent candidate!"
    print("  -> PASSED: Provider A queue properly isolated from Provider B and Independent candidates.")
    passed += 1

    # ── Test K: Superadmin Global Queue Visibility ──────────────────────────
    print("\n[TEST K] Superadmin queue has global visibility across all candidates")
    superadmin = create_superadmin()
    client.force_authenticate(user=superadmin)
    resp = client.get("/api/workforce/admin/applications/")
    assert resp.status_code == status.HTTP_200_OK
    super_ids = [app["id"] for app in resp.json()]
    assert emp_p.id in super_ids
    assert emp_beta.id in super_ids
    assert emp_ind.id in super_ids
    print("  -> PASSED: Superadmin has full visibility across all applications.")
    passed += 1

    # ── Test L: Provider Admin Detail View of Join Request Candidate ─────────
    print("\n[TEST L] Provider Admin A detail view of pending join request candidate succeeds")
    client.force_authenticate(user=admin_alpha)
    resp = client.get(f"/api/workforce/admin/applications/{emp_p.id}/")
    assert resp.status_code == status.HTTP_200_OK
    dossier = resp.json()
    assert dossier["id"] == emp_p.id
    assert dossier["join_request"]["status"] == "PENDING"
    assert dossier["association_status"] == "PENDING"
    print("  -> PASSED: Dossier fetched with join request details.")
    passed += 1

    # ── Test M: Cross-Tenant Detail View Forbidden ───────────────────────────
    print("\n[TEST M] Provider Admin B detail view of Provider A candidate fails with 403")
    client.force_authenticate(user=admin_beta)
    resp = client.get(f"/api/workforce/admin/applications/{emp_p.id}/")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json().get("code") == "CROSS_TENANT_FORBIDDEN"
    print("  -> PASSED: Cross-tenant application detail access blocked with 403.")
    passed += 1

    # ── Test N: Provider Admin Approves Join Request ─────────────────────────
    print("\n[TEST N] Provider Admin A approves join request -> atomically sets company ownership")
    client.force_authenticate(user=admin_alpha)
    resp = client.post(f"/api/workforce/admin/join-requests/{emp_p.id}/decide/", {
        "action": "approve"
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "APPROVED"

    # Verify atomic DB updates
    user_p.refresh_from_db()
    emp_p.refresh_from_db()
    assert user_p.company_id == prov_alpha.id, "User.company_id was not set to Provider A!"
    assert emp_p.company_id == prov_alpha.id, "Employee.company_id was not set to Provider A!"

    join_req.refresh_from_db()
    assert join_req.status == WorkforceProviderJoinRequest.Status.APPROVED
    assert join_req.decided_by == admin_alpha
    assert emp_p.bank_details["onboarding"]["join_request"]["status"] == "APPROVED"
    print("  -> PASSED: User and Employee atomically enrolled under Provider A upon approval.")
    passed += 1

    # ── Test O: Provider Admin Rejects Join Request ─────────────────────────
    print("\n[TEST O] Provider Admin B rejects join request -> keeps company=NULL, status=REJECTED")
    client.force_authenticate(user=admin_beta)
    resp = client.post(f"/api/workforce/admin/join-requests/{emp_beta.id}/decide/", {
        "action": "reject",
        "reason": "Not currently onboarding in your area."
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["status"] == "REJECTED"

    user_beta = User.objects.get(email=f"betatech_{suffix_beta}@example.com")
    emp_beta.refresh_from_db()
    user_beta.refresh_from_db()
    assert user_beta.company_id is None
    assert emp_beta.company_id is None

    join_req_beta = WorkforceProviderJoinRequest.objects.get(technician=emp_beta, provider=prov_beta)
    assert join_req_beta.status == WorkforceProviderJoinRequest.Status.REJECTED
    assert join_req_beta.rejection_reason == "Not currently onboarding in your area."
    assert emp_beta.bank_details["onboarding"]["join_request"]["status"] == "REJECTED"
    print("  -> PASSED: Rejection leaves technician independent with company=NULL.")
    passed += 1

    # ── Test P: Cross-Tenant Join Request Decision Forbidden ─────────────────
    print("\n[TEST P] Provider Admin B cannot decide Provider A join request (403)")
    # Create another tech for Prov A
    suffix_cross = get_unique_suffix()
    client.force_authenticate(user=None)
    client.post("/api/workforce/signup/", {
        "first_name": "CrossTech",
        "last_name": "Candidate",
        "email": f"crosstech_{suffix_cross}@example.com",
        "mobile_number": f"34567{suffix_cross[:5]}",
        "password": "ValidPassword123!",
        "account_type": "provider",
        "provider_id": prov_alpha.id,
    }, format="json")
    emp_cross = Employee.objects.get(user__email=f"crosstech_{suffix_cross}@example.com")

    # Provider Admin B attempts to approve Prov A's tech
    client.force_authenticate(user=admin_beta)
    resp = client.post(f"/api/workforce/admin/join-requests/{emp_cross.id}/decide/", {
        "action": "approve"
    }, format="json")
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json().get("code") == "CROSS_TENANT_FORBIDDEN"
    print("  -> PASSED: Cross-tenant join request decision blocked with 403.")
    passed += 1

    # ── Test Q: Full Application Approval with Pending Join Request ──────────
    print("\n[TEST Q] Full Application Approval atomically approves pending join request")
    # Prepare documents and services for emp_cross
    svc = WorkforceServiceCatalog.objects.create(
        category="Plumbing",
        name=f"Drain Cleaning {suffix_cross}",
        price=75.00,
        is_active=True,
    )

    bank_details = emp_cross.bank_details or {}
    onboarding = bank_details.get("onboarding", {})
    onboarding["documents"] = {
        "government_id": {"status": "approved", "title": "Government ID"},
    }
    onboarding["services"] = [
        {"id": svc.id, "name": svc.name, "status": "approved"},
    ]
    onboarding["status"] = "submitted"
    bank_details["onboarding"] = onboarding
    emp_cross.bank_details = bank_details
    emp_cross.save()

    # Provider Admin Alpha approves candidate application
    client.force_authenticate(user=admin_alpha)
    resp = client.post(f"/api/workforce/admin/applications/{emp_cross.id}/approve/")
    assert resp.status_code == status.HTTP_200_OK

    emp_cross.refresh_from_db()
    user_cross = User.objects.get(email=f"crosstech_{suffix_cross}@example.com")
    assert emp_cross.company_id == prov_alpha.id
    assert user_cross.company_id == prov_alpha.id
    assert emp_cross.bank_details["onboarding"]["status"] == "approved"
    assert emp_cross.bank_details["onboarding"]["join_request"]["status"] == "APPROVED"
    print("  -> PASSED: Application approval atomically approved join request and assigned company.")
    passed += 1

    # ── Test R: Login and /auth/me/ Response Consistency ─────────────────────
    print("\n[TEST R] Login and /auth/me/ return correct association_status and provider metadata")
    client.force_authenticate(user=None)

    # 1. Independent tech login
    resp_ind_login = client.post("/api/auth/login/", {
        "identifier": ind_email,
        "password": "ValidPassword123!",
    }, format="json")
    assert resp_ind_login.status_code == status.HTTP_200_OK
    ind_auth_data = resp_ind_login.json()["user"]
    assert ind_auth_data["is_independent"] is True
    assert ind_auth_data["association_status"] == "INDEPENDENT"
    assert ind_auth_data["company"] is None

    # 2. Approved tech login
    resp_appr_login = client.post("/api/auth/login/", {
        "identifier": prov_tech_email,
        "password": "ValidPassword123!",
    }, format="json")
    assert resp_appr_login.status_code == status.HTTP_200_OK
    appr_auth_data = resp_appr_login.json()["user"]
    assert appr_auth_data["is_independent"] is False
    assert appr_auth_data["association_status"] == "APPROVED"
    assert appr_auth_data["provider_id"] == prov_alpha.id

    # 3. Approved tech /auth/me/
    client.force_authenticate(user=user_p)
    resp_me = client.get("/api/auth/me/")
    assert resp_me.status_code == status.HTTP_200_OK
    me_data = resp_me.json()
    assert me_data["is_independent"] is False
    assert me_data["association_status"] == "APPROVED"
    assert me_data["provider_id"] == prov_alpha.id
    print("  -> PASSED: Login and /auth/me/ responses consistently reflect association states.")
    passed += 1

    print("\n" + "=" * 80)
    print(f"AUDIT COMPLETE: {passed}/{total} TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
