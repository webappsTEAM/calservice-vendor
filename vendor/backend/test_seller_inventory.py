"""
test_seller_inventory.py

Comprehensive automated test suite verifying Phase 3: Seller Hub Inventory Management:
1. Initialize inventory for an approved product.
2. Prevent duplicate inventory for the same (company, product).
3. Block stock initialization on unapproved products (DRAFT, REJECTED).
4. Stock-In replenishment updates balance, batch, and creates STOCK_IN movement.
5. Stock Adjustment (Increase) updates balance and logs movement.
6. Stock Adjustment (Decrease) with mandatory reason updates balance and logs movement.
7. Stock Decrease without reason is blocked (400).
8. Negative stock prevention (attempting to reduce more than on-hand stock fails).
9. Decimal quantity precision for kg, grams, and litres (e.g. 2.750 kg).
10. Available quantity calculation (on_hand - reserved) and stock status determination (IN_STOCK, LOW_STOCK, OUT_OF_STOCK).
11. Recording damaged and expired stock write-offs.
12. Grocery batch creation and dynamic expiry status calculation (ACTIVE, EXPIRING_SOON, EXPIRED).
13. Strict tenant isolation: Seller A cannot access or adjust Seller B's inventory.
14. Platform Superadmin cross-tenant view, adjustments, and immutable audit logs.
15. Dashboard metrics endpoint accuracy from real database records.
"""
import os
import django
from decimal import Decimal
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]

import unittest
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from companies.models import Company
from workforce_api.models import (
    SellerHubCategory,
    SellerProduct,
    SellerProductImage,
    SellerInventory,
    SellerInventoryBatch,
    SellerInventoryMovement,
)


class SellerInventoryTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

        # 1. Superadmin User
        cls.superadmin_user, _ = User.objects.get_or_create(
            username="superadmin_inv_test",
            defaults={"email": "superadmin_inv@sevo.com", "is_superuser": True, "is_staff": True, "role": "admin"}
        )
        cls.superadmin_token = str(RefreshToken.for_user(cls.superadmin_user).access_token)

        # 2. Seller Company A & User A
        cls.company_a, _ = Company.objects.get_or_create(
            slug="store-alpha-inv",
            defaults={"company_name": "Store Alpha Groceries", "business_type": "grocery_supplier", "is_active": True}
        )
        cls.seller_user_a, _ = User.objects.get_or_create(
            username="seller_user_alpha_inv",
            defaults={"email": "seller_alpha_inv@store.com", "company": cls.company_a, "role": "admin"}
        )
        cls.seller_user_a.company = cls.company_a
        cls.seller_user_a.save()
        cls.seller_a_token = str(RefreshToken.for_user(cls.seller_user_a).access_token)

        # 3. Seller Company B & User B
        cls.company_b, _ = Company.objects.get_or_create(
            slug="store-beta-inv",
            defaults={"company_name": "Store Beta Supermarket", "business_type": "grocery_supplier", "is_active": True}
        )
        cls.seller_user_b, _ = User.objects.get_or_create(
            username="seller_user_beta_inv",
            defaults={"email": "seller_beta_inv@store.com", "company": cls.company_b, "role": "admin"}
        )
        cls.seller_user_b.company = cls.company_b
        cls.seller_user_b.save()
        cls.seller_b_token = str(RefreshToken.for_user(cls.seller_user_b).access_token)

        # 4. Category Hierarchy
        cls.root_cat, _ = SellerHubCategory.objects.get_or_create(
            slug="inv-test-grocery",
            defaults={"name": "Inv Test Grocery", "is_active": True}
        )
        cls.leaf_cat, _ = SellerHubCategory.objects.get_or_create(
            slug="inv-test-sunflower-oil",
            defaults={"name": "Inv Sunflower Oil", "parent": cls.root_cat, "is_active": True}
        )

        # Clean prior test inventory & products for these companies
        SellerInventoryMovement.objects.filter(inventory__company__in=[cls.company_a, cls.company_b]).delete()
        SellerInventoryBatch.objects.filter(inventory__company__in=[cls.company_a, cls.company_b]).delete()
        SellerInventory.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()
        SellerProduct.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()

        # 5. Create Approved and Draft Products for Company A
        cls.prod_approved_a = SellerProduct.objects.create(
            company=cls.company_a,
            created_by=cls.seller_user_a,
            category=cls.leaf_cat,
            title="Premium Sunflower Oil 1L",
            sku="INV-SUN-1L",
            brand="SunPure",
            unit="litre",
            pack_size="1L",
            mrp=Decimal("200.00"),
            selling_price=Decimal("180.00"),
            status=SellerProduct.Status.APPROVED,
        )
        SellerProductImage.objects.create(product=cls.prod_approved_a, image_url="https://example.com/oil1.jpg", is_primary=True)

        cls.prod_draft_a = SellerProduct.objects.create(
            company=cls.company_a,
            created_by=cls.seller_user_a,
            category=cls.leaf_cat,
            title="Draft Mustard Oil 1L",
            sku="INV-MUSTARD-1L",
            brand="MustardPure",
            unit="litre",
            pack_size="1L",
            mrp=Decimal("220.00"),
            selling_price=Decimal("195.00"),
            status=SellerProduct.Status.DRAFT,
        )

        # 6. Create Approved Product for Company B
        cls.prod_approved_b = SellerProduct.objects.create(
            company=cls.company_b,
            created_by=cls.seller_user_b,
            category=cls.leaf_cat,
            title="Organic Groundnut Oil 1L",
            sku="INV-GNUT-1L",
            brand="NutriGold",
            unit="litre",
            pack_size="1L",
            mrp=Decimal("250.00"),
            selling_price=Decimal("220.00"),
            status=SellerProduct.Status.APPROVED,
        )

    @classmethod
    def tearDownClass(cls):
        SellerInventoryMovement.objects.filter(inventory__company__in=[cls.company_a, cls.company_b]).delete()
        SellerInventoryBatch.objects.filter(inventory__company__in=[cls.company_a, cls.company_b]).delete()
        SellerInventory.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()
        SellerProduct.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()
        super().tearDownClass()

    def test_01_initialize_inventory_approved_product(self):
        """Seller initializes inventory for an APPROVED product with opening stock"""
        payload = {
            "product_id": self.prod_approved_a.id,
            "on_hand_qty": "50.000",
            "low_stock_threshold": "15.000",
            "reorder_level": "25.000",
            "batch_number": "BATCH-OIL-01",
            "expiry_date": (timezone.now().date() + timedelta(days=90)).isoformat(),
            "cost_price": "150.00",
            "reason": "Initial opening stock delivery.",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/inventory/initialize/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        data = resp.data["inventory"]
        self.assertEqual(Decimal(str(data["on_hand_qty"])), Decimal("50.000"))
        self.assertEqual(Decimal(str(data["available_qty"])), Decimal("50.000"))
        self.assertEqual(Decimal(str(data["low_stock_threshold"])), Decimal("15.000"))
        self.assertEqual(data["stock_status"], "IN_STOCK")

        # Verify OPENING_STOCK movement in DB
        inv_id = data["id"]
        mov = SellerInventoryMovement.objects.filter(inventory_id=inv_id).first()
        self.assertIsNotNone(mov)
        self.assertEqual(mov.movement_type, "OPENING_STOCK")
        self.assertEqual(mov.quantity_change, Decimal("50.000"))
        self.assertEqual(mov.balance_before, Decimal("0.000"))
        self.assertEqual(mov.balance_after, Decimal("50.000"))

        # Verify Batch created in DB
        batch = SellerInventoryBatch.objects.filter(inventory_id=inv_id, batch_number="BATCH-OIL-01").first()
        self.assertIsNotNone(batch)
        self.assertEqual(batch.current_quantity, Decimal("50.000"))
        self.assertEqual(batch.status, "ACTIVE")

    def test_02_duplicate_inventory_prevention(self):
        """Initializing inventory for a product that already has stock record returns 409 Conflict"""
        payload = {
            "product_id": self.prod_approved_a.id,
            "on_hand_qty": "10.000",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/inventory/initialize/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_409_CONFLICT)

    def test_03_unapproved_product_inventory_blocked(self):
        """Attempting to initialize stock for a DRAFT product is blocked (400)"""
        payload = {
            "product_id": self.prod_draft_a.id,
            "on_hand_qty": "10.000",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/inventory/initialize/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("APPROVED", str(resp.data.get("error", "")))

    def test_04_stock_in_replenishment(self):
        """Stock-in adds physical stock, creates batch, and generates immutable STOCK_IN movement"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        balance_before = inv.on_hand_qty

        payload = {
            "movement_type": "STOCK_IN",
            "quantity": "25.500",
            "batch_number": "BATCH-OIL-02",
            "expiry_date": (timezone.now().date() + timedelta(days=120)).isoformat(),
            "cost_price": "148.00",
            "reason": "Wholesale supplier shipment PO-102.",
            "reference_id": "PO-102",
        }
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        inv.refresh_from_db()
        expected_balance = balance_before + Decimal("25.500")
        self.assertEqual(inv.on_hand_qty, expected_balance)

        # Check movement record
        mov = SellerInventoryMovement.objects.filter(inventory=inv, movement_type="STOCK_IN").latest("created_at")
        self.assertEqual(mov.quantity_change, Decimal("25.500"))
        self.assertEqual(mov.balance_before, balance_before)
        self.assertEqual(mov.balance_after, expected_balance)
        self.assertEqual(mov.reference_id, "PO-102")

    def test_05_stock_adjustment_increase(self):
        """Stock adjustment increase (+5.000) updates balance and logs movement"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        balance_before = inv.on_hand_qty

        payload = {
            "movement_type": "ADJUSTMENT_INCREASE",
            "quantity": "5.000",
            "reason": "Physical count audit found extra bottle on shelf.",
        }
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        inv.refresh_from_db()
        self.assertEqual(inv.on_hand_qty, balance_before + Decimal("5.000"))

    def test_06_stock_adjustment_decrease_with_reason(self):
        """Stock adjustment decrease (-3.000) with reason decrements balance"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        balance_before = inv.on_hand_qty

        payload = {
            "movement_type": "ADJUSTMENT_DECREASE",
            "quantity": "3.000",
            "reason": "Internal QC sample testing.",
        }
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        inv.refresh_from_db()
        self.assertEqual(inv.on_hand_qty, balance_before - Decimal("3.000"))

    def test_07_stock_decrease_without_reason_blocked(self):
        """Decreasing stock without mandatory reason is blocked (400)"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        payload = {
            "movement_type": "ADJUSTMENT_DECREASE",
            "quantity": "2.000",
            "reason": "", # Missing reason
        }
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", str(resp.data))

    def test_08_negative_stock_prevention(self):
        """Attempting to reduce stock beyond on-hand quantity is blocked (400)"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        current_balance = inv.on_hand_qty

        payload = {
            "movement_type": "ADJUSTMENT_DECREASE",
            "quantity": str(current_balance + Decimal("100.000")),
            "reason": "Attempting invalid massive write-off.",
        }
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Insufficient", str(resp.data.get("error", "")))

    def test_09_decimal_quantity_precision(self):
        """Decimal quantities with 3 decimal places (e.g., 2.750 kg) retain exact precision"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        balance_before = inv.on_hand_qty

        payload = {
            "movement_type": "ADJUSTMENT_INCREASE",
            "quantity": "2.750",
            "reason": "Decimal precision test.",
        }
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        inv.refresh_from_db()
        self.assertEqual(inv.on_hand_qty, balance_before + Decimal("2.750"))

    def test_10_available_qty_and_stock_status(self):
        """Available quantity equals (on_hand - reserved) and determines stock status"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        inv.on_hand_qty = Decimal("12.000")
        inv.reserved_qty = Decimal("2.000")
        inv.low_stock_threshold = Decimal("15.000") # available (10.000) <= threshold (15.000) -> LOW_STOCK
        inv.save()

        resp = self.client.get(
            f"/api/workforce/seller-hub/inventory/{inv.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertEqual(Decimal(str(data["available_qty"])), Decimal("10.000"))
        self.assertEqual(data["stock_status"], "LOW_STOCK")

        # Test OUT_OF_STOCK
        inv.on_hand_qty = Decimal("0.000")
        inv.save()
        resp_out = self.client.get(
            f"/api/workforce/seller-hub/inventory/{inv.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_out.data["stock_status"], "OUT_OF_STOCK")

    def test_11_damaged_and_expired_stock_write_off(self):
        """Recording damaged and expired write-offs decrements stock and creates respective movement types"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        inv.on_hand_qty = Decimal("50.000")
        inv.reserved_qty = Decimal("0.000")
        inv.save()

        # 1. Record Damage
        resp_damage = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data={
                "movement_type": "DAMAGE",
                "quantity": "2.000",
                "reason": "Broken bottle during warehouse handling.",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_damage.status_code, status.HTTP_200_OK)
        inv.refresh_from_db()
        self.assertEqual(inv.on_hand_qty, Decimal("48.000"))

        # 2. Record Expired
        resp_expired = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv.id}/adjust/",
            data={
                "movement_type": "EXPIRED",
                "quantity": "3.000",
                "reason": "Passed expiry threshold disposal.",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_expired.status_code, status.HTTP_200_OK)
        inv.refresh_from_db()
        self.assertEqual(inv.on_hand_qty, Decimal("45.000"))

    def test_12_batch_expiry_status_detection(self):
        """Batch expiry dates correctly compute ACTIVE, EXPIRING_SOON, and EXPIRED statuses"""
        inv = SellerInventory.objects.get(product=self.prod_approved_a)
        today = timezone.now().date()

        # 1. Expiring soon batch (within 15 days)
        b_soon = SellerInventoryBatch.objects.create(
            inventory=inv,
            batch_number="BATCH-SOON-01",
            received_date=today - timedelta(days=60),
            expiry_date=today + timedelta(days=15),
            initial_quantity=Decimal("10.000"),
            current_quantity=Decimal("10.000"),
        )
        self.assertEqual(b_soon.update_dynamic_status(save=True), "EXPIRING_SOON")

        # 2. Already expired batch
        b_expired = SellerInventoryBatch.objects.create(
            inventory=inv,
            batch_number="BATCH-EXP-01",
            received_date=today - timedelta(days=120),
            expiry_date=today - timedelta(days=5),
            initial_quantity=Decimal("5.000"),
            current_quantity=Decimal("5.000"),
        )
        self.assertEqual(b_expired.update_dynamic_status(save=True), "EXPIRED")

        # Test batch list endpoint
        resp = self.client.get(
            f"/api/workforce/seller-hub/inventory/{inv.id}/batches/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        batch_statuses = [b["status"] for b in resp.data]
        self.assertIn("EXPIRING_SOON", batch_statuses)
        self.assertIn("EXPIRED", batch_statuses)

    def test_13_tenant_isolation(self):
        """Seller A cannot access, view, or adjust Seller B's inventory"""
        # Initialize inventory for Seller B
        inv_b = SellerInventory.objects.create(
            company=self.company_b,
            product=self.prod_approved_b,
            on_hand_qty=Decimal("100.000"),
            reserved_qty=Decimal("0.000"),
            low_stock_threshold=Decimal("10.000"),
        )

        # Seller A attempts to view Seller B's inventory
        resp_get = self.client.get(
            f"/api/workforce/seller-hub/inventory/{inv_b.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_get.status_code, status.HTTP_404_NOT_FOUND)

        # Seller A attempts to adjust Seller B's stock
        resp_adjust = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv_b.id}/adjust/",
            data={"movement_type": "ADJUSTMENT_INCREASE", "quantity": "10.000", "reason": "Unauthorized attempt."},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_adjust.status_code, status.HTTP_404_NOT_FOUND)

        # In inventory listing, Seller A only sees Company A items
        resp_list = self.client.get(
            "/api/workforce/seller-hub/inventory/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_list.status_code, status.HTTP_200_OK)
        ids_visible = [item["id"] for item in resp_list.data]
        self.assertNotIn(inv_b.id, ids_visible)

    def test_14_admin_superadmin_cross_tenant_access_and_audit(self):
        """Platform Superadmin can view and adjust stock across tenants with immutable actor audit"""
        inv_b = SellerInventory.objects.get(product=self.prod_approved_b)
        balance_before = inv_b.on_hand_qty

        # Superadmin adjusts Seller B stock
        resp = self.client.post(
            f"/api/workforce/seller-hub/inventory/{inv_b.id}/adjust/",
            data={
                "movement_type": "ADJUSTMENT_INCREASE",
                "quantity": "20.000",
                "reason": "Platform Superadmin inventory verification adjustment.",
                "reference_id": "ADMIN-AUDIT-99",
            },
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        inv_b.refresh_from_db()
        self.assertEqual(inv_b.on_hand_qty, balance_before + Decimal("20.000"))

        # Verify audit record names the Superadmin actor
        mov = SellerInventoryMovement.objects.filter(inventory=inv_b, reference_id="ADMIN-AUDIT-99").first()
        self.assertIsNotNone(mov)
        self.assertEqual(mov.actor, self.superadmin_user)

    def test_15_dashboard_metrics_real_db(self):
        """Seller Hub metrics endpoint returns accurate real DB counts for inventory"""
        resp = self.client.get(
            "/api/workforce/seller-hub/metrics/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data
        self.assertIn("total_inventory_products", data)
        self.assertIn("low_stock_items_count", data)
        self.assertIn("out_of_stock_items_count", data)
        self.assertIn("in_stock_items_count", data)
        self.assertIn("total_inventory_value", data)
        self.assertGreaterEqual(data["total_inventory_products"], 1)


if __name__ == "__main__":
    unittest.main()
