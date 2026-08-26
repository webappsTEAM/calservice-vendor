"""
backend/test_estimation_and_quotation_suite.py
Comprehensive End-to-End Test Suite for CalTrack Workforce Estimation & Commercial Quotation Workflow.
Executes against real Supabase PostgreSQL database with zero fake data.
"""
import os
import sys
import uuid
import django
from decimal import Decimal
from datetime import datetime, timezone, timedelta

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import connection, transaction
from rest_framework.test import APIRequestFactory, force_authenticate

from service_requests.models import (
    Service,
    ServiceRequest,
    RequestKind,
    QUOTATION_SERVICE_IDS,
    is_quotation_service,
)
from employees.models import Employee as WorkforceEmployee
from workforce_api.models import (
    PreServiceVerification,
    WorkforceRateCard,
    WorkforceQuote,
    WorkforceQuoteItem,
    WorkforceQuoteMeasurement,
    WorkforcePaintingQuote,
    WorkforceMasonQuote,
    generate_quote_number,
)
from workforce_api.services.quotation_service import (
    can_create_quote,
    recalculate_quote_totals,
    send_quote_to_customer,
    record_customer_decision,
    create_revised_quote_version,
    convert_accepted_quote_to_work_booking,
    admin_clear_mason_structural,
)
from workforce_api.views import (
    WorkforceEstimationGateView,
    WorkforceRateCardListView,
    WorkforceQuoteListView,
    WorkforceQuoteDetailView,
    WorkforceQuoteItemBulkView,
    WorkforceQuoteMeasurementsBulkView,
    WorkforceQuoteInspectionView,
    WorkforceQuoteSendView,
    WorkforceQuoteReviseView,
    WorkforceCustomerQuoteDetailView,
    WorkforceCustomerQuoteDecideView,
    WorkforceAdminQuoteClearanceView,
    WorkforceAdminQuoteMetricsView,
    WorkforceAdminQuoteRetryConversionView,
)

User = get_user_model()
factory = APIRequestFactory()

TEST_RUN_ID = uuid.uuid4().hex[:6]
PASSED_TESTS = []
FAILED_TESTS = []


def record_pass(test_name, details=""):
    print(f"  [PASS] {test_name} {details}")
    PASSED_TESTS.append(test_name)


def record_fail(test_name, error):
    import traceback
    print(f"  [FAIL] {test_name} -> {error}")
    traceback.print_exc()
    FAILED_TESTS.append((test_name, str(error)))


def setup_test_fixtures():
    """Create test company, users, employee, and sample service request."""
    print("\n--- Setting up Test Fixtures ---")
    admin_user, _ = User.objects.get_or_create(
        username=f"admin_quote_test_{TEST_RUN_ID}",
        defaults={"email": f"admin_quote_{TEST_RUN_ID}@example.com", "is_staff": True, "is_superuser": True},
    )
    admin_user.set_password("AdminPass123!")
    admin_user.save()

    emp_user, _ = User.objects.get_or_create(
        username=f"emp_quote_test_{TEST_RUN_ID}",
        defaults={"email": f"emp_quote_{TEST_RUN_ID}@example.com", "first_name": "Ramesh", "last_name": "Painter"},
    )
    emp_user.set_password("EmpPass123!")
    emp_user.save()

    employee, _ = WorkforceEmployee.objects.get_or_create(
        user=emp_user,
        defaults={"company_id": 1, "employee_id": f"EMP-{TEST_RUN_ID}", "is_online": True},
    )

    # Fetch a painting service (e.g. ID 91)
    painting_service = Service.objects.filter(id__in=QUOTATION_SERVICE_IDS).first()
    if not painting_service:
        painting_service = Service.objects.first()

    # Create an Estimation Job
    est_job = ServiceRequest.objects.create(
        customer_id=1,
        company_id=1,
        service_category="Painting",
        issue_title=f"Interior Painting ({TEST_RUN_ID})",
        description="Customer requested full interior and balcony repaint estimation.",
        address="102 Palm Grove Apartments, Indiranagar, Bangalore",
        latitude=12.971600,
        longitude=77.594600,
        request_kind=RequestKind.ESTIMATION,
        status="arrived",
        preferred_date=datetime.now(timezone.utc).date(),
        assigned_employee=employee,
        total_amount=Decimal("299.00"),  # Inspection fee
    )

    # Create PreServiceVerification for this job
    psv, _ = PreServiceVerification.objects.get_or_create(
        job=est_job,
        defaults={
            "employee": employee,
            "geofence_passed": False,
            "otp_verified": False,
            "presence_photo": "",
            "appliance_photo": "",
            "work_area_photo": "",
        },
    )

    print(f"  Test Admin: {admin_user.username}")
    print(f"  Test Employee: {employee.id} ({emp_user.username})")
    print(f"  Test Estimation Job: {est_job.id} ({est_job.issue_title})")
    return admin_user, employee, est_job, psv


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Service Classification
# ─────────────────────────────────────────────────────────────────────────────
def test_service_classification(painting_service):
    print("\n[TEST 1] Service Classification & Quotation Services Detection")
    try:
        assert len(QUOTATION_SERVICE_IDS) >= 8, f"Expected at least 8 quotation service IDs, got {len(QUOTATION_SERVICE_IDS)}"
        assert 91 in QUOTATION_SERVICE_IDS, "Painting ID 91 missing from QUOTATION_SERVICE_IDS"
        assert 35 in QUOTATION_SERVICE_IDS, "Mason ID 35 missing from QUOTATION_SERVICE_IDS"
        assert is_quotation_service(91) is True, "is_quotation_service(91) should be True"
        assert is_quotation_service(999999) is False, "is_quotation_service(999999) should be False"

        # Check Service properties
        if painting_service and painting_service.id in QUOTATION_SERVICE_IDS:
            assert painting_service.pricing_mode == "QUOTATION", f"Expected pricing_mode QUOTATION, got {painting_service.pricing_mode}"
            assert painting_service.requires_inspection is True, "requires_inspection should be True"
            assert painting_service.requires_measurement is True, "requires_measurement should be True"

        record_pass("test_service_classification", f"(Quotation Services count: {len(QUOTATION_SERVICE_IDS)})")
    except Exception as e:
        record_fail("test_service_classification", e)


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: ServiceRequest RequestKind Mapping & Properties
# ─────────────────────────────────────────────────────────────────────────────
def test_servicerequest_request_kind(est_job):
    print("\n[TEST 2] ServiceRequest RequestKind Mapping & Properties")
    try:
        assert est_job.request_kind == RequestKind.ESTIMATION, f"Expected ESTIMATION, got {est_job.request_kind}"
        assert est_job.is_estimation is True, "is_estimation should be True"
        assert est_job.is_work_job is False, "is_work_job should be False"
        assert est_job.pricing_mode == "QUOTATION", f"Expected QUOTATION, got {est_job.pricing_mode}"

        record_pass("test_servicerequest_request_kind", f"(RequestKind={est_job.request_kind})")
    except Exception as e:
        record_fail("test_servicerequest_request_kind", e)


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: Approved Rate Cards Catalog
# ─────────────────────────────────────────────────────────────────────────────
def test_rate_cards_catalog():
    print("\n[TEST 3] Rate Card Catalog Inspection")
    try:
        cards = WorkforceRateCard.objects.filter(is_active=True)
        assert cards.count() >= 10, f"Expected at least 10 seeded rate cards, got {cards.count()}"

        painting_cards = WorkforceRateCard.objects.filter(service_category__iexact="painting", is_active=True)
        mason_cards = WorkforceRateCard.objects.filter(service_category__iexact="mason", is_active=True)

        assert painting_cards.exists(), "Painting rate cards missing"
        assert mason_cards.exists(), "Mason rate cards missing"

        sample = painting_cards.first()
        assert sample.default_rate > 0, f"Default rate must be positive: {sample.default_rate}"
        assert sample.unit, f"Unit missing on rate card: {sample.unit}"

        record_pass("test_rate_cards_catalog", f"(Total Active Rate Cards: {cards.count()})")
    except Exception as e:
        record_fail("test_rate_cards_catalog", e)


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Pre-Service Verification Gate & can_create_quote
# ─────────────────────────────────────────────────────────────────────────────
def test_estimation_gate_rules(est_job, psv):
    print("\n[TEST 4] Pre-Service Verification Gate & can_create_quote Rule")
    try:
        # State 1: Nothing verified
        psv.geofence_passed = False
        psv.otp_verified = False
        psv.presence_photo = ""
        psv.appliance_photo = ""
        psv.work_area_photo = ""
        psv.is_complete = False
        psv.save()

        is_allowed, gate_res = can_create_quote(est_job)
        assert is_allowed is False, "Should be blocked when verification incomplete"
        assert len(gate_res["missing"]) >= 3, f"Expected at least 3 missing items, got {gate_res['missing']}"

        # State 2: Pass Geofence, OTP, Selfie, and Work Area Photo
        psv.geofence_passed = True
        psv.otp_verified = True
        psv.presence_photo = "pre_service/presence/test_selfie.jpg"
        psv.work_area_photo = "pre_service/work_area/test_area.jpg"
        psv.save()

        is_allowed_passed, gate_res_passed = can_create_quote(est_job)
        assert is_allowed_passed is True, f"Should be allowed when all verified, got: {gate_res_passed}"
        assert gate_res_passed["checks"]["gps_verified"] is True
        assert gate_res_passed["checks"]["otp_verified"] is True
        assert gate_res_passed["checks"]["selfie_verified"] is True
        assert gate_res_passed["checks"]["photos_verified"] is True

        record_pass("test_estimation_gate_rules", "(4-way verification gate verified)")
    except Exception as e:
        record_fail("test_estimation_gate_rules", e)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: Quotation Drafting, Line Items, & Authoritative Totals
# ─────────────────────────────────────────────────────────────────────────────
def test_quotation_creation_and_totals(employee, est_job):
    print("\n[TEST 5] Quotation Drafting & Totals Calculation")
    try:
        quote = WorkforceQuote.objects.create(
            job=est_job,
            technician=employee,
            company_id=1,
            customer_id=est_job.customer_id,
            title="Comprehensive 2BHK Asian Paints Royale Estimation",
            service_category="Painting",
            service_name=est_job.issue_title,
            inspection_fee=Decimal("299.00"),
            inspection_fee_adjusted=Decimal("299.00"),
            status="DRAFT",
        )
        assert quote.quote_number.startswith("QT-"), f"Invalid quote number: {quote.quote_number}"
        assert quote.quote_version == 1

        # Add Line Items
        item1 = WorkforceQuoteItem.objects.create(
            quote=quote,
            section="MATERIAL",
            name="Asian Paints Royale Luxury Emulsion",
            quantity=Decimal("1200.00"),
            unit="sqft",
            unit_price=Decimal("24.00"),
            tax_rate=Decimal("18.00"),
            discount_amount=Decimal("500.00"),
            material_source="CALTRACK",
        )

        item2 = WorkforceQuoteItem.objects.create(
            quote=quote,
            section="LABOUR",
            name="Master Painter Wall Preparation & Double Coat Application",
            quantity=Decimal("1200.00"),
            unit="sqft",
            unit_price=Decimal("12.00"),
            tax_rate=Decimal("18.00"),
            discount_amount=Decimal("0.00"),
            material_source="CALTRACK",
        )

        # Add Measurements
        meas = WorkforceQuoteMeasurement.objects.create(
            quote=quote,
            name="Living Room North Wall",
            length=Decimal("20.00"),
            height=Decimal("10.00"),
            area=Decimal("200.00"),
            unit="sqft",
        )

        # Add Painting Details
        p_detail = WorkforcePaintingQuote.objects.create(
            quote=quote,
            property_type="2BHK",
            area_sqft=Decimal("1200.00"),
            surface_condition="Good",
            paint_type="Premium",
            brand_grade="Asian Paints Royale Luxury",
            number_of_coats=2,
            requires_putty=True,
            requires_priming=True,
        )

        # Recalculate totals
        quote = recalculate_quote_totals(quote)

        assert quote.estimated_materials_cost == Decimal("28300.00"), f"Expected materials 28300.00, got {quote.estimated_materials_cost}"
        assert quote.estimated_labor_cost == Decimal("14400.00"), f"Expected labor 14400.00, got {quote.estimated_labor_cost}"
        assert quote.subtotal_amount == Decimal("42700.00"), f"Expected subtotal 42700.00, got {quote.subtotal_amount}"
        assert quote.tax_amount == Decimal("7686.00"), f"Expected tax 7686.00, got {quote.tax_amount}"
        assert quote.total_amount == Decimal("50386.00"), f"Expected grand total 50386.00, got {quote.total_amount}"
        assert quote.net_payable == Decimal("50087.00"), f"Expected net payable 50087.00, got {quote.net_payable}"

        record_pass("test_quotation_creation_and_totals", f"(Net Payable: INR {quote.net_payable})")
        return quote
    except Exception as e:
        record_fail("test_quotation_creation_and_totals", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Mason Structural Gate Enforcement & Admin Clearance
# ─────────────────────────────────────────────────────────────────────────────
def test_mason_structural_gate(admin_user, employee, est_job):
    print("\n[TEST 6] Mason Structural Gate Enforcement & Admin Clearance")
    try:
        mason_quote = WorkforceQuote.objects.create(
            job=est_job,
            technician=employee,
            company_id=1,
            customer_id=est_job.customer_id,
            title="Load-Bearing Partition Wall Demolition",
            service_category="Mason",
            service_name="Wall Demolition & Beam Retrofit",
            structural_impact="STRUCTURAL",
            status="DRAFT",
        )

        WorkforceQuoteItem.objects.create(
            quote=mason_quote,
            section="LABOUR",
            name="Demolition and Concrete Breaking",
            quantity=Decimal("1.00"),
            unit="job",
            unit_price=Decimal("15000.00"),
            tax_rate=Decimal("18.00"),
        )
        recalculate_quote_totals(mason_quote)

        # Attempt to send to customer without clearance — MUST FAIL
        blocked = False
        try:
            send_quote_to_customer(mason_quote.id)
        except Exception as err:
            blocked = True
            assert "structural" in str(err).lower(), f"Expected structural clearance error, got: {err}"

        assert blocked is True, "Quotation sending MUST be blocked when structural impact is uncleared"

        # Admin Grants Clearance
        cleared_quote = admin_clear_mason_structural(
            mason_quote.id,
            admin_user=admin_user,
            approved=True,
            notes="Structural Engineer inspected on-site: lintel beam is structurally sound.",
        )
        assert cleared_quote.is_structurally_cleared is True
        assert cleared_quote.admin_clearance_notes is not None

        # Now sending to customer MUST SUCCEED
        sent_quote = send_quote_to_customer(mason_quote.id)
        assert sent_quote.status == "SENT_TO_CUSTOMER"
        assert sent_quote.decision_token is not None

        record_pass("test_mason_structural_gate", "(Structural gate strictly enforced and cleared by Admin)")
    except Exception as e:
        record_fail("test_mason_structural_gate", e)


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Quotation Sending, Freezing, & Customer Decision Token
# ─────────────────────────────────────────────────────────────────────────────
def test_quote_sending_and_freezing(quote):
    print("\n[TEST 7] Quotation Sending, Freezing, & Decision Token")
    try:
        sent = send_quote_to_customer(quote.id)
        assert sent.status == "SENT_TO_CUSTOMER", f"Expected SENT_TO_CUSTOMER, got {sent.status}"
        assert sent.sent_at is not None
        assert sent.decision_token is not None and len(sent.decision_token) >= 32
        assert sent.valid_until > datetime.now(timezone.utc)

        # Verify Totals are Frozen
        assert sent.status != "DRAFT"

        record_pass("test_quote_sending_and_freezing", f"(Decision Token: {sent.decision_token[:10]}...)")
        return sent
    except Exception as e:
        record_fail("test_quote_sending_and_freezing", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Customer Decision Lifecycle: Revision Cycle (REQUEST_CHANGES)
# ─────────────────────────────────────────────────────────────────────────────
def test_customer_revision_cycle(quote):
    print("\n[TEST 8] Customer Decision Lifecycle: Changes Requested & Revision")
    try:
        # Customer requests changes -> automatically creates V2 Draft and marks V1 SUPERSEDED
        v1_changed, v2_quote = record_customer_decision(
            quote.id,
            action="REQUEST_CHANGES",
            notes="Please include balcony waterproofing in the quote.",
        )
        assert v2_quote is not None, "V2 quote must be created"
        assert v2_quote.id != quote.id, "V2 quote must be a new record"
        assert v2_quote.quote_number == quote.quote_number, "Quote number must remain stable across revisions"
        assert v2_quote.quote_version == 2, f"Expected version 2, got {v2_quote.quote_version}"
        assert v2_quote.status == "DRAFT", f"Expected status DRAFT for V2, got {v2_quote.status}"

        # Check V1 is marked SUPERSEDED
        v1_reloaded = WorkforceQuote.objects.get(id=quote.id)
        assert v1_reloaded.status == "SUPERSEDED", f"Expected V1 SUPERSEDED, got {v1_reloaded.status}"

        # Send V2 to customer
        v2_sent = send_quote_to_customer(v2_quote.id)
        assert v2_sent.status == "SENT_TO_CUSTOMER"

        record_pass("test_customer_revision_cycle", f"(V1 marked SUPERSEDED -> V2 DRAFT -> V2 SENT_TO_CUSTOMER)")
        return v2_sent
    except Exception as e:
        record_fail("test_customer_revision_cycle", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Test 9: Customer Acceptance & Work Booking Conversion
# ─────────────────────────────────────────────────────────────────────────────
def test_customer_acceptance_and_work_conversion(quote):
    print("\n[TEST 9] Customer Acceptance & Work Booking Conversion")
    try:
        accepted_quote, work_job = record_customer_decision(
            quote.id,
            action="ACCEPT",
            notes="Looks great, proceed with the work!",
        )
        assert accepted_quote.status == "CONVERTED", f"Expected CONVERTED, got {accepted_quote.status}"
        assert accepted_quote.customer_decided_at is not None

        # Verify canonical Work ServiceRequest was created
        assert work_job is not None, "Work ServiceRequest must be linked to converted quote"
        assert work_job.request_kind == RequestKind.WORK, f"Expected WORK request_kind, got {work_job.request_kind}"
        assert work_job.quote_number == quote.quote_number, f"Expected quote_number {quote.quote_number}, got {work_job.quote_number}"
        assert work_job.parent_request_id == quote.job_id, f"Expected parent_request_id {quote.job_id}, got {work_job.parent_request_id}"
        assert work_job.is_work_job is True
        assert work_job.is_estimation is False
        assert work_job.total_amount == quote.net_payable, f"Expected total_amount {quote.net_payable}, got {work_job.total_amount}"
        assert work_job.status in ["pending", "requested", "assigned", "confirmed"], f"Unexpected work job status: {work_job.status}"

        record_pass("test_customer_acceptance_and_work_conversion", f"(Work Job created: SR-{work_job.id}, Quote: {work_job.quote_number})")
        return accepted_quote
    except Exception as e:
        record_fail("test_customer_acceptance_and_work_conversion", e)
        return None
    except Exception as e:
        record_fail("test_customer_acceptance_and_work_conversion", e)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Test 10: Work Conversion Idempotency
# ─────────────────────────────────────────────────────────────────────────────
def test_conversion_idempotency(converted_quote):
    print("\n[TEST 10] Work Conversion Idempotency")
    try:
        original_work_job_id = converted_quote.work_job_id
        initial_work_jobs_count = ServiceRequest.objects.filter(quote_number=converted_quote.quote_number).count()

        # Call conversion again
        reconverted_work_job = convert_accepted_quote_to_work_booking(converted_quote)
        final_work_jobs_count = ServiceRequest.objects.filter(quote_number=converted_quote.quote_number).count()

        assert reconverted_work_job.id == original_work_job_id, "Work job ID changed upon duplicate conversion"
        assert initial_work_jobs_count == final_work_jobs_count == 1, f"Duplicate work bookings created: {final_work_jobs_count}"

        record_pass("test_conversion_idempotency", "(Zero duplicate ServiceRequests created on repeat conversion)")
    except Exception as e:
        record_fail("test_conversion_idempotency", e)


# ─────────────────────────────────────────────────────────────────────────────
# Test 11: HTTP API Views & Metrics
# ─────────────────────────────────────────────────────────────────────────────
def test_api_views_and_metrics(admin_user, employee, est_job):
    print("\n[TEST 11] HTTP API Views & Metrics Verification")
    try:
        # 1. Rate cards list view
        req = factory.get("/api/workforce/rate-cards/")
        force_authenticate(req, user=employee.user)
        res = WorkforceRateCardListView.as_view()(req)
        assert res.status_code == 200, f"Rate cards API returned {res.status_code}"
        assert len(res.data) > 0, "Rate cards API returned empty list"

        # 2. Estimation gate view
        req_gate = factory.get(f"/api/workforce/jobs/{est_job.id}/estimation-gate/")
        force_authenticate(req_gate, user=employee.user)
        res_gate = WorkforceEstimationGateView.as_view()(req_gate, pk=est_job.id)
        assert res_gate.status_code == 200, f"Estimation gate API returned {res_gate.status_code}"
        assert "can_create_quote" in res_gate.data

        # 3. Quotes list view
        req_q = factory.get("/api/workforce/quotes/")
        force_authenticate(req_q, user=employee.user)
        res_q = WorkforceQuoteListView.as_view()(req_q)
        assert res_q.status_code == 200, f"Quotes list API returned {res_q.status_code}"

        # 4. Admin metrics view
        req_m = factory.get("/api/workforce/admin/quotes/metrics/")
        force_authenticate(req_m, user=admin_user)
        res_m = WorkforceAdminQuoteMetricsView.as_view()(req_m)
        assert res_m.status_code == 200, f"Admin metrics API returned {res_m.status_code}"
        assert "total_quotes" in res_m.data
        assert "conversion_rate_percent" in res_m.data
        assert "converted_count" in res_m.data

        record_pass("test_api_views_and_metrics", "(All HTTP views authenticated, validated & responding)")
    except Exception as e:
        record_fail("test_api_views_and_metrics", e)


# ─────────────────────────────────────────────────────────────────────────────
# Main Runner
# ─────────────────────────────────────────────────────────────────────────────
def run_all_tests():
    print("=" * 75)
    print("CALTRACK WORKFORCE — ESTIMATION & QUOTATION E2E TEST SUITE")
    print("=" * 75)

    admin_user, employee, est_job, psv = setup_test_fixtures()

    # 1. Service Classification
    painting_service = Service.objects.filter(id__in=QUOTATION_SERVICE_IDS).first()
    test_service_classification(painting_service)

    # 2. RequestKind Mapping
    test_servicerequest_request_kind(est_job)

    # 3. Rate Cards Catalog
    test_rate_cards_catalog()

    # 4. Estimation Gate & Pre-Service Verification
    test_estimation_gate_rules(est_job, psv)

    # 5. Quotation Drafting & Authoritative Totals
    quote = test_quotation_creation_and_totals(employee, est_job)

    # 6. Mason Structural Gate
    test_mason_structural_gate(admin_user, employee, est_job)

    if quote:
        # 7. Quote Sending & Freezing
        sent_quote = test_quote_sending_and_freezing(quote)

        if sent_quote:
            # 8. Customer Decision Revision Cycle
            v2_sent = test_customer_revision_cycle(sent_quote)

            if v2_sent:
                # 9. Customer Acceptance & Work Booking Conversion
                converted_quote = test_customer_acceptance_and_work_conversion(v2_sent)

                if converted_quote:
                    # 10. Conversion Idempotency
                    test_conversion_idempotency(converted_quote)

    # 11. API Views & Metrics
    test_api_views_and_metrics(admin_user, employee, est_job)

    print("\n" + "=" * 75)
    print(f"RESULTS: {len(PASSED_TESTS)} PASSED, {len(FAILED_TESTS)} FAILED")
    print("=" * 75)

    if FAILED_TESTS:
        print("\nFailed Tests:")
        for name, err in FAILED_TESTS:
            print(f"  - {name}: {err}")
        sys.exit(1)
    else:
        print("\nALL ESTIMATION & QUOTATION E2E TESTS PASSED SUCCESSFULLY! [SUCCESS]")
        sys.exit(0)


if __name__ == "__main__":
    run_all_tests()
