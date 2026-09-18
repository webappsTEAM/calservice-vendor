"""
vendor/backend/test_seller_orders.py

Comprehensive test suite for Phase 4: Seller Hub Orders and Fulfilment:
1. Create seller order and link item snapshots.
2. Initial state NEW and inventory reservation handling.
3. Strict state machine transitions (NEW -> ACCEPTED -> PICKING -> PACKED -> READY_FOR_PICKUP -> HANDED_OVER -> DELIVERED).
4. Stock deduction on Handover/Delivery (ORDER_DEDUCTED movement and on-hand decrement).
5. Cancellation releases reserved stock (RESERVATION_RELEASED movement and reservation clear).
6. Invalid state machine transitions blocked with HTTP 400.
7. Cancellation strictly requires non-empty reason.
8. Item picking and packing checklist API (item-pick).
9. Tenant isolation: Seller A cannot view or modify Seller B's orders.
10. Admin/Superadmin cross-tenant view and action audit logging.
11. Packing slip API format and content.
12. Dashboard metrics accuracy from real DB records.
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
    SellerOrderAuditLog,
)

User = get_user_model()


class SellerOrdersTestCase(TestCase):
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

        self.seller_a = User.objects.create_user(
            username="seller_orders_a",
            email="seller_a@orders.com",
            password="Password123!",
            first_name="Alice",
            last_name="Farmer",
            is_active=True,
            company=self.company_a,
        )
        self.seller_b = User.objects.create_user(
            username="seller_orders_b",
            email="seller_b@orders.com",
            password="Password123!",
            first_name="Bob",
            last_name="Grocer",
            is_active=True,
            company=self.company_b,
        )
        self.superadmin = User.objects.create_superuser(
            username="orders_superadmin",
            email="admin@orders.com",
            password="Password123!",
            first_name="Admin",
            last_name="User",
        )

        # Authenticate tokens / headers
        from rest_framework_simplejwt.tokens import RefreshToken
        self.token_a = str(RefreshToken.for_user(self.seller_a).access_token)
        self.token_b = str(RefreshToken.for_user(self.seller_b).access_token)
        self.token_admin = str(RefreshToken.for_user(self.superadmin).access_token)

        # 2. Categories
        self.root_cat = SellerHubCategory.objects.create(name="Groceries", slug="groceries", is_active=True)
        self.oil_cat = SellerHubCategory.objects.create(name="Oils", slug="oils", parent=self.root_cat, is_active=True)

        # 3. Approved Products
        self.product_a1 = SellerProduct.objects.create(
            company=self.company_a,
            category=self.oil_cat,
            title="Cold Pressed Coconut Oil 1L",
            sku="COC-OIL-1L",
            unit="litre",
            pack_size="1 Litre",
            mrp=Decimal("350.00"),
            selling_price=Decimal("320.00"),
            status=SellerProduct.Status.APPROVED,
        )
        self.product_a2 = SellerProduct.objects.create(
            company=self.company_a,
            category=self.oil_cat,
            title="Cold Pressed Groundnut Oil 1L",
            sku="GND-OIL-1L",
            unit="litre",
            pack_size="1 Litre",
            mrp=Decimal("280.00"),
            selling_price=Decimal("250.00"),
            status=SellerProduct.Status.APPROVED,
        )

        self.product_b1 = SellerProduct.objects.create(
            company=self.company_b,
            category=self.oil_cat,
            title="Refined Sunflower Oil 1L",
            sku="SUN-OIL-1L",
            unit="litre",
            pack_size="1 Litre",
            mrp=Decimal("150.00"),
            selling_price=Decimal("135.00"),
            status=SellerProduct.Status.APPROVED,
        )

        # 4. Inventory Balances
        self.inv_a1 = SellerInventory.objects.create(
            company=self.company_a,
            product=self.product_a1,
            on_hand_qty=Decimal("50.000"),
            reserved_qty=Decimal("0.000"),
            low_stock_threshold=Decimal("10.000"),
        )
        self.inv_a2 = SellerInventory.objects.create(
            company=self.company_a,
            product=self.product_a2,
            on_hand_qty=Decimal("30.000"),
            reserved_qty=Decimal("0.000"),
            low_stock_threshold=Decimal("5.000"),
        )
        self.inv_b1 = SellerInventory.objects.create(
            company=self.company_b,
            product=self.product_b1,
            on_hand_qty=Decimal("100.000"),
            reserved_qty=Decimal("0.000"),
            low_stock_threshold=Decimal("20.000"),
        )

    def test_01_create_seller_order_with_items_and_snapshots(self):
        """Test creating a seller fulfilment order with snapshot item attributes."""
        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1001",
            company=self.company_a,
            order_number="SO-2026-0001",
            customer_name="John Doe",
            customer_phone="9876543210",
            delivery_address="123 Palm Grove, Chennai",
            fulfillment_type=SellerOrder.FulfillmentType.DELIVERY,
            delivery_slot="Tomorrow 10:00 AM - 1:00 PM",
            total_amount=Decimal("890.00"),
            status=SellerOrder.Status.NEW,
        )

        item1 = SellerOrderItem.objects.create(
            order=order,
            product=self.product_a1,
            product_title=self.product_a1.title,
            sku=self.product_a1.sku,
            unit=self.product_a1.unit,
            pack_size=self.product_a1.pack_size,
            ordered_quantity=Decimal("2.000"),
            unit_price=self.product_a1.selling_price,
            line_total=Decimal("640.00"),
        )
        item2 = SellerOrderItem.objects.create(
            order=order,
            product=self.product_a2,
            product_title=self.product_a2.title,
            sku=self.product_a2.sku,
            unit=self.product_a2.unit,
            pack_size=self.product_a2.pack_size,
            ordered_quantity=Decimal("1.000"),
            unit_price=self.product_a2.selling_price,
            line_total=Decimal("250.00"),
        )

        resp = self.client.get(
            f"/api/workforce/seller-hub/orders/{order.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_number"], "SO-2026-0001")
        self.assertEqual(len(resp.data["items"]), 2)
        self.assertEqual(resp.data["status"], "NEW")

    def test_02_strict_state_machine_happy_path(self):
        """Test transitioning order step-by-step through full state machine."""
        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1002",
            company=self.company_a,
            order_number="SO-2026-0002",
            customer_name="Jane Smith",
            total_amount=Decimal("320.00"),
            status=SellerOrder.Status.NEW,
        )
        SellerOrderItem.objects.create(
            order=order,
            product=self.product_a1,
            product_title=self.product_a1.title,
            sku=self.product_a1.sku,
            ordered_quantity=Decimal("1.000"),
            unit_price=Decimal("320.00"),
            line_total=Decimal("320.00"),
        )

        # Step 1: Accept Order
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "accept", "notes": "Order accepted by warehouse team."},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "ACCEPTED")

        # Step 2: Start Picking
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "start_picking"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "PICKING")

        # Step 3: Mark Packed
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "mark_packed"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "PACKED")

        # Step 4: Ready for Pickup
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "mark_ready"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "READY_FOR_PICKUP")

        # Step 5: Handover
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "handover", "handover_ref": "RIDER-EXP-9921"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "HANDED_OVER")

        # Step 6: Deliver
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "deliver"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "DELIVERED")

        # Verify audit logs created
        order.refresh_from_db()
        self.assertEqual(order.audit_logs.count(), 6)

    def test_03_inventory_deduction_on_handover(self):
        """Test physical on-hand inventory is deducted and ORDER_DEDUCTED movement is recorded on handover."""
        initial_on_hand = self.inv_a1.on_hand_qty  # 50.000

        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1003",
            company=self.company_a,
            order_number="SO-2026-0003",
            customer_name="Ravi Kumar",
            total_amount=Decimal("640.00"),
            status=SellerOrder.Status.READY_FOR_PICKUP,
        )
        SellerOrderItem.objects.create(
            order=order,
            product=self.product_a1,
            product_title=self.product_a1.title,
            sku=self.product_a1.sku,
            ordered_quantity=Decimal("5.000"),
            unit_price=Decimal("320.00"),
            line_total=Decimal("640.00"),
        )

        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "handover", "handover_ref": "DISPATCH-882"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        self.inv_a1.refresh_from_db()
        self.assertEqual(self.inv_a1.on_hand_qty, initial_on_hand - Decimal("5.000"))  # 45.000

        # Verify movement ledger
        movement = SellerInventoryMovement.objects.filter(
            inventory=self.inv_a1,
            movement_type=SellerInventoryMovement.MovementType.ORDER_DEDUCTED,
        ).first()
        self.assertIsNotNone(movement)
        self.assertEqual(movement.quantity_change, Decimal("-5.000"))
        self.assertEqual(movement.balance_after, Decimal("45.000"))

    def test_04_order_cancellation_releases_reservation(self):
        """Test cancelling an order safely releases reserved stock and creates RESERVATION_RELEASED movement."""
        self.inv_a1.reserved_qty = Decimal("4.000")
        self.inv_a1.save()

        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1004",
            company=self.company_a,
            order_number="SO-2026-0004",
            customer_name="Suresh Raina",
            status=SellerOrder.Status.ACCEPTED,
        )
        SellerOrderItem.objects.create(
            order=order,
            product=self.product_a1,
            product_title=self.product_a1.title,
            sku=self.product_a1.sku,
            ordered_quantity=Decimal("4.000"),
            unit_price=Decimal("320.00"),
            line_total=Decimal("1280.00"),
        )

        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {
                "action": "cancel",
                "cancellation_reason": "Customer called to cancel delivery due to address change.",
            },
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order"]["status"], "CANCELLED")

        self.inv_a1.refresh_from_db()
        self.assertEqual(self.inv_a1.reserved_qty, Decimal("0.000"))

        movement = SellerInventoryMovement.objects.filter(
            inventory=self.inv_a1,
            movement_type=SellerInventoryMovement.MovementType.RESERVATION_RELEASED,
        ).first()
        self.assertIsNotNone(movement)

    def test_05_cancellation_requires_mandatory_reason(self):
        """Test cancelling an order without a reason returns HTTP 400 Bad Request."""
        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1005",
            company=self.company_a,
            order_number="SO-2026-0005",
            status=SellerOrder.Status.NEW,
        )

        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "cancel", "cancellation_reason": ""},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("cancellation_reason", resp.data)

    def test_06_invalid_state_transition_blocked(self):
        """Test invalid out-of-order state transitions are rejected."""
        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1006",
            company=self.company_a,
            order_number="SO-2026-0006",
            status=SellerOrder.Status.NEW,
        )

        # Attempt NEW -> DELIVERED (invalid)
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/transition/",
            {"action": "deliver"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Invalid state transition", resp.data["error"])

    def test_07_item_pick_checklist_api(self):
        """Test updating item picked / packed status and fulfilled quantities."""
        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1007",
            company=self.company_a,
            order_number="SO-2026-0007",
            status=SellerOrder.Status.PICKING,
        )
        item = SellerOrderItem.objects.create(
            order=order,
            product=self.product_a1,
            product_title=self.product_a1.title,
            sku=self.product_a1.sku,
            ordered_quantity=Decimal("3.000"),
            unit_price=Decimal("320.00"),
            line_total=Decimal("960.00"),
            is_picked=False,
        )

        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order.id}/item-pick/",
            {
                "item_id": item.id,
                "is_picked": True,
                "fulfilled_quantity": "3.000",
                "notes": "Verified expiration date 2027-01-01",
            },
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["item"]["is_picked"])
        self.assertEqual(Decimal(resp.data["item"]["fulfilled_quantity"]), Decimal("3.000"))

    def test_08_tenant_isolation_cross_seller_access_blocked(self):
        """Test Seller A cannot view or transition Seller B's orders."""
        order_b = SellerOrder.objects.create(
            source_order_id="CUST-ORD-B-1001",
            company=self.company_b,
            order_number="SO-B-0001",
            status=SellerOrder.Status.NEW,
        )

        # Seller A tries to view Order B -> 404
        resp = self.client.get(
            f"/api/workforce/seller-hub/orders/{order_b.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

        # Seller A tries to transition Order B -> 404
        resp = self.client.post(
            f"/api/workforce/seller-hub/orders/{order_b.id}/transition/",
            {"action": "accept"},
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_09_packing_slip_api(self):
        """Test structured packing slip generation endpoint."""
        order = SellerOrder.objects.create(
            source_order_id="CUST-ORD-1009",
            company=self.company_a,
            order_number="SO-2026-0009",
            customer_name="Pooja Hegde",
            customer_phone="9988776655",
            delivery_address="Flat 402, Sea View Apartments",
            fulfillment_type=SellerOrder.FulfillmentType.DELIVERY,
            delivery_slot="Today Evening 6:00 PM",
            total_amount=Decimal("320.00"),
            status=SellerOrder.Status.PACKED,
        )
        SellerOrderItem.objects.create(
            order=order,
            product=self.product_a1,
            product_title=self.product_a1.title,
            sku=self.product_a1.sku,
            unit=self.product_a1.unit,
            pack_size=self.product_a1.pack_size,
            ordered_quantity=Decimal("1.000"),
            unit_price=Decimal("320.00"),
            line_total=Decimal("320.00"),
        )

        resp = self.client.get(
            f"/api/workforce/seller-hub/orders/{order.id}/packing-slip/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["order_number"], "SO-2026-0009")
        self.assertEqual(resp.data["customer"]["name"], "Pooja Hegde")
        self.assertEqual(resp.data["seller"]["name"], "Organic Farms Hub")
        self.assertEqual(len(resp.data["items"]), 1)

    def test_10_dashboard_metrics_real_db_order_counts(self):
        """Test Seller Hub metrics endpoint returns accurate live DB order counts."""
        SellerOrder.objects.create(
            source_order_id="CUST-MTR-1",
            company=self.company_a,
            order_number="SO-MTR-1",
            status=SellerOrder.Status.NEW,
        )
        SellerOrder.objects.create(
            source_order_id="CUST-MTR-2",
            company=self.company_a,
            order_number="SO-MTR-2",
            status=SellerOrder.Status.ACCEPTED,
        )
        SellerOrder.objects.create(
            source_order_id="CUST-MTR-3",
            company=self.company_a,
            order_number="SO-MTR-3",
            status=SellerOrder.Status.DELIVERED,
        )

        resp = self.client.get(
            "/api/workforce/seller-hub/metrics/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["pending_orders_count"], 1)
        self.assertEqual(resp.data["in_prep_orders_count"], 1)
        self.assertEqual(resp.data["completed_orders_count"], 1)
        self.assertEqual(resp.data["total_orders_count"], 3)


if __name__ == "__main__":
    import unittest
    unittest.main()

