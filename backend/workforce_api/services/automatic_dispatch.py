"""
Authoritative Automatic Geo-Based Dispatch Service.

Single source of truth for all automatic job dispatch, candidate ranking,
proximity evaluation, offer creation, fallback re-assignment, and cross-application
job reconciliation across Workforce and Marketplace.
"""
import logging
import datetime
from datetime import timedelta
from decimal import Decimal
from typing import List, Dict, Any, Tuple, Optional

from django.db import IntegrityError, transaction
from django.db.models import Case, Count, Exists, F, IntegerField, OuterRef, Prefetch, Q, Value, When
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
# GT-C-02: maximum unsettled cash a technician may hold before they stop
# being offered further CASH-collecting work (Gate 10). Rupees. Set to 0 or
# None to disable the ceiling entirely. Override per deployment with
# settings.DISPATCH_CASH_FLOAT_CEILING.
CASH_FLOAT_CEILING = Decimal("10000.00")

MIN_OFFER_WINDOW_MINUTES = 2
MAX_OFFER_WINDOW_MINUTES = 15

# ── X-11 / GT-B-02: rapid offer window for on-demand transport ────────────
# The minute-scale window above is right for a scheduled home-services
# visit, where a technician may reasonably be mid-task when an offer
# arrives. It is far too slow for on-demand goods transport: a customer
# standing next to their load watching "finding a driver" for two minutes
# per candidate, across several candidates, is the single most visible
# way this feels unlike Porter. Those platforms run a 15-30s ladder.
#
# So transport categories get their own seconds-scale ladder, and every
# other category keeps exactly the existing minute-scale behaviour --
# this is deliberately not a platform-wide change to dispatch timing.
#
# packers_movers is NOT included: a relocation is a scheduled, surveyed
# job, not an on-demand hail, so rushing that offer would just burn
# candidates.
RAPID_DISPATCH_SERVICE_CATEGORIES = {
    "goods_transport_truck",
    "goods_transport_two_wheeler",
}
# The ladder, indexed by how many offers this job has already burned.
# Widens as the job gets harder to place, rather than hammering the same
# short window forever.
RAPID_OFFER_WINDOW_LADDER_SECONDS = [20, 25, 30]
# Thin pools get a little more room even on the fast path.
RAPID_THIN_POOL_WINDOW_BONUS_SECONDS = 10
MIN_RAPID_OFFER_WINDOW_SECONDS = 15
MAX_RAPID_OFFER_WINDOW_SECONDS = 45

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

# Semantic ring aliases for progressive radius widening tiers.
# These give test code and documentation a named tier rather than a raw number.
# Ring 1 = initial base radius; Ring 2 = after first widening; Ring 3 = after second widening.
RING_1_MAX_KM = MAX_DISPATCH_RADIUS_KM                          # 50 km
RING_2_MAX_KM = MAX_DISPATCH_RADIUS_KM + RADIUS_WIDENING_STEP_KM  # 75 km
RING_3_MAX_KM = MAX_WIDENED_DISPATCH_RADIUS_KM                  # 100 km

# After this many failed offer cycles, the customer app is told the match
# is taking longer than usual (see _maybe_signal_customer_delay below).
CUSTOMER_DELAY_SIGNAL_AFTER_CYCLES = 2

# Dispatchable database statuses.
# 'received' is the Marketplace-side equivalent of 'new_request'; both mean the booking
# has been placed and is waiting for a driver/technician assignment.
DISPATCHABLE_STATUSES = ["draft", "new_request", "confirmed", "unassigned", "assigned", "redispatching", "received", "rescheduled"]

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
    "truck": {"truck", "packer & mover", "packers & movers", "logistics", "shifting", "packers_movers", "relocation"},
    "packer & mover": {"packer & mover", "packers & movers", "truck", "shifting", "relocation", "packers_movers"},
    "packers & movers": {"packer & mover", "packers & movers", "truck", "shifting", "relocation", "packers_movers"},
    "packers_movers": {"packer & mover", "packers & movers", "truck", "shifting", "relocation", "packers_movers"},
    "shifting": {"packer & mover", "packers & movers", "truck", "shifting", "relocation", "packers_movers"},
    "relocation": {"packer & mover", "packers & movers", "truck", "shifting", "relocation", "packers_movers"},
    "goods transport": {"goods_transport", "goods & transport", "goods and transport", "goods transport", "truck", "two wheeler", "packer & mover", "packers & movers", "logistics", "shifting", "packers_movers", "relocation", "goods_transport_truck", "goods_transport_two_wheeler"},
    "goods & transport": {"goods_transport", "goods & transport", "goods and transport", "goods transport", "truck", "two wheeler", "packer & mover", "packers & movers", "logistics", "shifting", "packers_movers", "relocation", "goods_transport_truck", "goods_transport_two_wheeler"},
    "goods and transport": {"goods_transport", "goods & transport", "goods and transport", "goods transport", "truck", "two wheeler", "packer & mover", "packers & movers", "logistics", "shifting", "packers_movers", "relocation", "goods_transport_truck", "goods_transport_two_wheeler"},
    "goods_transport": {"goods_transport", "goods & transport", "goods and transport", "goods transport", "truck", "two wheeler", "packer & mover", "packers & movers", "logistics", "shifting", "packers_movers", "relocation", "goods_transport_truck", "goods_transport_two_wheeler"},
    "goods_transport_truck": {"goods_transport_truck", "truck", "mini truck", "goods & transport", "goods and transport", "goods transport", "logistics", "packer & mover", "packers & movers"},
    "goods_transport_two_wheeler": {"goods_transport_two_wheeler", "two wheeler", "bike", "scooter", "goods & transport", "goods and transport", "goods transport", "logistics"},
}


def normalize_service_category(cat: str) -> str:
    """Normalizes service category into canonical lowercase slug."""
    raw = str(cat or "").strip().lower().replace("-", "_").replace(" ", "_")
    if raw in ("truck", "mini_truck", "goods_transport_truck"):
        return "goods_transport_truck"
    if raw in ("two_wheeler", "2_wheeler", "goods_transport_two_wheeler"):
        return "goods_transport_two_wheeler"
    if raw in ("packers_movers", "packer_mover", "packers_and_movers", "shifting"):
        return "packers_movers"
    if raw in ("goods_transport", "goods_and_transport"):
        return "goods_transport"
    return raw


def parse_preferred_slot_time(preferred_time):
    """Best-effort parse of slot time into a datetime.time object."""
    if not preferred_time:
        return None
    if isinstance(preferred_time, datetime.time):
        return preferred_time
    raw = str(preferred_time).strip()
    if not raw or raw.lower() in ("asap", "immediate", "none"):
        return None
    for sep in ("-", "–", "to "):
        if sep in raw:
            raw = raw.split(sep)[0].strip()
            break
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I %p", "%I:%M%p", "%I:%M %P", "%I %P"):
        try:
            return datetime.datetime.strptime(raw.upper().replace(".", ""), fmt).time()
        except ValueError:
            continue
    return None


def get_scheduled_dispatch_window(job_obj, now=None) -> Tuple[bool, Optional[datetime.datetime], Optional[datetime.datetime]]:
    """
    Evaluates whether a ServiceRequest is scheduled for a future window.
    Only holds future-scheduled bookings when they are outside their pre-service lead time.
    Returns:
        (is_future_scheduled: bool, scheduled_start_dt: Optional[datetime], dispatch_window_open_dt: Optional[datetime])
    """
    pref_date = getattr(job_obj, "preferred_date", None)
    if not pref_date:
        return False, None, None

    business_tz = timezone.get_current_timezone()
    if now is None:
        now = timezone.localtime(timezone.now(), business_tz)
    elif timezone.is_aware(now):
        now = timezone.localtime(now, business_tz)
    else:
        now = timezone.make_aware(now, business_tz)
    today = now.date()

    if pref_date < today:
        # Date in the past -> immediate
        return False, None, None

    category = normalize_service_category(getattr(job_obj, "service_category", "") or "")
    if category == "packers_movers":
        lead_minutes = getattr(settings, "PM_SCHEDULED_DISPATCH_LEAD_MINUTES", 120)
    else:
        lead_minutes = getattr(settings, "GT_SCHEDULED_DISPATCH_LEAD_MINUTES", 45)

    slot_time = parse_preferred_slot_time(getattr(job_obj, "preferred_time", None))

    if pref_date == today:
        if slot_time is None:
            # Same day without a specific future time slot -> immediate booking
            return False, None, None
        naive_dt = datetime.datetime.combine(today, slot_time)
        scheduled_dt = timezone.make_aware(naive_dt, business_tz) if timezone.is_naive(naive_dt) else naive_dt
        window_open = scheduled_dt - timedelta(minutes=lead_minutes)
        if now < window_open:
            return True, scheduled_dt, window_open
        return False, scheduled_dt, window_open

    # Future date (pref_date > today)
    if slot_time is None:
        # Default to 09:00 AM local time on future date
        slot_time = datetime.time(9, 0)
    naive_dt = datetime.datetime.combine(pref_date, slot_time)
    scheduled_dt = timezone.make_aware(naive_dt, business_tz) if timezone.is_naive(naive_dt) else naive_dt
    window_open = scheduled_dt - timedelta(minutes=lead_minutes)
    if now < window_open:
        return True, scheduled_dt, window_open
    return False, scheduled_dt, window_open


def canonical_service_match(requested_service: str, approved_services: List[str], verified_skills: List[str]) -> Tuple[bool, str, str]:
    """
    Evaluates whether a requested service matches an employee's authorized services or verified skills.
    Returns (is_match, match_method, matched_term).
    """
    if not requested_service:
        return True, "EMPTY_SERVICE_BYPASS", ""

    def normalize_term(t):
        return (
            str(t or "")
            .lower()
            .replace("—", " ")
            .replace("-", " ")
            .replace("_", " ")
            .replace("&", "and")
            .strip()
        )

    req_clean = normalize_term(requested_service)
    req_words = set(w for w in req_clean.split() if len(w) >= 2)

    # 1. Check exact or direct match against approved employee services
    for it in approved_services:
        if not it:
            continue
        it_clean = normalize_term(it)
        if req_clean == it_clean or req_clean in it_clean or it_clean in req_clean:
            return True, "EXACT_OR_SUBSTRING_SERVICE", it
        it_words = set(w for w in it_clean.split() if len(w) >= 2)
        if ("goods" in req_words and "transport" in req_words) and ("goods" in it_words and "transport" in it_words):
            return True, "GOODS_TRANSPORT_CATEGORY_MATCH", it

    # 2. Check verified skills
    for sk in verified_skills:
        if not sk:
            continue
        sk_clean = normalize_term(sk)
        if req_clean == sk_clean or req_clean in sk_clean or sk_clean in req_clean:
            return True, "VERIFIED_SKILL_MATCH", sk
        sk_words = set(w for w in sk_clean.split() if len(w) >= 2)
        if ("goods" in req_words and "transport" in req_words) and ("goods" in sk_words and "transport" in sk_words):
            return True, "GOODS_TRANSPORT_SKILL_MATCH", sk

    # 3. Check explicit canonical alias table
    for alias_key, alias_group in EXPLICIT_SERVICE_ALIASES.items():
        alias_key_clean = normalize_term(alias_key)
        alias_group_clean = {normalize_term(a) for a in alias_group}
        # If requested service matches this alias key/group
        if req_clean == alias_key_clean or req_clean in alias_group_clean or any(req_word in alias_group_clean for req_word in req_words):
            # Check if employee has any matching service in that alias group
            for it in approved_services:
                it_clean = normalize_term(it)
                if it_clean in alias_group_clean or any(w in alias_group_clean for w in it_clean.split() if len(w) >= 2):
                    return True, "EXPLICIT_ALIAS_SERVICE", it
            for sk in verified_skills:
                sk_clean = normalize_term(sk)
                if sk_clean in alias_group_clean or any(w in alias_group_clean for w in sk_clean.split() if len(w) >= 2):
                    return True, "EXPLICIT_ALIAS_SKILL", sk

    return False, "NO_MATCH", ""


class DispatchRaceLost(Exception):
    """
    Raised when the database's unique_active_job_offer_per_employee
    constraint fires because a concurrent dispatcher offered this
    technician another job first.

    A dedicated exception rather than a bare return because it has to
    escape the surrounding transaction.atomic() block -- once IntegrityError
    has fired, that transaction is poisoned and no further queries may run
    inside it. dispatch_job() catches this OUTSIDE the atomic block and
    turns it back into an ordinary (False, reason) result, so the job stays
    dispatchable for the next sweep rather than surfacing a 500.
    """


def employees_with_live_offers(exclude_job=None):
    """
    Ids of technicians who currently hold an OFFERED, unexpired job offer.

    Dispatch concurrency: two dispatch_job() runs for DIFFERENT jobs each
    lock only their own ServiceRequest row, so they do not exclude one
    another. Without this, both can rank the same idle technician first and
    both try to offer them a job at the same moment. Until now the ONLY
    thing preventing that was the unique_active_job_offer_per_employee
    constraint in the database -- and hitting it raised IntegrityError out
    of dispatch rather than gracefully moving to the next candidate.

    This is the application-level half of that guard. The DB constraint
    stays exactly where it is: this reduces collisions, the row lock in
    dispatch_job() serialises the ones that remain, and the constraint is
    the final backstop. Nothing here weakens the existing protection.
    """
    qs = WorkforceJobOffer.objects.filter(
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__gt=timezone.now(),
    )
    if exclude_job is not None:
        qs = qs.exclude(job=exclude_job)
    return set(qs.values_list("employee_id", flat=True))


def check_candidate_eligibility(emp: Employee, service_name: Optional[str] = None, job: Optional[Any] = None) -> Tuple[bool, str, Dict[str, bool]]:
    """
    10-Gate Employee Eligibility Engine:
    Authoritative server-side evaluation of 10 mandatory operational gates.
    Every gate fails closed.
    Returns (is_eligible, reason_message, gate_results_dict).
    """
    gate_results = {f"G{i}": True for i in range(1, 11)}

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
    service_name_clean = (service_name or "").strip().lower()

    if emp and getattr(emp, "company_id", None):
        from workforce_api.models import WorkforceRequiredDocument, WorkforceEmployeeDocument
        mandatory_doc_reqs = WorkforceRequiredDocument.objects.filter(company_id=emp.company_id, is_mandatory=True)
        # GT-A-02: a requirement with a non-empty applies_to_categories only
        # gates jobs in one of those categories (e.g. Driving Licence should
        # not block a technician from taking an AC-repair job). A requirement
        # with an empty list (the default, and every pre-existing row) keeps
        # applying to every job, exactly as before this field existed.
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
    else:
        documents = onboarding.get("documents", {})
        if any(doc.get("status") in ["rejected", "pending_review", "missing"] for doc in documents.values()):
            gate_results["G3"] = False
            return False, "Gate 3: Technician has unapproved dossier documents.", gate_results

    # GT-A-01/GT-A-02: for logistics jobs specifically, also require at
    # least one active Vehicle on file whose insurance/permit/PUC are all
    # current. Applies to all employees (company-affiliated or platform).
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
            if s.get("category_name"):
                approved_svcs.append(s["category_name"])

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

    # ── Gate 10: Cash Float Ceiling (GT-C-02) ──────────────────────────────────
    # A technician on cash-on-service jobs accumulates company money they
    # have not yet handed in. The settlement half of GT-C-02 already
    # existed (CashSettlement + compute_outstanding_cash), but nothing
    # ever acted on the number: a technician could keep taking cash jobs
    # while holding an unbounded and growing amount of the company's cash.
    # This is the exposure limit -- above the ceiling they stop being
    # offered new work until they settle up.
    #
    # Scoped to cash-collecting work only: a technician over the ceiling is
    # still eligible for prepaid/online jobs, because those add no further
    # cash exposure. Blocking them from all work would punish the company
    # twice over.
    #
    # Fails OPEN, unlike every other gate here. A ceiling check is a
    # financial-risk control, not a safety or compliance one, and if the
    # payment tables are unreadable the right outcome is that customers
    # still get drivers -- with the failure logged loudly -- rather than
    # dispatch silently going dark platform-wide.
    cash_ceiling = getattr(settings, "DISPATCH_CASH_FLOAT_CEILING", CASH_FLOAT_CEILING)
    # When we know the job, only apply the ceiling to cash-collecting work.
    # With no job in hand (the standalone eligibility-check endpoints) the
    # ceiling is applied -- the conservative reading of an unknown job.
    job_is_cash = True
    if job is not None:
        job_is_cash = str(getattr(job, "payment_method", "") or "").upper() in ("COD", "CASH", "CASH_ON_SERVICE")
    if job_is_cash and cash_ceiling is not None and cash_ceiling > 0:
        try:
            from workforce_api.services.cash_reconciliation import compute_outstanding_cash

            outstanding, _qs = compute_outstanding_cash(emp)
            if outstanding is not None and Decimal(outstanding) > Decimal(str(cash_ceiling)):
                gate_results["G10"] = False
                logger.info(
                    f"[DISPATCH_REJECT] employee={emp.id} reason=CASH_FLOAT_CEILING_EXCEEDED "
                    f"outstanding={outstanding} ceiling={cash_ceiling}"
                )
                return (
                    False,
                    (
                        f"Gate 10: Technician is holding {outstanding} in unsettled cash, "
                        f"above the {cash_ceiling} float ceiling. Settle cash to resume cash jobs."
                    ),
                    gate_results,
                )
        except Exception as exc:
            # See the fail-open note above.
            logger.warning(
                f"[DISPATCH_GATE10_UNAVAILABLE] employee={getattr(emp, 'id', None)} "
                f"could not evaluate cash float ceiling, allowing: {exc}"
            )

    return True, "All 10 Eligibility Gates Passed", gate_results


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
    # Technicians already holding a live offer for some OTHER job -- see
    # employees_with_live_offers() for why this matters.
    _employees_holding_offers = employees_with_live_offers(exclude_job=job_obj)

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

        # Dispatch concurrency: skip anyone already holding a live offer for
        # a DIFFERENT job. Cheap, and it keeps two concurrent dispatchers
        # from converging on the same technician in the first place.
        if emp.id in _employees_holding_offers:
            logger.info(
                f"[DISPATCH_REJECT] employee={emp.id} reason=ALREADY_HAS_LIVE_OFFER"
            )
            continue

        # Check eligibility against service_category, then issue_title
        is_eligible, reason, gate_results = check_candidate_eligibility(emp, job_obj.service_category, job=job_obj)
        if not is_eligible and job_obj.issue_title:
            is_eligible, reason, gate_results = check_candidate_eligibility(emp, job_obj.issue_title, job=job_obj)

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


def compute_offer_window_seconds(job_obj, pool_size: int, failed_cycles: int = 0) -> int:
    """
    X-11 / GT-B-02: how long a single exclusive offer stays open, in
    SECONDS.

    This is the function dispatch should use. For an on-demand transport
    category it returns a Porter-style short window from
    RAPID_OFFER_WINDOW_LADDER_SECONDS -- roughly 20-30s, widening as the
    job burns candidates, with a bonus when the pool is thin. For every
    other category it returns exactly what compute_offer_window_minutes()
    already returned, converted to seconds, so home-services dispatch
    timing is completely unchanged.

    Kept separate from compute_offer_window_minutes() rather than
    replacing it: that function is called elsewhere and its minute-scale
    contract is relied on, so this wraps it instead of changing it.
    """
    category = (getattr(job_obj, "service_category", "") or "").strip().lower()
    rapid_categories = getattr(
        settings, "DISPATCH_RAPID_SERVICE_CATEGORIES", RAPID_DISPATCH_SERVICE_CATEGORIES
    )
    if category not in rapid_categories:
        return compute_offer_window_minutes(job_obj, pool_size) * 60

    ladder = getattr(
        settings, "DISPATCH_RAPID_OFFER_WINDOW_LADDER_SECONDS", RAPID_OFFER_WINDOW_LADDER_SECONDS
    )
    if not ladder:
        return compute_offer_window_minutes(job_obj, pool_size) * 60

    index = min(max(int(failed_cycles or 0), 0), len(ladder) - 1)
    seconds = ladder[index]

    thin_threshold = getattr(settings, "DISPATCH_THIN_POOL_CANDIDATE_THRESHOLD", THIN_POOL_CANDIDATE_THRESHOLD)
    if pool_size <= thin_threshold:
        seconds += getattr(
            settings, "DISPATCH_RAPID_THIN_POOL_WINDOW_BONUS_SECONDS", RAPID_THIN_POOL_WINDOW_BONUS_SECONDS
        )

    min_seconds = getattr(settings, "DISPATCH_MIN_RAPID_OFFER_WINDOW_SECONDS", MIN_RAPID_OFFER_WINDOW_SECONDS)
    max_seconds = getattr(settings, "DISPATCH_MAX_RAPID_OFFER_WINDOW_SECONDS", MAX_RAPID_OFFER_WINDOW_SECONDS)
    return max(min_seconds, min(max_seconds, seconds))


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


def dispatch_job(job_id_or_obj, max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS, exclude_employee_ids: Optional[List[int]] = None, **kwargs) -> Tuple[bool, str]:
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

    try:
        return _dispatch_job_locked(job_id, max_gps_age_seconds, exclude_employee_ids)
    except DispatchRaceLost as race:
        # Lost the offer race to a concurrent dispatcher. Not an error
        # condition: the job simply stays dispatchable and the next sweep
        # picks it up. Handled out here because the transaction inside is
        # already rolled back by the time this arrives.
        return False, str(race)


def _dispatch_job_locked(job_id, max_gps_age_seconds, exclude_employee_ids):
    from workforce_api.models import WorkforceEventLog

    with transaction.atomic():
        job_obj = ServiceRequest.objects.select_for_update().filter(pk=job_id).first()
        if not job_obj:
            return False, "Job not found."

        if job_obj.status in ["completed", "cancelled", "rejected"]:
            return False, f"Job #{job_id} is {job_obj.status} and cannot be dispatched."

        if getattr(job_obj, "cargo_safety_status", None) == "rejected":
            return False, f"Job #{job_id} was rejected for prohibited cargo and cannot be dispatched."

        if job_obj.status in ["accepted", "on_the_way", "arrived", "in_progress"] and job_obj.assigned_employee:
            return False, f"Job #{job_id} is already accepted and in progress with Employee #{job_obj.assigned_employee_id}."

        now = timezone.now()

        # Gate: Scheduled Job Hold (Safety Gate against premature dispatch)
        is_future, scheduled_dt, window_open = get_scheduled_dispatch_window(job_obj, now=now)
        if is_future:
            logger.info(
                f"[DISPATCH_SCHEDULED_HOLD] Job #{job_id} is scheduled for {scheduled_dt.isoformat()}. "
                f"Dispatch window opens at {window_open.isoformat()}. Holding job."
            )
            return True, f"Scheduled job held: service is at {scheduled_dt.strftime('%Y-%m-%d %H:%M')}; dispatch window opens at {window_open.strftime('%H:%M')}."

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

        # Walk the ranked candidates rather than only ever trying the top
        # one. Previously a single rejection at this final boundary failed
        # the whole dispatch run, even with other eligible technicians
        # standing right behind -- and the "rejection" is now much more
        # likely, because a concurrent dispatcher may legitimately have
        # taken the top candidate microseconds ago.
        top_candidate = None
        top_emp = None
        top_dist_km = None
        top_score = None
        _skipped = []

        for _candidate in candidates:
            _emp = _candidate["employee"]

            # Final workload concurrency verification boundary
            busy_check = get_employee_active_job(_emp)
            if busy_check:
                logger.warning(
                    f"[DISPATCH_REJECT] employee={_emp.id} job={job_obj.id} "
                    f"reason=EMPLOYEE_ALREADY_BUSY active_job={busy_check.id}"
                )
                _skipped.append(f"#{_emp.id} busy")
                continue

            # Dispatch concurrency guard, the serialising half.
            #
            # Lock this technician's row before deciding to offer them the
            # job. Two dispatch_job() runs for different jobs hold locks on
            # different ServiceRequest rows, so they do not exclude each
            # other -- but they DO both need this employee row, so whoever
            # gets it first wins and the second blocks here until the first
            # has committed its offer. The re-check below then sees that
            # offer and moves on to its next candidate.
            #
            # This is deliberately IN ADDITION to the database's
            # unique_active_job_offer_per_employee constraint, which is left
            # in place untouched: application guard first, constraint as the
            # backstop.
            _locked = Employee.objects.select_for_update().filter(pk=_emp.pk).first()
            if _locked is None:
                _skipped.append(f"#{_emp.id} vanished")
                continue

            _live_offer = WorkforceJobOffer.objects.filter(
                employee=_locked,
                status=WorkforceJobOffer.Status.OFFERED,
                expires_at__gt=timezone.now(),
            ).exclude(job=job_obj).first()
            if _live_offer:
                logger.info(
                    f"[DISPATCH_REJECT] employee={_emp.id} job={job_obj.id} "
                    f"reason=ALREADY_HAS_LIVE_OFFER offer={_live_offer.id} "
                    f"other_job={_live_offer.job_id}"
                )
                _skipped.append(f"#{_emp.id} already offered job #{_live_offer.job_id}")
                continue

            top_candidate = _candidate
            top_emp = _locked
            top_dist_km = _candidate["distance_km"]
            top_score = _candidate["score"]
            break

        if top_emp is None:
            reason = "; ".join(_skipped) or "no candidate passed the final concurrency check"
            logger.info(f"[DISPATCH_NO_CANDIDATE] job={job_obj.id} {reason}")
            _maybe_signal_customer_delay(job_obj, failed_cycle_count)
            return False, f"No technician could be offered Job #{job_obj.id} right now ({reason})."

        # Expire any previous offers for this job that might be dangling
        WorkforceJobOffer.objects.filter(job=job_obj, status=WorkforceJobOffer.Status.OFFERED).update(status=WorkforceJobOffer.Status.EXPIRED)

        # Variable offer window (Booking Dispatch Framework section 4): the
        # window flexes by booking priority, how deep the eligible pool
        # actually is, and service-category sparsity, instead of a fixed
        # five minutes for every job everywhere.
        # X-11 / GT-B-02: seconds, not minutes. For on-demand transport
        # categories this is a Porter-style ~20-30s ladder that widens as
        # the job burns candidates; every other category gets exactly the
        # previous minute-scale window, converted.
        offer_window_seconds = compute_offer_window_seconds(
            job_obj, len(candidates), failed_cycles=failed_cycle_count
        )
        expires_at = now + timedelta(seconds=offer_window_seconds)
        _maybe_signal_customer_delay(job_obj, failed_cycle_count)
        try:
            offer = WorkforceJobOffer.objects.create(
                job=job_obj,
                employee=top_emp,
                status=WorkforceJobOffer.Status.OFFERED,
                rank_score=top_score,
                expires_at=expires_at,
            )
        except IntegrityError:
            # The unique_active_job_offer_per_employee constraint fired --
            # the database's backstop caught a race the guards above did not.
            # Previously this propagated out of dispatch as an unhandled
            # IntegrityError; now it fails this run cleanly so the job stays
            # dispatchable and the next sweep can offer it to someone else.
            # Re-raised inside the atomic block would poison the transaction,
            # so nothing further is attempted here.
            logger.warning(
                f"[DISPATCH_RACE_LOST] job={job_obj.id} employee={top_emp.id} "
                f"lost the offer race to a concurrent dispatcher; will retry next sweep."
            )
            raise DispatchRaceLost(
                f"Technician #{top_emp.id} was offered another job concurrently."
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

    business_tz = timezone.get_current_timezone()
    local_now = timezone.localtime(now, business_tz) if timezone.is_aware(now) else timezone.make_aware(now, business_tz)
    today = local_now.date()

    # Exclude jobs scheduled far in the future (> tomorrow).
    # Since maximum dispatch lead time is 120 minutes (2 hours), any job scheduled
    # beyond tomorrow cannot enter its dispatch window in this cycle.
    # Excluding far-future jobs prevents head-of-line queue starvation.
    qs = qs.filter(
        Q(preferred_date__isnull=True) | Q(preferred_date__lte=today + timedelta(days=1))
    )

    # Prioritize immediate / overdue / open-window jobs ahead of held future-scheduled jobs:
    # Urgency Rank 0: Immediate bookings (preferred_date is NULL, or in past, or today with no specific slot)
    # Urgency Rank 1: Scheduled bookings (specific slot today or tomorrow)
    urgency_rank = Case(
        When(preferred_date__isnull=True, then=Value(0)),
        When(preferred_date__lt=today, then=Value(0)),
        When(Q(preferred_date=today) & (Q(preferred_time__isnull=True) | Q(preferred_time="")), then=Value(0)),
        default=Value(1),
        output_field=IntegerField(),
    )

    candidate_qs = (
        qs.exclude(
            # Exclude jobs that already have an active exclusive offer
            job_offers__status=WorkforceJobOffer.Status.OFFERED,
            job_offers__expires_at__gt=now,
        )
        .annotate(urgency_rank=urgency_rank)
        .order_by(
            F("urgency_rank").asc(),
            F("preferred_date").asc(nulls_first=True),
            F("created_at").asc(),
        )
        .distinct()
    )

    results = {
        "expired_offers_swept": expired_count,
        "pending_jobs_found": 0,
        "dispatched_count": 0,
        "unassigned_count": 0,
        "details": [],
    }

    evaluated_actionable_count = 0
    # Fetch an initial batch of candidates (up to max(limit * 3, 50)) to allow skipping held future jobs
    # without starving actionable immediate jobs behind them.
    batch_size = max(limit * 3, 50)
    candidate_jobs = list(candidate_qs[:batch_size])
    results["pending_jobs_found"] = len(candidate_jobs)

    for job in candidate_jobs:
        is_future, _, _ = get_scheduled_dispatch_window(job, now=now)
        if is_future:
            logger.info(f"[DISPATCH_PENDING_SCHEDULED_HELD] Job #{job.id} held outside scheduled dispatch window.")
            continue

        evaluated_actionable_count += 1
        logger.info(f"[DISPATCH_JOB_FOUND] Reconciling pending Job #{job.id} ({job.request_id}, status={job.status}).")
        success, msg = dispatch_job(job)
        results["details"].append({"job_id": job.id, "success": success, "message": msg})
        if success:
            results["dispatched_count"] += 1
        else:
            results["unassigned_count"] += 1

        if evaluated_actionable_count >= limit:
            break

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
    ).order_by(
        F("preferred_date").asc(nulls_first=True),
        F("created_at").asc(),
    ).distinct()

    dispatched_count = 0
    for job in pending_jobs:
        logger.info(f"[DISPATCH_GPS_TRIGGER] Fresh GPS for Employee #{emp.id} triggered evaluation for Job #{job.id}.")
        success, msg = dispatch_job(job)
        if success:
            dispatched_count += 1

    return dispatched_count


def reconcile_booking_for_dispatch(service_request, *args, **kwargs) -> Tuple[bool, str]:
    """
    Semantic alias for dispatch_job() using the ServiceRequest (booking) perspective.

    Both functions perform identical work: evaluate candidates and create a job
    offer for the given booking.  The name reconcile_booking_for_dispatch is used
    in documentation, webhooks, and test code to describe the action from the
    booking / marketplace side; dispatch_job() is the implementation name used
    internally.  Keeping both names prevents brittle import errors when either
    term appears in calling code.
    """
    return dispatch_job(service_request, *args, **kwargs)
