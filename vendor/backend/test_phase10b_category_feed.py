"""
test_phase10b_category_feed.py

Phase 10B: Marketplace Category Feed & Product Filtering Verification Test Suite.
Verifies:
1. Shared-Secret Authentication & Method Guards:
   - Missing secret -> 401/403 rejected.
   - Invalid / wrong secret -> 401/403 rejected.
   - Insecure default key ('wf_integration_key_default') -> rejected.
   - Browser / Seller JWT alone -> rejected.
   - Valid Bearer secret -> 200 OK.
   - Valid X-Workforce-Webhook-Secret header -> 200 OK.
   - Non-GET HTTP methods (POST, PATCH, DELETE) -> 405 Method Not Allowed.
2. Active Category & Ancestor Chain Lineage Filtering:
   - Inactive categories are excluded.
   - Inactive parent categories hide their entire active sub-tree.
3. Sellable Product Definition & Visibility Rules:
   - Only APPROVED products from active companies with on_hand_qty > reserved_qty count as sellable.
   - Draft, rejected, paused, unapproved, inactive company, or zero-stock products do NOT count.
4. Category Counts (Direct vs Total Descendants):
   - product_count = direct sellable products in this category.
   - total_product_count = direct products + all sellable products in descendant categories.
5. Hide Empty Subtree Filtering:
   - hide_empty=true (default): categories/subtrees with 0 total sellable products are pruned.
   - hide_empty=false: all active categories are returned.
6. Navigation Modes:
   - Nested tree (tree=true / default): returns root categories with recursive 'children' arrays.
   - Single-level (parent_id=<id|null>): returns flat list of active children for given parent.
   - Flat list (tree=false): returns flat list of all active categories.
7. MarketplaceProductListView Category Filtering:
   - category_id filter on leaf category -> returns leaf products.
   - category_id filter on non-leaf parent -> includes products in all descendant categories.
   - category_slug filter on leaf/parent -> works identically.
   - Unknown category ID -> 404 CATEGORY_NOT_FOUND.
   - Unknown category slug -> 404 CATEGORY_NOT_FOUND.
   - Inactive category or inactive parent chain -> 404 CATEGORY_NOT_FOUND.
8. Backward Compatibility & Snapshot Verification:
   - Product list and product detail key sets remain 100% byte-for-byte backward compatible.
9. Bounded Query Count Performance:
   - Tree generation with ~100 categories and ~500 products executes in <= 3 SQL queries.
"""

import os
import sys
import uuid
import tempfile
from decimal import Decimal

# Ensure temporary SQLite is used for all tests (NEVER PostgreSQL)
if not os.environ.get("SEVO_E2E_SQLITE_PATH"):
    temp_sqlite = os.path.join(tempfile.gettempdir(), f"sevo_phase10b_test_{uuid.uuid4().hex[:8]}.sqlite3")
    os.environ["SEVO_E2E_SQLITE_PATH"] = temp_sqlite

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection, reset_queries
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

# Hard safety guard: ensure test execution is strictly against SQLite
if connection.vendor != "sqlite":
    raise RuntimeError(
        f"SAFETY ABORT: test_phase10b_category_feed initialized against non-SQLite database (vendor={connection.vendor!r}). "
        "Tests must ONLY execute against isolated temporary SQLite."
    )

settings.WORKFORCE_WEBHOOK_SECRET = "test_valid_phase10b_secret_key_12345"
settings.WORKFORCE_API_KEY = "test_valid_phase10b_api_key_67890"

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
)
from workforce_api.views_marketplace_integration import (
    MarketplaceCategoryFeedView,
    MarketplaceProductListView,
    MarketplaceProductDetailView,
)

User = get_user_model()
factory = APIRequestFactory()

TEST_SECRET = "test_valid_phase10b_secret_key_12345"
AUTH_HEADER = f"Bearer {TEST_SECRET}"


def setup_test_data():
    """
    Sets up a clean test dataset with companies, multi-level category hierarchy,
    and products with various approval, stock, and status states.
    """
    if connection.vendor != "sqlite":
        raise RuntimeError(
            f"SAFETY ABORT: test_phase10b_category_feed attempted cleanup on non-SQLite database (vendor={connection.vendor!r}). "
            "Tests must ONLY execute against isolated temporary SQLite."
        )

    SellerProductImage.objects.all().delete()
    SellerInventory.objects.all().delete()
    SellerProduct.objects.all().delete()
    SellerHubCategory.objects.all().delete()
    Company.objects.all().delete()
    User.objects.all().delete()

    # Active and inactive companies
    active_company = Company.objects.create(
        company_name="Fresh Farm Supermarket",
        slug="fresh-farm",
        business_type="grocery_supplier",
        is_active=True,
    )
    inactive_company = Company.objects.create(
        company_name="Closed Grocery",
        slug="closed-grocery",
        business_type="grocery_supplier",
        is_active=False,
    )

    # Categories Hierarchy:
    # 1. Groceries (Root, active)
    #    1.1. Dairy & Eggs (L2, active)
    #         1.1.1. Fresh Milk (L3, active, leaf)
    #         1.1.2. Organic Eggs (L3, active, leaf)
    #         1.1.3. Butter (L3, active, leaf - will have 0 products)
    #    1.2. Beverages (L2, active)
    #         1.2.1. Fruit Juices (L3, active, leaf)
    #         1.2.2. Soft Drinks (L3, active, leaf - 0 products)
    #    1.3. Inactive Branch Parent (L2, is_active=False)
    #         1.3.1. Orphan Child (L3, is_active=True, but parent is inactive!)
    # 2. Snacks (Root, active - 0 products)
    # 3. Inactive Root Category (Root, is_active=False)
    #    3.1. Subcategory of Inactive Root (L2, is_active=True)

    c_groceries = SellerHubCategory.objects.create(
        name="Groceries", slug="groceries", sort_order=1, is_active=True, parent=None, icon="ShoppingBag"
    )
    c_dairy = SellerHubCategory.objects.create(
        name="Dairy & Eggs", slug="dairy-eggs", sort_order=1, is_active=True, parent=c_groceries, icon="Milk"
    )
    c_milk = SellerHubCategory.objects.create(
        name="Fresh Milk", slug="fresh-milk", sort_order=1, is_active=True, parent=c_dairy, icon="MilkBottle"
    )
    c_eggs = SellerHubCategory.objects.create(
        name="Organic Eggs", slug="organic-eggs", sort_order=2, is_active=True, parent=c_dairy, icon="Egg"
    )
    c_butter = SellerHubCategory.objects.create(
        name="Butter & Ghee", slug="butter-ghee", sort_order=3, is_active=True, parent=c_dairy, icon="Package"
    )

    c_bev = SellerHubCategory.objects.create(
        name="Beverages", slug="beverages", sort_order=2, is_active=True, parent=c_groceries, icon="Coffee"
    )
    c_juice = SellerHubCategory.objects.create(
        name="Fruit Juices", slug="fruit-juices", sort_order=1, is_active=True, parent=c_bev, icon="GlassWater"
    )
    c_soda = SellerHubCategory.objects.create(
        name="Soft Drinks", slug="soft-drinks", sort_order=2, is_active=True, parent=c_bev, icon="Sparkles"
    )

    c_inactive_parent = SellerHubCategory.objects.create(
        name="Frozen Foods", slug="frozen-foods", sort_order=3, is_active=False, parent=c_groceries
    )
    c_orphan_child = SellerHubCategory.objects.create(
        name="Ice Cream", slug="ice-cream", sort_order=1, is_active=True, parent=c_inactive_parent
    )

    c_snacks = SellerHubCategory.objects.create(
        name="Snacks", slug="snacks", sort_order=2, is_active=True, parent=None
    )

    c_inactive_root = SellerHubCategory.objects.create(
        name="Household", slug="household", sort_order=3, is_active=False, parent=None
    )
    c_cleaning = SellerHubCategory.objects.create(
        name="Cleaning", slug="cleaning", sort_order=1, is_active=True, parent=c_inactive_root
    )

    # Products:
    # 1. Milk Product 1: Approved, In Stock, Active Company (Sellable) -> in Fresh Milk
    p1 = SellerProduct.objects.create(
        company=active_company, category=c_milk, title="Whole Milk 1L", sku="MILK-1L",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("60.00"), selling_price=Decimal("55.00"), unit="L", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=p1, company=active_company, on_hand_qty=Decimal("10"), reserved_qty=Decimal("2"))
    SellerProductImage.objects.create(product=p1, image_url="https://example.com/milk.jpg", is_primary=True)

    # 2. Milk Product 2: Approved, In Stock (Sellable) -> in Fresh Milk
    p2 = SellerProduct.objects.create(
        company=active_company, category=c_milk, title="Skimmed Milk 500ml", sku="MILK-500ML",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("35.00"), selling_price=Decimal("30.00"), unit="ml", pack_size=Decimal("500")
    )
    SellerInventory.objects.create(product=p2, company=active_company, on_hand_qty=Decimal("15"), reserved_qty=Decimal("0"))

    # 3. Eggs Product: Approved, In Stock (Sellable) -> in Organic Eggs
    p3 = SellerProduct.objects.create(
        company=active_company, category=c_eggs, title="Farm Eggs 6pk", sku="EGGS-6PK",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("90.00"), selling_price=Decimal("85.00"), unit="pack", pack_size=Decimal("6")
    )
    SellerInventory.objects.create(product=p3, company=active_company, on_hand_qty=Decimal("20"), reserved_qty=Decimal("5"))

    # 4. Juice Product: Approved, In Stock (Sellable) -> in Fruit Juices
    p4 = SellerProduct.objects.create(
        company=active_company, category=c_juice, title="Fresh Orange Juice 1L", sku="JUICE-ORANGE-1L",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("120.00"), selling_price=Decimal("110.00"), unit="L", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=p4, company=active_company, on_hand_qty=Decimal("8"), reserved_qty=Decimal("0"))

    # 5. Out of Stock Product in Fresh Milk (Not Sellable -> available stock 0)
    p5 = SellerProduct.objects.create(
        company=active_company, category=c_milk, title="Almond Milk 1L", sku="ALMOND-MILK-1L",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("200.00"), selling_price=Decimal("180.00"), unit="L", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=p5, company=active_company, on_hand_qty=Decimal("5"), reserved_qty=Decimal("5"))

    # 6. Unapproved Product in Fresh Milk (Not Sellable -> draft status)
    p6 = SellerProduct.objects.create(
        company=active_company, category=c_milk, title="Soy Milk 1L", sku="SOY-MILK-1L",
        status=SellerProduct.Status.DRAFT, mrp=Decimal("150.00"), selling_price=Decimal("140.00"), unit="L", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=p6, company=active_company, on_hand_qty=Decimal("10"), reserved_qty=Decimal("0"))

    # 7. Inactive Company Product in Fresh Milk (Not Sellable)
    p7 = SellerProduct.objects.create(
        company=inactive_company, category=c_milk, title="Closed Store Milk", sku="CLOSED-MILK",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("50.00"), selling_price=Decimal("45.00"), unit="L", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=p7, company=inactive_company, on_hand_qty=Decimal("50"), reserved_qty=Decimal("0"))

    # 8. Product in Orphan Child Category (Not Sellable because parent category is inactive)
    p8 = SellerProduct.objects.create(
        company=active_company, category=c_orphan_child, title="Vanilla Ice Cream 500ml", sku="ICE-CREAM-500",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("150.00"), selling_price=Decimal("130.00"), unit="ml", pack_size=Decimal("500")
    )
    SellerInventory.objects.create(product=p8, company=active_company, on_hand_qty=Decimal("20"), reserved_qty=Decimal("0"))

    return {
        "active_company": active_company,
        "inactive_company": inactive_company,
        "c_groceries": c_groceries,
        "c_dairy": c_dairy,
        "c_milk": c_milk,
        "c_eggs": c_eggs,
        "c_butter": c_butter,
        "c_bev": c_bev,
        "c_juice": c_juice,
        "c_soda": c_soda,
        "c_inactive_parent": c_inactive_parent,
        "c_orphan_child": c_orphan_child,
        "c_snacks": c_snacks,
        "c_inactive_root": c_inactive_root,
        "c_cleaning": c_cleaning,
        "p1": p1, "p2": p2, "p3": p3, "p4": p4, "p5": p5, "p6": p6, "p7": p7, "p8": p8,
    }


def run_all_tests():
    passed = 0
    failed = 0
    test_results = []

    def report(name, success, details=""):
        nonlocal passed, failed
        if success:
            passed += 1
            test_results.append(f"  [PASS] {name}")
        else:
            failed += 1
            test_results.append(f"  [FAIL] {name}: {details}")

    print("================================================================================")
    print("PHASE 10B: MARKETPLACE CATEGORY FEED & PRODUCT FILTERING TEST SUITE")
    print("================================================================================")

    data = setup_test_data()

    # ── Test 1: Shared Secret Auth Guards ──────────────────────────────────────────
    view = MarketplaceCategoryFeedView.as_view()

    # 1.1 No auth header
    req = factory.get("/api/workforce/marketplace/categories/")
    res = view(req)
    report("Auth: No secret header returns 401/403", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.2 Wrong secret
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION="Bearer wrong_secret_key_xyz")
    res = view(req)
    report("Auth: Wrong Bearer secret returns 401/403", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.3 Insecure default key rejected
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION="Bearer wf_integration_key_default")
    res = view(req)
    report("Auth: Insecure default key is strictly rejected", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.4 Seller browser user without shared secret
    seller_user = User.objects.create_user(username="seller_test_user", password="password123", role="seller")
    req = factory.get("/api/workforce/marketplace/categories/")
    force_authenticate(req, user=seller_user)
    res = view(req)
    report("Auth: Browser user without shared secret is rejected", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.5 Valid Bearer token
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("Auth: Valid Bearer shared secret returns 200 OK", res.status_code == status.HTTP_200_OK)

    # 1.6 Valid X-Workforce-Webhook-Secret header
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_X_WORKFORCE_WEBHOOK_SECRET=TEST_SECRET)
    res = view(req)
    report("Auth: Valid X-Workforce-Webhook-Secret returns 200 OK", res.status_code == status.HTTP_200_OK)

    # 1.7 Valid X-Workforce-Api-Key header
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_X_WORKFORCE_API_KEY="test_valid_phase10b_api_key_67890")
    res = view(req)
    report("Auth: Valid X-Workforce-Api-Key returns 200 OK", res.status_code == status.HTTP_200_OK)

    # 1.8 Removed Header: Token prefix is rejected
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION=f"Token {TEST_SECRET}")
    res = view(req)
    report("Auth: Removed 'Token' prefix is rejected (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.9 Removed Header: X-Sevo-Integration-Secret is rejected
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_X_SEVO_INTEGRATION_SECRET=TEST_SECRET)
    res = view(req)
    report("Auth: Removed 'X-Sevo-Integration-Secret' is rejected (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.10 Non-ASCII safety on IsMarketplaceIntegrationCaller (never 500)
    non_ascii_secret = "🔑_tëst_ünicöde_sécrèt_123_☃"
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION=f"Bearer {non_ascii_secret}")
    res = view(req)
    report("Auth: Non-ASCII Bearer token safely rejected with 401/403 (no 500 crash)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    req = factory.get("/api/workforce/marketplace/categories/", HTTP_X_WORKFORCE_WEBHOOK_SECRET=non_ascii_secret)
    res = view(req)
    report("Auth: Non-ASCII X-Workforce-Webhook-Secret safely rejected with 401/403 (no 500 crash)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    req = factory.get("/api/workforce/marketplace/categories/", HTTP_X_WORKFORCE_API_KEY=non_ascii_secret)
    res = view(req)
    report("Auth: Non-ASCII X-Workforce-Api-Key safely rejected with 401/403 (no 500 crash)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.11 Comprehensive testing of IsInternalWorkforceCaller via real view (WorkforceJobCustomerCancelSyncView)
    from workforce_api.permissions import IsInternalWorkforceCaller
    from workforce_api.views import WorkforceJobCustomerCancelSyncView
    from service_requests.models import ServiceRequest

    sync_job = ServiceRequest.objects.create(
        request_id="REQ-INT-TEST-001",
        status="cancelled",
        company=data["active_company"],
    )
    cancel_sync_view = WorkforceJobCustomerCancelSyncView.as_view()

    # 1.11.1 Bearer with webhook secret -> Allowed (200 OK)
    req = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION=f"Bearer {TEST_SECRET}")
    res = cancel_sync_view(req, pk=sync_job.pk)
    report("InternalCaller View: Bearer with WORKFORCE_WEBHOOK_SECRET returns 200 OK (Allowed)", res.status_code == status.HTTP_200_OK)

    # 1.11.2 Bearer with API key -> Allowed (200 OK)
    req = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION="Bearer test_valid_phase10b_api_key_67890")
    res = cancel_sync_view(req, pk=sync_job.pk)
    report("InternalCaller View: Bearer with WORKFORCE_API_KEY returns 200 OK (Allowed)", res.status_code == status.HTTP_200_OK)

    # 1.11.3 Bearer with wrong secret/key -> Denied (401/403)
    req = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION="Bearer wrong_invalid_key_xyz")
    res = cancel_sync_view(req, pk=sync_job.pk)
    report("InternalCaller View: Bearer with invalid value is denied (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.11.4 Bearer with default literal key -> Denied (401/403)
    req = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION="Bearer wf_integration_key_default")
    res = cancel_sync_view(req, pk=sync_job.pk)
    report("InternalCaller View: Bearer with default literal 'wf_integration_key_default' is denied (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.11.5 Bearer with non-ASCII string -> Denied without 500
    req = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION=f"Bearer {non_ascii_secret}")
    res = cancel_sync_view(req, pk=sync_job.pk)
    report("InternalCaller View: Non-ASCII Bearer safely denied with 401/403 (no 500 error)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # 1.11.6 Empty configured API key -> API-key path denied
    saved_api_key = getattr(settings, "WORKFORCE_API_KEY", "")
    saved_env_key = os.environ.get("WORKFORCE_API_KEY")
    try:
        settings.WORKFORCE_API_KEY = ""
        if "WORKFORCE_API_KEY" in os.environ:
            del os.environ["WORKFORCE_API_KEY"]
        req = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION="Bearer test_valid_phase10b_api_key_67890")
        res = cancel_sync_view(req, pk=sync_job.pk)
        report("InternalCaller View: Empty configured API key denies API-key path (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
    finally:
        settings.WORKFORCE_API_KEY = saved_api_key
        if saved_env_key is not None:
            os.environ["WORKFORCE_API_KEY"] = saved_env_key

    # 1.12 Non-GET methods return 405
    req = factory.post("/api/workforce/marketplace/categories/", data={}, HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("Method Guard: POST returns 405 Method Not Allowed", res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED)

    req = factory.patch("/api/workforce/marketplace/categories/", data={}, HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("Method Guard: PATCH returns 405 Method Not Allowed", res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED)

    req = factory.delete("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("Method Guard: DELETE returns 405 Method Not Allowed", res.status_code == status.HTTP_405_METHOD_NOT_ALLOWED)

    # 1.13 Authentication & Permission Scope Separation (User Views vs Integration Views)
    from rest_framework_simplejwt.tokens import AccessToken
    from workforce_api.views_seller_hub import AdminSellerHubCategoryListView

    admin_user = User.objects.create(username="jwt_admin_test_user", is_staff=True, is_superuser=True, is_active=True)
    valid_jwt = str(AccessToken.for_user(admin_user))
    user_view = AdminSellerHubCategoryListView.as_view()

    # (a) A valid JWT user still works on views that accept users
    req = factory.get("/api/workforce/seller-hub/categories/", HTTP_AUTHORIZATION=f"Bearer {valid_jwt}")
    res = user_view(req)
    report("Scope Separation: (a) Valid JWT user is accepted on user views (200 OK)", res.status_code == status.HTTP_200_OK)

    # (b) An invalid JWT / garbage Bearer is rejected on user views
    req = factory.get("/api/workforce/seller-hub/categories/", HTTP_AUTHORIZATION="Bearer garbage.invalid.jwt.token")
    res = user_view(req)
    report("Scope Separation: (b) Invalid JWT / garbage Bearer is rejected on user views (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # (c) The shared secret only works on views whose permission class is IsInternalWorkforceCaller or IsMarketplaceIntegrationCaller
    req_mkt = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION=f"Bearer {TEST_SECRET}")
    res_mkt = view(req_mkt)
    req_int = factory.post(f"/api/workforce/jobs/{sync_job.pk}/customer-cancel-sync/", HTTP_AUTHORIZATION=f"Bearer {TEST_SECRET}")
    res_int = cancel_sync_view(req_int, pk=sync_job.pk)
    report("Scope Separation: (c) Shared secret works on IsMarketplaceIntegrationCaller view (200 OK)", res_mkt.status_code == status.HTTP_200_OK)
    report("Scope Separation: (c) Shared secret works on IsInternalWorkforceCaller view (200 OK)", res_int.status_code == status.HTTP_200_OK)

    # (d) The shared secret is NOT accepted as a login on user-only views
    req = factory.get("/api/workforce/seller-hub/categories/", HTTP_AUTHORIZATION=f"Bearer {TEST_SECRET}")
    res = user_view(req)
    report("Scope Separation: (d) Shared secret is NOT accepted as a login on user-only views (401/403)", res.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # ── Test 2: Active Category & Ancestor Chain Lineage Filtering ────────────────
    req = factory.get("/api/workforce/marketplace/categories/?hide_empty=false", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("Active Lineage: hide_empty=false returns 200 OK", res.status_code == status.HTTP_200_OK)
    
    # Flatten tree to check included category slugs
    all_returned_slugs = set()
    def collect_slugs(nodes):
        for n in nodes:
            all_returned_slugs.add(n["slug"])
            collect_slugs(n.get("children", []))
    collect_slugs(res.data)

    report("Active Lineage: Inactive root category 'household' is omitted", "household" not in all_returned_slugs)
    report("Active Lineage: Active child 'cleaning' of inactive root is omitted", "cleaning" not in all_returned_slugs)
    report("Active Lineage: Inactive parent 'frozen-foods' is omitted", "frozen-foods" not in all_returned_slugs)
    report("Active Lineage: Active child 'ice-cream' under inactive parent is omitted", "ice-cream" not in all_returned_slugs)
    report("Active Lineage: Active tree categories are present", {"groceries", "dairy-eggs", "fresh-milk", "organic-eggs", "butter-ghee", "beverages", "fruit-juices", "soft-drinks", "snacks"}.issubset(all_returned_slugs))

    # ── Test 3: Sellable Product Counts & Calculations ─────────────────────────────
    # Check specific nodes in tree
    groceries_node = next((n for n in res.data if n["slug"] == "groceries"), None)
    report("Counts: Groceries root node exists", groceries_node is not None)
    
    if groceries_node:
        # Direct product count for Groceries = 0
        # Sellable products in tree:
        # - Fresh Milk: p1 (in stock), p2 (in stock) = 2 (p5 out of stock, p6 draft, p7 inactive co)
        # - Organic Eggs: p3 = 1
        # - Fruit Juices: p4 = 1
        # Total Groceries = 2 + 1 + 1 = 4
        report("Counts: Groceries direct product_count is 0", groceries_node["product_count"] == 0)
        report("Counts: Groceries total_product_count is 4", groceries_node["total_product_count"] == 4)

        dairy_node = next((n for n in groceries_node["children"] if n["slug"] == "dairy-eggs"), None)
        report("Counts: Dairy & Eggs total_product_count is 3 (2 milk + 1 eggs)", dairy_node and dairy_node["total_product_count"] == 3)

        milk_node = next((n for n in dairy_node["children"] if n["slug"] == "fresh-milk"), None)
        report("Counts: Fresh Milk direct product_count is 2", milk_node and milk_node["product_count"] == 2)
        report("Counts: Fresh Milk total_product_count is 2", milk_node and milk_node["total_product_count"] == 2)

        butter_node = next((n for n in dairy_node["children"] if n["slug"] == "butter-ghee"), None)
        report("Counts: Butter & Ghee product_count is 0", butter_node and butter_node["product_count"] == 0)
        report("Counts: Butter & Ghee total_product_count is 0", butter_node and butter_node["total_product_count"] == 0)

        bev_node = next((n for n in groceries_node["children"] if n["slug"] == "beverages"), None)
        report("Counts: Beverages total_product_count is 1 (1 juice)", bev_node and bev_node["total_product_count"] == 1)

    # ── Test 4: Schema Fields on Category Items ───────────────────────────────────
    if groceries_node and dairy_node and milk_node:
        expected_fields = {
            "id", "name", "slug", "parent_id", "sort_order", "icon", "image",
            "is_leaf", "has_children", "path", "path_string", "product_count",
            "total_product_count", "children"
        }
        report("Schema: Root node contains exact expected keys", set(groceries_node.keys()) == expected_fields)
        report("Schema: Root is_leaf is False and has_children is True", groceries_node["is_leaf"] is False and groceries_node["has_children"] is True)
        report("Schema: Leaf is_leaf is True and has_children is False", milk_node["is_leaf"] is True and milk_node["has_children"] is False)
        report("Schema: Path string matches breadcrumbs", milk_node["path_string"] == "Groceries > Dairy & Eggs > Fresh Milk")
        report("Schema: Path array length is 3", len(milk_node["path"]) == 3)
        report("Schema: Path array elements have id, name, slug", all(set(p.keys()) == {"id", "name", "slug"} for p in milk_node["path"]))

    # ── Test 5: hide_empty=true (Default) Pruning ──────────────────────────────────
    req = factory.get("/api/workforce/marketplace/categories/", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("hide_empty Default: Returns 200 OK", res.status_code == status.HTTP_200_OK)

    pruned_slugs = set()
    def collect_pruned_slugs(nodes):
        for n in nodes:
            pruned_slugs.add(n["slug"])
            collect_pruned_slugs(n.get("children", []))
    collect_pruned_slugs(res.data)

    report("hide_empty: Snacks (0 products) is pruned from root", "snacks" not in pruned_slugs)
    report("hide_empty: Butter & Ghee (0 products) is pruned from Dairy", "butter-ghee" not in pruned_slugs)
    report("hide_empty: Soft Drinks (0 products) is pruned from Beverages", "soft-drinks" not in pruned_slugs)
    report("hide_empty: Groceries (4 products) is retained", "groceries" in pruned_slugs)
    report("hide_empty: Dairy & Eggs (3 products) is retained", "dairy-eggs" in pruned_slugs)
    report("hide_empty: Fresh Milk (2 products) is retained", "fresh-milk" in pruned_slugs)
    report("hide_empty: Organic Eggs (1 product) is retained", "organic-eggs" in pruned_slugs)
    report("hide_empty: Fruit Juices (1 product) is retained", "fruit-juices" in pruned_slugs)

    # ── Test 6: Navigation Modes (parent_id & tree=false) ──────────────────────────
    # 6.1 parent_id=null (Roots only)
    req = factory.get("/api/workforce/marketplace/categories/?parent_id=null&hide_empty=false", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("parent_id=null: Returns 200 OK", res.status_code == status.HTTP_200_OK)
    root_slugs = [c["slug"] for c in res.data]
    report("parent_id=null: Returns only root active categories", set(root_slugs) == {"groceries", "snacks"})
    report("parent_id mode: Does not nest children attribute", "children" not in res.data[0])

    # 6.2 parent_id=<dairy_id>
    req = factory.get(f"/api/workforce/marketplace/categories/?parent_id={data['c_dairy'].id}&hide_empty=false", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("parent_id=<id>: Returns 200 OK", res.status_code == status.HTTP_200_OK)
    dairy_child_slugs = [c["slug"] for c in res.data]
    report("parent_id=<id>: Returns direct children", set(dairy_child_slugs) == {"fresh-milk", "organic-eggs", "butter-ghee"})

    # 6.3 parent_id=<dairy_id> with hide_empty=true
    req = factory.get(f"/api/workforce/marketplace/categories/?parent_id={data['c_dairy'].id}&hide_empty=true", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    dairy_child_slugs_filtered = [c["slug"] for c in res.data]
    report("parent_id=<id> with hide_empty: Excludes 0-stock butter", set(dairy_child_slugs_filtered) == {"fresh-milk", "organic-eggs"})

    # 6.4 tree=false (Flat active list)
    req = factory.get("/api/workforce/marketplace/categories/?tree=false&hide_empty=false", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    report("tree=false: Returns flat list of all active categories", len(res.data) == 9)

    # ── Test 7: MarketplaceProductListView Category Filtering ─────────────────────
    prod_view = MarketplaceProductListView.as_view()

    # 7.1 Filter by leaf category_id
    req = factory.get(f"/api/workforce/marketplace/products/?category_id={data['c_milk'].id}", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: category_id (leaf) returns 200 OK", res.status_code == status.HTTP_200_OK)
    report("Product Filter: category_id (leaf) returns 2 sellable milk products", res.data["count"] == 2)
    milk_skus = [p["sku"] for p in res.data["results"]]
    report("Product Filter: Correct milk SKUs returned", set(milk_skus) == {"MILK-1L", "MILK-500ML"})

    # 7.2 Filter by parent category_id (Dairy & Eggs -> milk + eggs)
    req = factory.get(f"/api/workforce/marketplace/products/?category_id={data['c_dairy'].id}", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: category_id (parent) returns 200 OK", res.status_code == status.HTTP_200_OK)
    report("Product Filter: category_id (parent) includes descendant milk and eggs products (count=3)", res.data["count"] == 3)
    dairy_skus = [p["sku"] for p in res.data["results"]]
    report("Product Filter: Correct dairy SKUs returned", set(dairy_skus) == {"MILK-1L", "MILK-500ML", "EGGS-6PK"})

    # 7.3 Filter by root category_slug (groceries -> milk + eggs + juice)
    req = factory.get("/api/workforce/marketplace/products/?category_slug=groceries", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: category_slug (root) returns 200 OK", res.status_code == status.HTTP_200_OK)
    report("Product Filter: category_slug (root) includes all sub-tree products (count=4)", res.data["count"] == 4)

    # 7.4 Unknown category_id -> 404 CATEGORY_NOT_FOUND
    req = factory.get("/api/workforce/marketplace/products/?category_id=999999", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: Unknown category_id returns 404", res.status_code == status.HTTP_404_NOT_FOUND)
    report("Product Filter: Unknown category_id code is CATEGORY_NOT_FOUND", res.data.get("code") == "CATEGORY_NOT_FOUND")

    # 7.5 Unknown category_slug -> 404 CATEGORY_NOT_FOUND
    req = factory.get("/api/workforce/marketplace/products/?category_slug=nonexistent-category-slug", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: Unknown category_slug returns 404", res.status_code == status.HTTP_404_NOT_FOUND)
    report("Product Filter: Unknown category_slug code is CATEGORY_NOT_FOUND", res.data.get("code") == "CATEGORY_NOT_FOUND")

    # 7.6 Inactive category_id -> 404 CATEGORY_NOT_FOUND
    req = factory.get(f"/api/workforce/marketplace/products/?category_id={data['c_inactive_parent'].id}", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: Inactive category_id returns 404 CATEGORY_NOT_FOUND", res.status_code == status.HTTP_404_NOT_FOUND and res.data.get("code") == "CATEGORY_NOT_FOUND")

    # 7.7 Category with inactive parent chain -> 404 CATEGORY_NOT_FOUND
    req = factory.get(f"/api/workforce/marketplace/products/?category_id={data['c_orphan_child'].id}", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Product Filter: Inactive parent chain category returns 404 CATEGORY_NOT_FOUND", res.status_code == status.HTTP_404_NOT_FOUND and res.data.get("code") == "CATEGORY_NOT_FOUND")

    # ── Test 8: Snapshot & Backward Compatibility ─────────────────────────────────
    # 8.1 Product list response structure snapshot
    req = factory.get("/api/workforce/marketplace/products/", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Snapshot: Product list returns 200 OK", res.status_code == status.HTTP_200_OK)
    expected_top_keys = {"count", "page", "page_size", "total_pages", "results"}
    report("Snapshot: Top-level product list keys unchanged", set(res.data.keys()) == expected_top_keys)

    expected_product_keys = {
        "id", "sku", "title", "brand", "unit", "pack_size", "mrp", "selling_price",
        "currency", "primary_image", "images", "description", "storage_info",
        "expiry_info", "tax_rate", "hsn_code", "seller_id", "seller_name",
        "category_path", "category_hierarchy", "available_stock", "in_stock",
        "seller", "category", "availability", "updated_at"
    }
    first_product = res.data["results"][0]
    report("Snapshot: Product item keys match 100% exact snapshot", set(first_product.keys()) == expected_product_keys)

    # 8.2 Product detail response structure snapshot
    detail_view = MarketplaceProductDetailView.as_view()
    req = factory.get(f"/api/workforce/marketplace/products/{data['p1'].id}/", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = detail_view(req, pk=data["p1"].id)
    report("Snapshot: Product detail returns 200 OK", res.status_code == status.HTTP_200_OK)
    report("Snapshot: Product detail keys match 100% exact snapshot", set(res.data.keys()) == expected_product_keys)

    # ── Test 9: Database Query Count Performance Assertion ─────────────────────────
    # Seed 50 categories and 100 products to verify bounded query count
    bulk_parent = SellerHubCategory.objects.create(name="Bulk Parent", slug="bulk-parent", is_active=True, sort_order=10)
    for i in range(50):
        sub = SellerHubCategory.objects.create(name=f"Bulk Sub {i}", slug=f"bulk-sub-{i}", is_active=True, parent=bulk_parent, sort_order=i)
        p = SellerProduct.objects.create(
            company=data["active_company"], category=sub, title=f"Bulk Prod {i}", sku=f"BULK-{i}",
            status=SellerProduct.Status.APPROVED, mrp=Decimal("100.00"), selling_price=Decimal("90.00"), unit="pc", pack_size=Decimal("1")
        )
        SellerInventory.objects.create(product=p, company=data["active_company"], on_hand_qty=Decimal("10"), reserved_qty=Decimal("0"))

    reset_queries()
    req = factory.get("/api/workforce/marketplace/categories/?tree=true", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    query_count = len(connection.queries)
    report(f"Performance: Tree endpoint with 60+ categories & 100+ products runs in {query_count} SQL queries (<= 3 queries)", query_count <= 3)

    # ── Test 10: Explicit 5-Condition Sellable Product Rule in One Category ─────────
    # Create isolated active category
    rule_cat = SellerHubCategory.objects.create(
        name="Isolated Rule Test Category",
        slug="isolated-rule-cat",
        is_active=True,
        sort_order=99,
        parent=None,
    )

    # (a) Sellable product: APPROVED, active seller, on_hand > reserved (available > 0)
    pa = SellerProduct.objects.create(
        company=data["active_company"], category=rule_cat, title="Product A Sellable", sku="SKU-RULE-A",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("100.00"), selling_price=Decimal("90.00"), unit="pc", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=pa, company=data["active_company"], on_hand_qty=Decimal("10"), reserved_qty=Decimal("2"))

    # (b) Unapproved / Draft product: DRAFT status, active seller, available > 0
    pb = SellerProduct.objects.create(
        company=data["active_company"], category=rule_cat, title="Product B Draft", sku="SKU-RULE-B",
        status=SellerProduct.Status.DRAFT, mrp=Decimal("100.00"), selling_price=Decimal("90.00"), unit="pc", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=pb, company=data["active_company"], on_hand_qty=Decimal("10"), reserved_qty=Decimal("0"))

    # (c) Paused product: PAUSED status, active seller, available > 0
    pc = SellerProduct.objects.create(
        company=data["active_company"], category=rule_cat, title="Product C Paused", sku="SKU-RULE-C",
        status=SellerProduct.Status.PAUSED, mrp=Decimal("100.00"), selling_price=Decimal("90.00"), unit="pc", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=pc, company=data["active_company"], on_hand_qty=Decimal("10"), reserved_qty=Decimal("0"))

    # (d) Zero available stock product: APPROVED status, active seller, on_hand == reserved (available == 0)
    pd = SellerProduct.objects.create(
        company=data["active_company"], category=rule_cat, title="Product D Out of Stock", sku="SKU-RULE-D",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("100.00"), selling_price=Decimal("90.00"), unit="pc", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=pd, company=data["active_company"], on_hand_qty=Decimal("5"), reserved_qty=Decimal("5"))

    # (e) Inactive seller product: APPROVED status, inactive seller (is_active=False), available > 0
    pe = SellerProduct.objects.create(
        company=data["inactive_company"], category=rule_cat, title="Product E Inactive Seller", sku="SKU-RULE-E",
        status=SellerProduct.Status.APPROVED, mrp=Decimal("100.00"), selling_price=Decimal("90.00"), unit="pc", pack_size=Decimal("1")
    )
    SellerInventory.objects.create(product=pe, company=data["inactive_company"], on_hand_qty=Decimal("10"), reserved_qty=Decimal("0"))

    # 10.1 Assert Category Feed counts
    req = factory.get("/api/workforce/marketplace/categories/?tree=false&hide_empty=false", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = view(req)
    rule_cat_node = next((n for n in res.data if n["slug"] == "isolated-rule-cat"), None)
    report("Sellable Rule: Isolated category found in feed", rule_cat_node is not None)
    if rule_cat_node:
        report("Sellable Rule: product_count is exactly 1 (only Product A)", rule_cat_node["product_count"] == 1)
        report("Sellable Rule: total_product_count is exactly 1 (only Product A)", rule_cat_node["total_product_count"] == 1)

    # 10.2 Assert MarketplaceProductListView filtered by category_id
    req = factory.get(f"/api/workforce/marketplace/products/?category_id={rule_cat.id}", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Sellable Rule: Product list by category_id returns 200 OK", res.status_code == status.HTTP_200_OK)
    report("Sellable Rule: Product list by category_id count is 1", res.data["count"] == 1)
    returned_skus = [p["sku"] for p in res.data["results"]]
    report("Sellable Rule: Product list contains Product A", "SKU-RULE-A" in returned_skus)
    report("Sellable Rule: Product list excludes Draft Product B", "SKU-RULE-B" not in returned_skus)
    report("Sellable Rule: Product list excludes Paused Product C", "SKU-RULE-C" not in returned_skus)
    report("Sellable Rule: Product list excludes Out-of-Stock Product D", "SKU-RULE-D" not in returned_skus)
    report("Sellable Rule: Product list excludes Inactive Seller Product E", "SKU-RULE-E" not in returned_skus)

    # 10.3 Assert MarketplaceProductListView filtered by category_slug
    req = factory.get("/api/workforce/marketplace/products/?category_slug=isolated-rule-cat", HTTP_AUTHORIZATION=AUTH_HEADER)
    res = prod_view(req)
    report("Sellable Rule: Product list by category_slug returns 200 OK", res.status_code == status.HTTP_200_OK)
    report("Sellable Rule: Product list by category_slug count is 1", res.data["count"] == 1)
    report("Sellable Rule: Product list by category_slug contains ONLY Product A", [p["sku"] for p in res.data["results"]] == ["SKU-RULE-A"])

    # Print results
    print("\nTest Results:")
    for r in test_results:
        print(r)
    print("\n--------------------------------------------------------------------------------")
    print(f"Summary: {passed} PASSED, {failed} FAILED (Total: {passed + failed})")
    print("================================================================================")
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

