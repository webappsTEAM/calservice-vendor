"""
vendor/backend/run_returns_verification.py

Comprehensive End-to-End Test Suite for Phase 5 (Seller Hub Returns Correction: Return-Restock Audit Accuracy):
1. Empty state for seller with no returns (clean empty array, no mock data).
2. Create seller return and test list/search/filtering.
3. Return detail with line items, SKU snapshots, and photo evidence URLs.
4. Seller review with mandatory rejection reason validation and approve transition.
5. Pickup scheduling with tracking ref and parcel arrival acknowledgment.
6. Physical quality check inspection with item condition and inspecting actor logging.
7. Sellable return creates exactly one RETURN_RESTOCK movement:
   - On-hand inventory atomically incremented.
   - Batch quantity atomically incremented.
   - Dedicated movement_type == 'RETURN_RESTOCK' (NOT 'STOCK_IN').
   - Contains compound reference with Return # and Order #.
   - Reason documents Return #, Order #, QC status, Return reason, and notes.
8. Supplier stock receipt remains STOCK_IN (verified via inventory adjustment/stock-in).
9. Damaged, expired, opened, missing, or unsellable returned items create DAMAGE movement and NEVER create RETURN_RESTOCK.
10. Idempotency against retries: Repeated restock action on already restocked return is blocked (HTTP 400) and does not duplicate inventory or movements.
11. Source return reference idempotency: Repeated intake of the same source_return_id returns existing SellerReturn (created=False, HTTP 200).
12. Close return case transition.
13. Strict multi-tenant isolation (Seller B blocked with HTTP 404 from viewing or altering Seller A's returns).
14. Dashboard returns metrics accuracy.
"""
import os
import sys
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
settings.ALLOWED_HOSTS = ["*"]

from django.db import transaction
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from companies.models import Company
from workforce_api.models import (
    SellerHubCategory,
    SellerProduct,
    SellerInventory,
    SellerInventoryBatch,
    SellerInventoryMovement,
    SellerOrder,
    SellerOrderItem,
    SellerReturn,
    SellerReturnItem,
    SellerReturnAuditLog,
)

User = get_user_model()
client = APIClient()

print("=" * 80)
print("SEVO-VENDOR PHASE 5: RETURN-RESTOCK AUDIT ACCURACY VERIFICATION")
print("=" * 80)

passed = 0
failed = 0

def assert_true(expr, msg):
    global passed, failed
    if expr:
        print(f"  [PASS] {msg}")
        passed += 1
    else:
        print(f"  [FAIL] {msg}")
        failed += 1

try:
    with transaction.atomic():
        # 1. Setup Test Companies and Users
        company_a, _ = Company.objects.get_or_create(
            slug="test-returns-company-a",
            defaults={"company_name": "Test Returns Seller A", "is_active": True}
        )
        company_b, _ = Company.objects.get_or_create(
            slug="test-returns-company-b",
            defaults={"company_name": "Test Returns Seller B", "is_active": True}
        )

        user_a, _ = User.objects.get_or_create(
            username="seller_returns_a@test.com",
            defaults={"email": "seller_returns_a@test.com", "company": company_a, "first_name": "Alice"}
        )
        user_a.company = company_a
        user_a.save()

        user_b, _ = User.objects.get_or_create(
            username="seller_returns_b@test.com",
            defaults={"email": "seller_returns_b@test.com", "company": company_b, "first_name": "Bob"}
        )
        user_b.company = company_b
        user_b.save()

        # 2. Category & Product
        category, _ = SellerHubCategory.objects.get_or_create(
            slug="returns-test-category",
            defaults={"name": "Returns Test Category", "is_active": True}
        )
        product_a, _ = SellerProduct.objects.get_or_create(
            sku="RET-PROD-001",
            company=company_a,
            defaults={
                "title": "Organic Almond Milk 1L",
                "category": category,
                "created_by": user_a,
                "mrp": Decimal("280.00"),
                "selling_price": Decimal("250.00"),
                "status": SellerProduct.Status.APPROVED,
            }
        )

        # 3. Inventory & Batch
        inv_a, _ = SellerInventory.objects.get_or_create(
            company=company_a,
            product=product_a,
            defaults={
                "on_hand_qty": Decimal("100.000"),
                "reserved_qty": Decimal("0.000"),
                "low_stock_threshold": Decimal("15.000"),
            }
        )
        inv_a.on_hand_qty = Decimal("100.000")
        inv_a.reserved_qty = Decimal("0.000")
        inv_a.save()

        batch_a, _ = SellerInventoryBatch.objects.get_or_create(
            inventory=inv_a,
            batch_number="BATCH-RET-TEST-01",
            defaults={
                "initial_quantity": Decimal("100.000"),
                "current_quantity": Decimal("100.000"),
            }
        )
        batch_a.current_quantity = Decimal("100.000")
        batch_a.save()

        # 4. Source Order
        order_a, _ = SellerOrder.objects.get_or_create(
            order_number="RET-TEST-ORD-01",
            company=company_a,
            defaults={
                "source_order_id": "CUST-ORD-RET-99",
                "customer_name": "Priya Sharma",
                "customer_phone": "9876543210",
                "delivery_address": "Flat 402, Green Meadows",
                "status": SellerOrder.Status.DELIVERED,
                "total_amount": Decimal("525.00"),
                "payment_status": "PAID",
            }
        )
        order_item_a, _ = SellerOrderItem.objects.get_or_create(
            order=order_a,
            sku=product_a.sku,
            defaults={
                "product": product_a,
                "product_title": product_a.title,
                "ordered_quantity": Decimal("2.000"),
                "fulfilled_quantity": Decimal("2.000"),
                "unit_price": Decimal("250.00"),
                "line_total": Decimal("500.00"),
                "batch": batch_a,
                "is_picked": True,
                "is_packed": True,
            }
        )

        # 5. Clean prior returns for isolation
        SellerReturn.objects.filter(company__in=[company_a, company_b]).delete()

        print("\n--- TEST 1: EMPTY STATE FOR SELLER WITH NO RETURNS ---")
        client.force_authenticate(user=user_b)
        res_empty = client.get("/api/workforce/seller-hub/returns/")
        assert_true(res_empty.status_code == status.HTTP_200_OK and len(res_empty.data) == 0,
                    "Seller B with no returns receives an empty array with HTTP 200 (no mock returns)")

        print("\n--- TEST 2: CREATE SELLER RETURN AND TEST LIST / SEARCH ---")
        return_a = SellerReturn.objects.create(
            order=order_a,
            company=company_a,
            source_return_id="RET-SRC-9001",
            return_number="RET-2026-0001",
            customer_name="Priya Sharma",
            customer_phone="9876543210",
            customer_address="Flat 402, Green Meadows",
            reason="Damaged item seal upon delivery",
            customer_notes="Bottle seal was slightly torn in transit.",
            status=SellerReturn.Status.REQUESTED,
            evidence_urls=["https://storage.sevo.com/returns/sample_evidence.jpg"],
        )
        return_item_a = SellerReturnItem.objects.create(
            return_case=return_a,
            order_item=order_item_a,
            product=product_a,
            sku=product_a.sku,
            product_title=product_a.title,
            returned_quantity=Decimal("1.000"),
        )

        client.force_authenticate(user=user_a)
        res_list = client.get("/api/workforce/seller-hub/returns/")
        assert_true(res_list.status_code == status.HTTP_200_OK and len(res_list.data) == 1,
                    "Seller A lists their returns successfully")
        assert_true(res_list.data[0]["return_number"] == "RET-2026-0001",
                    "Return number matches created record")

        # Search matching
        res_search = client.get("/api/workforce/seller-hub/returns/?search=Priya")
        assert_true(len(res_search.data) == 1, "Search by customer name matches")
        res_no_match = client.get("/api/workforce/seller-hub/returns/?search=NonExistent123")
        assert_true(len(res_no_match.data) == 0, "Non-matching search returns empty list")

        print("\n--- TEST 3: RETURN DETAIL WITH ITEMS AND EVIDENCE ---")
        res_detail = client.get(f"/api/workforce/seller-hub/returns/{return_a.id}/")
        assert_true(res_detail.status_code == status.HTTP_200_OK, "Detail view returns HTTP 200")
        assert_true(len(res_detail.data["items"]) == 1, "Detail includes line items list")
        assert_true(res_detail.data["items"][0]["sku"] == "RET-PROD-001", "Line item contains correct product SKU")
        assert_true(res_detail.data["evidence_urls"] == ["https://storage.sevo.com/returns/sample_evidence.jpg"],
                    "Submitted photo evidence URLs are preserved")

        print("\n--- TEST 4: SELLER REVIEW (APPROVE / REJECT REASON VALIDATION) ---")
        # Reject without reason -> 400
        res_bad_reject = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/review/", {
            "decision": "reject",
            "rejection_reason": "",
        }, format="json")
        assert_true(res_bad_reject.status_code == status.HTTP_400_BAD_REQUEST,
                    "Rejection without mandatory rejection_reason is blocked with HTTP 400")

        # Valid Approve
        res_approve = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/review/", {
            "decision": "approve",
            "seller_notes": "Approved for return pickup.",
        }, format="json")
        assert_true(res_approve.status_code == status.HTTP_200_OK, "Review decision APPROVE succeeds with HTTP 200")
        return_a.refresh_from_db()
        assert_true(return_a.status == SellerReturn.Status.APPROVED, "Return status transitioned to APPROVED")
        assert_true(return_a.seller_decision == "APPROVED", "Seller decision recorded as APPROVED")
        assert_true(return_a.reviewed_at is not None, "reviewed_at timestamp is set")

        audit_review = SellerReturnAuditLog.objects.filter(return_case=return_a).last()
        assert_true(audit_review is not None and audit_review.action == "APPROVED", "Audit log created for APPROVE")

        print("\n--- TEST 5: PICKUP SCHEDULE & RECEIVE AT STORE ---")
        res_pickup = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/schedule-pickup/", {
            "pickup_ref": "SEVO-RIDER-PKP-101",
            "notes": "Assigned to driver",
        }, format="json")
        assert_true(res_pickup.status_code == status.HTTP_200_OK, "Pickup scheduling succeeds with HTTP 200")
        return_a.refresh_from_db()
        assert_true(return_a.status == SellerReturn.Status.PICKUP_SCHEDULED, "Status is PICKUP_SCHEDULED")
        assert_true(return_a.pickup_ref == "SEVO-RIDER-PKP-101", "Pickup ref is persisted")

        res_receive = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/receive/", {
            "notes": "Delivered to warehouse dock A",
        }, format="json")
        assert_true(res_receive.status_code == status.HTTP_200_OK, "Package receipt acknowledgment succeeds")
        return_a.refresh_from_db()
        assert_true(return_a.status == SellerReturn.Status.RECEIVED, "Status is RECEIVED")
        assert_true(return_a.received_at is not None, "received_at timestamp is populated")

        print("\n--- TEST 6: PHYSICAL QUALITY INSPECTION (QC) ---")
        qc_payload = {
            "quality_check_status": "PASSED",
            "quality_check_notes": "Bottle seal intact, suitable for restock.",
            "items_qc": [
                {
                    "item_id": return_item_a.id,
                    "item_condition": "SEALED_INTACT",
                    "qc_result": "PASSED",
                    "qc_notes": "Pristine condition",
                }
            ],
        }
        res_qc = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/quality-check/", qc_payload, format="json")
        assert_true(res_qc.status_code == status.HTTP_200_OK, "Quality check inspection succeeds with HTTP 200")
        return_a.refresh_from_db()
        return_item_a.refresh_from_db()
        assert_true(return_a.status == SellerReturn.Status.QUALITY_CHECK, "Status transitioned to QUALITY_CHECK")
        assert_true(return_a.quality_check_status == "PASSED", "quality_check_status is PASSED")
        assert_true(return_a.quality_checked_by == user_a, "quality_checked_by records inspecting user")
        assert_true(return_item_a.item_condition == "SEALED_INTACT", "Item condition updated to SEALED_INTACT")

        print("\n--- TEST 7: SELLABLE RETURN CREATES EXACTLY ONE RETURN_RESTOCK MOVEMENT ---")
        initial_on_hand = inv_a.on_hand_qty # 100.000
        initial_batch_qty = batch_a.current_quantity # 100.000

        restock_payload = {
            "restock_decision": "FULL_RESTOCK",
            "restock_notes": "Restocked into shelf rack A-02",
            "items_breakdown": [
                {
                    "item_id": return_item_a.id,
                    "restocked_quantity": "1.000",
                    "scrapped_quantity": "0.000",
                }
            ],
        }
        res_restock = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/restock/", restock_payload, format="json")
        assert_true(res_restock.status_code == status.HTTP_200_OK, "Restock execution succeeds with HTTP 200")

        return_a.refresh_from_db()
        return_item_a.refresh_from_db()
        inv_a.refresh_from_db()
        batch_a.refresh_from_db()

        assert_true(return_a.status == SellerReturn.Status.RESTOCKED, "Status transitioned to RESTOCKED")
        assert_true(return_item_a.restocked_quantity == Decimal("1.000"), "Restocked quantity recorded as 1.000")
        assert_true(inv_a.on_hand_qty == initial_on_hand + Decimal("1.000"),
                    f"Inventory on_hand_qty atomically incremented ({initial_on_hand} -> {inv_a.on_hand_qty})")
        assert_true(batch_a.current_quantity == initial_batch_qty + Decimal("1.000"),
                    f"Batch quantity atomically incremented ({initial_batch_qty} -> {batch_a.current_quantity})")

        # Verify dedicated RETURN_RESTOCK movement
        movements = SellerInventoryMovement.objects.filter(
            inventory=inv_a,
            reference_id__contains=return_a.return_number,
        )
        assert_true(movements.count() == 1, "Exactly ONE inventory movement created for this return restock")
        restock_mov = movements.first()
        assert_true(restock_mov.movement_type == SellerInventoryMovement.MovementType.RETURN_RESTOCK,
                    f"Movement type is RETURN_RESTOCK (got '{restock_mov.movement_type}'), NOT STOCK_IN")
        assert_true(restock_mov.quantity_change == Decimal("1.000"), "Movement quantity change is +1.000")
        assert_true(restock_mov.balance_before == initial_on_hand and restock_mov.balance_after == initial_on_hand + Decimal("1.000"),
                    "Movement balance before and after accurately recorded")
        assert_true(return_a.return_number in restock_mov.reference_id and order_a.order_number in restock_mov.reference_id,
                    f"reference_id contains both Return # and Order # ('{restock_mov.reference_id}')")
        assert_true("QC: PASSED" in restock_mov.reason and return_a.reason in restock_mov.reason,
                    f"Movement reason preserves QC status and return reason ('{restock_mov.reason}')")

        print("\n--- TEST 8: SUPPLIER STOCK RECEIPT REMAINS STOCK_IN ---")
        # Perform supplier stock-in adjustment
        res_supplier_stock = client.post(f"/api/workforce/seller-hub/inventory/{inv_a.id}/adjust/", {
            "movement_type": "STOCK_IN",
            "quantity": "25.000",
            "reason": "Supplier shipment PO-9988 received from warehouse distributor",
            "reference_id": "PO-9988",
        }, format="json")
        assert_true(res_supplier_stock.status_code == status.HTTP_200_OK, "Supplier stock adjustment succeeds")
        supplier_mov = SellerInventoryMovement.objects.filter(inventory=inv_a, reference_id="PO-9988").first()
        assert_true(supplier_mov is not None and supplier_mov.movement_type == SellerInventoryMovement.MovementType.STOCK_IN,
                    f"Genuine supplier/purchase stock receipt correctly uses STOCK_IN (got '{supplier_mov.movement_type}')")

        print("\n--- TEST 9: UNSELLABLE / DAMAGED ITEMS CREATE DAMAGE MOVEMENT, NEVER RETURN_RESTOCK ---")
        # Create second return for damaged item
        return_damaged = SellerReturn.objects.create(
            order=order_a,
            company=company_a,
            source_return_id="RET-SRC-DAMAGED-9002",
            return_number="RET-2026-0002",
            customer_name="Priya Sharma",
            customer_phone="9876543210",
            reason="EXPIRED",
            status=SellerReturn.Status.QUALITY_CHECK,
            quality_check_status="FAILED",
            quality_check_notes="Product expired and pack leaking. Unfit for resale.",
        )
        return_item_damaged = SellerReturnItem.objects.create(
            return_case=return_damaged,
            order_item=order_item_a,
            product=product_a,
            sku=product_a.sku,
            product_title=product_a.title,
            returned_quantity=Decimal("1.000"),
            item_condition="EXPIRED",
            qc_result="FAILED",
        )

        inv_a.refresh_from_db()
        curr_on_hand = inv_a.on_hand_qty
        res_scrap = client.post(f"/api/workforce/seller-hub/returns/{return_damaged.id}/restock/", {
            "restock_decision": "SCRAP_DISPOSE",
            "restock_notes": "Expired product discarded into scrap bin",
            "items_breakdown": [
                {
                    "item_id": return_item_damaged.id,
                    "restocked_quantity": "0.000",
                    "scrapped_quantity": "1.000",
                }
            ],
        }, format="json")
        assert_true(res_scrap.status_code == status.HTTP_200_OK, "Scrap disposal execution succeeds")
        inv_a.refresh_from_db()
        return_damaged.refresh_from_db()

        assert_true(return_damaged.status == SellerReturn.Status.DISCARDED, "Status transitioned to DISCARDED")
        assert_true(inv_a.on_hand_qty == curr_on_hand, f"On-hand stock is unchanged for scrapped items ({curr_on_hand})")

        # Verify NO RETURN_RESTOCK movement was created
        has_return_restock_for_damaged = SellerInventoryMovement.objects.filter(
            inventory=inv_a,
            movement_type=SellerInventoryMovement.MovementType.RETURN_RESTOCK,
            reference_id__contains=return_damaged.return_number,
        ).exists()
        assert_true(not has_return_restock_for_damaged, "Damaged/unsellable goods NEVER create a RETURN_RESTOCK movement")

        damage_mov = SellerInventoryMovement.objects.filter(
            inventory=inv_a,
            movement_type=SellerInventoryMovement.MovementType.DAMAGE,
            reference_id__contains=return_damaged.return_number,
        ).first()
        assert_true(damage_mov is not None, "Damaged returned item correctly creates DAMAGE disposal movement")

        print("\n--- TEST 10: IDEMPOTENCY: REPEATED RESTOCK ACTION BLOCKED FROM DUPLICATING STOCK ---")
        # Attempt to restock return_a a second time
        bal_before_retry = inv_a.on_hand_qty
        res_retry = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/restock/", restock_payload, format="json")
        assert_true(res_retry.status_code == status.HTTP_400_BAD_REQUEST,
                    "Retrying restock on an already restocked return is blocked with HTTP 400")
        inv_a.refresh_from_db()
        assert_true(inv_a.on_hand_qty == bal_before_retry,
                    f"Inventory balance remained completely unchanged ({bal_before_retry}) — no double counting")

        print("\n--- TEST 11: SOURCE RETURN REFERENCE IDEMPOTENCY ---")
        # 1st Intake call
        intake_payload = {
            "source_return_id": "CANONICAL-CUST-RET-9900",
            "source_order_id": "CUST-ORD-RET-99",
            "reason": "DEFECTIVE",
            "customer_notes": "Defective pump nozzle",
            "evidence_urls": ["https://storage.sevo.com/returns/defective_nozzle.jpg"],
            "items": [
                {
                    "sku": product_a.sku,
                    "returned_quantity": "1.000",
                }
            ],
        }
        res_intake_1 = client.post("/api/workforce/seller-hub/returns/intake/", intake_payload, format="json")
        assert_true(res_intake_1.status_code == status.HTTP_201_CREATED and res_intake_1.data["created"] is True,
                    "First intake call creates SellerReturn with HTTP 201 (created=True)")
        first_id = res_intake_1.data["return"]["id"]

        # 2nd Intake call (Duplicate retry with identical source_return_id)
        res_intake_2 = client.post("/api/workforce/seller-hub/returns/intake/", intake_payload, format="json")
        assert_true(res_intake_2.status_code == status.HTTP_200_OK and res_intake_2.data["created"] is False,
                    "Second intake call with identical source_return_id returns existing return with HTTP 200 (created=False)")
        assert_true(res_intake_2.data["return"]["id"] == first_id,
                    "Returned record ID matches the original intake record (no duplicate created)")

        # Verify DB has exactly one row for this source_return_id
        db_count = SellerReturn.objects.filter(source_return_id="CANONICAL-CUST-RET-9900").count()
        assert_true(db_count == 1, f"Database contains exactly 1 SellerReturn for source_return_id (count={db_count})")

        print("\n--- TEST 12: CLOSE RETURN CASE ---")
        res_close = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/close/", {"notes": "All done."}, format="json")
        assert_true(res_close.status_code == status.HTTP_200_OK, "Close return case succeeds with HTTP 200")
        return_a.refresh_from_db()
        assert_true(return_a.status == SellerReturn.Status.CLOSED, "Status transitioned to CLOSED")
        assert_true(return_a.closed_at is not None, "closed_at timestamp recorded")

        print("\n--- TEST 13: MULTI-TENANT ISOLATION ---")
        client.force_authenticate(user=user_b)
        res_b_view = client.get(f"/api/workforce/seller-hub/returns/{return_a.id}/")
        assert_true(res_b_view.status_code == status.HTTP_404_NOT_FOUND,
                    "Seller B cannot view Seller A's return case (HTTP 404)")

        res_b_action = client.post(f"/api/workforce/seller-hub/returns/{return_a.id}/review/", {"decision": "approve"}, format="json")
        assert_true(res_b_action.status_code == status.HTTP_404_NOT_FOUND,
                    "Seller B cannot perform action on Seller A's return case (HTTP 404)")

        print("\n--- TEST 14: SELLER HUB DASHBOARD RETURNS METRICS ---")
        client.force_authenticate(user=user_a)
        res_metrics = client.get("/api/workforce/seller-hub/metrics/")
        assert_true(res_metrics.status_code == status.HTTP_200_OK, "Seller metrics returns HTTP 200")
        assert_true(res_metrics.data["total_returns_count"] == 3, "total_returns_count is 3")
        assert_true(res_metrics.data["resolved_returns_count"] == 2, "resolved_returns_count is 2 (CLOSED & DISCARDED)")
        assert_true(res_metrics.data["pending_returns_count"] == 1, "pending_returns_count is 1 (intake case)")

        # Rollback all test data cleanly
        raise Exception("ROLLBACK_TRANSACTION_CLEAN")

except Exception as e:
    if "ROLLBACK_TRANSACTION_CLEAN" not in str(e):
        print(f"\n[ERROR] Unexpected test exception: {e}")
        import traceback
        traceback.print_exc()
        failed += 1

print("\n" + "=" * 80)
print(f"VERIFICATION SUMMARY: {passed} PASSED, {failed} FAILED")
print("=" * 80)

if failed > 0:
    sys.exit(1)
else:
    sys.exit(0)
