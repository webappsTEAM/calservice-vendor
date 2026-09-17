"""
vendor/backend/inventory/views.py

VENDOR_STOCK_MANAGEMENT_IMPLEMENTATION_PLAN.md Phase 1. Every write here is
scoped to request.company (resolved by companies.middleware.CompanyMiddleware
from the vendor's own JWT/cookie, same as everywhere else in this backend)
and rejects touching a product another company already claimed --
see services.assert_owns_product / NotYourProductError.
"""
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsVendorAdmin
from service_requests.models import Package
from inventory.models import InventoryItem
from inventory import services as stock_services
from inventory.selectors import get_vendor_stock_status, get_daily_stock_history
from inventory.serializers import (
    VendorStockListSerializer,
    RestockActionSerializer,
    AdjustActionSerializer,
    UpdateDetailsSerializer,
)
from inventory.utils.unit_conversion import to_grams


def _company_or_403(request):
    company = getattr(request, "company", None) or getattr(request.user, "company", None)
    if not company:
        return None
    return company


class VendorStockListView(APIView):
    """
    GET /api/vendor/stock/

    Lists every vegetable/produce Package (not just ones this vendor already
    owns) -- matches the Customer app's current admin list behavior, which
    is unfiltered by company today. Each row's `is_claimed`/`is_mine` tells
    the frontend whether this vendor can act on it: unclaimed products can be
    restocked (which claims them for this vendor); products another vendor
    already claimed show read-only.
    """
    permission_classes = [IsAuthenticated, IsVendorAdmin]

    def get(self, request):
        company = _company_or_403(request)
        if not company:
            return Response({"success": False, "message": "No company associated with this account."}, status=status.HTTP_403_FORBIDDEN)

        qs = Package.objects.filter(
            service__slug="vegetables"
        ).select_related("stock_item", "service").order_by("sort_order", "name")

        serializer = VendorStockListSerializer(qs, many=True, context={"company": company})
        return Response({"success": True, "data": serializer.data, "count": len(serializer.data)})


class VendorStockRestockView(APIView):
    """POST /api/vendor/stock/<product_id>/restock/  Body: { "quantity": 10, "unit": "kg" }"""
    permission_classes = [IsAuthenticated, IsVendorAdmin]

    def post(self, request, product_id):
        company = _company_or_403(request)
        if not company:
            return Response({"success": False, "message": "No company associated with this account."}, status=status.HTTP_403_FORBIDDEN)

        product = get_object_or_404(Package.objects.select_related("stock_item", "service"), id=product_id)
        serializer = RestockActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "message": "Validation error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stock_services.add_stock(
                product=product,
                quantity=serializer.validated_data["quantity"],
                unit=serializer.validated_data["unit"],
                company=company,
                entered_by_user=request.user,
            )
        except stock_services.NotYourProductError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        product.refresh_from_db()
        return Response({
            "success": True,
            "message": f"Successfully restocked {product.name}.",
            "data": get_vendor_stock_status(product),
        })


class VendorStockMarkOutOfStockView(APIView):
    """POST /api/vendor/stock/<product_id>/mark-out-of-stock/"""
    permission_classes = [IsAuthenticated, IsVendorAdmin]

    def post(self, request, product_id):
        company = _company_or_403(request)
        if not company:
            return Response({"success": False, "message": "No company associated with this account."}, status=status.HTTP_403_FORBIDDEN)

        product = get_object_or_404(Package.objects.select_related("stock_item", "service"), id=product_id)
        try:
            stock_services.mark_out_of_stock(product=product, company=company, entered_by_user=request.user)
        except stock_services.NotYourProductError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        product.refresh_from_db()
        return Response({
            "success": True,
            "message": f"Marked {product.name} as out of stock.",
            "data": get_vendor_stock_status(product),
        })


class VendorStockAdjustView(APIView):
    """POST /api/vendor/stock/<product_id>/adjust/  Body: { "quantity": 5, "unit": "kg", "reason": "..." }"""
    permission_classes = [IsAuthenticated, IsVendorAdmin]

    def post(self, request, product_id):
        company = _company_or_403(request)
        if not company:
            return Response({"success": False, "message": "No company associated with this account."}, status=status.HTTP_403_FORBIDDEN)

        product = get_object_or_404(Package.objects.select_related("stock_item", "service"), id=product_id)
        serializer = AdjustActionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "message": "Validation error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stock_services.adjust_stock(
                product=product,
                quantity=serializer.validated_data["quantity"],
                unit=serializer.validated_data["unit"],
                reason=serializer.validated_data["reason"],
                company=company,
                entered_by_user=request.user,
            )
        except stock_services.NotYourProductError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        product.refresh_from_db()
        return Response({
            "success": True,
            "message": f"Successfully adjusted stock for {product.name}.",
            "data": get_vendor_stock_status(product),
        })


class VendorStockUpdateDetailsView(APIView):
    """PATCH /api/vendor/stock/<product_id>/update-details/  price, offer_price, reorder/restock levels"""
    permission_classes = [IsAuthenticated, IsVendorAdmin]

    def patch(self, request, product_id):
        company = _company_or_403(request)
        if not company:
            return Response({"success": False, "message": "No company associated with this account."}, status=status.HTTP_403_FORBIDDEN)

        product = get_object_or_404(Package.objects.select_related("stock_item", "service"), id=product_id)
        serializer = UpdateDetailsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"success": False, "message": "Validation error", "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        reorder_grams = None
        if data.get("reorder_level_quantity") is not None:
            reorder_grams = to_grams(data["reorder_level_quantity"], data.get("reorder_level_unit", "kg"), allow_zero=True)
        restock_grams = None
        if data.get("restock_level_quantity") is not None:
            restock_grams = to_grams(data["restock_level_quantity"], data.get("restock_level_unit", "kg"), allow_zero=True)

        try:
            stock_services.update_price_and_levels(
                product=product,
                company=company,
                price=data.get("price"),
                offer_price=data.get("offer_price"),
                reorder_level_grams=reorder_grams,
                restock_level_grams=restock_grams,
                entered_by_user=request.user,
            )
        except stock_services.NotYourProductError as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_403_FORBIDDEN)
        except Exception as exc:
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        product.refresh_from_db()
        return Response({
            "success": True,
            "message": f"Successfully updated {product.name} details.",
            "data": get_vendor_stock_status(product),
        })


class VendorStockHistoryView(APIView):
    """GET /api/vendor/stock/<product_id>/history/?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD"""
    permission_classes = [IsAuthenticated, IsVendorAdmin]

    def get(self, request, product_id):
        product = get_object_or_404(Package.objects.select_related("stock_item"), id=product_id)

        today = timezone.localdate()
        start_date_str = request.GET.get("start_date")
        end_date_str = request.GET.get("end_date")
        try:
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date() if start_date_str else (today - timezone.timedelta(days=7))
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else today
        except ValueError:
            return Response({"success": False, "message": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        history = get_daily_stock_history(product=product, start_date=start_date, end_date=end_date)
        return Response({
            "success": True,
            "product_id": product.id,
            "product_name": product.name,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
            "data": history,
        })
