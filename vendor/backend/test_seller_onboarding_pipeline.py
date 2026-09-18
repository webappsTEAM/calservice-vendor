"""
test_seller_onboarding_pipeline.py
Automated verification for Sevo Seller Hub onboarding & superadmin review pipeline.
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from companies.models import Company, Region
from workforce_api.models import VendorStore

User = get_user_model()


def run_tests():
    print("\n" + "=" * 70)
    print("SEVO SELLER HUB & ADMIN VERIFICATION PIPELINE TESTS")
    print("=" * 70)

    client = APIClient()

    # 1. Setup Superadmin & Non-superadmin users
    region, _ = Region.objects.get_or_create(code="IN", defaults={"name": "India", "currency": "INR"})
    admin_company, _ = Company.objects.get_or_create(
        id=1,
        defaults={"company_name": "Caldim Platform Operations", "slug": "caldim-platform", "is_active": True, "region": region}
    )

    superadmin_user, _ = User.objects.get_or_create(
        username="superadmin_test_seller",
        defaults={
            "email": "superadmin_test_seller@sevo.in",
            "is_superuser": True,
            "is_staff": True,
            "role": "superadmin",
            "company": admin_company,
            "is_active": True,
        }
    )
    superadmin_user.set_password("AdminPass@123")
    superadmin_user.save()

    regular_vendor_company, _ = Company.objects.get_or_create(
        slug="regular-vendor-test",
        defaults={"company_name": "Regular Vendor Co", "is_active": True, "region": region}
    )
    vendor_admin_user, _ = User.objects.get_or_create(
        username="vendor_admin_test_seller",
        defaults={
            "email": "vendor_admin_test_seller@example.com",
            "role": "manager",
            "company": regular_vendor_company,
            "is_active": True,
        }
    )
    vendor_admin_user.set_password("VendorPass@123")
    vendor_admin_user.save()

    # Tokens
    login_res = client.post("/api/auth/login/", {"identifier": "superadmin_test_seller", "password": "AdminPass@123"}, format="json")
    assert login_res.status_code == 200, f"Superadmin login failed: {login_res.data}"
    superadmin_token = login_res.data.get("access_token") or login_res.data.get("token")
    auth_header = {"HTTP_AUTHORIZATION": f"Bearer {superadmin_token}"}

    v_login_res = client.post("/api/auth/login/", {"identifier": "vendor_admin_test_seller", "password": "VendorPass@123"}, format="json")
    assert v_login_res.status_code == 200, f"Vendor admin login failed: {v_login_res.data}"
    vendor_token = v_login_res.data.get("access_token") or v_login_res.data.get("token")
    vendor_auth_header = {"HTTP_AUTHORIZATION": f"Bearer {vendor_token}"}

    print("[PASS] Test fixtures and tokens initialized.")

    # 2. Test Grocery Seller Signup with NO categories selected (new requirement)
    seller_email = f"seller_{os.getpid()}_{int(django.utils.timezone.now().timestamp())}@krishnamart.com"
    seller_mobile = f"98765{str(os.getpid()).zfill(5)[:5]}"
    signup_payload = {
        "business_name": "Sri Krishna Mart",
        "store_name": "Krishna Supermarket Hosur",
        "contact_first_name": "Krishna",
        "contact_last_name": "Kumar",
        "email": seller_email,
        "mobile_number": seller_mobile,
        "password": "SellerSecure@123",
        "address": "123 Market Road, Hosur",
        "city": "Hosur",
        "fssai_license_number": "12421008000999",
        "gst_number": "33AAAAA0000A1Z5",
        "documents": {
            "fssai_certificate": {
                "title": "FSSAI License Certificate",
                "file_url": "https://storage.sevo.in/docs/fssai_krishna.pdf",
                "document_number": "12421008000999",
            },
            "store_photo": {
                "title": "Store Front Photo",
                "file_url": "https://storage.sevo.in/photos/krishna_front.jpg",
            }
        }
    }

    signup_res = client.post("/api/workforce/seller/signup/", signup_payload, format="json")
    print(f"Seller Signup Response Status: {signup_res.status_code}")
    print(f"Seller Signup Response Data: {signup_res.data}")
    assert signup_res.status_code == 201, f"Seller signup failed: {signup_res.data}"
    data = signup_res.data
    store_id = data["application_id"]
    assert "access_token" not in data, "Security violation: Seller signup must not issue active tokens immediately"
    assert data["status"] == "submitted", f"Expected submitted status, got {data['status']}"

    # Verify DB state of created records
    store = VendorStore.objects.select_related("company").get(pk=store_id)
    assert store.company.is_active is False, "Company must be inactive upon seller registration"
    assert store.is_accepting_orders is False, "Store must not accept orders before approval"
    assert store.fssai_license_number == "12421008000999"
    assert store.gst_number == "33AAAAA0000A1Z5"
    seller_user = User.objects.get(email=seller_email)
    assert seller_user.is_active is False, "Merchant User account must be inactive until admin approval"
    print(f"[PASS] Seller signup (no categories) created inactive Company, User, and VendorStore #{store_id}.")

    # 3. Test Authorization on Admin Seller Applications list
    # Unauthenticated must fail (401 or 403)
    anon_client = APIClient()
    unauth_list_res = anon_client.get("/api/workforce/admin/seller-applications/")
    assert unauth_list_res.status_code in [401, 403], f"Expected 401/403 for unauthenticated request, got {unauth_list_res.status_code}"

    # Regular vendor admin sees only their own company's applications (empty list here)
    vadmin_list_res = client.get("/api/workforce/admin/seller-applications/", **vendor_auth_header)
    assert vadmin_list_res.status_code == 200, f"Expected 200 for vendor admin, got {vadmin_list_res.status_code}"
    assert not any(a["id"] == store_id for a in vadmin_list_res.data), "Tenant isolation failure: Vendor admin should not see store from another company"

    # Superadmin sees all applications
    auth_list_res = client.get("/api/workforce/admin/seller-applications/", **auth_header)
    assert auth_list_res.status_code == 200, f"Superadmin list failed: {auth_list_res.data}"
    apps = auth_list_res.data
    assert any(a["id"] == store_id for a in apps), f"Newly created store #{store_id} not found in superadmin list"
    print("[PASS] Tenant & role gating verified on seller applications list.")

    # 4. Test Detail endpoint & Cross-tenant protection
    vadmin_detail_res = client.get(f"/api/workforce/admin/seller-applications/{store_id}/", **vendor_auth_header)
    assert vadmin_detail_res.status_code == 403, f"Cross-tenant failure: Expected 403 for unauthorized company admin, got {vadmin_detail_res.status_code}"

    detail_res = client.get(f"/api/workforce/admin/seller-applications/{store_id}/", **auth_header)
    assert detail_res.status_code == 200, f"Detail failed: {detail_res.data}"
    assert detail_res.data["store_name"] == "Krishna Supermarket Hosur"
    assert "fssai_certificate" in detail_res.data["documents_status"]
    print("[PASS] Detail view and cross-tenant security verified.")

    # 5. Test Approval validation: Attempting approval before verifying docs must fail
    premature_approve_res = client.post(f"/api/workforce/admin/seller-applications/{store_id}/approve/", **auth_header)
    assert premature_approve_res.status_code == 400, f"Expected 400 when approving unverified docs, got {premature_approve_res.status_code}"
    print("[PASS] Backend state machine blocked premature approval with unverified documents.")

    # 6. Bulk approve all pending documents
    bulk_doc_res = client.post(
        f"/api/workforce/admin/seller-applications/{store_id}/documents/bulk-verify/",
        {"action": "approve", "all_pending": True},
        format="json",
        **auth_header
    )
    assert bulk_doc_res.status_code == 200, f"Bulk doc verify failed: {bulk_doc_res.data}"

    # 7. Approve seller application (without categories required)
    final_approve_res = client.post(f"/api/workforce/admin/seller-applications/{store_id}/approve/", **auth_header)
    assert final_approve_res.status_code == 200, f"Final approve failed: {final_approve_res.data}"

    # Verify activated records in database
    store.refresh_from_db()
    assert store.onboarding["status"] == "approved", f"Expected onboarding status approved, got {store.onboarding['status']}"
    assert store.is_accepting_orders is True, "Store must now accept orders"
    assert store.company.is_active is True, "Company must be active"
    seller_user.refresh_from_db()
    assert seller_user.is_active is True, "Seller User must be active after approval"
    print("[PASS] Full document verification & application approval successfully activated company, user, and store without requiring category selection.")

    # 8. Test Correction & Rejection on a second test applicant
    seller2_email = f"seller2_{os.getpid()}_{int(django.utils.timezone.now().timestamp())}@testmart.com"
    signup2_payload = {
        "business_name": "Test Fresh Mart",
        "contact_first_name": "Ravi",
        "email": seller2_email,
        "mobile_number": f"98764{str(os.getpid()).zfill(5)[:5]}",
        "password": "SellerPass@123",
    }
    signup2_res = client.post("/api/workforce/seller/signup/", signup2_payload, format="json")
    assert signup2_res.status_code == 201
    store2_id = signup2_res.data["application_id"]

    # Request correction
    corr_res = client.post(
        f"/api/workforce/admin/seller-applications/{store2_id}/request-correction/",
        {"notes": "Please upload a valid FSSAI license certificate."},
        format="json",
        **auth_header
    )
    assert corr_res.status_code == 200
    store2 = VendorStore.objects.get(pk=store2_id)
    assert store2.onboarding["status"] == "correction_required"

    # Reject
    reject_res = client.post(
        f"/api/workforce/admin/seller-applications/{store2_id}/reject/",
        {"reason": "Ineligible location and missing documentation."},
        format="json",
        **auth_header
    )
    assert reject_res.status_code == 200
    store2.refresh_from_db()
    assert store2.onboarding["status"] == "rejected"
    assert store2.company.is_active is False
    print("[PASS] Correction requests and rejection state transitions verified.")

    # 9. Test ProviderSignupView no longer activates grocery_supplier instantly
    prov_email = f"prov_grocery_{os.getpid()}_{int(django.utils.timezone.now().timestamp())}@example.com"
    prov_signup_res = client.post(
        "/api/workforce/provider/signup/",
        {
            "business_name": "Grocery Provider Test",
            "contact_first_name": "Anil",
            "email": prov_email,
            "mobile_number": f"98763{str(os.getpid()).zfill(5)[:5]}",
            "password": "ProvPass@123",
            "business_type": "grocery_supplier",
        },
        format="json"
    )
    assert prov_signup_res.status_code == 201
    assert "access_token" not in prov_signup_res.data, "Provider signup for grocery_supplier must not return active tokens"
    prov_user = User.objects.get(email=prov_email)
    assert prov_user.is_active is False, "Provider user for grocery_supplier must start inactive"
    print("[PASS] ProviderSignupView instant activation removed for grocery_supplier.")

    # 10. Regression Check: Regular Technician Signup
    tech_email = f"tech_{os.getpid()}_{int(django.utils.timezone.now().timestamp())}@techtest.com"
    tech_signup_res = client.post(
        "/api/workforce/signup/",
        {
            "first_name": "Sunil",
            "last_name": "Rao",
            "email": tech_email,
            "mobile_number": f"98762{str(os.getpid()).zfill(5)[:5]}",
            "password": "TechPass@123",
        },
        format="json"
    )
    assert tech_signup_res.status_code == 201, f"Technician signup failed: {tech_signup_res.data}"
    print("[PASS] Technician signup unaffected and operational.")

    # 11. Regression Check: Standard Service Provider Signup
    sp_email = f"prov_svc_{os.getpid()}_{int(django.utils.timezone.now().timestamp())}@servicetest.com"
    sp_signup_res = client.post(
        "/api/workforce/provider/signup/",
        {
            "business_name": "Standard Plumbing Co",
            "contact_first_name": "Vijay",
            "email": sp_email,
            "mobile_number": f"98761{str(os.getpid()).zfill(5)[:5]}",
            "password": "ProviderPass@123",
            "business_type": "service_provider",
        },
        format="json"
    )
    assert sp_signup_res.status_code == 201, f"Provider signup failed: {sp_signup_res.data}"
    print("[PASS] Standard service provider signup unaffected and operational.")

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY (11/11)")
    print("=" * 70)


if __name__ == "__main__":
    run_tests()
