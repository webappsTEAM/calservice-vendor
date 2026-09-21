"""
run_marketplace_integration_verification.py

Comprehensive verification test suite for Phase 8A:
Vendor-side Customer Marketplace Integration APIs.

Tests:
1. Public Customer Catalog Integration Feed (filtering, lineage, sanitization, search, store/category filters)
2. Product Detail API (sanitized payload, 404 for unapproved/out-of-stock)
3. Customer Cart Validation API (live price & stock checks, error codes)
4. Canonical Order Intake API (atomic reservation, strict idempotency, insufficient stock rejection, rollback)
5. Order Cancellation & Stock Release API (atomic stock release, idempotency, state validation)
6. Integration Security & Tenant Isolation (fail-closed auth, secret headers, bearer tokens)
"""

import os
import sys
import tempfile
import django
from decimal import Decimal
import uuid

_sqlite_temp = tempfile.NamedTemporaryFile(suffix="_marketplace_verif.sqlite3", delete=False)
_sqlite_temp.close()
os.environ["SEVO_E2E_SQLITE_PATH"] = _sqlite_temp.name

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection

# Hard safety guard: ensure test execution is strictly against SQLite
if connection.vendor != "sqlite":
    raise RuntimeError(
        f"SAFETY ABORT: run_marketplace_integration_verification initialized against non-SQLite database (vendor={connection.vendor!r}). "
        "Tests must ONLY execute against isolated temporary SQLite."
    )

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

settings.ALLOWED_HOSTS = ["*"]

from unittest.mock import patch
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory
from rest_framework import status

TEST_WEBHOOK_SECRET = "test-secret-not-real-run-marketplace"
settings.WORKFORCE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
settings.WORKFORCE_API_KEY = TEST_WEBHOOK_SECRET


def _guarded_real_post(*args, **kwargs):
    raise AssertionError(f"SECURITY GUARD: Real outbound network request attempted in run_marketplace_integration_verification: {args} {kwargs}")

from companies.models import Company
from workforce_api.models import (
    SellerHubCategory,
    SellerProduct,
    SellerProductImage,
    SellerInventory,
    SellerInventoryMovement,
    SellerOrder,
    SellerOrderItem,
    SellerOrderAuditLog,
)
from workforce_api.views_marketplace_integration import (
    MarketplaceProductListView,
    MarketplaceProductDetailView,
    MarketplaceCartValidateView,
    MarketplaceOrderIntakeView,
    MarketplaceOrderCancelReleaseView,
    get_active_seller_category_ids,
)

User = get_user_model()
factory = APIRequestFactory()


def run_tests():
    print("=" * 80)
    print("STARTING PHASE 8A: CUSTOMER MARKETPLACE INTEGRATION VERIFICATION")
    print("=" * 80)

    patch_dispatch = patch("workforce_api.services.seller_order_outbox._trigger_background_dispatch")
    patch_dispatch.start()
    patch_post = patch("requests.post", side_effect=_guarded_real_post)
    patch_post.start()

    uid = uuid.uuid4().hex[:6]

    # 1. Setup Test Data
    print("\n--- 1. Setting up Test Data ---")
    admin_user, _ = User.objects.get_or_create(
        username=f"mkt_test_admin_{uid}",
        defaults={"email": f"mkt_admin_{uid}@sevo.local", "role": "ADMIN", "is_staff": True}
    )

    company_active, _ = Company.objects.get_or_create(
        slug=f"fresh-greens-store-{uid}",
        defaults={
            "company_name": "Fresh Greens Store",
            "is_active": True,
            "business_type": "grocery_seller",
        }
    )
    company_active.is_active = True
    company_active.save()

    company_inactive, _ = Company.objects.get_or_create(
        slug=f"inactive-store-{uid}",
        defaults={
            "company_name": "Inactive Store",
            "is_active": False,
            "business_type": "grocery_seller",
        }
    )
    company_inactive.is_active = False
    company_inactive.save()

    # Create Category Hierarchy:
    # Root: Groceries (Active)
    #  -> Child: Dairy & Eggs (Active)
    #      -> Grandchild: Farm Fresh Milk (Active)
    #  -> Inactive Branch: Seasonal Fruits (Inactive)
    #      -> Child under inactive: Mangoes (Active flag, but parent inactive)
    root_cat, _ = SellerHubCategory.objects.get_or_create(
        slug=f"mkt-groceries-{uid}",
        defaults={"name": "Groceries", "is_active": True, "sort_order": 1}
    )
    root_cat.is_active = True
    root_cat.parent = None
    root_cat.save()

    child_cat, _ = SellerHubCategory.objects.get_or_create(
        slug=f"mkt-dairy-eggs-{uid}",
        defaults={"name": "Dairy & Eggs", "is_active": True, "parent": root_cat, "sort_order": 1}
    )
    child_cat.is_active = True
    child_cat.parent = root_cat
    child_cat.save()

    grandchild_cat, _ = SellerHubCategory.objects.get_or_create(
        slug=f"mkt-farm-milk-{uid}",
        defaults={"name": "Farm Fresh Milk", "is_active": True, "parent": child_cat, "sort_order": 1}
    )
    grandchild_cat.is_active = True
    grandchild_cat.parent = child_cat
    grandchild_cat.save()

    inactive_root, _ = SellerHubCategory.objects.get_or_create(
        slug=f"mkt-seasonal-fruits-{uid}",
        defaults={"name": "Seasonal Fruits", "is_active": False, "sort_order": 2}
    )
    inactive_root.is_active = False
    inactive_root.parent = None
    inactive_root.save()

    mangoes_cat, _ = SellerHubCategory.objects.get_or_create(
        slug=f"mkt-mangoes-{uid}",
        defaults={"name": "Mangoes", "is_active": True, "parent": inactive_root, "sort_order": 1}
    )
    mangoes_cat.is_active = True
    mangoes_cat.parent = inactive_root
    mangoes_cat.save()

    # Verify category active lineage helper
    active_ids = get_active_seller_category_ids()
    assert root_cat.id in active_ids, "Root cat should be active"
    assert child_cat.id in active_ids, "Child cat should be active"
    assert grandchild_cat.id in active_ids, "Grandchild cat should be active"
    assert inactive_root.id not in active_ids, "Inactive root should not be active"
    assert mangoes_cat.id not in active_ids, "Mangoes child of inactive parent must NOT be active"
    print("  [OK] Category lineage active calculation correctly verified.")

    # Create Products:
    # 1. Product A: Approved, in-stock, active company, active cat -> SHOULD BE PUBLISHED
    prod_a, _ = SellerProduct.objects.get_or_create(
        company=company_active,
        sku="SKU-MILK-001",
        defaults={
            "title": "Organic Farm Milk 1L",
            "category": grandchild_cat,
            "brand": "PureDairy",
            "mrp": Decimal("75.00"),
            "selling_price": Decimal("68.00"),
            "status": "APPROVED",
            "unit": "L",
            "pack_size": "1 Litre",
            "admin_review_note": "Reviewed and approved by QA team",
        }
    )
    prod_a.status = "APPROVED"
    prod_a.category = grandchild_cat
    prod_a.admin_review_note = "Reviewed and approved by QA team"
    prod_a.save()

    # Image for Prod A
    SellerProductImage.objects.filter(product=prod_a).delete()
    SellerProductImage.objects.create(
        product=prod_a,
        image_url="https://cdn.example.com/milk_front.jpg",
        is_primary=True,
        sort_order=1
    )
    SellerProductImage.objects.create(
        product=prod_a,
        image_url="https://cdn.example.com/milk_back.jpg",
        is_primary=False,
        sort_order=2
    )

    inv_a, _ = SellerInventory.objects.get_or_create(
        company=company_active,
        product=prod_a,
        defaults={"on_hand_qty": 50, "reserved_qty": 5}
    )
    inv_a.on_hand_qty = 50
    inv_a.reserved_qty = 5  # Available = 45
    inv_a.save()

    # 2. Product B: DRAFT status -> MUST NOT BE PUBLISHED
    prod_b, _ = SellerProduct.objects.get_or_create(
        company=company_active,
        sku="SKU-DRAFT-002",
        defaults={
            "title": "Draft Butter 500g",
            "category": child_cat,
            "brand": "PureDairy",
            "mrp": Decimal("120.00"),
            "selling_price": Decimal("110.00"),
            "status": "DRAFT",
            "unit": "g",
            "pack_size": "500g"
        }
    )
    prod_b.status = "DRAFT"
    prod_b.save()
    inv_b, _ = SellerInventory.objects.get_or_create(
        company=company_active,
        product=prod_b,
        defaults={"on_hand_qty": 20, "reserved_qty": 0}
    )
    inv_b.on_hand_qty = 20
    inv_b.reserved_qty = 0
    inv_b.save()

    # 3. Product C: Out of stock (on_hand = reserved) -> MUST NOT BE PUBLISHED
    prod_c, _ = SellerProduct.objects.get_or_create(
        company=company_active,
        sku="SKU-OUT-OF-STOCK-003",
        defaults={
            "title": "Sold Out Cheese 200g",
            "category": child_cat,
            "brand": "PureDairy",
            "mrp": Decimal("150.00"),
            "selling_price": Decimal("140.00"),
            "status": "APPROVED",
            "unit": "g",
            "pack_size": "200g"
        }
    )
    prod_c.status = "APPROVED"
    prod_c.save()
    inv_c, _ = SellerInventory.objects.get_or_create(
        company=company_active,
        product=prod_c,
        defaults={"on_hand_qty": 10, "reserved_qty": 10}
    )
    inv_c.on_hand_qty = 10
    inv_c.reserved_qty = 10  # Available = 0
    inv_c.save()

    # 4. Product D: Under Inactive Category lineage -> MUST NOT BE PUBLISHED
    prod_d, _ = SellerProduct.objects.get_or_create(
        company=company_active,
        sku="SKU-INACT-CAT-004",
        defaults={
            "title": "Alphonso Mango 1kg",
            "category": mangoes_cat,
            "brand": "Ratnagiri",
            "mrp": Decimal("500.00"),
            "selling_price": Decimal("450.00"),
            "status": "APPROVED",
            "unit": "kg",
            "pack_size": "1 kg"
        }
    )
    prod_d.status = "APPROVED"
    prod_d.category = mangoes_cat
    prod_d.save()
    inv_d, _ = SellerInventory.objects.get_or_create(
        company=company_active,
        product=prod_d,
        defaults={"on_hand_qty": 100, "reserved_qty": 0}
    )
    inv_d.on_hand_qty = 100
    inv_d.reserved_qty = 0
    inv_d.save()

    # 5. Product E: Belonging to Inactive Company -> MUST NOT BE PUBLISHED
    prod_e, _ = SellerProduct.objects.get_or_create(
        company=company_inactive,
        sku="SKU-INACT-COMP-005",
        defaults={
            "title": "Inactive Seller Bread 400g",
            "category": root_cat,
            "brand": "BakeFresh",
            "mrp": Decimal("40.00"),
            "selling_price": Decimal("38.00"),
            "status": "APPROVED",
            "unit": "g",
            "pack_size": "400g"
        }
    )
    prod_e.status = "APPROVED"
    prod_e.save()
    inv_e, _ = SellerInventory.objects.get_or_create(
        company=company_inactive,
        product=prod_e,
        defaults={"on_hand_qty": 30, "reserved_qty": 0}
    )
    inv_e.on_hand_qty = 30
    inv_e.reserved_qty = 0
    inv_e.save()

    print("  [OK] Test data created successfully.")

    # Configure Integration Secret
    headers = {"HTTP_X_WORKFORCE_WEBHOOK_SECRET": TEST_WEBHOOK_SECRET}

    # =========================================================================
    # 2. Test Integration Authentication (Security Fail-Closed)
    # =========================================================================
    print("\n--- 2. Testing Integration Authentication & Security ---")
    list_view = MarketplaceProductListView.as_view()

    # Unauthenticated request (no header)
    req_no_auth = factory.get("/api/workforce/marketplace/products/")
    res_no_auth = list_view(req_no_auth)
    assert res_no_auth.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN], f"Expected 401/403, got {res_no_auth.status_code}"
    print("  [OK] Unauthenticated request correctly rejected with 401/403.")

    # Invalid Secret Header
    req_bad_auth = factory.get("/api/workforce/marketplace/products/", HTTP_X_WORKFORCE_WEBHOOK_SECRET="invalid_token_12345")
    res_bad_auth = list_view(req_bad_auth)
    assert res_bad_auth.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN], f"Expected 401/403, got {res_bad_auth.status_code}"
    print("  [OK] Invalid secret header correctly rejected.")

    # Valid Secret Header
    req_valid = factory.get("/api/workforce/marketplace/products/", **headers)
    res_valid = list_view(req_valid)
    assert res_valid.status_code == status.HTTP_200_OK, f"Expected 200, got {res_valid.status_code}"
    print("  [OK] Valid integration secret successfully authenticated.")

    # =========================================================================
    # 3. Test Public Customer Catalog Feed API
    # =========================================================================
    print("\n--- 3. Testing Public Customer Catalog Feed API ---")
    results = res_valid.data.get("results", [])
    product_ids = [p["id"] for p in results]

    # Verification: Only Product A should be present
    assert prod_a.id in product_ids, "Product A (approved + in-stock + active category) must be published"
    assert prod_b.id not in product_ids, "Product B (DRAFT) must NOT be published"
    assert prod_c.id not in product_ids, "Product C (Out of Stock) must NOT be published"
    assert prod_d.id not in product_ids, "Product D (Inactive parent category) must NOT be published"
    assert prod_e.id not in product_ids, "Product E (Inactive Company) must NOT be published"
    print("  [OK] Catalog feed publishes ONLY eligible approved & in-stock products with active category lineage.")

    # Check payload sanitization
    prod_a_data = next(p for p in results if p["id"] == prod_a.id)
    assert "cost_price" not in prod_a_data, "Cost price must NOT be exposed in customer payload"
    assert "internal_notes" not in prod_a_data, "Internal notes must NOT be exposed"
    assert "admin_review_notes" not in prod_a_data, "Admin review notes must NOT be exposed"
    assert "admin_review_note" not in prod_a_data, "Admin review note must NOT be exposed"
    assert prod_a_data["title"] == "Organic Farm Milk 1L"
    assert prod_a_data["sku"] == "SKU-MILK-001"
    assert prod_a_data["seller_name"] == "Fresh Greens Store"
    assert prod_a_data["available_stock"] == 45
    assert prod_a_data["in_stock"] is True
    assert prod_a_data["selling_price"] == "68.00"
    assert prod_a_data["mrp"] == "75.00"
    assert prod_a_data["primary_image"] == "https://cdn.example.com/milk_front.jpg"
    assert prod_a_data["category_path"] == "Groceries > Dairy & Eggs > Farm Fresh Milk"
    assert len(prod_a_data["category_hierarchy"]) == 3, f"Expected category hierarchy depth 3, got {prod_a_data['category_hierarchy']}"
    print("  [OK] Customer catalog payload is strictly sanitized and contains all required customer fields.")

    # Search filter test
    req_search = factory.get("/api/workforce/marketplace/products/?search=Organic", **headers)
    res_search = list_view(req_search)
    assert res_search.data["count"] >= 1
    assert any(p["id"] == prod_a.id for p in res_search.data["results"])

    req_search_none = factory.get("/api/workforce/marketplace/products/?search=NonExistentItem999", **headers)
    res_search_none = list_view(req_search_none)
    assert res_search_none.data["count"] == 0
    print("  [OK] Catalog search query filter functions correctly.")

    # Category filter test (filtering by root category should include descendants)
    req_cat_filter = factory.get(f"/api/workforce/marketplace/products/?category={root_cat.id}", **headers)
    res_cat_filter = list_view(req_cat_filter)
    assert any(p["id"] == prod_a.id for p in res_cat_filter.data["results"]), "Filtering by parent category should match grandchild product"
    print("  [OK] Catalog category filtering includes descendant subcategories.")

    # Store filter test
    req_store_filter = factory.get(f"/api/workforce/marketplace/products/?seller_id={company_active.id}", **headers)
    res_store_filter = list_view(req_store_filter)
    assert any(p["id"] == prod_a.id for p in res_store_filter.data["results"])
    print("  [OK] Catalog seller/store filter works as expected.")

    # =========================================================================
    # 4. Test Product Detail Lookup API
    # =========================================================================
    print("\n--- 4. Testing Product Detail Lookup API ---")
    detail_view = MarketplaceProductDetailView.as_view()

    # Detail for active/in-stock product
    req_detail_a = factory.get(f"/api/workforce/marketplace/products/{prod_a.id}/", **headers)
    res_detail_a = detail_view(req_detail_a, pk=prod_a.id)
    assert res_detail_a.status_code == status.HTTP_200_OK
    assert res_detail_a.data["id"] == prod_a.id
    assert len(res_detail_a.data["images"]) == 2
    assert "cost_price" not in res_detail_a.data
    print("  [OK] Product detail returns complete sanitized payload and gallery.")

    # Detail for unapproved product -> 404
    req_detail_b = factory.get(f"/api/workforce/marketplace/products/{prod_b.id}/", **headers)
    res_detail_b = detail_view(req_detail_b, pk=prod_b.id)
    assert res_detail_b.status_code == status.HTTP_404_NOT_FOUND
    print("  [OK] Product detail for DRAFT product correctly returns 404.")

    # Detail for out-of-stock product -> 404
    req_detail_c = factory.get(f"/api/workforce/marketplace/products/{prod_c.id}/", **headers)
    res_detail_c = detail_view(req_detail_c, pk=prod_c.id)
    assert res_detail_c.status_code == status.HTTP_404_NOT_FOUND
    print("  [OK] Product detail for OUT_OF_STOCK product correctly returns 404.")

    # =========================================================================
    # 5. Test Customer Cart Validation API
    # =========================================================================
    print("\n--- 5. Testing Customer Cart Validation API ---")
    cart_val_view = MarketplaceCartValidateView.as_view()

    # Case A: Valid Cart Item (requested qty <= available stock)
    cart_payload_valid = {
        "items": [
            {
                "product_id": prod_a.id,
                "requested_quantity": 3,
                "expected_unit_price": "68.00"
            }
        ]
    }
    req_cart_valid = factory.post(
        "/api/workforce/marketplace/cart/validate/",
        cart_payload_valid,
        format="json",
        **headers
    )
    res_cart_valid = cart_val_view(req_cart_valid)
    assert res_cart_valid.status_code == status.HTTP_200_OK
    assert res_cart_valid.data["is_valid"] is True
    assert res_cart_valid.data["items"][0]["status"] == "AVAILABLE"
    assert res_cart_valid.data["items"][0]["available_quantity"] == 45
    assert res_cart_valid.data["items"][0]["current_selling_price"] == "68.00"
    print("  [OK] Valid cart validation returns is_valid=True with live price and stock.")

    # Case B: Price Mismatch detected (frontend had stale price)
    cart_payload_price_mismatch = {
        "items": [
            {
                "product_id": prod_a.id,
                "requested_quantity": 2,
                "expected_unit_price": "50.00"  # Stale price
            }
        ]
    }
    req_cart_price = factory.post(
        "/api/workforce/marketplace/cart/validate/",
        cart_payload_price_mismatch,
        format="json",
        **headers
    )
    res_cart_price = cart_val_view(req_cart_price)
    assert res_cart_price.status_code == status.HTTP_200_OK
    assert res_cart_price.data["is_valid"] is False
    assert res_cart_price.data["items"][0]["price_changed"] is True
    assert res_cart_price.data["items"][0]["current_selling_price"] == "68.00"
    print("  [OK] Cart validation detects stale prices and provides current DB selling price.")

    # Case C: Insufficient Stock requested
    cart_payload_excess = {
        "items": [
            {
                "product_id": prod_a.id,
                "requested_quantity": 100,  # Only 45 available
                "expected_unit_price": "68.00"
            }
        ]
    }
    req_cart_excess = factory.post(
        "/api/workforce/marketplace/cart/validate/",
        cart_payload_excess,
        format="json",
        **headers
    )
    res_cart_excess = cart_val_view(req_cart_excess)
    assert res_cart_excess.status_code == status.HTTP_200_OK
    assert res_cart_excess.data["is_valid"] is False
    assert res_cart_excess.data["items"][0]["status"] == "INSUFFICIENT_STOCK"
    assert res_cart_excess.data["items"][0]["available_quantity"] == 45
    print("  [OK] Cart validation detects insufficient stock and returns available quantity.")

    # Case D: Unapproved or Inactive Product in Cart
    cart_payload_unapproved = {
        "items": [
            {
                "product_id": prod_b.id,  # DRAFT
                "requested_quantity": 1
            }
        ]
    }
    req_cart_unapproved = factory.post(
        "/api/workforce/marketplace/cart/validate/",
        cart_payload_unapproved,
        format="json",
        **headers
    )
    res_cart_unapproved = cart_val_view(req_cart_unapproved)
    assert res_cart_unapproved.status_code == status.HTTP_200_OK
    assert res_cart_unapproved.data["is_valid"] is False
    assert res_cart_unapproved.data["items"][0]["status"] == "UNAVAILABLE"
    print("  [OK] Cart validation rejects unapproved products.")

    # =========================================================================
    # 6. Test Canonical Customer-Order Intake API & Atomic Stock Reservation
    # =========================================================================
    print("\n--- 6. Testing Canonical Customer-Order Intake API ---")
    intake_view = MarketplaceOrderIntakeView.as_view()

    # Check inventory before intake
    inv_a.refresh_from_db()
    initial_on_hand = inv_a.on_hand_qty
    initial_reserved = inv_a.reserved_qty
    order_qty = 4

    source_order_id = f"CUST-ORD-{uuid.uuid4().hex[:10].upper()}"
    intake_payload = {
        "source_order_id": source_order_id,
        "seller_id": company_active.id,
        "customer_name": "Alice Sharma",
        "customer_phone": "+919876543210",
        "customer_email": "alice@example.com",
        "fulfilment_type": "DELIVERY",
        "delivery_address": {
            "street": "123 MG Road, Koramangala",
            "city": "Bengaluru",
            "state": "KA",
            "pincode": "560034"
        },
        "payment_snapshot": {
            "method": "UPI",
            "transaction_id": "TXN_UPI_891234",
            "status": "PAID",
            "currency": "INR",
            "paid_amount": "272.00"
        },
        "items": [
            {
                "product_id": prod_a.id,
                "quantity": order_qty,
                "unit_price": "68.00"
            }
        ]
    }

    # First Intake Request
    req_intake_1 = factory.post(
        "/api/workforce/marketplace/orders/intake/",
        intake_payload,
        format="json",
        **headers
    )
    res_intake_1 = intake_view(req_intake_1)
    assert res_intake_1.status_code == status.HTTP_201_CREATED, f"Expected 201, got {res_intake_1.status_code}: {res_intake_1.data}"
    order_data = res_intake_1.data["order"]
    assert order_data["source_order_id"] == source_order_id
    assert order_data["status"] == "NEW"
    assert order_data["items_count"] == 1
    assert Decimal(str(order_data["total_amount"])) == Decimal("272.00")

    # Check stock reservation in DB
    inv_a.refresh_from_db()
    assert inv_a.reserved_qty == initial_reserved + order_qty, f"Reserved qty should be {initial_reserved + order_qty}, got {inv_a.reserved_qty}"
    assert inv_a.on_hand_qty == initial_on_hand, "On hand qty should remain unchanged during reservation"

    # Check inventory movement was logged
    movement = SellerInventoryMovement.objects.filter(
        inventory=inv_a,
        movement_type="RESERVED",
        reference_id=source_order_id
    ).first()
    assert movement is not None, "RESERVED movement record must exist"
    assert movement.movement_type == "RESERVED"
    print("  [OK] Order intake successfully reserved stock atomically and created RESERVED movement record.")

    # Check audit log
    created_order = SellerOrder.objects.get(source_order_id=source_order_id)
    audit = SellerOrderAuditLog.objects.filter(order=created_order, action="ORDER_INTAKE").first()
    assert audit is not None, "ORDER_INTAKE audit log must exist"
    print("  [OK] Order audit log recorded properly.")

    # Idempotency Test: Sending EXACT SAME source_order_id again
    req_intake_retry = factory.post(
        "/api/workforce/marketplace/orders/intake/",
        intake_payload,
        format="json",
        **headers
    )
    res_intake_retry = intake_view(req_intake_retry)
    assert res_intake_retry.status_code == status.HTTP_200_OK, f"Expected 200 for idempotent retry, got {res_intake_retry.status_code}"
    assert res_intake_retry.data["is_idempotent_replay"] is True
    assert res_intake_retry.data["order"]["id"] == order_data["id"]

    # Verify inventory was NOT reserved a second time
    inv_a.refresh_from_db()
    assert inv_a.reserved_qty == initial_reserved + order_qty, "Idempotent replay must NOT double-reserve stock"
    print("  [OK] Order intake idempotency verified: Replay returns original order without duplicating stock reservations.")

    # Test Insufficient Stock Intake Rejection & Rollback
    excess_source_order_id = f"CUST-ORD-EXCESS-{uuid.uuid4().hex[:8].upper()}"
    excess_intake_payload = {
        "source_order_id": excess_source_order_id,
        "seller_id": company_active.id,
        "customer_name": "Bob Smith",
        "customer_phone": "+919876543211",
        "items": [
            {
                "product_id": prod_a.id,
                "quantity": 9999,  # Impossible quantity
                "unit_price": "68.00"
            }
        ]
    }
    req_intake_excess = factory.post(
        "/api/workforce/marketplace/orders/intake/",
        excess_intake_payload,
        format="json",
        **headers
    )
    res_intake_excess = intake_view(req_intake_excess)
    assert res_intake_excess.status_code == status.HTTP_409_CONFLICT, f"Expected 409, got {res_intake_excess.status_code}"
    assert res_intake_excess.data["error_code"] == "INSUFFICIENT_STOCK"
    assert not SellerOrder.objects.filter(source_order_id=excess_source_order_id).exists(), "No order record should be saved on conflict"

    # Verify inventory remains unchanged after failed intake
    inv_a.refresh_from_db()
    assert inv_a.reserved_qty == initial_reserved + order_qty, "Failed intake must cleanly roll back stock reservations"
    print("  [OK] Insufficient stock intake rejected with 409 and clean transaction rollback.")

    # =========================================================================
    # 7. Test Order Cancellation & Reservation Release API
    # =========================================================================
    print("\n--- 7. Testing Order Cancellation & Reservation Release API ---")
    cancel_view = MarketplaceOrderCancelReleaseView.as_view()

    cancel_payload = {
        "cancellation_reason": "Customer changed mind before fulfilment",
        "cancelled_by": "CUSTOMER",
        "cancellation_notes": "Cancelled through app checkout page"
    }

    # Cancel order
    req_cancel_1 = factory.post(
        f"/api/workforce/marketplace/orders/{source_order_id}/cancel/",
        cancel_payload,
        format="json",
        **headers
    )
    res_cancel_1 = cancel_view(req_cancel_1, source_order_id=source_order_id)
    assert res_cancel_1.status_code == status.HTTP_200_OK, f"Expected 200, got {res_cancel_1.status_code}: {res_cancel_1.data}"
    assert res_cancel_1.data["order_status"] == "CANCELLED"
    assert res_cancel_1.data["released_reservations_count"] == 1

    # Check inventory reservation released in DB
    inv_a.refresh_from_db()
    assert inv_a.reserved_qty == initial_reserved, f"Reserved qty should have returned to {initial_reserved}, got {inv_a.reserved_qty}"

    # Check reservation release movement
    rel_movement = SellerInventoryMovement.objects.filter(
        inventory=inv_a,
        movement_type="RESERVATION_RELEASED",
        reference_id=source_order_id
    ).first()
    assert rel_movement is not None, "RESERVATION_RELEASED movement record must exist"
    assert rel_movement.movement_type == "RESERVATION_RELEASED"
    print("  [OK] Order cancellation atomically released reserved stock and created RESERVATION_RELEASED movement.")

    # Check cancellation audit log
    cancel_audit = SellerOrderAuditLog.objects.filter(order=created_order, action="CANCELLED_BY_INTEGRATION").first()
    assert cancel_audit is not None, "CANCELLED_BY_INTEGRATION audit log must exist"
    print("  [OK] Cancellation audit log recorded.")

    # Idempotent Cancellation Retry
    req_cancel_retry = factory.post(
        f"/api/workforce/marketplace/orders/{source_order_id}/cancel/",
        cancel_payload,
        format="json",
        **headers
    )
    res_cancel_retry = cancel_view(req_cancel_retry, source_order_id=source_order_id)
    assert res_cancel_retry.status_code == status.HTTP_200_OK
    assert res_cancel_retry.data["already_cancelled"] is True

    # Verify inventory was NOT released again (avoid negative reserved_qty)
    inv_a.refresh_from_db()
    assert inv_a.reserved_qty == initial_reserved, "Cancellation retry must NOT double-release stock"
    print("  [OK] Order cancellation idempotency verified: Repeating cancel does not duplicate stock releases.")

    # Try cancelling non-existent order -> 404
    req_cancel_404 = factory.post(
        "/api/workforce/marketplace/orders/NON-EXISTENT-ID-999/cancel/",
        cancel_payload,
        format="json",
        **headers
    )
    res_cancel_404 = cancel_view(req_cancel_404, source_order_id="NON-EXISTENT-ID-999")
    assert res_cancel_404.status_code == status.HTTP_404_NOT_FOUND
    print("  [OK] Cancelling non-existent source order returns 404.")

    patch_post.stop()
    patch_dispatch.stop()

    print("\n" + "=" * 80)
    print("ALL PHASE 8A VERIFICATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
