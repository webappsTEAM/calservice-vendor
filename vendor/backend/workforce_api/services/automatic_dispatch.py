"""
Authoritative Automatic Geo-Based Dispatch Service.

Single source of truth for all automatic job dispatch, candidate ranking,
proximity evaluation, offer creation, fallback re-assignment, and cross-application
job reconciliation across Workforce and Marketplace.
"""
import logging
from datetime import timedelta
from typing import List, Dict, Any, Tuple, Optional

from django.db import transaction
from django.db.models import Count, Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

from service_requests.models import ServiceRequest, EmployeeJob
from service_requests.state_machine import apply_transition
from employees.models import Employee
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceNotification,
    WorkforceEmployeeSkill,
    WorkforceEmployeeCompliance,
    WorkforceEmployeeSchedule,
)
from time_tracking.geo import haversine_distance
from workforce_api.services.workload import get_employee_active_job, ACTIVE_WORKLOAD_STATUSES

logger = logging.getLogger("workforce.dispatch")

# Strict GPS telemetry freshness requirement (5 minutes maximum age for live dispatch, matching UI / spec)
MAX_GPS_AGE_SECONDS = 300

# Maximum geographic dispatch radius (50 km) before any widening kicks in.
MAX_DISPATCH_RADIUS_KM = 50.0

# Default job offer duration before auto-expiry and fallback -- kept as the
# fallback value used by compute_offer_window_minutes() below for any
# priority it doesn't recognize, and by any caller that still imports this
# constant directly.
DEFAULT_OFFER_DURATION_MINUTES = 5

# ── Variable offer window (Booking Dispatch Framework, section 4) ───────────
# The offer window is no longer one fixed number everywhere. It's a base
# value by booking priority, adjusted by how many eligible candidates were
# actually found for this job (a thin pool gets more time since burning the
# one good option on a timeout is expensive; a deep pool gets less since a
# strong next candidate is always a moment away), with a small extra bump
# for service categories known to have few qualified technicians. All of
# this is read through django.conf.settings with these as the defaults, so
# it can be retuned in an environment's settings without a code change --
# see the SEVO Booking Dispatch Framework doc, section 4, for the full
# rationale. Promote this to a DB-backed config table if/when it needs to
# vary per company or per zone rather than globally.
DEFAULT_OFFER_WINDOW_MINUTES_BY_PRIORITY = {
    "urgent": 2,
    "high": 3,
    "normal": 5,
    "low": 8,
}
THIN_POOL_CANDIDATE_THRESHOLD = 2   # this many eligible candidates or fewer counts as "thin"
DEEP_POOL_CANDIDATE_THRESHOLD = 8   # this many or more counts as "deep"
THIN_POOL_WINDOW_BONUS_MINUTES = 3
DEEP_POOL_WINDOW_PENALTY_MINUTES = 2
SPARSE_SERVICE_CATEGORY_WINDOW_BONUS_MINUTES = 3
MIN_OFFER_WINDOW_MINUTES = 2
MAX_OFFER_WINDOW_MINUTES = 15

# Service categories known to have a historically thin technician pool --
# these get the sparse-category bonus above regardless of how today's live
# pool looks, so a category that's thin on average doesn't need to burn a
# few timed-out offers before the system starts giving it more time. Purely
# additive to the live pool-depth signal, not a replacement for it.
SPARSE_SERVICE_CATEGORIES = {
    "specialist electrical",
    "elevator maintenance",
    "industrial hvac",
}

# ── Progressive radius widening (Booking Dispatch Framework, section 4) ───
# A booking that's burned through this many failed offer cycles (decline,
# reject, or timeout -- see _count_failed_offer_cycles below) without an
# acceptance gets a wider search radius on its next dispatch attempt,
# rather than staying capped at MAX_DISPATCH_RADIUS_KM forever. This trades
# a longer commute for a real technician over continuing to fail against an
# empty-or-exhausted pool. Capped at MAX_WIDENED_DISPATCH_RADIUS_KM: past
# that point a customer is genuinely outside any reasonable service area,
# and the right outcome is admin escalation (see dispatch_job below), not
# an ever-larger radius.
RADIUS_WIDENING_AFTER_CYCLES = 2
RADIUS_WIDENING_STEP_KM = 25.0
MAX_WIDENED_DISPATCH_RADIUS_KM = 100.0

# After this many failed offer cycles, the customer app is told the match
# is taking longer than usual (see _maybe_signal_customer_delay below).
CUSTOMER_DELAY_SIGNAL_AFTER_CYCLES = 2

# Dispatchable database statuses
DISPATCHABLE_STATUSES = ["draft", "new_request", "confirmed", "unassigned", "assigned", "redispatching"]

# GT-A-01/GT-A-02: service_name values that require a vehicle on file with
# current insurance/permit/PUC (Gate 3). Mirrors
# Customer/backend/service_requests/services/logistics_pricing.py's
# LOGISTICS_CATEGORIES -- kept as its own constant here (rather than a
# cross-app import) since the two Django projects share a database but not
# a codebase.
LOGISTICS_SERVICE_CATEGORIES = {
    "goods_transport_truck",
    "goods_transport_two_wheeler",
    "packers_movers",
    # HS-E-06: was missing here -- Customer/backend/service_requests/
    # services/__init__.py's LOGISTICS_STOP_CATEGORIES (the multi-stop
    # trip editor's gate) includes this bare slug alongside the two
    # specific transport modes; this set was the odd one out.
    "goods_transport",
}

# Canonical service synonyms and explicit alias dictionary
EXPLICIT_SERVICE_ALIASES = {
    "hvac": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "ac": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "air conditioning": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "ac repair & diagnostics": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "ac service & cleaning": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "ac gas & refrigerant": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "ac installation & uninstallation": {"hvac", "ac", "air conditioning", "ac service", "ac repair", "ac installation", "ac gas", "ac repair & diagnostics", "ac service & cleaning", "ac gas & refrigerant", "ac installation & uninstallation"},
    "plumbing": {"plumbing", "plumber", "pipe repair", "water leakage", "drainage", "tap repair", "sanitary"},
    "electrical": {"electrical", "electrician", "wiring", "switchboard", "fan repair", "fuse repair", "light fitting"},
    "electrician": {"electrical", "electrician", "wiring", "switchboard", "fan repair", "fuse repair", "light fitting"},
    "refrigerator": {"refrigerator", "fridge", "freezer", "single door fridge", "double door fridge"},
    "washing machine": {"washing machine", "washer", "dryer", "top load", "front load"},
    "tv & display": {"tv & display", "tv", "television", "led tv", "smart tv", "display"},
    "microwave oven repair": {"microwave", "microwave oven", "microwave oven repair", "oven"},
    "carpentry services": {"carpentry", "carpenter", "wood work", "furniture repair", "door repair", "carpentry services"},
    "pest control": {"pest control", "cockroach control", "ants & bed bugs control", "termite control", "bed bugs", "cockroach", "termite"},
    "cockroach control": {"cockroach control", "cockroach", "pest control"},
    "ants & bed bugs control": {"ants & bed bugs control", "ants", "bed bugs", "pest control"},
    "termite control": {"termite control", "termite", "pest control"},
    "cleaning": {"cleaning", "kitchen cleaning", "bathroom cleaning", "full house cleaning", "sofa cleaning", "deep cleaning", "house cleaning"},
    "kitchen cleaning": {"kitchen cleaning", "cleaning", "deep cleaning"},
    "bathroom cleaning": {"bathroom cleaning", "cleaning", "deep cleaning"},
    "full house cleaning": {"full house cleaning", "cleaning", "deep cleaning", "house cleaning"},
    "sofa cleaning": {"sofa cleaning", "cleaning", "couch cleaning"},
    "two wheeler": {"two wheeler", "bike", "scooter", "motorcycle", "bike repair", "two wheeler repair"},
    "truck": {"truck", "packer & mover", "packers & movers", "logistics", "shifting"},
    "packer & mover": {"packer & mover", "packers & movers", "truck", "shifting", "relocation"},
}


def canonical_service_match(requested_service: str, approved_services: List[str], verified_skills: List[str]) -> Tuple[bool, str, str]:
    """
    Evaluates whether a requested service matches an employee's authorized services or verified skills.
    Returns (is_match, match_method, matched_term).
    """
    if not requested_service:
        return True, "EMPTY_SERVICE_BYPASS", ""

    req_clean = requested_service.lower().replace("—", " ").replace("-", " ").strip()
    req_words = set(w for w in req_clean.split() if len(w) >= 2)

    # 1. Check exact or direct match against approved employee services
    for it in approved_services:
        if not it:
            continue
        it_clean = it.lower().replace("—", " ").replace("-", " ").strip()
        if req_clean == it_clean or req_clean in it_clean or it_clean in req_clean:
            return True, "EXACT_OR_SUBSTRING_SERVICE", it

    # 2. Check verified skills
    for sk in verified_skills:
        if not sk:
            continue
        sk_clean = sk.lower().replace("—", " ").replace("-", " ").strip()
        if req_clean == sk_clean or req_clean in sk_clean or sk_clean in req_clean:
            return True, "VERIFIED_SKILL_MATCH", sk

    # 3. Check explicit canonical alias table
    for alias_key, alias_group in EXPLICIT_SERVICE_ALIASES.items():
        # If requested service matches this alias key/group
        if req_clean == alias_key or req_clean in alias_group or any(req_word in alias_group for req_word in req_words):
            # Check if employee has any matching service in that alias group
            for it in approved_services:
                it_clean = it.lower().replace("—", " ").replace("-", " ").strip()
                if it_clean in alias_group or any(w in alias_group for w in it_clean.split() if len(w) >= 2):
                    return True, "EXPLICIT_ALIAS_SERVICE", it
            for sk in verified_skills:
                sk_clean = sk.lower().replace("—", " ").replace("-", " ").strip()
                if sk_clean in alias_group or any(w in alias_group for w in sk_clean.split() if len(w) >= 2):
                    return True, "EXPLICIT_ALIAS_SKILL", sk

    return False, "NO_MATCH", ""


def check_candidate_eligibility(emp: Employee, service_name: Optional[str] = None) -> Tuple[bool, str, Dict[str, bool]]:
    """
    9-Gate Employee Eligibility Engine:
    Authoritative server-side evaluation of 9 mandatory operational gates.
    Every gate fails closed.
    Returns (is_eligible, reason_message, gate_results_dict).
    """
    gate_results = {f"G{i}": True for i in range(1, 10)}

    # ── Gate 1: Account Active ────────────────────────────────────────────────
    if not emp or not emp.is_active or not getattr(emp.user, "is_active", True):
        gate_results["G1"] = False
        logger.debug(f"[9GATE_REJECT_GATE1_ACCOUNT_INACTIVE] Employee #{getattr(emp, 'id', None)} account is inactive.")
        return False, "Gate 1: Technician account is inactive.", gate_results

    bank_details = emp.bank_details or {}
    onboarding = bank_details.get("onboarding", {})

    # ── Gate 2: Registration Approved ─────────────────────────────────────────
    reg_status = onboarding.get("status", "not_started")
    if reg_status != "approved":
        gate_results["G2"] = False
        logger.debug(f"[9GATE_REJECT_GATE2_ONBOARDING_UNAPPROVED] Employee #{emp.id} onboarding status is '{reg_status}'.")
        return False, "Gate 2: Technician registration onboarding is not approved.", gate_results

    # ── Gate 3: Required Documents Approved ───────────────────────────────────
    if emp and getattr(emp, "company_id", None):
        from workforce_api.models import WorkforceRequiredDocument, WorkforceEmployeeDocument
        mandatory_doc_reqs = WorkforceRequiredDocument.objects.filter(company_id=emp.company_id, is_mandatory=True)
        # GT-A-02: a requirement with a non-empty applies_to_categories only
        # gates jobs in one of those categories (e.g. Driving Licence should
        # not block a technician from taking an AC-repair job). A requirement
        # with an empty list (the default, and every pre-existing row) keeps
        # applying to every job, exactly as before this field existed.
        service_name_clean = (service_name or "").strip().lower()
        mandatory_doc_reqs = [
            rd for rd in mandatory_doc_reqs
            if not rd.applies_to_categories
            or service_name_clean in {str(c).strip().lower() for c in rd.applies_to_categories}
        ]
        if mandatory_doc_reqs:
            if hasattr(emp, "prefetched_employee_documents"):
                emp_docs_map = {d.requirement_id: d for d in emp.prefetched_employee_documents}
            else:
                emp_docs_map = {
                    d.requirement_id: d
                    for d in WorkforceEmployeeDocument.objects.filter(employee=emp, requirement__in=mandatory_doc_reqs)
                }

            today = timezone.now().date()
            for req_doc in mandatory_doc_reqs:
                emp_doc = emp_docs_map.get(req_doc.id)
                if not emp_doc or emp_doc.status != "APPROVED":
                    gate_results["G3"] = False
                    st = emp_doc.status if emp_doc else "MISSING"
                    logger.debug(f"[9GATE_REJECT_GATE3_DOCUMENTS_UNAPPROVED] Employee #{emp.id} mandatory document '{req_doc.title}' is {st}.")
                    return False, f"Gate 3: Technician mandatory document '{req_doc.title}' is {st} (must be APPROVED).", gate_results
                if emp_doc.expiry_date and emp_doc.expiry_date < today:
                    gate_results["G3"] = False
                    logger.debug(f"[9GATE_REJECT_GATE3_DOCUMENTS_EXPIRED] Employee #{emp.id} mandatory document '{req_doc.title}' expired on {emp_doc.expiry_date}.")
                    return False, f"Gate 3: Technician mandatory document '{req_doc.title}' expired on {emp_doc.expiry_date}.", gate_results

        # GT-A-01/GT-A-02: for logistics jobs specifically, also require at
        # least one active Vehicle on file whose insurance/permit/PUC are all
        # current. This is opt-in in effect: an employee with zero Vehicle
        # rows is only blocked for jobs in LOGISTICS_SERVICE_CATEGORIES, and
        # only once dispatch actually routes a logistics job their way --
        # non-logistics dispatch is entirely unaffected.
        if service_name_clean in LOGISTICS_SERVICE_CATEGORIES:
            from workforce_api.models import Vehicle
            vehicles = list(Vehicle.objects.filter(employee=emp, is_active=True))
            if not vehicles:
                gate_results["G3"] = False
                logger.debug(f"[9GATE_REJECT_GATE3_NO_VEHICLE] Employee #{emp.id} has no active vehicle on file for logistics job '{service_name}'.")
                return False, "Gate 3: No active vehicle on file for this logistics job.", gate_results
            if not any(v.is_document_current() for v in vehicles):
                gate_results["G3"] = False
                logger.debug(f"[9GATE_REJECT_GATE3_VEHICLE_DOCS_EXPIRED] Employee #{emp.id} has no vehicle with current insurance/permit/PUC.")
                return False, "Gate 3: Vehicle insurance, permit or PUC has expired.", gate_results
        else:
            documents = onboarding.get("documents", {})
            if any(doc.get("status") in ["rejected", "pending_review", "missing"] for doc in documents.values()):
                gate_results["G3"] = False
                logger.debug(f"[9GATE_REJECT_GATE3_DOCUMENTS_UNAPPROVED] Employee #{emp.id} has unapproved documents.")
                return False, "Gate 3: Technician has unapproved dossier documents.", gate_results
    else:
        documents = onboarding.get("documents", {})
        if any(doc.get("status") in ["rejected", "pending_review", "missing"] for doc in documents.values()):
            gate_results["G3"] = False
            return False, "Gate 3: Technician has unapproved dossier documents.", gate_results

    # ── Gate 4: Mandatory Compliance Valid ────────────────────────────────────
    if emp and getattr(emp, "company_id", None):
        from workforce_api.models import WorkforceComplianceRequirement
        mandatory_comp_reqs = WorkforceComplianceRequirement.objects.filter(company_id=emp.company_id, is_mandatory=True)
        if mandatory_comp_reqs.exists():
            today = timezone.now().date()
            emp_comp_records = list(WorkforceEmployeeCompliance.objects.filter(employee=emp, requirement__in=mandatory_comp_reqs))
            emp_comp_map = {c.requirement_id: c for c in emp_comp_records}
            for comp_req in mandatory_comp_reqs:
                c_rec = emp_comp_map.get(comp_req.id)
                if not c_rec or c_rec.status in ["MISSING", "PENDING_REVIEW", "REJECTED", "EXPIRED"]:
                    gate_results["G4"] = False
                    st = c_rec.status if c_rec else "MISSING"
                    logger.debug(f"[9GATE_REJECT_GATE4_COMPLIANCE_INVALID] Employee #{emp.id} mandatory compliance '{comp_req.title}' is {st}.")
                    return False, f"Gate 4: Mandatory compliance '{comp_req.title}' is {st} (must be VALID).", gate_results
                if c_rec.expiry_date and c_rec.expiry_date < today:
                    gate_results["G4"] = False
                    return False, f"Gate 4: Mandatory compliance '{comp_req.title}' expired on {c_rec.expiry_date}.", gate_results
        else:
            if hasattr(emp, "prefetched_invalid_compliance"):
                if emp.prefetched_invalid_compliance:
                    gate_results["G4"] = False
                    logger.debug(f"[9GATE_REJECT_GATE4_COMPLIANCE_INVALID] Employee #{emp.id} has invalid compliance.")
                    return False, "Gate 4: Technician has expired or rejected mandatory compliance document.", gate_results
            else:
                mandatory_comp = WorkforceEmployeeCompliance.objects.filter(
                    employee=emp,
                    requirement__is_mandatory=True,
                    status__in=["EXPIRED", "REJECTED"],
                ).first()
                if mandatory_comp:
                    gate_results["G4"] = False
                    logger.debug(f"[9GATE_REJECT_GATE4_COMPLIANCE_INVALID] Employee #{emp.id} compliance '{mandatory_comp.requirement.title}' is {mandatory_comp.status}.")
                    return False, f"Gate 4: Technician has expired or rejected mandatory compliance document: '{mandatory_comp.requirement.title}'.", gate_results
    else:
        if hasattr(emp, "prefetched_invalid_compliance"):
            if emp.prefetched_invalid_compliance:
                gate_results["G4"] = False
                return False, "Gate 4: Technician has expired or rejected mandatory compliance document.", gate_results
        else:
            mandatory_comp = WorkforceEmployeeCompliance.objects.filter(
                employee=emp,
                requirement__is_mandatory=True,
                status__in=["EXPIRED", "REJECTED"],
            ).first()
            if mandatory_comp:
                gate_results["G4"] = False
                return False, f"Gate 4: Technician has expired or rejected mandatory compliance document: '{mandatory_comp.requirement.title}'.", gate_results

    # ── Gate 5: Working Schedule ──────────────────────────────────────────────
    if hasattr(emp, "prefetched_today_schedules"):
        sched = emp.prefetched_today_schedules[0] if emp.prefetched_today_schedules else None
    else:
        today_dow = timezone.now().weekday()
        sched = WorkforceEmployeeSchedule.objects.filter(employee=emp, day_of_week=today_dow).first()

    if sched:
        if not sched.is_working_day:
            gate_results["G5"] = False
            logger.debug(f"[9GATE_REJECT_GATE5_SCHEDULE_OFF] Employee #{emp.id} is scheduled off today.")
            return False, "Gate 5: Technician is scheduled off today.", gate_results
        now_time = timezone.now().time()
        if not (sched.start_time <= now_time <= sched.end_time):
            gate_results["G5"] = False
            logger.debug(f"[9GATE_REJECT_GATE5_SCHEDULE_OUTSIDE] Employee #{emp.id} outside hours ({sched.start_time}-{sched.end_time}).")
            return False, f"Gate 5: Technician is outside scheduled working hours ({sched.start_time.strftime('%H:%M')}-{sched.end_time.strftime('%H:%M')}).", gate_results

    # ── Gate 6: Service / Skill Authorization ─────────────────────────────────
    approved_svcs = []
    for s in onboarding.get("services", []):
        if s.get("status") == "approved":
            if s.get("name"):
                approved_svcs.append(s["name"])
            if s.get("category"):
                approved_svcs.append(s["category"])

    if hasattr(emp, "prefetched_verified_skills"):
        verified_skills = [es.skill.name for es in emp.prefetched_verified_skills]
    else:
        verified_skills = list(
            WorkforceEmployeeSkill.objects.filter(employee=emp, is_verified=True).values_list("skill__name", flat=True)
        )

    if service_name:
        is_match, method, matched = canonical_service_match(service_name, approved_svcs, verified_skills)
        logger.info(f"[DISPATCH_SERVICE_MATCH] job_service=\"{service_name}\" employee_services={approved_svcs} verified_skills={verified_skills} match_method={method} result={'PASS' if is_match else 'FAIL'}")
        if not is_match:
            gate_results["G6"] = False
            logger.debug(f"[9GATE_REJECT_GATE6_SKILL_MISMATCH] Employee #{emp.id} not authorized/verified for '{service_name}'.")
            return False, f"Gate 6: Technician is not authorized or verified for requested service '{service_name}'.", gate_results

    # ── Gate 7: Live Presence (Online & Available) ────────────────────────────
    if not emp.is_online or emp.current_availability != "available":
        gate_results["G7"] = False
        logger.debug(f"[9GATE_REJECT_GATE7_PRESENCE_OFFLINE] Employee #{emp.id} presence is is_online={emp.is_online}, avail={emp.current_availability}.")
        return False, "Gate 7: Technician is currently OFFLINE or unavailable.", gate_results

    # ── Gate 8: Leave Check ───────────────────────────────────────────────────
    today_str = timezone.now().date().isoformat()
    leaves = bank_details.get("leaves", [])
    for l in leaves:
        if l.get("status") == "approved":
            start_date = l.get("start_date", "")
            end_date = l.get("end_date", "")
            if start_date <= today_str <= end_date:
                gate_results["G8"] = False
                logger.debug(f"[9GATE_REJECT_GATE8_LEAVE_ACTIVE] Employee #{emp.id} on approved leave ({start_date} to {end_date}).")
                return False, f"Gate 8: Technician is on approved leave from {start_date} to {end_date}.", gate_results

    # ── Gate 9: Workload Concurrency (Single-Active-Job Isolation) ──────────────
    from workforce_api.services.workload import get_employee_active_job
    active_job = get_employee_active_job(emp)
    if active_job:
        gate_results["G9"] = False
        logger.info(
            f"[DISPATCH_REJECT] employee={emp.id} reason=EMPLOYEE_ALREADY_BUSY active_job={active_job.id}"
        )
        return False, f"Gate 9: Technician is busy on active Job #{active_job.id} ({active_job.request_id}).", gate_results

    return True, "All 9 Eligibility Gates Passed", gate_results


def get_eligible_candidates(job_id_or_obj, max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS, exclude_employee_ids: Optional[List[int]] = None, radius_km: float = MAX_DISPATCH_RADIUS_KM) -> List[Dict[str, Any]]:
    """
    Finds and ranks all eligible candidate employees for a given ServiceRequest.
    Uses database-level filtering and prefetching for optimal WAN performance.
    """
    if hasattr(job_id_or_obj, "latitude"):
        job_obj = job_id_or_obj
    else:
        job_obj = ServiceRequest.objects.filter(pk=job_id_or_obj).first()
        if not job_obj:
            logger.warning(f"[DISPATCH_JOB_NOT_FOUND] Job #{job_id_or_obj} not found.")
            return []

    if job_obj.latitude is None or job_obj.longitude is None:
        logger.warning(f"[DISPATCH_GPS_MISSING] Job #{job_obj.id} lacks customer GPS coordinates.")
        return []

    try:
        cust_lat = float(job_obj.latitude)
        cust_lon = float(job_obj.longitude)
    except (ValueError, TypeError):
        logger.warning(f"[DISPATCH_GPS_MISSING] Job #{job_obj.id} has invalid customer GPS coordinates ({job_obj.latitude}, {job_obj.longitude}).")
        return []

    today_dow = timezone.now().weekday()
    from workforce_api.services.workload import ACTIVE_WORKLOAD_STATUSES, get_employee_active_job
    busy_subquery = ServiceRequest.objects.filter(
        assigned_employee_id=OuterRef("pk"),
        status__in=ACTIVE_WORKLOAD_STATUSES
    )

    candidates_qs = (
        Employee.objects.filter(
            is_active=True,
            is_online=True,
            current_availability="available",
        )
        .select_related("user", "company", "scorecard")
        .annotate(is_busy_job=Exists(busy_subquery))
    )

    if exclude_employee_ids:
        candidates_qs = candidates_qs.exclude(pk__in=exclude_employee_ids)

    # GT-E-02: declining/cancelling an offer previously carried no
    # consequence for ranking -- a technician who reliably rejects or lets
    # offers expire ranked exactly the same as one who always accepts.
    # Annotate a rolling 30-day offer-outcome count per candidate so the
    # scoring loop below can apply a small reliability penalty. This reuses
    # existing WorkforceJobOffer rows -- no new model/migration needed.
    _reliability_window_start = timezone.now() - timedelta(days=30)
    candidates_qs = candidates_qs.annotate(
        recent_offers_total=Count(
            "job_offers",
            filter=Q(job_offers__offered_at__gte=_reliability_window_start),
        ),
        recent_offers_declined=Count(
            "job_offers",
            filter=Q(
                job_offers__offered_at__gte=_reliability_window_start,
                job_offers__status__in=["REJECTED", "DECLINED", "EXPIRED", "CANCELLED"],
            ),
        ),
    )

    candidates_qs = (
        candidates_qs
        .prefetch_related(
            Prefetch(
                "compliance_records",
                queryset=WorkforceEmployeeCompliance.objects.filter(
                    requirement__is_mandatory=True,
                    status__in=["EXPIRED", "REJECTED"],
                ),
                to_attr="prefetched_invalid_compliance",
            ),
            Prefetch(
                "schedules",
                queryset=WorkforceEmployeeSchedule.objects.filter(day_of_week=today_dow),
                to_attr="prefetched_today_schedules",
            ),
            Prefetch(
                "skills",
                queryset=WorkforceEmployeeSkill.objects.filter(is_verified=True).select_related("skill"),
                to_attr="prefetched_verified_skills",
            ),
        )
    )

    if not job_obj.company_id or job_obj.company_id == 1:
        candidates_qs = candidates_qs.filter(Q(company_id=1) | Q(company__isnull=True))
    else:
        candidates_qs = candidates_qs.filter(company_id=job_obj.company_id)

    # Exclude candidates who have already received or rejected/cancelled an offer for this job, or explicitly excluded
    previous_offers = set(
        WorkforceJobOffer.objects.filter(
            job=job_obj,
            status__in=["OFFERED", "REJECTED", "CANCELLED", "ACCEPTED"]
        ).values_list("employee_id", flat=True)
    )
    if exclude_employee_ids:
        previous_offers.update(exclude_employee_ids)

    ranked_candidates = []
    now = timezone.now()

    for emp in candidates_qs:
        if emp.id in previous_offers:
            logger.debug(f"[DISPATCH_CANDIDATE_REJECTED] Employee #{emp.id} already has offer history for Job #{job_obj.id}.")
            continue

        # Extract live GPS from User.last_known_location
        last_loc = getattr(emp.user, "last_known_location", None) or {}
        emp_lat = last_loc.get("latitude") if last_loc.get("latitude") is not None else last_loc.get("lat")
        emp_lon = last_loc.get("longitude") if last_loc.get("longitude") is not None else (last_loc.get("lng") or last_loc.get("lon"))

        gps_age_s = None
        updated_at_str = last_loc.get("updated_at") or last_loc.get("captured_at")
        if updated_at_str:
            try:
                loc_dt = parse_datetime(str(updated_at_str))
                if loc_dt:
                    if timezone.is_naive(loc_dt):
                        loc_dt = timezone.make_aware(loc_dt)
                    gps_age_s = (now - loc_dt).total_seconds()
            except Exception:
                pass

        dist_km = None
        emp_lat_f = None
        emp_lon_f = None
        if emp_lat is not None and emp_lon is not None:
            try:
                emp_lat_f = float(emp_lat)
                emp_lon_f = float(emp_lon)
                dist_m = haversine_distance(cust_lat, cust_lon, emp_lat_f, emp_lon_f)
                dist_km = dist_m / 1000.0
            except (ValueError, TypeError):
                pass

        logger.info(
            f"[9GATE_EVALUATION] employee={emp.id} online={emp.is_online} availability={emp.current_availability} "
            f"gps_age={f'{gps_age_s:.1f}s' if gps_age_s is not None else 'MISSING'} "
            f"distance_km={f'{dist_km:.2f}km' if dist_km is not None else 'UNKNOWN'}"
        )

        # Check eligibility against service_category, then issue_title
        is_eligible, reason, gate_results = check_candidate_eligibility(emp, job_obj.service_category)
        if not is_eligible and job_obj.issue_title:
            is_eligible, reason, gate_results = check_candidate_eligibility(emp, job_obj.issue_title)

        g_str = " ".join(f"{k}={'PASS' if v else 'FAIL'}" for k, v in gate_results.items())
        logger.info(f"[9GATE_RESULT] employee={emp.id} {g_str}")

        if not is_eligible:
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason={reason}")
            continue

        if emp_lat_f is None or emp_lon_f is None:
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=GPS_MISSING")
            continue

        if gps_age_s is None or gps_age_s > max_gps_age_seconds or gps_age_s < -60:
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=GPS_STALE gps_age={gps_age_s}s")
            continue

        if dist_km is None or dist_km > radius_km:
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=RADIUS_EXCEEDED distance_km={dist_km}")
            continue

        # Proximity score (closer = higher score, max 100)
        proximity_score = max(0.0, 100.0 - (dist_km * 2.0))

        # Skill proficiency score bonus from prefetched skills
        skills = getattr(emp, "prefetched_verified_skills", [])
        max_prof = 0
        for sk in skills:
            sk_name = sk.skill.name.lower()
            matches = False
            for term in [job_obj.service_category, job_obj.issue_title]:
                if term and (term.lower() in sk_name or sk_name in term.lower()):
                    matches = True
                    break
            if matches:
                if sk.proficiency_level == "EXPERT":
                    max_prof = max(max_prof, 30)
                elif sk.proficiency_level == "INTERMEDIATE":
                    max_prof = max(max_prof, 20)
                else:
                    max_prof = max(max_prof, 10)

        # Territory bonus
        city = (emp.bank_details or {}).get("onboarding", {}).get("draft", {}).get("personal", {}).get("city", "")
        territory_bonus = 15.0 if (job_obj.address and city and city.lower() in job_obj.address.lower()) else 0.0

        # Shift clock-in bonus
        bank_details = emp.bank_details or {}
        is_clocked_in = bank_details.get("attendance", {}).get("is_clocked_in", False)
        clock_in_bonus = 10.0 if is_clocked_in else 0.0

        # GT-E-02: reliability penalty. Only applied once there's a real
        # sample (>=3 offers in the last 30 days) so a technician's very
        # first offer or two is never penalized off a fluke. Max penalty is
        # capped at 20 points -- enough to matter in ranking without letting
        # it override a technician being genuinely much closer/more skilled.
        recent_total = getattr(emp, "recent_offers_total", 0) or 0
        recent_declined = getattr(emp, "recent_offers_declined", 0) or 0
        reliability_penalty = 0.0
        if recent_total >= 3:
            reliability_penalty = min(20.0, (recent_declined / recent_total) * 20.0)

        # SEVO business plan Section 4 / Days 31-60 roadmap: "Rating and
        # SLA scorecards go live and start feeding the dispatch-ranking
        # algorithm." Same shape as reliability_penalty above: only kicks
        # in once there is a real sample (WorkforceScorecard already
        # withholds a tier -- and this bonus -- below 3 ratings), capped
        # so it nudges ranking without overriding proximity/skill.
        scorecard = getattr(emp, "scorecard", None)
        scorecard_bonus = 0.0
        if scorecard is not None and scorecard.rating_count >= 3:
            rating_component = (float(scorecard.average_rating) / 5.0) * 10.0
            sla_component = (float(scorecard.sla_score) / 100.0) * 10.0
            scorecard_bonus = max(0.0, min(20.0, rating_component + sla_component))

        total_score = proximity_score + max_prof + territory_bonus + clock_in_bonus + scorecard_bonus - reliability_penalty

        logger.info(f"[DISPATCH_CANDIDATE_FOUND] Employee #{emp.id} ({emp.user.username}) eligible for Job #{job_obj.id}: {dist_km:.2f}km away, score={total_score:.1f} (scorecard_bonus={scorecard_bonus:.1f}, reliability_penalty={reliability_penalty:.1f})")

        ranked_candidates.append({
            "employee": emp,
            "distance_km": dist_km,
            "score": total_score,
        })

    # Sort primarily by nearest distance (ascending), then by highest score (descending)
    ranked_candidates.sort(key=lambda x: (x["distance_km"], -x["score"]))
    return ranked_candidates


def compute_offer_window_minutes(job_obj, pool_size: int) -> int:
    """
    How long a single exclusive offer stays open before it expires and the
    job falls through to the next-ranked candidate. Booking Dispatch
    Framework section 4: this used to be one fixed number
    (DEFAULT_OFFER_DURATION_MINUTES) everywhere; it now flexes by booking
    priority, how many eligible candidates were actually found (a thin
    pool gets more time, a deep one gets less), and whether the service
    category is a historically thin one. All the tuning knobs are settings-
    overridable module constants above, not hardcoded here, so an
    environment can retune them without a deploy.
    """
    priority = (getattr(job_obj, "priority", "") or "normal").lower()
    by_priority = getattr(
        settings, "DISPATCH_OFFER_WINDOW_MINUTES_BY_PRIORITY", DEFAULT_OFFER_WINDOW_MINUTES_BY_PRIORITY
    )
    minutes = by_priority.get(priority, DEFAULT_OFFER_DURATION_MINUTES)

    thin_threshold = getattr(settings, "DISPATCH_THIN_POOL_CANDIDATE_THRESHOLD", THIN_POOL_CANDIDATE_THRESHOLD)
    deep_threshold = getattr(settings, "DISPATCH_DEEP_POOL_CANDIDATE_THRESHOLD", DEEP_POOL_CANDIDATE_THRESHOLD)
    if pool_size <= thin_threshold:
        minutes += getattr(settings, "DISPATCH_THIN_POOL_WINDOW_BONUS_MINUTES", THIN_POOL_WINDOW_BONUS_MINUTES)
    elif pool_size >= deep_threshold:
        minutes -= getattr(settings, "DISPATCH_DEEP_POOL_WINDOW_PENALTY_MINUTES", DEEP_POOL_WINDOW_PENALTY_MINUTES)

    sparse_categories = getattr(settings, "DISPATCH_SPARSE_SERVICE_CATEGORIES", SPARSE_SERVICE_CATEGORIES)
    category = (getattr(job_obj, "service_category", "") or "").strip().lower()
    if category in sparse_categories:
        minutes += getattr(
            settings, "DISPATCH_SPARSE_SERVICE_CATEGORY_WINDOW_BONUS_MINUTES", SPARSE_SERVICE_CATEGORY_WINDOW_BONUS_MINUTES
        )

    min_minutes = getattr(settings, "DISPATCH_MIN_OFFER_WINDOW_MINUTES", MIN_OFFER_WINDOW_MINUTES)
    max_minutes = getattr(settings, "DISPATCH_MAX_OFFER_WINDOW_MINUTES", MAX_OFFER_WINDOW_MINUTES)
    return max(min_minutes, min(max_minutes, minutes))


def _count_failed_offer_cycles(job_obj) -> int:
    """How many offers this job has already burned through without an
    acceptance -- rejected, declined, or expired. Drives both progressive
    radius widening and the customer delay signal below."""
    return WorkforceJobOffer.objects.filter(
        job=job_obj,
        status__in=[
            WorkforceJobOffer.Status.REJECTED,
            WorkforceJobOffer.Status.DECLINED,
            WorkforceJobOffer.Status.EXPIRED,
        ],
    ).count()


def get_effective_radius_km(failed_cycle_count: int) -> float:
    """
    Progressive radius widening (Booking Dispatch Framework section 4):
    stays at the normal MAX_DISPATCH_RADIUS_KM until a job has failed
    RADIUS_WIDENING_AFTER_CYCLES offer cycles, then widens by
    RADIUS_WIDENING_STEP_KM per additional failed cycle, capped at
    MAX_WIDENED_DISPATCH_RADIUS_KM -- past that a customer is genuinely
    outside any reasonable service area and the right outcome is admin
    escalation, not an ever-larger radius.
    """
    base_radius = getattr(settings, "DISPATCH_MAX_RADIUS_KM", MAX_DISPATCH_RADIUS_KM)
    after_cycles = getattr(settings, "DISPATCH_RADIUS_WIDENING_AFTER_CYCLES", RADIUS_WIDENING_AFTER_CYCLES)
    if failed_cycle_count < after_cycles:
        return base_radius

    step_km = getattr(settings, "DISPATCH_RADIUS_WIDENING_STEP_KM", RADIUS_WIDENING_STEP_KM)
    max_radius = getattr(settings, "DISPATCH_MAX_WIDENED_RADIUS_KM", MAX_WIDENED_DISPATCH_RADIUS_KM)
    extra_cycles = (failed_cycle_count - after_cycles) + 1
    widened = base_radius + (extra_cycles * step_km)
    return min(widened, max_radius)


def describe_unassigned_reason(failed_cycle_count: int, effective_radius_km: float) -> Tuple[str, str]:
    """
    Returns (reason_code, human_message) so an admin sees WHY a job has no
    candidate -- nobody has been tried yet vs. everyone tried has already
    declined/timed out vs. the search radius is maxed out -- instead of one
    generic "no technician available" notice for every case.
    """
    max_radius = getattr(settings, "DISPATCH_MAX_WIDENED_RADIUS_KM", MAX_WIDENED_DISPATCH_RADIUS_KM)
    if failed_cycle_count == 0:
        return (
            "NO_ELIGIBLE_NEARBY",
            f"No technician is currently online, available, and eligible within {effective_radius_km:.0f} km.",
        )
    if effective_radius_km >= max_radius:
        return (
            "POOL_EXHAUSTED_AFTER_WIDENING",
            f"Every technician within the maximum {max_radius:.0f} km search radius has already "
            f"declined, timed out, or is otherwise unavailable ({failed_cycle_count} offer cycle(s) tried).",
        )
    return (
        "POOL_THIN_WIDENING",
        f"No remaining eligible technician within {effective_radius_km:.0f} km after "
        f"{failed_cycle_count} failed offer cycle(s); radius will widen further on retry.",
    )


def _maybe_signal_customer_delay(job_obj, failed_cycle_count: int) -> None:
    """
    Once a booking has burned through enough failed offer cycles that the
    match is genuinely taking longer than usual, soften the customer app's
    status signal instead of leaving it looking identical to a booking that
    matched instantly (Booking Dispatch Framework section 4). Fires once,
    exactly when the threshold is crossed, not on every subsequent cycle.

    NOTE: this sends a "booking.dispatch_delayed" webhook event. As of this
    change, the Customer app's webhook receiver
    (Customer/backend/workforce_integration/views.py) does not yet have a
    handler for that event type -- delivery will be logged but the event
    itself is a no-op on the receiving end until that side adds one. Wiring
    is deliberately vendor-side-only here (see module docstring in
    services/customer_webhook.py for the cross-app boundary); the Customer
    app's own receiver change is out of scope for this pass.
    """
    threshold = getattr(settings, "DISPATCH_CUSTOMER_DELAY_SIGNAL_AFTER_CYCLES", CUSTOMER_DELAY_SIGNAL_AFTER_CYCLES)
    if failed_cycle_count != threshold:
        return
    try:
        from workforce_api.services.customer_webhook import notify_customer_app
        notify_customer_app(
            "booking.dispatch_delayed",
            job_obj,
            failed_offer_cycles=failed_cycle_count,
        )
    except Exception as webhook_err:
        logger.info(f"Could not notify Customer app of dispatch delay for Job #{job_obj.id}: {webhook_err}")


def dispatch_job(job_id_or_obj, max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS, exclude_employee_ids: Optional[List[int]] = None) -> Tuple[bool, str]:
    """
    Executes automatic dispatch for a single ServiceRequest:
    1. Locks ServiceRequest row with select_for_update inside transaction.atomic()
    2. Validates dispatchable state and coordinates
    3. Checks if an active exclusive offer already exists (idempotent guard)
    4. Evaluates and ranks eligible candidates
    5. Creates WorkforceJobOffer, sends JOB_OFFER notification, and logs audit events
    """
    job_id = job_id_or_obj.pk if hasattr(job_id_or_obj, "pk") else job_id_or_obj
    from workforce_api.models import WorkforceEventLog

    with transaction.atomic():
        job_obj = ServiceRequest.objects.select_for_update().filter(pk=job_id).first()
        if not job_obj:
            return False, "Job not found."

        if job_obj.status in ["completed", "cancelled"]:
            return False, f"Job #{job_id} is {job_obj.status} and cannot be dispatched."

        if job_obj.status in ["accepted", "on_the_way", "arrived", "in_progress"] and job_obj.assigned_employee:
            return False, f"Job #{job_id} is already accepted and in progress with Employee #{job_obj.assigned_employee_id}."

        now = timezone.now()

        logger.info(
            f"[DISPATCH_EVALUATION] job_id={job_obj.id} "
            f"service=\"{job_obj.service_category or job_obj.issue_title}\" "
            f"customer_lat={job_obj.latitude} customer_lng={job_obj.longitude}"
        )

        # Idempotency: Check if an active, non-expired offer already exists
        active_offer = WorkforceJobOffer.objects.select_for_update().filter(
            job=job_obj,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        ).first()

        if active_offer:
            logger.info(f"[DISPATCH_OFFER_EXISTS] Job #{job_id} already has active offer #{active_offer.id} for Employee #{active_offer.employee_id}.")
            return True, f"Active offer already pending for Employee #{active_offer.employee_id}."

        # Validate customer booking coordinates
        if job_obj.latitude is None or job_obj.longitude is None:
            if job_obj.status != "unassigned":
                apply_transition(job_obj, "unassigned")
            logger.warning(f"[DISPATCH_GPS_MISSING] Job #{job_id} is missing coordinates.")
        # Ensure default platform company context if unassigned
        if not job_obj.company_id:
            job_obj.company_id = 1
            job_obj.save(update_fields=["company_id"])

        WorkforceEventLog.objects.create(
            event_type="DISPATCH_STARTED",
            payload={"job_id": job_obj.id, "service": job_obj.service_category}
        )

        # Progressive radius widening (Booking Dispatch Framework section 4):
        # how many times has this job already failed a full offer cycle
        # (decline/reject/expire)? Feeds both the search radius below and
        # the customer delay signal further down.
        failed_cycle_count = _count_failed_offer_cycles(job_obj)
        effective_radius_km = get_effective_radius_km(failed_cycle_count)

        # Find eligible candidate technicians
        candidates = get_eligible_candidates(
            job_obj,
            max_gps_age_seconds=max_gps_age_seconds,
            exclude_employee_ids=exclude_employee_ids,
            radius_km=effective_radius_km,
        )

        WorkforceEventLog.objects.create(
            event_type="CANDIDATES_EVALUATED",
            payload={"job_id": job_obj.id, "eligible_count": len(candidates)}
        )

        if not candidates:
            if job_obj.status != "unassigned" or job_obj.assigned_employee is not None:
                job_obj.status = "unassigned"
                job_obj.assigned_employee = None
                job_obj.save(update_fields=["status", "assigned_employee"])

            admin_user = None
            if job_obj.company:
                admin_user = get_user_model().objects.filter(
                    Q(role__in=["admin", "manager"]) | Q(is_staff=True),
                    company=job_obj.company
                ).first()
            if not admin_user:
                admin_user = get_user_model().objects.filter(is_superuser=True).first()

            reason_code, reason_message = describe_unassigned_reason(failed_cycle_count, effective_radius_km)

            if admin_user:
                service_name = job_obj.issue_title or job_obj.service_category or "Service"
                WorkforceNotification.objects.create(
                    recipient=admin_user,
                    title="Automatic Dispatch: Awaiting Technician",
                    message=f"Job #{job_obj.id} ({service_name}) remains unassigned. {reason_message}",
                    notification_type="DISPATCH_UNASSIGNED",
                    company=job_obj.company,
                    related_object_id=str(job_obj.id),
                )

            WorkforceEventLog.objects.create(
                event_type="DISPATCH_UNASSIGNED_REASON",
                payload={
                    "job_id": job_obj.id,
                    "reason_code": reason_code,
                    "reason_message": reason_message,
                    "failed_cycle_count": failed_cycle_count,
                    "effective_radius_km": effective_radius_km,
                },
            )
            _maybe_signal_customer_delay(job_obj, failed_cycle_count)
            return False, f"No eligible technicians available for automatic dispatch. {reason_message}"

        # Top nearest candidate
        top_candidate = candidates[0]
        top_emp = top_candidate["employee"]
        top_dist_km = top_candidate["distance_km"]
        top_score = top_candidate["score"]

        # Final workload concurrency verification boundary
        busy_check = get_employee_active_job(top_emp)
        if busy_check:
            logger.warning(
                f"[DISPATCH_REJECT] employee={top_emp.id} job={job_obj.id} "
                f"reason=EMPLOYEE_ALREADY_BUSY active_job={busy_check.id}"
            )
            return False, f"Technician #{top_emp.id} is busy on active Job #{busy_check.id}. Cannot offer Job #{job_obj.id}."

        # Expire any previous offers for this job that might be dangling
        WorkforceJobOffer.objects.filter(job=job_obj, status=WorkforceJobOffer.Status.OFFERED).update(status=WorkforceJobOffer.Status.EXPIRED)

        # Variable offer window (Booking Dispatch Framework section 4): the
        # window flexes by booking priority, how deep the eligible pool
        # actually is, and service-category sparsity, instead of a fixed
        # five minutes for every job everywhere.
        offer_window_minutes = compute_offer_window_minutes(job_obj, len(candidates))
        expires_at = now + timedelta(minutes=offer_window_minutes)
        _maybe_signal_customer_delay(job_obj, failed_cycle_count)
        offer = WorkforceJobOffer.objects.create(
            job=job_obj,
            employee=top_emp,
            status=WorkforceJobOffer.Status.OFFERED,
            rank_score=top_score,
            expires_at=expires_at,
        )

        # Keep ServiceRequest unassigned until candidate accepts via backend atomic transaction
        if job_obj.status in ["draft", "new_request", "confirmed"]:
            apply_transition(job_obj, "unassigned")

        # Fixes X-01: let the customer know an offer went out to a technician
        # (their app deliberately does NOT surface technician details yet at
        # this stage -- see workforce_integration/views.py's
        # "technician.assigned" handler -- this is just "someone was asked").
        try:
            from workforce_api.services.customer_webhook import notify_customer_app
            notify_customer_app(
                "technician.assigned",
                job_obj,
                technician_id=str(top_emp.id),
                vendor_name=getattr(job_obj.company, "company_name", "") if getattr(job_obj, "company", None) else "",
            )
        except Exception as webhook_err:
            logger.info(f"Could not notify Customer app of offer for Job #{job_obj.id}: {webhook_err}")

        WorkforceEventLog.objects.create(
            user=top_emp.user,
            event_type="OFFER_CREATED",
            payload={"job_id": job_obj.id, "offer_id": offer.id, "employee_id": top_emp.id, "distance_km": round(top_dist_km, 2)}
        )

        loc_str = f" at {job_obj.address}" if job_obj.address else ""
        req_id_str = f" ({job_obj.request_id})" if job_obj.request_id else f" #{job_obj.id}"
        service_label = job_obj.issue_title or job_obj.service_category or "Service Request"
        expiry_str = expires_at.strftime("%H:%M:%S UTC")

        WorkforceNotification.objects.create(
            recipient=top_emp.user,
            title="New Job Offer Available!",
            message=f"You have a new exclusive job offer for '{service_label}'{req_id_str}{loc_str} ({top_dist_km:.1f} km away). Expiry: {expiry_str}. Open your dashboard to Accept or Decline.",
            notification_type="JOB_OFFER",
            company=job_obj.company,
            related_object_id=str(job_obj.id),
        )

        logger.info(
            f"[DISPATCH_DECISION] job={job_obj.id} employee={top_emp.id} "
            f"distance_km={top_dist_km:.2f} score={top_score:.1f} status=OFFER_CREATED"
        )
        return True, f"Job #{job_obj.id} offered to {top_emp.user.get_full_name() or top_emp.user.username} ({top_dist_km:.1f}km away, Score: {top_score:.1f})."


def dispatch_next_candidate(job_id_or_obj) -> Tuple[bool, str]:
    """
    Triggered when an offer is declined or expired:
    Recalculates eligibility and dispatches to the next nearest candidate.
    """
    logger.info(f"[DISPATCH_FALLBACK] Triggering fallback dispatch for Job #{job_id_or_obj}.")
    return dispatch_job(job_id_or_obj)


def expire_and_reassign_offers() -> int:
    """
    Scans for expired job offers in OFFERED state, marks them EXPIRED,
    and automatically triggers fallback dispatch for each affected job.
    Returns the count of expired offers handled.
    """
    now = timezone.now()
    expired_offers = list(
        WorkforceJobOffer.objects.filter(
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__lte=now,
        ).select_related("job")
    )

    count = 0
    for offer in expired_offers:
        with transaction.atomic():
            off_locked = WorkforceJobOffer.objects.select_for_update().filter(pk=offer.pk, status=WorkforceJobOffer.Status.OFFERED).first()
            if not off_locked:
                continue
            off_locked.status = WorkforceJobOffer.Status.EXPIRED
            off_locked.save(update_fields=["status"])
            count += 1
            logger.info(f"[DISPATCH_OFFER_EXPIRED] Offer #{offer.id} for Job #{offer.job_id} expired. Triggering fallback dispatch.")

        # Re-dispatch job outside the offer lock transaction
        dispatch_next_candidate(offer.job_id)

    return count


def dispatch_pending_jobs(company_id=None, limit: int = 50) -> Dict[str, Any]:
    """
    Core cross-application reconciliation function:
    1. Sweeps and reassigns expired offers.
    2. Discovers all dispatchable jobs in the database (regardless of which application created them).
    3. Filters out jobs that already have an active exclusive offer.
    4. Evaluates proximity and dispatches pending jobs.
    """
    # 1. Sweep expired offers first
    expired_count = expire_and_reassign_offers()

    now = timezone.now()
    qs = ServiceRequest.objects.filter(
        status__in=DISPATCHABLE_STATUSES,
        assigned_employee__isnull=True,
        latitude__isnull=False,
        longitude__isnull=False,
    )
    if company_id:
        qs = qs.filter(company_id=company_id)

    # Find all jobs in dispatchable states
    pending_jobs = list(
        qs.exclude(
            # Exclude jobs that already have an active exclusive offer
            job_offers__status=WorkforceJobOffer.Status.OFFERED,
            job_offers__expires_at__gt=now,
        ).order_by("-created_at").distinct()[:limit]
    )

    results = {
        "expired_offers_swept": expired_count,
        "pending_jobs_found": len(pending_jobs),
        "dispatched_count": 0,
        "unassigned_count": 0,
        "details": [],
    }

    for job in pending_jobs:
        logger.info(f"[DISPATCH_JOB_FOUND] Reconciling pending Job #{job.id} ({job.request_id}, status={job.status}).")
        success, msg = dispatch_job(job)
        results["details"].append({"job_id": job.id, "success": success, "message": msg})
        if success:
            results["dispatched_count"] += 1
        else:
            results["unassigned_count"] += 1

    return results


def reconsider_jobs_for_employee(employee_or_id) -> int:
    """
    Triggered when an employee transmits fresh GPS coordinates:
    Finds pending unassigned/dispatchable jobs within the employee's company
    and evaluates dispatch immediately.
    """
    emp_id = employee_or_id.pk if hasattr(employee_or_id, "pk") else employee_or_id
    emp = Employee.objects.filter(pk=emp_id).first()
    if not emp or not emp.is_active or not emp.is_online or emp.current_availability != "available" or get_employee_active_job(emp):
        return 0

    now = timezone.now()
    if emp.company_id and emp.company_id > 1:
        company_filter = Q(company_id=emp.company_id)
    else:
        company_filter = Q(company_id=1) | Q(company__isnull=True)

    pending_jobs = ServiceRequest.objects.filter(
        company_filter,
        status__in=DISPATCHABLE_STATUSES,
        assigned_employee__isnull=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).exclude(
        job_offers__status=WorkforceJobOffer.Status.OFFERED,
        job_offers__expires_at__gt=now,
    ).exclude(
        # Don't reconsider jobs the employee already declined/received
        job_offers__employee_id=emp.id,
    ).distinct()

    dispatched_count = 0
    for job in pending_jobs:
        logger.info(f"[DISPATCH_GPS_TRIGGER] Fresh GPS for Employee #{emp.id} triggered evaluation for Job #{job.id}.")
        success, msg = dispatch_job(job)
        if success:
            dispatched_count += 1

    return dispatched_count
