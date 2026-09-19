import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from service_requests.models import ServiceRequest
from employees.models import Employee
from workforce_api.services.automatic_dispatch import (
    get_eligible_candidates,
    check_candidate_eligibility,
    DISPATCHABLE_STATUSES,
)

e = Employee.objects.filter(user__username="technician01").first()
print(f"Technician01: id={e.id}, is_online={e.is_online}, avail={e.current_availability}, company={e.company_id}")
loc = getattr(e.user, "last_known_location", None)
print(f"Technician01 loc: {loc}")
print(f"Technician01 services: {(e.bank_details or {}).get('onboarding', {}).get('services', [])}")

print("\n=== EVALUATING DISPATCHABLE JOBS FOR technician01 ===")
for sr in ServiceRequest.objects.filter(status__in=DISPATCHABLE_STATUSES).order_by("-id")[:10]:
    print(f"\nJob #{sr.id} (cat={sr.service_category}, status={sr.status}, company={sr.company_id}):")
    # 1. Direct eligibility check on technician01
    eligible, reason, checks = check_candidate_eligibility(e, sr.service_category, sr)
    print(f"  check_candidate_eligibility for technician01: eligible={eligible}, reason='{reason}', checks={checks}")
    try:
        candidates = get_eligible_candidates(sr.id)
        print(f"  Total eligible candidates in pool: {len(candidates)}")
        matching_t1 = [c for c in candidates if c.get("employee_id") == e.id]
        if matching_t1:
            print(f"  -> MATCHED technician01! Distance: {matching_t1[0].get('distance_km')}km")
        else:
            print("  -> technician01 NOT in eligible pool.")
    except Exception as exc:
        print(f"  -> Error: {exc}")
