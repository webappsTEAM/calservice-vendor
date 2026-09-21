import os
import sys
import uuid
import tempfile
import django

_sqlite_temp = tempfile.NamedTemporaryFile(suffix="_reports_verif.sqlite3", delete=False)
_sqlite_temp.close()
os.environ["SEVO_E2E_SQLITE_PATH"] = _sqlite_temp.name

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.apps import apps
from django.conf import settings
from django.db import connection

# Hard safety guard: ensure test execution is strictly against SQLite
if connection.vendor != "sqlite":
    raise RuntimeError(
        f"SAFETY ABORT: run_reports_verification initialized against non-SQLite database (vendor={connection.vendor!r}). "
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
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate
from django.contrib.auth import get_user_model

TEST_WEBHOOK_SECRET = "test-secret-not-real-run-reports"
settings.WORKFORCE_WEBHOOK_SECRET = TEST_WEBHOOK_SECRET
settings.WORKFORCE_API_KEY = TEST_WEBHOOK_SECRET


def _guarded_real_post(*args, **kwargs):
    raise AssertionError(f"SECURITY GUARD: Real outbound network request attempted in run_reports_verification: {args} {kwargs}")

from companies.models import Company
from workforce_api.models import (
    SellerHubCategory,
    SellerProduct,
    SellerProductImage,
    SellerInventory,
    SellerInventoryBatch,
    SellerInventoryMovement,
    SellerOrder,
    SellerOrderItem,
    SellerReturn,
    SellerClaim,
)
from workforce_api.views_seller_hub import (
    SellerReportsSummaryView,
    SellerReportsPerformanceView,
    SellerReportsQualityAuditView,
    SellerReportsExportCSVView,
)

User = get_user_model()

def run_tests():
    print("=" * 70)
    print(">>> RUNNING PHASE 7: SELLER REPORTS, QUALITY & PERFORMANCE SUITE <<<")
    print("=" * 70)

    factory = APIRequestFactory()

    patch_dispatch = patch("workforce_api.services.seller_order_outbox._trigger_background_dispatch")
    patch_dispatch.start()
    patch_post = patch("requests.post", side_effect=_guarded_real_post)
    patch_post.start()

    uid = uuid.uuid4().hex[:6]

    # 1. Setup Companies and Users
    comp_a, _ = Company.objects.get_or_create(
        slug=f"reports-company-a-{uid}",
        defaults={"company_name": "Reports Test Seller A", "business_type": "grocery_supplier", "is_active": True}
    )
    comp_b, _ = Company.objects.get_or_create(
        slug=f"reports-company-b-{uid}",
        defaults={"company_name": "Reports Test Seller B", "business_type": "grocery_supplier", "is_active": True}
    )

    user_a, _ = User.objects.get_or_create(
        username=f"reports_seller_a_{uid}@test.com",
        defaults={
            "email": f"reports_seller_a_{uid}@test.com",
            "company": comp_a,
            "role": "seller",
            "is_staff": False,
            "is_superuser": False,
        }
    )
    if user_a.company != comp_a:
        user_a.company = comp_a
        user_a.save()

    user_b, _ = User.objects.get_or_create(
        username=f"reports_seller_b_{uid}@test.com",
        defaults={
            "email": f"reports_seller_b_{uid}@test.com",
            "company": comp_b,
            "role": "seller",
            "is_staff": False,
            "is_superuser": False,
        }
    )
    if user_b.company != comp_b:
        user_b.company = comp_b
        user_b.save()

    admin_user, _ = User.objects.get_or_create(
        username=f"reports_superadmin_{uid}@test.com",
        defaults={
            "email": f"reports_superadmin_{uid}@test.com",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True,
        }
    )

    # ── Test 1: Empty state reports for Seller B ──
    print("\n--- Test 1: Empty State Reports for Seller B ---")
    req = factory.get("/api/workforce/seller-hub/reports/summary/?days=30")
    force_authenticate(req, user=user_b)
    resp = SellerReportsSummaryView.as_view()(req)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    data_b = resp.data
    assert data_b["total_products_count"] == 0
    assert Decimal(str(data_b["fulfilled_order_gross_value"])) == Decimal("0.00")
    assert data_b["total_orders_count"] == 0
    assert data_b["catalog_quality_score"] == 100.0
    print("[PASS] Empty state returns clean zeroes without errors.")

    # ── Test 2: Seed Real Operational Data for Seller A ──
    print("\n--- Test 2: Seed Real Operational Data for Seller A ---")
    cat, _ = SellerHubCategory.objects.get_or_create(
        slug="cat-reports-test",
        defaults={"name": "Reports Test Category", "is_active": True}
    )

    # Product 1: Approved, in stock, fully compliant
    p1, _ = SellerProduct.objects.get_or_create(
        sku="REP-SKU-001",
        defaults={
            "company": comp_a,
            "category": cat,
            "title": "Fresh Organic Apples 1kg",
            "mrp": Decimal("150.00"),
            "selling_price": Decimal("120.00"),
            "status": "APPROVED",
            "description": "Premium organic apples rich in fiber.",
        }
    )
    SellerProductImage.objects.get_or_create(
        product=p1,
        image_url="https://example.com/apple.jpg",
        defaults={"is_primary": True}
    )

    # Product 2: Approved, zero stock, missing description
    p2, _ = SellerProduct.objects.get_or_create(
        sku="REP-SKU-002",
        defaults={
            "company": comp_a,
            "category": cat,
            "title": "Organic Bananas 500g",
            "mrp": Decimal("60.00"),
            "selling_price": Decimal("50.00"),
            "status": "APPROVED",
            "description": "",
        }
    )

    p3, _ = SellerProduct.objects.get_or_create(
        sku="REP-SKU-003",
        defaults={
            "company": comp_a,
            "category": cat,
            "title": "Alphonso Mangoes 1kg",
            "mrp": Decimal("500.00"),
            "selling_price": Decimal("400.00"),
            "status": "SUBMITTED",
            "description": "Alphonso mangoes direct from Ratnagiri farms.",
        }
    )
    p3.status = "SUBMITTED"
    p3.description = "Alphonso mangoes direct from Ratnagiri farms."
    p3.save()

    # Inventory & Batches for Product 1
    inv1, _ = SellerInventory.objects.get_or_create(
        product=p1,
        defaults={
            "company": comp_a,
            "on_hand_qty": Decimal("50.000"),
            "reserved_qty": Decimal("5.000"),
            "low_stock_threshold": Decimal("10.000"),
        }
    )
    inv1.on_hand_qty = Decimal("50.000")
    inv1.save()

    # Batch 1: Expiring in 10 days (< 30 days)
    b1, _ = SellerInventoryBatch.objects.get_or_create(
        inventory=inv1,
        batch_number="BATCH-REP-EXP10",
        defaults={
            "initial_quantity": Decimal("20.000"),
            "current_quantity": Decimal("20.000"),
            "expiry_date": date.today() + timedelta(days=10),
        }
    )

    # Batch 2: Expiring in 120 days
    b2, _ = SellerInventoryBatch.objects.get_or_create(
        inventory=inv1,
        batch_number="BATCH-REP-EXP120",
        defaults={
            "initial_quantity": Decimal("30.000"),
            "current_quantity": Decimal("30.000"),
            "expiry_date": date.today() + timedelta(days=120),
        }
    )

    # Inventory Movements
    SellerInventoryMovement.objects.get_or_create(
        inventory=inv1,
        movement_type="STOCK_IN",
        quantity_change=Decimal("50.000"),
        defaults={
            "balance_before": Decimal("0.000"),
            "balance_after": Decimal("50.000"),
            "reference_id": "PO-1001",
            "actor": user_a,
        }
    )
    SellerInventoryMovement.objects.get_or_create(
        inventory=inv1,
        movement_type="RETURN_RESTOCK",
        quantity_change=Decimal("2.000"),
        defaults={
            "balance_before": Decimal("48.000"),
            "balance_after": Decimal("50.000"),
            "reference_id": "RET-1001",
            "actor": user_a,
        }
    )

    # Orders for Seller A
    # Order 1: Delivered, Gross Value = 240.00
    ord1, _ = SellerOrder.objects.get_or_create(
        order_number="ORD-REP-001",
        defaults={
            "source_order_id": "SRC-ORD-REP-001",
            "company": comp_a,
            "status": "DELIVERED",
            "total_amount": Decimal("240.00"),
            "customer_name": "Rohan Sharma",
            "customer_phone": "+919876543210",
            "delivery_address": "123 Green Avenue, Bangalore",
            "delivered_at": timezone.now() - timedelta(days=1),
        }
    )
    # Order 2: In Preparation, Amount = 120.00
    ord2, _ = SellerOrder.objects.get_or_create(
        order_number="ORD-REP-002",
        defaults={
            "source_order_id": "SRC-ORD-REP-002",
            "company": comp_a,
            "status": "PICKING",
            "total_amount": Decimal("120.00"),
            "customer_name": "Priya Verma",
            "customer_phone": "+919876543211",
            "delivery_address": "456 Palm Grove, Bangalore",
        }
    )
    # Order 3: Cancelled, Amount = 100.00
    ord3, _ = SellerOrder.objects.get_or_create(
        order_number="ORD-REP-003",
        defaults={
            "source_order_id": "SRC-ORD-REP-003",
            "company": comp_a,
            "status": "CANCELLED",
            "total_amount": Decimal("100.00"),
            "customer_name": "Anil Kumar",
            "customer_phone": "+919876543212",
            "delivery_address": "789 Lake Road, Bangalore",
        }
    )

    # Returns for Seller A
    ret1, _ = SellerReturn.objects.get_or_create(
        return_number="RET-REP-001",
        defaults={
            "source_return_id": "SRC-RET-REP-001",
            "company": comp_a,
            "order": ord1,
            "status": "RESTOCKED",
            "quality_check_status": "PASSED",
            "reason": "DAMAGED",
            "customer_name": "Rohan Sharma",
        }
    )

    # Claims for Seller A
    claim1, _ = SellerClaim.objects.get_or_create(
        claim_number="CLM-REP-001",
        defaults={
            "source_claim_id": "SRC-CLM-REP-001",
            "company": comp_a,
            "order": ord1,
            "claim_type": "DAMAGED_ITEM",
            "status": "SELLER_RESPONSE_REQUIRED",
            "claimed_amount": Decimal("150.00"),
            "description": "Outer shipping box was crushed during transit",
        }
    )
    print("[PASS] Seeded real operational database records.")

    # ── Test 3: Validate SellerReportsSummaryView ──
    print("\n--- Test 3: Validate SellerReportsSummaryView ---")
    req = factory.get("/api/workforce/seller-hub/reports/summary/?days=30")
    force_authenticate(req, user=user_a)
    resp = SellerReportsSummaryView.as_view()(req)
    assert resp.status_code == 200
    summary = resp.data

    assert summary["total_products_count"] == 3, f"Expected 3, got {summary['total_products_count']}"
    assert summary["approved_products_count"] == 2, f"Expected 2, got {summary['approved_products_count']}"
    assert summary["pending_products_count"] == 1, f"Expected 1, got {summary['pending_products_count']}"
    assert summary["missing_images_count"] == 1, f"Expected 1, got {summary['missing_images_count']}"
    assert summary["missing_descriptions_count"] == 1, f"Expected 1, got {summary['missing_descriptions_count']}"

    assert summary["total_orders_count"] == 3, f"Expected 3, got {summary['total_orders_count']}"
    assert summary["delivered_orders_count"] == 1, f"Expected 1, got {summary['delivered_orders_count']}"
    assert Decimal(str(summary["fulfilled_order_gross_value"])) == Decimal("240.00"), f"Expected 240.00, got {summary['fulfilled_order_gross_value']}"

    assert summary["expiring_batches_count"] == 1, f"Expected 1, got {summary['expiring_batches_count']}"
    assert summary["total_returns_count"] == 1, f"Expected 1, got {summary['total_returns_count']}"
    assert summary["total_claims_count"] == 1, f"Expected 1, got {summary['total_claims_count']}"
    assert summary["claims_requiring_response_count"] == 1, f"Expected 1, got {summary['claims_requiring_response_count']}"

    print(f"[PASS] Summary KPIs verified: Catalog Quality: {summary['catalog_quality_score']}%, Fulfilled Value: INR {summary['fulfilled_order_gross_value']}, Expiring Batches: {summary['expiring_batches_count']}")

    # ── Test 4: Validate SellerReportsQualityAuditView ──
    print("\n--- Test 4: Validate SellerReportsQualityAuditView ---")
    req = factory.get("/api/workforce/seller-hub/reports/quality-audit/")
    force_authenticate(req, user=user_a)
    resp = SellerReportsQualityAuditView.as_view()(req)
    assert resp.status_code == 200
    audit = resp.data

    assert audit["missing_images_count"] == 1
    assert audit["expiring_batches_count"] == 1
    assert audit["claims_requiring_response_count"] == 1
    assert audit["total_issues_count"] >= 3
    print(f"[PASS] Quality Audit Checklist verified: {audit['total_issues_count']} actionable findings generated.")

    # ── Test 5: Validate SellerReportsExportCSVView ──
    print("\n--- Test 5: Validate SellerReportsExportCSVView ---")
    for report_type in ["orders", "inventory", "returns", "claims", "quality"]:
        req = factory.get(f"/api/workforce/seller-hub/reports/export-csv/?type={report_type}&days=30")
        force_authenticate(req, user=user_a)
        resp = SellerReportsExportCSVView.as_view()(req)
        assert resp.status_code == 200
        assert resp["Content-Type"] == "text/csv; charset=utf-8"
        assert f"sevo_seller_{report_type}_report" in resp["Content-Disposition"]
        content = resp.content.decode("utf-8")
        assert len(content) > 20, f"CSV content for {report_type} was empty"
        print(f"  [PASS] Exported {report_type} CSV successfully ({len(content)} bytes).")

    # ── Test 6: Platform Superadmin View ──
    print("\n--- Test 6: Platform Superadmin View ---")
    req = factory.get(f"/api/workforce/seller-hub/reports/summary/?days=30&company_id={comp_a.id}")
    force_authenticate(req, user=admin_user)
    resp = SellerReportsSummaryView.as_view()(req)
    assert resp.status_code == 200
    admin_summary = resp.data
    assert admin_summary["total_products_count"] == 3
    print("[PASS] Platform Superadmin successfully scoped reports to Seller A.")

    patch_post.stop()
    patch_dispatch.stop()

    print("\n" + "=" * 70)
    print(">>> ALL PHASE 7 REPORTS, QUALITY & PERFORMANCE CHECKS PASSED <<<")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
