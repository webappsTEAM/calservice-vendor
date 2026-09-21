"""
test_phase10a_category_picker.py

Comprehensive Phase 10A Verification Test Suite:
1. Vendor GET /api/workforce/seller-hub/catalog/categories/ works and is strictly read-only.
2. Role Gating: Vendor mutations (POST/PATCH/DELETE) return 403; Staff Admin & Superadmin succeed.
3. Cascading Level Loading (?parent_id=<id|null>) lazy loading.
4. Search (?q=<text>) with full breadcrumbs and active ancestor filtering.
5. Unified One-Leaf Rule:
   - Category with all inactive children is selectable in picker AND accepted on product create.
   - Category with one active child is rejected in picker (is_leaf=False) AND rejected on product create (400 CATEGORY_NOT_LEAF).
6. Product Creation Validation: Leaf Only & Active Chain Only.
7. Product Update & Legacy Compatibility.
8. Product-Conflict Guards on Admin Category Changes:
   - (a) PATCH parent to a category that has products -> 409 CATEGORY_HAS_PRODUCTS.
   - (b) PATCH reactivate child under a category that has products -> 409 CATEGORY_HAS_PRODUCTS.
   - (c) POST create child under a category that has products -> 409 CATEGORY_HAS_PRODUCTS.
9. Other Creation Paths: Bulk CSV Upload Category Validation (Preview & Commit Steps).
10. Database Query Performance: Bounded queries.
11. Seed Safety Verification:
    - Existing category with products refuses child creation on dry-run & --commit.
    - Idempotent second commit creates 0 new items.
12. Customer Marketplace Payload Snapshot Verification:
    - Product list & product detail endpoints return 100% exact expected keys.
"""

import os
import sys
import io
import uuid
import tempfile
from decimal import Decimal
from pathlib import Path

# Ensure temporary SQLite is used for all tests (NEVER PostgreSQL)
if not os.environ.get("SEVO_E2E_SQLITE_PATH"):
    temp_sqlite = os.path.join(tempfile.gettempdir(), f"sevo_phase10a_test_{uuid.uuid4().hex[:8]}.sqlite3")
    os.environ["SEVO_E2E_SQLITE_PATH"] = temp_sqlite

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection, reset_queries
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

created_table_count = 0
with connection.schema_editor() as schema_editor:
    for model in apps.get_models():
        try:
            schema_editor.create_model(model)
            created_table_count += 1
        except Exception as e:
            err_msg = str(e).lower()
            if "already exists" in err_msg or "duplicate table" in err_msg:
                continue
            raise RuntimeError(f"Failed to create schema for model {model.__name__}: {e}") from e
print(f"SQLite Schema Initialized: {created_table_count} tables created.")

from django.contrib.auth import get_user_model
from companies.models import Company
from workforce_api.models import (
    SellerHubCategory,
    SellerProduct,
    SellerInventory,
)
from workforce_api.views_seller_hub import (
    SellerCatalogCategoryListView,
    AdminSellerHubCategoryListView,
    AdminSellerHubCategoryDetailView,
    AdminCatalogCategoryActiveListView,
    SellerProductListView,
    SellerProductDetailView,
    SellerProductBulkUploadView,
)
from workforce_api.views_marketplace_integration import (
    MarketplaceProductListView,
    MarketplaceProductDetailView,
)

User = get_user_model()
factory = APIRequestFactory()

TEST_WEBHOOK_SECRET = "test-secret-not-real-phase10a-key"
settings.WORKFORCE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
settings.WORKFORCE_API_KEY = TEST_WEBHOOK_SECRET
TEST_SECRET = TEST_WEBHOOK_SECRET


def run_tests():
    print("=" * 80)
    print("PHASE 10A — MEESHO CATEGORY PICKER & GATING VERIFICATION")
    print("=" * 80)

    passed_count = 0
    failed_count = 0

    def assert_test(condition, name, error_msg=""):
        nonlocal passed_count, failed_count
        if condition:
            passed_count += 1
            print(f"  [PASS] {name}")
        else:
            failed_count += 1
            print(f"  [FAIL] {name}: {error_msg}")

    # Setup test users
    superadmin, _ = User.objects.get_or_create(
        username="phase10_superadmin",
        defaults={"email": "phase10_superadmin@test.com", "is_superuser": True, "is_staff": True}
    )
    superadmin.is_superuser = True
    superadmin.is_staff = True
    superadmin.save()

    platform_company, _ = Company.objects.get_or_create(
        id=1,
        defaults={"company_name": "Caldim Platform", "business_type": "platform", "is_active": True}
    )

    staff_admin, _ = User.objects.get_or_create(
        username="phase10_staffadmin",
        defaults={"email": "phase10_staffadmin@test.com", "is_superuser": False, "is_staff": True, "company": platform_company, "role": "admin"}
    )
    staff_admin.is_superuser = False
    staff_admin.is_staff = True
    staff_admin.company = platform_company
    staff_admin.role = "admin"
    staff_admin.save()

    vendor_company, _ = Company.objects.get_or_create(
        company_name="Phase10 Grocery Store Ltd",
        defaults={"business_type": "grocery_supplier"}
    )
    vendor_company.business_type = "grocery_supplier"
    vendor_company.is_active = True
    vendor_company.save()

    vendor_user, _ = User.objects.get_or_create(
        username="phase10_vendor_seller",
        defaults={
            "email": "phase10_vendor@test.com",
            "role": "seller",
            "is_staff": False,
            "is_superuser": False,
        }
    )
    vendor_user.company = vendor_company
    vendor_user.role = "seller"
    vendor_user.is_superuser = False
    vendor_user.is_staff = False
    vendor_user.save()

    # Build fresh test categories
    test_prefix = f"p10_{uuid.uuid4().hex[:6]}"

    # Root Department: Grocery
    root_cat, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-grocery",
        defaults={"name": "P10 Grocery", "sort_order": 1, "is_active": True}
    )
    root_cat.is_active = True
    root_cat.parent = None
    root_cat.save()

    # Level 2 Subcategory: Dairy
    sub_dairy, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-dairy",
        defaults={"name": "P10 Dairy & Eggs", "parent": root_cat, "sort_order": 1, "is_active": True}
    )
    sub_dairy.parent = root_cat
    sub_dairy.is_active = True
    sub_dairy.save()

    # Level 3 Leaf: Milk
    leaf_milk, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-milk",
        defaults={"name": "P10 Fresh Milk", "parent": sub_dairy, "sort_order": 1, "is_active": True}
    )
    leaf_milk.parent = sub_dairy
    leaf_milk.is_active = True
    leaf_milk.save()

    # Level 3 Leaf: Paneer
    leaf_paneer, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-paneer",
        defaults={"name": "P10 Fresh Paneer", "parent": sub_dairy, "sort_order": 2, "is_active": True}
    )
    leaf_paneer.parent = sub_dairy
    leaf_paneer.is_active = True
    leaf_paneer.save()

    # Inactive Category Subtree for filtering tests
    sub_inactive_parent, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-inactive-parent",
        defaults={"name": "P10 Inactive Branch", "parent": root_cat, "sort_order": 99, "is_active": False}
    )
    sub_inactive_parent.is_active = False
    sub_inactive_parent.save()

    leaf_under_inactive, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-leaf-under-inactive",
        defaults={"name": "P10 Leaf Under Inactive", "parent": sub_inactive_parent, "sort_order": 1, "is_active": True}
    )
    leaf_under_inactive.parent = sub_inactive_parent
    leaf_under_inactive.is_active = True
    leaf_under_inactive.save()

    # ─────────────────────────────────────────────────────────────────────────
    # 1. Vendor Read-Only Access on GET /api/workforce/seller-hub/catalog/categories/
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 1. Read-Only Vendor Endpoint Tests ---")
    req = factory.get("/api/workforce/seller-hub/catalog/categories/")
    force_authenticate(req, user=vendor_user)
    view = SellerCatalogCategoryListView.as_view()
    res = view(req)
    assert_test(res.status_code == 200, "Vendor can GET catalog categories (200 OK)", f"Got {res.status_code}")

    # Unauthenticated rejected
    req_anon = factory.get("/api/workforce/seller-hub/catalog/categories/")
    res_anon = view(req_anon)
    assert_test(res_anon.status_code in (401, 403), "Unauthenticated request rejected (401/403)", f"Got {res_anon.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. Role Gating: Admin / Superadmin Allowed, Vendor Blocked (403)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 2. Role Gating: Admin / Superadmin Allowed (201/200/200), Vendor Blocked (403) ---")
    post_view = AdminSellerHubCategoryListView.as_view()
    detail_view = AdminSellerHubCategoryDetailView.as_view()

    # Vendor write attempts -> 403
    post_req = factory.post("/api/workforce/seller-hub/categories/", {"name": "Vendor Hacked Category"})
    force_authenticate(post_req, user=vendor_user)
    post_res = post_view(post_req)
    assert_test(post_res.status_code == 403, "Vendor POST category returns 403 Forbidden", f"Got {post_res.status_code}")

    patch_req = factory.patch(f"/api/workforce/seller-hub/categories/{leaf_milk.id}/", {"name": "Vendor Modified Name"})
    force_authenticate(patch_req, user=vendor_user)
    patch_res = detail_view(patch_req, pk=leaf_milk.id)
    assert_test(patch_res.status_code == 403, "Vendor PATCH category returns 403 Forbidden", f"Got {patch_res.status_code}")

    del_req = factory.delete(f"/api/workforce/seller-hub/categories/{leaf_milk.id}/")
    force_authenticate(del_req, user=vendor_user)
    del_res = detail_view(del_req, pk=leaf_milk.id)
    assert_test(del_res.status_code == 403, "Vendor DELETE category returns 403 Forbidden", f"Got {del_res.status_code}")

    # Staff Admin (is_staff=True, is_superuser=False) -> Succeeds
    admin_post_req = factory.post("/api/workforce/seller-hub/categories/", {
        "name": f"Staff Admin Cat {uuid.uuid4().hex[:4]}",
        "slug": f"staff-admin-cat-{uuid.uuid4().hex[:4]}",
    })
    force_authenticate(admin_post_req, user=staff_admin)
    admin_post_res = post_view(admin_post_req)
    assert_test(admin_post_res.status_code == 201, "Staff Admin (is_staff=True) POST category succeeds (201 Created)", f"Got {admin_post_res.status_code}")
    staff_created_cat_id = admin_post_res.data["category"]["id"]

    admin_patch_req = factory.patch(f"/api/workforce/seller-hub/categories/{staff_created_cat_id}/", {
        "name": "Staff Admin Cat Renamed",
    })
    force_authenticate(admin_patch_req, user=staff_admin)
    admin_patch_res = detail_view(admin_patch_req, pk=staff_created_cat_id)
    assert_test(admin_patch_res.status_code == 200, "Staff Admin (is_staff=True) PATCH category succeeds (200 OK)", f"Got {admin_patch_res.status_code}")

    admin_del_req = factory.delete(f"/api/workforce/seller-hub/categories/{staff_created_cat_id}/")
    force_authenticate(admin_del_req, user=staff_admin)
    admin_del_res = detail_view(admin_del_req, pk=staff_created_cat_id)
    assert_test(admin_del_res.status_code == 200, "Staff Admin (is_staff=True) DELETE category succeeds (200 OK)", f"Got {admin_del_res.status_code}")

    # Super Admin (is_superuser=True) -> Succeeds
    super_post_req = factory.post("/api/workforce/seller-hub/categories/", {
        "name": f"Super Admin Cat {uuid.uuid4().hex[:4]}",
        "slug": f"super-admin-cat-{uuid.uuid4().hex[:4]}",
    })
    force_authenticate(super_post_req, user=superadmin)
    super_post_res = post_view(super_post_req)
    assert_test(super_post_res.status_code == 201, "Super Admin (is_superuser=True) POST category succeeds (201 Created)", f"Got {super_post_res.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. Cascading Level Lazy Loading (?parent_id=<id|null>)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 3. Cascading Level Loading (?parent_id) ---")
    # Roots
    req_root = factory.get("/api/workforce/seller-hub/catalog/categories/?parent_id=null")
    force_authenticate(req_root, user=vendor_user)
    res_root = view(req_root)
    root_ids = [c["id"] for c in res_root.data]
    assert_test(root_cat.id in root_ids, "parent_id=null returns root category", f"Roots: {root_ids}")

    # Level 2 under root
    req_l2 = factory.get(f"/api/workforce/seller-hub/catalog/categories/?parent_id={root_cat.id}")
    force_authenticate(req_l2, user=vendor_user)
    res_l2 = view(req_l2)
    l2_ids = [c["id"] for c in res_l2.data]
    assert_test(sub_dairy.id in l2_ids, "parent_id=root returns subcategory", f"L2 ids: {l2_ids}")
    dairy_item = next((c for c in res_l2.data if c["id"] == sub_dairy.id), None)
    assert_test(dairy_item and dairy_item["has_children"] is True and dairy_item["is_leaf"] is False,
                "Subcategory has_children=True and is_leaf=False")

    # Level 3 under dairy
    req_l3 = factory.get(f"/api/workforce/seller-hub/catalog/categories/?parent_id={sub_dairy.id}")
    force_authenticate(req_l3, user=vendor_user)
    res_l3 = view(req_l3)
    l3_ids = [c["id"] for c in res_l3.data]
    assert_test(leaf_milk.id in l3_ids and leaf_paneer.id in l3_ids,
                "parent_id=sub_dairy returns leaf categories", f"L3 ids: {l3_ids}")
    milk_item = next((c for c in res_l3.data if c["id"] == leaf_milk.id), None)
    assert_test(milk_item and milk_item["has_children"] is False and milk_item["is_leaf"] is True,
                "Leaf category has_children=False and is_leaf=True")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. Search (?q=<text>) with Full Breadcrumbs and Active Ancestor Filtering
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 4. Search (?q) and Inactive Chain Filtering ---")
    req_search = factory.get(f"/api/workforce/seller-hub/catalog/categories/?q={leaf_milk.name}")
    force_authenticate(req_search, user=vendor_user)
    res_search = view(req_search)
    assert_test(len(res_search.data) >= 1, "Search returns matching category", f"Matches: {len(res_search.data)}")
    search_milk = res_search.data[0]
    assert_test(search_milk["id"] == leaf_milk.id and search_milk["is_leaf"] is True,
                "Search item accurately flags is_leaf=True")
    assert_test(search_milk.get("path_string") and root_cat.name in search_milk["path_string"] and sub_dairy.name in search_milk["path_string"],
                "Search item includes full breadcrumb path_string", f"Path string: {search_milk.get('path_string')}")

    # Inactive ancestor chain test: leaf_under_inactive is active, but its parent is inactive
    req_inact = factory.get(f"/api/workforce/seller-hub/catalog/categories/?q={leaf_under_inactive.name}")
    force_authenticate(req_inact, user=vendor_user)
    res_inact = view(req_inact)
    inact_match = [c for c in res_inact.data if c["id"] == leaf_under_inactive.id]
    assert_test(len(inact_match) == 0,
                "Category with inactive parent is completely hidden from vendor picker", f"Matches: {len(inact_match)}")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. ONE LEAF RULE: Active Children vs Inactive Children
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 5. Unified One-Leaf Rule Verification ---")
    # Category with all inactive children -> IS A LEAF
    cat_all_inactive_children, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-cat-inactive-kids",
        defaults={"name": "P10 Cat With Inactive Kids", "parent": root_cat, "sort_order": 5, "is_active": True}
    )
    cat_all_inactive_children.parent = root_cat
    cat_all_inactive_children.is_active = True
    cat_all_inactive_children.save()

    child_inact_1, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-inact-child-1",
        defaults={"name": "Inactive Child 1", "parent": cat_all_inactive_children, "is_active": False}
    )
    child_inact_1.parent = cat_all_inactive_children
    child_inact_1.is_active = False
    child_inact_1.save()

    child_inact_2, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-inact-child-2",
        defaults={"name": "Inactive Child 2", "parent": cat_all_inactive_children, "is_active": False}
    )
    child_inact_2.parent = cat_all_inactive_children
    child_inact_2.is_active = False
    child_inact_2.save()

    # In picker endpoint, cat_all_inactive_children must have is_leaf=True
    req_inact_kids = factory.get(f"/api/workforce/seller-hub/catalog/categories/?q={cat_all_inactive_children.name}")
    force_authenticate(req_inact_kids, user=vendor_user)
    res_inact_kids = view(req_inact_kids)
    inact_kid_item = next((c for c in res_inact_kids.data if c["id"] == cat_all_inactive_children.id), None)
    assert_test(inact_kid_item and inact_kid_item["is_leaf"] is True,
                "Category with only inactive children reports is_leaf=True in picker", f"Item: {inact_kid_item}")

    # Product create with cat_all_inactive_children SUCCEEDS
    prod_view = SellerProductListView.as_view()
    req_p_inact_kids = factory.post("/api/workforce/seller-hub/products/", {
        "title": "Product Under Inactive Children Cat",
        "sku": f"SKU-INACTKIDS-{uuid.uuid4().hex[:4]}",
        "category": cat_all_inactive_children.id,
        "mrp": "100.00",
        "selling_price": "90.00",
    })
    force_authenticate(req_p_inact_kids, user=vendor_user)
    res_p_inact_kids = prod_view(req_p_inact_kids)
    assert_test(res_p_inact_kids.status_code == 201,
                "Product create with category having only inactive children succeeds (201 Created)",
                f"Got {res_p_inact_kids.status_code}: {res_p_inact_kids.data}")

    # Category with 1 active child -> NOT A LEAF
    cat_active_child, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-cat-active-kid",
        defaults={"name": "P10 Cat With Active Kid", "parent": root_cat, "sort_order": 6, "is_active": True}
    )
    cat_active_child.parent = root_cat
    cat_active_child.is_active = True
    cat_active_child.save()

    child_act, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-act-child",
        defaults={"name": "Active Child", "parent": cat_active_child, "is_active": True}
    )
    child_act.parent = cat_active_child
    child_act.is_active = True
    child_act.save()

    # In picker endpoint, cat_active_child must have is_leaf=False
    req_act_kid = factory.get(f"/api/workforce/seller-hub/catalog/categories/?q={cat_active_child.name}")
    force_authenticate(req_act_kid, user=vendor_user)
    res_act_kid = view(req_act_kid)
    act_kid_item = next((c for c in res_act_kid.data if c["id"] == cat_active_child.id), None)
    assert_test(act_kid_item and act_kid_item["is_leaf"] is False,
                "Category with active child reports is_leaf=False in picker")

    # Product create with cat_active_child FAILS (400 CATEGORY_NOT_LEAF)
    req_p_act_kid = factory.post("/api/workforce/seller-hub/products/", {
        "title": "Product Under Active Child Cat",
        "sku": f"SKU-ACTKID-{uuid.uuid4().hex[:4]}",
        "category": cat_active_child.id,
        "mrp": "100.00",
        "selling_price": "90.00",
    })
    force_authenticate(req_p_act_kid, user=vendor_user)
    res_p_act_kid = prod_view(req_p_act_kid)
    assert_test(res_p_act_kid.status_code == 400,
                "Product create with category having active child is rejected (400 CATEGORY_NOT_LEAF)",
                f"Got {res_p_act_kid.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. Product Creation Validation: Leaf Only & Active Chain Only
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 6. Product Creation Validation ---")
    # Valid leaf category succeeds (201 Created)
    valid_sku = f"SKU-MILK-{uuid.uuid4().hex[:4]}"
    req_p_valid = factory.post("/api/workforce/seller-hub/products/", {
        "title": "Fresh Cow Milk 1L",
        "sku": valid_sku,
        "category": leaf_milk.id,
        "mrp": "70.00",
        "selling_price": "65.00",
        "unit": "litre",
        "pack_size": "1L",
        "status": "APPROVED",
    })
    force_authenticate(req_p_valid, user=vendor_user)
    res_p_valid = prod_view(req_p_valid)
    assert_test(res_p_valid.status_code == 201, "Product creation with valid leaf category succeeds (201 Created)", f"Got {res_p_valid.status_code}: {res_p_valid.data}")
    created_product_id = res_p_valid.data["product"]["id"]

    # Inactive parent chain rejected
    req_p_inact = factory.post("/api/workforce/seller-hub/products/", {
        "title": "Invalid Inactive Chain Product",
        "sku": f"SKU-INACT-{uuid.uuid4().hex[:4]}",
        "category": leaf_under_inactive.id,
        "mrp": "100.00",
        "selling_price": "90.00",
    })
    force_authenticate(req_p_inact, user=vendor_user)
    res_p_inact = prod_view(req_p_inact)
    assert_test(res_p_inact.status_code == 400, "Product creation with inactive parent chain rejected (400 Bad Request)", f"Got {res_p_inact.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. Product Update & Legacy Compatibility
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7. Product Update & Legacy Compatibility ---")
    p_detail_view = SellerProductDetailView.as_view()

    # Legacy product created directly in DB with non-leaf category
    legacy_product = SellerProduct.objects.create(
        company=vendor_company,
        category=sub_dairy,  # Non-leaf
        title="Legacy Dairy Pack",
        sku=f"SKU-LEGACY-{uuid.uuid4().hex[:4]}",
        mrp=Decimal("150.00"),
        selling_price=Decimal("140.00"),
        status="DRAFT"
    )

    # Partial update without changing category (e.g. updating price/title) should SUCCEED
    req_update_price = factory.patch(f"/api/workforce/seller-hub/products/{legacy_product.id}/", {
        "selling_price": "135.00",
        "title": "Legacy Dairy Pack Updated",
    })
    force_authenticate(req_update_price, user=vendor_user)
    res_update_price = p_detail_view(req_update_price, pk=legacy_product.id)
    assert_test(res_update_price.status_code == 200,
                "Legacy product with unchanged non-leaf category can update other fields (200 OK)",
                f"Got {res_update_price.status_code}: {res_update_price.data}")

    # Updating category on legacy product to another non-leaf category must be REJECTED
    req_update_cat_nonleaf = factory.patch(f"/api/workforce/seller-hub/products/{legacy_product.id}/", {
        "category": root_cat.id,
    })
    force_authenticate(req_update_cat_nonleaf, user=vendor_user)
    res_update_cat_nonleaf = p_detail_view(req_update_cat_nonleaf, pk=legacy_product.id)
    assert_test(res_update_cat_nonleaf.status_code == 400,
                "Changing category to non-leaf on update is rejected (400 Bad Request)",
                f"Got {res_update_cat_nonleaf.status_code}")

    # Updating category on legacy product to a valid leaf must SUCCEED
    req_update_cat_leaf = factory.patch(f"/api/workforce/seller-hub/products/{legacy_product.id}/", {
        "category": leaf_paneer.id,
    })
    force_authenticate(req_update_cat_leaf, user=vendor_user)
    res_update_cat_leaf = p_detail_view(req_update_cat_leaf, pk=legacy_product.id)
    assert_test(res_update_cat_leaf.status_code == 200,
                "Changing category to valid leaf on update succeeds (200 OK)",
                f"Got {res_update_cat_leaf.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 8. Product-Conflict Guards on Admin Category Changes (a, b, c)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 8. Admin Hierarchy Product-Conflict Guards (a, b, c) ---")
    admin_detail_view = AdminSellerHubCategoryDetailView.as_view()
    admin_list_view = AdminSellerHubCategoryListView.as_view()

    # leaf_milk has a product attached (Fresh Cow Milk 1L, id: created_product_id)

    # (a) PATCH parent to a category that has products -> 409 CATEGORY_HAS_PRODUCTS
    unrelated_cat, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-unrelated",
        defaults={"name": "P10 Unrelated Cat", "is_active": True}
    )
    req_guard_a = factory.patch(f"/api/workforce/seller-hub/categories/{unrelated_cat.id}/", {
        "parent_id": leaf_milk.id,
    })
    force_authenticate(req_guard_a, user=superadmin)
    res_guard_a = admin_detail_view(req_guard_a, pk=unrelated_cat.id)
    assert_test(res_guard_a.status_code == 409 and res_guard_a.data.get("code") == "CATEGORY_HAS_PRODUCTS",
                "(a) PATCH parent to a category with products is rejected (409 CATEGORY_HAS_PRODUCTS)",
                f"Got {res_guard_a.status_code}: {res_guard_a.data}")

    # (b) PATCH reactivate child under a category that has products -> 409 CATEGORY_HAS_PRODUCTS
    inactive_child_under_milk, _ = SellerHubCategory.objects.get_or_create(
        slug=f"{test_prefix}-inact-under-milk",
        defaults={"name": "Inactive Under Milk", "parent": leaf_milk, "is_active": False}
    )
    inactive_child_under_milk.parent = leaf_milk
    inactive_child_under_milk.is_active = False
    inactive_child_under_milk.save()

    req_guard_b = factory.patch(f"/api/workforce/seller-hub/categories/{inactive_child_under_milk.id}/", {
        "is_active": True,
    })
    force_authenticate(req_guard_b, user=superadmin)
    res_guard_b = admin_detail_view(req_guard_b, pk=inactive_child_under_milk.id)
    assert_test(res_guard_b.status_code == 409 and res_guard_b.data.get("code") == "CATEGORY_HAS_PRODUCTS",
                "(b) PATCH reactivating child under a category with products is rejected (409 CATEGORY_HAS_PRODUCTS)",
                f"Got {res_guard_b.status_code}: {res_guard_b.data}")

    # (c) POST create child under a category that has products -> 409 CATEGORY_HAS_PRODUCTS
    req_guard_c = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "New Subcategory Under Milk",
        "parent_id": leaf_milk.id,
    })
    force_authenticate(req_guard_c, user=superadmin)
    res_guard_c = admin_list_view(req_guard_c)
    assert_test(res_guard_c.status_code == 409 and res_guard_c.data.get("code") == "CATEGORY_HAS_PRODUCTS",
                "(c) POST creating child under a category with products is rejected (409 CATEGORY_HAS_PRODUCTS)",
                f"Got {res_guard_c.status_code}: {res_guard_c.data}")

    # ─────────────────────────────────────────────────────────────────────────
    # 9. Other Creation Paths: Bulk CSV Upload Category Validation (Preview & Commit)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 9. Other Creation Paths: Bulk Upload Category Validation ---")
    bulk_view = SellerProductBulkUploadView.as_view()

    # Bulk CSV Preview accepts valid leaf
    csv_valid = (
        "Title,Description,Brand,SKU,Barcode,Category_Slug,Unit,Pack_Size,MRP,Selling_Price,Tax_Rate,HSN_Code\n"
        f"Bulk Cow Milk 1L,Fresh milk,DairyBrand,SKU-BULK-1,,{leaf_paneer.slug},litre,1L,70.00,65.00,0,0401\n"
    )
    req_bulk_preview = factory.post(
        "/api/workforce/seller-hub/products/bulk-upload/?preview=true",
        {"file": io.BytesIO(csv_valid.encode("utf-8"))},
        format="multipart",
    )
    req_bulk_preview.FILES["file"] = django.core.files.uploadedfile.SimpleUploadedFile("products.csv", csv_valid.encode("utf-8"), content_type="text/csv")
    force_authenticate(req_bulk_preview, user=vendor_user)
    res_bulk_preview = bulk_view(req_bulk_preview)
    assert_test(res_bulk_preview.status_code == 200 and res_bulk_preview.data.get("valid_rows_count") == 1,
                "Bulk upload preview accepts valid leaf category", f"Got: {res_bulk_preview.data}")

    # Bulk CSV Commit Step REJECTS non-leaf category
    csv_nonleaf = (
        "Title,Description,Brand,SKU,Barcode,Category_Slug,Unit,Pack_Size,MRP,Selling_Price,Tax_Rate,HSN_Code\n"
        f"Bulk Invalid NonLeaf,Desc,Brand,SKU-BULK-FAIL,,{sub_dairy.slug},litre,1L,70.00,65.00,0,0401\n"
    )
    req_bulk_commit_fail = factory.post(
        "/api/workforce/seller-hub/products/bulk-upload/",
        {"file": io.BytesIO(csv_nonleaf.encode("utf-8"))},
        format="multipart",
    )
    req_bulk_commit_fail.FILES["file"] = django.core.files.uploadedfile.SimpleUploadedFile("products_fail.csv", csv_nonleaf.encode("utf-8"), content_type="text/csv")
    force_authenticate(req_bulk_commit_fail, user=vendor_user)
    res_bulk_commit_fail = bulk_view(req_bulk_commit_fail)
    assert_test(res_bulk_commit_fail.status_code == 400 and res_bulk_commit_fail.data.get("failed_rows_count") == 1,
                "Bulk upload commit step rejects non-leaf category with 400 and blocks product creation",
                f"Got: {res_bulk_commit_fail.data}")

    # ─────────────────────────────────────────────────────────────────────────
    # 10. Single Query Bounded Performance
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 10. Database Query Performance ---")
    reset_queries()
    req_perf = factory.get("/api/workforce/seller-hub/catalog/categories/?tree=true")
    force_authenticate(req_perf, user=vendor_user)
    with django.db.connection.cursor() as cursor:
        res_perf = view(req_perf)
    query_count = len(connection.queries)
    assert_test(res_perf.status_code == 200, "Tree endpoint returns 200 OK")
    assert_test(query_count <= 2, f"Tree resolution executes in bounded SQL queries (measured: {query_count} queries)")

    # ─────────────────────────────────────────────────────────────────────────
    # 11. Seed Safety: Refusal to Attach Children & Idempotency
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 11. Seed Safety & Conflict Refusal Verification ---")
    from django.core.management import call_command

    # Create an existing category that has products attached
    seed_conflict_cat, _ = SellerHubCategory.objects.get_or_create(
        slug="beverages",
        defaults={"name": "Beverages", "sort_order": 1, "is_active": True}
    )
    seed_conflict_cat.is_active = True
    seed_conflict_cat.save()

    # Attach a product to this category
    SellerProduct.objects.create(
        company=vendor_company,
        category=seed_conflict_cat,
        title="Beverage Product Test",
        sku=f"SKU-BEV-{uuid.uuid4().hex[:4]}",
        mrp=Decimal("50.00"),
        selling_price=Decimal("45.00"),
        status="APPROVED"
    )

    # Run seed in dry-run mode -> Should report conflict and refuse subcategories
    out_dry = io.StringIO()
    call_command("seed_grocery_categories", stdout=out_dry)
    dry_text = out_dry.getvalue()
    assert_test("CONFLICT / REFUSED" in dry_text and "beverages" in dry_text,
                "seed_grocery_categories dry-run reports conflict on category with products")

    # Run seed in --commit mode
    out_commit1 = io.StringIO()
    call_command("seed_grocery_categories", commit=True, stdout=out_commit1)
    commit1_text = out_commit1.getvalue()
    assert_test("CONFLICT / REFUSED" in commit1_text,
                "seed_grocery_categories --commit refuses attaching children to category with products")
    # Subcategories of beverages (e.g. tea-coffee) must NOT be created under seed_conflict_cat
    assert_test(not SellerHubCategory.objects.filter(slug="tea-coffee", parent=seed_conflict_cat).exists(),
                "Subcategories were NOT attached to category that has products")

    # Re-running --commit must be idempotent (0 created)
    out_commit2 = io.StringIO()
    call_command("seed_grocery_categories", commit=True, stdout=out_commit2)
    commit2_text = out_commit2.getvalue()
    assert_test("Created: 0" in commit2_text,
                "Re-running seed_grocery_categories --commit creates 0 new items (idempotent)")

    # ─────────────────────────────────────────────────────────────────────────
    # 12. Customer Marketplace Payload Snapshot Verification
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 12. Customer Marketplace Payload Snapshot Verification ---")
    # Setup approved product with inventory
    mkt_product = SellerProduct.objects.create(
        company=vendor_company,
        category=leaf_milk,
        title="Marketplace Snapshot Product",
        brand="SnapshotBrand",
        sku=f"SKU-SNAP-{uuid.uuid4().hex[:4]}",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
        unit="piece",
        pack_size="1 pc",
        status=SellerProduct.Status.APPROVED,
    )
    SellerInventory.objects.create(
        product=mkt_product,
        company=vendor_company,
        on_hand_qty=Decimal("10.000"),
        reserved_qty=Decimal("0.000"),
    )

    expected_product_keys = {
        "id", "sku", "title", "brand", "unit", "pack_size", "mrp", "selling_price",
        "currency", "primary_image", "images", "description", "storage_info",
        "expiry_info", "tax_rate", "hsn_code", "seller_id", "seller_name",
        "category_path", "category_hierarchy", "available_stock", "in_stock",
        "seller", "category", "availability", "updated_at"
    }

    # Test Product List Payload
    mkt_list_view = MarketplaceProductListView.as_view()
    req_mkt_list = factory.get(
        "/api/workforce/marketplace/products/",
        HTTP_X_WORKFORCE_WEBHOOK_SECRET=TEST_SECRET,
    )
    res_mkt_list = mkt_list_view(req_mkt_list)
    assert_test(res_mkt_list.status_code == 200, "Marketplace product list returns 200 OK")
    assert_test(len(res_mkt_list.data["results"]) > 0, "Marketplace product list contains products")
    first_item = res_mkt_list.data["results"][0]
    list_keys = set(first_item.keys())
    missing_list_keys = expected_product_keys - list_keys
    extra_list_keys = list_keys - expected_product_keys
    assert_test(list_keys == expected_product_keys,
                "Marketplace product list item matches exact expected payload schema",
                f"Missing: {missing_list_keys}, Extra: {extra_list_keys}")

    # Test Product Detail Payload
    mkt_detail_view = MarketplaceProductDetailView.as_view()
    req_mkt_detail = factory.get(
        f"/api/workforce/marketplace/products/{mkt_product.id}/",
        HTTP_X_WORKFORCE_WEBHOOK_SECRET=TEST_SECRET,
    )
    res_mkt_detail = mkt_detail_view(req_mkt_detail, pk=mkt_product.id)
    assert_test(res_mkt_detail.status_code == 200, "Marketplace product detail returns 200 OK")
    detail_keys = set(res_mkt_detail.data.keys())
    assert_test(detail_keys == expected_product_keys,
                "Marketplace product detail matches exact expected payload schema",
                f"Missing: {expected_product_keys - detail_keys}, Extra: {detail_keys - expected_product_keys}")

    # ─────────────────────────────────────────────────────────────────────────
    # 13. AdminCatalogCategoryActiveListView Performance & Correctness
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 13. AdminCatalogCategoryActiveListView Performance & Correctness ---")

    # 1. Build test tree in SQLite
    # 60 roots each with 2 children
    p13_prefix = f"p13_{uuid.uuid4().hex[:6]}"

    p13_roots = []
    p13_leaves = []

    for i in range(1, 61):
        r = SellerHubCategory.objects.create(
            name=f"TreeRoot{i:02d}_{p13_prefix}",
            slug=f"tree-root-{i:02d}-{p13_prefix}",
            sort_order=i,
            is_active=True,
        )
        c1 = SellerHubCategory.objects.create(
            name=f"TreeChild{i:02d}_1_{p13_prefix}",
            slug=f"tree-child-{i:02d}-1-{p13_prefix}",
            parent=r,
            sort_order=1,
            is_active=True,
        )
        c2 = SellerHubCategory.objects.create(
            name=f"TreeChild{i:02d}_2_{p13_prefix}",
            slug=f"tree-child-{i:02d}-2-{p13_prefix}",
            parent=r,
            sort_order=2,
            is_active=True,
        )
        p13_roots.append(r)
        p13_leaves.extend([c1, c2])

    # One inactive root with an active child (must be excluded)
    inact_root_p13 = SellerHubCategory.objects.create(
        name=f"InactiveRoot_{p13_prefix}",
        slug=f"inact-root-{p13_prefix}",
        sort_order=900,
        is_active=False,
    )
    act_child_inact_p13 = SellerHubCategory.objects.create(
        name=f"ActiveChildOfInactive_{p13_prefix}",
        slug=f"act-child-of-inact-{p13_prefix}",
        parent=inact_root_p13,
        sort_order=1,
        is_active=True,
    )

    # One inactive leaf (excluded) under an active root with an active sibling
    inact_leaf_parent_p13 = SellerHubCategory.objects.create(
        name=f"ActiveParentOfInactLeaf_{p13_prefix}",
        slug=f"act-parent-of-inact-leaf-{p13_prefix}",
        sort_order=901,
        is_active=True,
    )
    act_sibling_p13 = SellerHubCategory.objects.create(
        name=f"ActiveSiblingLeaf_{p13_prefix}",
        slug=f"act-sibling-leaf-{p13_prefix}",
        parent=inact_leaf_parent_p13,
        sort_order=1,
        is_active=True,
    )
    inact_leaf_p13 = SellerHubCategory.objects.create(
        name=f"InactiveChildLeaf_{p13_prefix}",
        slug=f"inact-child-leaf-{p13_prefix}",
        parent=inact_leaf_parent_p13,
        sort_order=2,
        is_active=False,
    )

    # One 3-level branch
    branch_l1_p13 = SellerHubCategory.objects.create(
        name=f"BranchL1_{p13_prefix}",
        slug=f"branch-l1-{p13_prefix}",
        sort_order=902,
        is_active=True,
    )
    branch_l2_p13 = SellerHubCategory.objects.create(
        name=f"BranchL2_{p13_prefix}",
        slug=f"branch-l2-{p13_prefix}",
        parent=branch_l1_p13,
        sort_order=1,
        is_active=True,
    )
    branch_l3_p13 = SellerHubCategory.objects.create(
        name=f"BranchL3_{p13_prefix}",
        slug=f"branch-l3-{p13_prefix}",
        parent=branch_l2_p13,
        sort_order=1,
        is_active=True,
    )

    # Build independently expected category list from all categories in DB:
    # An active category is valid iff all its ancestors are active.
    # A category is a leaf iff it has no active children whose ancestor chain is active.
    all_cats_db = {c.id: c for c in SellerHubCategory.objects.all()}

    def is_valid_active(cat_id):
        visited = set()
        curr = cat_id
        while curr is not None:
            if curr in visited:
                return False
            visited.add(curr)
            c = all_cats_db.get(curr)
            if not c or not c.is_active:
                return False
            curr = c.parent_id
        return True

    valid_active_cats = [c for c in all_cats_db.values() if is_valid_active(c.id)]
    valid_ids_set = {c.id for c in valid_active_cats}

    def has_active_kid(cat_id):
        return any(c.parent_id == cat_id and c.id in valid_ids_set for c in valid_active_cats)

    def get_path(cat):
        names = [cat.name]
        curr = cat.parent_id
        visited = {cat.id}
        while curr is not None and curr in all_cats_db and curr not in visited:
            visited.add(curr)
            names.insert(0, all_cats_db[curr].name)
            curr = all_cats_db[curr].parent_id
        return " > ".join(names)

    expected_all_list = []
    for c in valid_active_cats:
        is_leaf_val = not has_active_kid(c.id)
        parent_obj = all_cats_db.get(c.parent_id)
        expected_all_list.append({
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "path": get_path(c),
            "parent_name": parent_obj.name if parent_obj else None,
            "icon": c.icon,
            "is_leaf": is_leaf_val,
        })
    expected_all_list.sort(key=lambda x: x["path"])
    expected_leaf_only_list = [item for item in expected_all_list if item["is_leaf"]]

    active_view = AdminCatalogCategoryActiveListView.as_view()

    # 2. Test as authenticated seller
    # GET /seller-hub/categories/active/
    req_act_seller = factory.get("/api/workforce/seller-hub/categories/active/")
    force_authenticate(req_act_seller, user=vendor_user)
    with CaptureQueriesContext(connection) as ctx_seller_all:
        res_act_seller = active_view(req_act_seller)

    assert_test(res_act_seller.status_code == 200, "Seller GET /categories/active/ returns 200 OK")
    assert_test(res_act_seller.data == expected_all_list, "Seller GET /categories/active/ matches expected JSON data")
    seller_all_qcount = len(ctx_seller_all.captured_queries)
    assert_test(seller_all_qcount <= 4, f"Seller GET /categories/active/ query count <= 4 (observed: {seller_all_qcount})")

    # GET /seller-hub/categories/active/?leaf_only=true
    req_leaf_seller = factory.get("/api/workforce/seller-hub/categories/active/?leaf_only=true")
    force_authenticate(req_leaf_seller, user=vendor_user)
    with CaptureQueriesContext(connection) as ctx_seller_leaf:
        res_leaf_seller = active_view(req_leaf_seller)

    assert_test(res_leaf_seller.status_code == 200, "Seller GET /categories/active/?leaf_only=true returns 200 OK")
    assert_test(res_leaf_seller.data == expected_leaf_only_list, "Seller GET /categories/active/?leaf_only=true matches expected leaf JSON data")
    seller_leaf_qcount = len(ctx_seller_leaf.captured_queries)
    assert_test(seller_leaf_qcount <= 4, f"Seller GET /categories/active/?leaf_only=true query count <= 4 (observed: {seller_leaf_qcount})")

    # 3. Test as platform admin
    # GET /seller-hub/categories/active/
    req_act_admin = factory.get("/api/workforce/seller-hub/categories/active/")
    force_authenticate(req_act_admin, user=superadmin)
    with CaptureQueriesContext(connection) as ctx_admin_all:
        res_act_admin = active_view(req_act_admin)

    assert_test(res_act_admin.status_code == 200, "Platform Admin GET /categories/active/ returns 200 OK")
    assert_test(res_act_admin.data == expected_all_list, "Platform Admin GET /categories/active/ matches expected JSON data")
    admin_all_qcount = len(ctx_admin_all.captured_queries)
    assert_test(admin_all_qcount <= 4, f"Platform Admin GET /categories/active/ query count <= 4 (observed: {admin_all_qcount})")

    # GET /seller-hub/categories/active/?leaf_only=true
    req_leaf_admin = factory.get("/api/workforce/seller-hub/categories/active/?leaf_only=true")
    force_authenticate(req_leaf_admin, user=superadmin)
    with CaptureQueriesContext(connection) as ctx_admin_leaf:
        res_leaf_admin = active_view(req_leaf_admin)

    assert_test(res_leaf_admin.status_code == 200, "Platform Admin GET /categories/active/?leaf_only=true returns 200 OK")
    assert_test(res_leaf_admin.data == expected_leaf_only_list, "Platform Admin GET /categories/active/?leaf_only=true matches expected leaf JSON data")
    admin_leaf_qcount = len(ctx_admin_leaf.captured_queries)
    assert_test(admin_leaf_qcount <= 4, f"Platform Admin GET /categories/active/?leaf_only=true query count <= 4 (observed: {admin_leaf_qcount})")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {passed_count} PASSED, {failed_count} FAILED")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
