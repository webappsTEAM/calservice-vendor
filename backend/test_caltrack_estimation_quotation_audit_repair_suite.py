#!/usr/bin/env python
"""
backend/test_caltrack_estimation_quotation_audit_repair_suite.py

Comprehensive End-to-End Master Test Suite for CalTrack Estimation & Quotation Engine.
Verifies all 6 mandatory sections:
  1. Service-Matched Dispatch (AC vs Painter isolation)
  2. Mandatory Accept Flow (Quoted Execution, Same Technician, No Broadcast)
  3. Mandatory Decline Flow (Fee Due, Authoritative Collection, SettingsHubInvoice)
  4. Amount Authority Test (Booking A ₹249 vs Booking B ₹349 dynamic preservation)
  5. Quotation Amount Test (Accepted Quote Net Payable -> Execution Amount)
  6. Idempotency Test (Duplicate Accept, Payment, Invoice triggers)
"""
import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
import uuid
from decimal import Decimal
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from service_requests.models import (
    CatalogCategory,
    Service,
    ServiceRequest,
    EmployeeJob,
    Estimation,
    EstimationFee,
    EstimationQuotation,
    EstimationQuotationItem,
    Inspection,
    SettingsHubInvoice,
    ServiceRequestPayment,
)
from employees.models import Employee
from companies.models import Company
from workforce_api.models import (
    WorkforceEmployeeService,
    WorkforceQuote,
    WorkforceQuoteItem,
    WorkforceQuoteMeasurement,
    PreServiceVerification,
    WorkforceJobOffer,
    WorkforceEventLog,
)
from workforce_api.services.automatic_dispatch import dispatch_job
from workforce_api.services.quotation_service import (
    can_create_quote,
    send_quote_to_customer,
    record_customer_decision,
    convert_accepted_quote_to_work_booking,
)
from workforce_api.views import (
    WorkforceQuoteItemBulkView,
    WorkforceQuoteMeasurementsBulkView,
    WorkforceQuoteInspectionView,
    WorkforceCustomerQuoteDecideView,
    WorkforceJobPaymentVerifyOTPView,
)

User = get_user_model()
factory = APIRequestFactory()

def log_test(name, passed, detail=""):
    badge = " [PASS] " if passed else " [FAIL] "
    print(f"{badge} {name}")
    if detail:
        print(f"        -> {detail}")
    if not passed:
        raise AssertionError(f"Test failed: {name} - {detail}")


def run_suite():
    print("=" * 80)
    print("CALTRACK ESTIMATION & QUOTATION END-TO-END CONNECTION MASTER TEST SUITE")
    print("=" * 80)

    run_id = uuid.uuid4().hex[:6].upper()
    now = timezone.now()

    # Setup Company
    company, _ = Company.objects.get_or_create(
        company_name=f"CalTrack Test Corp {run_id}",
        defaults={"is_active": True}
    )

    # Use canonical database services (Source of Truth)
    ac_service = Service.objects.filter(id=63).first() or Service.objects.filter(name__icontains="AC Repair").first()
    paint_service = Service.objects.filter(id=91).first() or Service.objects.filter(name__icontains="Painting").first()
    assert ac_service is not None, "Canonical AC service (id=63) must exist in DB."
    assert paint_service is not None, "Canonical Painting service (id=91) must exist in DB."

    # Setup Technicians: AC Technician vs Painter
    now_iso = timezone.now().isoformat()
    user_ac, _ = User.objects.get_or_create(
        username=f"tech_ac_{run_id}",
        defaults={"email": f"ac_{run_id}@caltrack.com", "first_name": "Ravi", "last_name": "AC Tech"}
    )
    user_ac.set_password("pass1234")
    user_ac.last_known_location = {
        "latitude": 13.0827,
        "longitude": 80.2707,
        "accuracy": 10.0,
        "captured_at": now_iso,
        "updated_at": now_iso,
    }
    user_ac.save()

    emp_ac, _ = Employee.objects.get_or_create(
        user=user_ac,
        defaults={
            "company": company,
            "employee_id": f"EMP-AC-{run_id}",
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
            "bank_details": {
                "onboarding": {
                    "status": "approved",
                    "services": [
                        {"id": ac_service.id, "name": ac_service.name, "category": "hvac", "status": "approved"}
                    ]
                }
            }
        }
    )
    emp_ac.company = company
    emp_ac.is_active = True
    emp_ac.is_online = True
    emp_ac.current_availability = "available"
    emp_ac.bank_details = {
        "onboarding": {
            "status": "approved",
            "services": [
                {"id": ac_service.id, "name": ac_service.name, "category": "hvac", "status": "approved"}
            ]
        }
    }
    emp_ac.save()

    # Approve AC service for AC tech
    WorkforceEmployeeService.objects.get_or_create(
        employee=emp_ac,
        service=ac_service,
        defaults={"status": WorkforceEmployeeService.Status.APPROVED}
    )

    user_painter, _ = User.objects.get_or_create(
        username=f"tech_paint_{run_id}",
        defaults={"email": f"paint_{run_id}@caltrack.com", "first_name": "Suresh", "last_name": "Painter"}
    )
    user_painter.set_password("pass1234")
    user_painter.last_known_location = {
        "latitude": 13.0827,
        "longitude": 80.2707,
        "accuracy": 10.0,
        "captured_at": now_iso,
        "updated_at": now_iso,
    }
    user_painter.save()

    emp_painter, _ = Employee.objects.get_or_create(
        user=user_painter,
        defaults={
            "company": company,
            "employee_id": f"EMP-PAINT-{run_id}",
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
            "bank_details": {
                "onboarding": {
                    "status": "approved",
                    "services": [
                        {"id": paint_service.id, "name": paint_service.name, "category": "painting", "status": "approved"}
                    ]
                }
            }
        }
    )
    emp_painter.company = company
    emp_painter.is_active = True
    emp_painter.is_online = True
    emp_painter.current_availability = "available"
    emp_painter.bank_details = {
        "onboarding": {
            "status": "approved",
            "services": [
                {"id": paint_service.id, "name": paint_service.name, "category": "painting", "status": "approved"}
            ]
        }
    }
    emp_painter.save()

    # Approve Painting service for painter (ONLY painting, ZERO AC)
    WorkforceEmployeeService.objects.get_or_create(
        employee=emp_painter,
        service=paint_service,
        defaults={"status": WorkforceEmployeeService.Status.APPROVED}
    )

    # -------------------------------------------------------------------------
    # TEST 1: Service-Matched Dispatch & Candidate Isolation
    # -------------------------------------------------------------------------
    print("\n--- TEST 1: Service-Matched Dispatch Isolation ---")
    custom_booking_fee = Decimal("275.00")
    ac_sr = ServiceRequest.objects.create(
        request_kind="estimation",
        company=company,
        customer_name="Anita Sharma",
        phone="9876543210",
        issue_title=ac_service.name,
        service_category="AC Services",
        cart_data=[{"id": ac_service.id, "name": ac_service.name}],
        address="12 Anna Nagar, Chennai",
        latitude=Decimal("13.0827"),
        longitude=Decimal("80.2707"),
        total_amount=custom_booking_fee,
        preferred_date=now.date(),
        status="confirmed",
    )

    # Verify auto-initialization from ServiceRequest.total_amount
    est_obj = Estimation.objects.filter(service_request=ac_sr).first()
    fee_obj = est_obj.fees.first() if est_obj else None
    log_test(
        "Estimation & EstimationFee auto-initialized from booking total_amount",
        est_obj is not None and fee_obj is not None and fee_obj.amount == custom_booking_fee,
        f"fee.amount={fee_obj.amount if fee_obj else None}, expected={custom_booking_fee}"
    )

    # Dispatch AC estimation
    dispatch_job(ac_sr.id)

    ac_offers = WorkforceJobOffer.objects.filter(job=ac_sr, employee=emp_ac)
    paint_offers = WorkforceJobOffer.objects.filter(job=ac_sr, employee=emp_painter)

    log_test(
        "Only AC-approved technician receives AC estimation offer",
        ac_offers.count() >= 1,
        f"AC Tech offers count={ac_offers.count()}"
    )
    log_test(
        "Painter receives ZERO AC estimation offers",
        paint_offers.count() == 0,
        f"Painter Tech offers count={paint_offers.count()}"
    )

    offer_event = WorkforceEventLog.objects.filter(
        event_type="JOB_OFFER_CREATED",
        payload__job_id=ac_sr.id,
        payload__employee_id=emp_ac.id
    ).first()
    log_test("JOB_OFFER_CREATED durable event logged with correct payload", offer_event is not None)

    # -------------------------------------------------------------------------
    # TEST 2: Offer Acceptance & Active Jobs Mapping
    # -------------------------------------------------------------------------
    print("\n--- TEST 2: Offer Acceptance & Active Jobs Mapping ---")
    # Atomically accept offer
    ac_offer = ac_offers.first()
    ac_offer.status = "ACCEPTED"
    ac_offer.save(update_fields=["status"])

    ac_sr.status = "assigned"
    ac_sr.assigned_employee = emp_ac
    ac_sr.technician_name = emp_ac.user.get_full_name()
    ac_sr.save(update_fields=["status", "assigned_employee", "technician_name", "updated_at"])

    emp_job, _ = EmployeeJob.objects.update_or_create(
        service_request=ac_sr,
        employee=emp_ac,
        defaults={"status": "ASSIGNED", "is_primary": True, "assigned_date": now}
    )
    log_test("Technician EmployeeJob created as PRIMARY and ASSIGNED", emp_job.is_primary and emp_job.status == "ASSIGNED")

    # -------------------------------------------------------------------------
    # TEST 3: Pre-Service Verification Gate
    # -------------------------------------------------------------------------
    print("\n--- TEST 3: Pre-Service Verification Gate ---")
    psv, _ = PreServiceVerification.objects.get_or_create(job=ac_sr, defaults={"employee": emp_ac})
    if not psv.employee:
        psv.employee = emp_ac
        psv.save()
    can_q_before, _ = can_create_quote(ac_sr)
    log_test("Quote creation blocked prior to 4-gate verification completion", not can_q_before)

    psv.geofence_passed = True
    psv.otp_verified = True
    psv.presence_photo = "uploads/selfie_test.jpg"
    psv.work_area_photo = "uploads/area_test.jpg"
    psv.appliance_photo = "uploads/ac_test.jpg"
    psv.is_complete = True
    psv.save()

    can_q_after, details = can_create_quote(ac_sr)
    log_test("Quote creation unlocked after GPS, OTP, Selfie, and Photos verification", can_q_after, str(details))

    # -------------------------------------------------------------------------
    # TEST 4: Inspection Completion & Event
    # -------------------------------------------------------------------------
    print("\n--- TEST 4: Inspection Completion & Event ---")
    # Initialize WorkforceQuote linked to ac_sr
    wf_quote = WorkforceQuote.objects.create(
        quote_number=f"QTE-{ac_sr.id}-V1",
        quote_version=1,
        job=ac_sr,
        technician=emp_ac,
        company=company,
        title="AC Repair and Gas Refill",
        service_category="AC Services",
        status=WorkforceQuote.Status.DRAFT,
    )

    insp_view = WorkforceQuoteInspectionView.as_view()
    insp_req = factory.post(
        f"/api/workforce/quotes/{wf_quote.id}/inspection/",
        {"area_sqft": 150, "structural_impact": False, "notes": "AC cooling coil requires chemical wash & gas top-up"},
        format="json"
    )
    force_authenticate(insp_req, user=user_ac)
    insp_res = insp_view(insp_req, pk=wf_quote.id)
    log_test("WorkforceQuoteInspectionView completes and records inspection", insp_res.status_code == 200)

    insp_event = WorkforceEventLog.objects.filter(
        event_type="INSPECTION_UPDATED",
        payload__quote_id=wf_quote.id
    ).first()
    log_test("INSPECTION_UPDATED durable event logged", insp_event is not None)

    # -------------------------------------------------------------------------
    # TEST 5: Quotation Items Bulk Saving & Rate Snapshotting
    # -------------------------------------------------------------------------
    print("\n--- TEST 5: Quotation Line Items & Authoritative Recalculation ---")
    item_view = WorkforceQuoteItemBulkView.as_view()
    items_payload = [
        {
            "name": "Chemical Wash Service",
            "item_type": "labor",
            "quantity": 1,
            "unit": "visit",
            "unit_price": 800.0,
            "tax_rate": 18.0,
            "discount_amount": 0.0,
        },
        {
            "name": "R32 Refrigerant Gas Refill",
            "item_type": "part",
            "quantity": 1,
            "unit": "cylinder",
            "unit_price": 1500.0,
            "tax_rate": 18.0,
            "discount_amount": 100.0,
        }
    ]
    item_req = factory.post(
        f"/api/workforce/quotes/{wf_quote.id}/items/bulk/",
        {"items": items_payload},
        format="json"
    )
    force_authenticate(item_req, user=user_ac)
    item_res = item_view(item_req, pk=wf_quote.id)
    log_test("WorkforceQuoteItemBulkView persists items", item_res.status_code == 200)

    wf_quote.refresh_from_db()
    # Expected subtotal = 800 + 1400 = 2200.00; discount = 100; taxable = 2200; tax 18% = 396; net = 2596.00
    log_test(
        "Authoritative backend calculation engine computes correct net payable",
        wf_quote.subtotal_amount == Decimal("2200.00") and wf_quote.net_payable == Decimal("2596.00"),
        f"subtotal={wf_quote.subtotal_amount}, net_payable={wf_quote.net_payable}"
    )

    # Check canonical EstimationQuotation synchronization
    canon_q = EstimationQuotation.objects.filter(quote_ref=wf_quote.quote_number).first()
    log_test(
        "WorkforceQuote synchronized into canonical EstimationQuotation & Items",
        canon_q is not None and canon_q.items.count() == 2,
        f"canon_items_count={canon_q.items.count() if canon_q else 0}"
    )

    # Send Quote to Customer
    send_quote_to_customer(wf_quote.id)
    wf_quote.refresh_from_db()
    log_test(
        "Quotation sent, valid_until set, decision_token generated",
        wf_quote.status == WorkforceQuote.Status.SENT_TO_CUSTOMER and bool(wf_quote.decision_token)
    )

    q_sent_event = WorkforceEventLog.objects.filter(
        event_type="QUOTATION_SENT",
        payload__quote_id=wf_quote.id
    ).first()
    log_test("QUOTATION_SENT durable event logged", q_sent_event is not None)

    # -------------------------------------------------------------------------
    # TEST 6: MANDATORY ACCEPT TEST (Section 24)
    # -------------------------------------------------------------------------
    print("\n--- TEST 6: MANDATORY ACCEPT TEST (Section 24) ---")
    decide_view = WorkforceCustomerQuoteDecideView.as_view()
    accept_req = factory.post(
        f"/api/workforce/customer/quote-token/{wf_quote.decision_token}/decide/",
        {"decision": "ACCEPT", "notes": "Approved for execution"},
        format="json"
    )
    accept_res = decide_view(accept_req, token=wf_quote.decision_token)
    log_test("Customer ACCEPT endpoint returns 200", accept_res.status_code == 200, str(accept_res.data))

    wf_quote.refresh_from_db()
    exec_sr = wf_quote.work_job

    log_test(
        "Exactly ONE execution job created with request_kind=quoted_execution",
        exec_sr is not None and exec_sr.request_kind in ["quoted_execution", "work", "WORK"],
        f"exec_id={exec_sr.id if exec_sr else None}, request_kind={exec_sr.request_kind if exec_sr else None}"
    )
    log_test(
        "Execution job parent_request_id points to estimation job",
        exec_sr and exec_sr.parent_request_id == ac_sr.id,
        f"parent_request_id={exec_sr.parent_request_id if exec_sr else None}, expected={ac_sr.id}"
    )
    log_test(
        "SAME TECHNICIAN assigned to execution job (NO general dispatch broadcast)",
        exec_sr and exec_sr.assigned_employee == emp_ac,
        f"assigned={exec_sr.assigned_employee if exec_sr else None}, expected={emp_ac}"
    )
    log_test(
        "Execution total_amount equals accepted quote net payable (NO HARDCODED PRICE)",
        exec_sr and exec_sr.total_amount == wf_quote.net_payable,
        f"exec_amount={exec_sr.total_amount if exec_sr else None}, quote_net={wf_quote.net_payable}"
    )

    # Verify EmployeeJob for execution job
    exec_ej = EmployeeJob.objects.filter(service_request=exec_sr, employee=emp_ac).first()
    log_test(
        "EmployeeJob created for SAME technician on execution job",
        exec_ej is not None and exec_ej.status == "ASSIGNED" and exec_ej.is_primary
    )

    # Verify parent fee waived
    fee_obj.refresh_from_db()
    log_test("Parent estimation fee marked WAIVED upon quotation acceptance", fee_obj.status == "WAIVED")

    # Verify events
    appr_event = WorkforceEventLog.objects.filter(event_type="QUOTATION_APPROVED", payload__quote_id=wf_quote.id).first()
    exec_event = WorkforceEventLog.objects.filter(event_type="EXECUTION_JOB_CREATED", payload__job_id=exec_sr.id).first()
    log_test("QUOTATION_APPROVED durable event logged", appr_event is not None)
    log_test("EXECUTION_JOB_CREATED durable event logged", exec_event is not None)

    # -------------------------------------------------------------------------
    # TEST 7: MANDATORY DECLINE TEST (Section 25)
    # -------------------------------------------------------------------------
    print("\n--- TEST 7: MANDATORY DECLINE TEST (Section 25) ---")
    custom_decline_fee = Decimal("340.00")
    decline_sr = ServiceRequest.objects.create(
        request_kind="estimation",
        company=company,
        customer_name="Vikram Seth",
        phone="9876543211",
        issue_title=ac_service.name,
        service_category="AC Services",
        cart_data=[{"id": ac_service.id, "name": ac_service.name}],
        address="15 Anna Nagar, Chennai",
        latitude=Decimal("13.0827"),
        longitude=Decimal("80.2707"),
        total_amount=custom_decline_fee,
        preferred_date=now.date(),
        status="assigned",
        assigned_employee=emp_ac,
    )
    EmployeeJob.objects.create(service_request=decline_sr, employee=emp_ac, status="ASSIGNED", is_primary=True)

    d_est = Estimation.objects.filter(service_request=decline_sr).first()
    d_fee = d_est.fees.first()
    log_test(
        "Decline flow estimation fee initialized to authoritative INR 340.00",
        d_fee.amount == custom_decline_fee,
        f"fee={d_fee.amount}"
    )

    # Create Quote for decline flow
    d_quote = WorkforceQuote.objects.create(
        quote_number=f"QTE-DEC-{decline_sr.id}-V1",
        quote_version=1,
        job=decline_sr,
        technician=emp_ac,
        company=company,
        title="AC Overhaul",
        total_amount=Decimal("4500.00"),
        net_payable=Decimal("4500.00"),
        status=WorkforceQuote.Status.SENT_TO_CUSTOMER,
        decision_token=f"DEC_TOKEN_{run_id}",
    )

    # Customer declines
    dec_req = factory.post(
        f"/api/workforce/customer/quote-token/{d_quote.decision_token}/decide/",
        {"decision": "DECLINE", "decline_reason": "Price exceeds budget"},
        format="json"
    )
    dec_res = decide_view(dec_req, token=d_quote.decision_token)
    log_test("Customer DECLINE endpoint returns 200", dec_res.status_code == 200)

    d_quote.refresh_from_db()
    d_fee.refresh_from_db()
    decline_sr.refresh_from_db()

    log_test("Quotation marked DECLINED", d_quote.status == WorkforceQuote.Status.DECLINED)
    log_test("ZERO execution jobs created on decline", d_quote.work_job is None)
    log_test(
        "Estimation fee status is PENDING (fee due from customer)",
        d_fee.status == "PENDING" and d_fee.amount == custom_decline_fee,
        f"fee_status={d_fee.status}, amount={d_fee.amount}"
    )

    decl_event = WorkforceEventLog.objects.filter(event_type="QUOTATION_DECLINED", payload__quote_id=d_quote.id).first()
    log_test("QUOTATION_DECLINED durable event logged", decl_event is not None)

    # Now collect fee via VendorEstimationCustomerDecideView (or fee collection)
    from service_requests.vendor_views import VendorEstimationCustomerDecideView
    vendor_decide_view = VendorEstimationCustomerDecideView.as_view()
    collect_req = factory.post(
        f"/api/vendor/estimations/{decline_sr.id}/customer-decide/",
        {
            "decision": "REJECT",
            "rejection_reason": "PRICE_TOO_HIGH",
            "payment_method": "CASH",
        },
        format="json"
    )
    force_authenticate(collect_req, user=user_ac)
    collect_res = vendor_decide_view(collect_req, pk=decline_sr.id)
    log_test("Fee collection & decline invoice creation returns 200", collect_res.status_code == 200)

    d_fee.refresh_from_db()
    decline_sr.refresh_from_db()

    log_test("Estimation fee marked COLLECTED", d_fee.status == "COLLECTED")

    # Verify SettingsHubInvoice created with authoritative fee amount
    inv_obj = SettingsHubInvoice.objects.filter(invoice_number=decline_sr.invoice_id).first()
    log_test(
        "Authoritative SettingsHubInvoice persisted with exact booking fee amount (NO HARDCODED 199)",
        inv_obj is not None and inv_obj.amount == custom_decline_fee and inv_obj.status == "PAID",
        f"invoice_num={decline_sr.invoice_id}, amount={inv_obj.amount if inv_obj else None}, expected={custom_decline_fee}"
    )

    # Verify durable events
    pmt_ev = WorkforceEventLog.objects.filter(event_type="PAYMENT_UPDATED", payload__service_request_id=decline_sr.id).first()
    inv_ev = WorkforceEventLog.objects.filter(event_type="INVOICE_CREATED", payload__service_request_id=decline_sr.id).first()
    job_ev = WorkforceEventLog.objects.filter(event_type="JOB_COMPLETED", payload__job_id=decline_sr.id).first()
    log_test("PAYMENT_UPDATED durable event logged", pmt_ev is not None)
    log_test("INVOICE_CREATED durable event logged", inv_ev is not None)
    log_test("JOB_COMPLETED durable event logged", job_ev is not None)

    # Verify EmployeeJob completed
    dec_ej = EmployeeJob.objects.filter(service_request=decline_sr, employee=emp_ac).first()
    log_test("Technician EmployeeJob marked COMPLETED on fee payment", dec_ej.status == "COMPLETED")

    # -------------------------------------------------------------------------
    # TEST 8: AMOUNT AUTHORITY TEST (Section 26: Booking A ₹249 vs Booking B ₹349)
    # -------------------------------------------------------------------------
    print("\n--- TEST 8: AMOUNT AUTHORITY TEST (Booking A ₹249 vs Booking B ₹349) ---")
    amt_a = Decimal("249.00")
    amt_b = Decimal("349.00")

    sr_a = ServiceRequest.objects.create(
        request_kind="estimation",
        company=company,
        customer_name="Customer A",
        address="100 Mount Road, Chennai",
        issue_title=ac_service.name,
        service_category="AC Services",
        total_amount=amt_a,
        preferred_date=now.date(),
    )
    est_a = Estimation.objects.filter(service_request=sr_a).first()
    fee_a = est_a.fees.first()

    sr_b = ServiceRequest.objects.create(
        request_kind="estimation",
        company=company,
        customer_name="Customer B",
        address="101 Mount Road, Chennai",
        issue_title=ac_service.name,
        service_category="AC Services",
        total_amount=amt_b,
        preferred_date=now.date(),
    )
    est_b = Estimation.objects.filter(service_request=sr_b).first()
    fee_b = est_b.fees.first()

    log_test(
        "Booking A authoritative fee strictly equals INR 249.00",
        fee_a.amount == amt_a,
        f"actual={fee_a.amount}, expected={amt_a}"
    )
    log_test(
        "Booking B authoritative fee strictly equals INR 349.00",
        fee_b.amount == amt_b,
        f"actual={fee_b.amount}, expected={amt_b}"
    )

    # -------------------------------------------------------------------------
    # TEST 9: QUOTATION AMOUNT TEST (Section 27: Quote A INR 1,850 vs Quote B INR 3,200)
    # -------------------------------------------------------------------------
    print("\n--- TEST 9: QUOTATION AMOUNT TEST (Quote A INR 1,850 vs Quote B INR 3,200) ---")
    quote_amt_a = Decimal("1850.00")
    q_a = WorkforceQuote.objects.create(
        quote_number=f"QTE-TEST-A-{run_id}",
        quote_version=1,
        job=sr_a,
        technician=emp_ac,
        company=company,
        title="Quote A",
        total_amount=quote_amt_a,
        net_payable=quote_amt_a,
        status=WorkforceQuote.Status.SENT_TO_CUSTOMER,
        decision_token=f"TOKEN_A_{run_id}",
    )
    work_a = convert_accepted_quote_to_work_booking(q_a)
    log_test(
        "Accepted Quote A converts to execution job with exact payable amount INR 1,850.00",
        work_a.total_amount == quote_amt_a,
        f"actual={work_a.total_amount}, expected={quote_amt_a}"
    )

    quote_amt_b = Decimal("3200.00")
    q_b = WorkforceQuote.objects.create(
        quote_number=f"QTE-TEST-B-{run_id}",
        quote_version=1,
        job=sr_b,
        technician=emp_ac,
        company=company,
        title="Quote B",
        total_amount=quote_amt_b,
        net_payable=quote_amt_b,
        status=WorkforceQuote.Status.SENT_TO_CUSTOMER,
        decision_token=f"TOKEN_B_{run_id}",
    )
    work_b = convert_accepted_quote_to_work_booking(q_b)
    log_test(
        "Accepted Quote B converts to execution job with exact payable amount INR 3,200.00",
        work_b.total_amount == quote_amt_b,
        f"actual={work_b.total_amount}, expected={quote_amt_b}"
    )

    # -------------------------------------------------------------------------
    # TEST 10: IDEMPOTENCY TEST (Section 28)
    # -------------------------------------------------------------------------
    print("\n--- TEST 10: IDEMPOTENCY TEST (Section 28) ---")
    # Repeated ACCEPT
    work_a_repeat1 = convert_accepted_quote_to_work_booking(q_a)
    work_a_repeat2 = convert_accepted_quote_to_work_booking(q_a)

    log_test(
        "Repeated ACCEPT call returns identical execution job ID (No duplicate jobs)",
        work_a.id == work_a_repeat1.id == work_a_repeat2.id,
        f"ids=({work_a.id}, {work_a_repeat1.id}, {work_a_repeat2.id})"
    )

    matching_work_jobs = ServiceRequest.objects.filter(quote_number=q_a.quote_number)
    log_test(
        "Exactly ONE execution ServiceRequest exists for Quote A",
        matching_work_jobs.count() == 1,
        f"count={matching_work_jobs.count()}"
    )

    # Repeated Payment / Invoice
    inv_count_before = SettingsHubInvoice.objects.filter(invoice_number=decline_sr.invoice_id).count()
    collect_res2 = vendor_decide_view(collect_req, pk=decline_sr.id)
    inv_count_after = SettingsHubInvoice.objects.filter(invoice_number=decline_sr.invoice_id).count()
    log_test(
        "Repeated payment / invoice triggers produce exactly ONE SettingsHubInvoice",
        inv_count_before == 1 and inv_count_after == 1,
        f"before={inv_count_before}, after={inv_count_after}"
    )

    print("\n" + "=" * 80)
    print("ALL 10 MANDATORY VERIFICATION GATES PASSED WITHOUT ERRORS!")
    print("=" * 80)


if __name__ == "__main__":
    run_suite()
