"""
workforce_api/views_marketplace_integration.py

Phase 8A: Vendor-side Public Customer Marketplace Integration APIs.
Enables Sevo-customer to securely query published products, validate cart pricing and stock,
intake canonical customer orders with atomic inventory reservation, and release reservations
upon order cancellation with strict idempotency and zero mock data.
"""

import uuid
import logging
from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

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
    SellerOrderStatusOutbox,
)
from workforce_api.permissions import IsMarketplaceIntegrationCaller
from workforce_api.serializers import (
    SellerOrderDetailSerializer,
)
from workforce_api.services.seller_order_outbox import record_seller_order_status_event

logger = logging.getLogger(__name__)


# ─── Category Lineage Helpers ─────────────────────────────────────────────────

def get_active_seller_category_ids():
    """
    Returns a set of category IDs where the category AND all of its parent
    ancestors in the tree are marked is_active=True.
    Safe against cycles, memory efficient, and runs in O(N).
    """
    cats = list(SellerHubCategory.objects.all().values("id", "parent_id", "is_active"))
    cat_by_id = {c["id"]: c for c in cats}
    active_ids = set()

    for c in cats:
        curr = c
        all_active = True
        visited = set()
        while curr:
            if curr["id"] in visited:
                all_active = False
                break
            visited.add(curr["id"])
            if not curr["is_active"]:
                all_active = False
                break
            parent_id = curr["parent_id"]
            curr = cat_by_id.get(parent_id) if parent_id else None
        if all_active:
            active_ids.add(c["id"])
    return active_ids


def get_descendant_category_ids(root_category_id):
    """
    Returns a set containing root_category_id and all its descendant category IDs.
    """
    cats = list(SellerHubCategory.objects.all().values("id", "parent_id"))
    descendants = {root_category_id}
    changed = True
    while changed:
        changed = False
        for c in cats:
            if c["id"] not in descendants and c["parent_id"] in descendants:
                descendants.add(c["id"])
                changed = True
    return descendants


def build_category_path(category):
    """
    Constructs a human-readable breadcrumb path, e.g. 'Groceries > Fresh Produce > Fruits'.
    """
    if not category:
        return ""
    names = []
    curr = category
    visited = set()
    while curr and curr.id not in visited:
        visited.add(curr.id)
        names.append(curr.name)
        curr = curr.parent
    return " > ".join(reversed(names))


def build_category_hierarchy(category):
    """
    Constructs list of breadcrumb items from root to leaf.
    """
    if not category:
        return []
    items = []
    curr = category
    visited = set()
    while curr and curr.id not in visited:
        visited.add(curr.id)
        items.append({
            "id": curr.id,
            "name": curr.name,
            "slug": curr.slug,
        })
        curr = curr.parent
    return list(reversed(items))


def get_sellable_products_queryset(active_cat_ids=None):
    """
    Shared authoritative queryset for sellable marketplace products.
    Conditions:
      - status == APPROVED (and not paused/rejected/draft)
      - company__is_active == True
      - category_id in active_cat_ids (active category and entire ancestor chain active)
      - inventory available qty > 0 (on_hand_qty > reserved_qty)
    """
    if active_cat_ids is None:
        active_cat_ids = get_active_seller_category_ids()
    if not active_cat_ids:
        return SellerProduct.objects.none()

    return SellerProduct.objects.filter(
        status=SellerProduct.Status.APPROVED,
        company__is_active=True,
        category_id__in=active_cat_ids,
        inventory__on_hand_qty__gt=models.F("inventory__reserved_qty"),
    )


# ─── 1. Public Customer Catalog Integration APIs ──────────────────────────────

class MarketplaceCategoryFeedView(APIView):
    """
    GET /api/workforce/marketplace/categories/
    Read-only server-to-server category feed for the Customer marketplace app.
    Protected by IsMarketplaceIntegrationCaller (Shared Secret / Webhook Secret).
    Returns active categories whose entire ancestor chain is active.

    Query Params:
      - tree (bool): default true. When true, returns nested category tree with children.
      - parent_id (int|null): return direct active children of given parent (null/empty for root).
      - hide_empty (bool): default true. When true, prunes/hides categories with zero
        sellable products across their entire subtree.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def get(self, request):
        # 1. Fetch all categories in 1 query and compute valid active lineage
        all_cats = list(SellerHubCategory.objects.all().order_by("sort_order", "name", "id"))
        cat_by_id = {c.id: c for c in all_cats}

        active_cat_ids = set()
        for c in all_cats:
            curr = c
            all_active = True
            visited = set()
            while curr:
                if curr.id in visited:
                    all_active = False
                    break
                visited.add(curr.id)
                if not curr.is_active:
                    all_active = False
                    break
                parent_id = curr.parent_id
                curr = cat_by_id.get(parent_id) if parent_id else None
            if all_active:
                active_cat_ids.add(c.id)

        active_cats = [c for c in all_cats if c.id in active_cat_ids]
        cat_map = {c.id: c for c in active_cats}
        children_map = {}
        for c in active_cats:
            children_map.setdefault(c.parent_id, []).append(c.id)

        # 2. Fetch direct sellable product counts grouped by category in 1 query
        direct_counts = {}
        if active_cat_ids:
            cnt_rows = (
                get_sellable_products_queryset(active_cat_ids)
                .values("category_id")
                .annotate(cnt=models.Count("id"))
                .values_list("category_id", "cnt")
            )
            direct_counts = dict(cnt_rows)

        # 3. Compute total_product_count rollups (category + all active descendants) in memory O(N)
        total_counts = {}
        def get_total_count(cat_id):
            if cat_id in total_counts:
                return total_counts[cat_id]
            cnt = direct_counts.get(cat_id, 0)
            for child_id in children_map.get(cat_id, []):
                cnt += get_total_count(child_id)
            total_counts[cat_id] = cnt
            return cnt

        for c in active_cats:
            get_total_count(c.id)

        # Helper: compute path breadcrumbs from root to category
        def compute_path(cat_id):
            path = []
            curr_id = cat_id
            visited = set()
            while curr_id is not None and curr_id in cat_map and curr_id not in visited:
                visited.add(curr_id)
                cat = cat_map[curr_id]
                path.append({
                    "id": cat.id,
                    "name": cat.name,
                    "slug": cat.slug,
                })
                curr_id = cat.parent_id
            path.reverse()
            return path

        # Helper: serialize single item
        def serialize_item(cat, children_list=None):
            active_child_ids = children_map.get(cat.id, [])
            has_children = len(active_child_ids) > 0
            is_leaf = not has_children
            path = compute_path(cat.id)
            path_string = " > ".join(p["name"] for p in path)
            item = {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "parent_id": cat.parent_id,
                "sort_order": cat.sort_order,
                "icon": cat.icon or "",
                "image": cat.image or "",
                "is_leaf": is_leaf,
                "has_children": has_children,
                "path": path,
                "path_string": path_string,
                "product_count": direct_counts.get(cat.id, 0),
                "total_product_count": total_counts.get(cat.id, 0),
            }
            if children_list is not None:
                item["children"] = children_list
            return item

        # Parse query params
        hide_empty_param = request.query_params.get("hide_empty")
        hide_empty = True if hide_empty_param is None or str(hide_empty_param).lower() in ("true", "1") else False

        parent_id_param = request.query_params.get("parent_id")
        tree_param = request.query_params.get("tree")

        # 1. parent_id mode (one level)
        if parent_id_param is not None:
            if str(parent_id_param).lower() in ("null", "none", "", "0"):
                target_parent = None
            elif str(parent_id_param).isdigit():
                target_parent = int(parent_id_param)
            else:
                return Response([], status=status.HTTP_200_OK)

            matching_ids = children_map.get(target_parent, [])
            if hide_empty:
                matching_ids = [cid for cid in matching_ids if total_counts.get(cid, 0) > 0]

            results = [serialize_item(cat_map[cid]) for cid in matching_ids if cid in cat_map]
            return Response(results, status=status.HTTP_200_OK)

        # 2. Flat mode if tree=false
        if tree_param is not None and str(tree_param).lower() in ("false", "0"):
            results = []
            for c in active_cats:
                if hide_empty and total_counts.get(c.id, 0) == 0:
                    continue
                results.append(serialize_item(c))
            return Response(results, status=status.HTTP_200_OK)

        # 3. Default: Nested tree mode (tree=true)
        def build_tree_node(cat_id):
            cat = cat_map[cat_id]
            child_ids = children_map.get(cat_id, [])
            if hide_empty:
                child_ids = [cid for cid in child_ids if total_counts.get(cid, 0) > 0]
            children_items = [build_tree_node(cid) for cid in child_ids]
            return serialize_item(cat, children_list=children_items)

        root_ids = children_map.get(None, [])
        if hide_empty:
            root_ids = [rid for rid in root_ids if total_counts.get(rid, 0) > 0]

        tree_data = [build_tree_node(rid) for rid in root_ids]
        return Response(tree_data, status=status.HTTP_200_OK)


MarketplaceCategoryListView = MarketplaceCategoryFeedView


class MarketplaceProductListView(APIView):
    """
    GET /api/workforce/marketplace/products/
    Public read-only customer catalog feed.
    Shows ONLY products that are:
      - SellerProduct status APPROVED (and not paused/rejected/draft)
      - Seller company is active (is_active=True)
      - Category and all ancestor categories are active (is_active=True)
      - Available inventory quantity > 0 (on_hand_qty - reserved_qty > 0)
    Supports search, category filtering, seller filtering, and pagination.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def get(self, request):
        active_cat_ids = get_active_seller_category_ids()
        if not active_cat_ids:
            return Response({
                "count": 0,
                "page": 1,
                "page_size": 20,
                "total_pages": 0,
                "results": [],
            }, status=status.HTTP_200_OK)

        # Base Published Filter (reusing shared helper)
        queryset = get_sellable_products_queryset(active_cat_ids).select_related(
            "company", "category", "category__parent", "inventory"
        ).prefetch_related("images")

        # 1. Search Query
        search_query = request.query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                models.Q(title__icontains=search_query)
                | models.Q(brand__icontains=search_query)
                | models.Q(sku__icontains=search_query)
                | models.Q(description__icontains=search_query)
            )

        # 2. Category Filter (by ID or Slug, including sub-tree descendants)
        cat_id_param = request.query_params.get("category_id")
        cat_slug_param = request.query_params.get("category_slug", "").strip()

        if cat_id_param is not None or cat_slug_param:
            target_cat_id = None
            if cat_id_param is not None:
                try:
                    target_cat_id = int(cat_id_param)
                except (ValueError, TypeError):
                    return Response(
                        {"error": "Category not found.", "code": "CATEGORY_NOT_FOUND"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                if target_cat_id not in active_cat_ids:
                    return Response(
                        {"error": "Category not found or inactive.", "code": "CATEGORY_NOT_FOUND"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
            elif cat_slug_param:
                cat_obj = SellerHubCategory.objects.filter(slug=cat_slug_param).first()
                if not cat_obj or cat_obj.id not in active_cat_ids:
                    return Response(
                        {"error": "Category not found or inactive.", "code": "CATEGORY_NOT_FOUND"},
                        status=status.HTTP_404_NOT_FOUND,
                    )
                target_cat_id = cat_obj.id

            if target_cat_id is not None:
                filter_cat_ids = get_descendant_category_ids(target_cat_id).intersection(active_cat_ids)
                queryset = queryset.filter(category_id__in=filter_cat_ids)

        # 3. Store / Seller Filter
        seller_id = request.query_params.get("company_id") or request.query_params.get("seller_id")
        if seller_id:
            try:
                queryset = queryset.filter(company_id=int(seller_id))
            except ValueError:
                pass

        # Order by sort
        queryset = queryset.order_by("title", "id")

        # Pagination
        try:
            page = max(1, int(request.query_params.get("page", 1)))
            page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except ValueError:
            page, page_size = 1, 20

        total_count = queryset.count()
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_items = queryset[start_idx:end_idx]

        results = []
        for p in page_items:
            inv = getattr(p, "inventory", None)
            avail_qty = max(Decimal("0.000"), (inv.on_hand_qty - inv.reserved_qty)) if inv else Decimal("0.000")

            primary_img = ""
            gallery = []
            for img in p.images.all():
                if img.image_url:
                    gallery.append(img.image_url)
                    if img.is_primary and not primary_img:
                        primary_img = img.image_url
            if not primary_img and gallery:
                primary_img = gallery[0]

            cat_path = build_category_path(p.category)
            cat_hierarchy = build_category_hierarchy(p.category)
            results.append({
                "id": p.id,
                "sku": p.sku,
                "title": p.title,
                "brand": p.brand or "",
                "unit": p.unit,
                "pack_size": str(p.pack_size),
                "mrp": str(p.mrp),
                "selling_price": str(p.selling_price),
                "currency": "INR",
                "primary_image": primary_img,
                "images": gallery,
                "description": p.description or "",
                "storage_info": p.storage_info or "",
                "expiry_info": p.expiry_info or "",
                "tax_rate": str(p.tax_rate),
                "hsn_code": p.hsn_code or "",
                "seller_id": p.company.id,
                "seller_name": p.company.company_name,
                "category_path": cat_path,
                "category_hierarchy": cat_hierarchy,
                "available_stock": float(round(avail_qty, 3)) if (avail_qty % 1) != 0 else int(avail_qty),
                "in_stock": avail_qty > Decimal("0.000"),
                "seller": {
                    "id": p.company.id,
                    "name": p.company.company_name,
                    "slug": p.company.slug,
                },
                "category": {
                    "id": p.category.id,
                    "name": p.category.name,
                    "slug": p.category.slug,
                    "path": cat_path,
                    "hierarchy": cat_hierarchy,
                },
                "availability": {
                    "in_stock": avail_qty > Decimal("0.000"),
                    "available_quantity": str(round(avail_qty, 3)),
                    "unit": p.unit,
                },
                "updated_at": p.updated_at.isoformat() if p.updated_at else "",
            })

        return Response({
            "count": total_count,
            "page": page,
            "page_size": page_size,
            "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
            "results": results,
        }, status=status.HTTP_200_OK)


class MarketplaceProductDetailView(APIView):
    """
    GET /api/workforce/marketplace/products/<int:pk>/
    Public product detail endpoint. Returns 404 if product is not eligible for publication.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def get(self, request, pk):
        active_cat_ids = get_active_seller_category_ids()
        p = SellerProduct.objects.filter(
            pk=pk,
            status=SellerProduct.Status.APPROVED,
            company__is_active=True,
            category_id__in=active_cat_ids,
        ).select_related("company", "category", "category__parent", "inventory").prefetch_related("images").first()

        if not p:
            return Response({"error": "Product not found or unavailable."}, status=status.HTTP_404_NOT_FOUND)

        inv = getattr(p, "inventory", None)
        avail_qty = max(Decimal("0.000"), (inv.on_hand_qty - inv.reserved_qty)) if inv else Decimal("0.000")
        if avail_qty <= Decimal("0.000"):
            return Response({"error": "Product is currently out of stock."}, status=status.HTTP_404_NOT_FOUND)

        primary_img = ""
        gallery = []
        for img in p.images.all():
            if img.image_url:
                gallery.append(img.image_url)
                if img.is_primary and not primary_img:
                    primary_img = img.image_url
        if not primary_img and gallery:
            primary_img = gallery[0]

        cat_path = build_category_path(p.category)
        cat_hierarchy = build_category_hierarchy(p.category)
        return Response({
            "id": p.id,
            "sku": p.sku,
            "title": p.title,
            "brand": p.brand or "",
            "unit": p.unit,
            "pack_size": str(p.pack_size),
            "mrp": str(p.mrp),
            "selling_price": str(p.selling_price),
            "currency": "INR",
            "primary_image": primary_img,
            "images": gallery,
            "description": p.description or "",
            "storage_info": p.storage_info or "",
            "expiry_info": p.expiry_info or "",
            "tax_rate": str(p.tax_rate),
            "hsn_code": p.hsn_code or "",
            "seller_id": p.company.id,
            "seller_name": p.company.company_name,
            "category_path": cat_path,
            "category_hierarchy": cat_hierarchy,
            "available_stock": float(round(avail_qty, 3)) if (avail_qty % 1) != 0 else int(avail_qty),
            "in_stock": avail_qty > Decimal("0.000"),
            "seller": {
                "id": p.company.id,
                "name": p.company.company_name,
                "slug": p.company.slug,
            },
            "category": {
                "id": p.category.id,
                "name": p.category.name,
                "slug": p.category.slug,
                "path": cat_path,
                "hierarchy": cat_hierarchy,
            },
            "availability": {
                "in_stock": avail_qty > Decimal("0.000"),
                "available_quantity": str(round(avail_qty, 3)),
                "unit": p.unit,
            },
            "updated_at": p.updated_at.isoformat() if p.updated_at else "",
        }, status=status.HTTP_200_OK)


# ─── 2. Customer-Cart Validation API ──────────────────────────────────────────

class MarketplaceCartValidateView(APIView):
    """
    POST /api/workforce/marketplace/cart/validate/
    Secure server-to-server endpoint for Sevo-customer to validate live product
    availability, active status, store consistency, and authoritative prices before checkout.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def post(self, request):
        items_payload = request.data.get("items")
        if not items_payload or not isinstance(items_payload, list):
            return Response(
                {"error": "A non-empty 'items' list is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        seller_id = request.data.get("seller_id") or request.data.get("company_id")
        active_cat_ids = get_active_seller_category_ids()

        validated_items = []
        errors = []
        subtotal = Decimal("0.00")

        product_ids = [item.get("product_id") for item in items_payload if isinstance(item, dict) and item.get("product_id")]
        products = {
            p.id: p
            for p in SellerProduct.objects.filter(id__in=product_ids).select_related("company", "category", "inventory")
        }

        for idx, item in enumerate(items_payload):
            if not isinstance(item, dict):
                continue
            p_id = item.get("product_id")
            # Support quantity / requested_quantity
            qty_val = item.get("quantity") if item.get("quantity") is not None else item.get("requested_quantity", 1)
            try:
                req_qty = Decimal(str(qty_val))
            except Exception:
                req_qty = Decimal("1.000")

            expected_price = item.get("expected_unit_price") or item.get("expected_price") or item.get("unit_price")

            if req_qty <= Decimal("0.000"):
                errors.append({
                    "product_id": p_id,
                    "code": "INVALID_QUANTITY",
                    "message": f"Requested quantity for product #{p_id} must be greater than zero.",
                })
                validated_items.append({
                    "product_id": p_id,
                    "status": "INVALID_QUANTITY",
                    "is_available": False,
                    "requested_quantity": str(round(req_qty, 3)),
                    "available_quantity": "0.000",
                    "error": "Quantity must be greater than zero.",
                })
                continue

            product = products.get(p_id)
            if not product:
                errors.append({
                    "product_id": p_id,
                    "code": "PRODUCT_NOT_FOUND",
                    "message": f"Product #{p_id} not found in seller catalog.",
                })
                validated_items.append({
                    "product_id": p_id,
                    "status": "UNAVAILABLE",
                    "is_available": False,
                    "requested_quantity": str(round(req_qty, 3)),
                    "available_quantity": "0.000",
                    "error": "Product not found.",
                })
                continue

            # 1. Product Status Check
            if product.status != SellerProduct.Status.APPROVED:
                errors.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "code": "PRODUCT_UNAVAILABLE",
                    "message": f"Product '{product.title}' is not approved for sale (Status: {product.status}).",
                })
                validated_items.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "status": "UNAVAILABLE",
                    "is_available": False,
                    "requested_quantity": str(round(req_qty, 3)),
                    "available_quantity": "0.000",
                    "current_selling_price": str(product.selling_price),
                    "error": f"Product is {product.status.lower()}.",
                })
                continue

            # 2. Company Active Check
            if not product.company or not product.company.is_active:
                errors.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "code": "STORE_INACTIVE",
                    "message": f"Merchant store '{getattr(product.company, 'company_name', '')}' is currently inactive.",
                })
                validated_items.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "status": "STORE_INACTIVE",
                    "is_available": False,
                    "requested_quantity": str(round(req_qty, 3)),
                    "available_quantity": "0.000",
                    "current_selling_price": str(product.selling_price),
                    "error": "Store is inactive.",
                })
                continue

            # 3. Single-Store Consistency Check (if seller_id provided)
            if seller_id and str(product.company_id) != str(seller_id):
                errors.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "code": "STORE_MISMATCH",
                    "message": f"Product '{product.title}' belongs to another merchant store.",
                })
                validated_items.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "status": "STORE_MISMATCH",
                    "is_available": False,
                    "requested_quantity": str(round(req_qty, 3)),
                    "available_quantity": "0.000",
                    "current_selling_price": str(product.selling_price),
                    "error": "Store mismatch.",
                })
                continue

            # 4. Active Category Lineage Check
            if product.category_id not in active_cat_ids:
                errors.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "code": "CATEGORY_DISABLED",
                    "message": f"Category for product '{product.title}' is currently inactive.",
                })
                validated_items.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "status": "CATEGORY_DISABLED",
                    "is_available": False,
                    "requested_quantity": str(round(req_qty, 3)),
                    "available_quantity": "0.000",
                    "current_selling_price": str(product.selling_price),
                    "error": "Category is disabled.",
                })
                continue

            # 5. Live Stock Availability Check
            inv = getattr(product, "inventory", None)
            avail_qty = max(Decimal("0.000"), (inv.on_hand_qty - inv.reserved_qty)) if inv else Decimal("0.000")

            if avail_qty < req_qty:
                avail_disp = float(round(avail_qty, 3)) if (avail_qty % 1) != 0 else int(avail_qty)
                req_disp = float(round(req_qty, 3)) if (req_qty % 1) != 0 else int(req_qty)
                errors.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "code": "INSUFFICIENT_STOCK",
                    "available_quantity": avail_disp,
                    "requested_quantity": req_disp,
                    "message": f"Only {avail_disp} unit(s) available for '{product.title}' (Requested: {req_disp}).",
                })
                validated_items.append({
                    "product_id": p_id,
                    "sku": product.sku,
                    "title": product.title,
                    "status": "INSUFFICIENT_STOCK",
                    "is_available": False,
                    "requested_quantity": req_disp,
                    "available_quantity": avail_disp,
                    "current_selling_price": str(product.selling_price),
                    "error": f"Only {avail_disp} units available.",
                })
                continue

            # Price check
            price_changed = False
            if expected_price is not None:
                try:
                    if Decimal(str(expected_price)) != product.selling_price:
                        price_changed = True
                        errors.append({
                            "product_id": p_id,
                            "code": "PRICE_CHANGED",
                            "expected_price": str(expected_price),
                            "current_price": str(product.selling_price),
                            "message": f"Price for '{product.title}' updated from {expected_price} to {product.selling_price}.",
                        })
                except Exception:
                    pass

            line_total = product.selling_price * req_qty
            subtotal += line_total

            avail_disp = float(round(avail_qty, 3)) if (avail_qty % 1) != 0 else int(avail_qty)
            req_disp = float(round(req_qty, 3)) if (req_qty % 1) != 0 else int(req_qty)

            validated_items.append({
                "product_id": product.id,
                "sku": product.sku,
                "title": product.title,
                "company_id": product.company.id,
                "seller_name": product.company.company_name,
                "requested_quantity": req_disp,
                "available_quantity": avail_disp,
                "mrp": str(product.mrp),
                "selling_price": str(product.selling_price),
                "current_selling_price": str(product.selling_price),
                "unit_price": str(product.selling_price),
                "line_total": str(round(line_total, 2)),
                "tax_rate": str(product.tax_rate),
                "hsn_code": product.hsn_code or "",
                "status": "AVAILABLE",
                "is_available": True,
                "price_changed": price_changed,
                "error": None,
            })

        is_valid = len(errors) == 0

        return Response({
            "is_valid": is_valid,
            "items": validated_items,
            "subtotal": str(round(subtotal, 2)),
            "currency": "INR",
            "errors": errors,
        }, status=status.HTTP_200_OK)


# ─── 3. Canonical Customer-Order Intake API ───────────────────────────────────

class MarketplaceOrderIntakeView(APIView):
    """
    POST /api/workforce/marketplace/orders/intake/
    Idempotent Seller Order creation and atomic inventory reservation endpoint.
    Called server-to-server by Sevo-customer backend upon confirmed checkout.
    Strictly validates authoritative pricing, active lineage, and creates transactional outbox event.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def post(self, request):
        source_order_id = str(request.data.get("source_order_id") or "").strip()
        if not source_order_id:
            return Response(
                {"error": "Missing mandatory 'source_order_id' canonical reference.", "code": "MISSING_SOURCE_ORDER_ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        company_id = request.data.get("company_id") or request.data.get("seller_id")
        if not company_id:
            return Response(
                {"error": "Missing mandatory 'company_id' merchant reference.", "code": "MISSING_COMPANY_ID"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items_payload = request.data.get("items")
        if not items_payload or not isinstance(items_payload, list):
            return Response(
                {"error": "Non-empty 'items' list is required.", "code": "INVALID_ITEMS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Fast Idempotency Check: Existing Order Lookup ─────────────────────
        existing_order = SellerOrder.objects.filter(source_order_id=source_order_id).first()
        if existing_order:
            logger.info(f"[ORDER_INTAKE] Duplicate intake for source_order_id '{source_order_id}'. Returning existing Order #{existing_order.order_number}.")
            return Response(
                {
                    "message": f"Order #{existing_order.order_number} already intaken.",
                    "created": False,
                    "is_idempotent_replay": True,
                    "order": SellerOrderDetailSerializer(existing_order).data,
                },
                status=status.HTTP_200_OK,
            )

        # ── Payload Validation: Duplicate Lines & Positive Quantities ─────────
        seen_product_ids = set()
        for idx, item in enumerate(items_payload):
            if not isinstance(item, dict):
                return Response(
                    {"error": f"Item at index {idx} must be a JSON object.", "code": "INVALID_PAYLOAD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            p_id = item.get("product_id")
            if not p_id or not isinstance(p_id, int):
                return Response(
                    {"error": f"Missing or invalid product_id at index {idx}.", "code": "INVALID_PRODUCT_ID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if p_id in seen_product_ids:
                return Response(
                    {"error": f"Duplicate product_id #{p_id} in intake items payload.", "code": "DUPLICATE_PRODUCT_LINE"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            seen_product_ids.add(p_id)

            raw_qty = item.get("quantity") if item.get("quantity") is not None else item.get("requested_quantity")
            if raw_qty is None:
                return Response(
                    {"error": f"Missing quantity for product #{p_id}.", "code": "INVALID_QUANTITY"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                qty = Decimal(str(raw_qty))
            except Exception:
                return Response(
                    {"error": f"Non-numeric quantity for product #{p_id}.", "code": "INVALID_QUANTITY"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if qty <= Decimal("0.000"):
                return Response(
                    {"error": f"Quantity for product #{p_id} must be greater than zero.", "code": "INVALID_QUANTITY"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Customer & Delivery Snapshots
        customer_name = str(request.data.get("customer_name") or "Valued Customer").strip()
        customer_phone = str(request.data.get("customer_phone") or "").strip()

        addr_val = request.data.get("delivery_address")
        if isinstance(addr_val, dict):
            parts = [str(v) for k, v in addr_val.items() if v]
            delivery_address = ", ".join(parts)
        elif addr_val is not None:
            delivery_address = str(addr_val).strip()
        else:
            delivery_address = ""

        delivery_slot = str(request.data.get("delivery_slot") or "").strip()
        delivery_notes = str(request.data.get("delivery_notes") or "").strip()

        pay_snapshot = request.data.get("payment_snapshot")
        if isinstance(pay_snapshot, dict):
            payment_method = str(pay_snapshot.get("method") or "ONLINE").strip()
            payment_status = str(pay_snapshot.get("status") or "PAID").strip()
        else:
            payment_method = str(request.data.get("payment_method") or "ONLINE").strip()
            payment_status = str(request.data.get("payment_status") or "PAID").strip()

        # ── Atomic Stock Reservation, Validation & Order Creation ─────────────
        product_ids = list(seen_product_ids)
        active_cat_ids = get_active_seller_category_ids()

        with transaction.atomic():
            # 1. Check & lock company
            company = Company.objects.select_for_update().filter(pk=company_id, is_active=True).first()
            if not company:
                return Response(
                    {"error": f"Active Seller Company #{company_id} not found.", "code": "STORE_INACTIVE"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # 2. Lock inventories for update
            inventories = {
                inv.product_id: inv
                for inv in SellerInventory.objects.select_for_update().filter(
                    company=company,
                    product_id__in=product_ids,
                ).select_related("product")
            }

            total_amount = Decimal("0.00")
            parsed_items = []

            for item in items_payload:
                p_id = item["product_id"]
                raw_qty = item.get("quantity") if item.get("quantity") is not None else item.get("requested_quantity")
                qty = Decimal(str(raw_qty))

                inv = inventories.get(p_id)
                if not inv:
                    return Response(
                        {
                            "error": f"Inventory record not found for product #{p_id} in seller store.",
                            "code": "INVENTORY_NOT_FOUND",
                            "product_id": p_id,
                        },
                        status=status.HTTP_404_NOT_FOUND,
                    )

                product = inv.product
                if product.company_id != company.id:
                    return Response(
                        {
                            "error": f"Product #{p_id} does not belong to seller store #{company.id}.",
                            "code": "STORE_MISMATCH",
                            "product_id": p_id,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if product.status != SellerProduct.Status.APPROVED:
                    return Response(
                        {
                            "error": f"Product '{product.title}' is not approved for sale (Status: {product.status}).",
                            "code": "PRODUCT_NOT_APPROVED",
                            "product_id": p_id,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if product.category_id not in active_cat_ids:
                    return Response(
                        {
                            "error": f"Category for product '{product.title}' is currently inactive.",
                            "code": "CATEGORY_DISABLED",
                            "product_id": p_id,
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                avail_qty = max(Decimal("0.000"), inv.on_hand_qty - inv.reserved_qty)
                if avail_qty < qty:
                    avail_disp = float(round(avail_qty, 3)) if (avail_qty % 1) != 0 else int(avail_qty)
                    req_disp = float(round(qty, 3)) if (qty % 1) != 0 else int(qty)
                    return Response(
                        {
                            "error": f"Insufficient stock for '{product.title}'. Only {avail_disp} available, requested {req_disp}.",
                            "code": "INSUFFICIENT_STOCK",
                            "error_code": "INSUFFICIENT_STOCK",
                            "product_id": p_id,
                            "available_quantity": str(round(avail_qty, 3)),
                            "requested_quantity": str(round(qty, 3)),
                        },
                        status=status.HTTP_409_CONFLICT,
                    )

                # Authoritative Price Verification
                caller_price = item.get("expected_unit_price") if item.get("expected_unit_price") is not None else (item.get("expected_price") if item.get("expected_price") is not None else item.get("unit_price"))
                if caller_price is not None:
                    try:
                        passed_dec = Decimal(str(caller_price))
                        if passed_dec != product.selling_price:
                            return Response(
                                {
                                    "error": f"Price for product '{product.title}' has changed. Current selling price is {product.selling_price}, but order specified {passed_dec}.",
                                    "code": "PRICE_CHANGED",
                                    "error_code": "PRICE_CHANGED",
                                    "product_id": p_id,
                                    "expected_price": str(passed_dec),
                                    "current_price": str(product.selling_price),
                                },
                                status=status.HTTP_409_CONFLICT,
                            )
                    except Exception:
                        pass

                unit_price = product.selling_price
                line_total = unit_price * qty
                total_amount += line_total

                parsed_items.append({
                    "product": product,
                    "inventory": inv,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "mrp": product.mrp,
                    "line_total": line_total,
                })

            # Generate Order Number
            now = timezone.now()
            order_number = f"SO-{now.strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

            # Race-safe insertion catching duplicate source_order_id
            try:
                order = SellerOrder.objects.create(
                    source_order_id=source_order_id,
                    company=company,
                    order_number=order_number,
                    customer_name=customer_name,
                    customer_phone=customer_phone,
                    delivery_address=delivery_address,
                    delivery_slot=delivery_slot,
                    delivery_notes=delivery_notes,
                    payment_method=payment_method,
                    payment_status=payment_status if payment_status in SellerOrder.PaymentStatus.values else SellerOrder.PaymentStatus.PAID,
                    total_amount=total_amount,
                    status=SellerOrder.Status.NEW,
                )
            except Exception as exc:
                # Concurrent race replay
                existing_order = SellerOrder.objects.filter(source_order_id=source_order_id).first()
                if existing_order:
                    logger.info(f"[ORDER_INTAKE] Concurrent intake race for '{source_order_id}'. Returning existing order.")
                    return Response(
                        {
                            "message": f"Order #{existing_order.order_number} already intaken.",
                            "created": False,
                            "is_idempotent_replay": True,
                            "order": SellerOrderDetailSerializer(existing_order).data,
                        },
                        status=status.HTTP_200_OK,
                    )
                raise exc

            # Reserve Inventory & Create Order Items
            for p_item in parsed_items:
                product = p_item["product"]
                inv = p_item["inventory"]
                qty = p_item["quantity"]

                inv.reserved_qty += qty
                inv.save(update_fields=["reserved_qty", "updated_at"])

                SellerInventoryMovement.objects.create(
                    inventory=inv,
                    movement_type=SellerInventoryMovement.MovementType.RESERVED,
                    quantity_change=Decimal("0.000"),
                    balance_before=inv.on_hand_qty,
                    balance_after=inv.on_hand_qty,
                    reason=f"Stock reserved for customer order #{order.order_number} (source: {source_order_id})",
                    reference_id=source_order_id,
                    actor=None,
                )

                SellerOrderItem.objects.create(
                    order=order,
                    product=product,
                    product_title=product.title,
                    sku=product.sku,
                    unit=product.unit or "",
                    pack_size=str(product.pack_size or ""),
                    ordered_quantity=qty,
                    unit_price=p_item["unit_price"],
                    line_total=p_item["line_total"],
                )

            # Audit Log
            SellerOrderAuditLog.objects.create(
                order=order,
                from_status="",
                to_status=SellerOrder.Status.NEW,
                action="ORDER_INTAKE",
                actor=None,
                notes=f"Canonical source order '{source_order_id}' created with atomic inventory reservation.",
            )

            # Outbox Event
            record_seller_order_status_event(
                order=order,
                previous_status="",
                new_status=SellerOrder.Status.NEW,
                event_type="seller_order.created",
                actor=None,
                cancellation_source=None,
            )

        logger.info(f"[ORDER_INTAKE] Successfully created SellerOrder #{order.order_number} for source_order_id '{source_order_id}'.")
        fresh_order = SellerOrder.objects.filter(pk=order.pk).prefetch_related("items", "audit_logs").first() or order
        return Response(
            {
                "message": f"Seller Order #{order.order_number} created and inventory reserved.",
                "created": True,
                "order": SellerOrderDetailSerializer(fresh_order).data,
            },
            status=status.HTTP_201_CREATED,
        )


# ─── 4. Customer-Order Cancellation & Reservation Release API ─────────────────

class MarketplaceOrderCancelReleaseView(APIView):
    """
    POST /api/workforce/marketplace/orders/<str:source_order_id>/cancel/
    Idempotent cancellation and reservation release endpoint called when customer
    cancels an order prior to delivery.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def post(self, request, source_order_id):
        cancellation_reason = request.data.get("cancellation_reason", "Customer cancelled before handover").strip()

        with transaction.atomic():
            order = SellerOrder.objects.select_for_update().filter(source_order_id=source_order_id).first()
            if not order:
                return Response(
                    {"error": f"Seller Order for source_order_id '{source_order_id}' not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # Idempotency: Already cancelled order
            if order.status == SellerOrder.Status.CANCELLED:
                return Response(
                    {
                        "message": f"Order #{order.order_number} is already cancelled.",
                        "already_cancelled": True,
                        "order": SellerOrderDetailSerializer(order).data,
                    },
                    status=status.HTTP_200_OK,
                )

            # Check if order is in a cancellable pre-handover state
            if order.status in (SellerOrder.Status.HANDED_OVER, SellerOrder.Status.DELIVERED):
                return Response(
                    {
                        "error": f"Cannot cancel order #{order.order_number} in '{order.status}' status (already handed over/delivered).",
                        "current_status": order.status,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            from_status = order.status
            now = timezone.now()

            # Release reserved inventory allocations
            for item in order.items.select_related("product"):
                if not item.product:
                    continue
                inv = SellerInventory.objects.select_for_update().filter(
                    company=order.company,
                    product=item.product,
                ).first()
                if not inv:
                    continue

                qty_to_release = item.ordered_quantity
                inv.reserved_qty = max(Decimal("0.000"), inv.reserved_qty - qty_to_release)
                inv.save(update_fields=["reserved_qty", "updated_at"])

                # Record RESERVATION_RELEASED movement
                SellerInventoryMovement.objects.create(
                    inventory=inv,
                    batch=item.batch,
                    movement_type=SellerInventoryMovement.MovementType.RESERVATION_RELEASED,
                    quantity_change=Decimal("0.000"),
                    balance_before=inv.on_hand_qty,
                    balance_after=inv.on_hand_qty,
                    reason=f"Reservation released for cancelled order #{order.order_number} (source: {source_order_id}): {cancellation_reason}",
                    reference_id=source_order_id,
                    actor=None,
                )

            # Transition Order to CANCELLED
            order.status = SellerOrder.Status.CANCELLED
            order.cancelled_at = now
            order.cancellation_reason = cancellation_reason
            order.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])

            # Create Audit Log
            SellerOrderAuditLog.objects.create(
                order=order,
                from_status=from_status,
                to_status=SellerOrder.Status.CANCELLED,
                action="CANCELLED_BY_INTEGRATION",
                actor=None,
                notes=cancellation_reason,
            )

            # Outbox Event
            record_seller_order_status_event(
                order=order,
                previous_status=from_status,
                new_status=SellerOrder.Status.CANCELLED,
                event_type="seller_order.cancelled",
                actor=None,
                cancellation_source="MARKETPLACE",
            )

        logger.info(f"[ORDER_CANCEL] Successfully cancelled SellerOrder #{order.order_number} and released reservations.")
        return Response(
            {
                "message": f"Order #{order.order_number} cancelled and reservations released successfully.",
                "already_cancelled": False,
                "order_status": "CANCELLED",
                "released_reservations_count": order.items.count(),
                "order": SellerOrderDetailSerializer(order).data,
            },
            status=status.HTTP_200_OK,
        )


# ─── 5. Authoritative Order Status Pull Fallback API ──────────────────────────

class MarketplaceOrderStatusView(APIView):
    """
    GET /api/workforce/marketplace/orders/<str:source_order_id>/status/
    Authoritative state pull fallback for Sevo-Customer marketplace backend.
    Protected by IsMarketplaceIntegrationCaller.
    """
    authentication_classes = []
    permission_classes = [IsMarketplaceIntegrationCaller]

    def get(self, request, source_order_id):
        order = SellerOrder.objects.filter(source_order_id=source_order_id).select_related("company").first()
        if not order:
            return Response(
                {"error": f"Order with source_order_id '{source_order_id}' not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        last_seq = SellerOrderStatusOutbox.objects.filter(order=order).aggregate(
            m=models.Max("sequence")
        )["m"] or 0

        timestamps = {}
        if order.created_at:
            timestamps["created_at"] = order.created_at.isoformat()
        if order.accepted_at:
            timestamps["accepted_at"] = order.accepted_at.isoformat()
        if order.picking_at:
            timestamps["picking_at"] = order.picking_at.isoformat()
        if order.packed_at:
            timestamps["packed_at"] = order.packed_at.isoformat()
        if order.ready_at:
            timestamps["ready_at"] = order.ready_at.isoformat()
        if order.handed_over_at:
            timestamps["handed_over_at"] = order.handed_over_at.isoformat()
        if order.delivered_at:
            timestamps["delivered_at"] = order.delivered_at.isoformat()
        if order.cancelled_at:
            timestamps["cancelled_at"] = order.cancelled_at.isoformat()
        if order.updated_at:
            timestamps["updated_at"] = order.updated_at.isoformat()

        cancelled_by_str = None
        if order.status == SellerOrder.Status.CANCELLED:
            cancelled_by_str = "SELLER" if order.cancelled_by else "INTEGRATION"

        return Response({
            "source_order_id": order.source_order_id,
            "vendor_order_number": order.order_number,
            "vendor_order_id": order.id,
            "seller_id": order.company_id,
            "seller_name": getattr(order.company, "company_name", ""),
            "current_status": order.status,
            "last_event_sequence": last_seq,
            "fulfillment_type": order.fulfillment_type,
            "delivery_slot": order.delivery_slot or "",
            "handover_ref": order.handover_ref or "",
            "status_timestamps": timestamps,
            "cancelled_at": order.cancelled_at.isoformat() if order.cancelled_at else None,
            "cancellation_reason": order.cancellation_reason if order.status == SellerOrder.Status.CANCELLED else None,
            "cancelled_by": cancelled_by_str,
        }, status=status.HTTP_200_OK)
