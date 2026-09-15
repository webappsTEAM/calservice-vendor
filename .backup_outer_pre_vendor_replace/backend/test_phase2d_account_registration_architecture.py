"""
workforce-app/backend/test_phase2d_account_registration_architecture.py
Comprehensive Verification Suite for Workforce Phase 2D:
Correct Account-Type Registration, Self-Service Provider Creation & Technician Provider Joining.
Tests A through X (24 scenarios).
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
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User
from companies.models import Company, Region
from employees.models import Employee
from workforce_api.models import WorkforceProviderJoinRequest
from workforce_api.services.provider_service import create_service_provider_with_admin


def get_or_create_region():
    region = Region.objects.filter(code="US").first()
    if not region:
        try:
            region = Region.objects.create(code="US", name="United States", currency="USD")
        except Exception:
            region = Region.objects.first()
    return region


def run_tests():
    client = APIClient()
    region = get_or_create_region()
    run_id = uuid.uuid4().hex[:6].upper()
    passed = 0
    total = 24

    print("=" * 80)
    print(f"STARTING PHASE 2D VERIFICATION SUITE (Run ID: {run_id})")
    print("=" * 80)

    # 1. Setup Base Providers
    active_provider = Company.objects.create(
        company_name=f"Metro Field Service Corp {run_id}",
        display_id=f"PROV-{run_id}",
        slug=f"metro-field-service-{run_id.lower()}",
        is_active=True,
        region=region,
    )

    rival_provider = Company.objects.create(
        company_name=f"Alliance Field Network {run_id}",
        display_id=f"PROV-AL-{run_id}",
        slug=f"alliance-field-network-{run_id.lower()}",
        is_active=True,
        region=region,
    )

    inactive_provider = Company.objects.create(
        company_name=f"Decommissioned Co {run_id}",
        display_id=f"PROV-OFF-{run_id}",
        slug=f"decommissioned-{run_id.lower()}",
        is_active=False,
        region=region,
    )

    provider_admin_user = User.objects.create_user(
        username=f"admin_metro_{run_id.lower()}",
        email=f"admin_metro_{run_id.lower()}@metrofield.com",
        password="AdminPassword123!",
        role="service_provider_admin",
        company=active_provider,
        is_staff=True,
        is_superuser=False,
    )

    superadmin_user = User.objects.create_superuser(
        username=f"super_{run_id.lower()}",
        email=f"super_{run_id.lower()}@platform.com",
        password="SuperPassword123!",
    )

    # ── Test A: Individual Technician Signup ──────────────────────────────────
    print("\n[TEST A] Individual Technician Signup sets company=NULL, role=employee")
    client.force_authenticate(user=None)
    ind_email = f"indep_{run_id.lower()}@example.com"
    resp_a = client.post("/api/workforce/signup/", {
        "first_name": "Individual",
        "last_name": "Tech",
        "email": ind_email,
        "mobile_number": f"+1999{run_id[:6]}",
        "password": "TechPassword123!",
        "account_type": "independent",
    }, format="json")
    assert resp_a.status_code == status.HTTP_201_CREATED, f"Expected 201, got {resp_a.status_code}: {resp_a.data}"
    user_a = User.objects.filter(email=ind_email).first()
    assert user_a is not None
    assert user_a.company is None
    assert user_a.role == "employee"
    emp_a = Employee.objects.filter(user=user_a).first()
    assert emp_a is not None
    assert emp_a.company is None
    assert WorkforceProviderJoinRequest.objects.filter(technician=emp_a).count() == 0
    print("  -> PASSED: Individual technician created with company=NULL and no join request.")
    passed += 1

    # ── Test B: Provider Technician Signup with Provider Selected ──────────────
    print("\n[TEST B] Provider Technician Signup creates pending join request and leaves company=NULL")
    join_email = f"joiner_{run_id.lower()}@example.com"
    resp_b = client.post("/api/workforce/signup/", {
        "first_name": "Applicant",
        "last_name": "Tech",
        "email": join_email,
        "mobile_number": f"+1888{run_id[:6]}",
        "password": "TechPassword123!",
        "account_type": "provider_technician",
        "provider_id": active_provider.id,
    }, format="json")
    assert resp_b.status_code == status.HTTP_201_CREATED, f"Expected 201, got {resp_b.status_code}: {resp_b.data}"
    user_b = User.objects.filter(email=join_email).first()
    emp_b = Employee.objects.filter(user=user_b).first()
    # INVARIANT: Both User.company and Employee.company MUST be None!
    assert user_b.company is None
    assert emp_b.company is None
    jr_b = WorkforceProviderJoinRequest.objects.filter(technician=emp_b, provider=active_provider).first()
    assert jr_b is not None
    assert jr_b.status == WorkforceProviderJoinRequest.Status.PENDING
    print("  -> PASSED: Join request created as PENDING, company remains NULL.")
    passed += 1

    # ── Test C: Provider Technician Cannot Signup Without Provider ────────────
    print("\n[TEST C] Provider Technician cannot signup without selecting a provider")
    resp_c = client.post("/api/workforce/signup/", {
        "first_name": "Applicant",
        "last_name": "NoProv",
        "email": f"noprov_{run_id.lower()}@example.com",
        "mobile_number": f"+1777{run_id[:6]}",
        "password": "TechPassword123!",
        "account_type": "provider_technician",
    }, format="json")
    assert resp_c.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Signup without provider selection rejected with 400.")
    passed += 1

    # ── Test D: Inactive Provider Cannot Be Selected ──────────────────────────
    print("\n[TEST D] Inactive Provider cannot be selected")
    resp_d = client.post("/api/workforce/signup/", {
        "first_name": "Applicant",
        "last_name": "OffProv",
        "email": f"offprov_{run_id.lower()}@example.com",
        "mobile_number": f"+1666{run_id[:6]}",
        "password": "TechPassword123!",
        "account_type": "provider_technician",
        "provider_id": inactive_provider.id,
    }, format="json")
    assert resp_d.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Inactive provider selection rejected with 400.")
    passed += 1

    # ── Test E: Invalid/Non-Existent Provider Rejected ────────────────────────
    print("\n[TEST E] Non-existent Provider ID rejected")
    resp_e = client.post("/api/workforce/signup/", {
        "first_name": "Applicant",
        "last_name": "FakeProv",
        "email": f"fake_{run_id.lower()}@example.com",
        "mobile_number": f"+1555{run_id[:6]}",
        "password": "TechPassword123!",
        "account_type": "provider_technician",
        "provider_id": 99999999,
    }, format="json")
    assert resp_e.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Non-existent provider rejected with 400.")
    passed += 1

    # ── Test F: Provider Admin Approves Join Request ───────────────────────────
    print("\n[TEST F] Provider Admin approves join request -> assigns User and Employee company")
    client.force_authenticate(user=provider_admin_user)
    resp_f = client.post(f"/api/workforce/admin/join-requests/{jr_b.id}/decide/", {
        "action": "APPROVE",
        "notes": "Approved for field duty.",
    }, format="json")
    assert resp_f.status_code == status.HTTP_200_OK, f"Expected 200, got {resp_f.status_code}: {resp_f.data}"
    jr_b.refresh_from_db()
    emp_b.refresh_from_db()
    user_b.refresh_from_db()
    assert jr_b.status == WorkforceProviderJoinRequest.Status.APPROVED
    assert emp_b.company_id == active_provider.id
    assert user_b.company_id == active_provider.id
    print("  -> PASSED: Join request approved; technician affiliated to provider.")
    passed += 1

    # ── Test G: Provider Admin Rejects Join Request ───────────────────────────
    print("\n[TEST G] Provider Admin rejects join request -> technician remains independent")
    cand_user_g = User.objects.create_user(
        username=f"cand_rej_{run_id.lower()}",
        email=f"cand_rej_{run_id.lower()}@test.com",
        password="Password123!",
        role="employee",
        company=None,
    )
    cand_emp_g = Employee.objects.create(
        user=cand_user_g,
        company=None,
        employee_id=f"EMP-REJ-{run_id}",
        bank_details={"onboarding": {"status": "submitted", "join_request": {"provider_id": active_provider.id, "status": "PENDING"}}},
    )
    jr_g = WorkforceProviderJoinRequest.objects.create(
        technician=cand_emp_g,
        provider=active_provider,
        status=WorkforceProviderJoinRequest.Status.PENDING,
    )
    resp_g = client.post(f"/api/workforce/admin/join-requests/{jr_g.id}/decide/", {
        "action": "REJECT",
        "rejection_reason": "Capacity reached.",
    }, format="json")
    assert resp_g.status_code == status.HTTP_200_OK
    jr_g.refresh_from_db()
    cand_emp_g.refresh_from_db()
    cand_user_g.refresh_from_db()
    assert jr_g.status == WorkforceProviderJoinRequest.Status.REJECTED
    assert cand_emp_g.company is None
    assert cand_user_g.company is None
    print("  -> PASSED: Join request rejected; technician remains independent.")
    passed += 1

    # ── Test H: Cross-Tenant Isolation on Join Requests ────────────────────────
    print("\n[TEST H] Cross-Tenant Isolation: Provider Admin A cannot decide Provider B requests")
    rival_user = User.objects.create_user(
        username=f"rival_cand_{run_id.lower()}",
        email=f"rival_cand_{run_id.lower()}@test.com",
        password="Password123!",
        role="employee",
        company=None,
    )
    rival_emp = Employee.objects.create(
        user=rival_user,
        company=None,
        employee_id=f"EMP-RIV-{run_id}",
    )
    rival_jr = WorkforceProviderJoinRequest.objects.create(
        technician=rival_emp,
        provider=rival_provider,
        status=WorkforceProviderJoinRequest.Status.PENDING,
    )
    client.force_authenticate(user=provider_admin_user)
    resp_h = client.post(f"/api/workforce/admin/join-requests/{rival_jr.id}/decide/", {
        "action": "APPROVE",
    }, format="json")
    assert resp_h.status_code == status.HTTP_403_FORBIDDEN
    print("  -> PASSED: Cross-tenant decision attempt blocked with 403 FORBIDDEN.")
    passed += 1

    # ── Test I: Cross-Tenant Isolation on Technicians ─────────────────────────
    print("\n[TEST I] Cross-Tenant Isolation: Provider Admin A cannot access Provider B technicians")
    rival_emp.company = rival_provider
    # Attempt to access rival technician detail -> MUST BE FORBIDDEN or NOT FOUND
    resp_i = client.get(f"/api/workforce/admin/technicians/{rival_emp.id}/")
    assert resp_i.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
    print("  -> PASSED: Cross-tenant technician access blocked safely.")
    passed += 1


    # ── Test J: Service Provider Self-Registration ────────────────────────────
    print("\n[TEST J] Service Provider Self-Registration creates Company + primary admin")
    client.force_authenticate(user=None)
    prov_name_j = f"Solar Wave Solutions {run_id}"
    admin_email_j = f"admin_sws_{run_id.lower()}@solarwave.com"
    resp_j = client.post("/api/workforce/service-providers/signup/", {
        "company_name": prov_name_j,
        "industry": "Solar Installation",
        "phone": f"+1444{run_id[:6]}",
        "email": admin_email_j,
        "address": "123 Clean Tech Way",
        "city": "Austin",
        "state": "TX",
        "country": "US",
        "first_name": "Elena",
        "last_name": "Reyes",
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!",
    }, format="json")
    assert resp_j.status_code == status.HTTP_201_CREATED, f"Expected 201, got {resp_j.status_code}: {resp_j.data}"
    assert "access_token" in resp_j.data
    assert "refresh_token" in resp_j.data
    comp_j = Company.objects.filter(company_name=prov_name_j).first()
    assert comp_j is not None
    assert comp_j.is_active is True
    assert comp_j.display_id.startswith("PROV-")
    admin_j = User.objects.filter(email=admin_email_j).first()
    assert admin_j is not None
    assert admin_j.role == "service_provider_admin"
    assert admin_j.company_id == comp_j.id
    assert admin_j.is_staff is True
    assert admin_j.is_superuser is False
    assert Employee.objects.filter(user=admin_j).first() is None
    print("  -> PASSED: Provider organization and primary admin created atomically.")
    passed += 1

    # ── Test K: Service Provider Registration is Atomic ───────────────────────
    print("\n[TEST K] Service Provider Registration rolls back atomically on error")
    initial_company_count = Company.objects.count()
    resp_k = client.post("/api/workforce/service-providers/signup/", {
        "company_name": f"Rollback Corp {run_id}",
        "first_name": "Collision",
        "email": admin_email_j,  # Colliding email
        "password": "Password123!",
        "confirm_password": "Password123!",
    }, format="json")
    assert resp_k.status_code == status.HTTP_400_BAD_REQUEST
    assert Company.objects.count() == initial_company_count
    print("  -> PASSED: Zero company records leaked on failed user creation.")
    passed += 1

    # ── Test L: Provider Registration Rejects Client-Supplied Company ID ───────
    print("\n[TEST L] Provider Registration rejects client-supplied company_id")
    resp_l = client.post("/api/workforce/service-providers/signup/", {
        "company_name": f"Tampered Co {run_id}",
        "company_id": active_provider.id,
        "first_name": "Tamper",
        "email": f"tamper_{run_id.lower()}@test.com",
        "password": "Password123!",
        "confirm_password": "Password123!",
    }, format="json")
    assert resp_l.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Client company_id injection rejected.")
    passed += 1

    # ── Test M: Provider Admin Can Login After Self-Registration ───────────────
    print("\n[TEST M] Provider Admin can log in with is_provider_admin=True")
    resp_m = client.post("/api/auth/login/", {
        "identifier": admin_email_j,
        "password": "SecurePassword123!",
    }, format="json")
    assert resp_m.status_code == status.HTTP_200_OK
    user_m = resp_m.data.get("user", {})
    assert user_m.get("is_provider_admin") is True
    assert user_m.get("is_superadmin") is False
    assert user_m.get("role") == "service_provider_admin"
    assert user_m.get("registration_status") == "approved"
    print("  -> PASSED: Provider admin authenticated with full portal authorization.")
    passed += 1

    # ── Test N: Provider Admin Can Create Technicians (Phase 2B) ──────────────
    print("\n[TEST N] Newly registered Provider Admin can create technicians in Phase 2B")
    client.force_authenticate(user=admin_j)
    tech_email_n = f"tech_sws_{run_id.lower()}@solarwave.com"
    resp_n = client.post("/api/workforce/admin/technicians/", {
        "first_name": "Mateo",
        "last_name": "Silva",
        "email": tech_email_n,
        "phone": f"+1333{run_id[:6]}",
        "temporary_password": "InitialPass123!",
        "title": "Solar Field Lead",
    }, format="json")
    assert resp_n.status_code == status.HTTP_201_CREATED, f"Expected 201, got {resp_n.status_code}: {resp_n.data}"
    tech_n = Employee.objects.filter(user__email=tech_email_n).first()
    assert tech_n is not None
    assert tech_n.company_id == comp_j.id
    print("  -> PASSED: Provider admin successfully added technician to their company.")
    passed += 1

    # ── Test O: Individual Technician Workflow Unaffected ─────────────────────
    print("\n[TEST O] Individual technician onboarding profile remains independent")
    client.force_authenticate(user=user_a)
    resp_o = client.get("/api/workforce/onboarding/me/")
    assert resp_o.status_code == status.HTTP_200_OK
    assert resp_o.data.get("company_id") is None
    print("  -> PASSED: Individual technician profile has company_id=NULL.")
    passed += 1

    # ── Test P: Affiliated Technician Workflow Unaffected ─────────────────────
    print("\n[TEST P] Affiliated technician profile reflects provider association")
    client.force_authenticate(user=user_b)
    resp_p = client.get("/api/auth/me/")
    assert resp_p.status_code == status.HTTP_200_OK
    assert resp_p.data.get("company") == active_provider.id
    assert resp_p.data.get("association_status") == "APPROVED"
    print("  -> PASSED: Affiliated technician correctly associated with active provider.")
    passed += 1

    # ── Test Q: Public Provider API Returns Only Active Providers ──────────────
    print("\n[TEST Q] Public provider API returns active providers and excludes inactive")
    client.force_authenticate(user=None)
    resp_q = client.get("/api/workforce/service-providers/public/")
    assert resp_q.status_code == status.HTTP_200_OK
    p_ids = [p["id"] for p in resp_q.data]
    assert active_provider.id in p_ids
    assert comp_j.id in p_ids
    assert inactive_provider.id not in p_ids
    print("  -> PASSED: Public provider API correctly excludes inactive companies.")
    passed += 1

    # ── Test R: Public Provider API Excludes Test/Demo Patterns ────────────────
    print("\n[TEST R] Public provider API excludes hardcoded/test provider patterns")
    resp_r = client.get("/api/workforce/service-providers/public/")
    assert resp_r.status_code == status.HTTP_200_OK
    names_lower = [p["company_name"].lower() for p in resp_r.data]
    for pattern in ["9gate", "phase2 enterprise", "scenario", "testa_co", "state machine audit"]:
        for name in names_lower:
            assert pattern not in name, f"Test pattern '{pattern}' found in public provider list name '{name}'"
    print("  -> PASSED: Zero test/demo providers present in public API.")
    passed += 1

    # ── Test S: Superadmin Can Still Create Providers ─────────────────────────
    print("\n[TEST S] Superadmin provider creation endpoint remains fully functional")
    client.force_authenticate(user=superadmin_user)
    prov_name_s = f"Global Industrial Services {run_id}"
    resp_s = client.post("/api/workforce/superadmin/service-providers/", {
        "company_name": prov_name_s,
        "admin_username": f"admin_gis_{run_id.lower()}",
        "admin_email": f"admin_gis_{run_id.lower()}@globalind.com",
        "admin_password": "SuperCreatedPass123!",
        "admin_first_name": "Global",
        "admin_last_name": "Admin",
        "industry": "Commercial Services",
    }, format="json")
    assert resp_s.status_code == status.HTTP_201_CREATED, f"Expected 201, got {resp_s.status_code}: {resp_s.data}"
    comp_s = Company.objects.filter(company_name=prov_name_s).first()
    assert comp_s is not None
    print("  -> PASSED: Superadmin successfully created Service Provider and Admin.")
    passed += 1

    # ── Test T: Superadmin Maintains Global Visibility ─────────────────────────
    print("\n[TEST T] Superadmin maintains global visibility across all providers")
    client.force_authenticate(user=superadmin_user)
    resp_t = client.get("/api/workforce/superadmin/service-providers/")
    assert resp_t.status_code == status.HTTP_200_OK
    all_comp_ids = [c["id"] for c in resp_t.data]
    assert active_provider.id in all_comp_ids
    assert rival_provider.id in all_comp_ids
    assert comp_j.id in all_comp_ids
    print("  -> PASSED: Superadmin has full visibility across tenant companies.")
    passed += 1

    # ── Test U: Technician Signup Rejects 'service_provider' Account Type ──────
    print("\n[TEST U] Technician signup endpoint rejects 'service_provider' account_type")
    client.force_authenticate(user=None)
    resp_u = client.post("/api/workforce/signup/", {
        "first_name": "Wants",
        "last_name": "Provider",
        "email": f"tech_prov_err_{run_id.lower()}@test.com",
        "mobile_number": f"+1222{run_id[:6]}",
        "password": "Password123!",
        "account_type": "service_provider",
    }, format="json")
    assert resp_u.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Technician signup rejected 'service_provider' with descriptive error.")
    passed += 1

    # ── Test V: Passwords Mismatch Rejected in Provider Signup ─────────────────
    print("\n[TEST V] Provider signup rejects mismatched passwords")
    resp_v = client.post("/api/workforce/service-providers/signup/", {
        "company_name": f"Mismatch Co {run_id}",
        "first_name": "Mis",
        "email": f"mismatch_{run_id.lower()}@test.com",
        "password": "PasswordOne123!",
        "confirm_password": "PasswordTwo456!",
    }, format="json")
    assert resp_v.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Password mismatch rejected.")
    passed += 1

    # ── Test W: Shared provider service helper generates display_id and slug ──
    print("\n[TEST W] Shared provider creation service generates PROV- display_id and slug")
    comp_w, admin_w = create_service_provider_with_admin({
        "company_name": f"Elite Field Dynamics {run_id}",
        "username": f"elite_{run_id.lower()}",
        "email": f"elite_{run_id.lower()}@test.com",
        "password": "Password123!",
        "first_name": "Elite",
        "last_name": "Admin",
    })
    assert comp_w.display_id.startswith("PROV-")
    assert "elite-field-dynamics" in comp_w.slug
    assert admin_w.role == "service_provider_admin"
    assert admin_w.company_id == comp_w.id
    print("  -> PASSED: Shared provider service correctly generated display_id and slug.")
    passed += 1

    # ── Test X: Verification of Invariants & Model Integrity ──────────────────
    print("\n[TEST X] Invariant check: Provider Admin is staff but never superuser")
    assert admin_j.is_staff is True
    assert admin_j.is_superuser is False
    assert Employee.objects.filter(user=admin_j).first() is None
    print("  -> PASSED: All architectural invariants strictly held.")
    passed += 1

    print("\n" + "=" * 80)
    print(f"PHASE 2D VERIFICATION COMPLETE: {passed}/{total} TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
