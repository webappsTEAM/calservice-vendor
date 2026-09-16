import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from workforce_api.services.automatic_dispatch import canonical_service_match
from service_requests.models import ServiceRequest

def test_empty_service_fails_closed():
    is_match, method, _ = canonical_service_match("", ["AC Repair"], ["HVAC"])
    assert not is_match, f"Expected False, got {is_match}"
    assert method == "EMPTY_SERVICE_FAIL_CLOSED"
    print("PASS: Empty service fails closed.")

def test_ac_vs_painter_service_matching():
    # AC technician has AC service and skills
    ac_services = ["AC Repair & Diagnostics", "AC Installation"]
    ac_skills = ["HVAC"]

    # Painter has Painting
    painter_services = ["Full House Painting", "Interior Painting"]
    painter_skills = ["Surface Preparation", "Wall Painting"]

    # 1. AC job to AC tech -> PASS
    match_ac, _, _ = canonical_service_match("AC Repair", ac_services, ac_skills)
    assert match_ac, "AC tech should match AC Repair"

    # 2. AC job to Painter -> FAIL
    match_painter, _, _ = canonical_service_match("AC Repair", painter_services, painter_skills)
    assert not match_painter, "Painter should NOT match AC Repair"

    # 3. Painting job to AC tech -> FAIL
    match_ac_painting, _, _ = canonical_service_match("Painting", ac_services, ac_skills)
    assert not match_ac_painting, "AC tech should NOT match Painting"

    print("PASS: AC technician vs Painter strict isolation verified.")

def test_presence_and_jobs_get_code_audit():
    # Verify views.py has no thread spawns for reconsider_jobs_for_employee
    views_path = os.path.join(os.path.dirname(__file__), "workforce_api", "views.py")
    with open(views_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "threading.Thread(target=reconsider_jobs_for_employee" not in content, "reconsider_jobs_for_employee thread spawn still in views.py!"
    assert "threading.Thread(target=expire_and_reassign_offers" not in content, "expire_and_reassign_offers thread spawn still in views.py!"
    print("PASS: views.py verified free of dispatch/reconsider thread spawns.")

def test_models_save_no_sync_fallback():
    models_path = os.path.join(os.path.dirname(__file__), "service_requests", "models.py")
    with open(models_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "reconcile_booking_for_dispatch(_job, use_redis_geo=False)" not in content, "Synchronous dispatch fallback still in ServiceRequest.save!"
    print("PASS: ServiceRequest.save verified free of synchronous dispatch fallback.")

if __name__ == "__main__":
    test_empty_service_fails_closed()
    test_ac_vs_painter_service_matching()
    test_presence_and_jobs_get_code_audit()
    test_models_save_no_sync_fallback()
    print("ALL P0 CHECKS PASSED!")
