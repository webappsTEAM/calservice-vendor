import os
import django
import uuid
from decimal import Decimal
from datetime import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest, EmployeeJob
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceEmployeeSchedule,
)
from workforce_api.views import WorkforceJobListView, WorkforceJobAcceptOfferView
from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    canonical_service_match,
)

User = get_user_model()


def run_verification():
    print("=" * 80)
    print("STARTING AUTHORITATIVE PARTNER & COMPANY DISPATCH & VISIBILITY VERIFICATION")
    print("=" * 80)

    factory = APIRequestFactory()
    uid = uuid.uuid4().hex[:6]

    def create_test_tech(username, email, service_name, company=None, lat=12.9716, lon=77.5946):
        if company is None:
            company = Company.objects.create(company_name=f"Independent_{username}_{uid}", is_active=True)
        user = User.objects.create_user(
            username=f"{username}_{uid}",
            email=f"{email}_{uid}@example.com",
            password="TestPassword123!",
            role="technician",
            is_active=True,
            last_known_location={"latitude": lat, "longitude": lon, "lat": lat, "lng": lon, "timestamp": timezone.now().isoformat()}
        )
        emp = Employee.objects.create(
            user=user,
            employee_id=f"EMP-{username}_{uid}",
            company=company,
            is_active=True,
            is_online=True,
            current_availability="online",
            bank_details={
                "onboarding": {
                    "status": "approved",
                    "step1": "completed",
                    "step2": "completed",
                    "step3": "completed",
                    "documents": {"aadhaar": {"status": "approved"}},
                    "services": [{"name": service_name, "category": service_name, "status": "approved"}],
                }
            },
            service_roles=[service_name],
        )
        for dow in range(7):
            WorkforceEmployeeSchedule.objects.create(
                employee=emp,
                company=company,
                day_of_week=dow,
                start_time=time(0, 0),
                end_time=time(23, 59),
                is_working_day=True,
            )
        return user, emp

    print("\n--- TEST CASE D: Service False Positives (Domain Protection) ---")
    d_cases = [
        ("Electrical Repair", ["Plumbing Repair"], False),
        ("AC Repair", ["Electrical Repair"], False),
        ("Kitchen Cleaning", ["AC Deep Cleaning & Anti-Bacterial Foam"], False),
        ("Electrical Installation", ["Plumbing Installation"], False),
        ("5/15A Socket Replacement", ["Switchboard Repair & Installation"], True),
        ("Kitchen Cleaning", ["Full Kitchen cleaning(Basic)"], True),
        ("Plumbing", ["Tap Repair"], True),
        ("AC Not Cooling", ["AC Regular Servicing & Jet Clean"], True),
        ("Interior Painting", ["Exterior Painting"], True),
        ("Interior Painting", ["Switchboard Repair & Installation"], False),
    ]
    for req_title, tech_services, expected_match in d_cases:
        matched, method, matched_term = canonical_service_match(req_title, tech_services, [])
        assert matched == expected_match, f"Failed Case D: '{req_title}' vs {tech_services} got {matched} (expected {expected_match}) via {method}"
        print(f"  [PASS] '{req_title}' vs {tech_services} -> matched={matched} via {method}")

    print("\n--- TEST CASE A: Independent Partners Isolation (No Company) ---")
    user_elec_indep, emp_elec_indep = create_test_tech("indep_elec", "indep_elec", "Switchboard Repair & Installation", company=None)
    user_clean_indep, emp_clean_indep = create_test_tech("indep_clean", "indep_clean", "Full Kitchen cleaning(Basic)", company=None)
    user_plumb_indep, emp_plumb_indep = create_test_tech("indep_plumb", "indep_plumb", "Tap Repair", company=None)

    booking_elec = ServiceRequest.objects.create(
        request_id=f"IND-EL-{uid}",
        status="confirmed",
        service_category="Electrical",
        issue_title="5/15A Socket Replacement",
        latitude=Decimal("12.9720"),
        longitude=Decimal("77.5950"),
        preferred_date=timezone.localdate(),
        preferred_time="10:00 AM",
        total_amount=Decimal("250.00"),
        payment_method="cash",
        payment_status="pending",
        company=None,
    )
    booking_clean = ServiceRequest.objects.create(
        request_id=f"IND-KC-{uid}",
        status="confirmed",
        service_category="kitchen_cleaning",
        issue_title="Full Kitchen cleaning(Basic)",
        latitude=Decimal("12.9720"),
        longitude=Decimal("77.5950"),
        preferred_date=timezone.localdate(),
        preferred_time="11:00 AM",
        total_amount=Decimal("799.00"),
        payment_method="cash",
        payment_status="pending",
        company=None,
    )
    booking_plumb = ServiceRequest.objects.create(
        request_id=f"IND-PL-{uid}",
        status="confirmed",
        service_category="Plumbing",
        issue_title="Tap Repair",
        latitude=Decimal("12.9720"),
        longitude=Decimal("77.5950"),
        preferred_date=timezone.localdate(),
        preferred_time="12:00 PM",
        total_amount=Decimal("300.00"),
        payment_method="cash",
        payment_status="pending",
        company=None,
    )

    reconcile_booking_for_dispatch(booking_elec)
    reconcile_booking_for_dispatch(booking_clean)
    reconcile_booking_for_dispatch(booking_plumb)

    # Verify Partner A receives offer for Electrical only
    elec_offers = list(WorkforceJobOffer.objects.filter(employee=emp_elec_indep, status="OFFERED").values_list("job_id", flat=True))
    clean_offers = list(WorkforceJobOffer.objects.filter(employee=emp_clean_indep, status="OFFERED").values_list("job_id", flat=True))
    plumb_offers = list(WorkforceJobOffer.objects.filter(employee=emp_plumb_indep, status="OFFERED").values_list("job_id", flat=True))

    assert booking_elec.id in elec_offers, f"Partner A (Electrical) must receive offer for Electrical #{booking_elec.id}, got {elec_offers}"
    assert booking_clean.id not in elec_offers, "Partner A must NOT receive Kitchen Cleaning offer!"
    assert booking_plumb.id not in elec_offers, "Partner A must NOT receive Plumbing offer!"

    assert booking_clean.id in clean_offers, f"Partner B (Cleaning) must receive offer for Kitchen Cleaning #{booking_clean.id}"
    assert booking_elec.id not in clean_offers, "Partner B must NOT receive Electrical offer!"

    assert booking_plumb.id in plumb_offers, f"Partner C (Plumbing) must receive offer for Plumbing #{booking_plumb.id}"
    assert booking_elec.id not in plumb_offers, "Partner C must NOT receive Electrical offer!"

    # Query Active Jobs API for each partner
    req_a = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_a, user=user_elec_indep)
    resp_a = WorkforceJobListView.as_view()(req_a)
    job_ids_a = [j["id"] for j in resp_a.data]
    assert job_ids_a == [booking_elec.id], f"Partner A Active Jobs must be [{booking_elec.id}], got {job_ids_a}"
    print(f"  [PASS] Partner A Active Jobs API returned: {job_ids_a} (Electrical only)")

    req_b = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_b, user=user_clean_indep)
    resp_b = WorkforceJobListView.as_view()(req_b)
    job_ids_b = [j["id"] for j in resp_b.data]
    assert job_ids_b == [booking_clean.id], f"Partner B Active Jobs must be [{booking_clean.id}], got {job_ids_b}"
    print(f"  [PASS] Partner B Active Jobs API returned: {job_ids_b} (Kitchen Cleaning only)")

    req_c = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_c, user=user_plumb_indep)
    resp_c = WorkforceJobListView.as_view()(req_c)
    job_ids_c = [j["id"] for j in resp_c.data]
    assert job_ids_c == [booking_plumb.id], f"Partner C Active Jobs must be [{booking_plumb.id}], got {job_ids_c}"
    print(f"  [PASS] Partner C Active Jobs API returned: {job_ids_c} (Plumbing only)")

    print("\n--- TEST CASE B: Company Partner Multi-Technician Isolation ---")
    company_x = Company.objects.create(company_name=f"Vendor X {uid}", is_active=True)
    user_tech_elec, emp_tech_elec = create_test_tech("vendor_elec", "vendor_elec", "Switchboard Repair & Installation", company=company_x)
    user_tech_clean, emp_tech_clean = create_test_tech("vendor_clean", "vendor_clean", "Full Kitchen cleaning(Basic)", company=company_x)
    user_tech_plumb, emp_tech_plumb = create_test_tech("vendor_plumb", "vendor_plumb", "Tap Repair", company=company_x)

    booking_company_elec = ServiceRequest.objects.create(
        request_id=f"CO-EL-{uid}",
        status="confirmed",
        service_category="Electrical",
        issue_title="5/15A Socket Replacement",
        latitude=Decimal("12.9720"),
        longitude=Decimal("77.5950"),
        preferred_date=timezone.localdate(),
        preferred_time="02:00 PM",
        total_amount=Decimal("350.00"),
        payment_method="cash",
        payment_status="pending",
        company=company_x,
    )
    reconcile_booking_for_dispatch(booking_company_elec)

    req_tech_a = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_tech_a, user=user_tech_elec)
    resp_tech_a = WorkforceJobListView.as_view()(req_tech_a)
    job_ids_tech_a = [j["id"] for j in resp_tech_a.data]
    assert job_ids_tech_a == [booking_company_elec.id], f"Company Tech A (Electrical) must see [{booking_company_elec.id}], got {job_ids_tech_a}"
    print(f"  [PASS] Company Tech A sees only Electrical job: {job_ids_tech_a}")

    req_tech_b = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_tech_b, user=user_tech_clean)
    resp_tech_b = WorkforceJobListView.as_view()(req_tech_b)
    job_ids_tech_b = [j["id"] for j in resp_tech_b.data]
    assert job_ids_tech_b == [], f"Company Tech B (Cleaning) must see [], got {job_ids_tech_b} (NO COMPANY LEAKAGE!)"
    print(f"  [PASS] Company Tech B sees empty active jobs (NO LEAKAGE): {job_ids_tech_b}")

    req_tech_c = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_tech_c, user=user_tech_plumb)
    resp_tech_c = WorkforceJobListView.as_view()(req_tech_c)
    job_ids_tech_c = [j["id"] for j in resp_tech_c.data]
    assert job_ids_tech_c == [], f"Company Tech C (Plumbing) must see [], got {job_ids_tech_c} (NO COMPANY LEAKAGE!)"
    print(f"  [PASS] Company Tech C sees empty active jobs (NO LEAKAGE): {job_ids_tech_c}")

    print("\n--- TEST CASE C: Marketplace company_id=NULL Visibility Rule ---")
    user_other, emp_other = create_test_tech("other_tech", "other_tech", "Switchboard Repair & Installation", company=None, lat=12.5000, lon=77.5000)
    req_other = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_other, user=user_other)
    resp_other = WorkforceJobListView.as_view()(req_other)
    assert len(resp_other.data) == 0, f"Unrelated technician must NOT see unoffered marketplace jobs, got {[j['id'] for j in resp_other.data]}"
    print("  [PASS] Marketplace company_id=NULL job is NOT visible to non-offered technician.")

    print("\n--- TEST CASE E: No Job State (Empty Invariant) ---")
    user_empty, emp_empty = create_test_tech("empty_tech", "empty_tech", "Carpentry", company=None)
    req_empty = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_empty, user=user_empty)
    resp_empty = WorkforceJobListView.as_view()(req_empty)
    assert resp_empty.data == [], f"Technician without offers/assignments must receive [], got {resp_empty.data}"
    print("  [PASS] Empty state strictly verified: API returned [].")

    print("\n" + "=" * 80)
    print("ALL VERIFICATION CASES (A, B, C, D, E) PASSED PERFECTLY WITH ZERO ERRORS!")
    print("=" * 80)


if __name__ == "__main__":
    run_verification()
