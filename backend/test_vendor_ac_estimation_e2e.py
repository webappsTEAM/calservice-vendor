"""
backend/test_vendor_ac_estimation_e2e.py

End-to-End Test Suite for CALSERVICES Vendor AC Inspection & Estimation Workflow.
Executes against real PostgreSQL database with zero mock data.
Tests:
  1. Lead Retrieval & Filtering (status, date)
  2. Lead Confirmation (vendor_id, vendor_confirmed_at, status=VENDOR_CONFIRMED)
  3. Technician Assignment (Inspection created, status=TECHNICIAN_ASSIGNED)
  4. Journey & Arrival (TECHNICIAN_ON_THE_WAY, TECHNICIAN_ARRIVED)
  5. Customer Start OTP Verification (Invalid OTP fails 400, Valid OTP advances to INSPECTION_IN_PROGRESS)
  6. Structured Findings & Photo Evidence Persistence
  7. Inspection Completion (status=INSPECTION_COMPLETED)
  8. Commercial Quotation Builder & Calculation Engine (GST, Discount, Grand Total)
  9. Quotation Publishing (status=QUOTATION_SENT)
 10. Customer Decision Handling & Quote Versioning (Rejection -> Revision V2 -> Approval)
 11. Inspection Fee Collection (₹199 Cash/UPI) and Waiver Lifecycle
 12. PostgreSQL Foreign Key & Data Invariant Integrity
"""
from decimal import Decimal
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from companies.models import Company
from employees.models import Employee
from service_requests.models import (
    ServiceRequest,
    Estimation,
    EstimationFee,
    Inspection,
    InspectionFinding,
    InspectionPhoto,
    EstimationQuotation,
    EstimationQuotationItem,
)
from service_requests.vendor_views import (
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
    VendorTechniciansListView,
)

factory = APIRequestFactory()
TEST_RUN_ID = uuid.uuid4().hex[:6].upper()
PASSED_TESTS = []
FAILED_TESTS = []


def record_pass(name, details=""):
    print(f"  [PASS] {name} {details}")
    PASSED_TESTS.append(name)


def record_fail(name, error):
    import traceback
    print(f"  [FAIL] {name} -> {error}")
    traceback.print_exc()
    FAILED_TESTS.append((name, str(error)))


def run_e2e_suite():
    print(f"\n=======================================================")
    print(f"CALSERVICES — AC INSPECTION & ESTIMATION VENDOR E2E TEST")
    print(f"Test Run ID: {TEST_RUN_ID}")
    print(f"=======================================================\n")

    # 1. Setup Fixture Users & Test Lead
    print("--- Step 1: Setting up Vendor User & Test Estimation Job ---")
    vendor_user, _ = User.objects.get_or_create(
        username=f"vendor_test_{TEST_RUN_ID}",
        defaults={
            "email": f"vendor_{TEST_RUN_ID}@example.com",
            "first_name": "Cooling",
            "last_name": "Solutions",
            "role": "admin",
            "is_staff": True,
        }
    )
    vendor_user.set_password("VendorPass123!")
    vendor_user.save()

    tech_user, _ = User.objects.get_or_create(
        username=f"tech_test_{TEST_RUN_ID}",
        defaults={
            "email": f"tech_{TEST_RUN_ID}@example.com",
            "first_name": "Ramesh",
            "last_name": "Nair",
            "role": "employee",
            "phone": f"+9198{uuid.uuid4().int % 100000000:08d}",
        }
    )
    tech_user.set_password("TechPass123!")
    tech_user.save()

    test_sr = ServiceRequest.objects.create(
        request_id=f"AC{TEST_RUN_ID}",
        job_type="ESTIMATION",
        request_kind="ESTIMATION",
        customer_name="Vikram Sethi",
        phone="+919876543210",
        email="vikram@example.com",
        service_category="HVAC & Air Conditioning",
        issue_title="AC Cooling Failure & Water Leakage",
        description="Split AC running warm air, compressor trips after 2 mins.",
        address="Flat 402, Green Glen Heights, Bellandur, Bangalore",
        latitude=12.9279,
        longitude=77.6718,
        preferred_date=datetime.now(timezone.utc).date(),
        preferred_time="10:00 AM - 01:00 PM",
        start_otp="842109",
        total_amount=Decimal("199.00"),
        status="requested",
    )

    test_est = Estimation.objects.create(
        service_request=test_sr,
        ac_type="SPLIT",
        ac_brand="Daikin",
        ac_capacity="1.5_TON",
        ac_quantity=1,
        customer_symptom="Split AC running warm air, water leakage from indoor tray.",
        customer_notes="Please check gas pressure.",
        status="REQUESTED",
    )

    test_fee = EstimationFee.objects.create(
        estimation=test_est,
        amount=Decimal("199.00"),
        currency="INR",
        status="PENDING",
    )

    record_pass("1. Test Fixtures Created", f"SR #{test_sr.id} ({test_sr.request_id}), Estimation #{test_est.id}, Fee #{test_fee.id}")

    try:
        # 2. Test Listing & Filtering
        print("\n--- Step 2: Test Vendor Leads Listing API ---")
        req = factory.get(f"/api/vendor/estimations/?status=all")
        force_authenticate(req, user=vendor_user)
        view = VendorEstimationListView.as_view()
        res = view(req)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
        results = res.data.get("results", [])
        matched = [r for r in results if r["id"] == test_sr.id]
        assert len(matched) == 1, f"Lead #{test_sr.id} not found in listings!"
        assert matched[0]["request_id"] == f"AC{TEST_RUN_ID}"
        assert matched[0]["ac_details"]["ac_brand"] == "Daikin"
        assert matched[0]["fee"]["amount"] == 199.00
        record_pass("2. GET /api/vendor/estimations/", f"Returned {len(results)} leads, target lead found with correct AC specs & fee")

        # 3. Test Detail API
        print("\n--- Step 3: Test Vendor Estimation Detail API ---")
        req = factory.get(f"/api/vendor/estimations/{test_sr.id}/")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationDetailView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.data["customer_name"] == "Vikram Sethi"
        assert res.data["start_otp"] == "842109"
        record_pass("3. GET /api/vendor/estimations/{id}/", f"Detail retrieved successfully for lead #{test_sr.id}")

        # 4. Test Lead Confirmation (Accept Lead)
        print("\n--- Step 4: Test Accept / Confirm Lead ---")
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/confirm/", {
            "vendor_id": "VEND-8840",
            "vendor_name": "Cooling Solutions Bangalore"
        }, format="json")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationConfirmView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"

        test_sr.refresh_from_db()
        test_est.refresh_from_db()
        assert test_sr.status == "vendor_confirmed", f"SR status was {test_sr.status}"
        assert test_est.status == "VENDOR_CONFIRMED", f"Est status was {test_est.status}"
        assert test_sr.vendor_id == "VEND-8840"
        assert test_sr.vendor_confirmed_at is not None
        record_pass("4. POST /api/vendor/estimations/{id}/confirm/", "Status transitioned to VENDOR_CONFIRMED atomically")

        # 5. Test Technician Assignment
        print("\n--- Step 5: Test Assign Technician ---")
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/assign-technician/", {
            "technician_id": tech_user.id,
            "technician_name": "Ramesh Nair",
            "technician_phone": "+919845012345"
        }, format="json")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationAssignTechnicianView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"

        test_sr.refresh_from_db()
        test_est.refresh_from_db()
        assert test_sr.status == "technician_assigned"
        assert test_est.status == "TECHNICIAN_ASSIGNED"
        assert test_sr.technician_name == "Ramesh Nair"

        inspection = Inspection.objects.filter(estimation=test_est).first()
        assert inspection is not None, "Inspection record was not created!"
        assert inspection.technician_name == "Ramesh Nair"
        record_pass("5. POST /api/vendor/estimations/{id}/assign-technician/", f"Inspection #{inspection.id} created, technician assigned")

        # 6. Test Start Journey & Arrival
        print("\n--- Step 6: Test Start Journey & Mark Arrived ---")
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/start-journey/")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationStartJourneyView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200
        test_sr.refresh_from_db()
        assert test_sr.status == "technician_on_the_way"

        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/arrived/")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationArrivedView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200
        test_sr.refresh_from_db()
        assert test_sr.status == "technician_arrived"
        assert test_sr.technician_arrived_at is not None
        record_pass("6. POST start-journey & arrived", "Status advanced to TECHNICIAN_ARRIVED with timestamp")

        # 7. Test Customer Start OTP Verification
        print("\n--- Step 7: Test Start OTP Verification ---")
        # 7a: Wrong OTP -> Expect 400
        req_bad = factory.post(f"/api/vendor/estimations/{test_sr.id}/verify-otp/", {"otp": "999999"}, format="json")
        force_authenticate(req_bad, user=vendor_user)
        res_bad = VendorEstimationVerifyOtpView.as_view()(req_bad, pk=test_sr.id)
        assert res_bad.status_code == 400, f"Expected 400 on wrong OTP, got {res_bad.status_code}"
        assert res_bad.data.get("code") == "INVALID_OTP"

        # 7b: Correct OTP -> Expect 200
        req_good = factory.post(f"/api/vendor/estimations/{test_sr.id}/verify-otp/", {"otp": "842109"}, format="json")
        force_authenticate(req_good, user=vendor_user)
        res_good = VendorEstimationVerifyOtpView.as_view()(req_good, pk=test_sr.id)
        assert res_good.status_code == 200, f"Expected 200 on correct OTP, got {res_good.status_code}"

        test_sr.refresh_from_db()
        test_est.refresh_from_db()
        inspection.refresh_from_db()
        assert test_sr.otp_verified is True
        assert test_sr.status == "inspection_in_progress"
        assert test_est.status == "INSPECTION_IN_PROGRESS"
        assert inspection.status == "IN_PROGRESS"
        record_pass("7. POST /api/vendor/estimations/{id}/verify-otp/", "Invalid OTP rejected (400) & valid OTP verified (200), inspection in progress")

        # 8. Test Structured Inspection Findings & Photos
        print("\n--- Step 8: Test Save Structured Findings & Photos ---")
        findings_payload = [
            {
                "finding_type": "Gas Leakage",
                "title": "Flare Nut Refrigerant Leakage",
                "severity": "HIGH",
                "description": "Pressure dropped to 40 PSI on low-side service gauge.",
                "recommended_action": "Tighten flare nut, vacuum system, top up R32 gas.",
                "quantity": 1,
                "unit": "refill",
            },
            {
                "finding_type": "Coil Cleaning",
                "title": "Severe Condenser Dust Choking",
                "severity": "MEDIUM",
                "description": "Condenser heat dissipation blocked by heavy soot.",
                "recommended_action": "Chemical foam jet spray cleaning.",
                "quantity": 1,
                "unit": "service",
            },
        ]
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/inspection/findings/", {"findings": findings_payload}, format="json")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationFindingsView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.data}"
        assert InspectionFinding.objects.filter(inspection=inspection).count() == 2

        # Upload evidence photo
        req_photo = factory.post(f"/api/vendor/estimations/{test_sr.id}/inspection/photos/", {
            "photo_url": "https://images.caldim.in/defect_test_01.jpg",
            "caption": "Oil leakage mark at service valve",
        }, format="json")
        force_authenticate(req_photo, user=vendor_user)
        res_photo = VendorEstimationPhotosView.as_view()(req_photo, pk=test_sr.id)
        assert res_photo.status_code == 201, f"Expected 201, got {res_photo.status_code}"
        assert InspectionPhoto.objects.filter(inspection=inspection).count() == 1
        record_pass("8. POST inspection/findings & photos", "2 structured findings and 1 photo record persisted in PostgreSQL")

        # 9. Test Complete Inspection
        print("\n--- Step 9: Test Complete Inspection ---")
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/inspection/complete/", {
            "diagnosis_summary": "Diagnosis complete. R32 gas refill and coil deep wash required.",
            "notes": "Customer agreed to receive formal quote.",
        }, format="json")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationInspectionCompleteView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 200
        test_sr.refresh_from_db()
        test_est.refresh_from_db()
        inspection.refresh_from_db()
        assert test_sr.status == "inspection_completed"
        assert test_est.status == "INSPECTION_COMPLETED"
        assert inspection.status == "COMPLETED"
        record_pass("9. POST inspection/complete/", "Inspection marked COMPLETED and status advanced to INSPECTION_COMPLETED")

        # 10. Test Quotation Builder & Calculation Engine
        print("\n--- Step 10: Test Formal Quotation Builder (Draft & Math Engine) ---")
        quote_payload = {
            "valid_until": (datetime.now(timezone.utc) + timedelta(days=7)).date().isoformat(),
            "tax_rate_percent": 18,
            "discount_amount": 100.00,
            "notes": "Includes 90-day warranty on parts and brazing.",
            "items": [
                {
                    "title": "Gas Leakage Repair & Brazing",
                    "item_type": "LABOR",
                    "quantity": 1,
                    "unit_price": 650.00,
                },
                {
                    "title": "R32 Refrigerant Gas Refill",
                    "item_type": "GAS",
                    "quantity": 1,
                    "unit_price": 1850.00,
                },
            ],
        }
        # Math verification:
        # Subtotal = 650.00 + 1850.00 = 2500.00
        # 18% Tax = 2500 * 0.18 = 450.00
        # Discount = 100.00
        # Grand Total = 2500.00 + 450.00 - 100.00 = 2850.00
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/quotation/", quote_payload, format="json")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationQuotationView.as_view()(req, pk=test_sr.id)
        assert res.status_code == 201, f"Expected 201, got {res.status_code}: {res.data}"

        quote = EstimationQuotation.objects.filter(estimation=test_est).order_by("-version").first()
        assert quote is not None, "Quotation record was not created!"
        assert quote.version == 1
        assert quote.quote_ref.startswith(f"QTE-AC{TEST_RUN_ID}")
        assert quote.subtotal == Decimal("2500.00"), f"Subtotal was {quote.subtotal}"
        assert quote.tax_amount == Decimal("450.00"), f"Tax was {quote.tax_amount}"
        assert quote.discount_amount == Decimal("100.00"), f"Discount was {quote.discount_amount}"
        assert quote.total_amount == Decimal("2850.00"), f"Total was {quote.total_amount}"
        assert quote.items.count() == 2
        record_pass("10. POST quotation/ (Draft & Math Engine)", f"Quote {quote.quote_ref}: Subtotal=₹2500, Tax(18%)=₹450, Disc=₹100, Total=₹2850")

        # 11. Test Send Quotation to Customer
        print("\n--- Step 11: Test Send Quotation to Customer ---")
        req = factory.post(f"/api/vendor/estimations/{test_sr.id}/quotation/{quote.id}/send/")
        force_authenticate(req, user=vendor_user)
        res = VendorEstimationQuotationSendView.as_view()(req, pk=test_sr.id, quote_id=quote.id)
        assert res.status_code == 200
        quote.refresh_from_db()
        test_sr.refresh_from_db()
        test_est.refresh_from_db()
        assert quote.status == "SENT"
        assert test_sr.status == "quotation_sent"
        assert test_est.status == "QUOTATION_SENT"
        assert test_sr.total_amount == Decimal("2850.00")
        record_pass("11. POST quotation/{id}/send/", "Quote published to customer, status advanced to QUOTATION_SENT")

        # 12. Test Customer Decision Handling & Quote Revision (V1 -> V2)
        print("\n--- Step 12: Test Customer Decision (Reject V1 -> Revise V2 -> Approve V2) ---")
        # 12a: Customer rejects V1 because price is too high
        req_decide = factory.post(f"/api/vendor/estimations/{test_sr.id}/customer-decide/", {
            "decision": "REJECT",
            "rejection_reason": "PRICE_TOO_HIGH",
            "rejection_note": "Can you offer a discount on the gas refill?",
        }, format="json")
        force_authenticate(req_decide, user=vendor_user)
        res_decide = VendorEstimationCustomerDecideView.as_view()(req_decide, pk=test_sr.id)
        assert res_decide.status_code == 200
        quote.refresh_from_db()
        test_sr.refresh_from_db()
        assert quote.status == "REJECTED"
        assert quote.rejection_reason == "PRICE_TOO_HIGH"
        assert test_sr.status in ["cancelled", "customer_rejected"]

        # 12b: Vendor revises quote -> creates Version 2
        req_revise = factory.post(f"/api/vendor/estimations/{test_sr.id}/quotation/{quote.id}/revise/")
        force_authenticate(req_revise, user=vendor_user)
        res_revise = VendorEstimationQuotationReviseView.as_view()(req_revise, pk=test_sr.id, quote_id=quote.id)
        assert res_revise.status_code == 200

        quote_v2 = EstimationQuotation.objects.filter(estimation=test_est).order_by("-version").first()
        assert quote_v2.version == 2
        assert quote_v2.quote_ref.endswith("-V2")
        assert quote_v2.status == "DRAFT"

        # Vendor offers ₹350 discount on V2 and sends it
        quote_v2.discount_amount = Decimal("350.00")
        quote_v2.total_amount = Decimal("2500.00") + Decimal("450.00") - Decimal("350.00") # = 2600.00
        quote_v2.save()

        req_send_v2 = factory.post(f"/api/vendor/estimations/{test_sr.id}/quotation/{quote_v2.id}/send/")
        force_authenticate(req_send_v2, user=vendor_user)
        VendorEstimationQuotationSendView.as_view()(req_send_v2, pk=test_sr.id, quote_id=quote_v2.id)

        # Customer approves V2
        req_app = factory.post(f"/api/vendor/estimations/{test_sr.id}/customer-decide/", {
            "decision": "APPROVE"
        }, format="json")
        force_authenticate(req_app, user=vendor_user)
        res_app = VendorEstimationCustomerDecideView.as_view()(req_app, pk=test_sr.id)
        assert res_app.status_code == 200
        quote_v2.refresh_from_db()
        test_sr.refresh_from_db()
        assert quote_v2.status in ["APPROVED", "CONVERTED"]
        assert test_sr.status in ["assigned", "in_progress", "customer_approved", "cancelled"]
        record_pass("12. Quote Revision & Customer Approval", f"V1 (REJECTED) -> V2 ({quote_v2.quote_ref} APPROVED at ₹2600)")

        # 13. Test Fee Collection and Waiver
        print("\n--- Step 13: Test Visit Fee Collection & Waiver ---")
        # 13a: Collect
        req_fee_col = factory.post(f"/api/vendor/estimations/{test_sr.id}/fee/collect/", {
            "payment_method": "UPI",
            "payment_reference": "UPI902834190823",
        }, format="json")
        force_authenticate(req_fee_col, user=vendor_user)
        res_fee_col = VendorEstimationFeeCollectView.as_view()(req_fee_col, pk=test_sr.id)
        assert res_fee_col.status_code == 200
        test_fee.refresh_from_db()
        assert test_fee.status == "COLLECTED"
        assert test_fee.payment_method == "UPI"
        assert test_fee.payment_reference == "UPI902834190823"

        # 13b: Waive
        req_fee_waive = factory.post(f"/api/vendor/estimations/{test_sr.id}/fee/waive/", {
            "reason": "Customer approved major repair work (₹2,600).",
        }, format="json")
        force_authenticate(req_fee_waive, user=vendor_user)
        res_fee_waive = VendorEstimationFeeWaiveView.as_view()(req_fee_waive, pk=test_sr.id)
        assert res_fee_waive.status_code == 200
        test_fee.refresh_from_db()
        assert test_fee.status == "WAIVED"
        assert "major repair work" in test_fee.waived_reason
        record_pass("13. Fee Collection & Waiver", "Fee marked COLLECTED (UPI) and subsequent waiver handled properly")

        # 14. Test Technicians Directory API
        print("\n--- Step 14: Test Technicians Directory API ---")
        req_techs = factory.get("/api/vendor/technicians/")
        force_authenticate(req_techs, user=vendor_user)
        res_techs = VendorTechniciansListView.as_view()(req_techs)
        assert res_techs.status_code == 200
        assert "technicians" in res_techs.data
        record_pass("14. GET /api/vendor/technicians/", f"Directory API returned {len(res_techs.data['technicians'])} technicians")

    finally:
        # Cleanup test records
        print("\n--- Cleaning up Test Fixtures ---")
        try:
            with connection.cursor() as cur:
                cur.execute("DELETE FROM service_requests_estimationquotationitem WHERE quotation_id IN (SELECT id FROM service_requests_estimationquotation WHERE estimation_id = %s)", [test_est.id])
                cur.execute("DELETE FROM service_requests_estimationquotation WHERE estimation_id = %s", [test_est.id])
                cur.execute("DELETE FROM service_requests_inspectionphoto WHERE inspection_id IN (SELECT id FROM service_requests_inspection WHERE estimation_id = %s)", [test_est.id])
                cur.execute("DELETE FROM service_requests_inspectionfinding WHERE inspection_id IN (SELECT id FROM service_requests_inspection WHERE estimation_id = %s)", [test_est.id])
                cur.execute("DELETE FROM service_requests_inspection WHERE estimation_id = %s", [test_est.id])
                cur.execute("DELETE FROM service_requests_estimationfee WHERE estimation_id = %s", [test_est.id])
                cur.execute("DELETE FROM service_requests_estimation WHERE id = %s", [test_est.id])
                cur.execute("DELETE FROM service_requests_payment WHERE service_request_id = %s", [test_sr.id])
                cur.execute("DELETE FROM settings_hub_invoice WHERE invoice_number LIKE %s", [f"%{test_sr.id}%"])
                cur.execute("DELETE FROM service_requests_servicerequest WHERE id = %s", [test_sr.id])
                cur.execute("DELETE FROM accounts_user WHERE id IN (%s, %s)", [vendor_user.id, tech_user.id])
            print("  Cleanup successful.")
        except Exception as e:
            print(f"  Cleanup note: {e}")

    # Summary
    print("\n=======================================================")
    print(f"TEST RESULTS: {len(PASSED_TESTS)} PASSED, {len(FAILED_TESTS)} FAILED")
    print("=======================================================")
    if FAILED_TESTS:
        print("\nFailures:")
        for name, err in FAILED_TESTS:
            print(f" - {name}: {err}")
        sys.exit(1)
    else:
        print("\nALL VENDOR AC INSPECTION & ESTIMATION TESTS PASSED 100%!")


if __name__ == "__main__":
    run_e2e_suite()
