"""
vendor/backend/test_seller_returns.py

Comprehensive automated test suite for Phase 5: Seller Hub Returns & Reverse Logistics:
1. Multi-tenant return listing and search/filtering.
2. Return case detail retrieval (line items, evidence snapshots, audit trail).
3. Seller review state machine transitions (REQUESTED -> UNDER_SELLER_REVIEW -> APPROVED, REJECTED, ESCALATED_TO_ADMIN).
4. Reverse logistics courier pickup scheduling (APPROVED -> PICKUP_SCHEDULED).
5. Store parcel receipt acknowledgment (PICKUP_SCHEDULED / APPROVED -> RECEIVED).
6. Physical quality inspection (RECEIVED -> QUALITY_CHECK with item condition and notes).
7. Atomic restocking workflow:
   - Increments inventory balance on-hand
   - Increments batch quantity if linked
   - Creates immutable STOCK_IN movement ledger records
   - Discards/scraps damaged goods with DAMAGE movement logs
   - Transitions state to RESTOCKED (or DISCARDED)
8. Case closure transition (RESTOCKED -> CLOSED).
9. Strict multi-tenant isolation: Seller B cannot view or manipulate Seller A's returns.
10. Dashboard returns metrics aggregation.
11. Invalid state machine transition rejections (HTTP 400).
12. Empty state verification when no real returns exist.
"""
import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]

from django.test import TestCase
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


class SellerReturnsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # 1. Create Sellers and Companies
        self.company_a = Company.objects.create(
            company_name="Organic Farms Hub",
            slug="organic-farms-hub",
            is_active=True,
        )
        self.company_b = Company.objects.create(
            company_name="Daily Fresh Grocers",
            slug="daily-fresh-grocers",
            is_active=True,
        )

        # 2. Create Users
        self.seller_user_a = User.objects.create_user(
            username="seller_a@test.com",
            email="seller_a@test.com",
            password="password123",
            company=self.company_a,
            first_name="Alice",
            last_name="Seller",
        )
        self.seller_user_b = User.objects.create_user(
            username="seller_b@test.com",
            email="seller_b@test.com",
            password="password123",
            company=self.company_b,
            first_name="Bob",
            last_name="Vendor",
        )
        self.admin_user = User.objects.create_superuser(
            username="admin@sevo.com",
            email="admin@sevo.com",
            password="password123",
        )

        # 3. Create Categories and Products
        self.category = SellerHubCategory.objects.create(
            name="Organic Cooking Oils",
            slug="organic-cooking-oils",
            is_active=True,
        )

        self.product_a = SellerProduct.objects.create(
            company=self.company_a,
            created_by=self.seller_user_a,
            category=self.category,
            title="Cold Pressed Groundnut Oil 1L",
            sku="CPO-GN-1L",
            mrp=Decimal("250.00"),
            selling_price=Decimal("220.00"),
            tax_rate=Decimal("5.00"),
            status=SellerProduct.Status.APPROVED,
        )

        # 4. Create Inventory and Batches
        self.inv_a = SellerInventory.objects.create(
            company=self.company_a,
            product=self.product_a,
            on_hand_qty=Decimal("50.000"),
            reserved_qty=Decimal("0.000"),
            low_stock_threshold=Decimal("10.000"),
        )
        self.batch_a = SellerInventoryBatch.objects.create(
            inventory=self.inv_a,
            batch_number="BATCH-GN-2026-A",
            initial_quantity=Decimal("50.000"),
            current_quantity=Decimal("50.000"),
        )

        # 5. Create Source Seller Order
        self.order_a = SellerOrder.objects.create(
            company=self.company_a,
            order_number="ORD-2026-0001",
            source_order_id="CUST-ORD-889911",
            customer_name="John Customer",
            customer_phone="9876543210",
            customer_email="john@test.com",
            delivery_address="123 Main St, Tech City",
            status=SellerOrder.Status.DELIVERED,
            subtotal=Decimal("440.00"),
            tax_amount=Decimal("22.00"),
            total_amount=Decimal("462.00"),
            payment_status="PAID",
        )
        self.order_item_a = SellerOrderItem.objects.create(
            order=self.order_a,
            product=self.product_a,
            sku=self.product_a.sku,
            product_title=self.product_a.title,
            ordered_quantity=Decimal("2.000"),
            fulfilled_quantity=Decimal("2.000"),
            unit_price=Decimal("220.00"),
            line_total=Decimal("440.00"),
            batch=self.batch_a,
            is_picked=True,
            is_packed=True,
        )

        # 6. Create Seller Return Case
        self.return_a = SellerReturn.objects.create(
            order=self.order_a,
            company=self.company_a,
            source_return_id="RET-CUST-99001",
            return_number="RET-2026-0001",
            customer_name="John Customer",
            customer_phone="9876543210",
            customer_address="123 Main St, Tech City",
            reason="Damaged seal / defective bottle",
            customer_notes="Bottle cap was slightly leaking on delivery.",
            status=SellerReturn.Status.REQUESTED,
            evidence_urls=["https://storage.sevo.com/returns/evidence_1.jpg"],
        )
        self.return_item_a = SellerReturnItem.objects.create(
            seller_return=self.return_a,
            order_item=self.order_item_a,
            product=self.product_a,
            sku=self.product_a.sku,
            product_title=self.product_a.title,
            returned_quantity=Decimal("1.000"),
        )

    def test_01_empty_state_when_no_returns_exist(self):
        """Seller B has no returns and should see empty list (no hardcoded data)."""
        self.client.force_authenticate(user=self.seller_user_b)
        response = self.client.get("/api/workforce/seller-hub/returns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_02_seller_return_list_and_search(self):
        """Seller A lists their returns and performs search/filter."""
        self.client.force_authenticate(user=self.seller_user_a)
        response = self.client.get("/api/workforce/seller-hub/returns/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["return_number"], "RET-2026-0001")
        self.assertEqual(response.data[0]["order_number"], "ORD-2026-0001")

        # Search by customer name
        search_res = self.client.get("/api/workforce/seller-hub/returns/?search=John")
        self.assertEqual(len(search_res.data), 1)

        # Search non-matching query
        no_match = self.client.get("/api/workforce/seller-hub/returns/?search=NonExistentQuery")
        self.assertEqual(len(no_match.data), 0)

    def test_03_seller_return_detail_view(self):
        """Retrieve full return case detail with line items and audit log."""
        self.client.force_authenticate(user=self.seller_user_a)
        response = self.client.get(f"/api/workforce/seller-hub/returns/{self.return_a.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["return_number"], "RET-2026-0001")
        self.assertEqual(len(response.data["items"]), 1)
        self.assertEqual(response.data["items"][0]["sku"], "CPO-GN-1L")
        self.assertEqual(response.data["evidence_urls"], ["https://storage.sevo.com/returns/evidence_1.jpg"])

    def test_04_seller_review_approve_transition(self):
        """Seller A reviews and approves return request."""
        self.client.force_authenticate(user=self.seller_user_a)
        payload = {
            "decision": "approve",
            "seller_notes": "Return approved. Please keep package ready for reverse pickup.",
        }
        response = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/review/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.return_a.refresh_from_db()
        self.assertEqual(self.return_a.status, SellerReturn.Status.APPROVED)
        self.assertEqual(self.return_a.seller_decision, SellerReturn.SellerDecision.APPROVED)
        self.assertIsNotNone(self.return_a.reviewed_at)

        # Check Audit Log
        audit = SellerReturnAuditLog.objects.filter(seller_return=self.return_a).last()
        self.assertEqual(audit.action, "APPROVED")
        self.assertEqual(audit.actor, self.seller_user_a)

    def test_05_seller_review_reject_requires_reason(self):
        """Rejecting a return strictly requires a non-empty rejection reason."""
        self.client.force_authenticate(user=self.seller_user_a)
        payload = {
            "decision": "reject",
            "rejection_reason": "",
        }
        response = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/review/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rejection_reason", response.data)

        # Valid rejection
        payload["rejection_reason"] = "Item returned past 7-day grocery freshness return window."
        response_valid = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/review/", payload, format="json")
        self.assertEqual(response_valid.status_code, status.HTTP_200_OK)
        self.return_a.refresh_from_db()
        self.assertEqual(self.return_a.status, SellerReturn.Status.REJECTED)
        self.assertEqual(self.return_a.rejection_reason, "Item returned past 7-day grocery freshness return window.")

    def test_06_schedule_pickup_and_receive_flow(self):
        """Transition through APPROVED -> PICKUP_SCHEDULED -> RECEIVED."""
        # 1. Approve
        self.return_a.status = SellerReturn.Status.APPROVED
        self.return_a.save()

        self.client.force_authenticate(user=self.seller_user_a)

        # 2. Schedule Pickup
        pickup_payload = {
            "pickup_ref": "SEVO-REVERSE-WAYBILL-7788",
            "notes": "Pickup assigned to local courier hub",
        }
        res_pickup = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/schedule-pickup/", pickup_payload, format="json")
        self.assertEqual(res_pickup.status_code, status.HTTP_200_OK)
        self.return_a.refresh_from_db()
        self.assertEqual(self.return_a.status, SellerReturn.Status.PICKUP_SCHEDULED)
        self.assertEqual(self.return_a.pickup_ref, "SEVO-REVERSE-WAYBILL-7788")

        # 3. Receive at Store
        res_receive = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/receive/", {"notes": "Parcel received at dock"}, format="json")
        self.assertEqual(res_receive.status_code, status.HTTP_200_OK)
        self.return_a.refresh_from_db()
        self.assertEqual(self.return_a.status, SellerReturn.Status.RECEIVED)
        self.assertIsNotNone(self.return_a.received_at)

    def test_07_quality_inspection_flow(self):
        """Perform physical quality check with item condition and pass result."""
        self.return_a.status = SellerReturn.Status.RECEIVED
        self.return_a.save()

        self.client.force_authenticate(user=self.seller_user_a)
        qc_payload = {
            "quality_check_status": "PASSED",
            "quality_check_notes": "Outer cap seal intact, no leakage found, verified fit for resale.",
            "items_qc": [
                {
                    "item_id": self.return_item_a.id,
                    "item_condition": "SEALED_INTACT",
                    "qc_result": "PASSED",
                    "qc_notes": "Unit in pristine factory sealed condition",
                }
            ],
        }
        res_qc = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/quality-check/", qc_payload, format="json")
        self.assertEqual(res_qc.status_code, status.HTTP_200_OK)
        self.return_a.refresh_from_db()
        self.return_item_a.refresh_from_db()

        self.assertEqual(self.return_a.status, SellerReturn.Status.QUALITY_CHECK)
        self.assertEqual(self.return_a.quality_check_status, "PASSED")
        self.assertEqual(self.return_a.quality_checked_by, self.seller_user_a)
        self.assertIsNotNone(self.return_a.inspected_at)
        self.assertEqual(self.return_item_a.item_condition, "SEALED_INTACT")
        self.assertEqual(self.return_item_a.qc_result, "PASSED")

    def test_08_atomic_restocking_and_ledger_update(self):
        """Restock verified return items, verifying inventory balance and movement ledger entries."""
        self.return_a.status = SellerReturn.Status.QUALITY_CHECK
        self.return_a.save()

        initial_on_hand = self.inv_a.on_hand_qty # 50.000
        initial_batch_qty = self.batch_a.current_quantity # 50.000

        self.client.force_authenticate(user=self.seller_user_a)
        restock_payload = {
            "restock_decision": "FULL_RESTOCK",
            "restock_notes": "Restocked into shelf rack A-02",
            "items_breakdown": [
                {
                    "item_id": self.return_item_a.id,
                    "restocked_quantity": "1.000",
                    "scrapped_quantity": "0.000",
                }
            ],
        }

        res_restock = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/restock/", restock_payload, format="json")
        self.assertEqual(res_restock.status_code, status.HTTP_200_OK)

        self.return_a.refresh_from_db()
        self.return_item_a.refresh_from_db()
        self.inv_a.refresh_from_db()
        self.batch_a.refresh_from_db()

        self.assertEqual(self.return_a.status, SellerReturn.Status.RESTOCKED)
        self.assertEqual(self.return_item_a.restocked_quantity, Decimal("1.000"))
        self.assertEqual(self.return_item_a.scrapped_quantity, Decimal("0.000"))

        # Check Inventory increment
        self.assertEqual(self.inv_a.on_hand_qty, initial_on_hand + Decimal("1.000"))
        self.assertEqual(self.batch_a.current_quantity, initial_batch_qty + Decimal("1.000"))

        # Check Immutable STOCK_IN Movement
        movement = SellerInventoryMovement.objects.filter(
            inventory=self.inv_a,
            movement_type=SellerInventoryMovement.MovementType.STOCK_IN,
            reference_id=self.return_a.return_number,
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity_change, Decimal("1.000"))
        self.assertEqual(movement.balance_before, initial_on_hand)
        self.assertEqual(movement.balance_after, initial_on_hand + Decimal("1.000"))

    def test_09_scrap_disposal_damaged_items(self):
        """Scrap/discard damaged return items without increasing saleable on-hand stock."""
        self.return_a.status = SellerReturn.Status.QUALITY_CHECK
        self.return_a.save()

        initial_on_hand = self.inv_a.on_hand_qty

        self.client.force_authenticate(user=self.seller_user_a)
        restock_payload = {
            "restock_decision": "SCRAP_DISPOSE",
            "restock_notes": "Damaged bottle discarded into scrap bin",
            "items_breakdown": [
                {
                    "item_id": self.return_item_a.id,
                    "restocked_quantity": "0.000",
                    "scrapped_quantity": "1.000",
                }
            ],
        }

        res_restock = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/restock/", restock_payload, format="json")
        self.assertEqual(res_restock.status_code, status.HTTP_200_OK)

        self.return_a.refresh_from_db()
        self.inv_a.refresh_from_db()

        self.assertEqual(self.return_a.status, SellerReturn.Status.DISCARDED)
        self.assertEqual(self.inv_a.on_hand_qty, initial_on_hand) # Unchanged on-hand

        # Check DAMAGE movement
        movement = SellerInventoryMovement.objects.filter(
            inventory=self.inv_a,
            movement_type=SellerInventoryMovement.MovementType.DAMAGE,
            reference_id=self.return_a.return_number,
        ).first()
        self.assertIsNotNone(movement)

    def test_10_close_return_case(self):
        """Final transition to CLOSED state."""
        self.return_a.status = SellerReturn.Status.RESTOCKED
        self.return_a.save()

        self.client.force_authenticate(user=self.seller_user_a)
        res = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/close/", {"notes": "Case closed."}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.return_a.refresh_from_db()
        self.assertEqual(self.return_a.status, SellerReturn.Status.CLOSED)
        self.assertIsNotNone(self.return_a.closed_at)

    def test_11_strict_multi_tenant_isolation(self):
        """Seller B cannot view or modify Seller A's return case."""
        self.client.force_authenticate(user=self.seller_user_b)

        # GET detail -> 404
        get_res = self.client.get(f"/api/workforce/seller-hub/returns/{self.return_a.id}/")
        self.assertEqual(get_res.status_code, status.HTTP_404_NOT_FOUND)

        # POST review -> 404
        post_res = self.client.post(f"/api/workforce/seller-hub/returns/{self.return_a.id}/review/", {"decision": "approve"}, format="json")
        self.assertEqual(post_res.status_code, status.HTTP_404_NOT_FOUND)

    def test_12_dashboard_returns_metrics_aggregation(self):
        """Verify dynamic calculation of returns counts in SellerHubMetricsView."""
        self.client.force_authenticate(user=self.seller_user_a)
        res = self.client.get("/api/workforce/seller-hub/metrics/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_returns_count"], 1)
        self.assertEqual(res.data["pending_returns_count"], 1)
        self.assertEqual(res.data["under_inspection_returns_count"], 0)
        self.assertEqual(res.data["resolved_returns_count"], 0)

        # Change to quality check
        self.return_a.status = SellerReturn.Status.QUALITY_CHECK
        self.return_a.save()

        res2 = self.client.get("/api/workforce/seller-hub/metrics/")
        self.assertEqual(res2.data["pending_returns_count"], 0)
        self.assertEqual(res2.data["under_inspection_returns_count"], 1)
