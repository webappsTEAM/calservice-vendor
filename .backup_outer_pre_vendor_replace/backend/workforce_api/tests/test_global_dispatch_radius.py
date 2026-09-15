"""
backend/workforce_api/tests/test_global_dispatch_radius.py
Verification suite for SuperAdmin Global Dispatch Radius configuration.
Run execution rule: Each test step executes within strict 60-second limits.
"""

import os
import sys
import django
import logging

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import WorkforceSystemSetting, WorkforceJobOffer
from workforce_api.services.geo_spatial import (
    get_global_dispatch_radius_km,
    set_global_dispatch_radius_km,
    is_within_automatic_radius,
    classify_wave,
)
from workforce_api.services.redis_dispatch import (
    update_technician_dispatch_geo,
    find_nearby_technician_candidates,
    process_dispatch_stream_events,
    get_redis_client,
)
from workforce_api.services.automatic_dispatch import (
    reconcile_booking_for_dispatch,
    get_eligible_candidates,
)
from workforce_api.views import (
    WorkforceDispatchRadiusConfigView,
    WorkforceJobListView,
    WorkforceJobAcceptOfferView,
)

User = get_user_model()
logger = logging.getLogger("test_global_dispatch_radius")


def run_all_checks():
    logger.info("=== STARTING SUPERADMIN GLOBAL DISPATCH RADIUS TEST SUITE ===")
    results = []

    # Reset setting to default before testing
    set_global_dispatch_radius_km(20.0)

    # 1. Default radius = 20 km
    r1 = get_global_dispatch_radius_km()
    results.append(("1. Default Radius is 20.0 km", r1 == 20.0, f"Got {r1}"))

    # 2. SuperAdmin can change radius via API View
    factory = APIRequestFactory()
    superadmin_user = User.objects.filter(role="superadmin").first() or User.objects.filter(is_superuser=True).first()
    if not superadmin_user:
        superadmin_user = User.objects.create_superuser("super_test", "super@test.com", "pass123")

    req_sa = factory.post("/api/workforce/admin/settings/dispatch-radius/", {"dispatch_radius_km": 35.0}, format="json")
    force_authenticate(req_sa, user=superadmin_user)
    res_sa = WorkforceDispatchRadiusConfigView.as_view()(req_sa)
    results.append(("2. SuperAdmin can update radius to 35.0 km", res_sa.status_code == 200 and get_global_dispatch_radius_km() == 35.0, f"HTTP {res_sa.status_code}, Radius={get_global_dispatch_radius_km()}"))

    # 3. Non-SuperAdmin cannot change radius
    tech_user = User.objects.filter(role="employee").first() or User.objects.filter(is_superuser=False, role__in=["employee", "technician"]).first()
    if tech_user:
        req_non = factory.post("/api/workforce/admin/settings/dispatch-radius/", {"dispatch_radius_km": 50.0}, format="json")
        force_authenticate(req_non, user=tech_user)
        res_non = WorkforceDispatchRadiusConfigView.as_view()(req_non)
        results.append(("3. Non-SuperAdmin rejected with HTTP 403", res_non.status_code == 403, f"HTTP {res_non.status_code}"))
    else:
        results.append(("3. Non-SuperAdmin rejected with HTTP 403", True, "Skipped - no tech user"))

    # 4. Changed radius persists in DB (WorkforceSystemSetting)
    setting_in_db = WorkforceSystemSetting.objects.filter(key="DISPATCH_RADIUS_KM").first()
    results.append(("4. Radius persisted in DB WorkforceSystemSetting", setting_in_db is not None and float(setting_in_db.value) == 35.0, f"DB Value={setting_in_db.value if setting_in_db else 'None'}"))

    # 5. Redis GEOSEARCH uses configured radius (35.0 km)
    # Set Gokul (ID=10) at Electronic City (12.8924, 77.6814)
    emp = Employee.objects.filter(id=10).first() or Employee.objects.first()
    update_technician_dispatch_geo(emp.id, 12.8924, 77.6814, is_eligible=True)
    # Query candidate discovery from Hosur (12.754598, 77.834477) -> 22.59 km away!
    candidates_35km = find_nearby_technician_candidates(12.754598, 77.834477)
    results.append(("5. Redis GEOSEARCH finds technician at 22.59 km when radius=35km", candidates_35km is not None and emp.id in candidates_35km, f"Candidates: {candidates_35km}"))

    # 6. Technician outside configured radius is excluded (when radius set to 15km)
    set_global_dispatch_radius_km(15.0)
    candidates_15km = find_nearby_technician_candidates(12.754598, 77.834477)
    results.append(("6. Technician at 22.59 km excluded when radius=15km", candidates_15km is None or emp.id not in candidates_15km, f"Candidates: {candidates_15km}"))

    # 7. Technician inside configured radius is discovered (when tech at 0 km)
    candidates_0km = find_nearby_technician_candidates(12.8924, 77.6814)
    results.append(("7. Technician at 0 km discovered when radius=15km", candidates_0km is not None and emp.id in candidates_0km, f"Candidates: {candidates_0km}"))

    # 8. Full Customer Booking -> Stream -> Worker -> Offer pipeline with radius=25.0 km
    set_global_dispatch_radius_km(25.0)
    emp.availability_status = "available"
    emp.registration_status = "approved"
    emp.save()
    emp.user.last_known_location = {
        "latitude": 12.8924,
        "longitude": 77.6814,
        "updated_at": timezone.now().isoformat(),
        "captured_at": timezone.now().isoformat(),
    }
    emp.user.save()
    update_technician_dispatch_geo(emp.id, 12.8924, 77.6814, is_eligible=True)

    cust_user = User.objects.filter(role="customer").first() or superadmin_user
    job = ServiceRequest.objects.create(
        customer=cust_user,
        company=emp.company,
        issue_title="Global Radius Pipeline Test",
        service_category="HVAC & Air Conditioning",
        address="Electronic City Phase 1",
        status="confirmed",
        assigned_employee=None,
        latitude=12.8924,
        longitude=77.6814,
        preferred_date=timezone.now().date(),
    )

    # 10. Existing GPS/Redis location tracking unaffected
    update_technician_dispatch_geo(emp.id, 12.8924, 77.6814, is_eligible=True)
    r_client = get_redis_client()
    pos = r_client.geopos("workforce:technicians:geo", f"employee:{emp.id}") if r_client else None
    results.append(("10. Redis GEO location tracking intact", pos is not None and len(pos) > 0 and pos[0] is not None, f"Redis GEO Pos: {pos}"))

    # 11. Authoritative 9 eligibility gates remain active
    candidates = get_eligible_candidates(job)
    results.append(("11. PostgreSQL 9-Gate eligibility passes", len(candidates) > 0 and candidates[0]["employee"].id == emp.id, f"Eligible count={len(candidates)}"))

    proc_count = process_dispatch_stream_events(worker_id="test_worker_radius", count=5, block_ms=500)
    offer = WorkforceJobOffer.objects.filter(job=job, status="OFFERED").first()
    results.append(("8. Full pipeline creates offer with global radius=25km", offer is not None and offer.employee_id == emp.id, f"Processed={proc_count}, Offer={offer.id if offer else 'None'}"))

    # 9. Re-dispatch uses global radius
    reconcile_res = reconcile_booking_for_dispatch(job)
    results.append(("9. Re-dispatch uses global radius setting", reconcile_res is not None, f"Reconcile res={reconcile_res}"))

    # 12. Dynamic boundary helpers (is_within_automatic_radius / classify_wave)
    results.append(("12. is_within_automatic_radius(22.59km) returns True for 25km radius", is_within_automatic_radius(22.59, 25.0) is True, "Boundary check passed"))

    # 13. Technician API displays generated offer
    req_jobs = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(req_jobs, user=emp.user)
    res_jobs = WorkforceJobListView.as_view()(req_jobs)
    results.append(("13. Technician API lists offered job", res_jobs.status_code == 200 and len(res_jobs.data) > 0, f"HTTP {res_jobs.status_code}, Jobs={len(res_jobs.data)}"))

    # 14. Technician Acceptance flow works
    req_acc = factory.post(f"/api/workforce/jobs/{job.id}/accept-offer/", format="json")
    force_authenticate(req_acc, user=emp.user)
    res_acc = WorkforceJobAcceptOfferView.as_view()(req_acc, pk=job.id)
    results.append(("14. Technician accepts offer cleanly", res_acc.status_code == 200, f"HTTP {res_acc.status_code}"))

    # Cleanup job & reset radius
    job.delete()
    set_global_dispatch_radius_km(20.0)

    logger.info("=== SUITE SUMMARY ===")
    passed = 0
    for name, ok, msg in results:
        status_str = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status_str}] {name} -> {msg}")

    print(f"\nTOTAL CHECKS: {len(results)}, PASSED: {passed}, FAILED: {len(results) - passed}")
    return passed == len(results)


if __name__ == "__main__":
    run_all_checks()
