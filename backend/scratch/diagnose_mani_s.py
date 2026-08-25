"""
backend/scratch/diagnose_mani_s.py
"""
import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceJobOffer
from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    get_eligible_candidates,
    check_candidate_eligibility,
    DISPATCHABLE_STATUSES,
)
from workforce_api.services.geo_spatial import calculate_distance_km

User = get_user_model()

print("="*80)
print("DIAGNOSING MANI S AND EXISTING BOOKINGS IN LIVE POSTGRES")
print("="*80)

# 1. Find Mani S
users = User.objects.filter(first_name__icontains="Mani") | User.objects.filter(username__icontains="mani") | User.objects.filter(last_name__icontains="Mani")
if not users.exists():
    users = User.objects.filter(role="employee")[:5]

for u in users:
    emp = getattr(u, "employee_profile", None)
    if not emp:
        emp = Employee.objects.filter(user=u).first()
    print(f"\nUser: id={u.id}, username={u.username}, name='{u.first_name} {u.last_name}', email={u.email}, role={u.role}")
    print(f"  - User location: {u.last_known_location}")
    if emp:
        print(f"  - Employee: id={emp.id}, company_id={emp.company_id}, is_active={emp.is_active}, is_online={emp.is_online}, current_availability={emp.current_availability}")
        onboarding = (emp.bank_details or {}).get("onboarding", {})
        print(f"  - Onboarding status: {onboarding.get('status')}")
        svcs = onboarding.get("services", [])
        print(f"  - Total onboarding services: {len(svcs)}")
        if svcs:
            print(f"  - Sample services: {[s.get('name') or s.get('category') for s in svcs[:5]]}")

# 2. Inspect all non-completed ServiceRequest records in the DB
print("\n" + "-"*80)
print("RECENT SERVICE REQUESTS IN DATABASE:")
print("-"*80)
srs = ServiceRequest.objects.order_by("-id")[:15]
for sr in srs:
    print(f"\nJob #{sr.id} ({sr.request_id}):")
    print(f"  - Service Category: '{sr.service_category}' | Issue Title: '{sr.issue_title}'")
    print(f"  - Status: '{sr.status}' (in DISPATCHABLE: {sr.status in DISPATCHABLE_STATUSES})")
    print(f"  - Company ID: {sr.company_id}")
    print(f"  - Assigned Employee ID: {sr.assigned_employee_id}")
    print(f"  - Coordinates: ({sr.latitude}, {sr.longitude})")
    print(f"  - Created At: {sr.created_at}")

    # Check offers for this job
    offers = WorkforceJobOffer.objects.filter(job=sr).order_by("-id")
    print(f"  - Total Offers in DB: {offers.count()}")
    for o in offers[:3]:
        print(f"    * Offer #{o.id} -> Emp #{o.employee_id}, Status: {o.status}, Offered At: {o.offered_at}, Expires At: {o.expires_at}")

# 3. If Mani S found and a dispatchable job exists, run candidate evaluation on Mani S
mani_emp = Employee.objects.filter(user__first_name__icontains="Mani").first() or Employee.objects.filter(user__username__icontains="mani").first()
if mani_emp:
    print("\n" + "-"*80)
    print(f"EVALUATING ELIGIBILITY OF MANI S (Emp #{mani_emp.id}) AGAINST PENDING JOBS:")
    print("-"*80)
    for sr in srs:
        if sr.status in DISPATCHABLE_STATUSES and sr.assigned_employee_id is None:
            print(f"\nEvaluating Job #{sr.id} ('{sr.service_category}' / '{sr.issue_title}'):")
            # Distance
            last_loc = getattr(mani_emp.user, "last_known_location", None) or {}
            emp_lat = last_loc.get("latitude") or last_loc.get("lat")
            emp_lon = last_loc.get("longitude") or last_loc.get("lng") or last_loc.get("lon")
            if emp_lat and emp_lon and sr.latitude and sr.longitude:
                dist = calculate_distance_km(float(sr.latitude), float(sr.longitude), float(emp_lat), float(emp_lon))
                print(f"  * Distance: {dist:.2f} km")
            else:
                print(f"  * Distance: CANNOT CALCULATE (emp_loc={last_loc}, sr_loc=({sr.latitude}, {sr.longitude}))")

            is_elig, reason, gates = check_candidate_eligibility(mani_emp, sr.service_category, check_workload=False)
            print(f"  * Category '{sr.service_category}' Eligibility: {is_elig}, Reason: {reason}")
            print(f"  * Gates: {gates}")
            if sr.issue_title:
                is_elig_t, reason_t, gates_t = check_candidate_eligibility(mani_emp, sr.issue_title, check_workload=False)
                print(f"  * Title '{sr.issue_title}' Eligibility: {is_elig_t}, Reason: {reason_t}")

            # Run get_eligible_candidates
            candidates = get_eligible_candidates(sr)
            print(f"  * get_eligible_candidates found: {len(candidates)} candidates")
            for c in candidates:
                print(f"    - Candidate: Emp #{c['employee'].id} ({c['employee'].user.username}), Dist: {c['distance_km']:.2f}km, Wave: {c['wave_number']}")

            # Try reconcile_booking_for_dispatch
            try:
                ok, msg = reconcile_booking_for_dispatch(sr)
                print(f"  * reconcile_booking_for_dispatch result: ok={ok}, msg='{msg}'")
            except Exception as e:
                import traceback
                print(f"  * reconcile_booking_for_dispatch EXCEPTION: {e}")
                traceback.print_exc()

    from django.test import Client
    client = Client()
    client.force_login(mani_emp.user)
    resp = client.get("/api/workforce/jobs/?status=active")
    print(f"\nActive Jobs API call for Mani S (status={resp.status_code}):")
    print(f"Returned {len(resp.json())} jobs: {resp.json()}")
