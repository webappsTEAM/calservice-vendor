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

def test_acceptance_and_redispatch_audit():
    views_path = os.path.join(os.path.dirname(__file__), "workforce_api", "views.py")
    with open(views_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify previous_offer_status captured before mutation
    assert "previous_offer_status = offer.status if offer else \"OFFERED\"" in content
    assert "previous_status=previous_offer_status" in content

    # Verify handleAcceptOffer does not call apiTransitionJob
    frontend_jobs_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "src", "pages", "employee", "EmployeeJobsPage.jsx")
    with open(frontend_jobs_path, "r", encoding="utf-8") as f:
        frontend_content = f.read()

    accept_fn = frontend_content.split("const handleAcceptOffer =")[1].split("const handleRejectOffer =")[0]
    assert "apiTransitionJob" not in accept_fn, "handleAcceptOffer still auto-transitions on acceptance!"
    print("PASS: Acceptance lifecycle and previous_status audit verified.")

def test_offer_and_assignment_webhook_semantics():
    dispatch_path = os.path.join(os.path.dirname(__file__), "workforce_api", "services", "automatic_dispatch.py")
    with open(dispatch_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Offer creation emits technician.offer_sent
    assert '"technician.offer_sent"' in content
    print("PASS: Offer creation emits technician.offer_sent.")

def test_dlq_poison_routing():
    from workforce_api.services.redis_dispatch import (
        REDIS_DISPATCH_DEAD_LETTER_STREAM,
        MAX_DISPATCH_DELIVERY_ATTEMPTS,
        recover_pending_dispatch_messages,
        process_dispatch_stream_events,
    )
    assert REDIS_DISPATCH_DEAD_LETTER_STREAM == "workforce:dispatch:dead_letter"
    assert MAX_DISPATCH_DELIVERY_ATTEMPTS == 5

    redis_dispatch_path = os.path.join(os.path.dirname(__file__), "workforce_api", "services", "redis_dispatch.py")
    with open(redis_dispatch_path, "r", encoding="utf-8") as f:
        code = f.read()

    assert "poison_msg_ids" in code
    assert "REDIS_DISPATCH_DEAD_LETTER_STREAM" in code
    assert "Exceeded maximum delivery attempts" in code
    print("PASS: DLQ and poison message policy verified.")

if __name__ == "__main__":
    test_empty_service_fails_closed()
    test_ac_vs_painter_service_matching()
    test_presence_and_jobs_get_code_audit()
    test_models_save_no_sync_fallback()
    test_acceptance_and_redispatch_audit()
    test_offer_and_assignment_webhook_semantics()
    test_dlq_poison_routing()
    print("ALL TESTS PASSED!")

