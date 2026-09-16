from django.urls import path
from inventory.views import (
    VendorStockListView,
    VendorStockRestockView,
    VendorStockMarkOutOfStockView,
    VendorStockAdjustView,
    VendorStockUpdateDetailsView,
    VendorStockHistoryView,
)

urlpatterns = [
    path("stock/", VendorStockListView.as_view(), name="vendor-stock-list"),
    path("stock/<int:product_id>/restock/", VendorStockRestockView.as_view(), name="vendor-stock-restock"),
    path("stock/<int:product_id>/mark-out-of-stock/", VendorStockMarkOutOfStockView.as_view(), name="vendor-stock-mark-out"),
    path("stock/<int:product_id>/adjust/", VendorStockAdjustView.as_view(), name="vendor-stock-adjust"),
    path("stock/<int:product_id>/update-details/", VendorStockUpdateDetailsView.as_view(), name="vendor-stock-update-details"),
    path("stock/<int:product_id>/history/", VendorStockHistoryView.as_view(), name="vendor-stock-history"),
]
