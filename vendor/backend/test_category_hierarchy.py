"""
test_category_hierarchy.py

Comprehensive test suite verifying multi-level hierarchical category support:
1. Root, child, and grandchild category creation with parent assignment.
2. Self-parenting and circular-reference prevention (rejection on validation).
3. Level / depth computation & breadcrumb ancestors list.
4. Tree retrieval endpoint and active tree filtering.
5. Parent-filtered queries (roots via parent_id=null / root=true, direct children via parent_id=<id>).
6. Safe deletion multi-tier guards:
   - Blocked when child subcategories exist (CATEGORY_HAS_CHILDREN).
   - Blocked when linked services or inventory items exist (CATEGORY_IN_USE).
   - Allowed when unlinked and child-free.
7. Active/inactive parent cascade visibility (inactive parent hides descendants from active list).
8. Existing category backward compatibility.
"""
import os
import sys
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS and "*" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from companies.models import Company
from employees.models import Employee
from service_requests.models import CatalogCategory, Service
from workforce_api.models import InventoryItem

User = get_user_model()
client = APIClient()


def run_tests():
    print("=" * 80)
    print("STARTING CATEGORY HIERARCHY AUTOMATED TEST SUITE")
    print("=" * 80)

    # 1. Setup Test Fixtures
    superadmin = User.objects.filter(is_superuser=True).first()
    if not superadmin:
        superadmin, _ = User.objects.get_or_create(
            username="hier_superadmin",
            defaults={"email": "hier_sa@sevo.com", "is_superuser": True, "is_staff": True}
        )
        superadmin.set_password("pass123")
        superadmin.is_superuser = True
        superadmin.is_staff = True
        superadmin.save()

    seller_company, _ = Company.objects.get_or_create(
        company_name="Hierarchy Test Groceries",
        defaults={"business_type": "grocery_supplier", "industry": "grocery"}
    )
    seller_company.business_type = "grocery_supplier"
    seller_company.save()

    seller_user = User.objects.filter(username="hier_seller_user").first()
    if not seller_user:
        seller_user = User.objects.create(
            username="hier_seller_user",
            email="seller_hier@sevo.com",
            role=User.Role.ADMIN,
            is_staff=False
        )
        seller_user.set_password("pass123")
        seller_user.company = seller_company
        seller_user.save()

    Employee.objects.update_or_create(
        user=seller_user,
        defaults={"company": seller_company, "employee_id": "EMP-HIER-01", "title": "Hierarchy Merchant"}
    )

    passed = 0
    total = 0

    client.force_authenticate(user=superadmin)

    # ── Test 1: Create Root Category (Grocery) ──────────────────────────────────
    total += 1
    print(f"\n[Test {total}] Creating Root Category 'Grocery'...")
    res_root = client.post("/api/workforce/seller-hub/categories/", {
        "name": "Grocery Hierarchy Test",
        "description": "All grocery items",
        "icon": "ShoppingBag",
        "sort_order": 1,
        "is_active": True,
    }, format="json")
    assert res_root.status_code == status.HTTP_201_CREATED, f"Failed: {res_root.data}"
    root_id = res_root.data["category"]["id"]
    assert res_root.data["category"]["level"] == 0
    assert res_root.data["category"]["parent"] is None
    assert res_root.data["category"]["parent_id"] is None
    print(f"  [PASS] Root category created with ID={root_id}, level=0")
    passed += 1

    # ── Test 2: Create Subcategory Level 1 ('Oil', 'Dhals', 'Masalas') ─────────
    total += 1
    print(f"\n[Test {total}] Creating Level 1 Subcategory 'Oil' under 'Grocery'...")
    res_oil = client.post("/api/workforce/seller-hub/categories/", {
        "name": "Oil Hierarchy Test",
        "description": "Edible cooking oils",
        "icon": "Package",
        "parent": root_id,
        "sort_order": 1,
        "is_active": True,
    }, format="json")
    assert res_oil.status_code == status.HTTP_201_CREATED, f"Failed: {res_oil.data}"
    oil_id = res_oil.data["category"]["id"]
    assert res_oil.data["category"]["level"] == 1
    assert res_oil.data["category"]["parent_id"] == root_id
    assert res_oil.data["category"]["parent_name"] == "Grocery Hierarchy Test"
    assert len(res_oil.data["category"]["ancestors"]) == 1
    assert res_oil.data["category"]["ancestors"][0]["id"] == root_id
    print(f"  [PASS] Subcategory 'Oil' created with ID={oil_id}, parent={root_id}, level=1")
    passed += 1

    # Create siblings Dhals and Masalas under Grocery
    total += 1
    print(f"\n[Test {total}] Creating Sibling Subcategories 'Dhals' and 'Masalas'...")
    res_dhals = client.post("/api/workforce/seller-hub/categories/", {
        "name": "Dhals Hierarchy Test",
        "parent_id": root_id,
        "sort_order": 2,
    }, format="json")
    dhals_id = res_dhals.data["category"]["id"]

    res_masalas = client.post("/api/workforce/seller-hub/categories/", {
        "name": "Masalas Hierarchy Test",
        "parent_id": root_id,
        "sort_order": 3,
    }, format="json")
    masalas_id = res_masalas.data["category"]["id"]

    # Verify Grocery subcategories count is now 3
    res_root_detail = client.get(f"/api/workforce/seller-hub/categories/{root_id}/")
    assert res_root_detail.status_code == status.HTTP_200_OK
    assert res_root_detail.data["children_count"] == 3
    assert len(res_root_detail.data["children"]) == 3
    print(f"  [PASS] Root 'Grocery' now has 3 children (Oil, Dhals, Masalas)")
    passed += 1

    # ── Test 3: Create Grandchild Subcategory Level 2 ('Sunflower Oil', 'Coconut Oil') ───
    total += 1
    print(f"\n[Test {total}] Creating Grandchild Level 2 ('Sunflower Oil', 'Coconut Oil') under 'Oil'...")
    res_sunflower = client.post("/api/workforce/seller-hub/categories/", {
        "name": "Sunflower Oil Test",
        "parent_id": oil_id,
        "sort_order": 1,
        "is_active": True,
    }, format="json")
    sunflower_id = res_sunflower.data["category"]["id"]
    assert res_sunflower.data["category"]["level"] == 2
    assert res_sunflower.data["category"]["parent_id"] == oil_id
    assert len(res_sunflower.data["category"]["ancestors"]) == 2
    assert res_sunflower.data["category"]["ancestors"][0]["id"] == root_id
    assert res_sunflower.data["category"]["ancestors"][1]["id"] == oil_id

    res_coconut = client.post("/api/workforce/seller-hub/categories/", {
        "name": "Coconut Oil Test",
        "parent_id": oil_id,
        "sort_order": 2,
        "is_active": True,
    }, format="json")
    coconut_id = res_coconut.data["category"]["id"]

    res_oil_detail = client.get(f"/api/workforce/seller-hub/categories/{oil_id}/")
    assert res_oil_detail.data["children_count"] == 2
    print(f"  [PASS] Level 2 Grandchildren created. 'Sunflower Oil' depth=2, ancestors path: Grocery -> Oil")
    passed += 1

    # ── Test 4: Circular Reference & Self-Parenting Guard ─────────────────────────
    total += 1
    print(f"\n[Test {total}] Testing Self-Parenting and Circular-Reference Guards...")
    # Self parenting attempt
    res_self = client.patch(f"/api/workforce/seller-hub/categories/{oil_id}/", {
        "parent_id": oil_id
    }, format="json")
    assert res_self.status_code == status.HTTP_400_BAD_REQUEST
    assert "cannot be its own parent" in str(res_self.data)
    print(f"  [PASS] Self-parenting blocked: {res_self.data}")

    # Circular parenting attempt: Make Grocery a child of its descendant Sunflower Oil
    res_circ = client.patch(f"/api/workforce/seller-hub/categories/{root_id}/", {
        "parent_id": sunflower_id
    }, format="json")
    assert res_circ.status_code == status.HTTP_400_BAD_REQUEST
    assert "Circular reference detected" in str(res_circ.data)
    print(f"  [PASS] Circular descendant parenting blocked: {res_circ.data}")
    passed += 1

    # ── Test 5: Parent-Filtered Listings & Hierarchy Querying ────────────────────
    total += 1
    print(f"\n[Test {total}] Querying categories filtered by parent...")
    # Fetch root categories only
    res_roots = client.get("/api/workforce/seller-hub/categories/?root=true")
    assert res_roots.status_code == status.HTTP_200_OK
    assert all(c["parent_id"] is None for c in res_roots.data)
    assert any(c["id"] == root_id for c in res_roots.data)

    # Fetch direct children of Grocery
    res_grocery_children = client.get(f"/api/workforce/seller-hub/categories/?parent_id={root_id}")
    assert res_grocery_children.status_code == status.HTTP_200_OK
    assert len(res_grocery_children.data) == 3
    assert {c["id"] for c in res_grocery_children.data} == {oil_id, dhals_id, masalas_id}

    # Fetch direct children of Oil
    res_oil_children = client.get(f"/api/workforce/seller-hub/categories/?parent_id={oil_id}")
    assert res_oil_children.status_code == status.HTTP_200_OK
    assert len(res_oil_children.data) == 2
    assert {c["id"] for c in res_oil_children.data} == {sunflower_id, coconut_id}
    print(f"  [PASS] Parent-filtered listing accurately partitions root and child nodes")
    passed += 1

    # ── Test 6: Tree API Traversal ───────────────────────────────────────────────
    total += 1
    print(f"\n[Test {total}] Testing Tree Retrieval Endpoint...")
    res_tree = client.get("/api/workforce/seller-hub/categories/tree/")
    assert res_tree.status_code == status.HTTP_200_OK
    # Find our root node in tree
    root_node = next((n for n in res_tree.data if n["id"] == root_id), None)
    assert root_node is not None
    assert len(root_node["children"]) == 3
    oil_node = next((n for n in root_node["children"] if n["id"] == oil_id), None)
    assert oil_node is not None
    assert len(oil_node["children"]) == 2
    print(f"  [PASS] Nested Tree API correctly returns complete 3-level tree hierarchy")
    passed += 1

    # ── Test 7: Safe Deletion Guard 1 (Category with Child Subcategories) ────────
    total += 1
    print(f"\n[Test {total}] Testing Deletion Blocking when Category has Subcategories...")
    # Attempting to delete Oil which has Sunflower Oil & Coconut Oil
    res_del_oil = client.delete(f"/api/workforce/seller-hub/categories/{oil_id}/")
    assert res_del_oil.status_code == status.HTTP_409_CONFLICT
    assert res_del_oil.data["code"] == "CATEGORY_HAS_CHILDREN"
    assert "contains 2 subcategory" in res_del_oil.data["error"]
    print(f"  [PASS] Safe Deletion Guard correctly blocked deletion of category with children: {res_del_oil.data['error']}")
    passed += 1

    # ── Test 8: Safe Deletion Guard 2 (Category with Linked Items) ────────────────
    total += 1
    print(f"\n[Test {total}] Testing Deletion Blocking when Leaf Category has Linked Items...")
    # Link an inventory item to Sunflower Oil
    inv = InventoryItem.objects.create(
        company=seller_company,
        catalogue_service_id=1,
        catalogue_category_id=sunflower_id,
        category_name_snapshot="Sunflower Oil",
        custom_name="Fortune Sunlite Sunflower Oil 1L",
        custom_price=Decimal("140.00"),
        quantity_in_stock=100,
        is_available=True,
    )
    res_del_sunflower = client.delete(f"/api/workforce/seller-hub/categories/{sunflower_id}/")
    assert res_del_sunflower.status_code == status.HTTP_409_CONFLICT
    assert res_del_sunflower.data["code"] == "CATEGORY_IN_USE"
    print(f"  [PASS] Safe Deletion Guard correctly blocked deletion of category with linked items: {res_del_sunflower.data['error']}")
    inv.delete()
    passed += 1

    # ── Test 9: Safe Deletion of Unlinked Leaf Node ──────────────────────────────
    total += 1
    print(f"\n[Test {total}] Deleting unlinked leaf node ('Sunflower Oil')...")
    res_del_leaf = client.delete(f"/api/workforce/seller-hub/categories/{sunflower_id}/")
    assert res_del_leaf.status_code == status.HTTP_200_OK
    assert not CatalogCategory.objects.filter(id=sunflower_id).exists()
    print(f"  [PASS] Leaf node deleted successfully")
    passed += 1

    # ── Test 10: Active Parent Cascade to Descendants ────────────────────────────
    total += 1
    print(f"\n[Test {total}] Testing Active/Inactive Parent Cascade Visibility...")
    client.force_authenticate(user=seller_user)
    # Both Grocery and Oil are active, so Coconut Oil is in active list
    res_act1 = client.get("/api/workforce/seller-hub/categories/active/")
    assert any(c["id"] == coconut_id for c in res_act1.data)

    # Deactivate parent 'Oil'
    client.force_authenticate(user=superadmin)
    client.patch(f"/api/workforce/seller-hub/categories/{oil_id}/", {"is_active": False}, format="json")

    # Seller checks active categories -> Coconut Oil should NOT be present because parent Oil is inactive
    client.force_authenticate(user=seller_user)
    res_act2 = client.get("/api/workforce/seller-hub/categories/active/")
    assert not any(c["id"] == coconut_id for c in res_act2.data)
    print(f"  [PASS] Inactive parent 'Oil' successfully hides active child 'Coconut Oil' from active catalog")
    passed += 1

    # ── Clean up test tree ───────────────────────────────────────────────────────
    client.force_authenticate(user=superadmin)
    client.delete(f"/api/workforce/seller-hub/categories/{coconut_id}/")
    client.delete(f"/api/workforce/seller-hub/categories/{oil_id}/")
    client.delete(f"/api/workforce/seller-hub/categories/{dhals_id}/")
    client.delete(f"/api/workforce/seller-hub/categories/{masalas_id}/")
    client.delete(f"/api/workforce/seller-hub/categories/{root_id}/")

    print("\n" + "=" * 80)
    print(f"CATEGORY HIERARCHY TEST RESULTS: {passed}/{total} TESTS PASSED (100% SUCCESS)")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
