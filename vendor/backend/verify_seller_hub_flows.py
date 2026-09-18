import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ["*"]

from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from companies.models import Company
from employees.models import Employee
from service_requests.models import CatalogCategory, Service
from workforce_api.models import SellerHubCategory, VendorCoupon, InventoryItem

User = get_user_model()
client = APIClient()

print("=" * 80)
print("SEVO-VENDOR SELLER HUB END-TO-END FLOW VERIFICATION")
print("=" * 80)

# Setup test users and companies
superadmin = User.objects.filter(is_superuser=True).first()
if not superadmin:
    superadmin, _ = User.objects.get_or_create(
        username="verify_superadmin_flow",
        defaults={"email": "verify_sa_flow@testsevo.com", "is_superuser": True, "is_staff": True}
    )
    superadmin.set_password("pass123")
    superadmin.is_superuser = True
    superadmin.is_staff = True
    superadmin.save()

vendor_company, _ = Company.objects.get_or_create(
    company_name="AC Repair Experts Test",
    defaults={"business_type": "service_provider", "industry": "appliances"}
)
vendor_company.business_type = "service_provider"
vendor_company.save()

vendor_admin = User.objects.filter(username="verify_vendor_admin_flow").first()
if not vendor_admin:
    vendor_admin = User.objects.create(
        username="verify_vendor_admin_flow",
        email="verify_vendoradmin_flow@testsevo.com",
        role=User.Role.ADMIN,
        is_staff=False
    )
    vendor_admin.set_password("pass123")
    vendor_admin.company = vendor_company
    vendor_admin.save()
else:
    vendor_admin.role = User.Role.ADMIN
    vendor_admin.save()

Employee.objects.update_or_create(
    user=vendor_admin,
    defaults={"company": vendor_company, "employee_id": "EMP-VADM-01", "title": "AC Vendor Admin"}
)

seller_company, _ = Company.objects.get_or_create(
    company_name="Green Farm Groceries Test",
    defaults={"business_type": "grocery_supplier", "industry": "grocery"}
)
seller_company.business_type = "grocery_supplier"
seller_company.save()

seller_user = User.objects.filter(username="verify_seller_user_flow").first()
if not seller_user:
    seller_user = User.objects.create(
        username="verify_seller_user_flow",
        email="verify_merchant_flow@testsevo.com",
        role=User.Role.ADMIN,
        is_staff=False
    )
    seller_user.set_password("pass123")
    seller_user.company = seller_company
    seller_user.save()
else:
    seller_user.role = User.Role.ADMIN
    seller_user.save()

Employee.objects.update_or_create(
    user=seller_user,
    defaults={"company": seller_company, "employee_id": "EMP-SELL-01", "title": "Green Farm Merchant"}
)

tech_user = User.objects.filter(username="verify_technician_flow").first()
if not tech_user:
    tech_user = User.objects.create(
        username="verify_technician_flow",
        email="verify_tech_flow@testsevo.com",
        role=User.Role.EMPLOYEE,
        is_staff=False
    )
    tech_user.set_password("pass123")
    tech_user.company = None
    tech_user.save()
else:
    tech_user.role = User.Role.EMPLOYEE
    tech_user.save()

tech_emp, _ = Employee.objects.update_or_create(
    user=tech_user,
    defaults={"company": None, "employee_id": "EMP-TECH-01", "title": "Field Technician"}
)

results = []

def record(test_num, name, passed, details=""):
    results.append({"num": test_num, "name": name, "passed": passed, "details": details})
    status_str = "[PASS]" if passed else "[FAIL]"
    print(f"{status_str} Test {test_num}: {name}")
    if details:
        print(f"       Details: {details}")

# ----------------------------------------------------------------------
# FLOW 1: Superadmin Login & Full CRUD
# ----------------------------------------------------------------------
print("\n>>> FLOW 1: SUPERADMIN VERIFICATION")
client.force_authenticate(user=superadmin)

# 1.1 /api/auth/me/ check for Superadmin
res = client.get("/api/auth/me/")
is_sa = res.status_code == 200 and res.data.get("is_superuser") and res.data.get("is_platform_admin")
record("1.1", "Superadmin Auth Me profile verification", is_sa, f"Role: {res.data.get('user_type')}")

# 1.2 Create Category
cat_data = {"name": "Exotic Organic Fruits", "description": "Fresh organic fruits directly from farm", "sort_order": 5, "is_active": True}
res = client.post("/api/workforce/seller-hub/categories/", data=cat_data, format="json")
created_cat_id = res.data.get("category", {}).get("id") if res.status_code == 201 else None
record("1.2", "Superadmin create CatalogCategory", res.status_code == 201 and created_cat_id is not None, f"Created ID: {created_cat_id}")

# 1.3 Edit Category & Toggle Enable/Disable
if created_cat_id:
    res = client.patch(f"/api/workforce/seller-hub/categories/{created_cat_id}/", data={"is_active": False, "description": "Updated fresh fruits"}, format="json")
    toggled = res.status_code == 200 and res.data.get("category", {}).get("is_active") is False
    record("1.3", "Superadmin edit category and disable", toggled, f"is_active: {res.data.get('category', {}).get('is_active')}")
    # Re-enable
    client.patch(f"/api/workforce/seller-hub/categories/{created_cat_id}/", data={"is_active": True}, format="json")
else:
    record("1.3", "Superadmin edit category and disable", False, "Category creation failed")

# 1.4 Safe Deletion Guard Blocked when linked
if created_cat_id:
    cat_obj = SellerHubCategory.objects.get(id=created_cat_id)
    # Link an InventoryItem
    inv = InventoryItem.objects.create(
        company=seller_company,
        catalogue_service_id=1,
        catalogue_category_id=created_cat_id,
        category_name_snapshot="Exotic Organic Fruits",
        custom_name="Dragonfruit 1kg",
        custom_price=Decimal("150.00"),
        quantity_in_stock=25,
        is_available=True,
    )
    res = client.delete(f"/api/workforce/seller-hub/categories/{created_cat_id}/")
    blocked = res.status_code == 409 and "Cannot delete category" in res.data.get("error", "")
    record("1.4", "Safe Deletion Guard blocks category deletion when items linked", blocked, f"Response: {res.data.get('error')}")
    # Remove link for safe deletion
    inv.delete()
else:
    record("1.4", "Safe Deletion Guard test", False, "Category creation failed")

# 1.5 Safe Deletion succeeds when unlinked
if created_cat_id:
    res = client.delete(f"/api/workforce/seller-hub/categories/{created_cat_id}/")
    deleted = res.status_code == 200
    record("1.5", "Safe Deletion succeeds when no items/services linked", deleted, f"Status: {res.status_code}")

import time
timestamp = int(time.time())

# 1.6 Superadmin Create, Edit, Toggle, Validate Coupon
c_code = f"HARVEST_{timestamp}"
c_data = {
    "company": seller_company.id,
    "code": c_code,
    "discount_type": "flat",
    "discount_value": "50.00",
    "min_order_amount": "200.00",
    "is_active": True
}
res = client.post("/api/workforce/seller-hub/coupons/", data=c_data, format="json")
created_c_id = res.data.get("coupon", {}).get("id") if res.status_code == 201 else None
record("1.6", "Superadmin create coupon", res.status_code == 201 and created_c_id is not None, f"Coupon ID: {created_c_id}")

if created_c_id:
    res = client.patch(f"/api/workforce/seller-hub/coupons/{created_c_id}/", data={"is_active": False, "discount_value": "60.00"}, format="json")
    c_updated = res.status_code == 200 and res.data.get("coupon", {}).get("is_active") is False
    record("1.7", "Superadmin edit coupon & toggle disable", c_updated, f"is_active: {res.data.get('coupon', {}).get('is_active')}")
else:
    record("1.7", "Superadmin edit coupon & toggle disable", False, "Coupon creation failed")


# ----------------------------------------------------------------------
# FLOW 2: Admin Login & RBAC Permissions
# ----------------------------------------------------------------------
print("\n>>> FLOW 2: ADMIN RBAC VERIFICATION")
client.force_authenticate(user=vendor_admin)

# 2.1 Admin profile check
res = client.get("/api/auth/me/")
is_va = res.status_code == 200 and res.data.get("is_vendor_admin") and not res.data.get("is_platform_admin")
record("2.1", "Vendor Admin Auth Me profile verification", is_va, f"user_type: {res.data.get('user_type')}")

# 2.2 Admin cannot create global CatalogCategory (reserved for Platform Superadmin)
res = client.post("/api/workforce/seller-hub/categories/", data={"name": "Hacked Category"}, format="json")
cat_blocked = res.status_code == 403
record("2.2", "Vendor Admin blocked from mutating global catalog categories", cat_blocked, f"Status: {res.status_code}")

# 2.3 Admin can read active categories
res = client.get("/api/workforce/seller-hub/categories/active/")
active_readable = res.status_code == 200 and isinstance(res.data, list)
record("2.3", "Vendor Admin can view active category catalog", active_readable, f"Count: {len(res.data) if isinstance(res.data, list) else 0}")

# 2.4 Admin cannot view other companies' coupons
res = client.get("/api/workforce/seller-hub/coupons/")
# Vendor admin belongs to AC Repair Experts, should see 0 green farm coupons
coupon_isolated = res.status_code == 200 and all(c.get("company_name") == "AC Repair Experts Test" for c in res.data)
record("2.4", "Vendor Admin coupon listing strictly tenant-isolated", coupon_isolated, f"Coupons visible: {len(res.data)}")


# ----------------------------------------------------------------------
# FLOW 3: Seller Hub Login & Workspace
# ----------------------------------------------------------------------
print("\n>>> FLOW 3: SELLER HUB MERCHANT VERIFICATION")
client.force_authenticate(user=seller_user)

# 3.1 Seller Auth Me verification
res = client.get("/api/auth/me/")
is_seller_flag = res.status_code == 200 and res.data.get("is_seller") and res.data.get("is_grocery_supplier")
record("3.1", "Seller Hub User Auth Me profile verification", is_seller_flag, f"is_seller: {res.data.get('is_seller')}, business_type: {res.data.get('business_type')}")

# 3.2 Seller can create store coupon
seller_c_code = f"ORGANIC_{timestamp}"
seller_c_data = {
    "code": seller_c_code,
    "discount_type": "percent",
    "discount_value": "10.00",
    "min_order_amount": "100.00",
    "is_active": True
}
res = client.post("/api/workforce/seller-hub/coupons/", data=seller_c_data, format="json")
seller_c_id = res.data.get("coupon", {}).get("id") if res.status_code == 201 else None
record("3.2", "Seller create store coupon", res.status_code == 201 and seller_c_id is not None, f"Coupon ID: {seller_c_id}")

# 3.3 Seller coupon listing only contains own store coupons
res = client.get("/api/workforce/seller-hub/coupons/")
seller_coupons_isolated = res.status_code == 200 and all(c.get("company") == seller_company.id for c in res.data)
record("3.3", "Seller coupon listing strictly isolated to own store", seller_coupons_isolated, f"Store coupons count: {len(res.data)}")

# 3.4 Seller active categories load from DB
res = client.get("/api/workforce/seller-hub/categories/active/")
cats_loaded = res.status_code == 200 and len(res.data) > 0
record("3.4", "Seller loads active categories from real DB", cats_loaded, f"Active Categories in DB: {len(res.data)}")

# 3.5 Seller blocked from modifying global catalog categories
res = client.post("/api/workforce/seller-hub/categories/", data={"name": "Seller Custom Category"}, format="json")
seller_cat_blocked = res.status_code == 403
record("3.5", "Seller blocked from global catalog creation", seller_cat_blocked, f"Status: {res.status_code}")

# 3.6 Seller blocked from workforce technician endpoints
res = client.get("/api/workforce/technicians/")
wf_blocked = res.status_code in [403, 404]
record("3.6", "Seller blocked from workforce operational routes", wf_blocked, f"Status: {res.status_code}")


# ----------------------------------------------------------------------
# FLOW 4: Sevo Vendor & Technician Regression
# ----------------------------------------------------------------------
print("\n>>> FLOW 4: SEVO VENDOR & TECHNICIAN REGRESSION")

# 4.1 Technician profile check
client.force_authenticate(user=tech_user)
res = client.get("/api/auth/me/")
is_tech = res.status_code == 200 and res.data.get("is_technician") and not res.data.get("is_seller")
record("4.1", "Technician profile has is_seller=False", is_tech, f"user_type: {res.data.get('user_type')}")

# 4.2 Technician blocked from Seller Hub coupons
res = client.get("/api/workforce/seller-hub/coupons/")
tech_blocked = res.status_code == 403
record("4.2", "Technician blocked from Seller Hub coupons", tech_blocked, f"Status: {res.status_code}")

# 4.3 Clean up test records
if created_c_id:
    VendorCoupon.objects.filter(id=created_c_id).delete()
if seller_c_id:
    VendorCoupon.objects.filter(id=seller_c_id).delete()
VendorCoupon.objects.filter(code__in=[c_code, seller_c_code]).delete()

# Summary
total = len(results)
passed = sum(1 for r in results if r["passed"])
print("\n" + "=" * 80)
print(f"VERIFICATION SUMMARY: {passed}/{total} TESTS PASSED ({passed/total*100:.1f}%)")
print("=" * 80)

if passed < total:
    sys.exit(1)
