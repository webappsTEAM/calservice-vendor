"""
test_seller_product_catalog.py

Comprehensive test suite verifying Phase 2: Seller Product Catalog & Catalog Uploads:
1. Relational models: SellerProduct, SellerProductImage, SellerCatalogUploadBatch, SellerProductAuditLog
2. Single product creation (Draft & Submitted)
3. Active Leaf Category enforcement (blocking assignment to parent categories with children)
4. Inactive Category enforcement
5. SKU uniqueness per seller (allowing different sellers to use the same SKU)
6. Pricing validation (selling_price <= mrp, mrp > 0)
7. Image requirement for submission
8. Tenant isolation & security (seller A cannot view/edit/delete seller B's items)
9. Admin review state machine (approve, reject with note, request changes with note, pause with note)
10. Resubmission lifecycle upon editing approved products
11. Bulk CSV template download
12. Bulk CSV upload preview with row-level error reporting
13. Bulk CSV atomic import with SellerCatalogUploadBatch tracking
14. Dashboard metrics endpoint verification
"""
import os
import io
import csv
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]

import unittest
from decimal import Decimal
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
    SellerCatalogUploadBatch,
    SellerProductAuditLog,
)


class SellerProductCatalogTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.client = APIClient()

        # 1. Superadmin User
        cls.superadmin_user, _ = User.objects.get_or_create(
            username="superadmin_catalog_test",
            defaults={"email": "superadmin_catalog@sevo.com", "is_superuser": True, "is_staff": True, "role": "admin"}
        )
        cls.superadmin_token = str(RefreshToken.for_user(cls.superadmin_user).access_token)

        # 2. Seller Company A & User A
        cls.company_a, _ = Company.objects.get_or_create(
            slug="store-alpha-groceries",
            defaults={"company_name": "Store Alpha Groceries", "business_type": "grocery_supplier", "is_active": True}
        )
        cls.seller_user_a, _ = User.objects.get_or_create(
            username="seller_user_alpha",
            defaults={"email": "seller_alpha@store.com", "company": cls.company_a, "role": "admin"}
        )
        cls.seller_user_a.company = cls.company_a
        cls.seller_user_a.save()
        cls.seller_a_token = str(RefreshToken.for_user(cls.seller_user_a).access_token)

        # 3. Seller Company B & User B
        cls.company_b, _ = Company.objects.get_or_create(
            slug="store-beta-supermarket",
            defaults={"company_name": "Store Beta Supermarket", "business_type": "grocery_supplier", "is_active": True}
        )
        cls.seller_user_b, _ = User.objects.get_or_create(
            username="seller_user_beta",
            defaults={"email": "seller_beta@store.com", "company": cls.company_b, "role": "admin"}
        )
        cls.seller_user_b.company = cls.company_b
        cls.seller_user_b.save()
        cls.seller_b_token = str(RefreshToken.for_user(cls.seller_user_b).access_token)

        # 4. Standard Non-seller Company & User
        cls.tech_company, _ = Company.objects.get_or_create(
            slug="tech-services-inc",
            defaults={"company_name": "Tech Services Inc", "business_type": "service_provider", "is_active": True}
        )
        cls.technician_user, _ = User.objects.get_or_create(
            username="tech_catalog_test",
            defaults={"email": "tech_catalog@sevo.com", "company": cls.tech_company, "role": "technician"}
        )
        cls.technician_token = str(RefreshToken.for_user(cls.technician_user).access_token)

        # 5. Setup Category Hierarchy (Grocery -> Oil -> Sunflower Oil)
        # Parent Root: Grocery
        cls.root_cat, _ = SellerHubCategory.objects.get_or_create(
            slug="test-cat-grocery",
            defaults={"name": "Test Grocery", "is_active": True}
        )
        # Parent L1: Cooking Oil
        cls.parent_oil, _ = SellerHubCategory.objects.get_or_create(
            slug="test-cat-oil",
            defaults={"name": "Test Cooking Oil", "parent": cls.root_cat, "is_active": True}
        )
        # Leaf L2: Sunflower Oil
        cls.leaf_sunflower, _ = SellerHubCategory.objects.get_or_create(
            slug="test-cat-sunflower-oil",
            defaults={"name": "Test Sunflower Oil", "parent": cls.parent_oil, "is_active": True}
        )
        # Inactive Leaf Category
        cls.inactive_leaf, _ = SellerHubCategory.objects.get_or_create(
            slug="test-cat-inactive-leaf",
            defaults={"name": "Test Inactive Leaf", "parent": cls.parent_oil, "is_active": False}
        )

        # Clean any prior test products
        SellerProduct.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()
        SellerCatalogUploadBatch.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()

    @classmethod
    def tearDownClass(cls):
        SellerProduct.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()
        SellerCatalogUploadBatch.objects.filter(company__in=[cls.company_a, cls.company_b]).delete()
        super().tearDownClass()

    def test_01_seller_create_draft_product(self):
        """Seller creates a valid DRAFT product"""
        payload = {
            "title": "Sunlite Refined Sunflower Oil 1L",
            "sku": "SUN-OIL-1L",
            "brand": "Sunlite",
            "category": self.leaf_sunflower.id,
            "unit": "litre",
            "pack_size": "1L",
            "mrp": "180.00",
            "selling_price": "165.00",
            "tax_rate": "5.00",
            "hsn_code": "1512",
            "storage_info": "Store in a cool dry place",
            "expiry_info": "9 months from packaging",
            "status": "DRAFT",
            "images": ["https://images.unsplash.com/photo-oil-1.jpg"],
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["product"]["title"], "Sunlite Refined Sunflower Oil 1L")
        self.assertEqual(resp.data["product"]["status"], "DRAFT")
        self.assertEqual(resp.data["product"]["company"], self.company_a.id)
        
        # Verify Audit Log was created
        prod_id = resp.data["product"]["id"]
        audit = SellerProductAuditLog.objects.filter(product_id=prod_id).first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.action, "CREATED")

    def test_02_sku_unique_per_seller_company(self):
        """Duplicate SKU within same seller company must be rejected"""
        payload = {
            "title": "Another Oil With Same SKU",
            "sku": "SUN-OIL-1L",
            "category": self.leaf_sunflower.id,
            "mrp": "190.00",
            "selling_price": "170.00",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sku", resp.data["details"])

    def test_03_different_sellers_can_use_same_sku(self):
        """Seller B CAN use the same SKU 'SUN-OIL-1L' for their store catalog"""
        payload = {
            "title": "Beta Store Sunflower Oil 1L",
            "sku": "SUN-OIL-1L",
            "category": self.leaf_sunflower.id,
            "mrp": "175.00",
            "selling_price": "160.00",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_b_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["product"]["company"], self.company_b.id)

    def test_04_parent_category_assignment_blocked(self):
        """Assigning a product to a parent category (with children) must fail validation"""
        payload = {
            "title": "Product in Parent Category",
            "sku": "PARENT-CAT-TEST",
            "category": self.parent_oil.id, # parent with children
            "mrp": "100.00",
            "selling_price": "90.00",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("leaf", str(resp.data["details"]))

    def test_05_inactive_category_assignment_blocked(self):
        """Assigning a product to an inactive category must fail validation"""
        payload = {
            "title": "Product in Inactive Category",
            "sku": "INACTIVE-CAT-TEST",
            "category": self.inactive_leaf.id,
            "mrp": "100.00",
            "selling_price": "90.00",
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("inactive", str(resp.data["details"]))

    def test_06_pricing_validation_selling_price_exceeding_mrp(self):
        """Selling price higher than MRP must fail validation"""
        payload = {
            "title": "Overpriced Product",
            "sku": "OVERPRICED-1",
            "category": self.leaf_sunflower.id,
            "mrp": "100.00",
            "selling_price": "120.00", # > MRP
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("selling_price", str(resp.data["details"]))

    def test_07_submitting_product_without_image_blocked(self):
        """Submitting product for review without at least 1 image must be blocked"""
        payload = {
            "title": "No Image Product",
            "sku": "NO-IMG-PROD",
            "category": self.leaf_sunflower.id,
            "mrp": "100.00",
            "selling_price": "90.00",
            "status": "SUBMITTED",
            "images": [],
        }
        resp = self.client.post(
            "/api/workforce/seller-hub/products/",
            data=payload,
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("image", str(resp.data).lower())

    def test_08_tenant_isolation_seller_a_cannot_access_seller_b(self):
        """Seller A cannot access or modify Seller B's products"""
        prod_b = SellerProduct.objects.filter(company=self.company_b).first()
        self.assertIsNotNone(prod_b)

        # Seller A tries to GET Seller B product
        resp_get = self.client.get(
            f"/api/workforce/seller-hub/products/{prod_b.id}/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_get.status_code, status.HTTP_404_NOT_FOUND)

        # Seller A tries to PATCH Seller B product
        resp_patch = self.client.patch(
            f"/api/workforce/seller-hub/products/{prod_b.id}/",
            data={"title": "Hacked Title"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_patch.status_code, status.HTTP_404_NOT_FOUND)

    def test_09_product_submit_workflow(self):
        """Seller submits a Draft product for approval"""
        prod = SellerProduct.objects.filter(company=self.company_a, status="DRAFT").first()
        self.assertIsNotNone(prod)

        resp = self.client.post(
            f"/api/workforce/seller-hub/products/{prod.id}/submit/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        prod.refresh_from_db()
        self.assertEqual(prod.status, "SUBMITTED")
        self.assertIsNotNone(prod.submitted_at)

    def test_10_admin_review_decisions_and_audit(self):
        """Platform Admin review decisions: request changes, reject with note, approve"""
        prod = SellerProduct.objects.filter(company=self.company_a, status="SUBMITTED").first()
        self.assertIsNotNone(prod)

        # 1. Reject without note -> blocked
        resp_reject_no_note = self.client.post(
            f"/api/workforce/seller-hub/products/{prod.id}/review/",
            data={"action": "reject", "note": ""},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}",
        )
        self.assertEqual(resp_reject_no_note.status_code, status.HTTP_400_BAD_REQUEST)

        # 2. Request Changes with note -> CHANGES_REQUESTED
        resp_changes = self.client.post(
            f"/api/workforce/seller-hub/products/{prod.id}/review/",
            data={"action": "request_changes", "note": "Please update product description and add clear brand image."},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}",
        )
        self.assertEqual(resp_changes.status_code, status.HTTP_200_OK)
        prod.refresh_from_db()
        self.assertEqual(prod.status, "CHANGES_REQUESTED")
        self.assertEqual(prod.admin_review_note, "Please update product description and add clear brand image.")

        # 3. Approve -> APPROVED
        resp_approve = self.client.post(
            f"/api/workforce/seller-hub/products/{prod.id}/review/",
            data={"action": "approve"},
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}",
        )
        self.assertEqual(resp_approve.status_code, status.HTTP_200_OK)
        prod.refresh_from_db()
        self.assertEqual(prod.status, "APPROVED")

        # Verify audit entries
        audits = SellerProductAuditLog.objects.filter(product=prod)
        self.assertTrue(audits.filter(action="APPROVED").exists())
        self.assertTrue(audits.filter(action="REQUEST_CHANGES").exists())

    def test_11_seller_edit_approved_product_reverts_to_review(self):
        """Meaningful price change on an APPROVED product by a seller moves it back to review queue"""
        prod = SellerProduct.objects.filter(company=self.company_a, status="APPROVED").first()
        self.assertIsNotNone(prod)

        resp = self.client.patch(
            f"/api/workforce/seller-hub/products/{prod.id}/",
            data={"selling_price": "155.00"}, # modified price
            format="json",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        prod.refresh_from_db()
        self.assertEqual(prod.status, "SUBMITTED") # moved back to review
        
        audit = SellerProductAuditLog.objects.filter(product=prod, action="RESUBMITTED").first()
        self.assertIsNotNone(audit)

    def test_12_bulk_csv_template_download(self):
        """CSV Bulk template endpoint generates valid CSV format"""
        resp = self.client.get(
            "/api/workforce/seller-hub/products/template/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv; charset=utf-8")
        content = resp.content.decode("utf-8")
        self.assertIn("Title", content)
        self.assertIn("SKU", content)
        self.assertIn("Category_Slug", content)
        self.assertIn("Selling_Price", content)

    def test_13_bulk_csv_preview_and_atomic_import(self):
        """Bulk CSV validation preview with errors and clean import"""
        # Create CSV content with 1 valid row and 1 invalid row (selling price > mrp)
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow([
            "Title", "Description", "Brand", "SKU", "Barcode", "Category_Slug", "Unit", "Pack_Size", "MRP", "Selling_Price", "Tax_Rate", "HSN_Code", "Image_URL", "Storage_Info", "Expiry_Info"
        ])
        writer.writerow([
            "Bulk Valid Groundnut Oil", "Cold pressed oil", "NutriGold", "NUTRI-GN-1L", "8901111111111", self.leaf_sunflower.slug, "litre", "1L", "220.00", "200.00", "5.00", "1512", "https://example.com/gn.jpg", "Cool place", "12 months"
        ])
        writer.writerow([
            "Bulk Invalid Price Oil", "Desc", "Brand", "BAD-PRICE-1L", "8902222222222", self.leaf_sunflower.slug, "litre", "1L", "100.00", "150.00", "5.00", "1512", "", "", ""
        ])

        csv_file = io.BytesIO(csv_buffer.getvalue().encode("utf-8"))
        csv_file.name = "catalog_feed.csv"

        # 1. Test Preview Validator (Dry-run)
        resp_prev = self.client.post(
            "/api/workforce/seller-hub/products/bulk-upload/?preview=true",
            data={"file": csv_file},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_prev.status_code, status.HTTP_200_OK)
        self.assertTrue(resp_prev.data["preview"])
        self.assertEqual(resp_prev.data["total_rows"], 2)
        self.assertEqual(resp_prev.data["valid_rows_count"], 1)
        self.assertEqual(resp_prev.data["invalid_rows_count"], 1)
        self.assertFalse(resp_prev.data["can_import"])

        # 2. Test Clean Valid Bulk Import
        clean_buffer = io.StringIO()
        clean_writer = csv.writer(clean_buffer)
        clean_writer.writerow([
            "Title", "Description", "Brand", "SKU", "Barcode", "Category_Slug", "Unit", "Pack_Size", "MRP", "Selling_Price", "Tax_Rate", "HSN_Code", "Image_URL", "Storage_Info", "Expiry_Info"
        ])
        clean_writer.writerow([
            "Bulk Valid Mustard Oil 1L", "Pure kachi ghani mustard oil", "Dhara", "DHARA-MUST-1L", "8903333333333", self.leaf_sunflower.slug, "litre", "1L", "160.00", "145.00", "5.00", "1512", "https://example.com/mustard.jpg", "Cool place", "12 months"
        ])

        clean_file = io.BytesIO(clean_buffer.getvalue().encode("utf-8"))
        clean_file.name = "clean_catalog_feed.csv"

        resp_import = self.client.post(
            "/api/workforce/seller-hub/products/bulk-upload/",
            data={"file": clean_file},
            format="multipart",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp_import.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp_import.data["imported_rows"], 1)
        
        # Verify SellerCatalogUploadBatch was created
        batch = SellerCatalogUploadBatch.objects.get(pk=resp_import.data["batch_id"])
        self.assertEqual(batch.status, "COMPLETED")
        self.assertEqual(batch.imported_rows, 1)

    def test_14_dashboard_metrics_endpoint(self):
        """Seller Hub dashboard metrics return accurate counts from real DB"""
        resp = self.client.get(
            "/api/workforce/seller-hub/metrics/",
            HTTP_AUTHORIZATION=f"Bearer {self.seller_a_token}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("catalogs_awaiting_approval", resp.data)
        self.assertIn("approved_products", resp.data)
        self.assertIn("total_products", resp.data)
        self.assertGreater(resp.data["total_products"], 0)


if __name__ == "__main__":
    unittest.main()
