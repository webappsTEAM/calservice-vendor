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
)
from workforce_api.serializers import (
    SellerHubCategoryAdminSerializer,
    SellerHubCategoryTreeSerializer,
    VendorCouponSerializer,
    SellerProductListSerializer,
    SellerProductDetailSerializer,
    SellerProductCreateUpdateSerializer,
    SellerProductImageSerializer,
    SellerProductAuditLogSerializer,
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
)
from companies.models import Company

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


# ═══════════════════════════════════════════════════════════════════════════════
# 1. SELLER HUB CATEGORIES MANAGEMENT (SellerHubCategory in workforce_seller_hub_category)
# ═══════════════════════════════════════════════════════════════════════════════

class AdminSellerHubCategoryListView(APIView):
    """
    GET  /api/workforce/seller-hub/categories/ – List Seller Hub categories with search, parent filtering & tree mode
    POST /api/workforce/seller-hub/categories/ – Create a new Seller Hub category (Superadmin only)
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
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)

        if not is_super:
            return Response(
                {"error": "Only platform superadministrators can create global catalog categories."},
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
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        if not is_super:
            return Response(
                {"error": "Only platform superadministrators can modify catalog categories."},
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
                data["parent"] = parent_val

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
        is_super = getattr(user, "is_superuser", False) or getattr(user, "is_platform_admin", False)
        if not is_super:
            return Response(
                {"error": "Only platform superadministrators can delete catalog categories."},
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
                cat_obj = leaf_cats_by_slug.get(cat_ident_clean) or leaf_cats_by_id.get(cat_ident_clean)
                if not cat_obj:
                    # Check if it was a parent category
                    parent_check = SellerHubCategory.objects.filter(slug=cat_ident_clean).first() or (SellerHubCategory.objects.filter(id=int(cat_ident_clean)).first() if cat_ident_clean.isdigit() else None)
                    if parent_check:
                        row_errors.append(f"Category '{parent_check.name}' is a parent category with subcategories. Products must be assigned to leaf categories only.")
                    else:
                        row_errors.append(f"Active leaf category '{cat_identifier}' not found.")

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



