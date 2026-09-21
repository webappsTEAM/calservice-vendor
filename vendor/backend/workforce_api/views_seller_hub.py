"""
workforce_api/views_seller_hub.py

Dedicated Seller Hub Backend APIs:
1. Seller Hub Categories Management (SellerHubCategory model in workforce_seller_hub_category)
   - Admin/Superadmin management (List, Search, Create, Edit, Toggle Active, Reorder, Safe Deletion)
   - Active categories retrieval for Seller Hub storefront & vendor catalogs
   - Fully isolated from the platform service CatalogCategory table
2. Store & Platform Coupons Management (VendorCoupon model in workforce_vendor_coupon)
   - Admin/Superadmin cross-tenant view and Vendor/Seller store-scoped CRUD
   - Search, Status/Discount filters, Validity dates, Usage limits, and Safe Validation
"""
import csv
import io
import os
import uuid
import logging
from decimal import Decimal, InvalidOperation
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.http import HttpResponse
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from accounts.permissions import is_admin_role
from workforce_api.models import (
    SellerHubCategory,
    VendorCoupon,
    InventoryItem,
    SellerCatalogUploadBatch,
    SellerProduct,
    SellerProductImage,
    SellerProductAuditLog,
    SellerInventory,
    SellerInventoryBatch,
    SellerInventoryMovement,
    SellerOrder,
    SellerOrderItem,
    SellerOrderAuditLog,
    SellerReturn,
    SellerReturnItem,
    SellerReturnAuditLog,
    SellerClaim,
    SellerClaimAuditLog,
)
from workforce_api.serializers import (
    SellerHubCategoryAdminSerializer,
    SellerHubCategoryTreeSerializer,
    SellerCatalogCategoryItemSerializer,
    VendorCouponSerializer,
    SellerProductListSerializer,
    SellerProductDetailSerializer,
    SellerProductCreateUpdateSerializer,
    SellerProductImageSerializer,
    SellerProductAuditLogSerializer,
    validate_product_category_is_leaf,
    SellerCatalogUploadBatchSerializer,
    SellerLeafCategorySerializer,
    SellerInventoryListSerializer,
    SellerInventoryDetailSerializer,
    SellerInventoryMovementSerializer,
    SellerInventoryBatchSerializer,
    SellerInventoryAdjustSerializer,
    SellerOrderListSerializer,
    SellerOrderDetailSerializer,
    SellerOrderItemSerializer,
    SellerOrderAuditLogSerializer,
    SellerOrderStatusTransitionSerializer,
    SellerOrderItemPickSerializer,
    SellerReturnListSerializer,
    SellerReturnDetailSerializer,
    SellerReturnReviewSerializer,
    SellerReturnQualityCheckSerializer,
    SellerReturnRestockSerializer,
    SellerReturnIntakeSerializer,
    SellerClaimListSerializer,
    SellerClaimDetailSerializer,
    SellerClaimCreateSerializer,
    SellerClaimRespondSerializer,
    SellerClaimAdminDecisionSerializer,
    SellerClaimIntakeSerializer,
)
from companies.models import Company
from workforce_api.services.seller_order_outbox import record_seller_order_status_event

logger = logging.getLogger(__name__)


def _resolve_user_company_id(user):
    """
    Securely resolve the user's company ID from backend context.
    Never trusts client-supplied ownership.
    """
    emp = getattr(user, "employee_profile", None)
    if emp and getattr(emp, "company_id", None):
        return emp.company_id
    if getattr(user, "company_id", None):
        return user.company_id
    return None


def _is_seller_or_grocery_supplier(user):
    """
    Check if user is a verified grocery supplier or seller business.
    """
    if getattr(user, "is_superuser", False):
        return True
    if not user.is_authenticated:
        return False
    emp = getattr(user, "employee_profile", None)
    company = getattr(emp, "company", None) if emp else getattr(user, "company", None)
    if not company:
        return False
    if company.id == 1 or getattr(company, "slug", "") in (
        "calservices", "caldim-platform", "caldim-engineering-pvt-ltd", "caldim-services"
    ):
        return True
    btype = getattr(company, "business_type", "") or ""
    if btype in ("grocery_supplier", "hybrid"):
        return True
    modules = getattr(company, "selected_modules", []) or []
    if any(m in modules for m in ("grocery_supplier", "grocery_inventory", "groceries")):
        return True
    industry = (getattr(company, "industry", "") or "").lower()
    if any(k in industry for k in ("grocery", "vegetable", "produce", "farm", "supermarket")):
        return True
    return False


def _is_admin_or_superadmin(user):
    """
    Check if user is a platform superadministrator or staff/admin user.
    Vendors, grocery suppliers, technicians, and regular employees return False.
    """
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False):
        return True
    if getattr(user, "is_staff", False):
        return True
    role = str(getattr(user, "role", "")).lower()
    if role in ("admin", "superadmin", "platform_admin", "staff"):
        return True
    return False


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SELLER HUB CATEGORIES MANAGEMENT (SellerHubCategory in workforce_seller_hub_category)
# ═══════════════════════════════════════════════════════════════════════════════

class AdminSellerHubCategoryListView(APIView):
    """
    GET  /api/workforce/seller-hub/categories/ – List Seller Hub categories with search, parent filtering & tree mode
    POST /api/workforce/seller-hub/categories/ – Create a new Seller Hub category (Admin & Super Admin)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_admin_user = _is_admin_or_superadmin(user)
        is_seller = _is_seller_or_grocery_supplier(user)

        if not (is_admin_user or is_seller):
            return Response(
                {"error": "You do not have permission to view categories."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = SellerHubCategory.objects.all()

        # Query Filters
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(name__icontains=search) |
                models.Q(slug__icontains=search) |
                models.Q(description__icontains=search)
            )

        is_active_param = request.query_params.get("is_active")
        if is_active_param is not None and is_active_param != "":
            if str(is_active_param).lower() in ("true", "1"):
                queryset = queryset.filter(is_active=True)
            elif str(is_active_param).lower() in ("false", "0"):
                queryset = queryset.filter(is_active=False)

        # Parent filtering
        parent_id_param = request.query_params.get("parent_id")
        root_param = request.query_params.get("root")

        if root_param is not None and str(root_param).lower() in ("true", "1"):
            queryset = queryset.filter(parent__isnull=True)
        elif parent_id_param is not None:
            if str(parent_id_param).lower() in ("null", "none", ""):
                queryset = queryset.filter(parent__isnull=True)
            elif str(parent_id_param).isdigit():
                queryset = queryset.filter(parent_id=int(parent_id_param))

        # Check if full tree requested
        tree_param = request.query_params.get("tree")
        if tree_param is not None and str(tree_param).lower() in ("true", "1"):
            roots = queryset.filter(parent__isnull=True).order_by("sort_order", "id")
            serializer = SellerHubCategoryTreeSerializer(roots, many=True, context={"request": request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        ordering = request.query_params.get("ordering", "sort_order")
        valid_orderings = ["sort_order", "-sort_order", "name", "-name", "id", "-id"]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering, "id")
        else:
            queryset = queryset.order_by("sort_order", "id")

        serializer = SellerHubCategoryAdminSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        if not _is_admin_or_superadmin(user):
            return Response(
                {"error": "Only platform administrators and superadministrators can create catalog categories."},
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data.copy()
        name = str(data.get("name", "")).strip()
        if not name:
            return Response(
                {"error": "Category name is required.", "field": "name"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate or sanitize slug
        slug = str(data.get("slug", "")).strip()
        if not slug:
            slug = slugify(name)
        else:
            slug = slugify(slug)

        # Ensure uniqueness of slug
        base_slug = slug
        counter = 1
        while SellerHubCategory.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        data["slug"] = slug

        # Parent resolution
        parent_val = data.get("parent") or data.get("parent_id")
        if parent_val in ("", "null", "none", None):
            data["parent"] = None
        else:
            data["parent"] = parent_val
            # Guard: Parent category must not contain products (a category with products cannot gain children)
            try:
                parent_id_num = int(parent_val) if not hasattr(parent_val, "id") else parent_val.id
                if SellerProduct.objects.filter(category_id=parent_id_num).exists():
                    parent_obj = SellerHubCategory.objects.filter(id=parent_id_num).first()
                    p_name = parent_obj.name if parent_obj else f"ID {parent_id_num}"
                    return Response(
                        {
                            "error": f"Cannot create subcategory under '{p_name}' because it already contains products. Move or reassign products first.",
                            "code": "CATEGORY_HAS_PRODUCTS",
                        },
                        status=status.HTTP_409_CONFLICT
                    )
            except (ValueError, TypeError):
                pass

        serializer = SellerHubCategoryAdminSerializer(data=data)
        if serializer.is_valid():
            cat = serializer.save()
            return Response(
                {
                    "message": "Category created successfully.",
                    "category": SellerHubCategoryAdminSerializer(cat).data,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": "Validation failed.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class AdminSellerHubCategoryDetailView(APIView):
    """
    GET    /api/workforce/seller-hub/categories/<int:pk>/ – Retrieve category with subcategories & breadcrumbs
    PATCH  /api/workforce/seller-hub/categories/<int:pk>/ – Edit category / parent / toggle active
    DELETE /api/workforce/seller-hub/categories/<int:pk>/ – Multi-tier safe deletion check & delete
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_category(self, pk):
        return SellerHubCategory.objects.filter(pk=pk).first()

    def get(self, request, pk):
        cat = self._get_category(pk)
        if not cat:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SellerHubCategoryAdminSerializer(cat)
        data = serializer.data
        children_qs = cat.children.all().order_by("sort_order", "id")
        data["children"] = SellerHubCategoryAdminSerializer(children_qs, many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        user = request.user
        if not _is_admin_or_superadmin(user):
            return Response(
                {"error": "Only platform administrators and superadministrators can modify catalog categories."},
                status=status.HTTP_403_FORBIDDEN
            )

        cat = self._get_category(pk)
        if not cat:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        if "slug" in data and data["slug"]:
            new_slug = slugify(str(data["slug"]).strip())
            if SellerHubCategory.objects.filter(slug=new_slug).exclude(pk=pk).exists():
                return Response(
                    {"error": f"A category with slug '{new_slug}' already exists.", "field": "slug"},
                    status=status.HTTP_409_CONFLICT
                )
            data["slug"] = new_slug

        if "parent" in data or "parent_id" in data:
            parent_val = data.get("parent") if "parent" in data else data.get("parent_id")
            if parent_val in ("", "null", "none", None):
                data["parent"] = None
            else:
                try:
                    parent_id_num = int(parent_val) if not hasattr(parent_val, "id") else parent_val.id
                    if parent_id_num == cat.id:
                        return Response(
                            {"error": "A category cannot be its own parent category.", "code": "INVALID_PARENT"},
                            status=status.HTTP_400_BAD_REQUEST
                        )

                    # Cycle detection: Ensure cat is not an ancestor of parent_id_num
                    curr = SellerHubCategory.objects.filter(id=parent_id_num).first()
                    visited = {cat.id}
                    while curr:
                        if curr.id in visited:
                            return Response(
                                {
                                    "error": f"Circular hierarchy detected: '{curr.name}' is a child or descendant of '{cat.name}'.",
                                    "code": "CYCLIC_HIERARCHY",
                                },
                                status=status.HTTP_400_BAD_REQUEST
                            )
                        visited.add(curr.id)
                        curr = curr.parent

                    # Product collision guard: Parent category must not already have products
                    if SellerProduct.objects.filter(category_id=parent_id_num).exists():
                        parent_obj = SellerHubCategory.objects.filter(id=parent_id_num).first()
                        p_name = parent_obj.name if parent_obj else f"ID {parent_id_num}"
                        return Response(
                            {
                                "error": f"Cannot make '{p_name}' a parent category because it already contains products. Move or reassign products first.",
                                "code": "CATEGORY_HAS_PRODUCTS",
                            },
                            status=status.HTTP_409_CONFLICT
                        )
                except (ValueError, TypeError):
                    pass
                data["parent"] = parent_val

        # Reactivation guard: Cannot reactivate a child category if its parent currently has products
        if "is_active" in data:
            is_active_val = data.get("is_active")
            if str(is_active_val).lower() in ("true", "1") and not cat.is_active:
                target_parent_id = parent_id_num if ("parent" in data or "parent_id" in data) else cat.parent_id
                if target_parent_id and SellerProduct.objects.filter(category_id=target_parent_id).exists():
                    parent_obj = SellerHubCategory.objects.filter(id=target_parent_id).first()
                    p_name = parent_obj.name if parent_obj else f"ID {target_parent_id}"
                    return Response(
                        {
                            "error": f"Cannot reactivate category under '{p_name}' because '{p_name}' already contains products. Move or reassign products first.",
                            "code": "CATEGORY_HAS_PRODUCTS",
                        },
                        status=status.HTTP_409_CONFLICT
                    )

        serializer = SellerHubCategoryAdminSerializer(cat, data=data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(
                {
                    "message": "Category updated successfully.",
                    "category": SellerHubCategoryAdminSerializer(updated).data,
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "Validation failed.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        user = request.user
        if not _is_admin_or_superadmin(user):
            return Response(
                {"error": "Only platform administrators and superadministrators can delete catalog categories."},
                status=status.HTTP_403_FORBIDDEN
            )

        cat = self._get_category(pk)
        if not cat:
            return Response({"error": "Category not found."}, status=status.HTTP_404_NOT_FOUND)

        # Safe Deletion Validation 1: Check child subcategories
        children_count = cat.children.count()
        if children_count > 0:
            return Response(
                {
                    "error": f"Cannot delete category '{cat.name}' because it contains {children_count} subcategory/subcategories. Please delete or reassign subcategories first.",
                    "code": "CATEGORY_HAS_CHILDREN",
                    "children_count": children_count,
                },
                status=status.HTTP_409_CONFLICT
            )

        # Safe Deletion Validation 2: Check linked InventoryItems
        inventory_count = InventoryItem.objects.filter(catalogue_category_id=pk).count()

        if inventory_count > 0:
            return Response(
                {
                    "error": f"Cannot delete category '{cat.name}' because it is linked to {inventory_count} inventory item(s). Deactivate the category instead to preserve operational records.",
                    "code": "CATEGORY_IN_USE",
                    "inventory_items_count": inventory_count,
                },
                status=status.HTTP_409_CONFLICT
            )

        cat_name = cat.name
        cat.delete()
        return Response(
            {"message": f"Category '{cat_name}' was deleted successfully."},
            status=status.HTTP_200_OK
        )


class AdminSellerHubCategoryActiveListView(APIView):
    """
    GET /api/workforce/seller-hub/categories/active/
    Read-only endpoint returning active Seller Hub categories whose parent chain is also active.
    Supports ?tree=true for active hierarchical trees.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        active_cats = SellerHubCategory.objects.filter(is_active=True).select_related("parent")
        # Filter out any category whose parent or grandparent is inactive
        valid_active_ids = set()
        for c in active_cats:
            curr = c.parent
            all_ancestors_active = True
            visited = {c.id}
            while curr and curr.id not in visited:
                if not getattr(curr, "is_active", True):
                    all_ancestors_active = False
                    break
                visited.add(curr.id)
                curr = getattr(curr, "parent", None)
            if all_ancestors_active:
                valid_active_ids.add(c.id)

        queryset = SellerHubCategory.objects.filter(id__in=valid_active_ids).order_by("sort_order", "name")

        # Optional tree mode for active categories
        tree_param = request.query_params.get("tree")
        if tree_param is not None and str(tree_param).lower() in ("true", "1"):
            roots = queryset.filter(parent__isnull=True).order_by("sort_order", "id")
            serializer = SellerHubCategoryTreeSerializer(roots, many=True, context={"request": request, "active_only": True})
            return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = SellerHubCategoryAdminSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AdminSellerHubCategoryTreeView(APIView):
    """
    GET /api/workforce/seller-hub/categories/tree/
    Returns full hierarchical tree of Seller Hub categories.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        is_seller = _is_seller_or_grocery_supplier(user)

        if not (is_super or is_admin or is_seller):
            return Response(
                {"error": "You do not have permission to view categories."},
                status=status.HTTP_403_FORBIDDEN
            )

        active_only = request.query_params.get("active_only", "").lower() in ("true", "1")
        roots = SellerHubCategory.objects.filter(parent__isnull=True)
        if active_only:
            roots = roots.filter(is_active=True)
        roots = roots.order_by("sort_order", "id")

        serializer = SellerHubCategoryTreeSerializer(roots, many=True, context={"request": request, "active_only": active_only})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerCatalogCategoryListView(APIView):
    """
    GET /api/workforce/seller-hub/catalog/categories/
    Read-only endpoint for vendors & admins to browse active leaf/branch categories.
    Supports:
      - ?parent_id=<id|null> : Returns immediate active children under parent_id (or roots if null/empty)
      - ?q=<text> : Substring search across all active categories, returning full breadcrumb path & is_leaf
      - ?tree=true : Returns full hierarchical tree of active categories with active parent chains
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        is_seller = _is_seller_or_grocery_supplier(user)

        if not (is_super or is_admin or is_seller):
            return Response(
                {"error": "You do not have permission to view catalog categories."},
                status=status.HTTP_403_FORBIDDEN
            )

        # 1. Fetch all active categories in 1 single SQL query
        all_active = list(SellerHubCategory.objects.filter(is_active=True).order_by("sort_order", "name"))
        cat_map = {c.id: c for c in all_active}

        # 2. Build active ancestor chain validation & parent->children graph in memory (0 queries)
        valid_active_ids = set()
        children_map = {}  # parent_id -> list of child_ids
        for c in all_active:
            children_map.setdefault(c.parent_id, []).append(c.id)

        for c in all_active:
            curr = c.parent_id
            chain_valid = True
            visited = {c.id}
            while curr is not None:
                if curr not in cat_map:
                    chain_valid = False
                    break
                if curr in visited:
                    chain_valid = False
                    break
                visited.add(curr)
                curr = cat_map[curr].parent_id
            if chain_valid:
                valid_active_ids.add(c.id)

        # Helper to compute breadcrumb path
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

        # Helper to serialize category item
        def serialize_item(cat):
            active_child_ids = [cid for cid in children_map.get(cat.id, []) if cid in valid_active_ids]
            has_children = len(active_child_ids) > 0
            is_leaf = not has_children
            path = compute_path(cat.id)
            path_string = " > ".join(p["name"] for p in path)
            return {
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "description": cat.description or "",
                "icon": cat.icon or "",
                "image": cat.image or "",
                "parent_id": cat.parent_id,
                "sort_order": cat.sort_order,
                "is_active": cat.is_active,
                "has_children": has_children,
                "is_leaf": is_leaf,
                "path": path,
                "path_string": path_string,
            }

        # Check tree mode param
        tree_param = request.query_params.get("tree")
        if tree_param is not None and str(tree_param).lower() in ("true", "1"):
            def build_tree_node(cat_id):
                cat = cat_map[cat_id]
                item = serialize_item(cat)
                child_ids = [cid for cid in children_map.get(cat_id, []) if cid in valid_active_ids]
                item["children"] = [build_tree_node(cid) for cid in child_ids]
                return item

            root_ids = [cid for cid in children_map.get(None, []) if cid in valid_active_ids]
            tree_data = [build_tree_node(rid) for rid in root_ids]
            return Response(tree_data, status=status.HTTP_200_OK)

        # Check search param
        q = request.query_params.get("q", "").strip()
        if q:
            q_lower = q.lower()
            results = []
            for c in all_active:
                if c.id not in valid_active_ids:
                    continue
                if q_lower in c.name.lower() or q_lower in c.slug.lower() or (c.description and q_lower in c.description.lower()):
                    results.append(serialize_item(c))
            return Response(results, status=status.HTTP_200_OK)

        # Check parent_id param
        parent_id_param = request.query_params.get("parent_id")
        if parent_id_param is not None:
            if str(parent_id_param).lower() in ("null", "none", "", "0"):
                target_parent = None
            elif str(parent_id_param).isdigit():
                target_parent = int(parent_id_param)
            else:
                return Response({"error": "Invalid parent_id parameter."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            target_parent = None

        child_ids = [cid for cid in children_map.get(target_parent, []) if cid in valid_active_ids]
        items = [serialize_item(cat_map[cid]) for cid in child_ids]
        return Response(items, status=status.HTTP_200_OK)


# Backward-compatible view aliases for URL routing
AdminCatalogCategoryListView = AdminSellerHubCategoryListView
AdminCatalogCategoryDetailView = AdminSellerHubCategoryDetailView
AdminCatalogCategoryActiveListView = AdminSellerHubCategoryActiveListView
AdminCatalogCategoryTreeView = AdminSellerHubCategoryTreeView



# ═══════════════════════════════════════════════════════════════════════════════
# 2. SELLER HUB COUPONS MANAGEMENT (VendorCoupon in workforce_vendor_coupon)
# ═══════════════════════════════════════════════════════════════════════════════

class AdminSellerCouponListView(APIView):
    """
    GET  /api/workforce/seller-hub/coupons/ – List coupons (Superadmin cross-tenant or store-scoped)
    POST /api/workforce/seller-hub/coupons/ – Create discount coupon
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        company_id = _resolve_user_company_id(user)

        if not is_super and not is_admin_role(user) and not _is_seller_or_grocery_supplier(user):
            return Response(
                {"error": "You do not have permission to view coupons."},
                status=status.HTTP_403_FORBIDDEN
            )

        queryset = VendorCoupon.objects.select_related("company").all()

        # Tenant isolation
        if not is_super:
            if not company_id:
                return Response(
                    {"error": "No company assigned to this seller account."},
                    status=status.HTTP_403_FORBIDDEN
                )
            queryset = queryset.filter(company_id=company_id)
        else:
            # Superadmin filter by company if specified
            filter_company = request.query_params.get("company_id")
            if filter_company:
                queryset = queryset.filter(company_id=filter_company)

        # Filters
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(code__icontains=search) |
                models.Q(description__icontains=search)
            )

        status_param = request.query_params.get("status", "").strip().lower()
        from django.utils import timezone
        now = timezone.now()
        if status_param == "active":
            queryset = queryset.filter(is_active=True).filter(
                models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=now)
            )
        elif status_param == "expired":
            queryset = queryset.filter(valid_until__lt=now)
        elif status_param == "inactive":
            queryset = queryset.filter(is_active=False)

        discount_type = request.query_params.get("discount_type")
        if discount_type in ("percent", "flat"):
            queryset = queryset.filter(discount_type=discount_type)

        queryset = queryset.order_by("-created_at")
        serializer = VendorCouponSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        company_id = _resolve_user_company_id(user)

        if not is_super and not is_admin_role(user) and not _is_seller_or_grocery_supplier(user):
            return Response(
                {"error": "You do not have permission to create coupons."},
                status=status.HTTP_403_FORBIDDEN
            )

        target_company_id = company_id
        if is_super and request.data.get("company_id"):
            target_company_id = request.data.get("company_id")
        elif is_super and not target_company_id:
            # Default to first company / platform company if superadmin without company
            first_comp = Company.objects.order_by("id").first()
            target_company_id = first_comp.id if first_comp else None

        if not target_company_id:
            return Response(
                {"error": "A target company/store is required to create a coupon."},
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request.data.copy()
        code = str(data.get("code", "")).strip().upper()
        if not code:
            return Response(
                {"error": "Coupon code is required.", "field": "code"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if VendorCoupon.objects.filter(company_id=target_company_id, code=code).exists():
            return Response(
                {"error": f"A coupon with code '{code}' already exists for this store.", "field": "code"},
                status=status.HTTP_409_CONFLICT
            )

        try:
            discount_value = Decimal(str(data.get("discount_value", "0")))
            if discount_value <= 0:
                return Response(
                    {"error": "Discount value must be greater than 0.", "field": "discount_value"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception:
            return Response(
                {"error": "Invalid discount value.", "field": "discount_value"},
                status=status.HTTP_400_BAD_REQUEST
            )

        discount_type = data.get("discount_type", "percent")
        if discount_type == "percent" and discount_value > 100:
            return Response(
                {"error": "Percentage discount cannot exceed 100%.", "field": "discount_value"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = VendorCouponSerializer(data=data)
        if serializer.is_valid():
            coupon = serializer.save(company_id=target_company_id, code=code)
            return Response(
                {
                    "message": f"Coupon '{coupon.code}' created successfully.",
                    "coupon": VendorCouponSerializer(coupon).data,
                },
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": "Validation failed.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class AdminSellerCouponDetailView(APIView):
    """
    GET    /api/workforce/seller-hub/coupons/<int:pk>/ – Get coupon details
    PATCH  /api/workforce/seller-hub/coupons/<int:pk>/ – Edit coupon / toggle active
    DELETE /api/workforce/seller-hub/coupons/<int:pk>/ – Delete coupon
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_coupon(self, user, pk):
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        company_id = _resolve_user_company_id(user)

        if is_super:
            return VendorCoupon.objects.select_related("company").filter(pk=pk).first()
        if company_id:
            return VendorCoupon.objects.select_related("company").filter(pk=pk, company_id=company_id).first()
        return None

    def get(self, request, pk):
        coupon = self._get_coupon(request.user, pk)
        if not coupon:
            return Response({"error": "Coupon not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = VendorCouponSerializer(coupon)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        coupon = self._get_coupon(request.user, pk)
        if not coupon:
            return Response({"error": "Coupon not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        if "code" in data and data["code"]:
            new_code = str(data["code"]).strip().upper()
            if VendorCoupon.objects.filter(company=coupon.company, code=new_code).exclude(pk=pk).exists():
                return Response(
                    {"error": f"A coupon with code '{new_code}' already exists for this store.", "field": "code"},
                    status=status.HTTP_409_CONFLICT
                )
            data["code"] = new_code

        serializer = VendorCouponSerializer(coupon, data=data, partial=True)
        if serializer.is_valid():
            updated = serializer.save()
            return Response(
                {
                    "message": f"Coupon '{updated.code}' updated successfully.",
                    "coupon": VendorCouponSerializer(updated).data,
                },
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": "Validation failed.", "details": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    def delete(self, request, pk):
        coupon = self._get_coupon(request.user, pk)
        if not coupon:
            return Response({"error": "Coupon not found."}, status=status.HTTP_404_NOT_FOUND)

        code = coupon.code
        coupon.delete()
        return Response(
            {"message": f"Coupon '{code}' was deleted successfully."},
            status=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 3. SELLER HUB LEAF CATEGORIES HELPER
# ═══════════════════════════════════════════════════════════════════════════════

class AdminCatalogCategoryActiveListView(APIView):
    """
    GET /api/workforce/seller-hub/categories/active/ – Retrieve active leaf categories
    with formatted path lineage for catalog assignment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        leaf_only = request.query_params.get("leaf_only", "").lower() in ("1", "true", "yes")

        # Fetch active categories
        active_cats = SellerHubCategory.objects.filter(is_active=True).select_related("parent").prefetch_related("children")
        
        categories_list = []
        for cat in active_cats:
            # Check ancestor chain: all ancestors must be active
            ancestor = cat.parent
            all_ancestors_active = True
            while ancestor:
                if not ancestor.is_active:
                    all_ancestors_active = False
                    break
                ancestor = ancestor.parent
            
            if not all_ancestors_active:
                continue

            has_active_children = cat.children.filter(is_active=True).exists()
            is_leaf = not has_active_children

            if leaf_only and not is_leaf:
                continue

            # Build ancestor lineage path
            path = [cat.name]
            curr = cat.parent
            while curr:
                path.insert(0, curr.name)
                curr = curr.parent

            categories_list.append({
                "id": cat.id,
                "name": cat.name,
                "slug": cat.slug,
                "path": " > ".join(path),
                "parent_name": cat.parent.name if cat.parent else None,
                "icon": cat.icon,
                "is_leaf": is_leaf,
            })

        categories_list.sort(key=lambda x: x["path"])
        return Response(categories_list, status=status.HTTP_200_OK)


class AdminCatalogCategoryTreeView(APIView):
    """
    GET /api/workforce/seller-hub/categories/tree/ – Retrieve full category hierarchy tree
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        queryset = SellerHubCategory.objects.all()
        is_active_param = request.query_params.get("is_active")
        if is_active_param is not None and str(is_active_param).lower() in ("true", "1"):
            queryset = queryset.filter(is_active=True)
        roots = queryset.filter(parent__isnull=True).order_by("sort_order", "id")
        serializer = SellerHubCategoryTreeSerializer(roots, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SELLER HUB PRODUCT CATALOG MANAGEMENT (Phase 2)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerProductListView(APIView):
    """
    GET  /api/workforce/seller-hub/products/ – List products (scoped to seller company or platform-wide for Admin)
    POST /api/workforce/seller-hub/products/ – Create a single product (DRAFT or SUBMITTED)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        queryset = SellerProduct.objects.select_related("category", "category__parent", "company", "reviewed_by", "created_by").prefetch_related("images")

        # Tenant Scoping: Sellers only see their company's products
        if not (is_super or (is_admin and not company_id)):
            if not company_id:
                return Response(
                    {"error": "User is not associated with an approved merchant company."},
                    status=status.HTTP_403_FORBIDDEN
                )
            queryset = queryset.filter(company_id=company_id)
        else:
            # Platform Superadmin can filter by specific seller company
            target_company = request.query_params.get("company_id")
            if target_company and str(target_company).isdigit():
                queryset = queryset.filter(company_id=int(target_company))

        # Filters
        status_param = request.query_params.get("status", "").strip().upper()
        if status_param and status_param != "ALL":
            queryset = queryset.filter(status=status_param)

        category_id = request.query_params.get("category_id")
        if category_id and str(category_id).isdigit():
            queryset = queryset.filter(category_id=int(category_id))

        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(title__icontains=search) |
                models.Q(sku__icontains=search) |
                models.Q(brand__icontains=search) |
                models.Q(barcode__icontains=search)
            )

        ordering = request.query_params.get("ordering", "-updated_at")
        valid_orderings = ["-updated_at", "updated_at", "-created_at", "created_at", "title", "-title", "selling_price", "-selling_price", "status"]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-updated_at")

        serializer = SellerProductListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        company_id = _resolve_user_company_id(user)
        if not company_id:
            return Response(
                {"error": "Unable to resolve your merchant store. Only verified sellers can create products."},
                status=status.HTTP_403_FORBIDDEN
            )

        company = Company.objects.filter(pk=company_id).first()
        if not company:
            return Response({"error": "Merchant company not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        images_data = data.pop("images", [])
        if isinstance(images_data, str):
            images_data = [images_data] if images_data.strip() else []

        initial_status = str(data.get("status", "DRAFT")).strip().upper()
        if initial_status not in [choice[0] for choice in SellerProduct.Status.choices]:
            initial_status = SellerProduct.Status.DRAFT

        # Rule: A product cannot be submitted for review without at least one valid image
        if initial_status in (SellerProduct.Status.SUBMITTED, SellerProduct.Status.UNDER_REVIEW):
            if not images_data or len([img for img in images_data if img and str(img).strip()]) == 0:
                return Response(
                    {"error": "At least one product image is required to submit a product for catalog review.", "field": "images"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        serializer = SellerProductCreateUpdateSerializer(data=data, context={"company": company, "request": request})
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            product = serializer.save(
                company=company,
                created_by=user,
                status=initial_status,
                submitted_at=timezone.now() if initial_status in (SellerProduct.Status.SUBMITTED, SellerProduct.Status.UNDER_REVIEW) else None,
            )

            # Create product images
            for idx, img_url in enumerate(images_data):
                if img_url and str(img_url).strip():
                    SellerProductImage.objects.create(
                        product=product,
                        image_url=str(img_url).strip(),
                        is_primary=(idx == 0),
                        sort_order=idx,
                    )

            # Create immutable audit log
            SellerProductAuditLog.objects.create(
                product=product,
                action="CREATED",
                from_status="",
                to_status=product.status,
                actor=user,
                notes=f"Product '{product.title}' created by {user.username} as {product.status}.",
            )

        return Response(
            {
                "message": f"Product '{product.title}' created successfully.",
                "product": SellerProductDetailSerializer(product).data,
            },
            status=status.HTTP_201_CREATED
        )


class SellerProductDetailView(APIView):
    """
    GET    /api/workforce/seller-hub/products/<int:pk>/ – Product details with images, category lineage, and audit timeline
    PATCH  /api/workforce/seller-hub/products/<int:pk>/ – Edit product
    DELETE /api/workforce/seller-hub/products/<int:pk>/ – Delete product (allowed only for DRAFT or REJECTED)
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_product(self, user, pk):
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        qs = SellerProduct.objects.select_related("category", "category__parent", "company", "reviewed_by", "created_by").prefetch_related("images", "audit_logs", "audit_logs__actor")
        if is_super or (is_admin and not company_id):
            return qs.filter(pk=pk).first()
        if company_id:
            return qs.filter(pk=pk, company_id=company_id).first()
        return None

    def get(self, request, pk):
        product = self._get_product(request.user, pk)
        if not product:
            return Response({"error": "Product not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        serializer = SellerProductDetailSerializer(product)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        product = self._get_product(request.user, pk)
        if not product:
            return Response({"error": "Product not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        data = request.data.copy()
        images_data = data.pop("images", None)

        old_status = product.status
        old_title = product.title
        old_price = product.selling_price
        old_mrp = product.mrp
        old_category_id = product.category_id

        # Rules for edits:
        # Sellers can edit Draft, Changes Requested, Rejected, and Paused products.
        # If an Approved product is modified by a seller, meaningful edits transition it back to UNDER_REVIEW/SUBMITTED with audit trail.
        requested_status = str(data.get("status", "")).strip().upper()
        if requested_status and requested_status != old_status:
            # Non-superadmins cannot directly set status to APPROVED
            if requested_status == SellerProduct.Status.APPROVED and not is_super:
                return Response(
                    {"error": "Only platform reviewers can approve products."},
                    status=status.HTTP_403_FORBIDDEN
                )

        serializer = SellerProductCreateUpdateSerializer(
            product,
            data=data,
            partial=True,
            context={"company": product.company, "request": request}
        )
        if not serializer.is_valid():
            return Response(
                {"error": "Validation failed.", "details": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            updated_product = serializer.save()

            # Handle image replacements if provided
            if images_data is not None:
                if isinstance(images_data, str):
                    images_data = [images_data] if images_data.strip() else []
                # Clear and re-create images
                product.images.all().delete()
                for idx, img_url in enumerate(images_data):
                    if img_url and str(img_url).strip():
                        SellerProductImage.objects.create(
                            product=product,
                            image_url=str(img_url).strip(),
                            is_primary=(idx == 0),
                            sort_order=idx,
                        )

            # Detect meaningful edits on APPROVED product
            meaningful_change = False
            notes_list = []
            if old_title != updated_product.title:
                meaningful_change = True
                notes_list.append(f"Title changed from '{old_title}' to '{updated_product.title}'")
            if old_price != updated_product.selling_price:
                meaningful_change = True
                notes_list.append(f"Selling price changed from ₹{old_price} to ₹{updated_product.selling_price}")
            if old_mrp != updated_product.mrp:
                meaningful_change = True
                notes_list.append(f"MRP changed from ₹{old_mrp} to ₹{updated_product.mrp}")
            if old_category_id != updated_product.category_id:
                meaningful_change = True
                notes_list.append(f"Category changed to '{updated_product.category.name}'")

            # Check if resubmission or status change
            if old_status == SellerProduct.Status.APPROVED and meaningful_change and not is_super:
                updated_product.status = SellerProduct.Status.SUBMITTED
                updated_product.submitted_at = timezone.now()
                updated_product.save(update_fields=["status", "submitted_at", "updated_at"])
                
                SellerProductAuditLog.objects.create(
                    product=updated_product,
                    action="RESUBMITTED",
                    from_status=old_status,
                    to_status=SellerProduct.Status.SUBMITTED,
                    actor=user,
                    notes=f"Approved product modified. Moved back to review queue. Changes: {', '.join(notes_list)}",
                )
            elif meaningful_change or old_status != updated_product.status:
                SellerProductAuditLog.objects.create(
                    product=updated_product,
                    action="EDITED",
                    from_status=old_status,
                    to_status=updated_product.status,
                    actor=user,
                    notes=f"Product updated by {user.username}. {', '.join(notes_list) if notes_list else ''}".strip(),
                )

        return Response(
            {
                "message": f"Product '{updated_product.title}' updated successfully.",
                "product": SellerProductDetailSerializer(updated_product).data,
            },
            status=status.HTTP_200_OK
        )

    def delete(self, request, pk):
        product = self._get_product(request.user, pk)
        if not product:
            return Response({"error": "Product not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        # Deletion rule: Allowed only for DRAFT or REJECTED products
        if product.status not in (SellerProduct.Status.DRAFT, SellerProduct.Status.REJECTED):
            return Response(
                {
                    "error": f"Cannot delete product in '{product.status}' status. You can only delete Draft or Rejected products. Consider pausing or deactivating instead."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        title = product.title
        product.delete()
        return Response(
            {"message": f"Product '{title}' was deleted successfully."},
            status=status.HTTP_200_OK
        )


class SellerProductSubmitView(APIView):
    """
    POST /api/workforce/seller-hub/products/<int:pk>/submit/ – Submit a Draft / Changes Requested product for Admin review
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        qs = SellerProduct.objects.select_related("category").prefetch_related("images")
        if is_super:
            product = qs.filter(pk=pk).first()
        else:
            product = qs.filter(pk=pk, company_id=company_id).first()

        if not product:
            return Response({"error": "Product not found or access denied."}, status=status.HTTP_404_NOT_FOUND)

        if product.status == SellerProduct.Status.APPROVED:
            return Response({"error": "This product is already approved."}, status=status.HTTP_400_BAD_REQUEST)

        # Validation Checks before submission
        if not product.title or not product.sku or not product.category:
            return Response(
                {"error": "Product title, SKU, and category are mandatory before submitting for review."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not product.category.is_active:
            return Response(
                {"error": f"Category '{product.category.name}' is inactive. Please reassign to an active leaf category."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if product.category.children.filter(is_active=True).exists():
            return Response(
                {"error": f"Category '{product.category.name}' is a parent category. Please select a specific leaf subcategory."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if product.selling_price > product.mrp:
            return Response(
                {"error": f"Selling price (₹{product.selling_price}) cannot exceed MRP (₹{product.mrp})."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Required product image validation
        if not product.images.exists():
            return Response(
                {"error": "At least one product image is required before submitting for catalog review."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from_st = product.status
        product.status = SellerProduct.Status.SUBMITTED
        product.submitted_at = timezone.now()
        product.save(update_fields=["status", "submitted_at", "updated_at"])

        SellerProductAuditLog.objects.create(
            product=product,
            action="SUBMITTED",
            from_status=from_st,
            to_status=SellerProduct.Status.SUBMITTED,
            actor=user,
            notes=f"Product submitted for admin catalog verification by {user.username}.",
        )

        return Response(
            {
                "message": f"Product '{product.title}' has been submitted for catalog approval.",
                "product": SellerProductDetailSerializer(product).data,
            },
            status=status.HTTP_200_OK
        )


class SellerProductReviewDecisionView(APIView):
    """
    POST /api/workforce/seller-hub/products/<int:pk>/review/ – Admin/Superadmin Catalog Review Decision
    Actions:
      - 'approve'
      - 'reject' (mandatory note)
      - 'request_changes' (mandatory note)
      - 'pause' (mandatory note)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)

        if not (is_super or is_admin):
            return Response(
                {"error": "Only platform administrators can perform catalog review decisions."},
                status=status.HTTP_403_FORBIDDEN
            )

        product = SellerProduct.objects.select_related("company", "category").prefetch_related("images").filter(pk=pk).first()
        if not product:
            return Response({"error": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        action = str(request.data.get("action", "")).strip().lower()
        note = str(request.data.get("note", "")).strip()

        valid_actions = {
            "approve": SellerProduct.Status.APPROVED,
            "reject": SellerProduct.Status.REJECTED,
            "request_changes": SellerProduct.Status.CHANGES_REQUESTED,
            "pause": SellerProduct.Status.PAUSED,
        }

        if action not in valid_actions:
            return Response(
                {"error": f"Invalid review action '{action}'. Valid actions are: approve, reject, request_changes, pause."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mandatory reason note for reject, request_changes, and pause
        if action in ("reject", "request_changes", "pause") and not note:
            return Response(
                {"error": f"A mandatory feedback reason/note is required when performing '{action}'.", "field": "note"},
                status=status.HTTP_400_BAD_REQUEST
            )

        target_status = valid_actions[action]
        from_st = product.status

        with transaction.atomic():
            product.status = target_status
            product.admin_review_note = note
            product.reviewed_by = user
            product.reviewed_at = timezone.now()
            product.save(update_fields=["status", "admin_review_note", "reviewed_by", "reviewed_at", "updated_at"])

            action_label = {
                "approve": "APPROVED",
                "reject": "REJECTED",
                "request_changes": "REQUEST_CHANGES",
                "pause": "PAUSED",
            }.get(action, action.upper())
            SellerProductAuditLog.objects.create(
                product=product,
                action=action_label,
                from_status=from_st,
                to_status=target_status,
                actor=user,
                notes=note or f"Product marked as {target_status} by reviewer {user.username}.",
            )

        return Response(
            {
                "message": f"Product '{product.title}' has been {target_status.lower()}.",
                "product": SellerProductDetailSerializer(product).data,
            },
            status=status.HTTP_200_OK
        )


class SellerProductTemplateDownloadView(APIView):
    """
    GET /api/workforce/seller-hub/products/template/ – Download standardized bulk catalog upload CSV template
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="sevo_seller_catalog_upload_template.csv"'

        writer = csv.writer(response)
        # Headers
        headers = [
            "Title",
            "Description",
            "Brand",
            "SKU",
            "Barcode",
            "Category_Slug",
            "Unit",
            "Pack_Size",
            "MRP",
            "Selling_Price",
            "Tax_Rate",
            "HSN_Code",
            "Image_URL",
            "Storage_Info",
            "Expiry_Info",
        ]
        writer.writerow(headers)

        # Fetch up to 3 sample leaf categories from DB for guide
        active_leafs = SellerHubCategory.objects.filter(is_active=True, children__isnull=True)[:3]
        slug1 = active_leafs[0].slug if len(active_leafs) > 0 else "sunflower-oil"
        slug2 = active_leafs[1].slug if len(active_leafs) > 1 else "toor-dal"

        # Sample guide rows
        writer.writerow([
            "Fortune Sunlite Refined Sunflower Oil",
            "100% pure refined sunflower oil for cooking.",
            "Fortune",
            "FORT-SUN-1L",
            "8901234567890",
            slug1,
            "litre",
            "1L",
            "180.00",
            "165.00",
            "5.00",
            "1512",
            "https://images.unsplash.com/photo-1474979266404-7eaacbcd87c5?w=500",
            "Store in a cool and dry place away from direct sunlight.",
            "Best before 9 months from manufacture",
        ])
        writer.writerow([
            "Tata Sampann Unpolished Toor Dal",
            "High protein unpolished toor dal rich in dietary fiber.",
            "Tata Sampann",
            "TATA-TOOR-1KG",
            "8909876543210",
            slug2,
            "kg",
            "1 kg",
            "195.00",
            "175.00",
            "0.00",
            "0713",
            "https://images.unsplash.com/photo-1585994192704-561f9d6a2f76?w=500",
            "Store in an airtight container.",
            "Best before 12 months from packing",
        ])

        return response


class SellerProductBulkUploadView(APIView):
    """
    POST /api/workforce/seller-hub/products/bulk-upload/ – Parse, validate, and atomically import bulk products
    Query Params:
      - preview=true: Dry-run validation only (returns preview rows and row errors without saving to DB)
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        user = request.user
        company_id = _resolve_user_company_id(user)
        if not company_id:
            return Response(
                {"error": "Merchant company not found. Only registered sellers can import catalog batches."},
                status=status.HTTP_403_FORBIDDEN
            )

        company = Company.objects.filter(pk=company_id).first()
        if not company:
            return Response({"error": "Merchant company not found."}, status=status.HTTP_404_NOT_FOUND)

        is_preview = str(request.query_params.get("preview", "")).lower() in ("true", "1") or str(request.data.get("preview", "")).lower() in ("true", "1")

        file_obj = request.FILES.get("file")
        if not file_obj:
            return Response({"error": "Please provide a CSV or Excel file (.csv, .xlsx)."}, status=status.HTTP_400_BAD_REQUEST)

        filename = file_obj.name.lower()
        if not (filename.endswith(".csv") or filename.endswith(".xlsx") or filename.endswith(".xls")):
            return Response({"error": "Unsupported file format. Please upload a .csv or .xlsx file."}, status=status.HTTP_400_BAD_REQUEST)

        # Read content
        try:
            if filename.endswith(".csv"):
                content = file_obj.read().decode("utf-8-sig", errors="replace")
                reader = csv.DictReader(io.StringIO(content))
                rows = list(reader)
            else:
                # Excel file
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(file_obj, data_only=True)
                    sheet = wb.active
                    header_row = [str(cell.value or "").strip() for cell in sheet[1]]
                    rows = []
                    for r in sheet.iter_rows(min_row=2, values_only=True):
                        if any(r):
                            row_dict = {}
                            for h_idx, h_val in enumerate(header_row):
                                row_dict[h_val] = str(r[h_idx] or "").strip() if h_idx < len(r) else ""
                            rows.append(row_dict)
                except ImportError:
                    return Response({"error": "Excel support requires openpyxl. Please upload a .csv file."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Failed to read file: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

        if not rows:
            return Response({"error": "The uploaded file contains no data rows."}, status=status.HTTP_400_BAD_REQUEST)

        if len(rows) > 500:
            return Response({"error": f"Upload batch size exceeds limit (500 rows maximum). File contains {len(rows)} rows."}, status=status.HTTP_400_BAD_REQUEST)

        # Pre-fetch existing SKUs for this company to check duplicates
        existing_skus = set(SellerProduct.objects.filter(company=company).values_list("sku", flat=True))
        
        # Pre-fetch active leaf categories map (slug -> category obj)
        all_cats = list(SellerHubCategory.objects.filter(is_active=True).prefetch_related("children"))
        leaf_cats_by_slug = {}
        leaf_cats_by_id = {}
        for c in all_cats:
            has_child = c.children.filter(is_active=True).exists() or c.children.exists()
            if not has_child:
                leaf_cats_by_slug[c.slug.lower()] = c
                leaf_cats_by_id[str(c.id)] = c

        parsed_items = []
        error_report = []
        seen_skus_in_batch = set()

        for idx, row in enumerate(rows, start=2): # row 1 is header
            row_errors = []
            
            # Normalize column names (ignore case and spacing)
            normalized_row = {str(k).strip().lower().replace(" ", "_"): str(v).strip() for k, v in row.items() if k}
            
            title = normalized_row.get("title") or normalized_row.get("product_title", "")
            if not title:
                row_errors.append("Product Title is required.")

            sku = normalized_row.get("sku") or normalized_row.get("product_sku", "")
            if not sku:
                row_errors.append("SKU is required.")
            else:
                sku_upper = sku.upper()
                if sku_upper in seen_skus_in_batch:
                    row_errors.append(f"Duplicate SKU '{sku}' found multiple times in this upload file.")
                elif sku in existing_skus:
                    row_errors.append(f"SKU '{sku}' already exists in your store product catalog.")
                else:
                    seen_skus_in_batch.add(sku_upper)

            # Category resolution
            cat_identifier = normalized_row.get("category_slug") or normalized_row.get("category") or normalized_row.get("category_id", "")
            cat_obj = None
            if not cat_identifier:
                row_errors.append("Category slug or ID is required.")
            else:
                cat_ident_clean = cat_identifier.strip().lower()
                cat_obj = SellerHubCategory.objects.filter(slug=cat_ident_clean).first()
                if not cat_obj and cat_ident_clean.isdigit():
                    cat_obj = SellerHubCategory.objects.filter(id=int(cat_ident_clean)).first()

                if not cat_obj:
                    row_errors.append(f"Category '{cat_identifier}' not found in catalog.")
                else:
                    is_valid, err_msg, _ = validate_product_category_is_leaf(cat_obj)
                    if not is_valid:
                        row_errors.append(err_msg)

            # Pricing validation
            mrp_val = None
            try:
                mrp_str = normalized_row.get("mrp", "").replace("₹", "").replace(",", "").strip()
                mrp_val = Decimal(mrp_str)
                if mrp_val <= 0:
                    row_errors.append("MRP must be greater than zero.")
            except (InvalidOperation, ValueError):
                row_errors.append("Invalid MRP format. Must be a valid positive number.")

            price_val = None
            try:
                price_str = normalized_row.get("selling_price", "").replace("₹", "").replace(",", "").strip()
                price_val = Decimal(price_str)
                if price_val <= 0:
                    row_errors.append("Selling price must be greater than zero.")
                elif mrp_val is not None and price_val > mrp_val:
                    row_errors.append(f"Selling price (₹{price_val}) cannot exceed MRP (₹{mrp_val}).")
            except (InvalidOperation, ValueError):
                row_errors.append("Invalid Selling Price format. Must be a valid positive number.")

            tax_val = Decimal("0.00")
            tax_str = normalized_row.get("tax_rate", "").replace("%", "").strip()
            if tax_str:
                try:
                    tax_val = Decimal(tax_str)
                    if tax_val < 0:
                        row_errors.append("Tax rate cannot be negative.")
                except (InvalidOperation, ValueError):
                    row_errors.append("Invalid Tax rate format.")

            unit = normalized_row.get("unit", "piece") or "piece"
            pack_size = normalized_row.get("pack_size", "1") or "1"
            brand = normalized_row.get("brand", "")
            barcode = normalized_row.get("barcode", "")
            description = normalized_row.get("description", "")
            hsn_code = normalized_row.get("hsn_code", "")
            storage_info = normalized_row.get("storage_info", "")
            expiry_info = normalized_row.get("expiry_info", "")
            image_url = normalized_row.get("image_url", "")

            item_data = {
                "row_number": idx,
                "title": title,
                "sku": sku,
                "brand": brand,
                "barcode": barcode,
                "category_id": cat_obj.id if cat_obj else None,
                "category_name": cat_obj.name if cat_obj else cat_identifier,
                "unit": unit,
                "pack_size": pack_size,
                "mrp": str(mrp_val) if mrp_val is not None else "",
                "selling_price": str(price_val) if price_val is not None else "",
                "tax_rate": str(tax_val),
                "hsn_code": hsn_code,
                "storage_info": storage_info,
                "expiry_info": expiry_info,
                "description": description,
                "image_url": image_url,
                "has_errors": len(row_errors) > 0,
                "errors": row_errors,
            }

            if row_errors:
                error_report.append({
                    "row": idx,
                    "sku": sku or f"Row {idx}",
                    "title": title,
                    "errors": row_errors,
                })

            parsed_items.append(item_data)

        # If preview mode, return validation summary
        if is_preview:
            return Response(
                {
                    "preview": True,
                    "total_rows": len(rows),
                    "valid_rows_count": len([i for i in parsed_items if not i["has_errors"]]),
                    "invalid_rows_count": len(error_report),
                    "can_import": len(error_report) == 0,
                    "items": parsed_items[:50], # preview top 50
                    "errors": error_report,
                },
                status=status.HTTP_200_OK
            )

        # Atomic Bulk Import Execution
        if len(error_report) > 0:
            return Response(
                {
                    "error": f"Import blocked: {len(error_report)} row(s) failed validation. Please resolve the errors before importing.",
                    "total_rows": len(rows),
                    "failed_rows_count": len(error_report),
                    "errors": error_report,
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            batch = SellerCatalogUploadBatch.objects.create(
                company=company,
                uploaded_by=user,
                file_name=file_obj.name,
                total_rows=len(parsed_items),
                imported_rows=0,
                failed_rows=0,
                status=SellerCatalogUploadBatch.Status.PROCESSING,
            )

            created_products = []
            for item in parsed_items:
                prod = SellerProduct.objects.create(
                    company=company,
                    created_by=user,
                    category_id=item["category_id"],
                    title=item["title"],
                    description=item["description"],
                    brand=item["brand"],
                    sku=item["sku"],
                    barcode=item["barcode"],
                    unit=item["unit"],
                    pack_size=item["pack_size"],
                    mrp=Decimal(item["mrp"]),
                    selling_price=Decimal(item["selling_price"]),
                    tax_rate=Decimal(item["tax_rate"]),
                    hsn_code=item["hsn_code"],
                    storage_info=item["storage_info"],
                    expiry_info=item["expiry_info"],
                    status=SellerProduct.Status.DRAFT,
                    upload_batch=batch,
                )

                if item["image_url"]:
                    SellerProductImage.objects.create(
                        product=prod,
                        image_url=item["image_url"],
                        is_primary=True,
                        sort_order=0,
                    )

                SellerProductAuditLog.objects.create(
                    product=prod,
                    action="BULK_IMPORTED",
                    from_status="",
                    to_status=SellerProduct.Status.DRAFT,
                    actor=user,
                    notes=f"Imported from bulk file batch #{batch.id} ({file_obj.name}).",
                )
                created_products.append(prod)

            batch.imported_rows = len(created_products)
            batch.status = SellerCatalogUploadBatch.Status.COMPLETED
            batch.save(update_fields=["imported_rows", "status", "updated_at"])

        return Response(
            {
                "message": f"Successfully imported {len(created_products)} products into draft catalog.",
                "batch_id": batch.id,
                "total_rows": len(parsed_items),
                "imported_rows": len(created_products),
                "status": "COMPLETED",
            },
            status=status.HTTP_201_CREATED
        )


class SellerProductBatchListView(APIView):
    """
    GET /api/workforce/seller-hub/products/batches/ – List upload batch history
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        company_id = _resolve_user_company_id(user)

        qs = SellerCatalogUploadBatch.objects.select_related("company", "uploaded_by")
        if not is_super:
            if not company_id:
                return Response([], status=status.HTTP_200_OK)
            qs = qs.filter(company_id=company_id)

        serializer = SellerCatalogUploadBatchSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerProductImageUploadView(APIView):
    """
    POST /api/workforce/seller-hub/products/upload-image/ – Secure image upload handler
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image_file = request.FILES.get("image")
        if not image_file:
            return Response({"error": "No image file provided."}, status=status.HTTP_400_BAD_REQUEST)

        # File size check (< 5MB)
        if image_file.size > 5 * 1024 * 1024:
            return Response({"error": "Image file exceeds 5MB maximum limit."}, status=status.HTTP_400_BAD_REQUEST)

        content_type = getattr(image_file, "content_type", "").lower()
        if not any(content_type.startswith(p) for p in ("image/jpeg", "image/png", "image/webp", "image/gif")):
            return Response({"error": "Invalid image format. Allowed formats: JPG, PNG, WEBP, GIF."}, status=status.HTTP_400_BAD_REQUEST)

        ext = os.path.splitext(image_file.name)[1].lower() or ".jpg"
        unique_name = f"seller_products/{uuid.uuid4().hex}{ext}"
        saved_path = default_storage.save(unique_name, image_file)
        image_url = default_storage.url(saved_path)

        return Response(
            {
                "message": "Image uploaded successfully.",
                "image_url": image_url,
            },
            status=status.HTTP_201_CREATED
        )


class SellerHubMetricsView(APIView):
    """
    GET /api/workforce/seller-hub/metrics/ – Dynamic real DB summary counts for Seller Dashboard
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
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

        return Response(
            {
                "catalogs_awaiting_approval": awaiting_approval,
                "approved_products": approved_count,
                "draft_products": draft_count,
                "changes_requested": changes_requested,
                "rejected_products": rejected_count,
                "paused_products": paused_count,
                "total_products": total_products,
                "active_categories": categories_count,
                "active_coupons": active_coupons,
                # Phase 3 Inventory Metrics
                "total_inventory_products": total_inventory_products,
                "low_stock_items_count": low_stock_items,
                "out_of_stock_items_count": out_of_stock_items,
                "in_stock_items_count": in_stock_items,
                "expiring_soon_items_count": expiring_soon_count,
                "total_inventory_value": str(round(total_inv_value, 2)),
                # Phase 4 Order & Fulfilment Metrics
                "total_orders_count": total_orders,
                "pending_orders_count": pending_orders,
                "in_prep_orders_count": in_prep_orders,
                "completed_orders_count": completed_orders,
                "cancelled_orders_count": cancelled_orders,
                "today_orders_count": today_orders,
                # Phase 5 Return Metrics
                "total_returns_count": total_returns,
                "pending_returns_count": pending_returns,
                "under_inspection_returns_count": under_inspection_returns,
                "resolved_returns_count": resolved_returns,
                # Phase 6 Claims Metrics
                "total_claims_count": total_claims,
                "open_claims_count": open_claims,
                "claims_requiring_response_count": claims_requiring_response,
                "escalated_claims_count": escalated_claims,
                "resolved_claims_count": resolved_claims,
            },
            status=status.HTTP_200_OK
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SELLER HUB INVENTORY MANAGEMENT VIEWS (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerInventoryListView(APIView):
    """
    GET /api/workforce/seller-hub/inventory/ – List seller product inventory balances
    Supports filtering by stock status, category, search, and sorting.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        queryset = SellerInventory.objects.select_related(
            "company",
            "product",
            "product__category",
            "product__category__parent",
        ).prefetch_related("product__images", "batches")

        # Tenant Scoping: Sellers only see their company's inventory
        if not (is_super or (is_admin and not company_id)):
            if not company_id:
                return Response(
                    {"error": "User is not associated with an approved merchant store."},
                    status=status.HTTP_403_FORBIDDEN
                )
            queryset = queryset.filter(company_id=company_id)
        else:
            # Superadmin filter by target company
            target_company = request.query_params.get("company_id")
            if target_company and str(target_company).isdigit():
                queryset = queryset.filter(company_id=int(target_company))

        # Search filter
        search = request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(product__title__icontains=search) |
                models.Q(product__sku__icontains=search) |
                models.Q(product__brand__icontains=search) |
                models.Q(product__barcode__icontains=search)
            )

        # Category filter
        category_id = request.query_params.get("category_id")
        if category_id and str(category_id).isdigit():
            queryset = queryset.filter(product__category_id=int(category_id))

        # Status filter
        status_param = request.query_params.get("status", "").strip().upper()
        today = timezone.now().date()
        thirty_days = today + timezone.timedelta(days=30)

        if status_param == "IN_STOCK":
            queryset = queryset.filter(on_hand_qty__gt=models.F("low_stock_threshold"))
        elif status_param == "LOW_STOCK":
            queryset = queryset.filter(
                on_hand_qty__gt=Decimal("0.000"),
                on_hand_qty__lte=models.F("low_stock_threshold")
            )
        elif status_param == "OUT_OF_STOCK":
            queryset = queryset.filter(on_hand_qty__lte=Decimal("0.000"))
        elif status_param == "EXPIRING_SOON":
            expiring_inv_ids = SellerInventoryBatch.objects.filter(
                current_quantity__gt=Decimal("0.000"),
                expiry_date__isnull=False,
                expiry_date__lte=thirty_days,
                expiry_date__gte=today,
            ).values_list("inventory_id", flat=True)
            queryset = queryset.filter(id__in=expiring_inv_ids)
        elif status_param == "EXPIRED":
            expired_inv_ids = SellerInventoryBatch.objects.filter(
                current_quantity__gt=Decimal("0.000"),
                expiry_date__isnull=False,
                expiry_date__lt=today,
            ).values_list("inventory_id", flat=True)
            queryset = queryset.filter(id__in=expired_inv_ids)
        elif status_param == "PAUSED":
            queryset = queryset.filter(product__status=SellerProduct.Status.PAUSED)

        # Ordering
        ordering = request.query_params.get("ordering", "-updated_at")
        valid_orderings = [
            "-updated_at", "updated_at",
            "on_hand_qty", "-on_hand_qty",
            "product__title", "-product__title",
            "product__sku", "-product__sku",
            "created_at", "-created_at"
        ]
        if ordering in valid_orderings:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-updated_at")

        serializer = SellerInventoryListSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerInventoryDetailView(APIView):
    """
    GET   /api/workforce/seller-hub/inventory/<int:pk>/ – Get full inventory detail with batches and recent movements
    PATCH /api/workforce/seller-hub/inventory/<int:pk>/ – Update threshold / reorder levels
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_inventory(self, user, pk):
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        qs = SellerInventory.objects.select_related(
            "company",
            "product",
            "product__category",
            "product__category__parent",
        ).prefetch_related("product__images", "batches", "movements", "movements__actor", "movements__batch")

        if not (is_super or (is_admin and not company_id)):
            if not company_id:
                return None
            qs = qs.filter(company_id=company_id)

        return qs.filter(pk=pk).first()

    def get(self, request, pk):
        inv = self._get_inventory(request.user, pk)
        if not inv:
            return Response({"error": "Inventory record not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SellerInventoryDetailSerializer(inv)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        inv = self._get_inventory(request.user, pk)
        if not inv:
            return Response({"error": "Inventory record not found."}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        updated_fields = []

        if "low_stock_threshold" in data:
            try:
                thresh = Decimal(str(data["low_stock_threshold"]))
                if thresh < 0:
                    return Response({"error": "Low stock threshold cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                inv.low_stock_threshold = thresh
                updated_fields.append("low_stock_threshold")
            except (ValueError, TypeError, InvalidOperation):
                return Response({"error": "Invalid low stock threshold."}, status=status.HTTP_400_BAD_REQUEST)

        if "reorder_level" in data:
            try:
                reorder = Decimal(str(data["reorder_level"]))
                if reorder < 0:
                    return Response({"error": "Reorder level cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
                inv.reorder_level = reorder
                updated_fields.append("reorder_level")
            except (ValueError, TypeError, InvalidOperation):
                return Response({"error": "Invalid reorder level."}, status=status.HTTP_400_BAD_REQUEST)

        if updated_fields:
            updated_fields.append("updated_at")
            inv.save(update_fields=updated_fields)

        return Response(
            {
                "message": "Inventory thresholds updated successfully.",
                "inventory": SellerInventoryDetailSerializer(inv).data,
            },
            status=status.HTTP_200_OK
        )


class SellerInventoryInitializeView(APIView):
    """
    POST /api/workforce/seller-hub/inventory/initialize/ – Initialize inventory for an approved product
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        product_id = request.data.get("product_id")
        if not product_id or not str(product_id).isdigit():
            return Response({"error": "A valid product_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        prod_qs = SellerProduct.objects.filter(pk=int(product_id))
        if not is_super:
            if not company_id:
                return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
            prod_qs = prod_qs.filter(company_id=company_id)

        product = prod_qs.first()
        if not product:
            return Response({"error": "Product not found or does not belong to your store."}, status=status.HTTP_404_NOT_FOUND)

        # Rule: Only approved products can have inventory initialized
        if product.status != SellerProduct.Status.APPROVED and not is_super:
            return Response(
                {"error": f"Cannot initialize stock for product with status '{product.status}'. Product must be APPROVED."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if hasattr(product, "inventory") and product.inventory is not None:
            return Response(
                {"error": f"Product '{product.title}' already has an active inventory record."},
                status=status.HTTP_409_CONFLICT
            )

        on_hand_raw = request.data.get("on_hand_qty", "0.000")
        low_stock_raw = request.data.get("low_stock_threshold", "10.000")
        reorder_raw = request.data.get("reorder_level", "20.000")

        try:
            on_hand = Decimal(str(on_hand_raw))
            low_stock = Decimal(str(low_stock_raw))
            reorder = Decimal(str(reorder_raw))
            if on_hand < 0 or low_stock < 0 or reorder < 0:
                return Response({"error": "Quantities and thresholds cannot be negative."}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, TypeError, InvalidOperation):
            return Response({"error": "Invalid numeric format for quantities."}, status=status.HTTP_400_BAD_REQUEST)

        batch_number = str(request.data.get("batch_number", "")).strip()
        expiry_date = request.data.get("expiry_date")
        cost_price_raw = request.data.get("cost_price")
        cost_price = None
        if cost_price_raw is not None and str(cost_price_raw).strip():
            try:
                cost_price = Decimal(str(cost_price_raw))
            except (ValueError, TypeError, InvalidOperation):
                return Response({"error": "Invalid cost price."}, status=status.HTTP_400_BAD_REQUEST)

        reason = str(request.data.get("reason", "Opening initial inventory setup.")).strip()

        with transaction.atomic():
            inv, created = SellerInventory.objects.get_or_create(
                company=product.company,
                product=product,
                defaults={
                    "on_hand_qty": on_hand,
                    "reserved_qty": Decimal("0.000"),
                    "low_stock_threshold": low_stock,
                    "reorder_level": reorder,
                }
            )
            if not created:
                return Response(
                    {"error": f"Product '{product.title}' already has an active inventory record."},
                    status=status.HTTP_409_CONFLICT
                )

            batch = None
            if on_hand > Decimal("0.000") and batch_number:
                batch = SellerInventoryBatch.objects.create(
                    inventory=inv,
                    batch_number=batch_number,
                    received_date=timezone.now().date(),
                    expiry_date=expiry_date or None,
                    initial_quantity=on_hand,
                    current_quantity=on_hand,
                    cost_price=cost_price,
                    status=SellerInventoryBatch.BatchStatus.ACTIVE,
                )
                batch.update_dynamic_status(save=True)

            if on_hand > Decimal("0.000"):
                SellerInventoryMovement.objects.create(
                    inventory=inv,
                    batch=batch,
                    movement_type=SellerInventoryMovement.MovementType.OPENING_STOCK,
                    quantity_change=on_hand,
                    balance_before=Decimal("0.000"),
                    balance_after=on_hand,
                    reason=reason,
                    reference_id=batch_number or "INIT-STOCK",
                    actor=user,
                )

        return Response(
            {
                "message": f"Inventory for '{product.title}' initialized successfully.",
                "inventory": SellerInventoryDetailSerializer(inv).data,
            },
            status=status.HTTP_201_CREATED
        )


class SellerInventoryAdjustView(APIView):
    """
    POST /api/workforce/seller-hub/inventory/<int:pk>/adjust/ – Atomic stock adjustment with row locking
    Supported actions:
      - OPENING_STOCK
      - STOCK_IN
      - ADJUSTMENT_INCREASE
      - ADJUSTMENT_DECREASE (mandatory reason)
      - DAMAGE (mandatory reason)
      - EXPIRED (mandatory reason)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        serializer = SellerInventoryAdjustSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"error": "Validation failed.", "details": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        valid_data = serializer.validated_data
        movement_type = valid_data["movement_type"]
        qty = valid_data["quantity"]
        reason = valid_data.get("reason", "").strip()
        ref_id = valid_data.get("reference_id", "").strip()
        batch_number = valid_data.get("batch_number", "").strip()
        expiry_date = valid_data.get("expiry_date")
        cost_price = valid_data.get("cost_price")

        with transaction.atomic():
            # Acquire row lock on inventory balance
            qs = SellerInventory.objects.select_for_update().select_related("company", "product").filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                qs = qs.filter(company_id=company_id)

            inv = qs.first()
            if not inv:
                return Response({"error": "Inventory record not found."}, status=status.HTTP_404_NOT_FOUND)

            # Rule: Only approved products can have active stock movements
            if inv.product.status != SellerProduct.Status.APPROVED and not is_super:
                return Response(
                    {"error": f"Cannot adjust stock for product with status '{inv.product.status}'. Product must be APPROVED."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            balance_before = inv.on_hand_qty
            batch = None

            is_increase = movement_type in (
                SellerInventoryMovement.MovementType.OPENING_STOCK,
                SellerInventoryMovement.MovementType.STOCK_IN,
                SellerInventoryMovement.MovementType.ADJUSTMENT_INCREASE,
            )

            if is_increase:
                qty_change = qty
                balance_after = balance_before + qty

                # Handle batch creation/increment
                if batch_number:
                    batch, created = SellerInventoryBatch.objects.get_or_create(
                        inventory=inv,
                        batch_number=batch_number,
                        defaults={
                            "received_date": timezone.now().date(),
                            "expiry_date": expiry_date,
                            "initial_quantity": qty,
                            "current_quantity": qty,
                            "cost_price": cost_price,
                            "status": SellerInventoryBatch.BatchStatus.ACTIVE,
                        }
                    )
                    if not created:
                        batch.current_quantity += qty
                        if expiry_date and not batch.expiry_date:
                            batch.expiry_date = expiry_date
                        if cost_price and not batch.cost_price:
                            batch.cost_price = cost_price
                        batch.update_dynamic_status(save=True)
                    else:
                        batch.update_dynamic_status(save=True)
            else:
                # Stock decrease / damage / expiry
                qty_change = -qty
                if balance_before < qty:
                    return Response(
                        {
                            "error": f"Insufficient on-hand stock ({balance_before} {inv.product.unit}) for requested reduction of {qty} {inv.product.unit}."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if (balance_before - inv.reserved_qty) < qty:
                    return Response(
                        {
                            "error": f"Cannot reduce stock below reserved amount ({inv.reserved_qty} {inv.product.unit} currently reserved)."
                        },
                        status=status.HTTP_400_BAD_REQUEST
                    )

                balance_after = balance_before - qty

                # Handle batch deduction
                if batch_number:
                    batch = SellerInventoryBatch.objects.filter(inventory=inv, batch_number=batch_number).first()
                    if batch:
                        batch.current_quantity = max(Decimal("0.000"), batch.current_quantity - qty)
                        batch.update_dynamic_status(save=True)
                else:
                    # Deduct FIFO from active batches
                    remaining_to_deduct = qty
                    active_batches = inv.batches.filter(current_quantity__gt=Decimal("0.000")).order_by("expiry_date", "created_at")
                    for b in active_batches:
                        if remaining_to_deduct <= 0:
                            break
                        deduct_from_b = min(b.current_quantity, remaining_to_deduct)
                        b.current_quantity -= deduct_from_b
                        b.update_dynamic_status(save=True)
                        remaining_to_deduct -= deduct_from_b

            # Update inventory on-hand balance
            inv.on_hand_qty = balance_after
            inv.save(update_fields=["on_hand_qty", "updated_at"])

            # Create immutable ledger movement record
            movement = SellerInventoryMovement.objects.create(
                inventory=inv,
                batch=batch,
                movement_type=movement_type,
                quantity_change=qty_change,
                balance_before=balance_before,
                balance_after=balance_after,
                reason=reason or f"Stock action '{movement_type}' performed by {user.username}.",
                reference_id=ref_id or batch_number or "",
                actor=user,
            )

        return Response(
            {
                "message": f"Stock movement '{movement_type}' recorded successfully.",
                "movement": SellerInventoryMovementSerializer(movement).data,
                "inventory": SellerInventoryDetailSerializer(inv).data,
            },
            status=status.HTTP_200_OK
        )


class SellerInventoryMovementListView(APIView):
    """
    GET /api/workforce/seller-hub/inventory/<int:pk>/movements/ – Filterable movement ledger
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        inv_qs = SellerInventory.objects.filter(pk=pk)
        if not is_super:
            if not company_id:
                return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
            inv_qs = inv_qs.filter(company_id=company_id)

        inv = inv_qs.first()
        if not inv:
            return Response({"error": "Inventory record not found."}, status=status.HTTP_404_NOT_FOUND)

        movements = inv.movements.select_related("actor", "batch").order_by("-created_at")

        # Movement type filter
        mtype = request.query_params.get("movement_type", "").strip()
        if mtype:
            movements = movements.filter(movement_type=mtype)

        # Date range filters
        start_date = request.query_params.get("start_date")
        if start_date:
            movements = movements.filter(created_at__date__gte=start_date)

        end_date = request.query_params.get("end_date")
        if end_date:
            movements = movements.filter(created_at__date__lte=end_date)

        serializer = SellerInventoryMovementSerializer(movements, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerInventoryBatchListView(APIView):
    """
    GET /api/workforce/seller-hub/inventory/<int:pk>/batches/ – List batches for inventory
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        inv_qs = SellerInventory.objects.filter(pk=pk)
        if not is_super:
            if not company_id:
                return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
            inv_qs = inv_qs.filter(company_id=company_id)

        inv = inv_qs.first()
        if not inv:
            return Response({"error": "Inventory record not found."}, status=status.HTTP_404_NOT_FOUND)

        batches = inv.batches.all().order_by("expiry_date", "-created_at")
        for b in batches:
            b.update_dynamic_status(save=False)

        serializer = SellerInventoryBatchSerializer(batches, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. SELLER HUB ORDERS & FULFILMENT VIEWS (Phase 4)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerOrderListView(APIView):
    """
    GET /api/workforce/seller-hub/orders/ – List seller fulfilment orders.
    Supports status filters, search, fulfillment type, and pagination.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        queryset = SellerOrder.objects.select_related("company").prefetch_related("items", "items__product")

        if not is_super:
            if not company_id:
                return Response({"count": 0, "results": []}, status=status.HTTP_200_OK)
            queryset = queryset.filter(company_id=company_id)
        else:
            filter_company = request.query_params.get("company_id")
            if filter_company:
                queryset = queryset.filter(company_id=filter_company)

        # Status filter
        status_filter = request.query_params.get("status", "").strip().upper()
        if status_filter and status_filter != "ALL":
            if status_filter == "IN_PREPARATION":
                queryset = queryset.filter(
                    status__in=[
                        SellerOrder.Status.ACCEPTED,
                        SellerOrder.Status.PICKING,
                        SellerOrder.Status.PACKED,
                        SellerOrder.Status.READY_FOR_PICKUP,
                    ]
                )
            elif status_filter == "COMPLETED":
                queryset = queryset.filter(
                    status__in=[
                        SellerOrder.Status.HANDED_OVER,
                        SellerOrder.Status.DELIVERED,
                    ]
                )
            elif status_filter in SellerOrder.Status.values:
                queryset = queryset.filter(status=status_filter)

        # Fulfillment type filter
        ftype = request.query_params.get("fulfillment_type", "").strip().upper()
        if ftype in SellerOrder.FulfillmentType.values:
            queryset = queryset.filter(fulfillment_type=ftype)

        # Date range filter
        start_date = request.query_params.get("start_date")
        if start_date:
            queryset = queryset.filter(created_at__date__gte=start_date)
        end_date = request.query_params.get("end_date")
        if end_date:
            queryset = queryset.filter(created_at__date__lte=end_date)

        # Search filter
        search_query = request.query_params.get("search", "").strip()
        if search_query:
            queryset = queryset.filter(
                models.Q(order_number__icontains=search_query)
                | models.Q(source_order_id__icontains=search_query)
                | models.Q(customer_name__icontains=search_query)
                | models.Q(customer_phone__icontains=search_query)
                | models.Q(items__product_title__icontains=search_query)
                | models.Q(items__sku__icontains=search_query)
            ).distinct()

        queryset = queryset.order_by("-created_at")

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

        serializer = SellerOrderListSerializer(page_items, many=True)
        return Response(
            {
                "count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size if total_count > 0 else 1,
                "results": serializer.data,
            },
            status=status.HTTP_200_OK
        )


class SellerOrderDetailView(APIView):
    """
    GET /api/workforce/seller-hub/orders/<int:pk>/ – Detailed order with items & audit history
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        order_qs = SellerOrder.objects.filter(pk=pk).select_related("company").prefetch_related("items", "items__product", "audit_logs", "audit_logs__actor")
        if not is_super:
            if not company_id:
                return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
            order_qs = order_qs.filter(company_id=company_id)

        order = order_qs.first()
        if not order:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SellerOrderDetailSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerOrderStatusTransitionView(APIView):
    """
    POST /api/workforce/seller-hub/orders/<int:pk>/transition/ – Advance or Cancel order state.
    Executes atomic state changes and inventory adjustments with row-locking.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        serializer = SellerOrderStatusTransitionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action = serializer.validated_data["action"]
        notes = serializer.validated_data.get("notes", "").strip()
        cancellation_reason = serializer.validated_data.get("cancellation_reason", "").strip()
        handover_ref = serializer.validated_data.get("handover_ref", "").strip()

        # Action to Target Status Mapping
        ACTION_TARGET_STATUS = {
            "accept": SellerOrder.Status.ACCEPTED,
            "start_picking": SellerOrder.Status.PICKING,
            "mark_packed": SellerOrder.Status.PACKED,
            "mark_ready": SellerOrder.Status.READY_FOR_PICKUP,
            "handover": SellerOrder.Status.HANDED_OVER,
            "deliver": SellerOrder.Status.DELIVERED,
            "cancel": SellerOrder.Status.CANCELLED,
        }

        target_status = ACTION_TARGET_STATUS.get(action)
        if not target_status:
            return Response({"error": f"Unknown transition action '{action}'."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            order_qs = SellerOrder.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                order_qs = order_qs.filter(company_id=company_id)

            order = order_qs.first()
            if not order:
                return Response({"error": "Order not found or permission denied."}, status=status.HTTP_404_NOT_FOUND)

            from_status = order.status

            # Validate State Machine Transition
            if not order.can_transition_to(target_status):
                return Response(
                    {
                        "error": f"Invalid state transition from '{from_status}' to '{target_status}'.",
                        "current_status": from_status,
                        "allowed_transitions": order.ALLOWED_TRANSITIONS.get(from_status, []),
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            now = timezone.now()

            # Handle status timestamps & state-specific logic
            if target_status == SellerOrder.Status.ACCEPTED:
                order.accepted_at = now
            elif target_status == SellerOrder.Status.PICKING:
                order.picking_at = now
            elif target_status == SellerOrder.Status.PACKED:
                order.packed_at = now
            elif target_status == SellerOrder.Status.READY_FOR_PICKUP:
                order.ready_at = now
            elif target_status == SellerOrder.Status.HANDED_OVER:
                order.handed_over_at = now
                if handover_ref:
                    order.handover_ref = handover_ref
                # Deduct inventory upon Handover (if stock was reserved)
                self._deduct_inventory_for_order(order, user, notes or f"Handover for order #{order.order_number}")
            elif target_status == SellerOrder.Status.DELIVERED:
                order.delivered_at = now
                # If delivered without prior handover deduction, ensure deducted
                self._deduct_inventory_for_order(order, user, notes or f"Delivered order #{order.order_number}")
            elif target_status == SellerOrder.Status.CANCELLED:
                order.cancelled_at = now
                order.cancellation_reason = cancellation_reason
                order.cancelled_by = user
                # Release reserved inventory on cancellation
                self._release_inventory_reservations(order, user, cancellation_reason)

            order.status = target_status
            if notes:
                order.seller_notes = (order.seller_notes + f"\n[{now.strftime('%Y-%m-%d %H:%M')}] " + notes).strip()

            order.save()

            # Create immutable audit log
            SellerOrderAuditLog.objects.create(
                order=order,
                from_status=from_status,
                to_status=target_status,
                action=f"Order {action.replace('_', ' ').title()}",
                actor=user,
                notes=cancellation_reason if target_status == SellerOrder.Status.CANCELLED else notes,
            )

            # Record outbox status event within the same transaction
            record_seller_order_status_event(
                order=order,
                previous_status=from_status,
                new_status=target_status,
                event_type="seller_order.cancelled" if target_status == SellerOrder.Status.CANCELLED else "seller_order.status_updated",
                actor=user,
                cancellation_source="SELLER" if target_status == SellerOrder.Status.CANCELLED else None,
            )

        detail_serializer = SellerOrderDetailSerializer(order)
        return Response(
            {
                "message": f"Order status updated to '{target_status}'.",
                "order": detail_serializer.data,
            },
            status=status.HTTP_200_OK
        )

    def _deduct_inventory_for_order(self, order, user, reason):
        """
        Deducts physical on-hand stock and releases the active reservation for fulfilled order items.
        """
        for item in order.items.select_related("product"):
            if not item.product:
                continue
            inv = SellerInventory.objects.select_for_update().filter(
                company=order.company,
                product=item.product,
            ).first()

            if not inv:
                continue

            qty_to_deduct = item.ordered_quantity
            bal_before = inv.on_hand_qty
            bal_after = max(Decimal("0.000"), inv.on_hand_qty - qty_to_deduct)
            reserved_after = max(Decimal("0.000"), inv.reserved_qty - qty_to_deduct)

            inv.on_hand_qty = bal_after
            inv.reserved_qty = reserved_after
            inv.save(update_fields=["on_hand_qty", "reserved_qty", "updated_at"])

            # Deduct from batch if linked
            if item.batch:
                b = SellerInventoryBatch.objects.select_for_update().filter(pk=item.batch.pk).first()
                if b:
                    b.current_quantity = max(Decimal("0.000"), b.current_quantity - qty_to_deduct)
                    b.update_dynamic_status(save=True)

            # Record ORDER_DEDUCTED movement
            SellerInventoryMovement.objects.create(
                inventory=inv,
                batch=item.batch,
                movement_type=SellerInventoryMovement.MovementType.ORDER_DEDUCTED,
                quantity_change=-qty_to_deduct,
                balance_before=bal_before,
                balance_after=bal_after,
                reason=reason,
                reference_id=order.source_order_id or order.order_number,
                actor=user,
            )

    def _release_inventory_reservations(self, order, user, reason):
        """
        Releases reserved inventory allocations when an order is cancelled.
        """
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
            bal_before = inv.on_hand_qty
            reserved_after = max(Decimal("0.000"), inv.reserved_qty - qty_to_release)

            inv.reserved_qty = reserved_after
            inv.save(update_fields=["reserved_qty", "updated_at"])

            # Record RESERVATION_RELEASED movement
            SellerInventoryMovement.objects.create(
                inventory=inv,
                batch=item.batch,
                movement_type=SellerInventoryMovement.MovementType.RESERVATION_RELEASED,
                quantity_change=Decimal("0.000"),
                balance_before=bal_before,
                balance_after=bal_before,
                reason=f"Order #{order.order_number} cancelled: {reason}",
                reference_id=order.source_order_id or order.order_number,
                actor=user,
            )


class SellerOrderItemPickView(APIView):
    """
    POST /api/workforce/seller-hub/orders/<int:pk>/item-pick/ – Pick/pack individual item
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        serializer = SellerOrderItemPickSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        item_id = serializer.validated_data["item_id"]
        is_picked = serializer.validated_data.get("is_picked")
        is_packed = serializer.validated_data.get("is_packed")
        fulfilled_qty = serializer.validated_data.get("fulfilled_quantity")
        batch_id = serializer.validated_data.get("batch_id")
        notes = serializer.validated_data.get("notes", "").strip()

        with transaction.atomic():
            order_qs = SellerOrder.objects.filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                order_qs = order_qs.filter(company_id=company_id)

            order = order_qs.first()
            if not order:
                return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

            item = order.items.filter(pk=item_id).first()
            if not item:
                return Response({"error": "Order item not found."}, status=status.HTTP_404_NOT_FOUND)

            if is_picked is not None:
                item.is_picked = is_picked
                if is_picked and fulfilled_qty is None:
                    item.fulfilled_quantity = item.ordered_quantity

            if is_packed is not None:
                item.is_packed = is_packed

            if fulfilled_qty is not None:
                item.fulfilled_quantity = fulfilled_qty

            if batch_id is not None:
                if batch_id:
                    batch = SellerInventoryBatch.objects.filter(pk=batch_id).first()
                    item.batch = batch
                else:
                    item.batch = None

            if notes:
                item.notes = notes

            item.save()

        return Response(
            {
                "message": "Order item updated successfully.",
                "item": SellerOrderItemSerializer(item).data,
            },
            status=status.HTTP_200_OK
        )


class SellerOrderPackingSlipView(APIView):
    """
    GET /api/workforce/seller-hub/orders/<int:pk>/packing-slip/ – Printable packing slip dataset
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        order_qs = SellerOrder.objects.filter(pk=pk).select_related("company").prefetch_related("items", "items__product")
        if not is_super:
            if not company_id:
                return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
            order_qs = order_qs.filter(company_id=company_id)

        order = order_qs.first()
        if not order:
            return Response({"error": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        company = order.company
        packing_slip_data = {
            "order_number": order.order_number,
            "source_order_id": order.source_order_id,
            "order_date": order.created_at.strftime("%d %b %Y, %I:%M %p"),
            "status": order.status,
            "fulfillment_type": order.fulfillment_type,
            "delivery_slot": order.delivery_slot,
            "delivery_notes": order.delivery_notes,
            "seller": {
                "name": company.company_name or company.name,
                "phone": getattr(company, "phone_number", ""),
                "address": getattr(company, "address", ""),
            },
            "customer": {
                "name": order.customer_name,
                "phone": order.customer_phone,
                "delivery_address": order.delivery_address,
            },
            "items": [
                {
                    "id": it.id,
                    "title": it.product_title,
                    "sku": it.sku,
                    "unit": it.unit,
                    "pack_size": it.pack_size,
                    "ordered_qty": str(it.ordered_quantity),
                    "fulfilled_qty": str(it.fulfilled_quantity),
                    "unit_price": str(it.unit_price),
                    "line_total": str(it.line_total),
                    "is_picked": it.is_picked,
                    "is_packed": it.is_packed,
                    "batch_number": it.batch.batch_number if it.batch else None,
                }
                for it in order.items.all()
            ],
            "total_amount": str(order.total_amount),
            "currency": order.currency,
            "payment_method": order.payment_method,
            "payment_status": order.payment_status,
        }

        return Response(packing_slip_data, status=status.HTTP_200_OK)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SELLER HUB RETURNS & REVERSE LOGISTICS VIEWS (Phase 5)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerReturnListView(APIView):
    """
    GET /api/workforce/seller-hub/returns/ – List return cases for seller
    Query filters: search, status, reason, date_from, date_to, ordering
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        qs = SellerReturn.objects.select_related("company", "order").prefetch_related("items")

        # Multi-Tenant Scoping: sellers only access their own returns
        if not (is_super or (is_admin and not company_id)):
            if not company_id:
                return Response(
                    {"error": "User is not associated with an approved merchant store."},
                    status=status.HTTP_403_FORBIDDEN
                )
            qs = qs.filter(company_id=company_id)
        else:
            target_company = request.query_params.get("company_id")
            if target_company and str(target_company).isdigit():
                qs = qs.filter(company_id=int(target_company))

        # Search filter
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                models.Q(return_number__icontains=search) |
                models.Q(source_return_id__icontains=search) |
                models.Q(order__order_number__icontains=search) |
                models.Q(customer_name__icontains=search) |
                models.Q(customer_phone__icontains=search) |
                models.Q(reason__icontains=search) |
                models.Q(items__product_title__icontains=search)
            ).distinct()

        # Status filter
        status_param = request.query_params.get("status", "").strip().upper()
        if status_param and status_param != "ALL":
            if status_param == "PENDING":
                qs = qs.filter(status__in=[SellerReturn.Status.REQUESTED, SellerReturn.Status.UNDER_SELLER_REVIEW])
            elif status_param == "IN_INSPECTION":
                qs = qs.filter(status__in=[
                    SellerReturn.Status.APPROVED,
                    SellerReturn.Status.PICKUP_SCHEDULED,
                    SellerReturn.Status.RECEIVED,
                    SellerReturn.Status.QUALITY_CHECK,
                ])
            elif status_param == "RESOLVED":
                qs = qs.filter(status__in=[
                    SellerReturn.Status.RESTOCKED,
                    SellerReturn.Status.CLOSED,
                    SellerReturn.Status.DISCARDED,
                    SellerReturn.Status.REJECTED,
                ])
            else:
                qs = qs.filter(status=status_param)

        # Reason filter
        reason_param = request.query_params.get("reason", "").strip()
        if reason_param:
            qs = qs.filter(reason=reason_param)

        # Date range filter
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        valid_orderings = [
            "-created_at", "created_at",
            "-updated_at", "updated_at",
            "status", "-status",
            "return_number", "-return_number",
        ]
        if ordering in valid_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-created_at")

        serializer = SellerReturnListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerReturnDetailView(APIView):
    """
    GET /api/workforce/seller-hub/returns/<int:pk>/ – Get return case details, line items, and audit trail
    """
    permission_classes = [permissions.IsAuthenticated]

    def _get_return(self, user, pk):
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        is_admin = is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        qs = SellerReturn.objects.select_related(
            "company",
            "order",
            "quality_checked_by",
        ).prefetch_related(
            "items",
            "items__product",
            "items__order_item",
            "audit_logs",
            "audit_logs__actor",
        )

        if not (is_super or (is_admin and not company_id)):
            if not company_id:
                return None
            qs = qs.filter(company_id=company_id)

        return qs.filter(pk=pk).first()

    def get(self, request, pk):
        ret = self._get_return(request.user, pk)
        if not ret:
            return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SellerReturnDetailSerializer(ret)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerReturnReviewView(APIView):
    """
    POST /api/workforce/seller-hub/returns/<int:pk>/review/ – Seller review decision (Approve / Reject / Escalate)
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        serializer = SellerReturnReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        decision = serializer.validated_data["decision"]
        seller_notes = serializer.validated_data.get("seller_notes", "").strip()
        rejection_reason = serializer.validated_data.get("rejection_reason", "").strip()

        with transaction.atomic():
            ret_qs = SellerReturn.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                ret_qs = ret_qs.filter(company_id=company_id)

            ret = ret_qs.first()
            if not ret:
                return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

            valid_statuses = [SellerReturn.Status.REQUESTED, SellerReturn.Status.UNDER_SELLER_REVIEW]
            if ret.status not in valid_statuses:
                return Response(
                    {"error": f"Cannot review return in state '{ret.status}'. Must be in REQUESTED or UNDER_SELLER_REVIEW."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_status = ret.status
            now = timezone.now()

            if decision == "approve":
                to_status = SellerReturn.Status.APPROVED
                ret.status = to_status
                ret.seller_decision = "APPROVED"
                ret.reviewed_at = now
                if seller_notes:
                    ret.seller_notes = seller_notes
                action_text = "APPROVED"
                notes_text = f"Return approved by seller: {seller_notes}" if seller_notes else "Return approved by seller."
            elif decision == "reject":
                to_status = SellerReturn.Status.REJECTED
                ret.status = to_status
                ret.seller_decision = "REJECTED"
                ret.rejection_reason = rejection_reason
                ret.reviewed_at = now
                if seller_notes:
                    ret.seller_notes = seller_notes
                action_text = "REJECTED"
                notes_text = f"Return rejected by seller: {rejection_reason}"
            else: # escalate
                to_status = SellerReturn.Status.ESCALATED_TO_ADMIN
                ret.status = to_status
                ret.seller_decision = "ESCALATED_TO_ADMIN"
                if seller_notes:
                    ret.seller_notes = seller_notes
                action_text = "ESCALATED_TO_ADMIN"
                notes_text = f"Return escalated to platform admin: {seller_notes}" if seller_notes else "Return escalated to platform admin."

            ret.save()

            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action=action_text,
                from_status=from_status,
                to_status=to_status,
                actor=user,
                notes=notes_text,
            )

        return Response(
            {
                "message": f"Return #{ret.return_number} review decision recorded as {decision.upper()}.",
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_200_OK
        )


class SellerReturnSchedulePickupView(APIView):
    """
    POST /api/workforce/seller-hub/returns/<int:pk>/schedule-pickup/ – Schedule return item pickup / courier
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        pickup_ref = str(request.data.get("pickup_ref", "")).strip()
        notes = str(request.data.get("notes", "")).strip()

        with transaction.atomic():
            ret_qs = SellerReturn.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                ret_qs = ret_qs.filter(company_id=company_id)

            ret = ret_qs.first()
            if not ret:
                return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

            if ret.status != SellerReturn.Status.APPROVED:
                return Response(
                    {"error": f"Cannot schedule pickup for return in state '{ret.status}'. Must be APPROVED."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_status = ret.status
            to_status = SellerReturn.Status.PICKUP_SCHEDULED
            ret.status = to_status
            if pickup_ref:
                ret.pickup_ref = pickup_ref
            ret.save()

            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action="PICKUP_SCHEDULED",
                from_status=from_status,
                to_status=to_status,
                actor=user,
                notes=f"Pickup scheduled. Ref: {pickup_ref or 'N/A'}. {notes}".strip(),
            )

        return Response(
            {
                "message": f"Pickup scheduled for Return #{ret.return_number}.",
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_200_OK
        )


class SellerReturnReceiveView(APIView):
    """
    POST /api/workforce/seller-hub/returns/<int:pk>/receive/ – Acknowledge receipt of returned parcel at seller store
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        notes = str(request.data.get("notes", "")).strip()

        with transaction.atomic():
            ret_qs = SellerReturn.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                ret_qs = ret_qs.filter(company_id=company_id)

            ret = ret_qs.first()
            if not ret:
                return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

            valid_statuses = [SellerReturn.Status.APPROVED, SellerReturn.Status.PICKUP_SCHEDULED]
            if ret.status not in valid_statuses:
                return Response(
                    {"error": f"Cannot mark received for return in state '{ret.status}'. Must be APPROVED or PICKUP_SCHEDULED."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_status = ret.status
            to_status = SellerReturn.Status.RECEIVED
            ret.status = to_status
            ret.received_at = timezone.now()
            ret.save()

            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action="RECEIVED",
                from_status=from_status,
                to_status=to_status,
                actor=user,
                notes=f"Return package received at store: {notes}" if notes else "Return package received at store.",
            )

        return Response(
            {
                "message": f"Return #{ret.return_number} marked as received at store.",
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_200_OK
        )


class SellerReturnQualityCheckView(APIView):
    """
    POST /api/workforce/seller-hub/returns/<int:pk>/quality-check/ – Perform physical product quality check
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        serializer = SellerReturnQualityCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        qc_status = serializer.validated_data["quality_check_status"]
        qc_notes = serializer.validated_data.get("quality_check_notes", "").strip()
        items_qc = serializer.validated_data.get("items_qc", [])

        with transaction.atomic():
            ret_qs = SellerReturn.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                ret_qs = ret_qs.filter(company_id=company_id)

            ret = ret_qs.first()
            if not ret:
                return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

            valid_statuses = [SellerReturn.Status.RECEIVED, SellerReturn.Status.QUALITY_CHECK]
            if ret.status not in valid_statuses:
                return Response(
                    {"error": f"Cannot perform quality check on return in state '{ret.status}'. Must be RECEIVED or QUALITY_CHECK."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_status = ret.status
            to_status = SellerReturn.Status.QUALITY_CHECK
            ret.status = to_status
            ret.quality_check_status = qc_status
            ret.quality_check_notes = qc_notes
            ret.quality_checked_by = user
            ret.inspected_at = timezone.now()
            ret.save()

            # Process individual item QC results if provided
            for it_data in items_qc:
                item_id = it_data.get("item_id")
                if not item_id:
                    continue
                item_obj = ret.items.filter(pk=item_id).first()
                if item_obj:
                    if "item_condition" in it_data:
                        item_obj.item_condition = it_data["item_condition"]
                    if "qc_result" in it_data:
                        item_obj.qc_result = it_data["qc_result"]
                    if "qc_notes" in it_data:
                        item_obj.qc_notes = str(it_data["qc_notes"]).strip()
                    item_obj.save()

            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action="QUALITY_CHECKED",
                from_status=from_status,
                to_status=to_status,
                actor=user,
                notes=f"Quality check completed with status '{qc_status}': {qc_notes}".strip(),
            )

        return Response(
            {
                "message": f"Quality inspection recorded for Return #{ret.return_number}.",
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_200_OK
        )


class SellerReturnRestockView(APIView):
    """
    POST /api/workforce/seller-hub/returns/<int:pk>/restock/ – Restock verified goods into live inventory ledger
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        serializer = SellerReturnRestockSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        restock_decision = serializer.validated_data["restock_decision"]
        restock_notes = serializer.validated_data.get("restock_notes", "").strip()
        items_breakdown = serializer.validated_data.get("items_breakdown", [])

        with transaction.atomic():
            ret_qs = SellerReturn.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                ret_qs = ret_qs.filter(company_id=company_id)

            ret = ret_qs.first()
            if not ret:
                return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

            # Idempotency check: if already processed for restocking, reject duplicate execution
            if ret.status in [SellerReturn.Status.RESTOCKED, SellerReturn.Status.DISCARDED, SellerReturn.Status.CLOSED] or ret.restocked_at is not None:
                return Response(
                    {"error": f"Return #{ret.return_number} has already been processed for restocking (Status: '{ret.status}'). Duplicate restock operations are blocked."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            valid_statuses = [SellerReturn.Status.QUALITY_CHECK, SellerReturn.Status.RECEIVED]
            if ret.status not in valid_statuses:
                return Response(
                    {"error": f"Cannot restock return in state '{ret.status}'. Must be QUALITY_CHECK or RECEIVED."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_status = ret.status
            total_restocked_units = Decimal("0.000")
            total_scrapped_units = Decimal("0.000")

            # Map breakdown by item_id
            breakdown_map = {b.get("item_id"): b for b in items_breakdown if b.get("item_id")}

            for item in ret.items.select_for_update().all():
                b_info = breakdown_map.get(item.id)

                if b_info:
                    try:
                        restock_qty = Decimal(str(b_info.get("restocked_quantity", "0.000")))
                        scrap_qty = Decimal(str(b_info.get("scrapped_quantity", "0.000")))
                    except (InvalidOperation, ValueError, TypeError):
                        restock_qty = Decimal("0.000")
                        scrap_qty = Decimal("0.000")
                elif restock_decision == "FULL_RESTOCK":
                    restock_qty = item.returned_quantity
                    scrap_qty = Decimal("0.000")
                elif restock_decision == "SCRAP_DISPOSE":
                    restock_qty = Decimal("0.000")
                    scrap_qty = item.returned_quantity
                else: # PARTIAL default
                    restock_qty = item.returned_quantity
                    scrap_qty = Decimal("0.000")

                # Ensure non-negative and capped to returned_quantity
                restock_qty = max(Decimal("0.000"), min(restock_qty, item.returned_quantity))
                scrap_qty = max(Decimal("0.000"), min(scrap_qty, item.returned_quantity - restock_qty))

                item.restocked_quantity = restock_qty
                item.scrapped_quantity = scrap_qty
                item.save(update_fields=["restocked_quantity", "scrapped_quantity"])

                total_restocked_units += restock_qty
                total_scrapped_units += scrap_qty

                order_ref = ret.order.order_number if ret.order else "N/A"
                compound_ref = f"RET:{ret.return_number}|ORD:{order_ref}"

                # Execute inventory balance update for restocked units
                if restock_qty > Decimal("0.000") and item.product:
                    inv = SellerInventory.objects.select_for_update().filter(
                        company=ret.company,
                        product=item.product,
                    ).first()

                    if inv:
                        bal_before = inv.on_hand_qty
                        bal_after = bal_before + restock_qty
                        inv.on_hand_qty = bal_after
                        inv.save(update_fields=["on_hand_qty", "updated_at"])

                        # If batch exists, increment batch quantity as well
                        batch_obj = None
                        if item.order_item and item.order_item.batch:
                            batch_obj = item.order_item.batch
                            batch_obj.current_quantity = batch_obj.current_quantity + restock_qty
                            batch_obj.save(update_fields=["current_quantity", "updated_at"])

                        # Create dedicated immutable RETURN_RESTOCK inventory movement record
                        SellerInventoryMovement.objects.create(
                            inventory=inv,
                            batch=batch_obj,
                            movement_type=SellerInventoryMovement.MovementType.RETURN_RESTOCK,
                            quantity_change=restock_qty,
                            balance_before=bal_before,
                            balance_after=bal_after,
                            reason=f"Customer Return Restock #{ret.return_number} (Order #{order_ref}) | QC: {ret.quality_check_status} | Reason: {ret.reason} | Notes: {restock_notes or 'None'}",
                            reference_id=compound_ref,
                            actor=user,
                        )

                # Log scrapped units disposal movement if any (DAMAGE type)
                if scrap_qty > Decimal("0.000") and item.product:
                    inv = SellerInventory.objects.filter(
                        company=ret.company,
                        product=item.product,
                    ).first()
                    if inv:
                        SellerInventoryMovement.objects.create(
                            inventory=inv,
                            batch=item.order_item.batch if item.order_item else None,
                            movement_type=SellerInventoryMovement.MovementType.DAMAGE,
                            quantity_change=Decimal("0.000"), # damaged units were already deducted on sale
                            balance_before=inv.on_hand_qty,
                            balance_after=inv.on_hand_qty,
                            reason=f"Customer Return Damaged/Scrapped #{ret.return_number} (Order #{order_ref}) | Scrapped: {scrap_qty} units | QC: {ret.quality_check_status} | Reason: {ret.reason} | Notes: {restock_notes or 'None'}",
                            reference_id=compound_ref,
                            actor=user,
                        )

            # Finalize return status
            if total_restocked_units > Decimal("0.000"):
                to_status = SellerReturn.Status.RESTOCKED
            else:
                to_status = SellerReturn.Status.DISCARDED

            ret.status = to_status
            ret.restock_decision = restock_decision
            ret.restock_notes = restock_notes
            ret.restocked_at = timezone.now()
            ret.save()

            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action="RESTOCKED" if to_status == SellerReturn.Status.RESTOCKED else "DISCARDED",
                from_status=from_status,
                to_status=to_status,
                actor=user,
                notes=f"Restock processed ({total_restocked_units} restocked, {total_scrapped_units} scrapped). Notes: {restock_notes}".strip(),
            )

        return Response(
            {
                "message": f"Return #{ret.return_number} restock completed ({total_restocked_units} items returned to stock).",
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_200_OK
        )


class SellerReturnCloseView(APIView):
    """
    POST /api/workforce/seller-hub/returns/<int:pk>/close/ – Mark return case as resolved and closed
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        company_id = _resolve_user_company_id(user)
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        notes = str(request.data.get("notes", "")).strip()

        with transaction.atomic():
            ret_qs = SellerReturn.objects.select_for_update().filter(pk=pk)
            if not is_super:
                if not company_id:
                    return Response({"error": "Merchant company not found."}, status=status.HTTP_403_FORBIDDEN)
                ret_qs = ret_qs.filter(company_id=company_id)

            ret = ret_qs.first()
            if not ret:
                return Response({"error": "Return case not found."}, status=status.HTTP_404_NOT_FOUND)

            valid_statuses = [
                SellerReturn.Status.RESTOCKED,
                SellerReturn.Status.DISCARDED,
                SellerReturn.Status.REJECTED,
                SellerReturn.Status.QUALITY_CHECK,
                SellerReturn.Status.CLOSED,
            ]
            if ret.status not in valid_statuses:
                return Response(
                    {"error": f"Cannot close return in state '{ret.status}'. Return must be restocked, discarded, or rejected first."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            from_status = ret.status
            to_status = SellerReturn.Status.CLOSED
            ret.status = to_status
            ret.closed_at = timezone.now()
            ret.save()

            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action="CLOSED",
                from_status=from_status,
                to_status=to_status,
                actor=user,
                notes=f"Return case closed: {notes}" if notes else "Return case successfully closed.",
            )

        return Response(
            {
                "message": f"Return #{ret.return_number} closed successfully.",
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_200_OK
        )


class SellerReturnIntakeView(APIView):
    """
    POST /api/workforce/seller-hub/returns/intake/ – Idempotent return intake contract for customer marketplace
    Guarantees idempotency on source_return_id:
    - If a return with the same source_return_id already exists, returns the existing SellerReturn record with created=False and HTTP 200.
    - If new, atomically creates the SellerReturn and line item records with created=True and HTTP 201.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SellerReturnIntakeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        source_return_id = serializer.validated_data["source_return_id"].strip()
        source_order_id = serializer.validated_data["source_order_id"].strip()
        reason = serializer.validated_data.get("reason", "DAMAGED")
        customer_notes = serializer.validated_data.get("customer_notes", "")
        evidence_urls = serializer.validated_data.get("evidence_urls", [])
        items_data = serializer.validated_data.get("items", [])

        with transaction.atomic():
            # Idempotency check: return existing record if already intaken
            existing = SellerReturn.objects.filter(source_return_id=source_return_id).first()
            if existing:
                return Response(
                    {
                        "message": f"Return case with source reference '{source_return_id}' already exists.",
                        "created": False,
                        "return": SellerReturnDetailSerializer(existing).data,
                    },
                    status=status.HTTP_200_OK
                )

            # Find canonical SellerOrder
            order = SellerOrder.objects.filter(source_order_id=source_order_id).first()
            if not order:
                return Response(
                    {"error": f"Associated SellerOrder with source reference '{source_order_id}' not found."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Generate return reference
            last_ret = SellerReturn.objects.filter(company=order.company).order_by("-id").first()
            next_num = (last_ret.id + 1) if last_ret else 1
            return_number = f"RET-{timezone.now().year}-{next_num:04d}"

            ret = SellerReturn.objects.create(
                order=order,
                company=order.company,
                source_return_id=source_return_id,
                return_number=return_number,
                customer_name=order.customer_name,
                customer_phone=order.customer_phone,
                customer_address=order.delivery_address,
                reason=reason,
                customer_notes=customer_notes,
                evidence_urls=evidence_urls,
                status=SellerReturn.Status.REQUESTED,
            )

            # Create line items
            for it_data in items_data:
                order_item_id = it_data.get("order_item_id")
                sku = it_data.get("sku", "")
                returned_qty_raw = it_data.get("returned_quantity", "1.000")

                try:
                    returned_qty = Decimal(str(returned_qty_raw))
                except (InvalidOperation, ValueError, TypeError):
                    returned_qty = Decimal("1.000")

                order_item = None
                product = None

                if order_item_id:
                    order_item = order.items.filter(pk=order_item_id).first()
                if not order_item and sku:
                    order_item = order.items.filter(sku=sku).first()

                if order_item:
                    product = order_item.product
                    prod_title = order_item.product_title
                    prod_sku = order_item.sku
                    prod_unit = order_item.unit
                    prod_pack = order_item.pack_size
                    batch = order_item.batch
                else:
                    product = SellerProduct.objects.filter(company=order.company, sku=sku).first()
                    prod_title = product.title if product else (it_data.get("product_title") or sku)
                    prod_sku = sku
                    prod_unit = product.unit if product else ""
                    prod_pack = product.pack_size if product else ""
                    batch = None

                if product:
                    SellerReturnItem.objects.create(
                        return_case=ret,
                        order_item=order_item,
                        product=product,
                        product_title=prod_title,
                        sku=prod_sku,
                        unit=prod_unit,
                        pack_size=prod_pack,
                        returned_quantity=returned_qty,
                        batch=batch,
                    )

            # Initial Audit Log
            SellerReturnAuditLog.objects.create(
                return_case=ret,
                action="REQUEST_INTAKE",
                from_status="",
                to_status=SellerReturn.Status.REQUESTED,
                actor=request.user,
                notes=f"Customer return intake received for Order #{order.order_number} (Source Ret ID: {source_return_id}).",
            )

        return Response(
            {
                "message": f"Return #{ret.return_number} intaken successfully.",
                "created": True,
                "return": SellerReturnDetailSerializer(ret).data,
            },
            status=status.HTTP_201_CREATED
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SELLER HUB CLAIMS & DISPUTES MANAGEMENT VIEWS (Phase 6)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerClaimListView(APIView):
    """
    GET /api/workforce/seller-hub/claims/ – List claims with status tabs, search & filters
    POST /api/workforce/seller-hub/claims/ – Create an internal operational dispute / claim
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        qs = SellerClaim.objects.select_related("company", "order", "return_case").all()

        if not is_super:
            if company_id:
                qs = qs.filter(company_id=company_id)
            else:
                return Response([], status=status.HTTP_200_OK)
        else:
            filter_company = request.query_params.get("company_id")
            if filter_company:
                qs = qs.filter(company_id=filter_company)

        status_param = request.query_params.get("status", "ALL").upper()
        if status_param == "OPEN":
            qs = qs.filter(status=SellerClaim.Status.OPEN)
        elif status_param == "NEEDS_RESPONSE":
            qs = qs.filter(status=SellerClaim.Status.SELLER_RESPONSE_REQUIRED)
        elif status_param == "UNDER_REVIEW":
            qs = qs.filter(status=SellerClaim.Status.UNDER_REVIEW)
        elif status_param == "ESCALATED":
            qs = qs.filter(status=SellerClaim.Status.ESCALATED)
        elif status_param == "APPROVED":
            qs = qs.filter(status=SellerClaim.Status.APPROVED)
        elif status_param == "REJECTED":
            qs = qs.filter(status=SellerClaim.Status.REJECTED)
        elif status_param == "SETTLED":
            qs = qs.filter(status=SellerClaim.Status.SETTLED)
        elif status_param == "CLOSED":
            qs = qs.filter(status=SellerClaim.Status.CLOSED)

        claim_type_param = request.query_params.get("claim_type")
        if claim_type_param:
            qs = qs.filter(claim_type=claim_type_param)

        order_id = request.query_params.get("order_id")
        if order_id:
            qs = qs.filter(order_id=order_id)

        return_id = request.query_params.get("return_id")
        if return_id:
            qs = qs.filter(return_case_id=return_id)

        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                models.Q(claim_number__icontains=search)
                | models.Q(source_claim_id__icontains=search)
                | models.Q(order__order_number__icontains=search)
                | models.Q(return_case__return_number__icontains=search)
                | models.Q(customer_name__icontains=search)
                | models.Q(description__icontains=search)
            )

        serializer = SellerClaimListSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        serializer = SellerClaimCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        order_id = data.get("order_id")
        return_id = data.get("return_id")

        order = None
        if order_id:
            order = SellerOrder.objects.filter(id=order_id).first()
            if not order:
                return Response({"error": f"Order #{order_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            if not is_super and company_id and order.company_id != company_id:
                return Response({"error": "Unauthorized order access."}, status=status.HTTP_403_FORBIDDEN)

        return_case = None
        if return_id:
            return_case = SellerReturn.objects.filter(id=return_id).first()
            if not return_case:
                return Response({"error": f"Return #{return_id} not found."}, status=status.HTTP_404_NOT_FOUND)
            if not is_super and company_id and return_case.company_id != company_id:
                return Response({"error": "Unauthorized return access."}, status=status.HTTP_403_FORBIDDEN)

        # Resolve Company
        target_company = None
        if order:
            target_company = order.company
        elif return_case:
            target_company = return_case.company
        elif company_id:
            target_company = Company.objects.filter(id=company_id).first()

        if not target_company:
            return Response({"error": "Target seller company could not be resolved."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Generate sequential claim number
            year = timezone.now().year
            seq_count = SellerClaim.objects.filter(claim_number__startswith=f"CLM-{year}-").count() + 1
            claim_number = f"CLM-{year}-{seq_count:04d}"
            while SellerClaim.objects.filter(claim_number=claim_number).exists():
                seq_count += 1
                claim_number = f"CLM-{year}-{seq_count:04d}"

            source_claim_id = f"INT-CLM-{uuid.uuid4().hex[:12].upper()}"

            claim = SellerClaim.objects.create(
                source_claim_id=source_claim_id,
                claim_number=claim_number,
                company=target_company,
                order=order,
                return_case=return_case,
                claim_type=data["claim_type"],
                description=data["description"],
                claimed_amount=data.get("claimed_amount") or Decimal("0.00"),
                evidence_urls=data.get("evidence_urls", []),
                customer_name=data.get("customer_name") or (order.customer_name if order else ""),
                customer_phone=data.get("customer_phone") or (order.customer_phone if order else ""),
                status=SellerClaim.Status.OPEN,
                created_by=user,
            )

            SellerClaimAuditLog.objects.create(
                claim=claim,
                from_status="",
                to_status=SellerClaim.Status.OPEN,
                action="CLAIM_CREATED",
                actor=user,
                notes=f"Internal dispute ticket #{claim_number} created for {target_company.company_name}.",
            )

        return Response(
            {
                "message": f"Claim #{claim.claim_number} created successfully.",
                "claim": SellerClaimDetailSerializer(claim).data,
            },
            status=status.HTTP_201_CREATED
        )


class SellerClaimDetailView(APIView):
    """
    GET /api/workforce/seller-hub/claims/<id>/ – View full claim details, evidence, & audit history
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        claim = SellerClaim.objects.select_related(
            "company", "order", "return_case", "seller_responded_by", "admin_decided_by", "created_by"
        ).prefetch_related("audit_logs").filter(pk=pk).first()

        if not claim:
            return Response({"error": "Claim not found."}, status=status.HTTP_404_NOT_FOUND)

        if not is_super and company_id and claim.company_id != company_id:
            return Response({"error": "Claim not found or unauthorized."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SellerClaimDetailSerializer(claim)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SellerClaimRespondView(APIView):
    """
    POST /api/workforce/seller-hub/claims/<id>/respond/ – Seller submits response & evidence
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        with transaction.atomic():
            claim = SellerClaim.objects.select_for_update().filter(pk=pk).first()
            if not claim:
                return Response({"error": "Claim not found."}, status=status.HTTP_404_NOT_FOUND)

            if not is_super and company_id and claim.company_id != company_id:
                return Response({"error": "Unauthorized claim access."}, status=status.HTTP_404_NOT_FOUND)

            if claim.status in [SellerClaim.Status.CLOSED, SellerClaim.Status.SETTLED]:
                return Response({"error": f"Cannot respond to a {claim.status} claim."}, status=status.HTTP_400_BAD_REQUEST)

            serializer = SellerClaimRespondSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            response_text = serializer.validated_data["seller_response"]
            new_evidence = serializer.validated_data.get("evidence_urls", [])

            prev_status = claim.status
            claim.seller_response = response_text
            claim.seller_responded_at = timezone.now()
            claim.seller_responded_by = user

            # Append evidence
            combined_evidence = list(claim.evidence_urls or [])
            for url in new_evidence:
                if url not in combined_evidence:
                    combined_evidence.append(url)
            claim.evidence_urls = combined_evidence

            # Transition from SELLER_RESPONSE_REQUIRED to UNDER_REVIEW
            if claim.status == SellerClaim.Status.SELLER_RESPONSE_REQUIRED:
                claim.status = SellerClaim.Status.UNDER_REVIEW

            claim.save()

            SellerClaimAuditLog.objects.create(
                claim=claim,
                from_status=prev_status,
                to_status=claim.status,
                action="SELLER_RESPONSE_SUBMITTED",
                actor=user,
                notes=response_text,
            )

        return Response(
            {
                "message": "Response submitted successfully.",
                "claim": SellerClaimDetailSerializer(claim).data,
            },
            status=status.HTTP_200_OK
        )


class SellerClaimEscalateView(APIView):
    """
    POST /api/workforce/seller-hub/claims/<id>/escalate/ – Escalate dispute to Platform Admin
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        with transaction.atomic():
            claim = SellerClaim.objects.select_for_update().filter(pk=pk).first()
            if not claim:
                return Response({"error": "Claim not found."}, status=status.HTTP_404_NOT_FOUND)

            if not is_super and company_id and claim.company_id != company_id:
                return Response({"error": "Unauthorized claim access."}, status=status.HTTP_404_NOT_FOUND)

            if not claim.can_transition_to(SellerClaim.Status.ESCALATED):
                return Response(
                    {"error": f"Cannot escalate claim in status '{claim.status}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            notes = request.data.get("notes", "Escalated to Platform Admin for dispute arbitration.")
            prev_status = claim.status
            claim.status = SellerClaim.Status.ESCALATED
            claim.save(update_fields=["status", "updated_at"])

            SellerClaimAuditLog.objects.create(
                claim=claim,
                from_status=prev_status,
                to_status=claim.status,
                action="ESCALATED_TO_ADMIN",
                actor=user,
                notes=notes,
            )

        return Response(
            {
                "message": "Claim escalated to Platform Admin.",
                "claim": SellerClaimDetailSerializer(claim).data,
            },
            status=status.HTTP_200_OK
        )


class SellerClaimAdminDecisionView(APIView):
    """
    POST /api/workforce/seller-hub/claims/<id>/admin-decision/ – Admin review decision with mandatory reason
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        if not is_super:
            return Response(
                {"error": "Only platform administrators can perform claim arbitration decisions."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = SellerClaimAdminDecisionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        decision = serializer.validated_data["decision"]
        reason = serializer.validated_data["reason"]

        target_status_map = {
            "REQUEST_SELLER_RESPONSE": SellerClaim.Status.SELLER_RESPONSE_REQUIRED,
            "APPROVE": SellerClaim.Status.APPROVED,
            "REJECT": SellerClaim.Status.REJECTED,
            "SETTLE": SellerClaim.Status.SETTLED,
            "CLOSE": SellerClaim.Status.CLOSED,
        }
        target_status = target_status_map.get(decision)

        with transaction.atomic():
            claim = SellerClaim.objects.select_for_update().filter(pk=pk).first()
            if not claim:
                return Response({"error": "Claim not found."}, status=status.HTTP_404_NOT_FOUND)

            if not claim.can_transition_to(target_status):
                return Response(
                    {"error": f"Invalid state transition from '{claim.status}' to '{target_status}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            prev_status = claim.status
            claim.status = target_status
            claim.admin_decision = decision
            claim.admin_decision_reason = reason
            claim.admin_decided_at = timezone.now()
            claim.admin_decided_by = user

            if decision in ["APPROVE", "REJECT", "SETTLE"]:
                claim.resolved_at = timezone.now()
            elif decision == "CLOSE":
                claim.closed_at = timezone.now()

            claim.save()

            SellerClaimAuditLog.objects.create(
                claim=claim,
                from_status=prev_status,
                to_status=claim.status,
                action=f"ADMIN_{decision}",
                actor=user,
                notes=reason,
            )

        return Response(
            {
                "message": f"Admin decision '{decision}' applied successfully.",
                "claim": SellerClaimDetailSerializer(claim).data,
            },
            status=status.HTTP_200_OK
        )


class SellerClaimCloseView(APIView):
    """
    POST /api/workforce/seller-hub/claims/<id>/close/ – Mark claim case as closed and archived
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        with transaction.atomic():
            claim = SellerClaim.objects.select_for_update().filter(pk=pk).first()
            if not claim:
                return Response({"error": "Claim not found."}, status=status.HTTP_404_NOT_FOUND)

            if not is_super and company_id and claim.company_id != company_id:
                return Response({"error": "Unauthorized claim access."}, status=status.HTTP_404_NOT_FOUND)

            if not claim.can_transition_to(SellerClaim.Status.CLOSED):
                return Response(
                    {"error": f"Cannot close claim currently in '{claim.status}'."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            notes = request.data.get("notes", "Claim case resolved and closed.")
            prev_status = claim.status
            claim.status = SellerClaim.Status.CLOSED
            claim.closed_at = timezone.now()
            claim.save(update_fields=["status", "closed_at", "updated_at"])

            SellerClaimAuditLog.objects.create(
                claim=claim,
                from_status=prev_status,
                to_status=claim.status,
                action="CLOSE_CLAIM",
                actor=user,
                notes=notes,
            )

        return Response(
            {
                "message": "Claim closed successfully.",
                "claim": SellerClaimDetailSerializer(claim).data,
            },
            status=status.HTTP_200_OK
        )


class SellerClaimIntakeView(APIView):
    """
    POST /api/workforce/seller-hub/claims/intake/
    Secure, idempotent customer claim intake API for later Sevo-customer integration.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = SellerClaimIntakeSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        source_claim_id = data["source_claim_id"].strip()

        # Idempotency Check
        existing_claim = SellerClaim.objects.filter(source_claim_id=source_claim_id).first()
        if existing_claim:
            return Response(
                {
                    "message": "Claim already intaken (idempotent response).",
                    "created": False,
                    "claim": SellerClaimDetailSerializer(existing_claim).data,
                },
                status=status.HTTP_200_OK
            )

        # Resolve order
        order = None
        source_order_id = data.get("source_order_id")
        order_id = data.get("order_id")
        if source_order_id:
            order = SellerOrder.objects.filter(source_order_id=source_order_id).first()
        elif order_id:
            order = SellerOrder.objects.filter(id=order_id).first()

        # Resolve return
        return_case = None
        source_return_id = data.get("source_return_id")
        return_id = data.get("return_id")
        if source_return_id:
            return_case = SellerReturn.objects.filter(source_return_id=source_return_id).first()
        elif return_id:
            return_case = SellerReturn.objects.filter(id=return_id).first()

        # Resolve company
        company = None
        if order:
            company = order.company
        elif return_case:
            company = return_case.company
        elif data.get("company_id"):
            company = Company.objects.filter(id=data["company_id"]).first()

        if not company:
            return Response(
                {"error": "Could not determine seller company for this claim."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            year = timezone.now().year
            seq_count = SellerClaim.objects.filter(claim_number__startswith=f"CLM-{year}-").count() + 1
            claim_number = f"CLM-{year}-{seq_count:04d}"
            while SellerClaim.objects.filter(claim_number=claim_number).exists():
                seq_count += 1
                claim_number = f"CLM-{year}-{seq_count:04d}"

            claim = SellerClaim.objects.create(
                source_claim_id=source_claim_id,
                claim_number=claim_number,
                company=company,
                order=order,
                return_case=return_case,
                claim_type=data.get("claim_type", SellerClaim.ClaimType.DAMAGED_ITEM),
                description=data["description"],
                claimed_amount=data.get("claimed_amount") or Decimal("0.00"),
                evidence_urls=data.get("evidence_urls", []),
                customer_name=data.get("customer_name") or (order.customer_name if order else ""),
                customer_phone=data.get("customer_phone") or (order.customer_phone if order else ""),
                status=SellerClaim.Status.OPEN,
                created_by=request.user,
            )

            SellerClaimAuditLog.objects.create(
                claim=claim,
                from_status="",
                to_status=SellerClaim.Status.OPEN,
                action="CUSTOMER_CLAIM_INTAKE",
                actor=request.user,
                notes=f"Customer claim intake received (Source Claim ID: {source_claim_id}).",
            )

        return Response(
            {
                "message": f"Claim #{claim.claim_number} intaken successfully.",
                "created": True,
                "claim": SellerClaimDetailSerializer(claim).data,
            },
            status=status.HTTP_201_CREATED
        )


# ═══════════════════════════════════════════════════════════════════════════════
# 9. SELLER HUB REPORTS, QUALITY CONTROLS & PERFORMANCE (Phase 7)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerReportsSummaryView(APIView):
    """
    GET /api/workforce/seller-hub/reports/summary/
    Comprehensive operational summary KPIs across orders, gross fulfilled value, catalog quality,
    inventory health, return rates, and dispute frequency.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        # Scoping
        order_qs = SellerOrder.objects.all()
        prod_qs = SellerProduct.objects.all()
        inv_qs = SellerInventory.objects.all()
        ret_qs = SellerReturn.objects.all()
        claim_qs = SellerClaim.objects.all()
        batch_qs = SellerInventoryBatch.objects.all()

        if not is_super:
            if company_id:
                order_qs = order_qs.filter(company_id=company_id)
                prod_qs = prod_qs.filter(company_id=company_id)
                inv_qs = inv_qs.filter(company_id=company_id)
                ret_qs = ret_qs.filter(company_id=company_id)
                claim_qs = claim_qs.filter(company_id=company_id)
                batch_qs = batch_qs.filter(inventory__company_id=company_id)
            else:
                return Response(self._empty_summary(), status=status.HTTP_200_OK)
        else:
            filter_company = request.query_params.get("company_id")
            if filter_company:
                order_qs = order_qs.filter(company_id=filter_company)
                prod_qs = prod_qs.filter(company_id=filter_company)
                inv_qs = inv_qs.filter(company_id=filter_company)
                ret_qs = ret_qs.filter(company_id=filter_company)
                claim_qs = claim_qs.filter(company_id=filter_company)
                batch_qs = batch_qs.filter(inventory__company_id=filter_company)

        # Date Filtering
        period = request.query_params.get("period", "30d").lower()
        now = timezone.now()
        start_date = None
        if period == "7d":
            start_date = now - timezone.timedelta(days=7)
        elif period == "30d":
            start_date = now - timezone.timedelta(days=30)
        elif period == "90d":
            start_date = now - timezone.timedelta(days=90)

        if start_date:
            order_qs_period = order_qs.filter(created_at__gte=start_date)
            ret_qs_period = ret_qs.filter(created_at__gte=start_date)
            claim_qs_period = claim_qs.filter(created_at__gte=start_date)
        else:
            order_qs_period = order_qs
            ret_qs_period = ret_qs
            claim_qs_period = claim_qs

        # 1. Order & Fulfilment Performance
        total_orders = order_qs_period.count()
        delivered_orders = order_qs_period.filter(
            status__in=[SellerOrder.Status.DELIVERED, SellerOrder.Status.HANDED_OVER]
        ).count()
        cancelled_orders = order_qs_period.filter(status=SellerOrder.Status.CANCELLED).count()
        in_prep_orders = order_qs_period.filter(
            status__in=[
                SellerOrder.Status.ACCEPTED,
                SellerOrder.Status.PICKING,
                SellerOrder.Status.PACKED,
                SellerOrder.Status.READY_FOR_PICKUP,
            ]
        ).count()
        pending_orders = order_qs_period.filter(status=SellerOrder.Status.NEW).count()

        fulfilled_value_agg = order_qs_period.filter(
            status__in=[SellerOrder.Status.DELIVERED, SellerOrder.Status.HANDED_OVER]
        ).aggregate(total=models.Sum("total_amount"))["total"] or Decimal("0.00")

        active_order_base = total_orders - cancelled_orders
        fulfilment_success_rate = (
            round((delivered_orders / active_order_base) * 100, 1) if active_order_base > 0 else (100.0 if total_orders == 0 else 0.0)
        )
        cancellation_rate = (
            round((cancelled_orders / total_orders) * 100, 1) if total_orders > 0 else 0.0
        )

        # 2. Catalog Quality & Compliance
        total_products = prod_qs.count()
        approved_products = prod_qs.filter(status=SellerProduct.Status.APPROVED).count()
        draft_products = prod_qs.filter(status=SellerProduct.Status.DRAFT).count()
        rejected_products = prod_qs.filter(status=SellerProduct.Status.REJECTED).count()
        changes_requested_products = prod_qs.filter(status=SellerProduct.Status.CHANGES_REQUESTED).count()

        catalog_quality_score = (
            round((approved_products / total_products) * 100, 1) if total_products > 0 else 100.0
        )

        missing_images_count = prod_qs.filter(
            status=SellerProduct.Status.APPROVED,
            images__isnull=True,
        ).distinct().count()

        missing_description_count = prod_qs.filter(
            models.Q(description__exact="") | models.Q(description__isnull=True)
        ).count()

        # 3. Inventory Health & Stock Velocity
        total_inventory_skus = inv_qs.count()
        in_stock_skus = inv_qs.filter(on_hand_qty__gt=models.F("low_stock_threshold")).count()
        low_stock_skus = inv_qs.filter(
            on_hand_qty__gt=Decimal("0.000"),
            on_hand_qty__lte=models.F("low_stock_threshold")
        ).count()
        out_of_stock_skus = inv_qs.filter(on_hand_qty__lte=Decimal("0.000")).count()

        inventory_health_index = (
            round((in_stock_skus / total_inventory_skus) * 100, 1) if total_inventory_skus > 0 else 100.0
        )

        today = now.date()
        thirty_days = today + timezone.timedelta(days=30)
        expiring_soon_count = batch_qs.filter(
            current_quantity__gt=Decimal("0.000"),
            expiry_date__isnull=False,
            expiry_date__lte=thirty_days,
            expiry_date__gte=today,
        ).values("inventory_id").distinct().count()

        total_inv_val = Decimal("0.00")
        for item in inv_qs.select_related("product"):
            if item.product and item.on_hand_qty > 0:
                price = getattr(item.product, "selling_price", Decimal("0.00")) or Decimal("0.00")
                total_inv_val += item.on_hand_qty * price

        # 4. Returns & QC Quality
        total_returns = ret_qs_period.count()
        return_rate = (
            round((total_returns / delivered_orders) * 100, 1) if delivered_orders > 0 else 0.0
        )
        qc_passed_restocked = ret_qs_period.filter(status=SellerReturn.Status.RESTOCKED).count()
        qc_failed_scrapped = ret_qs_period.filter(status=SellerReturn.Status.DISCARDED).count()

        # 5. Claims & Dispute Metrics
        total_claims = claim_qs_period.count()
        open_claims = claim_qs_period.filter(
            status__in=[
                SellerClaim.Status.OPEN,
                SellerClaim.Status.UNDER_REVIEW,
                SellerClaim.Status.SELLER_RESPONSE_REQUIRED,
                SellerClaim.Status.ESCALATED,
            ]
        ).count()
        escalated_claims = claim_qs_period.filter(status=SellerClaim.Status.ESCALATED).count()
        resolved_claims = claim_qs_period.filter(
            status__in=[
                SellerClaim.Status.APPROVED,
                SellerClaim.Status.REJECTED,
                SellerClaim.Status.SETTLED,
                SellerClaim.Status.CLOSED,
            ]
        ).count()
        dispute_rate = (
            round((total_claims / total_orders) * 100, 1) if total_orders > 0 else 0.0
        )
        claimed_val_agg = claim_qs_period.aggregate(total=models.Sum("claimed_amount"))["total"] or Decimal("0.00")

        pending_products = prod_qs.filter(
            status__in=[SellerProduct.Status.SUBMITTED, SellerProduct.Status.UNDER_REVIEW]
        ).count()
        total_on_hand_qty = inv_qs.aggregate(total=models.Sum("on_hand_qty"))["total"] or Decimal("0.000")
        claims_requiring_response = claim_qs_period.filter(
            status=SellerClaim.Status.SELLER_RESPONSE_REQUIRED
        ).count()

        return Response(
            {
                "period": period,
                # Fulfilment KPIs
                "total_orders_count": total_orders,
                "delivered_orders_count": delivered_orders,
                "cancelled_orders_count": cancelled_orders,
                "in_prep_orders_count": in_prep_orders,
                "pending_orders_count": pending_orders,
                "fulfilled_order_gross_value": str(round(fulfilled_value_agg, 2)),
                "fulfilment_success_rate": fulfilment_success_rate,
                "cancellation_rate": cancellation_rate,
                # Catalog Quality
                "total_products_count": total_products,
                "approved_products_count": approved_products,
                "pending_products_count": pending_products,
                "draft_products_count": draft_products,
                "rejected_products_count": rejected_products,
                "changes_requested_products_count": changes_requested_products,
                "catalog_quality_score": catalog_quality_score,
                "missing_images_count": missing_images_count,
                "missing_image_products_count": missing_images_count,
                "missing_descriptions_count": missing_description_count,
                "missing_description_products_count": missing_description_count,
                # Inventory Health
                "total_inventory_skus": total_inventory_skus,
                "total_inventory_items_count": total_inventory_skus,
                "in_stock_skus": in_stock_skus,
                "low_stock_skus": low_stock_skus,
                "low_stock_count": low_stock_skus,
                "out_of_stock_skus": out_of_stock_skus,
                "out_of_stock_count": out_of_stock_skus,
                "total_on_hand_quantity": str(round(total_on_hand_qty, 3)),
                "inventory_health_index": inventory_health_index,
                "expiring_batches_count": expiring_soon_count,
                "expiring_soon_batches_count": expiring_soon_count,
                "inventory_valuation": str(round(total_inv_val, 2)),
                "total_inventory_valuation": str(round(total_inv_val, 2)),
                # Returns & QC
                "total_returns_count": total_returns,
                "pending_returns_count": ret_qs_period.filter(status__in=[SellerReturn.Status.REQUESTED, SellerReturn.Status.UNDER_SELLER_REVIEW, SellerReturn.Status.RECEIVED, SellerReturn.Status.QUALITY_CHECK]).count(),
                "return_rate": return_rate,
                "qc_passed_restocked_count": qc_passed_restocked,
                "qc_failed_scrapped_count": qc_failed_scrapped,
                # Claims
                "total_claims_count": total_claims,
                "open_claims_count": open_claims,
                "claims_requiring_response_count": claims_requiring_response,
                "escalated_claims_count": escalated_claims,
                "resolved_claims_count": resolved_claims,
                "dispute_rate": dispute_rate,
                "total_claimed_amount": str(round(claimed_val_agg, 2)),
            },
            status=status.HTTP_200_OK
        )

    def _empty_summary(self):
        return {
            "period": "30d",
            "total_orders_count": 0,
            "delivered_orders_count": 0,
            "cancelled_orders_count": 0,
            "in_prep_orders_count": 0,
            "pending_orders_count": 0,
            "fulfilled_order_gross_value": "0.00",
            "fulfilment_success_rate": 100.0,
            "cancellation_rate": 0.0,
            "total_products_count": 0,
            "approved_products_count": 0,
            "pending_products_count": 0,
            "draft_products_count": 0,
            "rejected_products_count": 0,
            "changes_requested_products_count": 0,
            "catalog_quality_score": 100.0,
            "missing_images_count": 0,
            "missing_image_products_count": 0,
            "missing_descriptions_count": 0,
            "missing_description_products_count": 0,
            "total_inventory_skus": 0,
            "total_inventory_items_count": 0,
            "in_stock_skus": 0,
            "low_stock_skus": 0,
            "low_stock_count": 0,
            "out_of_stock_skus": 0,
            "out_of_stock_count": 0,
            "total_on_hand_quantity": "0.000",
            "inventory_health_index": 100.0,
            "expiring_batches_count": 0,
            "expiring_soon_batches_count": 0,
            "inventory_valuation": "0.00",
            "total_inventory_valuation": "0.00",
            "total_returns_count": 0,
            "pending_returns_count": 0,
            "return_rate": 0.0,
            "qc_passed_restocked_count": 0,
            "qc_failed_scrapped_count": 0,
            "total_claims_count": 0,
            "open_claims_count": 0,
            "claims_requiring_response_count": 0,
            "escalated_claims_count": 0,
            "resolved_claims_count": 0,
            "dispute_rate": 0.0,
            "total_claimed_amount": "0.00",
        }


class SellerReportsPerformanceView(APIView):
    """
    GET /api/workforce/seller-hub/reports/performance/
    Periodic time-series breakdowns for order volumes, inventory movements, returns reasons, and claim types.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        order_qs = SellerOrder.objects.all()
        movement_qs = SellerInventoryMovement.objects.all()
        ret_qs = SellerReturn.objects.all()
        claim_qs = SellerClaim.objects.all()

        if not is_super:
            if company_id:
                order_qs = order_qs.filter(company_id=company_id)
                movement_qs = movement_qs.filter(inventory__company_id=company_id)
                ret_qs = ret_qs.filter(company_id=company_id)
                claim_qs = claim_qs.filter(company_id=company_id)
            else:
                return Response(
                    {"order_trends": [], "inventory_movements": [], "returns_by_reason": [], "claims_by_type": []},
                    status=status.HTTP_200_OK
                )
        else:
            filter_company = request.query_params.get("company_id")
            if filter_company:
                order_qs = order_qs.filter(company_id=filter_company)
                movement_qs = movement_qs.filter(inventory__company_id=filter_company)
                ret_qs = ret_qs.filter(company_id=filter_company)
                claim_qs = claim_qs.filter(company_id=filter_company)

        period = request.query_params.get("period", "30d").lower()
        now = timezone.now()
        days = 30
        if period == "7d":
            days = 7
        elif period == "90d":
            days = 90
        elif period == "all":
            days = 365

        start_date = now - timezone.timedelta(days=days)
        order_qs = order_qs.filter(created_at__gte=start_date)
        movement_qs = movement_qs.filter(created_at__gte=start_date)
        ret_qs = ret_qs.filter(created_at__gte=start_date)
        claim_qs = claim_qs.filter(created_at__gte=start_date)

        # 1. Order Trends (Daily/Weekly)
        order_trends_map = {}
        for d in range(min(days, 30)):
            dt = (now - timezone.timedelta(days=d)).date()
            dt_str = dt.isoformat()
            order_trends_map[dt_str] = {
                "date": dt_str,
                "orders_count": 0,
                "fulfilled_value": Decimal("0.00"),
                "cancelled_count": 0,
            }

        for ord_obj in order_qs:
            d_str = ord_obj.created_at.date().isoformat()
            if d_str in order_trends_map:
                order_trends_map[d_str]["orders_count"] += 1
                if ord_obj.status in [SellerOrder.Status.DELIVERED, SellerOrder.Status.HANDED_OVER]:
                    order_trends_map[d_str]["fulfilled_value"] += ord_obj.total_amount
                elif ord_obj.status == SellerOrder.Status.CANCELLED:
                    order_trends_map[d_str]["cancelled_count"] += 1

        order_trends = sorted(
            [
                {
                    "date": v["date"],
                    "orders_count": v["orders_count"],
                    "fulfilled_value": str(round(v["fulfilled_value"], 2)),
                    "cancelled_count": v["cancelled_count"],
                }
                for v in order_trends_map.values()
            ],
            key=lambda x: x["date"]
        )

        # 2. Inventory Movements Breakdown
        movement_types = [
            ("STOCK_IN", "Stock Receipt"),
            ("RETURN_RESTOCK", "Return Restocked"),
            ("ORDER_RESERVED", "Order Reserved"),
            ("ORDER_FULFILLED", "Order Fulfilled"),
            ("DAMAGE", "Scrap / Damage"),
            ("EXPIRED", "Expired Product"),
            ("AUDIT_CORRECTION", "Audit Adjustment"),
        ]
        movement_breakdown = []
        for mt_key, mt_label in movement_types:
            mt_records = movement_qs.filter(movement_type=mt_key)
            cnt = mt_records.count()
            net_qty = mt_records.aggregate(total=models.Sum("quantity_change"))["total"] or Decimal("0.000")
            movement_breakdown.append({
                "movement_type": mt_key,
                "movement_type_display": mt_label,
                "count": cnt,
                "net_quantity": str(round(net_qty, 3)),
            })

        # 3. Returns by Reason
        returns_by_reason = []
        for r_code, r_label in SellerReturn.Reason.choices:
            cnt = ret_qs.filter(reason=r_code).count()
            returns_by_reason.append({
                "reason": r_code,
                "reason_display": r_label,
                "count": cnt,
            })

        # 4. Claims by Type
        claims_by_type = []
        for c_code, c_label in SellerClaim.ClaimType.choices:
            c_records = claim_qs.filter(claim_type=c_code)
            cnt = c_records.count()
            val = c_records.aggregate(total=models.Sum("claimed_amount"))["total"] or Decimal("0.00")
            claims_by_type.append({
                "claim_type": c_code,
                "claim_type_display": c_label,
                "count": cnt,
                "total_amount": str(round(val, 2)),
            })

        return Response(
            {
                "order_trends": order_trends,
                "inventory_movements": movement_breakdown,
                "returns_by_reason": returns_by_reason,
                "claims_by_type": claims_by_type,
            },
            status=status.HTTP_200_OK
        )


class SellerReportsQualityAuditView(APIView):
    """
    GET /api/workforce/seller-hub/reports/quality-audit/
    Actionable quality controls and compliance checklist highlighting operational risks.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        prod_qs = SellerProduct.objects.all()
        inv_qs = SellerInventory.objects.all()
        batch_qs = SellerInventoryBatch.objects.all()
        order_qs = SellerOrder.objects.all()
        ret_qs = SellerReturn.objects.all()
        claim_qs = SellerClaim.objects.all()

        if not is_super:
            if company_id:
                prod_qs = prod_qs.filter(company_id=company_id)
                inv_qs = inv_qs.filter(company_id=company_id)
                batch_qs = batch_qs.filter(inventory__company_id=company_id)
                order_qs = order_qs.filter(company_id=company_id)
                ret_qs = ret_qs.filter(company_id=company_id)
                claim_qs = claim_qs.filter(company_id=company_id)
            else:
                return Response([], status=status.HTTP_200_OK)
        else:
            filter_company = request.query_params.get("company_id")
            if filter_company:
                prod_qs = prod_qs.filter(company_id=filter_company)
                inv_qs = inv_qs.filter(company_id=filter_company)
                batch_qs = batch_qs.filter(inventory__company_id=filter_company)
                order_qs = order_qs.filter(company_id=filter_company)
                ret_qs = ret_qs.filter(company_id=filter_company)
                claim_qs = claim_qs.filter(company_id=filter_company)

        checklist = []
        now = timezone.now()
        today = now.date()
        thirty_days = today + timezone.timedelta(days=30)
        twenty_four_hours_ago = now - timezone.timedelta(hours=24)
        forty_eight_hours_ago = now - timezone.timedelta(hours=48)

        # 1. Approved items with 0 stock
        zero_stock_items = inv_qs.filter(
            product__status=SellerProduct.Status.APPROVED,
            on_hand_qty__lte=Decimal("0.000")
        ).select_related("product")[:5]
        for item in zero_stock_items:
            checklist.append({
                "audit_type": "OUT_OF_STOCK_APPROVED",
                "severity": "HIGH",
                "title": f"Approved Product Out of Stock: {item.product.title}",
                "entity_ref": f"SKU: {item.product.sku}",
                "description": "Product is listed as approved on catalog but has 0 on-hand inventory.",
                "action_recommended": "Replenish inventory via Stock-In or pause product listing.",
            })

        # 2. Expiring Batches within 30 days
        expiring_batches = batch_qs.filter(
            current_quantity__gt=Decimal("0.000"),
            expiry_date__isnull=False,
            expiry_date__lte=thirty_days,
            expiry_date__gte=today,
        ).select_related("inventory__product")[:5]
        for b in expiring_batches:
            p_title = b.inventory.product.title if b.inventory and b.inventory.product else "Inventory Item"
            checklist.append({
                "audit_type": "BATCH_EXPIRING_SOON",
                "severity": "MEDIUM",
                "title": f"Batch Expiring Soon: {p_title}",
                "entity_ref": f"Batch #{b.batch_number} (Exp: {b.expiry_date})",
                "description": f"{b.current_quantity} unit(s) remaining in batch expiring within 30 days.",
                "action_recommended": "Mark down price with a promotional store coupon or dispose before expiry.",
            })

        # 3. Missing Images on Approved Products
        missing_img_prods = prod_qs.filter(
            status=SellerProduct.Status.APPROVED,
            images__isnull=True,
        ).distinct()[:5]
        for p in missing_img_prods:
            checklist.append({
                "audit_type": "MISSING_PRODUCT_IMAGE",
                "severity": "MEDIUM",
                "title": f"Missing Photographic Image: {p.title}",
                "entity_ref": f"SKU: {p.sku}",
                "description": "Active product has no high-resolution pack photo attached.",
                "action_recommended": "Upload product pack image in Catalog Uploads.",
            })

        # 4. Stale In-Prep Orders (>24h)
        stale_orders = order_qs.filter(
            status__in=[SellerOrder.Status.ACCEPTED, SellerOrder.Status.PICKING],
            created_at__lte=twenty_four_hours_ago
        )[:5]
        for ord_obj in stale_orders:
            checklist.append({
                "audit_type": "STALE_ORDER_FULFILMENT",
                "severity": "HIGH",
                "title": f"Delayed Order Fulfilment: Order #{ord_obj.order_number}",
                "entity_ref": f"Ord #{ord_obj.order_number} ({ord_obj.status})",
                "description": f"Order has been in '{ord_obj.status}' status for over 24 hours without packing completion.",
                "action_recommended": "Complete item picking and pack parcel for courier pickup immediately.",
            })

        # 5. Claims Requiring Response
        pending_resp_claims = claim_qs.filter(
            status=SellerClaim.Status.SELLER_RESPONSE_REQUIRED
        )[:5]
        for clm in pending_resp_claims:
            checklist.append({
                "audit_type": "CLAIM_RESPONSE_REQUIRED",
                "severity": "HIGH",
                "title": f"Seller Statement Required: Claim #{clm.claim_number}",
                "entity_ref": f"Claim #{clm.claim_number}",
                "description": f"Dispute ticket requires merchant response: '{clm.description[:80]}...'",
                "action_recommended": "Submit packing explanation and proof in Claims portal.",
            })

        # 6. Returns Pending Review (>48h)
        pending_review_returns = ret_qs.filter(
            status__in=[SellerReturn.Status.REQUESTED, SellerReturn.Status.UNDER_SELLER_REVIEW],
            created_at__lte=forty_eight_hours_ago
        )[:5]
        for ret_obj in pending_review_returns:
            checklist.append({
                "audit_type": "RETURN_REVIEW_OVERDUE",
                "severity": "MEDIUM",
                "title": f"Return Review Overdue: Return #{ret_obj.return_number}",
                "entity_ref": f"Return #{ret_obj.return_number}",
                "description": "Customer return case has been awaiting merchant review decision for over 48 hours.",
                "action_recommended": "Review photo evidence and approve return pickup or reject with reason.",
            })

        return Response({
            "total_issues_count": len(checklist),
            "missing_images_count": len([x for x in checklist if x["audit_type"] == "MISSING_PRODUCT_IMAGE"]),
            "expiring_batches_count": len([x for x in checklist if x["audit_type"] == "BATCH_EXPIRING_SOON"]),
            "claims_requiring_response_count": len([x for x in checklist if x["audit_type"] == "CLAIM_RESPONSE_REQUIRED"]),
            "out_of_stock_approved_count": len([x for x in checklist if x["audit_type"] == "OUT_OF_STOCK_APPROVED"]),
            "returns_pending_qc_count": len([x for x in checklist if x["audit_type"] in ("RETURN_REVIEW_OVERDUE", "RETURN_PENDING_QC")]),
            "checklist": checklist,
            "items": checklist,
        }, status=status.HTTP_200_OK)


class SellerReportsExportCSVView(APIView):
    """
    GET /api/workforce/seller-hub/reports/export-csv/?type=(orders|inventory|returns|claims|quality)
    Generates real-time downloadable CSV reports.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        is_super = getattr(user, "is_superuser", False) or is_admin_role(user)
        company_id = _resolve_user_company_id(user)

        report_type = request.query_params.get("type") or request.query_params.get("report_type", "orders")
        report_type = report_type.lower().strip()
        now_str = timezone.now().strftime("%Y%m%d_%H%M%S")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="sevo_seller_{report_type}_report_{now_str}.csv"'

        writer = csv.writer(response)

        if report_type == "orders":
            qs = SellerOrder.objects.all()
            if not is_super and company_id:
                qs = qs.filter(company_id=company_id)
            elif is_super and (c_id := request.query_params.get("company_id")):
                qs = qs.filter(company_id=c_id)

            writer.writerow([
                "Order Number",
                "Source Order ID",
                "Company",
                "Customer Name",
                "Customer Phone",
                "Delivery Address",
                "Fulfilment Type",
                "Payment Method",
                "Total Amount (INR)",
                "Status",
                "Created At",
                "Delivered At",
            ])
            for ord_obj in qs.select_related("company"):
                writer.writerow([
                    ord_obj.order_number,
                    ord_obj.source_order_id,
                    getattr(ord_obj.company, "company_name", ""),
                    ord_obj.customer_name,
                    ord_obj.customer_phone,
                    ord_obj.delivery_address,
                    ord_obj.fulfillment_type,
                    ord_obj.payment_method,
                    str(ord_obj.total_amount),
                    ord_obj.status,
                    ord_obj.created_at.isoformat() if ord_obj.created_at else "",
                    ord_obj.delivered_at.isoformat() if ord_obj.delivered_at else "",
                ])

        elif report_type == "inventory":
            qs = SellerInventory.objects.all()
            if not is_super and company_id:
                qs = qs.filter(company_id=company_id)
            elif is_super and (c_id := request.query_params.get("company_id")):
                qs = qs.filter(company_id=c_id)

            writer.writerow([
                "SKU",
                "Product Title",
                "Company",
                "Category",
                "On Hand Qty",
                "Reserved Qty",
                "Low Stock Threshold",
                "Selling Price (INR)",
                "Total Valuation (INR)",
                "Status",
            ])
            for inv in qs.select_related("product__category", "company"):
                p = inv.product
                price = getattr(p, "selling_price", Decimal("0.00")) if p else Decimal("0.00")
                val = inv.on_hand_qty * price if inv.on_hand_qty > 0 else Decimal("0.00")
                writer.writerow([
                    p.sku if p else "",
                    p.title if p else "",
                    getattr(inv.company, "company_name", ""),
                    p.category.name if p and p.category else "",
                    str(inv.on_hand_qty),
                    str(inv.reserved_qty),
                    str(inv.low_stock_threshold),
                    str(price),
                    str(round(val, 2)),
                    "IN_STOCK" if inv.on_hand_qty > inv.low_stock_threshold else ("LOW_STOCK" if inv.on_hand_qty > 0 else "OUT_OF_STOCK"),
                ])

        elif report_type == "returns":
            qs = SellerReturn.objects.all()
            if not is_super and company_id:
                qs = qs.filter(company_id=company_id)
            elif is_super and (c_id := request.query_params.get("company_id")):
                qs = qs.filter(company_id=c_id)

            writer.writerow([
                "Return Number",
                "Order Number",
                "Company",
                "Customer Name",
                "Reason",
                "QC Status",
                "Restock Decision",
                "Status",
                "Created At",
                "Closed At",
            ])
            for ret in qs.select_related("order", "company"):
                writer.writerow([
                    ret.return_number,
                    ret.order.order_number if ret.order else "",
                    getattr(ret.company, "company_name", ""),
                    ret.customer_name,
                    ret.reason,
                    ret.quality_check_status,
                    ret.restock_decision,
                    ret.status,
                    ret.created_at.isoformat() if ret.created_at else "",
                    ret.closed_at.isoformat() if ret.closed_at else "",
                ])

        elif report_type == "claims":
            qs = SellerClaim.objects.all()
            if not is_super and company_id:
                qs = qs.filter(company_id=company_id)
            elif is_super and (c_id := request.query_params.get("company_id")):
                qs = qs.filter(company_id=c_id)

            writer.writerow([
                "Claim Number",
                "Order Number",
                "Return Number",
                "Company",
                "Claim Type",
                "Claimed Amount (INR)",
                "Status",
                "Seller Response",
                "Admin Decision",
                "Created At",
                "Resolved At",
            ])
            for clm in qs.select_related("order", "return_case", "company"):
                writer.writerow([
                    clm.claim_number,
                    clm.order.order_number if clm.order else "",
                    clm.return_case.return_number if clm.return_case else "",
                    getattr(clm.company, "company_name", ""),
                    clm.claim_type,
                    str(clm.claimed_amount),
                    clm.status,
                    clm.seller_response,
                    clm.admin_decision,
                    clm.created_at.isoformat() if clm.created_at else "",
                    clm.resolved_at.isoformat() if clm.resolved_at else "",
                ])

        elif report_type == "quality":
            writer.writerow([
                "Audit Type",
                "Severity",
                "Title",
                "Entity Reference",
                "Description",
                "Action Recommended",
            ])
            # Run quick audit
            audit_view = SellerReportsQualityAuditView()
            audit_resp = audit_view.get(request)
            items = audit_resp.data.get("checklist", audit_resp.data) if isinstance(audit_resp.data, dict) else audit_resp.data
            for item in items:
                writer.writerow([
                    item.get("audit_type", ""),
                    item.get("severity", ""),
                    item.get("title", ""),
                    item.get("entity_ref", ""),
                    item.get("description", ""),
                    item.get("action_recommended", ""),
                ])

        else:
            writer.writerow(["Invalid report type requested."])

        return response







