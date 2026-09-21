"""
test_phase11_category_product_approval.py

Phase 11: Vendor Categories Approval & Approved-Only Inventory Verification Test Suite.
Verifies:
1. Role Gating & Permissions:
   - Anonymous -> 401 Unauthorized on all admin approval endpoints.
   - Seller -> 403 Forbidden on all admin approval endpoints.
   - Staff Admin -> 200 OK.
   - Superadmin -> 200 OK.
2. Admin Seller List for Approval:
   - Correct aggregation of pending, approved, rejected, total counts, and last_submitted_at.
   - Aggregation handles SUBMITTED, UNDER_REVIEW, CHANGES_REQUESTED in pending_count.
   - Search by seller/company name.
   - has_pending=true filter.
   - Ordering by most pending first.
   - Bounded query count performance (e.g. 30 sellers, 300 products in bounded SQL queries).
3. Admin Seller Product List for Approval:
   - Default status is PENDING (submitted/under review/changes requested).
   - Status filters (PENDING, APPROVED, REJECTED, ALL).
   - Category filter includes descendant products.
   - Search by title/SKU.
   - Cross-seller isolation (Seller B's products never appear for Seller A).
4. Product Detail for Review:
   - Returns all product fields, images, category path, path_string, audit history.
5. Status Coverage & Approve/Reject Transitions:
   - Approve SUBMITTED -> APPROVED (200 OK).
   - Approve UNDER_REVIEW -> APPROVED (200 OK).
   - Approve CHANGES_REQUESTED -> APPROVED (200 OK).
   - Reject SUBMITTED -> REJECTED (200 OK).
   - Reject UNDER_REVIEW -> REJECTED (200 OK).
   - Reject CHANGES_REQUESTED -> REJECTED (200 OK).
   - Approve already APPROVED product -> 409 ALREADY_APPROVED (not 500).
   - Approve PAUSED product -> 409 INVALID_STATE (not 500).
   - Approve DRAFT product -> 409 INVALID_STATE (not 500).
   - Reject without reason or with reason < 5 chars -> 400 Bad Request.
   - Approve with invalid category (inactive or non-leaf) -> 409 CATEGORY_NOT_ELIGIBLE.
   - Bulk approve -> per-id results.
6. Re-approval Rule Checks:
   - Editing title of APPROVED product -> sends to SUBMITTED and blocks stock writes with 409.
   - Editing price of APPROVED product -> sends to SUBMITTED and blocks stock writes with 409.
   - Editing description of APPROVED product -> sends to SUBMITTED and blocks stock writes with 409.
   - Editing images of APPROVED product -> sends to SUBMITTED and blocks stock writes with 409.
   - Editing category of APPROVED product -> sends to SUBMITTED and blocks stock writes with 409.
   - Stock-only adjustment on APPROVED product -> retains APPROVED status.
7. Resubmission:
   - Rejected product submitted -> resets to SUBMITTED and clears rejection reason.
8. Inventory Gating:
   - Inventory list returns only APPROVED products in active category chain.
   - Stock initialize and stock adjust on non-approved products -> 409 PRODUCT_NOT_APPROVED.
   - Stock initialize and stock adjust on approved products -> succeeds (201/200).
9. Marketplace Integration Compatibility:
   - Marketplace payload format is preserved.
   - Unapproved products are hidden from sellable products feed.
"""

import os
import sys
import uuid
import tempfile
from decimal import Decimal

# Ensure temporary SQLite is used for all tests (NEVER PostgreSQL)
if not os.environ.get("SEVO_E2E_SQLITE_PATH"):
    temp_sqlite = os.path.join(tempfile.gettempdir(), f"sevo_phase11_test_{uuid.uuid4().hex[:8]}.sqlite3")
    os.environ["SEVO_E2E_SQLITE_PATH"] = temp_sqlite

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection, reset_queries
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
    SellerProductImage,
    SellerInventory,
    SellerProductAuditLog,
    SellerOrder,
    SellerOrderItem,
    SellerReturn,
    SellerClaim,
    VendorCoupon,
)
from accounts.views import LoginView, MeView
from accounts.platform import is_platform_admin_user
from workforce_api.views_seller_hub import (
    AdminSellerApprovalListView,
    AdminSellerProductApprovalListView,
    AdminProductApprovalDetailView,
    AdminProductApproveView,
    AdminProductRejectView,
    AdminProductBulkApproveView,
    SellerProductListView,
    SellerProductDetailView,
    SellerProductSubmitView,
    SellerProductBatchListView,
    SellerInventoryListView,
    SellerInventoryInitializeView,
    SellerInventoryAdjustView,
    AdminCatalogCategoryListView,
    AdminCatalogCategoryDetailView,
    AdminSellerHubCategoryListView,
    AdminSellerHubCategoryDetailView,
    SellerCatalogCategoryListView,
    SellerOrderDetailView,
    SellerOrderStatusTransitionView,
    SellerReturnListView,
    SellerReturnDetailView,
    SellerReturnReviewView,
    SellerClaimListView,
    SellerClaimDetailView,
    SellerClaimRespondView,
    AdminSellerCouponListView,
    AdminSellerCouponDetailView,
)


User = get_user_model()
factory = APIRequestFactory()

def run_tests():
    print("\n" + "=" * 80)
    print("PHASE 11: VENDOR CATEGORIES APPROVAL & APPROVED-ONLY INVENTORY TEST SUITE")
    print("=" * 80 + "\n")

    test_count = 0
    passed_count = 0

    def test(name, condition, err_msg=""):
        nonlocal test_count, passed_count
        test_count += 1
        if condition:
            passed_count += 1
            print(f"  [PASS] {test_count:02d}. {name}")
        else:
            print(f"  [FAIL] {test_count:02d}. {name} - {err_msg}")

    # ─────────────────────────────────────────────────────────────────────────
    # 0. FIXTURES SETUP
    # ─────────────────────────────────────────────────────────────────────────
    # Companies (company_admin is created first so company.id == 1 is platform)
    company_admin = Company.objects.create(
        company_name="Admin HQ",
        business_type="platform",
        is_active=True,
    )
    company_seller_a = Company.objects.create(
        company_name="Fresh Mart Seller A",
        business_type="grocery_supplier",
        is_active=True,
    )
    company_seller_b = Company.objects.create(
        company_name="Organic Valley Seller B",
        business_type="grocery_supplier",
        is_active=True,
    )

    # Users
    user_seller_a = User.objects.create_user(
        username="seller_a_user",
        email="seller_a@test.com",
        password="password123",
        role="seller",
        company=company_seller_a,
    )
    user_seller_b = User.objects.create_user(
        username="seller_b_user",
        email="seller_b@test.com",
        password="password123",
        role="seller",
        company=company_seller_b,
    )
    user_admin = User.objects.create_superuser(
        username="staff_admin_user",
        email="admin@test.com",
        password="password123",
        company=company_admin,
    )
    user_superadmin = User.objects.create_superuser(
        username="superadmin_user",
        email="superadmin@test.com",
        password="password123",
        company=company_admin,
    )

    # Categories
    cat_root = SellerHubCategory.objects.create(
        name="Groceries & Staples",
        slug="groceries-staples",
        is_active=True,
    )
    cat_sub = SellerHubCategory.objects.create(
        name="Rice & Grains",
        slug="rice-grains",
        parent=cat_root,
        is_active=True,
    )
    cat_leaf = SellerHubCategory.objects.create(
        name="Basmati Rice",
        slug="basmati-rice",
        parent=cat_sub,
        is_active=True,
    )
    cat_leaf2 = SellerHubCategory.objects.create(
        name="Brown Rice",
        slug="brown-rice",
        parent=cat_sub,
        is_active=True,
    )
    cat_inactive = SellerHubCategory.objects.create(
        name="Archived Category",
        slug="archived-cat",
        is_active=False,
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 1. ROLE GATING TESTS
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 1. ROLE GATING & PERMISSIONS ---")

    # 1a. Anonymous -> 401 on seller list
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
    resp = AdminSellerApprovalListView.as_view()(req)
    test("Anonymous user on approval seller list -> 401", resp.status_code == status.HTTP_401_UNAUTHORIZED, f"got {resp.status_code}")

    # 1b. Seller -> 403 on seller list
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
    force_authenticate(req, user=user_seller_a)
    resp = AdminSellerApprovalListView.as_view()(req)
    test("Seller user on approval seller list -> 403", resp.status_code == status.HTTP_403_FORBIDDEN, f"got {resp.status_code}")

    # 1c. Staff Admin -> 200 on seller list
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerApprovalListView.as_view()(req)
    test("Staff Admin on approval seller list -> 200", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

    # 1d. Superadmin -> 200 on seller list
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
    force_authenticate(req, user=user_superadmin)
    resp = AdminSellerApprovalListView.as_view()(req)
    test("Superadmin on approval seller list -> 200", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 2. SELLER LIST AGGREGATION & SEARCH
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 2. ADMIN SELLER LIST AGGREGATION ---")

    # Create products for Seller A: 1 submitted, 1 under_review, 1 changes_requested, 1 approved, 1 rejected
    prod_a1 = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Seller A Basmati 1kg",
        sku="SKU-A-001",
        mrp=Decimal("150.00"),
        selling_price=Decimal("130.00"),
        status=SellerProduct.Status.SUBMITTED,
    )
    prod_a2 = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Seller A Basmati 5kg",
        sku="SKU-A-002",
        mrp=Decimal("600.00"),
        selling_price=Decimal("550.00"),
        status=SellerProduct.Status.UNDER_REVIEW,
    )
    prod_a_cr = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Seller A Basmati CR",
        sku="SKU-A-CR",
        mrp=Decimal("250.00"),
        selling_price=Decimal("220.00"),
        status=SellerProduct.Status.CHANGES_REQUESTED,
        admin_review_note="Fix ingredient list",
    )
    prod_a3 = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Seller A Basmati Premium",
        sku="SKU-A-003",
        mrp=Decimal("200.00"),
        selling_price=Decimal("180.00"),
        status=SellerProduct.Status.APPROVED,
    )
    prod_a4 = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Seller A Rejected Item",
        sku="SKU-A-004",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
        status=SellerProduct.Status.REJECTED,
        admin_review_note="Blurry image",
    )

    # Create products for Seller B: 0 submitted, 2 approved
    prod_b1 = SellerProduct.objects.create(
        company=company_seller_b,
        category=cat_leaf,
        title="Seller B Basmati 1kg",
        sku="SKU-B-001",
        mrp=Decimal("140.00"),
        selling_price=Decimal("120.00"),
        status=SellerProduct.Status.APPROVED,
    )
    prod_b2 = SellerProduct.objects.create(
        company=company_seller_b,
        category=cat_leaf,
        title="Seller B Brown Rice",
        sku="SKU-B-002",
        mrp=Decimal("180.00"),
        selling_price=Decimal("160.00"),
        status=SellerProduct.Status.APPROVED,
    )

    # 2a. Fetch all sellers
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerApprovalListView.as_view()(req)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("Seller list returns 2 sellers", len(data) == 2, f"got {len(data)}")

    seller_a_row = next((r for r in data if r["seller_id"] == company_seller_a.id), None)
    test("Seller A aggregated counts correct (3 pending [SUBMITTED+UNDER_REVIEW+CHANGES_REQUESTED], 1 approved, 1 rejected, 5 total)",
         seller_a_row and seller_a_row["pending_count"] == 3 and seller_a_row["approved_count"] == 1 and
         seller_a_row["rejected_count"] == 1 and seller_a_row["total_count"] == 5,
         f"got {seller_a_row}")

    seller_b_row = next((r for r in data if r["seller_id"] == company_seller_b.id), None)
    test("Seller B aggregated counts correct (0 pending, 2 approved, 0 rejected, 2 total)",
         seller_b_row and seller_b_row["pending_count"] == 0 and seller_b_row["approved_count"] == 2 and
         seller_b_row["total_count"] == 2,
         f"got {seller_b_row}")

    # 2b. has_pending=true filter
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/?has_pending=true")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerApprovalListView.as_view()(req)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("has_pending=true returns only Seller A", len(data) == 1 and data[0]["seller_id"] == company_seller_a.id, f"got {data}")

    # 2c. Search filter
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/?search=Organic")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerApprovalListView.as_view()(req)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("search='Organic' returns only Seller B", len(data) == 1 and data[0]["seller_id"] == company_seller_b.id, f"got {data}")

    # ─────────────────────────────────────────────────────────────────────────
    # 3. ADMIN SELLER PRODUCT LIST FOR APPROVAL
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 3. ADMIN SELLER PRODUCT LIST ---")

    # 3a. Default status filter is PENDING (returns 3 pending products for Seller A: SUBMITTED, UNDER_REVIEW, CHANGES_REQUESTED)
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_a.id}/products/")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerProductApprovalListView.as_view()(req, seller_id=company_seller_a.id)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("Default status filter PENDING returns 3 pending products for Seller A", len(data) == 3, f"got {len(data)}")

    # 3b. Status filter APPROVED returns 1 product
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_a.id}/products/?status=APPROVED")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerProductApprovalListView.as_view()(req, seller_id=company_seller_a.id)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("status=APPROVED returns 1 product for Seller A", len(data) == 1 and data[0]["id"] == prod_a3.id, f"got {data}")

    # 3c. Status filter ALL returns all 5 products
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_a.id}/products/?status=ALL")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerProductApprovalListView.as_view()(req, seller_id=company_seller_a.id)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("status=ALL returns 5 products for Seller A", len(data) == 5, f"got {len(data)}")

    # 3d. Category filter on root category includes descendant products
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_a.id}/products/?status=ALL&category_id={cat_root.id}")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerProductApprovalListView.as_view()(req, seller_id=company_seller_a.id)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("category_id filter on root category includes descendant products", len(data) == 5, f"got {len(data)}")

    # 3e. Search filter on title/SKU
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_a.id}/products/?status=ALL&search=SKU-A-002")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerProductApprovalListView.as_view()(req, seller_id=company_seller_a.id)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    test("search='SKU-A-002' returns exactly 1 product", len(data) == 1 and data[0]["sku"] == "SKU-A-002", f"got {data}")

    # 3f. Isolation: Seller A's products do NOT appear under Seller B's endpoint
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_b.id}/products/?status=ALL")
    force_authenticate(req, user=user_admin)
    resp = AdminSellerProductApprovalListView.as_view()(req, seller_id=company_seller_b.id)
    data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
    seller_a_ids = {prod_a1.id, prod_a2.id, prod_a_cr.id, prod_a3.id, prod_a4.id}
    b_returned_ids = {p["id"] for p in data}
    test("Seller B's products view contains none of Seller A's products", len(seller_a_ids.intersection(b_returned_ids)) == 0, f"overlap: {seller_a_ids.intersection(b_returned_ids)}")

    # ─────────────────────────────────────────────────────────────────────────
    # 4. APPROVAL, REJECTION & DETAIL VIEWS (STATUS COVERAGE)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 4. APPROVAL, REJECTION & STATUS COVERAGE ---")

    # 4a. Get Product Detail for review
    req = factory.get(f"/api/workforce/admin/seller-hub/approval/products/{prod_a1.id}/")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApprovalDetailView.as_view()(req, pk=prod_a1.id)
    test("Product detail for review returns 200 with full fields and path_string", resp.status_code == status.HTTP_200_OK and resp.data["id"] == prod_a1.id and "path_string" in resp.data, f"got {resp.data}")

    # 4b. Single Approve from SUBMITTED status
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_a1.id}/approve/", {"note": "Approved submitted item"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApproveView.as_view()(req, pk=prod_a1.id)
    prod_a1.refresh_from_db()
    test("Approve SUBMITTED product -> 200 OK and status becomes APPROVED", resp.status_code == status.HTTP_200_OK and prod_a1.status == SellerProduct.Status.APPROVED, f"got {resp.status_code}, status={prod_a1.status}")
    test("Approve records reviewed_by and reviewed_at", prod_a1.reviewed_by == user_admin and prod_a1.reviewed_at is not None, f"reviewed_by={prod_a1.reviewed_by}, reviewed_at={prod_a1.reviewed_at}")

    # 4c. Single Approve from UNDER_REVIEW status
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_a2.id}/approve/", {"note": "Approved under_review item"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApproveView.as_view()(req, pk=prod_a2.id)
    prod_a2.refresh_from_db()
    test("Approve UNDER_REVIEW product -> 200 OK and status becomes APPROVED", resp.status_code == status.HTTP_200_OK and prod_a2.status == SellerProduct.Status.APPROVED, f"got {resp.status_code}, status={prod_a2.status}")

    # 4d. Single Approve from CHANGES_REQUESTED status
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_a_cr.id}/approve/", {"note": "Approved changes_requested item"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApproveView.as_view()(req, pk=prod_a_cr.id)
    prod_a_cr.refresh_from_db()
    test("Approve CHANGES_REQUESTED product -> 200 OK and status becomes APPROVED", resp.status_code == status.HTTP_200_OK and prod_a_cr.status == SellerProduct.Status.APPROVED, f"got {resp.status_code}, status={prod_a_cr.status}")

    # 4e. Reject from SUBMITTED, UNDER_REVIEW, and CHANGES_REQUESTED
    prod_rej_sub = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Rej Sub", sku="REJ-SUB", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.SUBMITTED)
    prod_rej_ur = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Rej UR", sku="REJ-UR", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.UNDER_REVIEW)
    prod_rej_cr = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Rej CR", sku="REJ-CR", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.CHANGES_REQUESTED)

    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_rej_sub.id}/reject/", {"reason": "Rejection from SUBMITTED"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductRejectView.as_view()(req, pk=prod_rej_sub.id)
    prod_rej_sub.refresh_from_db()
    test("Reject SUBMITTED product -> 200 OK and status becomes REJECTED", resp.status_code == status.HTTP_200_OK and prod_rej_sub.status == SellerProduct.Status.REJECTED, f"status={prod_rej_sub.status}")

    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_rej_ur.id}/reject/", {"reason": "Rejection from UNDER_REVIEW"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductRejectView.as_view()(req, pk=prod_rej_ur.id)
    prod_rej_ur.refresh_from_db()
    test("Reject UNDER_REVIEW product -> 200 OK and status becomes REJECTED", resp.status_code == status.HTTP_200_OK and prod_rej_ur.status == SellerProduct.Status.REJECTED, f"status={prod_rej_ur.status}")

    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_rej_cr.id}/reject/", {"reason": "Rejection from CHANGES_REQUESTED"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductRejectView.as_view()(req, pk=prod_rej_cr.id)
    prod_rej_cr.refresh_from_db()
    test("Reject CHANGES_REQUESTED product -> 200 OK and status becomes REJECTED", resp.status_code == status.HTTP_200_OK and prod_rej_cr.status == SellerProduct.Status.REJECTED, f"status={prod_rej_cr.status}")

    # 4f. Approving an already APPROVED product -> 409 Conflict (not 500)
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_a1.id}/approve/", format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApproveView.as_view()(req, pk=prod_a1.id)
    test("Approving an already APPROVED product returns 409 (not 500)", resp.status_code == status.HTTP_409_CONFLICT, f"got {resp.status_code}")

    # 4g. Approving a PAUSED product -> 409 Conflict (not 500)
    prod_paused = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Paused Prod", sku="PAUSED-001", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.PAUSED)
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_paused.id}/approve/", format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApproveView.as_view()(req, pk=prod_paused.id)
    test("Approving a PAUSED product returns 409 (not 500)", resp.status_code == status.HTTP_409_CONFLICT, f"got {resp.status_code}")

    # 4h. Reject without reason or with reason < 5 chars -> 400 Bad Request
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_a4.id}/reject/", {"reason": "bad"}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductRejectView.as_view()(req, pk=prod_a4.id)
    test("Reject with reason < 5 chars returns 400", resp.status_code == status.HTTP_400_BAD_REQUEST, f"got {resp.status_code}")

    # 4i. Approve product with ineligible category (e.g. non-leaf category) -> 409 CATEGORY_NOT_ELIGIBLE
    prod_nonleaf = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_root,  # Root category is NOT a leaf!
        title="Invalid Category Product",
        sku="SKU-INV-001",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
        status=SellerProduct.Status.SUBMITTED,
    )
    req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_nonleaf.id}/approve/", format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductApproveView.as_view()(req, pk=prod_nonleaf.id)
    test("Approve product in non-leaf category returns 409 CATEGORY_NOT_ELIGIBLE", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "CATEGORY_NOT_ELIGIBLE", f"got {resp.status_code}, data={resp.data}")

    # ─────────────────────────────────────────────────────────────────────────
    # 5. BULK APPROVE
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 5. BULK APPROVE ---")

    prod_bulk1 = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Bulk Prod 1",
        sku="SKU-BLK-001",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
        status=SellerProduct.Status.SUBMITTED,
    )
    prod_bulk2 = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Bulk Prod 2",
        sku="SKU-BLK-002",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
        status=SellerProduct.Status.SUBMITTED,
    )

    req = factory.post("/api/workforce/admin/seller-hub/approval/products/bulk-approve/", {"product_ids": [prod_bulk1.id, prod_bulk2.id, 999999]}, format="json")
    force_authenticate(req, user=user_admin)
    resp = AdminProductBulkApproveView.as_view()(req)
    test("Bulk approve returns 200 with per-id results list", resp.status_code == status.HTTP_200_OK and "results" in resp.data, f"got {resp.data}")
    results_map = {r["product_id"]: r for r in resp.data["results"]}
    test("Bulk approve succeeded for valid submitted products", results_map.get(prod_bulk1.id, {}).get("status") == "APPROVED" and results_map.get(prod_bulk2.id, {}).get("status") == "APPROVED", f"got {results_map}")
    test("Bulk approve reports not found for non-existent product", results_map.get(999999, {}).get("code") == "NOT_FOUND" and not results_map.get(999999, {}).get("success"), f"got {results_map}")

    # ─────────────────────────────────────────────────────────────────────────
    # 6. RE-APPROVAL SEPARATE FIELD TESTS & INVENTORY GATING
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 6. RE-APPROVAL SEPARATE FIELD TESTS ---")

    # 6a. Editing TITLE of APPROVED product -> SUBMITTED and blocks stock write with 409
    p_title = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Base Title", sku="REAPP-TITLE", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    inv_title, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=p_title, defaults={"on_hand_qty": Decimal("10.000")})
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_title.id}/", {"title": "Changed Title"}, format="json")
    force_authenticate(req, user=user_seller_a)
    SellerProductDetailView.as_view()(req, pk=p_title.id)
    p_title.refresh_from_db()
    test("Editing TITLE of APPROVED product sends it back to SUBMITTED", p_title.status == SellerProduct.Status.SUBMITTED, f"status={p_title.status}")
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_title.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "1.000", "reason": "Test"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_title.id)
    test("Stock write on TITLE-edited product is blocked with 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}")

    # 6b. Editing PRICE of APPROVED product -> SUBMITTED and blocks stock write with 409
    p_price = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Base Price Prod", sku="REAPP-PRICE", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    inv_price, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=p_price, defaults={"on_hand_qty": Decimal("10.000")})
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_price.id}/", {"selling_price": "85.00"}, format="json")
    force_authenticate(req, user=user_seller_a)
    SellerProductDetailView.as_view()(req, pk=p_price.id)
    p_price.refresh_from_db()
    test("Editing PRICE of APPROVED product sends it back to SUBMITTED", p_price.status == SellerProduct.Status.SUBMITTED, f"status={p_price.status}")
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_price.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "1.000", "reason": "Test"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_price.id)
    test("Stock write on PRICE-edited product is blocked with 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}")

    # 6c. Editing DESCRIPTION of APPROVED product -> SUBMITTED and blocks stock write with 409
    p_desc = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Base Desc Prod", description="Initial description", sku="REAPP-DESC", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    inv_desc, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=p_desc, defaults={"on_hand_qty": Decimal("10.000")})
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_desc.id}/", {"description": "Updated new description text"}, format="json")
    force_authenticate(req, user=user_seller_a)
    SellerProductDetailView.as_view()(req, pk=p_desc.id)
    p_desc.refresh_from_db()
    test("Editing DESCRIPTION of APPROVED product sends it back to SUBMITTED", p_desc.status == SellerProduct.Status.SUBMITTED, f"status={p_desc.status}")
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_desc.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "1.000", "reason": "Test"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_desc.id)
    test("Stock write on DESCRIPTION-edited product is blocked with 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}")

    # 6d. Editing IMAGES of APPROVED product -> SUBMITTED and blocks stock write with 409
    p_img = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Base Img Prod", sku="REAPP-IMG", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    SellerProductImage.objects.create(product=p_img, image_url="https://images.unsplash.com/img1", is_primary=True)
    inv_img, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=p_img, defaults={"on_hand_qty": Decimal("10.000")})
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_img.id}/", {"images": ["https://images.unsplash.com/img2"]}, format="json")
    force_authenticate(req, user=user_seller_a)
    SellerProductDetailView.as_view()(req, pk=p_img.id)
    p_img.refresh_from_db()
    test("Editing IMAGES of APPROVED product sends it back to SUBMITTED", p_img.status == SellerProduct.Status.SUBMITTED, f"status={p_img.status}")
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_img.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "1.000", "reason": "Test"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_img.id)
    test("Stock write on IMAGES-edited product is blocked with 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}")

    # 6e. Editing CATEGORY of APPROVED product -> SUBMITTED and blocks stock write with 409
    p_cat = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Base Cat Prod", sku="REAPP-CAT", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    inv_cat, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=p_cat, defaults={"on_hand_qty": Decimal("10.000")})
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_cat.id}/", {"category": cat_leaf2.id}, format="json")
    force_authenticate(req, user=user_seller_a)
    SellerProductDetailView.as_view()(req, pk=p_cat.id)
    p_cat.refresh_from_db()
    test("Editing CATEGORY of APPROVED product sends it back to SUBMITTED", p_cat.status == SellerProduct.Status.SUBMITTED, f"status={p_cat.status}")
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_cat.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "1.000", "reason": "Test"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_cat.id)
    test("Stock write on CATEGORY-edited product is blocked with 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}")

    # 6f. Stock-only adjustment on APPROVED product does NOT change its status
    p_stock = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Stock Only Prod", sku="STOCK-ONLY", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    inv_stock, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=p_stock, defaults={"on_hand_qty": Decimal("10.000")})
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_stock.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "5.000", "reason": "Restocking count"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_stock.id)
    p_stock.refresh_from_db()
    test("Stock-only adjustment on APPROVED product succeeds (200 OK)", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")
    test("Stock-only adjustment does NOT change product status (remains APPROVED)", p_stock.status == SellerProduct.Status.APPROVED, f"status={p_stock.status}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7. RESUBMISSION OF REJECTED PRODUCT
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7. RESUBMISSION OF REJECTED PRODUCT ---")

    prod_resub = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Rejected Prod To Resubmit",
        sku="REJ-RESUB-001",
        mrp=Decimal("100.00"),
        selling_price=Decimal("90.00"),
        status=SellerProduct.Status.REJECTED,
        admin_review_note="Please fix image resolution and details.",
    )
    SellerProductImage.objects.create(
        product=prod_resub,
        image_url="https://images.unsplash.com/photo-1586201375761-83865001e31c",
        is_primary=True,
    )

    test("prod_resub is currently REJECTED with reason", prod_resub.status == SellerProduct.Status.REJECTED and bool(prod_resub.rejection_reason))

    # 7a. Submit endpoint on rejected product
    req = factory.post(f"/api/workforce/seller-hub/products/{prod_resub.id}/submit/", format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerProductSubmitView.as_view()(req, pk=prod_resub.id)
    prod_resub.refresh_from_db()
    test("Submitting rejected product via POST submit/ sets status to SUBMITTED and clears rejection reason", resp.status_code == status.HTTP_200_OK and prod_resub.status == SellerProduct.Status.SUBMITTED and not prod_resub.rejection_reason, f"status={prod_resub.status}, reason={prod_resub.rejection_reason}")

    # 7b. Edit & Resubmit REJECTED product via PATCH (Edit Modal Save)
    p_rej_edit = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Rejected Before Edit",
        sku="REJ-EDIT-001",
        mrp=Decimal("120.00"),
        selling_price=Decimal("100.00"),
        status=SellerProduct.Status.REJECTED,
        admin_review_note="Fix title and price",
    )
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_rej_edit.id}/", {"title": "Fixed Title After Rejection"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerProductDetailView.as_view()(req, pk=p_rej_edit.id)
    p_rej_edit.refresh_from_db()
    test("Edit & Resubmit REJECTED product via PATCH sets status to SUBMITTED and clears rejection reason", resp.status_code == status.HTTP_200_OK and p_rej_edit.status == SellerProduct.Status.SUBMITTED and not p_rej_edit.rejection_reason and not p_rej_edit.admin_review_note, f"status={p_rej_edit.status}, reason={p_rej_edit.rejection_reason}")

    # 7c. Edit & Resubmit CHANGES_REQUESTED product via PATCH (Edit Modal Save)
    p_cr_edit = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Changes Req Prod",
        sku="CR-EDIT-001",
        mrp=Decimal("150.00"),
        selling_price=Decimal("130.00"),
        status=SellerProduct.Status.CHANGES_REQUESTED,
        admin_review_note="Update description clarity",
    )
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_cr_edit.id}/", {"description": "Crystal clear brand new description"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerProductDetailView.as_view()(req, pk=p_cr_edit.id)
    p_cr_edit.refresh_from_db()
    test("Edit & Resubmit CHANGES_REQUESTED product via PATCH sets status to SUBMITTED and clears admin_review_note", resp.status_code == status.HTTP_200_OK and p_cr_edit.status == SellerProduct.Status.SUBMITTED and not p_cr_edit.admin_review_note, f"status={p_cr_edit.status}, note={p_cr_edit.admin_review_note}")

    # 7d. Stock writes on resubmitted products are blocked with 409 until approved
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": p_rej_edit.id, "on_hand_qty": "10.000"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryInitializeView.as_view()(req)
    test("Stock write on resubmitted REJECTED product is blocked with 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}")

    # 7e. A seller cannot edit or resubmit another seller's product
    req = factory.patch(f"/api/workforce/seller-hub/products/{p_rej_edit.id}/", {"title": "Hacked Title"}, format="json")
    force_authenticate(req, user=user_seller_b)
    resp = SellerProductDetailView.as_view()(req, pk=p_rej_edit.id)
    test("Seller B cannot edit/resubmit Seller A's product -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

    req = factory.post(f"/api/workforce/seller-hub/products/{p_rej_edit.id}/submit/", format="json")
    force_authenticate(req, user=user_seller_b)
    resp = SellerProductSubmitView.as_view()(req, pk=p_rej_edit.id)
    test("Seller B cannot submit Seller A's product -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

    # 7f. Admin Category List Serializer returns exact count fields (products_count, children_count, etc.)
    cat_parent_test = SellerHubCategory.objects.create(name="Parent Count Test", slug="parent-count-test", is_active=True, sort_order=90)
    # 3 children under cat_parent_test
    c_child1 = SellerHubCategory.objects.create(name="Child 1", slug="child-1-test", parent=cat_parent_test, is_active=True, sort_order=1)
    c_child2 = SellerHubCategory.objects.create(name="Child 2", slug="child-2-test", parent=cat_parent_test, is_active=True, sort_order=2)
    c_child3 = SellerHubCategory.objects.create(name="Child 3", slug="child-3-test", parent=cat_parent_test, is_active=False, sort_order=3)
    # 2 products directly linked to cat_parent_test (one Seller A, one Seller B, one active, one inactive)
    p_cnt1 = SellerProduct.objects.create(company=company_seller_a, category=cat_parent_test, title="Prod 1 Count", sku="CNT-P1", mrp=Decimal("50"), selling_price=Decimal("40"), status=SellerProduct.Status.APPROVED)
    p_cnt2 = SellerProduct.objects.create(company=company_seller_b, category=cat_parent_test, title="Prod 2 Count", sku="CNT-P2", mrp=Decimal("60"), selling_price=Decimal("50"), status=SellerProduct.Status.DRAFT)

    req = factory.get(f"/api/workforce/seller-hub/categories/?search=Parent+Count+Test")
    force_authenticate(req, user=user_admin)
    resp = AdminCatalogCategoryListView.as_view()(req)

    test("Admin Category List returns 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")
    matched_cat = next((c for c in resp.data if c["id"] == cat_parent_test.id), {})
    test("Admin Category item contains 'products_count' field", "products_count" in matched_cat, f"keys={list(matched_cat.keys())}")
    test("Admin Category item contains 'children_count' field", "children_count" in matched_cat, f"keys={list(matched_cat.keys())}")
    test("Admin Category item contains 'subcategories_count' field", "subcategories_count" in matched_cat, f"keys={list(matched_cat.keys())}")
    test("Admin Category products_count == 2 (counts all products across sellers and statuses)", matched_cat.get("products_count") == 2, f"got {matched_cat.get('products_count')}")
    test("Admin Category children_count == 3 (counts all active and inactive direct subcategories)", matched_cat.get("children_count") == 3, f"got {matched_cat.get('children_count')}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7g. EQUIVALENCE MATRIX TEST (10 Users, DB-Reloaded via User.objects.get)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7g. 10-USER EQUIVALENCE MATRIX (DB-RELOADED) ---")

    matrix_specs = [
        # (label, username, kwargs, expected_is_platform_admin)
        ("superuser", "eq_superuser", {"is_superuser": True, "is_staff": True, "company": None}, True),
        ("company-1 is_staff", "eq_co1_staff", {"is_staff": True, "role": "employee", "company": company_admin}, True),
        ("company-1 role admin", "eq_co1_admin", {"is_staff": False, "role": "admin", "company": company_admin}, True),
        ("company-1 role manager", "eq_co1_manager", {"is_staff": False, "role": "manager", "company": company_admin}, True),
        ("role superadmin", "eq_superadmin_role", {"is_staff": False, "role": "superadmin", "company": company_seller_a}, True),
        ("role platform_admin", "eq_platform_admin_role", {"is_staff": False, "role": "platform_admin", "company": company_seller_a}, True),
        ("company-2 role admin owner of products", "eq_co2_admin", {"is_staff": False, "role": "admin", "company": company_seller_a}, False),
        ("company-2 is_staff technician", "eq_co2_tech", {"is_staff": True, "role": "employee", "company": company_seller_a}, False),
        ("company-2 manager", "eq_co2_manager", {"is_staff": False, "role": "manager", "company": company_seller_a}, False),
        ("a seller user", "eq_seller_user", {"is_staff": False, "role": "seller", "company": company_seller_a}, False),
    ]

    for label, uname, ufields, expected_admin in matrix_specs:
        u_obj = User.objects.create_user(
            username=uname,
            email=f"{uname}@example.com",
            password="password123",
            **ufields
        )
        # Reload directly from database to test pure ORM instance without in-memory cache
        u_db = User.objects.get(id=u_obj.id)
        helper_val = is_platform_admin_user(u_db)
        test(f"Equivalence Matrix [{label}]: helper == {expected_admin}", helper_val == expected_admin, f"got {helper_val}")

        # Login endpoint check
        login_req = factory.post("/api/accounts/login/", {"identifier": uname, "password": "password123"}, format="json")
        login_resp = LoginView.as_view()(login_req)
        login_is_platform = login_resp.data.get("user", {}).get("is_platform_admin") if login_resp.status_code == 200 else None
        test(f"Equivalence Matrix [{label}]: login API is_platform_admin == {expected_admin}", login_is_platform == expected_admin, f"got {login_is_platform}")

        # Endpoint authorization check on approval sellers list
        appr_req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
        force_authenticate(appr_req, user=u_db)
        appr_resp = AdminSellerApprovalListView.as_view()(appr_req)
        expected_status = status.HTTP_200_OK if expected_admin else status.HTTP_403_FORBIDDEN
        test(f"Equivalence Matrix [{label}]: GET approval sellers -> {expected_status}", appr_resp.status_code == expected_status, f"got {appr_resp.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7h. REAL JWT LOGIN AUTHENTICATION (NO force_authenticate)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7h. REAL LOGIN AUTHENTICATION (JWT) ---")

    # Platform Admin real login
    plat_login_req = factory.post("/api/accounts/login/", {"identifier": "eq_co1_admin", "password": "password123"}, format="json")
    plat_login_resp = LoginView.as_view()(plat_login_req)
    test("Platform admin real login succeeds (200 OK)", plat_login_resp.status_code == status.HTTP_200_OK, f"got {plat_login_resp.status_code}")
    plat_token = plat_login_resp.data.get("access_token") or plat_login_resp.data.get("token")

    # Call approval sellers with real JWT
    real_appr_req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/", HTTP_AUTHORIZATION=f"Bearer {plat_token}")
    real_appr_resp = AdminSellerApprovalListView.as_view()(real_appr_req)
    test("Real JWT Platform Admin -> GET approval sellers -> 200 OK", real_appr_resp.status_code == status.HTTP_200_OK, f"got {real_appr_resp.status_code}")

    # Call approve product with real JWT
    real_approve_req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{p_rej_edit.id}/approve/", {"note": "JWT approved"}, format="json", HTTP_AUTHORIZATION=f"Bearer {plat_token}")
    real_approve_resp = AdminProductApproveView.as_view()(real_approve_req, pk=p_rej_edit.id)
    test("Real JWT Platform Admin -> POST approve product -> 200 OK", real_approve_resp.status_code == status.HTTP_200_OK, f"got {real_approve_resp.status_code}")

    # Call create category with real JWT
    real_cat_req = factory.post("/api/workforce/seller-hub/categories/", {"name": "JWT Plat Category"}, format="json", HTTP_AUTHORIZATION=f"Bearer {plat_token}")
    real_cat_resp = AdminCatalogCategoryListView.as_view()(real_cat_req)
    test("Real JWT Platform Admin -> POST create category -> 201 Created", real_cat_resp.status_code == status.HTTP_201_CREATED, f"got {real_cat_resp.status_code}")

    # Seller Company Admin real login
    seller_admin_login_req = factory.post("/api/accounts/login/", {"identifier": "eq_co2_admin", "password": "password123"}, format="json")
    seller_admin_login_resp = LoginView.as_view()(seller_admin_login_req)
    test("Seller company admin real login succeeds (200 OK)", seller_admin_login_resp.status_code == status.HTTP_200_OK, f"got {seller_admin_login_resp.status_code}")
    seller_admin_token = seller_admin_login_resp.data.get("access_token") or seller_admin_login_resp.data.get("token")

    # Seller Company Admin attempts approval sellers with real JWT -> 403
    s_real_appr_req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/", HTTP_AUTHORIZATION=f"Bearer {seller_admin_token}")
    s_real_appr_resp = AdminSellerApprovalListView.as_view()(s_real_appr_req)
    test("Real JWT Seller Company Admin -> GET approval sellers -> 403 Forbidden", s_real_appr_resp.status_code == status.HTTP_403_FORBIDDEN, f"got {s_real_appr_resp.status_code}")

    # Seller Company Admin attempts approve product with real JWT -> 403
    s_real_approve_req = factory.post(f"/api/workforce/admin/seller-hub/approval/products/{p_rej_edit.id}/approve/", {"note": "Unauthorized approve"}, format="json", HTTP_AUTHORIZATION=f"Bearer {seller_admin_token}")
    s_real_approve_resp = AdminProductApproveView.as_view()(s_real_approve_req, pk=p_rej_edit.id)
    test("Real JWT Seller Company Admin -> POST approve product -> 403 Forbidden", s_real_approve_resp.status_code == status.HTTP_403_FORBIDDEN, f"got {s_real_approve_resp.status_code}")

    # Seller Company Admin attempts create category with real JWT -> 403
    s_real_cat_req = factory.post("/api/workforce/seller-hub/categories/", {"name": "Unauthorized Cat"}, format="json", HTTP_AUTHORIZATION=f"Bearer {seller_admin_token}")
    s_real_cat_resp = AdminCatalogCategoryListView.as_view()(s_real_cat_req)
    test("Real JWT Seller Company Admin -> POST create category -> 403 Forbidden", s_real_cat_resp.status_code == status.HTTP_403_FORBIDDEN, f"got {s_real_cat_resp.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7i. SELLER REGRESSION & ISOLATION TESTS
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7i. SELLER REGRESSION & ISOLATION ---")

    # Reload seller user fresh from DB
    u_seller_reloaded = User.objects.get(id=user_seller_a.id)

    # 1. Catalog upload batches list -> 200
    req = factory.get("/api/workforce/seller-hub/products/batches/")
    force_authenticate(req, user=u_seller_reloaded)
    resp_batches = SellerProductBatchListView.as_view()(req)
    test("Seller regression: GET catalog batches list -> 200 OK", resp_batches.status_code == status.HTTP_200_OK, f"got {resp_batches.status_code}")

    # 2. Product create -> 201
    req = factory.post("/api/workforce/seller-hub/products/", {
        "title": "Seller Regression Product",
        "sku": "SKU-REG-001",
        "category": cat_leaf.id,
        "mrp": "199.00",
        "selling_price": "149.00",
        "status": "DRAFT",
    }, format="json")
    force_authenticate(req, user=u_seller_reloaded)
    resp_prod_create = SellerProductListView.as_view()(req)
    test("Seller regression: POST product create -> 201 Created", resp_prod_create.status_code == status.HTTP_201_CREATED, f"got {resp_prod_create.status_code}")
    reg_prod_id = resp_prod_create.data.get("product", {}).get("id") or resp_prod_create.data.get("id")

    # 3. Product edit -> 200
    req = factory.patch(f"/api/workforce/seller-hub/products/{reg_prod_id}/", {"title": "Seller Regression Product Edited"}, format="json")
    force_authenticate(req, user=u_seller_reloaded)
    resp_prod_edit = SellerProductDetailView.as_view()(req, pk=reg_prod_id)
    test("Seller regression: PATCH product edit -> 200 OK", resp_prod_edit.status_code == status.HTTP_200_OK, f"got {resp_prod_edit.status_code}")

    # 4. Submit for review -> 200
    # First attach an image so submission rule passes
    SellerProductImage.objects.create(product_id=reg_prod_id, image_url="https://example.com/reg.jpg", is_primary=True)
    req = factory.post(f"/api/workforce/seller-hub/products/{reg_prod_id}/submit/", format="json")
    force_authenticate(req, user=u_seller_reloaded)
    resp_prod_submit = SellerProductSubmitView.as_view()(req, pk=reg_prod_id)
    test("Seller regression: POST product submit for review -> 200 OK", resp_prod_submit.status_code == status.HTTP_200_OK, f"got {resp_prod_submit.status_code}")

    # 5. Inventory list -> 200
    req = factory.get("/api/workforce/seller-hub/inventory/")
    force_authenticate(req, user=u_seller_reloaded)
    resp_inv_list = SellerInventoryListView.as_view()(req)
    test("Seller regression: GET inventory list -> 200 OK", resp_inv_list.status_code == status.HTTP_200_OK, f"got {resp_inv_list.status_code}")

    # 6. Stock initialize on own approved product -> 201
    prod_reg_appr = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Seller Reg Approved Prod",
        sku="SKU-REG-APPR-01",
        mrp=Decimal("80.00"),
        selling_price=Decimal("70.00"),
        status=SellerProduct.Status.APPROVED,
    )
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": prod_reg_appr.id, "on_hand_qty": "15.000"}, format="json")
    force_authenticate(req, user=u_seller_reloaded)
    resp_inv_init = SellerInventoryInitializeView.as_view()(req)
    test("Seller regression: POST stock initialize on own approved product -> 201 Created", resp_inv_init.status_code == status.HTTP_201_CREATED, f"got {resp_inv_init.status_code}")
    reg_inv_id = resp_inv_init.data.get("inventory", {}).get("id") or resp_inv_init.data.get("id")

    # 7. Stock adjust on own approved product -> 200
    req = factory.post(f"/api/workforce/seller-hub/inventory/{reg_inv_id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "5.000", "reason": "Audit adjustment"}, format="json")
    force_authenticate(req, user=u_seller_reloaded)
    resp_inv_adj = SellerInventoryAdjustView.as_view()(req, pk=reg_inv_id)
    test("Seller regression: POST stock adjust on own approved product -> 200 OK", resp_inv_adj.status_code == status.HTTP_200_OK, f"got {resp_inv_adj.status_code}")

    # 8. Seller gets 403 on every Categories & Categories Approval endpoint
    forbidden_endpoints = [
        ("POST categories create", AdminCatalogCategoryListView.as_view(), factory.post("/api/workforce/seller-hub/categories/", {"name": "Blocked Cat"}, format="json"), {}),
        ("PATCH category edit", AdminCatalogCategoryDetailView.as_view(), factory.patch(f"/api/workforce/seller-hub/categories/{cat_leaf.id}/", {"name": "Blocked Name"}, format="json"), {"pk": cat_leaf.id}),
        ("DELETE category delete", AdminCatalogCategoryDetailView.as_view(), factory.delete(f"/api/workforce/seller-hub/categories/{cat_leaf.id}/"), {"pk": cat_leaf.id}),
        ("GET approval sellers list", AdminSellerApprovalListView.as_view(), factory.get("/api/workforce/admin/seller-hub/approval/sellers/"), {}),
        ("GET approval seller products", AdminSellerProductApprovalListView.as_view(), factory.get(f"/api/workforce/admin/seller-hub/approval/sellers/{company_seller_a.id}/products/"), {"seller_id": company_seller_a.id}),
        ("GET approval product detail", AdminProductApprovalDetailView.as_view(), factory.get(f"/api/workforce/admin/seller-hub/approval/products/{prod_reg_appr.id}/"), {"pk": prod_reg_appr.id}),
        ("POST approval product approve", AdminProductApproveView.as_view(), factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_reg_appr.id}/approve/", format="json"), {"pk": prod_reg_appr.id}),
        ("POST approval product reject", AdminProductRejectView.as_view(), factory.post(f"/api/workforce/admin/seller-hub/approval/products/{prod_reg_appr.id}/reject/", {"reason": "Not allowed"}, format="json"), {"pk": prod_reg_appr.id}),
        ("POST approval bulk approve", AdminProductBulkApproveView.as_view(), factory.post("/api/workforce/admin/seller-hub/approval/products/bulk-approve/", {"product_ids": [prod_reg_appr.id]}, format="json"), {}),
    ]

    for name, view_fn, req_obj, kwargs in forbidden_endpoints:
        force_authenticate(req_obj, user=u_seller_reloaded)
        res = view_fn(req_obj, **kwargs)
        test(f"Seller regression: {name} -> 403 Forbidden", res.status_code == status.HTTP_403_FORBIDDEN, f"got {res.status_code}")

    # 9. Cross-seller isolation: Seller A cannot see or edit Seller B's product
    req = factory.get(f"/api/workforce/seller-hub/products/{prod_b1.id}/")
    force_authenticate(req, user=u_seller_reloaded)
    resp_iso = SellerProductDetailView.as_view()(req, pk=prod_b1.id)
    test("Seller regression cross-isolation: Seller A GET Seller B product -> 404 Not Found", resp_iso.status_code == status.HTTP_404_NOT_FOUND, f"got {resp_iso.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7j. COMPANY-2 ROLE="ADMIN" (IS_STAFF=FALSE) TENANT ISOLATION & SELLER REGRESSION
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7j. COMPANY-2 ROLE='ADMIN' (IS_STAFF=FALSE) TENANT ISOLATION & SELLER REGRESSION ---")

    # Reload company-2 role="admin" user fresh from DB
    u_co2_admin_reloaded = User.objects.get(username="eq_co2_admin")
    test("Company-2 Admin User is loaded from DB with role='admin', is_staff=False, is_superuser=False",
         u_co2_admin_reloaded.role == "admin" and not u_co2_admin_reloaded.is_staff and not u_co2_admin_reloaded.is_superuser,
         f"role={u_co2_admin_reloaded.role}, is_staff={u_co2_admin_reloaded.is_staff}")

    # (a) GET / PATCH / submit another company's product -> 404 or 403, never 200
    req = factory.get(f"/api/workforce/seller-hub/products/{prod_b1.id}/")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_get_other = SellerProductDetailView.as_view()(req, pk=prod_b1.id)
    test("Company-2 Admin: GET another company's product -> 404 Not Found (never 200)", resp_co2_get_other.status_code == status.HTTP_404_NOT_FOUND, f"got {resp_co2_get_other.status_code}")

    req = factory.patch(f"/api/workforce/seller-hub/products/{prod_b1.id}/", {"title": "Hacked Title"}, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_patch_other = SellerProductDetailView.as_view()(req, pk=prod_b1.id)
    test("Company-2 Admin: PATCH another company's product -> 404 Not Found (never 200)", resp_co2_patch_other.status_code == status.HTTP_404_NOT_FOUND, f"got {resp_co2_patch_other.status_code}")

    req = factory.post(f"/api/workforce/seller-hub/products/{prod_b1.id}/submit/", format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_sub_other = SellerProductSubmitView.as_view()(req, pk=prod_b1.id)
    test("Company-2 Admin: POST submit another company's product -> 404 Not Found (never 200)", resp_co2_sub_other.status_code == status.HTTP_404_NOT_FOUND, f"got {resp_co2_sub_other.status_code}")

    # (b) Inventory list contains only own company's items
    # Create inventory item for company_seller_b to verify isolation
    inv_b, _ = SellerInventory.objects.get_or_create(company=company_seller_b, product=prod_b1, defaults={"on_hand_qty": Decimal("40.000")})
    req = factory.get("/api/workforce/seller-hub/inventory/")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_inv = SellerInventoryListView.as_view()(req)
    test("Company-2 Admin: GET inventory list -> 200 OK", resp_co2_inv.status_code == status.HTTP_200_OK, f"got {resp_co2_inv.status_code}")
    co2_inv_product_ids = [item["product"] for item in resp_co2_inv.data]
    test("Company-2 Admin: Inventory list contains ONLY own company items (excludes Seller B)",
         prod_b1.id not in co2_inv_product_ids,
         f"returned product IDs: {co2_inv_product_ids}")

    # (c) Stock initialise / adjust on another company's product -> 404 or 403 (never 200/201)
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": prod_b1.id, "on_hand_qty": "10.000"}, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_init_other = SellerInventoryInitializeView.as_view()(req)
    test("Company-2 Admin: POST stock initialize on another company's product -> 404 Not Found (never 201)", resp_co2_init_other.status_code == status.HTTP_404_NOT_FOUND, f"got {resp_co2_init_other.status_code}")

    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_b.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "5.000", "reason": "Unauthorized adjust"}, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_adj_other = SellerInventoryAdjustView.as_view()(req, pk=inv_b.id)
    test("Company-2 Admin: POST stock adjust on another company's inventory -> 404 Not Found (never 200)", resp_co2_adj_other.status_code == status.HTTP_404_NOT_FOUND, f"got {resp_co2_adj_other.status_code}")

    # (d) Own-company seller operations for Company-2 Admin persona (200/201 on all operations)
    req = factory.get("/api/workforce/seller-hub/products/batches/")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_batches = SellerProductBatchListView.as_view()(req)
    test("Company-2 Admin: GET catalog batches list -> 200 OK", resp_co2_batches.status_code == status.HTTP_200_OK, f"got {resp_co2_batches.status_code}")

    req = factory.post("/api/workforce/seller-hub/products/", {
        "title": "Company 2 Admin Own Product",
        "sku": "SKU-CO2-ADM-001",
        "category": cat_leaf.id,
        "mrp": "250.00",
        "selling_price": "210.00",
        "status": "DRAFT",
    }, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_create = SellerProductListView.as_view()(req)
    test("Company-2 Admin: POST product create -> 201 Created", resp_co2_create.status_code == status.HTTP_201_CREATED, f"got {resp_co2_create.status_code}")
    co2_prod_id = resp_co2_create.data.get("product", {}).get("id") or resp_co2_create.data.get("id")

    req = factory.patch(f"/api/workforce/seller-hub/products/{co2_prod_id}/", {"title": "Company 2 Admin Own Product Edited"}, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_edit = SellerProductDetailView.as_view()(req, pk=co2_prod_id)
    test("Company-2 Admin: PATCH product edit on own product -> 200 OK", resp_co2_edit.status_code == status.HTTP_200_OK, f"got {resp_co2_edit.status_code}")

    SellerProductImage.objects.create(product_id=co2_prod_id, image_url="https://example.com/co2_adm.jpg", is_primary=True)
    req = factory.post(f"/api/workforce/seller-hub/products/{co2_prod_id}/submit/", format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_submit = SellerProductSubmitView.as_view()(req, pk=co2_prod_id)
    test("Company-2 Admin: POST product submit for review on own product -> 200 OK", resp_co2_submit.status_code == status.HTTP_200_OK, f"got {resp_co2_submit.status_code}")

    prod_co2_appr = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Company 2 Admin Approved Product",
        sku="SKU-CO2-APPR-01",
        mrp=Decimal("120.00"),
        selling_price=Decimal("110.00"),
        status=SellerProduct.Status.APPROVED,
    )
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": prod_co2_appr.id, "on_hand_qty": "30.000"}, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_inv_init = SellerInventoryInitializeView.as_view()(req)
    test("Company-2 Admin: POST stock initialize on own approved product -> 201 Created", resp_co2_inv_init.status_code == status.HTTP_201_CREATED, f"got {resp_co2_inv_init.status_code}")
    co2_inv_id = resp_co2_inv_init.data.get("inventory", {}).get("id") or resp_co2_inv_init.data.get("id")

    req = factory.post(f"/api/workforce/seller-hub/inventory/{co2_inv_id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "10.000", "reason": "Admin restock"}, format="json")
    force_authenticate(req, user=u_co2_admin_reloaded)
    resp_co2_inv_adj = SellerInventoryAdjustView.as_view()(req, pk=co2_inv_id)
    test("Company-2 Admin: POST stock adjust on own approved product -> 200 OK", resp_co2_inv_adj.status_code == status.HTTP_200_OK, f"got {resp_co2_inv_adj.status_code}")

    # Company-2 Admin gets 403 on every Categories & Categories Approval endpoint
    for name, view_fn, req_obj, kwargs in forbidden_endpoints:
        force_authenticate(req_obj, user=u_co2_admin_reloaded)
        res = view_fn(req_obj, **kwargs)
        test(f"Company-2 Admin: {name} -> 403 Forbidden", res.status_code == status.HTTP_403_FORBIDDEN, f"got {res.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7k. COMPANY-LESS USERS TENANT RESTRICTION (STAFF/ADMIN WITHOUT COMPANY)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7k. COMPANY-LESS USERS TENANT RESTRICTION ---")

    u_staff_nocomp = User.objects.create_user(
        username="staff_nocomp_user",
        email="staff_nocomp@test.com",
        password="password123",
        is_staff=True,
        role="employee",
        company=None,
    )
    u_admin_nocomp = User.objects.create_user(
        username="admin_nocomp_user",
        email="admin_nocomp@test.com",
        password="password123",
        is_staff=False,
        role="admin",
        company=None,
    )

    # Reload fresh from DB
    u_staff_nocomp_db = User.objects.get(username="staff_nocomp_user")
    u_admin_nocomp_db = User.objects.get(username="admin_nocomp_user")

    for u_test, u_label in [(u_staff_nocomp_db, "Company-less Staff Employee"), (u_admin_nocomp_db, "Company-less Admin")]:
        # Products list -> 403 Forbidden
        req = factory.get("/api/workforce/seller-hub/products/")
        force_authenticate(req, user=u_test)
        resp = SellerProductListView.as_view()(req)
        test(f"{u_label}: GET products list -> 403 Forbidden", resp.status_code == status.HTTP_403_FORBIDDEN, f"got {resp.status_code}")

        # Product detail -> 404 Not Found
        req = factory.get(f"/api/workforce/seller-hub/products/{prod_co2_appr.id}/")
        force_authenticate(req, user=u_test)
        resp = SellerProductDetailView.as_view()(req, pk=prod_co2_appr.id)
        test(f"{u_label}: GET product detail -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Inventory list -> 403 Forbidden
        req = factory.get("/api/workforce/seller-hub/inventory/")
        force_authenticate(req, user=u_test)
        resp = SellerInventoryListView.as_view()(req)
        test(f"{u_label}: GET inventory list -> 403 Forbidden", resp.status_code == status.HTTP_403_FORBIDDEN, f"got {resp.status_code}")

        # Inventory adjust -> 404/403
        req = factory.post(f"/api/workforce/seller-hub/inventory/{co2_inv_id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "1.000", "reason": "Test"}, format="json")
        force_authenticate(req, user=u_test)
        resp = SellerInventoryAdjustView.as_view()(req, pk=co2_inv_id)
        test(f"{u_label}: POST inventory adjust -> 403 or 404", resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), f"got {resp.status_code}")

        # Order detail -> 403/404
        req = factory.get(f"/api/workforce/seller-hub/orders/1/")
        force_authenticate(req, user=u_test)
        resp = SellerOrderDetailView.as_view()(req, pk=1)
        test(f"{u_label}: GET order detail -> 403 or 404", resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), f"got {resp.status_code}")

        # Returns list -> 403 Forbidden
        req = factory.get("/api/workforce/seller-hub/returns/")
        force_authenticate(req, user=u_test)
        resp = SellerReturnListView.as_view()(req)
        test(f"{u_label}: GET returns list -> 403 Forbidden", resp.status_code == status.HTTP_403_FORBIDDEN, f"got {resp.status_code}")

    # Platform Admin can view all where endpoint intends it
    req = factory.get("/api/workforce/seller-hub/products/")
    force_authenticate(req, user=user_admin)
    resp = SellerProductListView.as_view()(req)
    test("Platform Admin: GET products list -> 200 OK (sees all products)", resp.status_code == status.HTTP_200_OK and len(resp.data) > 0, f"got {resp.status_code}")

    req = factory.get(f"/api/workforce/seller-hub/products/{prod_co2_appr.id}/")
    force_authenticate(req, user=user_admin)
    resp = SellerProductDetailView.as_view()(req, pk=prod_co2_appr.id)
    test("Platform Admin: GET product detail -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

    req = factory.get("/api/workforce/seller-hub/inventory/")
    force_authenticate(req, user=user_admin)
    resp = SellerInventoryListView.as_view()(req)
    test("Platform Admin: GET inventory list -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

    # ─────────────────────────────────────────────────────────────────────────
    # 7l. CROSS-TENANT TESTS FOR ORDERS, RETURNS, CLAIMS, COUPONS
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 7l. CROSS-TENANT TESTS FOR ORDERS, RETURNS, CLAIMS, COUPONS ---")

    # Fixtures for Company A and Company B
    ord_a = SellerOrder.objects.create(
        company=company_seller_a,
        source_order_id="ORD-SRC-A-001",
        order_number="ORD-SEVO-A-001",
        customer_name="Customer A",
        customer_phone="+919999900001",
        delivery_address="123 Street A",
        total_amount=Decimal("500.00"),
        status=SellerOrder.Status.NEW,
    )
    ord_b = SellerOrder.objects.create(
        company=company_seller_b,
        source_order_id="ORD-SRC-B-001",
        order_number="ORD-SEVO-B-001",
        customer_name="Customer B",
        customer_phone="+919999900002",
        delivery_address="456 Street B",
        total_amount=Decimal("750.00"),
        status=SellerOrder.Status.NEW,
    )

    ret_a = SellerReturn.objects.create(
        company=company_seller_a,
        order=ord_a,
        return_number="RET-SEVO-A-001",
        source_return_id="RET-SRC-A-001",
        customer_name="Customer A",
        reason="Defective",
        status=SellerReturn.Status.REQUESTED,
    )
    ret_b = SellerReturn.objects.create(
        company=company_seller_b,
        order=ord_b,
        return_number="RET-SEVO-B-001",
        source_return_id="RET-SRC-B-001",
        customer_name="Customer B",
        reason="Wrong Item",
        status=SellerReturn.Status.REQUESTED,
    )

    clm_a = SellerClaim.objects.create(
        company=company_seller_a,
        order=ord_a,
        claim_number="CLM-2026-A001",
        source_claim_id="CLM-SRC-A-001",
        customer_name="Customer A",
        claim_type="LOST_IN_TRANSIT",
        status=SellerClaim.Status.OPEN,
    )
    clm_b = SellerClaim.objects.create(
        company=company_seller_b,
        order=ord_b,
        claim_number="CLM-2026-B001",
        source_claim_id="CLM-SRC-B-001",
        customer_name="Customer B",
        claim_type="DAMAGED_IN_TRANSIT",
        status=SellerClaim.Status.OPEN,
    )

    coup_a = VendorCoupon.objects.create(
        company=company_seller_a,
        code="SAVE10A",
        discount_type="percent",
        discount_value=Decimal("10.00"),
        is_active=True,
    )
    coup_b = VendorCoupon.objects.create(
        company=company_seller_b,
        code="SAVE20B",
        discount_type="percent",
        discount_value=Decimal("20.00"),
        is_active=True,
    )

    # Test cross-tenant isolation for Company-2 Admin AND Dedicated Seller
    for u_persona, p_label in [(u_co2_admin_reloaded, "Company-2 Admin"), (user_seller_a, "Dedicated Seller A")]:
        # Orders: GET other company's order detail -> 404
        req = factory.get(f"/api/workforce/seller-hub/orders/{ord_b.id}/")
        force_authenticate(req, user=u_persona)
        resp = SellerOrderDetailView.as_view()(req, pk=ord_b.id)
        test(f"{p_label}: GET other company order detail -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Orders: POST transition on other company's order -> 404
        req = factory.post(f"/api/workforce/seller-hub/orders/{ord_b.id}/transition/", {"action": "accept"}, format="json")
        force_authenticate(req, user=u_persona)
        resp = SellerOrderStatusTransitionView.as_view()(req, pk=ord_b.id)
        test(f"{p_label}: POST transition on other company order -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Returns: GET returns list excludes other company's returns
        req = factory.get("/api/workforce/seller-hub/returns/")
        force_authenticate(req, user=u_persona)
        resp = SellerReturnListView.as_view()(req)
        test(f"{p_label}: GET returns list -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")
        ret_ids = [r["id"] for r in resp.data]
        test(f"{p_label}: Returns list contains own return and excludes Company B", ret_a.id in ret_ids and ret_b.id not in ret_ids, f"ret_ids={ret_ids}")

        # Returns: GET other company's return detail -> 404
        req = factory.get(f"/api/workforce/seller-hub/returns/{ret_b.id}/")
        force_authenticate(req, user=u_persona)
        resp = SellerReturnDetailView.as_view()(req, pk=ret_b.id)
        test(f"{p_label}: GET other company return detail -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Claims: GET claims list excludes other company's claims
        req = factory.get("/api/workforce/seller-hub/claims/")
        force_authenticate(req, user=u_persona)
        resp = SellerClaimListView.as_view()(req)
        test(f"{p_label}: GET claims list -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")
        clm_ids = [c["id"] for c in resp.data]
        test(f"{p_label}: Claims list contains own claim and excludes Company B", clm_a.id in clm_ids and clm_b.id not in clm_ids, f"clm_ids={clm_ids}")

        # Claims: GET other company's claim detail -> 404
        req = factory.get(f"/api/workforce/seller-hub/claims/{clm_b.id}/")
        force_authenticate(req, user=u_persona)
        resp = SellerClaimDetailView.as_view()(req, pk=clm_b.id)
        test(f"{p_label}: GET other company claim detail -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Coupons: GET coupons list excludes other company's coupons
        req = factory.get("/api/workforce/seller-hub/coupons/")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponListView.as_view()(req)
        test(f"{p_label}: GET coupons list -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")
        coup_ids = [c["id"] for c in resp.data]
        test(f"{p_label}: Coupons list contains own coupon and excludes Company B", coup_a.id in coup_ids and coup_b.id not in coup_ids, f"coup_ids={coup_ids}")

        # Coupons: GET other company's coupon detail -> 404
        req = factory.get(f"/api/workforce/seller-hub/coupons/{coup_b.id}/")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_b.id)
        test(f"{p_label}: GET other company coupon detail -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Returns: Write transition on other company's return -> 404
        req = factory.post(f"/api/workforce/seller-hub/returns/{ret_b.id}/review/", {"decision": "approve"}, format="json")
        force_authenticate(req, user=u_persona)
        resp = SellerReturnReviewView.as_view()(req, pk=ret_b.id)
        test(f"{p_label}: POST review transition on other company return -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Claims: Write response on other company's claim -> 404
        req = factory.post(f"/api/workforce/seller-hub/claims/{clm_b.id}/respond/", {"seller_response": "Unauthorized response"}, format="json")
        force_authenticate(req, user=u_persona)
        resp = SellerClaimRespondView.as_view()(req, pk=clm_b.id)
        test(f"{p_label}: POST respond transition on other company claim -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Coupons: PATCH on other company's coupon -> 404
        req = factory.patch(f"/api/workforce/seller-hub/coupons/{coup_b.id}/", {"discount_value": "99.00"}, format="json")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_b.id)
        test(f"{p_label}: PATCH on other company coupon -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Coupons: DELETE on other company's coupon -> 404
        req = factory.delete(f"/api/workforce/seller-hub/coupons/{coup_b.id}/")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_b.id)
        test(f"{p_label}: DELETE on other company coupon -> 404 Not Found", resp.status_code == status.HTTP_404_NOT_FOUND, f"got {resp.status_code}")

        # Own-company operations work (200 OK / 201 Created / 200 Deleted)
        req = factory.get(f"/api/workforce/seller-hub/orders/{ord_a.id}/")
        force_authenticate(req, user=u_persona)
        resp = SellerOrderDetailView.as_view()(req, pk=ord_a.id)
        test(f"{p_label}: GET own order detail -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        req = factory.get(f"/api/workforce/seller-hub/returns/{ret_a.id}/")
        force_authenticate(req, user=u_persona)
        resp = SellerReturnDetailView.as_view()(req, pk=ret_a.id)
        test(f"{p_label}: GET own return detail -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        # Own return review write
        ret_own_temp = SellerReturn.objects.create(
            company=company_seller_a,
            order=ord_a,
            return_number=f"RET-TEMP-{uuid.uuid4().hex[:6]}",
            source_return_id=f"RET-SRC-TEMP-{uuid.uuid4().hex[:6]}",
            customer_name="Customer A",
            reason="Damaged item",
            status=SellerReturn.Status.REQUESTED,
        )
        req = factory.post(f"/api/workforce/seller-hub/returns/{ret_own_temp.id}/review/", {"decision": "approve", "seller_notes": "Approved for refund"}, format="json")
        force_authenticate(req, user=u_persona)
        resp = SellerReturnReviewView.as_view()(req, pk=ret_own_temp.id)
        test(f"{p_label}: POST review transition on own return -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        req = factory.get(f"/api/workforce/seller-hub/claims/{clm_a.id}/")
        force_authenticate(req, user=u_persona)
        resp = SellerClaimDetailView.as_view()(req, pk=clm_a.id)
        test(f"{p_label}: GET own claim detail -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        # Own claim respond write
        clm_own_temp = SellerClaim.objects.create(
            company=company_seller_a,
            order=ord_a,
            claim_number=f"CLM-TEMP-{uuid.uuid4().hex[:6]}",
            source_claim_id=f"CLM-SRC-TEMP-{uuid.uuid4().hex[:6]}",
            customer_name="Customer A",
            claim_type="LOST_IN_TRANSIT",
            status=SellerClaim.Status.OPEN,
        )
        req = factory.post(f"/api/workforce/seller-hub/claims/{clm_own_temp.id}/respond/", {"seller_response": "Dispatched with tracking proof."}, format="json")
        force_authenticate(req, user=u_persona)
        resp = SellerClaimRespondView.as_view()(req, pk=clm_own_temp.id)
        test(f"{p_label}: POST respond transition on own claim -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        req = factory.get(f"/api/workforce/seller-hub/coupons/{coup_a.id}/")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_a.id)
        test(f"{p_label}: GET own coupon detail -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        # Own coupon PATCH write
        req = factory.patch(f"/api/workforce/seller-hub/coupons/{coup_a.id}/", {"discount_value": "12.00"}, format="json")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_a.id)
        test(f"{p_label}: PATCH on own coupon -> 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}")

        # Own coupon DELETE write
        coup_del_temp = VendorCoupon.objects.create(
            company=company_seller_a,
            code=f"DEL{uuid.uuid4().hex[:5].upper()}",
            discount_type="flat",
            discount_value=Decimal("50.00"),
            is_active=True,
        )
        req = factory.delete(f"/api/workforce/seller-hub/coupons/{coup_del_temp.id}/")
        force_authenticate(req, user=u_persona)
        resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_del_temp.id)
        test(f"{p_label}: DELETE on own coupon -> 200 OK", resp.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT), f"got {resp.status_code}")

    # Company-less non-platform staff user write restrictions
    req = factory.post(f"/api/workforce/seller-hub/returns/{ret_a.id}/review/", {"decision": "approve"}, format="json")
    force_authenticate(req, user=u_staff_nocomp)
    resp = SellerReturnReviewView.as_view()(req, pk=ret_a.id)
    test("Company-less Staff Employee: POST review on return -> 403 Forbidden", resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), f"got {resp.status_code}")

    req = factory.post(f"/api/workforce/seller-hub/claims/{clm_a.id}/respond/", {"seller_response": "Hacked response"}, format="json")
    force_authenticate(req, user=u_staff_nocomp)
    resp = SellerClaimRespondView.as_view()(req, pk=clm_a.id)
    test("Company-less Staff Employee: POST respond on claim -> 404 Not Found", resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), f"got {resp.status_code}")

    req = factory.patch(f"/api/workforce/seller-hub/coupons/{coup_a.id}/", {"discount_value": "99.00"}, format="json")
    force_authenticate(req, user=u_staff_nocomp)
    resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_a.id)
    test("Company-less Staff Employee: PATCH coupon -> 404 Not Found", resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), f"got {resp.status_code}")

    req = factory.delete(f"/api/workforce/seller-hub/coupons/{coup_a.id}/")
    force_authenticate(req, user=u_staff_nocomp)
    resp = AdminSellerCouponDetailView.as_view()(req, pk=coup_a.id)
    test("Company-less Staff Employee: DELETE coupon -> 404 Not Found", resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND), f"got {resp.status_code}")



    # ─────────────────────────────────────────────────────────────────────────
    # 8. INVENTORY GATING (SERVER-SIDE ON ALL STOCK PATHS)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 8. INVENTORY GATING (APPROVED-ONLY) ---")

    # 8a. Inventory List returns ONLY APPROVED products
    prod_gating_appr = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Gating Appr", sku="GT-APPR", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.APPROVED)
    prod_gating_sub = SellerProduct.objects.create(company=company_seller_a, category=cat_leaf, title="Gating Sub", sku="GT-SUB", mrp=Decimal("100"), selling_price=Decimal("90"), status=SellerProduct.Status.SUBMITTED)
    inv_ga, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=prod_gating_appr, defaults={"on_hand_qty": Decimal("50.000")})
    inv_gs, _ = SellerInventory.objects.get_or_create(company=company_seller_a, product=prod_gating_sub, defaults={"on_hand_qty": Decimal("10.000")})

    req = factory.get("/api/workforce/seller-hub/inventory/")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryListView.as_view()(req)
    inv_returned_prods = [i["product"] for i in resp.data]
    test("Inventory list returns APPROVED product", prod_gating_appr.id in inv_returned_prods, f"returned {inv_returned_prods}")
    test("Inventory list EXCLUDES non-approved product", prod_gating_sub.id not in inv_returned_prods, f"returned {inv_returned_prods}")

    # 8b. SellerInventoryInitializeView on DRAFT product -> 409 Conflict PRODUCT_NOT_APPROVED
    prod_draft = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Draft Product",
        sku="SKU-DFT-001",
        mrp=Decimal("50.00"),
        selling_price=Decimal("45.00"),
        status=SellerProduct.Status.DRAFT,
    )
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": prod_draft.id, "on_hand_qty": "20.000"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryInitializeView.as_view()(req)
    test("Initialize stock on DRAFT product returns 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}, data={resp.data}")

    # 8c. SellerInventoryInitializeView on SUBMITTED product -> 409 Conflict PRODUCT_NOT_APPROVED
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": prod_gating_sub.id, "on_hand_qty": "20.000"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryInitializeView.as_view()(req)
    test("Initialize stock on SUBMITTED product returns 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}, data={resp.data}")

    # 8d. SellerInventoryInitializeView on APPROVED product -> 201 Created
    prod_init_appr = SellerProduct.objects.create(
        company=company_seller_a,
        category=cat_leaf,
        title="Approved Uninitialized Prod",
        sku="SKU-UNINIT-001",
        mrp=Decimal("50.00"),
        selling_price=Decimal("45.00"),
        status=SellerProduct.Status.APPROVED,
    )
    req = factory.post("/api/workforce/seller-hub/inventory/initialize/", {"product_id": prod_init_appr.id, "on_hand_qty": "25.000"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryInitializeView.as_view()(req)
    test("Initialize stock on APPROVED product succeeds with 201 Created", resp.status_code == status.HTTP_201_CREATED, f"got {resp.status_code}, data={resp.data}")

    # 8e. SellerInventoryAdjustView on non-approved product -> 409 Conflict PRODUCT_NOT_APPROVED
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_gs.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "5.000", "reason": "Stock count adjustment"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_gs.id)
    test("Adjust stock on non-approved product returns 409 PRODUCT_NOT_APPROVED", resp.status_code == status.HTTP_409_CONFLICT and resp.data.get("code") == "PRODUCT_NOT_APPROVED", f"got {resp.status_code}, data={resp.data}")

    # 8f. SellerInventoryAdjustView on approved product -> 200 OK
    req = factory.post(f"/api/workforce/seller-hub/inventory/{inv_ga.id}/adjust/", {"movement_type": "ADJUSTMENT_INCREASE", "quantity": "5.000", "reason": "Physical count adjustment"}, format="json")
    force_authenticate(req, user=user_seller_a)
    resp = SellerInventoryAdjustView.as_view()(req, pk=inv_ga.id)
    test("Adjust stock on APPROVED product succeeds with 200 OK", resp.status_code == status.HTTP_200_OK, f"got {resp.status_code}, data={resp.data}")

    # ─────────────────────────────────────────────────────────────────────────
    # 9. BOUNDED QUERY PERFORMANCE TEST
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 9. BOUNDED QUERY COUNT PERFORMANCE ---")

    # Create 30 sellers and 300 products to test query scaling
    perf_sellers = []
    for i in range(30):
        c = Company.objects.create(company_name=f"Perf Seller {i:02d}", business_type="grocery_supplier", is_active=True)
        perf_sellers.append(c)
        # Create 10 products per seller
        for j in range(10):
            st = SellerProduct.Status.SUBMITTED if j < 4 else (SellerProduct.Status.APPROVED if j < 8 else SellerProduct.Status.REJECTED)
            SellerProduct.objects.create(
                company=c,
                category=cat_leaf,
                title=f"Perf Prod S{i} P{j}",
                sku=f"PERF-S{i}-P{j}",
                mrp=Decimal("100.00"),
                selling_price=Decimal("90.00"),
                status=st,
            )

    reset_queries()
    req = factory.get("/api/workforce/admin/seller-hub/approval/sellers/")
    force_authenticate(req, user=user_admin)
    with connection.cursor() as cursor:
        resp = AdminSellerApprovalListView.as_view()(req)
    
    query_count = len(connection.queries)
    test(f"Seller List aggregation executes in bounded SQL queries (measured {query_count} queries for 32 sellers and 300+ products)", query_count <= 4, f"queries={query_count}")

    # ─────────────────────────────────────────────────────────────────────────
    # 10. CATEGORY CREATION & SELLER PICKER VISIBILITY (CASES A-E)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- 10. CATEGORY CREATION & SELLER PICKER VISIBILITY (CASES A-E) ---")

    def _extract_cat_id(resp):
        if "category" in resp.data and isinstance(resp.data["category"], dict):
            return resp.data["category"].get("id")
        return resp.data.get("id")

    # Case a: A new ROOT category, active, no children
    req_a = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "Organic Pantry Roots",
        "slug": "organic-pantry-roots",
        "is_active": True,
        "parent": None,
        "sort_order": 50,
    }, format="json")
    force_authenticate(req_a, user=user_admin)
    resp_a = AdminSellerHubCategoryListView.as_view()(req_a)
    cat_a_id = _extract_cat_id(resp_a)
    test("Case a: Platform Admin POST new root active category -> 201 Created", resp_a.status_code == status.HTTP_201_CREATED and cat_a_id is not None, f"status={resp_a.status_code}")

    for u_persona, p_label in [(user_seller_a, "Dedicated Seller A"), (u_co2_admin_reloaded, "Company-2 Admin")]:
        req_pick = factory.get("/api/workforce/seller-hub/catalog/categories/?parent_id=null")
        force_authenticate(req_pick, user=u_persona)
        resp_pick = SellerCatalogCategoryListView.as_view()(req_pick)
        item_a = next((c for c in resp_pick.data if c["id"] == cat_a_id), None)
        test(f"Case a ({p_label}): New root category appears in picker with is_leaf=True", item_a is not None and item_a.get("is_leaf") is True and item_a.get("has_children") is False, f"item={item_a}")

    # Case b: A new child under an existing leaf that has no products
    req_b = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "Ancient Grains",
        "slug": "ancient-grains",
        "is_active": True,
        "parent": cat_a_id,
        "sort_order": 1,
    }, format="json")
    force_authenticate(req_b, user=user_admin)
    resp_b = AdminSellerHubCategoryListView.as_view()(req_b)
    cat_b_id = _extract_cat_id(resp_b)
    test("Case b: Platform Admin POST child under empty root -> 201 Created", resp_b.status_code == status.HTTP_201_CREATED and cat_b_id is not None, f"status={resp_b.status_code}")

    for u_persona, p_label in [(user_seller_a, "Dedicated Seller A"), (u_co2_admin_reloaded, "Company-2 Admin")]:
        req_pick_root = factory.get("/api/workforce/seller-hub/catalog/categories/?parent_id=null")
        force_authenticate(req_pick_root, user=u_persona)
        resp_pick_root = SellerCatalogCategoryListView.as_view()(req_pick_root)
        item_root = next((c for c in resp_pick_root.data if c["id"] == cat_a_id), None)
        test(f"Case b ({p_label}): Parent root now reports has_children=True and is_leaf=False", item_root is not None and item_root.get("has_children") is True and item_root.get("is_leaf") is False, f"item={item_root}")

        req_pick_child = factory.get(f"/api/workforce/seller-hub/catalog/categories/?parent_id={cat_a_id}")
        force_authenticate(req_pick_child, user=u_persona)
        resp_pick_child = SellerCatalogCategoryListView.as_view()(req_pick_child)
        item_b = next((c for c in resp_pick_child.data if c["id"] == cat_b_id), None)
        test(f"Case b ({p_label}): Child appears in parent column with is_leaf=True", item_b is not None and item_b.get("is_leaf") is True, f"item={item_b}")

    # Case c: A new child under a parent that already has children
    req_c = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "Millets & Quinoa",
        "slug": "millets-quinoa",
        "is_active": True,
        "parent": cat_a_id,
        "sort_order": 2,
    }, format="json")
    force_authenticate(req_c, user=user_admin)
    resp_c = AdminSellerHubCategoryListView.as_view()(req_c)
    cat_c_id = _extract_cat_id(resp_c)
    test("Case c: Platform Admin POST second child under parent -> 201 Created", resp_c.status_code == status.HTTP_201_CREATED and cat_c_id is not None, f"status={resp_c.status_code}")

    for u_persona, p_label in [(user_seller_a, "Dedicated Seller A"), (u_co2_admin_reloaded, "Company-2 Admin")]:
        req_pick_child = factory.get(f"/api/workforce/seller-hub/catalog/categories/?parent_id={cat_a_id}")
        force_authenticate(req_pick_child, user=u_persona)
        resp_pick_child = SellerCatalogCategoryListView.as_view()(req_pick_child)
        child_ids = [c["id"] for c in resp_pick_child.data]
        test(f"Case c ({p_label}): Both sibling children appear in column", cat_b_id in child_ids and cat_c_id in child_ids, f"child_ids={child_ids}")

    # Case d: A new category created inactive; and a child under an inactive parent
    req_d_root = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "Inactive Seasonal Department",
        "slug": "inactive-seasonal-dept",
        "is_active": False,
        "parent": None,
        "sort_order": 99,
    }, format="json")
    force_authenticate(req_d_root, user=user_admin)
    resp_d_root = AdminSellerHubCategoryListView.as_view()(req_d_root)
    cat_d_root_id = _extract_cat_id(resp_d_root)

    req_d_child = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "Diwali Gift Hampers",
        "slug": "diwali-gift-hampers",
        "is_active": True,
        "parent": cat_d_root_id,
        "sort_order": 1,
    }, format="json")
    force_authenticate(req_d_child, user=user_admin)
    resp_d_child = AdminSellerHubCategoryListView.as_view()(req_d_child)
    cat_d_child_id = _extract_cat_id(resp_d_child)
    test("Case d: Platform Admin creates inactive root and active child under it -> 201 Created", resp_d_root.status_code == status.HTTP_201_CREATED and resp_d_child.status_code == status.HTTP_201_CREATED, f"root={resp_d_root.status_code}, child={resp_d_child.status_code}")

    for u_persona, p_label in [(user_seller_a, "Dedicated Seller A"), (u_co2_admin_reloaded, "Company-2 Admin")]:
        req_pick_root = factory.get("/api/workforce/seller-hub/catalog/categories/?parent_id=null")
        force_authenticate(req_pick_root, user=u_persona)
        resp_pick_root = SellerCatalogCategoryListView.as_view()(req_pick_root)
        root_ids = [c["id"] for c in resp_pick_root.data]
        test(f"Case d ({p_label}): Inactive root is hidden from seller roots", cat_d_root_id not in root_ids, f"root_ids={root_ids}")

        req_pick_child = factory.get(f"/api/workforce/seller-hub/catalog/categories/?parent_id={cat_d_root_id}")
        force_authenticate(req_pick_child, user=u_persona)
        resp_pick_child = SellerCatalogCategoryListView.as_view()(req_pick_child)
        child_ids = [c["id"] for c in resp_pick_child.data]
        test(f"Case d ({p_label}): Active child under inactive parent is omitted by active chain rule", cat_d_child_id not in child_ids, f"child_ids={child_ids}")

    # Case e: A new category created with Admin form default values
    req_e = factory.post("/api/workforce/seller-hub/categories/", {
        "name": "Beverages & Cold Brews",
        "slug": "beverages-cold-brews",
        "description": "",
        "icon": "Store",
        "parent": None,
        "sort_order": 1,
        "is_active": True,
    }, format="json")
    force_authenticate(req_e, user=user_admin)
    resp_e = AdminSellerHubCategoryListView.as_view()(req_e)
    cat_e_id = _extract_cat_id(resp_e)
    test("Case e: Category created with default Admin form values -> 201 Created", resp_e.status_code == status.HTTP_201_CREATED and cat_e_id is not None, f"status={resp_e.status_code}")

    for u_persona, p_label in [(user_seller_a, "Dedicated Seller A"), (u_co2_admin_reloaded, "Company-2 Admin")]:
        req_pick_e = factory.get("/api/workforce/seller-hub/catalog/categories/?parent_id=null")
        force_authenticate(req_pick_e, user=u_persona)
        resp_pick_e = SellerCatalogCategoryListView.as_view()(req_pick_e)
        item_e = next((c for c in resp_pick_e.data if c["id"] == cat_e_id), None)
        test(f"Case e ({p_label}): Category created with default form values appears in seller picker", item_e is not None and item_e.get("is_leaf") is True, f"item={item_e}")

    print("\n" + "=" * 80)
    print(f"PHASE 11 RESULTS: {passed_count}/{test_count} tests PASSED.")
    print("=" * 80 + "\n")

    if passed_count == test_count:
        return True
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
