"""
workforce-app/backend/service_requests/vendor_urls.py

URL routes for Vendor AC Estimation & Quotation Builder module.
Mounted at /api/vendor/ and /api/workforce/vendor/.
"""
from django.urls import path
from .vendor_views import (
    VendorEstimationListView,
    VendorEstimationDetailView,
    VendorEstimationConfirmView,
    VendorEstimationAssignTechnicianView,
    VendorEstimationStartJourneyView,
    VendorEstimationArrivedView,
    VendorEstimationVerifyOtpView,
    VendorEstimationFindingsView,
    VendorEstimationPhotosView,
    VendorEstimationInspectionCompleteView,
    VendorEstimationQuotationView,
    VendorEstimationQuotationSendView,
    VendorEstimationQuotationReviseView,
    VendorEstimationFeeCollectView,
    VendorEstimationFeeWaiveView,
    VendorEstimationCustomerDecideView,
    VendorEstimationInvoiceView,
    VendorTechniciansListView,
)

urlpatterns = [
    # Estimation Leads Listing & Detail
    path("estimations/", VendorEstimationListView.as_view(), name="vendor-estimation-list"),
    path("estimations/<int:pk>/", VendorEstimationDetailView.as_view(), name="vendor-estimation-detail"),

    # Lifecycle Action Steps
    path("estimations/<int:pk>/confirm/", VendorEstimationConfirmView.as_view(), name="vendor-estimation-confirm"),
    path("estimations/<int:pk>/assign-technician/", VendorEstimationAssignTechnicianView.as_view(), name="vendor-estimation-assign-technician"),
    path("estimations/<int:pk>/start-journey/", VendorEstimationStartJourneyView.as_view(), name="vendor-estimation-start-journey"),
    path("estimations/<int:pk>/arrived/", VendorEstimationArrivedView.as_view(), name="vendor-estimation-arrived"),
    path("estimations/<int:pk>/verify-otp/", VendorEstimationVerifyOtpView.as_view(), name="vendor-estimation-verify-otp"),

    # Inspection Findings & Photos
    path("estimations/<int:pk>/inspection/findings/", VendorEstimationFindingsView.as_view(), name="vendor-estimation-findings"),
    path("estimations/<int:pk>/inspection/photos/", VendorEstimationPhotosView.as_view(), name="vendor-estimation-photos"),
    path("estimations/<int:pk>/inspection/complete/", VendorEstimationInspectionCompleteView.as_view(), name="vendor-estimation-inspection-complete"),

    # Quotation Builder, Send & Revise
    path("estimations/<int:pk>/quotation/", VendorEstimationQuotationView.as_view(), name="vendor-estimation-quotation-create"),
    path("estimations/<int:pk>/quotation/<int:quote_id>/send/", VendorEstimationQuotationSendView.as_view(), name="vendor-estimation-quotation-send"),
    path("estimations/<int:pk>/quotation/<int:quote_id>/revise/", VendorEstimationQuotationReviseView.as_view(), name="vendor-estimation-quotation-revise"),

    # Visit Fee Collection & Waiver
    path("estimations/<int:pk>/fee/collect/", VendorEstimationFeeCollectView.as_view(), name="vendor-estimation-fee-collect"),
    path("estimations/<int:pk>/fee/waive/", VendorEstimationFeeWaiveView.as_view(), name="vendor-estimation-fee-waive"),

    # Customer Decision Simulator / Receiver
    path("estimations/<int:pk>/customer-decide/", VendorEstimationCustomerDecideView.as_view(), name="vendor-estimation-customer-decide"),

    # Authoritative Invoice Data & Download for Customer
    path("estimations/<int:pk>/invoice/", VendorEstimationInvoiceView.as_view(), name="vendor-estimation-invoice"),
    path("estimations/<int:pk>/invoice/pdf/", VendorEstimationInvoiceView.as_view(), name="vendor-estimation-invoice-pdf"),

    # Technicians Directory
    path("technicians/", VendorTechniciansListView.as_view(), name="vendor-technicians-list"),
]
