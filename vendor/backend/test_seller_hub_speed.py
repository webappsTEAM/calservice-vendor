"""
vendor/backend/test_seller_hub_speed.py

Speed and Correctness Verification Test Suite for:
1. GET /api/workforce/seller-hub/metrics/ (bounded to <= 10 queries, Oracle verified against _legacy_metrics)
2. GET /api/workforce/seller-hub/categories/tree/ (bounded to <= 4 queries, Oracle verified against _legacy_tree)
"""
import os
import sys
import uuid
import tempfile
from decimal import Decimal

# Ensure temporary SQLite is used for all tests (NEVER PostgreSQL)
if not os.environ.get("SEVO_E2E_SQLITE_PATH"):
    temp_sqlite = os.path.join(tempfile.gettempdir(), f"sevo_speed_test_{uuid.uuid4().hex[:8]}.sqlite3")
    os.environ["SEVO_E2E_SQLITE_PATH"] = temp_sqlite

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
import django
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection, models
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

# Strict SQLite Isolation Guard
assert connection.vendor == "sqlite", f"Safety Violation: Tests must run on sqlite, got {connection.vendor}"

# Schema initialization
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

from django.contrib.auth import get_user_model
from companies.models import Company
from workforce_api.models import (
    SellerHubCategory,
    VendorCoupon,
    SellerProduct,
    SellerInventory,
    SellerInventoryBatch,
    SellerOrder,
    SellerOrderItem,
    SellerReturn,
    SellerReturnItem,
    SellerClaim,
    InventoryItem,
)
from workforce_api.serializers import SellerHubCategoryAdminSerializer
from workforce_api.views_seller_hub import (
    SellerHubMetricsView,
    AdminCatalogCategoryTreeView,
    AdminSellerHubCategoryListView,
    is_platform_reviewer,
    _resolve_user_company_id,
)

User = get_user_model()
factory = APIRequestFactory()

TEST_SECRET = "test-secret-speed-verification"
settings.WORKFORCE_WEBHOOK_SECRET = TEST_SECRET
settings.WORKFORCE_API_KEY = TEST_SECRET


def _legacy_metrics(user):
    """
    Exact verbatim legacy implementation used as an oracle for metrics correctness.
    """
    is_super = is_platform_reviewer(user)
    company_id = _resolve_user_company_id(user)

    # Products QuerySet
    prod_qs = SellerProduct.objects.all()
    if not is_super:
        if company_id:
            prod_qs = prod_qs.filter(company_id=company_id)
        else:
            prod_qs = prod_qs.none()

    awaiting_approval = prod_qs.filter(status__in=[SellerProduct.Status.SUBMITTED, SellerProduct.Status.UNDER_REVIEW]).count()
    approved_count = prod_qs.filter(status=SellerProduct.Status.APPROVED).count()
    draft_count = prod_qs.filter(status=SellerProduct.Status.DRAFT).count()
    changes_requested = prod_qs.filter(status=SellerProduct.Status.CHANGES_REQUESTED).count()
    rejected_count = prod_qs.filter(status=SellerProduct.Status.REJECTED).count()
    paused_count = prod_qs.filter(status=SellerProduct.Status.PAUSED).count()
    total_products = prod_qs.count()

    # Active categories count
    categories_count = SellerHubCategory.objects.filter(is_active=True).count()

    # Active store coupons count
    coupon_qs = VendorCoupon.objects.filter(is_active=True)
    if not is_super and company_id:
        coupon_qs = coupon_qs.filter(company_id=company_id)
    active_coupons = coupon_qs.count()

    # Inventory QuerySet
    inv_qs = SellerInventory.objects.all()
    if not is_super:
        if company_id:
            inv_qs = inv_qs.filter(company_id=company_id)
        else:
            inv_qs = inv_qs.none()

    total_inventory_products = inv_qs.count()
    low_stock_items = inv_qs.filter(
        on_hand_qty__gt=Decimal("0.000"),
        on_hand_qty__lte=models.F("low_stock_threshold")
    ).count()
    out_of_stock_items = inv_qs.filter(on_hand_qty__lte=Decimal("0.000")).count()
    in_stock_items = inv_qs.filter(on_hand_qty__gt=models.F("low_stock_threshold")).count()

    # Expiring Soon Batches (within next 30 days)
    today = timezone.now().date()
    thirty_days = today + timezone.timedelta(days=30)
    expiring_batches_qs = SellerInventoryBatch.objects.filter(
        inventory__in=inv_qs,
        current_quantity__gt=Decimal("0.000"),
        expiry_date__isnull=False,
        expiry_date__lte=thirty_days,
        expiry_date__gte=today,
    )
    expiring_soon_count = expiring_batches_qs.values("inventory_id").distinct().count()

    # Total Inventory Value (on_hand_qty * selling_price)
    total_inv_value = Decimal("0.00")
    for item in inv_qs.select_related("product"):
        if item.product and item.on_hand_qty > 0:
            price = getattr(item.product, "selling_price", Decimal("0.00")) or Decimal("0.00")
            total_inv_value += item.on_hand_qty * price

    # Phase 4 Order QuerySet
    order_qs = SellerOrder.objects.all()
    if not is_super:
        if company_id:
            order_qs = order_qs.filter(company_id=company_id)
        else:
            order_qs = order_qs.none()

    total_orders = order_qs.count()
    pending_orders = order_qs.filter(status=SellerOrder.Status.NEW).count()
    in_prep_orders = order_qs.filter(
        status__in=[
            SellerOrder.Status.ACCEPTED,
            SellerOrder.Status.PICKING,
            SellerOrder.Status.PACKED,
            SellerOrder.Status.READY_FOR_PICKUP,
        ]
    ).count()
    completed_orders = order_qs.filter(
        status__in=[
            SellerOrder.Status.HANDED_OVER,
            SellerOrder.Status.DELIVERED,
        ]
    ).count()
    cancelled_orders = order_qs.filter(status=SellerOrder.Status.CANCELLED).count()
    today_orders = order_qs.filter(created_at__date=today).count()

    # Phase 5 Return QuerySet
    return_qs = SellerReturn.objects.all()
    if not is_super:
        if company_id:
            return_qs = return_qs.filter(company_id=company_id)
        else:
            return_qs = return_qs.none()

    total_returns = return_qs.count()
    pending_returns = return_qs.filter(
        status__in=[
            SellerReturn.Status.REQUESTED,
            SellerReturn.Status.UNDER_SELLER_REVIEW,
        ]
    ).count()
    under_inspection_returns = return_qs.filter(
        status__in=[
            SellerReturn.Status.APPROVED,
            SellerReturn.Status.PICKUP_SCHEDULED,
            SellerReturn.Status.RECEIVED,
            SellerReturn.Status.QUALITY_CHECK,
        ]
    ).count()
    resolved_returns = return_qs.filter(
        status__in=[
            SellerReturn.Status.RESTOCKED,
            SellerReturn.Status.CLOSED,
            SellerReturn.Status.DISCARDED,
            SellerReturn.Status.REJECTED,
        ]
    ).count()

    # Phase 6 Claim QuerySet
    claim_qs = SellerClaim.objects.all()
    if not is_super:
        if company_id:
            claim_qs = claim_qs.filter(company_id=company_id)
        else:
            claim_qs = claim_qs.none()

    total_claims = claim_qs.count()
    open_claims = claim_qs.filter(
        status__in=[
            SellerClaim.Status.OPEN,
            SellerClaim.Status.UNDER_REVIEW,
            SellerClaim.Status.SELLER_RESPONSE_REQUIRED,
            SellerClaim.Status.ESCALATED,
        ]
    ).count()
    claims_requiring_response = claim_qs.filter(
        status=SellerClaim.Status.SELLER_RESPONSE_REQUIRED
    ).count()
    escalated_claims = claim_qs.filter(
        status=SellerClaim.Status.ESCALATED
    ).count()
    resolved_claims = claim_qs.filter(
        status__in=[
            SellerClaim.Status.APPROVED,
            SellerClaim.Status.REJECTED,
            SellerClaim.Status.SETTLED,
            SellerClaim.Status.CLOSED,
        ]
    ).count()

    return {
        "catalogs_awaiting_approval": awaiting_approval,
        "approved_products": approved_count,
        "draft_products": draft_count,
        "changes_requested": changes_requested,
        "rejected_products": rejected_count,
        "paused_products": paused_count,
        "total_products": total_products,
        "active_categories": categories_count,
        "active_coupons": active_coupons,
        "total_inventory_products": total_inventory_products,
        "low_stock_items_count": low_stock_items,
        "out_of_stock_items_count": out_of_stock_items,
        "in_stock_items_count": in_stock_items,
        "expiring_soon_items_count": expiring_soon_count,
        "total_inventory_value": str(round(total_inv_value, 2)),
        "total_orders_count": total_orders,
        "pending_orders_count": pending_orders,
        "in_prep_orders_count": in_prep_orders,
        "completed_orders_count": completed_orders,
        "cancelled_orders_count": cancelled_orders,
        "today_orders_count": today_orders,
        "total_returns_count": total_returns,
        "pending_returns_count": pending_returns,
        "under_inspection_returns_count": under_inspection_returns,
        "resolved_returns_count": resolved_returns,
        "total_claims_count": total_claims,
        "open_claims_count": open_claims,
        "claims_requiring_response_count": claims_requiring_response,
        "escalated_claims_count": escalated_claims,
        "resolved_claims_count": resolved_claims,
    }


def _legacy_tree(active_only=False):
    """
    Exact verbatim legacy implementation used as an oracle for tree correctness.
    """
    roots = SellerHubCategory.objects.filter(parent__isnull=True)
    if active_only:
        roots = roots.filter(is_active=True)
    roots = roots.order_by("sort_order", "id")

    def _node(cat):
        qs = cat.children.all()
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "id")
        
        try:
            inv_count = InventoryItem.objects.filter(catalogue_category_id=cat.id).count()
        except Exception:
            inv_count = 0
            
        try:
            children_count = cat.children.count()
        except Exception:
            children_count = 0

        depth = 0
        curr = getattr(cat, "parent", None)
        visited = {cat.id}
        while curr and getattr(curr, "id", None) not in visited:
            depth += 1
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)

        return {
            "id": cat.id,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "icon": cat.icon,
            "image": cat.image,
            "is_active": cat.is_active,
            "sort_order": cat.sort_order,
            "parent_id": cat.parent_id,
            "level": depth,
            "children_count": children_count,
            "services_count": 0,
            "inventory_items_count": inv_count,
            "children": [_node(c) for c in qs],
        }

    return [_node(r) for r in roots]


def run_tests():
    print("=" * 80)
    print("SELLER HUB SPEED & CORRECTNESS VERIFICATION SUITE")
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

    # Setup Users & Companies
    superadmin, _ = User.objects.get_or_create(
        username="speed_superadmin",
        defaults={"email": "speed_superadmin@test.com", "is_superuser": True, "is_staff": True}
    )
    superadmin.is_superuser = True
    superadmin.is_staff = True
    superadmin.save()

    company_a = Company.objects.create(
        company_name="Speed Test Store A",
        business_type="grocery_supplier",
        is_active=True,
    )
    company_b = Company.objects.create(
        company_name="Speed Test Store B",
        business_type="grocery_supplier",
        is_active=True,
    )

    seller_a = User.objects.create(
        username="speed_seller_a",
        email="seller_a@speed.com",
        role="seller",
        company=company_a,
    )
    seller_no_co = User.objects.create(
        username="speed_seller_no_co",
        email="seller_no_co@speed.com",
        role="seller",
        company=None,
    )

    # Categories
    cat_root = SellerHubCategory.objects.create(name="Speed Root", slug="speed-root", sort_order=1, is_active=True)
    cat_sub = SellerHubCategory.objects.create(name="Speed Sub", slug="speed-sub", parent=cat_root, sort_order=1, is_active=True)
    cat_leaf_a = SellerHubCategory.objects.create(name="Speed Leaf A", slug="speed-leaf-a", parent=cat_sub, sort_order=1, is_active=True)
    cat_leaf_b = SellerHubCategory.objects.create(name="Speed Leaf B", slug="speed-leaf-b", parent=cat_sub, sort_order=2, is_active=True)
    cat_inact = SellerHubCategory.objects.create(name="Speed Inactive", slug="speed-inact", parent=cat_root, sort_order=3, is_active=False)

    # Products in every status for Company A
    statuses = [
        SellerProduct.Status.DRAFT,
        SellerProduct.Status.SUBMITTED,
        SellerProduct.Status.UNDER_REVIEW,
        SellerProduct.Status.APPROVED,
        SellerProduct.Status.REJECTED,
        SellerProduct.Status.CHANGES_REQUESTED,
        SellerProduct.Status.PAUSED,
    ]
    prods_a = {}
    for st in statuses:
        p = SellerProduct.objects.create(
            company=company_a,
            category=cat_leaf_a,
            title=f"Prod A {st}",
            sku=f"SKU-A-{st}-{uuid.uuid4().hex[:4]}",
            selling_price=Decimal("150.00"),
            mrp=Decimal("180.00"),
            status=st,
        )
        prods_a[st] = p

    # Product with 0.00 selling price
    prod_no_price = SellerProduct.objects.create(
        company=company_a,
        category=cat_leaf_a,
        title="Prod Zero Price",
        sku=f"SKU-ZEROPRICE-{uuid.uuid4().hex[:4]}",
        selling_price=Decimal("0.00"),
        mrp=Decimal("100.00"),
        status=SellerProduct.Status.APPROVED,
    )

    # Products for Company B
    SellerProduct.objects.create(
        company=company_b,
        category=cat_leaf_b,
        title="Prod B Approved",
        sku=f"SKU-B-APP-{uuid.uuid4().hex[:4]}",
        selling_price=Decimal("200.00"),
        mrp=Decimal("220.00"),
        status=SellerProduct.Status.APPROVED,
    )

    # Inventory Rows in Company A
    inv_instock = SellerInventory.objects.create(
        company=company_a,
        product=prods_a[SellerProduct.Status.APPROVED],
        on_hand_qty=Decimal("50.000"),
        reserved_qty=Decimal("5.000"),
        low_stock_threshold=Decimal("10.000"),
    )
    inv_lowstock = SellerInventory.objects.create(
        company=company_a,
        product=prods_a[SellerProduct.Status.SUBMITTED],
        on_hand_qty=Decimal("5.000"),
        reserved_qty=Decimal("0.000"),
        low_stock_threshold=Decimal("10.000"),
    )
    inv_outofstock = SellerInventory.objects.create(
        company=company_a,
        product=prods_a[SellerProduct.Status.DRAFT],
        on_hand_qty=Decimal("0.000"),
        reserved_qty=Decimal("0.000"),
        low_stock_threshold=Decimal("10.000"),
    )
    inv_noprice = SellerInventory.objects.create(
        company=company_a,
        product=prod_no_price,
        on_hand_qty=Decimal("20.000"),
        reserved_qty=Decimal("0.000"),
        low_stock_threshold=Decimal("5.000"),
    )

    # Batches
    today = timezone.now().date()
    SellerInventoryBatch.objects.create(
        inventory=inv_instock,
        batch_number="BATCH-EXP-10D",
        initial_quantity=Decimal("10.000"),
        current_quantity=Decimal("10.000"),
        expiry_date=today + timezone.timedelta(days=10),
    )
    SellerInventoryBatch.objects.create(
        inventory=inv_instock,
        batch_number="BATCH-EXP-45D",
        initial_quantity=Decimal("15.000"),
        current_quantity=Decimal("15.000"),
        expiry_date=today + timezone.timedelta(days=45),
    )
    SellerInventoryBatch.objects.create(
        inventory=inv_lowstock,
        batch_number="BATCH-ZERO-QTY",
        initial_quantity=Decimal("5.000"),
        current_quantity=Decimal("0.000"),
        expiry_date=today + timezone.timedelta(days=5),
    )

    # Orders in every status
    order_statuses = [
        SellerOrder.Status.NEW,
        SellerOrder.Status.ACCEPTED,
        SellerOrder.Status.PICKING,
        SellerOrder.Status.PACKED,
        SellerOrder.Status.READY_FOR_PICKUP,
        SellerOrder.Status.HANDED_OVER,
        SellerOrder.Status.DELIVERED,
        SellerOrder.Status.CANCELLED,
    ]
    orders_list = []
    for ost in order_statuses:
        ord_obj = SellerOrder.objects.create(
            company=company_a,
            order_number=f"ORD-A-{ost}-{uuid.uuid4().hex[:4]}",
            source_order_id=f"SRC-A-{ost}-{uuid.uuid4().hex[:8]}",
            customer_name="Test Customer",
            status=ost,
            total_amount=Decimal("300.00"),
        )
        orders_list.append(ord_obj)

    # Returns in every status
    return_statuses = [
        SellerReturn.Status.REQUESTED,
        SellerReturn.Status.UNDER_SELLER_REVIEW,
        SellerReturn.Status.APPROVED,
        SellerReturn.Status.PICKUP_SCHEDULED,
        SellerReturn.Status.RECEIVED,
        SellerReturn.Status.QUALITY_CHECK,
        SellerReturn.Status.RESTOCKED,
        SellerReturn.Status.CLOSED,
        SellerReturn.Status.DISCARDED,
        SellerReturn.Status.REJECTED,
    ]
    for rst in return_statuses:
        SellerReturn.objects.create(
            company=company_a,
            order=orders_list[0],
            return_number=f"RET-A-{rst}-{uuid.uuid4().hex[:4]}",
            source_return_id=f"SRC-RET-A-{rst}-{uuid.uuid4().hex[:8]}",
            status=rst,
        )

    # Claims in every status
    claim_statuses = [
        SellerClaim.Status.OPEN,
        SellerClaim.Status.UNDER_REVIEW,
        SellerClaim.Status.SELLER_RESPONSE_REQUIRED,
        SellerClaim.Status.ESCALATED,
        SellerClaim.Status.APPROVED,
        SellerClaim.Status.REJECTED,
        SellerClaim.Status.SETTLED,
        SellerClaim.Status.CLOSED,
    ]
    for cst in claim_statuses:
        SellerClaim.objects.create(
            company=company_a,
            order=orders_list[0],
            claim_number=f"CLM-A-{cst}-{uuid.uuid4().hex[:4]}",
            source_claim_id=f"SRC-CLM-A-{cst}-{uuid.uuid4().hex[:8]}",
            customer_name="Test Customer",
            status=cst,
            claim_type="DAMAGED_IN_TRANSIT",
            claimed_amount=Decimal("100.00"),
        )

    # Coupons
    VendorCoupon.objects.create(company=company_a, code="COUPON-A-ACT", discount_type="percent", discount_value=Decimal("10.00"), is_active=True)
    VendorCoupon.objects.create(company=company_a, code="COUPON-A-INACT", discount_type="percent", discount_value=Decimal("10.00"), is_active=False)
    VendorCoupon.objects.create(company=company_b, code="COUPON-B-ACT", discount_type="percent", discount_value=Decimal("10.00"), is_active=True)

    # ─────────────────────────────────────────────────────────────────────────
    # PART 1: SellerHubMetricsView Verification
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- PART 1: SellerHubMetricsView Speed & Oracle Equality ---")
    metrics_view = SellerHubMetricsView.as_view()

    # 1. Test Seller with Company
    req_seller_a = factory.get("/api/workforce/seller-hub/metrics/")
    force_authenticate(req_seller_a, user=seller_a)
    with CaptureQueriesContext(connection) as ctx_seller_a:
        res_seller_a = metrics_view(req_seller_a)
    
    assert_test(res_seller_a.status_code == 200, "Seller A metrics returns 200 OK")
    oracle_a = _legacy_metrics(seller_a)
    assert_test(res_seller_a.data == oracle_a, "Seller A metrics 100% matches legacy oracle",
                f"Diff:\nGot: {res_seller_a.data}\nExp: {oracle_a}")
    qcount_a = len(ctx_seller_a.captured_queries)
    assert_test(qcount_a <= 10, f"Seller A metrics query count <= 10 (observed: {qcount_a})")

    # 2. Test Seller WITHOUT Company
    req_no_co = factory.get("/api/workforce/seller-hub/metrics/")
    force_authenticate(req_no_co, user=seller_no_co)
    with CaptureQueriesContext(connection) as ctx_no_co:
        res_no_co = metrics_view(req_no_co)
    
    assert_test(res_no_co.status_code == 200, "Seller No Company metrics returns 200 OK")
    oracle_no_co = _legacy_metrics(seller_no_co)
    assert_test(res_no_co.data == oracle_no_co, "Seller No Company metrics 100% matches legacy oracle",
                f"Diff:\nGot: {res_no_co.data}\nExp: {oracle_no_co}")
    qcount_no_co = len(ctx_no_co.captured_queries)
    assert_test(qcount_no_co <= 10, f"Seller No Company query count <= 10 (observed: {qcount_no_co})")

    # 3. Test Platform Admin
    req_admin = factory.get("/api/workforce/seller-hub/metrics/")
    force_authenticate(req_admin, user=superadmin)
    with CaptureQueriesContext(connection) as ctx_admin:
        res_admin = metrics_view(req_admin)
    
    assert_test(res_admin.status_code == 200, "Platform Admin metrics returns 200 OK")
    oracle_admin = _legacy_metrics(superadmin)
    assert_test(res_admin.data == oracle_admin, "Platform Admin metrics 100% matches legacy oracle",
                f"Diff:\nGot: {res_admin.data}\nExp: {oracle_admin}")
    qcount_admin = len(ctx_admin.captured_queries)
    assert_test(qcount_admin <= 10, f"Platform Admin query count <= 10 (observed: {qcount_admin})")

    # ─────────────────────────────────────────────────────────────────────────
    # PART 2: AdminCatalogCategoryTreeView Verification
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- PART 2: AdminCatalogCategoryTreeView Speed & Oracle Equality ---")
    
    # Build a larger tree: 60 roots x 2 children, 1 inactive branch, 1 3-level branch
    p2_prefix = f"p2_{uuid.uuid4().hex[:6]}"
    for i in range(1, 61):
        r = SellerHubCategory.objects.create(name=f"TreeRoot{i:02d}_{p2_prefix}", slug=f"tr-{i:02d}-{p2_prefix}", sort_order=i, is_active=True)
        c1 = SellerHubCategory.objects.create(name=f"TreeChild{i:02d}_1_{p2_prefix}", slug=f"tc-{i:02d}-1-{p2_prefix}", parent=r, sort_order=1, is_active=True)
        c2 = SellerHubCategory.objects.create(name=f"TreeChild{i:02d}_2_{p2_prefix}", slug=f"tc-{i:02d}-2-{p2_prefix}", parent=r, sort_order=2, is_active=True)
        # Link an inventory item to some category
        if i == 1:
            InventoryItem.objects.create(
                company=company_a,
                catalogue_category_id=c1.id,
                catalogue_service_id=9999,
            )

    # Inactive branch
    inact_r = SellerHubCategory.objects.create(name=f"InactRoot_{p2_prefix}", slug=f"inact-r-{p2_prefix}", sort_order=900, is_active=False)
    SellerHubCategory.objects.create(name=f"InactChild_{p2_prefix}", slug=f"inact-c-{p2_prefix}", parent=inact_r, sort_order=1, is_active=True)

    # 3-level branch
    b_l1 = SellerHubCategory.objects.create(name=f"BranchL1_{p2_prefix}", slug=f"bl1-{p2_prefix}", sort_order=901, is_active=True)
    b_l2 = SellerHubCategory.objects.create(name=f"BranchL2_{p2_prefix}", slug=f"bl2-{p2_prefix}", parent=b_l1, sort_order=1, is_active=True)
    b_l3 = SellerHubCategory.objects.create(name=f"BranchL3_{p2_prefix}", slug=f"bl3-{p2_prefix}", parent=b_l2, sort_order=1, is_active=True)

    tree_view = AdminCatalogCategoryTreeView.as_view()

    # Full Tree (all categories)
    req_tree_all = factory.get("/api/workforce/seller-hub/categories/tree/")
    force_authenticate(req_tree_all, user=superadmin)
    with CaptureQueriesContext(connection) as ctx_tree_all:
        res_tree_all = tree_view(req_tree_all)

    assert_test(res_tree_all.status_code == 200, "Full Category Tree returns 200 OK")
    oracle_tree_all = _legacy_tree(active_only=False)
    assert_test(res_tree_all.data == oracle_tree_all, "Full Category Tree 100% matches legacy oracle")
    qcount_tree_all = len(ctx_tree_all.captured_queries)
    assert_test(qcount_tree_all <= 4, f"Full Category Tree query count <= 4 (observed: {qcount_tree_all})")

    # Active-Only Tree (?is_active=true)
    req_tree_active = factory.get("/api/workforce/seller-hub/categories/tree/?is_active=true")
    force_authenticate(req_tree_active, user=superadmin)
    with CaptureQueriesContext(connection) as ctx_tree_active:
        res_tree_active = tree_view(req_tree_active)

    assert_test(res_tree_active.status_code == 200, "Active-Only Category Tree returns 200 OK")
    oracle_tree_active = _legacy_tree(active_only=True)
    assert_test(res_tree_active.data == oracle_tree_active, "Active-Only Category Tree 100% matches legacy oracle")
    qcount_tree_active = len(ctx_tree_active.captured_queries)
    assert_test(qcount_tree_active <= 4, f"Active-Only Category Tree query count <= 4 (observed: {qcount_tree_active})")

    # ─────────────────────────────────────────────────────────────────────────
    # PART 3: AdminSellerHubCategoryListView (GET seller-hub/categories/) Speed & Oracle Equality
    # ─────────────────────────────────────────────────────────────────────────
    print("\n--- PART 3: AdminSellerHubCategoryListView (GET seller-hub/categories/) Speed & Oracle Equality ---")
    
    # Extra mixed active/inactive categories fixture:
    # 1. Active root
    p3_act_root = SellerHubCategory.objects.create(name="P3 Act Root", slug="p3-act-root", sort_order=100, is_active=True)
    # 2. Inactive root
    p3_inact_root = SellerHubCategory.objects.create(name="P3 Inact Root", slug="p3-inact-root", sort_order=101, is_active=False)
    # 3. Inactive child of active parent
    p3_inact_child_act_p = SellerHubCategory.objects.create(name="P3 Inact Child of Act P", slug="p3-inact-child-act-p", parent=p3_act_root, sort_order=1, is_active=False)
    # 4. Active child of inactive parent
    p3_act_child_inact_p = SellerHubCategory.objects.create(name="P3 Act Child of Inact P", slug="p3-act-child-inact-p", parent=p3_inact_root, sort_order=1, is_active=True)
    # 5 & 6. 2-level nesting under active parent
    p3_nest_l1 = SellerHubCategory.objects.create(name="P3 Nest L1", slug="p3-nest-l1", parent=p3_act_root, sort_order=2, is_active=True)
    p3_nest_l2 = SellerHubCategory.objects.create(name="P3 Nest L2", slug="p3-nest-l2", parent=p3_nest_l1, sort_order=1, is_active=True)

    # Attach products and inventory items
    SellerProduct.objects.create(
        company=company_a,
        category=p3_nest_l2,
        title="P3 Nest L2 Prod",
        sku=f"SKU-P3-L2-{uuid.uuid4().hex[:4]}",
        selling_price=Decimal("100.00"),
        mrp=Decimal("120.00"),
        status=SellerProduct.Status.APPROVED,
    )
    InventoryItem.objects.create(
        company=company_a,
        catalogue_category_id=p3_nest_l2.id,
        catalogue_service_id=7777,
    )

    admin_cat_list_view = AdminSellerHubCategoryListView.as_view()

    # Call GET /api/workforce/seller-hub/categories/ as Platform Admin
    req_admin_cat_list = factory.get("/api/workforce/seller-hub/categories/")
    force_authenticate(req_admin_cat_list, user=superadmin)
    with CaptureQueriesContext(connection) as ctx_admin_cat_list:
        res_admin_cat_list = admin_cat_list_view(req_admin_cat_list)

    assert_test(res_admin_cat_list.status_code == 200, "Admin Category List returns 200 OK")
    
    # Oracle: Legacy SellerHubCategoryAdminSerializer
    legacy_qs = SellerHubCategory.objects.all().order_by("sort_order", "id")
    oracle_admin_cat_list = SellerHubCategoryAdminSerializer(legacy_qs, many=True).data
    
    assert_test(res_admin_cat_list.data == oracle_admin_cat_list, "Admin Category List 100% matches legacy serializer oracle")
    qcount_admin_cat_list = len(ctx_admin_cat_list.captured_queries)
    # Ceiling chosen: <= 4 queries (1 for categories, 1 for product counts, 1 for inventory item counts, +1 buffer)
    assert_test(qcount_admin_cat_list <= 4, f"Admin Category List query count <= 4 (observed: {qcount_admin_cat_list})")

    print("\n" + "=" * 80)
    print(f"VERIFICATION SUMMARY: {passed_count} PASSED, {failed_count} FAILED")
    print("=" * 80)

    if failed_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
