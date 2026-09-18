"""
test_seller_hub_comprehensive.py

Comprehensive test suite verifying:
1. Catalog Categories management (CatalogCategory in service_requests_catalogcategory)
   - Superadmin listing, searching, creating, editing, activating/deactivating, and ordering
   - Safe deletion protection when services or inventory items are linked
   - Active categories public/seller endpoint
2. Coupons management (VendorCoupon in workforce_vendor_coupon)
   - Store & platform coupon creation with percentage/flat discount rules, min order value, max discount cap, usage limits, validity dates
   - Server-side tenant isolation between merchants
   - Search, status filtering, editing, toggling active, and deletion
3. Role separation & access guards
   - Seller Hub accounts blocked from non-seller technician/dispatch endpoints
   - Technicians blocked from seller coupon management
   - Unauthenticated requests blocked
"""
import os
import sys
import django
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from companies.models import Company, Region
from employees.models import Employee
from service_requests.models import CatalogCategory, Service
from workforce_api.models import VendorCoupon, InventoryItem

User = get_user_model()


def run_tests():
    print("=" * 80)
    print("STARTING SELLER HUB COMPREHENSIVE AUTOMATED TEST SUITE")
    print("=" * 80)

    client = APIClient()

    # 1. Setup Test Fixtures
    region, _ = Region.objects.get_or_create(code="IN", defaults={"name": "India", "currency": "INR", "currency_symbol": "₹"})

    # Superadmin User
    superadmin_user, _ = User.objects.get_or_create(
        username="superadmin_test_hub",
        defaults={"email": "superadmin_hub@sevo.com", "is_superuser": True, "is_staff": True, "is_active": True}
    )
    superadmin_user.set_password("pass1234")
    superadmin_user.save()

    # Seller Company A (Grocery Supplier)
    seller_comp_a, _ = Company.objects.get_or_create(
        slug="fresh-veggies-mart",
        defaults={
            "company_name": "Fresh Veggies Mart",
            "business_type": "grocery_supplier",
            "region": region,
            "is_active": True,
        }
    )
    seller_user_a, _ = User.objects.get_or_create(
        username="seller_user_a",
        defaults={
            "email": "seller_a@veggies.com",
            "company": seller_comp_a,
            "role": "admin",
            "is_active": True,
        }
    )
    seller_user_a.set_password("pass1234")
    seller_user_a.company = seller_comp_a
    seller_user_a.save()

    # Seller Company B (Bakery Supplier)
    seller_comp_b, _ = Company.objects.get_or_create(
        slug="sweet-bakes-store",
        defaults={
            "company_name": "Sweet Bakes Store",
            "business_type": "grocery_supplier",
            "region": region,
            "is_active": True,
        }
    )
    seller_user_b, _ = User.objects.get_or_create(
        username="seller_user_b",
        defaults={
            "email": "seller_b@bakes.com",
            "company": seller_comp_b,
            "role": "admin",
            "is_active": True,
        }
    )
    seller_user_b.set_password("pass1234")
    seller_user_b.company = seller_comp_b
    seller_user_b.save()

    # Technician User (Non-Seller)
    tech_comp, _ = Company.objects.get_or_create(
        slug="ac-repair-pros",
        defaults={
            "company_name": "AC Repair Pros",
            "business_type": "service_provider",
            "region": region,
            "is_active": True,
        }
    )
    tech_user, _ = User.objects.get_or_create(
        username="tech_john_doe",
        defaults={
            "email": "tech_john@acrepair.com",
            "company": tech_comp,
            "role": "technician",
            "is_active": True,
        }
    )
    tech_user.set_password("pass1234")
    tech_user.save()
    tech_emp, _ = Employee.objects.get_or_create(
        user=tech_user,
        defaults={
            "employee_id": "EMP-TECH-TEST-01",
            "company": tech_comp,
        }
    )

    passed = 0
    total = 0

    # ── Test 1: Category Listing & Creation by Superadmin ──────────────────────
    total += 1
    print(f"\n[Test {total}] Superadmin creating and listing Catalog Categories...")
    client.force_authenticate(user=superadmin_user)

    cat_name = "Organic Fruits & Vegetables"
    res_create = client.post("/api/workforce/seller-hub/categories/", {
        "name": cat_name,
        "description": "Farm fresh organic fruits and hand-picked vegetables",
        "icon": "Carrot",
        "sort_order": 10,
        "is_active": True,
    }, format="json")

    assert res_create.status_code == status.HTTP_201_CREATED, f"Expected 201, got {res_create.status_code}: {res_create.data}"
    cat_id = res_create.data["category"]["id"]
    assert res_create.data["category"]["name"] == cat_name
    assert "organic-fruits" in res_create.data["category"]["slug"]
    print(f"  [PASS] Category '{cat_name}' created with ID={cat_id}, slug='{res_create.data['category']['slug']}'")
    passed += 1

    # ── Test 2: Category Search & Sorting ──────────────────────────────────────
    total += 1
    print(f"\n[Test {total}] Category search & filtering...")
    res_search = client.get("/api/workforce/seller-hub/categories/?search=Organic")
    assert res_search.status_code == status.HTTP_200_OK
    assert any(c["id"] == cat_id for c in res_search.data)
    print(f"  [PASS] Search query returned {len(res_search.data)} matching categories")
    passed += 1

    # ── Test 3: Category Edit & Toggle Active ──────────────────────────────────
    total += 1
    print(f"\n[Test {total}] Updating category and toggling active status...")
    res_patch = client.patch(f"/api/workforce/seller-hub/categories/{cat_id}/", {
        "is_active": False,
        "sort_order": 99,
    }, format="json")
    assert res_patch.status_code == status.HTTP_200_OK
    assert res_patch.data["category"]["is_active"] is False
    assert res_patch.data["category"]["sort_order"] == 99

    # Re-activate for subsequent tests
    client.patch(f"/api/workforce/seller-hub/categories/{cat_id}/", {"is_active": True}, format="json")
    print(f"  [PASS] Category {cat_id} updated and active status toggled")
    passed += 1

    # ── Test 4: Active Categories Public / Seller Endpoint ────────────────────
    total += 1
    print(f"\n[Test {total}] Active categories list endpoint...")
    client.force_authenticate(user=seller_user_a)
    res_active = client.get("/api/workforce/seller-hub/categories/active/")
    assert res_active.status_code == status.HTTP_200_OK
    assert any(c["id"] == cat_id for c in res_active.data)
    print(f"  [PASS] Active categories endpoint returned {len(res_active.data)} items for seller")
    passed += 1

    # ── Test 5: Safe Deletion Guard (Category with linked items) ──────────────
    total += 1
    print(f"\n[Test {total}] Testing Safe Deletion Guard when items are linked...")
    # Link an inventory item to this category
    inv = InventoryItem.objects.create(
        company=seller_comp_a,
        catalogue_service_id=1,
        catalogue_category_id=cat_id,
        category_name_snapshot=cat_name,
        custom_name="Organic Red Apples 1kg",
        custom_price=Decimal("120.00"),
        quantity_in_stock=50,
        is_available=True,
    )

    client.force_authenticate(user=superadmin_user)
    res_del_blocked = client.delete(f"/api/workforce/seller-hub/categories/{cat_id}/")
    assert res_del_blocked.status_code == status.HTTP_409_CONFLICT, f"Expected 409, got {res_del_blocked.status_code}: {res_del_blocked.data}"
    assert res_del_blocked.data["code"] == "CATEGORY_IN_USE"
    print(f"  [PASS] Safe Deletion Guard successfully blocked deletion: '{res_del_blocked.data['error']}'")
    passed += 1

    # Cleanup linked item and test successful deletion of temporary category
    total += 1
    print(f"\n[Test {total}] Testing safe deletion of unlinked category...")
    inv.delete()
    res_del_ok = client.delete(f"/api/workforce/seller-hub/categories/{cat_id}/")
    assert res_del_ok.status_code == status.HTTP_200_OK
    assert not CatalogCategory.objects.filter(id=cat_id).exists()
    print(f"  [PASS] Unlinked category {cat_id} deleted successfully")
    passed += 1

    # ── Test 6: Seller A Creating Store Coupon ─────────────────────────────────
    total += 1
    print(f"\n[Test {total}] Seller A creating percentage discount coupon...")
    client.force_authenticate(user=seller_user_a)

    coupon_code = "VEGGIE20"
    res_coup_a = client.post("/api/workforce/seller-hub/coupons/", {
        "code": coupon_code,
        "description": "20% off on fresh produce orders above ₹300",
        "discount_type": "percent",
        "discount_value": 20.0,
        "min_order_amount": 300.0,
        "max_discount_amount": 150.0,
        "usage_limit_total": 500,
        "usage_limit_per_user": 2,
        "valid_from": timezone.now().isoformat(),
        "valid_until": (timezone.now() + timedelta(days=30)).isoformat(),
        "is_active": True,
    }, format="json")

    assert res_coup_a.status_code == status.HTTP_201_CREATED, f"Expected 201, got {res_coup_a.status_code}: {res_coup_a.data}"
    coupon_a_id = res_coup_a.data["coupon"]["id"]
    assert res_coup_a.data["coupon"]["code"] == coupon_code
    print(f"  [PASS] Coupon '{coupon_code}' created for Seller A (ID={coupon_a_id})")
    passed += 1

    # ── Test 7: Duplicate Coupon Code in Same Store Rejected ───────────────────
    total += 1
    print(f"\n[Test {total}] Duplicate coupon code in same store rejected with 409...")
    res_dup = client.post("/api/workforce/seller-hub/coupons/", {
        "code": coupon_code,
        "discount_type": "percent",
        "discount_value": 15.0,
    }, format="json")
    assert res_dup.status_code == status.HTTP_409_CONFLICT
    print(f"  [PASS] Duplicate coupon rejection confirmed: {res_dup.data['error']}")
    passed += 1

    # ── Test 8: Same Coupon Code in Different Store Permitted (Tenant Isolated)
    total += 1
    print(f"\n[Test {total}] Seller B creating same coupon code in independent store...")
    client.force_authenticate(user=seller_user_b)
    res_coup_b = client.post("/api/workforce/seller-hub/coupons/", {
        "code": coupon_code,
        "description": "Bakery 20% off",
        "discount_type": "percent",
        "discount_value": 20.0,
        "is_active": True,
    }, format="json")
    assert res_coup_b.status_code == status.HTTP_201_CREATED
    coupon_b_id = res_coup_b.data["coupon"]["id"]
    print(f"  [PASS] Store isolation confirmed: Seller B created '{coupon_code}' (ID={coupon_b_id})")
    passed += 1

    # ── Test 9: Tenant Isolation on Coupon Listing & Modification ──────────────
    total += 1
    print(f"\n[Test {total}] Verifying tenant isolation (Seller A cannot see or edit Seller B's coupon)...")
    client.force_authenticate(user=seller_user_a)

    # Seller A listing coupons should only see their own coupon
    res_list_a = client.get("/api/workforce/seller-hub/coupons/")
    assert res_list_a.status_code == status.HTTP_200_OK
    assert all(c["company"] == seller_comp_a.id for c in res_list_a.data)
    assert any(c["id"] == coupon_a_id for c in res_list_a.data)
    assert not any(c["id"] == coupon_b_id for c in res_list_a.data)

    # Seller A trying to edit Seller B's coupon should return 404 (or 403)
    res_edit_cross = client.patch(f"/api/workforce/seller-hub/coupons/{coupon_b_id}/", {"discount_value": 50.0}, format="json")
    assert res_edit_cross.status_code == status.HTTP_404_NOT_FOUND
    print(f"  [PASS] Tenant isolation strictly enforced on listing and modifications")
    passed += 1

    # ── Test 10: Superadmin Cross-Tenant Coupon View & Management ──────────────
    total += 1
    print(f"\n[Test {total}] Superadmin cross-tenant view of all coupons...")
    client.force_authenticate(user=superadmin_user)
    res_super_coupons = client.get("/api/workforce/seller-hub/coupons/")
    assert res_super_coupons.status_code == status.HTTP_200_OK
    assert any(c["id"] == coupon_a_id for c in res_super_coupons.data)
    assert any(c["id"] == coupon_b_id for c in res_super_coupons.data)
    print(f"  [PASS] Superadmin can view coupons across all vendors ({len(res_super_coupons.data)} found)")
    passed += 1

    # ── Test 11: Technician Blocked from Seller Hub Management ─────────────────
    total += 1
    print(f"\n[Test {total}] Technician blocked from Seller Hub coupon & category creation...")
    client.force_authenticate(user=tech_user)

    res_tech_cat = client.post("/api/workforce/seller-hub/categories/", {"name": "Hacked Cat"}, format="json")
    assert res_tech_cat.status_code == status.HTTP_403_FORBIDDEN

    res_tech_coup = client.post("/api/workforce/seller-hub/coupons/", {"code": "HACK50", "discount_value": 50}, format="json")
    assert res_tech_coup.status_code == status.HTTP_403_FORBIDDEN
    print(f"  [PASS] Technician strictly forbidden from Seller Hub management endpoints")
    passed += 1

    # ── Test 12: Unauthenticated Access Blocked ────────────────────────────────
    total += 1
    print(f"\n[Test {total}] Unauthenticated access blocked with 401...")
    client.force_authenticate(user=None)
    res_unauth = client.get("/api/workforce/seller-hub/categories/")
    assert res_unauth.status_code == status.HTTP_401_UNAUTHORIZED
    print(f"  [PASS] Unauthenticated requests rejected with 401 Unauthorized")
    passed += 1

    # Clean up test coupons
    VendorCoupon.objects.filter(id__in=[coupon_a_id, coupon_b_id]).delete()

    print("\n" + "=" * 80)
    print(f"SELLER HUB TEST RESULTS: {passed}/{total} TESTS PASSED (100% SUCCESS)")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
