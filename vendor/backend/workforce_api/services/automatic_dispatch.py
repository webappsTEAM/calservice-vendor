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
    WorkforceJobLifecycleEvent,
    WorkforceNotification,
    WorkforceEmployeeSkill,
    WorkforceEmployeeCompliance,
    WorkforceEmployeeSchedule,
    WorkforceDispatchState,
    WorkforceEventLog,
)
from time_tracking.geo import haversine_distance
from workforce_api.services.workload import get_employee_active_job, ACTIVE_WORKLOAD_STATUSES

logger = logging.getLogger("workforce.dispatch")

# GPS telemetry freshness requirement (configurable, default 1 hour / 3600 seconds for active shifts)
MAX_GPS_AGE_SECONDS = int(getattr(settings, "DISPATCH_MAX_GPS_AGE_SECONDS", 3600))

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


def get_booking_discovery_scope(company=None):
    """
    Backwards-compatible helper for company-scoped job discovery.
    """
    if not company:
        return Q()
    return Q(company=company)


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
    "painting": {"painting", "paintings", "painter", "interior painting", "exterior painting", "waterproofing", "wood & metal", "texture decor", "wall painting", "house painting", "epoxy flooring", "industrial epoxy flooring", "whitewash", "distemper", "emulsion", "primer"},
    "paintings": {"painting", "paintings", "painter", "interior painting", "exterior painting", "waterproofing", "wood & metal", "texture decor", "wall painting", "house painting", "epoxy flooring", "industrial epoxy flooring", "whitewash", "distemper", "emulsion", "primer"},
    "interior painting": {"painting", "paintings", "painter", "interior painting", "wall painting", "whitewash", "emulsion"},
    "exterior painting": {"painting", "paintings", "painter", "exterior painting", "weatherproof", "emulsion"},
    "waterproofing": {"painting", "paintings", "waterproofing", "dampness treatment", "tar sheet", "terrace waterproofing"},
    "wood & metal": {"painting", "paintings", "wood & metal", "wood and metal", "enamel painting", "pu coating"},
    "texture decor": {"painting", "paintings", "texture decor", "texture painting", "stencil design", "royal play"},
    "mason": {"mason", "masonry", "tile fixing", "bathroom tile fixing", "minor masonry", "small construction work", "brick & block work", "plastering & wall repair", "wall & partition construction", "wall breaking & demolition", "civil work", "flooring", "tiling", "civil"},
    "masonry": {"mason", "masonry", "tile fixing", "bathroom tile fixing", "minor masonry", "small construction work", "brick & block work", "plastering & wall repair", "wall & partition construction", "wall breaking & demolition", "civil work", "flooring", "tiling", "civil"},
    "bathroom tile fixing": {"mason", "masonry", "tile fixing", "bathroom tile fixing", "tiling", "flooring", "civil"},
    "minor masonry": {"mason", "masonry", "minor masonry", "small construction work", "brick & block work", "plastering & wall repair", "civil work", "civil"},
    "brick & block work": {"mason", "masonry", "brick & block work", "brick work", "block work", "civil work", "civil"},
    "plastering & wall repair": {"mason", "masonry", "plastering & wall repair", "plastering", "wall repair", "civil work", "civil"},
    "wall & partition construction": {"mason", "masonry", "wall & partition construction", "partition work", "civil work", "civil"},
    "wall breaking & demolition": {"mason", "masonry", "wall breaking & demolition", "demolition", "civil work", "civil"},
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
    if raw in ("paintings", "painting", "interior_painting", "exterior_painting", "waterproofing", "texture_decor", "wood_metal"):
        return "painting"
    if raw in ("mason", "masonry", "bathroom_tile_fixing", "minor_masonry", "brick_block_work", "plastering_wall_repair", "wall_partition_construction", "wall_breaking_demolition"):
        return "mason"
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


class ScheduledDispatchWindow(tuple):
    """
    Backwards-compatible 3-tuple: (is_future, scheduled_dt, window_open)
    with named attribute properties:
      - is_future: bool (True if before window_open, i.e. held)
      - scheduled_dt: Optional[datetime.datetime]
      - window_open: Optional[datetime.datetime] (T - 1 hour)
      - window_close: Optional[datetime.datetime] (T + 1 hour)
      - is_closed: bool (True if now > window_close)
      - is_eligible: bool (True if window_open <= now <= window_close)
    """
    def __new__(cls, is_future: bool, scheduled_dt: Optional[datetime.datetime],
                window_open: Optional[datetime.datetime],
                window_close: Optional[datetime.datetime] = None,
                is_closed: bool = False, is_eligible: bool = True):
        obj = super().__new__(cls, (is_future, scheduled_dt, window_open))
        obj.is_future = is_future
        obj.scheduled_dt = scheduled_dt
        obj.window_open = window_open
        obj.window_close = window_close
        obj.is_closed = is_closed
        obj.is_eligible = is_eligible
        return obj


def get_scheduled_dispatch_window(job_obj, now=None) -> ScheduledDispatchWindow:
    """
    Canonical single source of truth for scheduled dispatch timing.
    Calculates scheduled window: [scheduled_time - 1 hour, scheduled_time + 1 hour].
    - Before window_open (T - 1 hour): is_future=True, is_eligible=False, is_closed=False (held)
    - Within window [T - 1 hr, T + 1 hr]: is_future=False, is_eligible=True, is_closed=False (eligible)
    - After window_close (T + 1 hr): is_future=False, is_eligible=False, is_closed=True (closed)
    - Immediate bookings (no scheduled time or ASAP): is_future=False, is_eligible=True, is_closed=False
    """
    pref_date = getattr(job_obj, "preferred_date", None)
    if not pref_date:
        return ScheduledDispatchWindow(False, None, None, None, is_closed=False, is_eligible=True)

    company = getattr(job_obj, "company", None)
    co_tz_str = getattr(company, "timezone", None) if company else None
    operational_tz = None
    if co_tz_str and co_tz_str.upper() != "UTC":
        try:
            import zoneinfo
            operational_tz = zoneinfo.ZoneInfo(co_tz_str)
        except Exception:
            pass

    if operational_tz is None:
        try:
            import zoneinfo
            operational_tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        except Exception:
            operational_tz = timezone.get_current_timezone()

    # Normalize `now` to operational_tz
    if now is None:
        now = timezone.now().astimezone(operational_tz)
    else:
        if timezone.is_naive(now):
            now = timezone.make_aware(now, operational_tz)
        else:
            now = now.astimezone(operational_tz)

    today = now.date()

    if pref_date < today:
        # Date in the past -> offer window closed
        return ScheduledDispatchWindow(False, None, None, None, is_closed=True, is_eligible=False)

    slot_time = parse_preferred_slot_time(getattr(job_obj, "preferred_time", None))

    if pref_date == today and slot_time is None:
        # Same day without a specific future time slot -> immediate booking
        return ScheduledDispatchWindow(False, None, None, None, is_closed=False, is_eligible=True)

    if slot_time is None:
        # Future date (pref_date > today) without slot defaults to 09:00 AM local operational time
        slot_time = datetime.time(9, 0)

    naive_dt = datetime.datetime.combine(pref_date, slot_time)
    scheduled_dt = naive_dt.replace(tzinfo=operational_tz)
    window_open = scheduled_dt - timedelta(hours=1)
    window_close = scheduled_dt + timedelta(hours=1)

    if now < window_open:
        # Before T - 1 hour: not dispatchable yet (held)
        return ScheduledDispatchWindow(True, scheduled_dt, window_open, window_close, is_closed=False, is_eligible=False)

    if now > window_close:
        # After T + 1 hour: offer window closed; no new offers
        return ScheduledDispatchWindow(False, scheduled_dt, window_open, window_close, is_closed=True, is_eligible=False)

    # Within [T - 1 hour, T + 1 hour]: dispatchable / eligible for new job offer
    return ScheduledDispatchWindow(False, scheduled_dt, window_open, window_close, is_closed=False, is_eligible=True)


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


def check_candidate_eligibility(
    emp: Employee,
    service_name: Optional[str] = None,
    job: Optional[Any] = None,
    purpose: str = "offer_reception",
    **kwargs,
) -> Tuple[bool, str, Dict[str, bool]]:
    """
    10-Gate Employee Eligibility Engine:
    Authoritative server-side evaluation of 10 mandatory operational gates.
    Supports two purposes:
      - purpose="offer_reception": technician must be online; busy technicians
        can receive and view incoming offers (Gate 9 passes).
      - purpose="acceptance": technician must be online/available and have NO
        conflicting active workload (Gate 9 fails if busy).
    Every gate fails closed.
    Returns (is_eligible, reason_message, gate_results_dict).
    """
    check_workload = kwargs.get("check_workload", None)
    is_for_acceptance = (purpose == "acceptance") or (check_workload is True)
    gate_results = {f"G{i}": True for i in range(1, 11)}

    from service_requests.models import ServiceRequest
    if isinstance(service_name, ServiceRequest) or (service_name is not None and hasattr(service_name, "service_category")):
        if job is None:
            job = service_name
        service_name = getattr(service_name, "service_category", "") or getattr(service_name, "issue_title", "")

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
    if is_for_acceptance:
        if not emp.is_online or emp.current_availability != "available":
            gate_results["G7"] = False
            logger.debug(f"[9GATE_REJECT_GATE7_PRESENCE_OFFLINE] Employee #{emp.id} presence is is_online={emp.is_online}, avail={emp.current_availability}.")
            return False, "Gate 7: Technician is currently OFFLINE or unavailable.", gate_results
    else:
        # For offer reception: technician must be online; busy technicians are allowed to receive offers
        if not emp.is_online:
            gate_results["G7"] = False
            logger.debug(f"[9GATE_REJECT_GATE7_PRESENCE_OFFLINE] Employee #{emp.id} presence is is_online={emp.is_online}.")
            return False, "Gate 7: Technician is currently OFFLINE.", gate_results

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
    if is_for_acceptance:
        from workforce_api.services.workload import get_employee_active_job
        active_job = get_employee_active_job(emp)
        if active_job:
            gate_results["G9"] = False
            logger.info(
                f"[DISPATCH_REJECT] employee={emp.id} reason=EMPLOYEE_ALREADY_BUSY active_job={active_job.id}"
            )
            return False, f"Gate 9: Technician is busy on active Job #{active_job.id} ({active_job.request_id}).", gate_results
    else:
        # For offer reception: a technician can receive and view incoming offers while executing another job
        gate_results["G9"] = True

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


def can_receive_offer(emp: Employee, job_obj: Any) -> Tuple[bool, str]:
    """
    Authoritative check: can technician RECEIVE and VIEW an incoming offer for job_obj?
    Preserves all qualification, tenant, GPS, compliance, schedule, leave, and cash gates.
    Allows busy technicians who are online to receive offers.
    """
    if not emp:
        return False, "Employee not found."
    job_id = getattr(job_obj, "id", None) or getattr(job_obj, "pk", None)
    if job_id:
        try:
            has_same_job_offer = WorkforceJobOffer.objects.filter(
                job_id=job_id,
                employee=emp,
                status__in=["OFFERED", "REJECTED", "DECLINED", "ACCEPTED"]
            ).exists()
            if has_same_job_offer:
                return False, f"Employee #{getattr(emp, 'id', None)} already has offer history for Job #{job_id}."
        except Exception:
            pass

    is_eligible, reason, _ = check_candidate_eligibility(
        emp,
        service_name=getattr(job_obj, "service_category", None),
        job=job_obj,
        purpose="offer_reception",
    )
    if not is_eligible and getattr(job_obj, "issue_title", None):
        is_eligible, reason, _ = check_candidate_eligibility(
            emp,
            service_name=job_obj.issue_title,
            job=job_obj,
            purpose="offer_reception",
        )
    return is_eligible, reason


def can_accept_offer(emp: Employee, job_obj: Any) -> Tuple[bool, str]:
    """
    Authoritative check: can technician ACCEPT an offer for job_obj?
    Enforces workload concurrency: technician cannot accept while having an active conflicting job.
    """
    if not emp:
        return False, "Employee not found."
    from workforce_api.services.workload import get_employee_active_job
    active_job = get_employee_active_job(emp)
    if active_job and active_job.id != getattr(job_obj, "id", None):
        return False, f"Technician already has an active assigned Job #{active_job.id}."

    is_eligible, reason, _ = check_candidate_eligibility(
        emp,
        service_name=getattr(job_obj, "service_category", None),
        job=job_obj,
        purpose="acceptance",
    )
    if not is_eligible and getattr(job_obj, "issue_title", None):
        is_eligible, reason, _ = check_candidate_eligibility(
            emp,
            service_name=job_obj.issue_title,
            job=job_obj,
            purpose="acceptance",
        )
    return is_eligible, reason


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
        candidates_qs = candidates_qs.filter(Q(company_id=1) | Q(company__isnull=True) | Q(company_id__gt=1))
    else:
        candidates_qs = candidates_qs.filter(company_id=job_obj.company_id)

    # Exclude candidates who have already received or rejected/declined/cancelled an offer for this job, or explicitly excluded
    previous_offers = set(
        WorkforceJobOffer.objects.filter(
            job=job_obj,
            status__in=["OFFERED", "REJECTED", "DECLINED", "CANCELLED", "ACCEPTED"]
        ).values_list("employee_id", flat=True)
    )
    if exclude_employee_ids:
        previous_offers.update(exclude_employee_ids)

    # Permanent historical exclusion: an employee who declined/rejected this job is never eligible
    declined_history_subquery = WorkforceJobOffer.objects.filter(
        job=job_obj,
        employee=OuterRef("pk"),
        status__in=[WorkforceJobOffer.Status.REJECTED, WorkforceJobOffer.Status.DECLINED],
    )
    candidates_qs = candidates_qs.exclude(Exists(declined_history_subquery))
    candidates_qs = candidates_qs.exclude(
        Exists(
            WorkforceJobLifecycleEvent.objects.filter(
                job=job_obj,
                employee=OuterRef("pk"),
                event_type="EMPLOYEE_JOB_DECLINED",
            )
        )
    )
    if previous_offers:
        candidates_qs = candidates_qs.exclude(pk__in=previous_offers)

    ranked_candidates = []
    now = timezone.now()
    # Technicians already holding a live offer for some OTHER job -- see
    # employees_with_live_offers() for why this matters.
    _employees_holding_offers = employees_with_live_offers(exclude_job=job_obj)

    for emp in candidates_qs:
        # Invariant: Technician who previously rejected or declined this job must NEVER receive it again
        is_declined = (
            emp.id in previous_offers
            or WorkforceJobOffer.objects.filter(
                job=job_obj,
                employee=emp,
                status__in=[WorkforceJobOffer.Status.REJECTED, WorkforceJobOffer.Status.DECLINED]
            ).exists()
            or WorkforceJobLifecycleEvent.objects.filter(
                job=job_obj,
                employee=emp,
                event_type="EMPLOYEE_JOB_DECLINED"
            ).exists()
        )
        if is_declined:
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=ALREADY_DECLINED")
            continue
        if emp.id in previous_offers:
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=ALREADY_OFFERED")
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

        # Check eligibility against service_category, then issue_title for offer reception
        is_eligible, reason, gate_results = check_candidate_eligibility(
            emp, job_obj.service_category, job=job_obj, purpose="offer_reception"
        )
        if not is_eligible and job_obj.issue_title:
            is_eligible, reason, gate_results = check_candidate_eligibility(
                emp, job_obj.issue_title, job=job_obj, purpose="offer_reception"
            )

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


def compute_dispatch_retry_delay(attempt_count: int) -> int:
    """
    Authoritative canonical dispatch retry backoff policy:
    Attempt 1  -> 10 seconds
    Attempt 2  -> 20 seconds
    Attempt 3  -> 30 seconds
    Attempt 4+ -> 60 seconds maximum
    """
    if attempt_count <= 1:
        return 10
    elif attempt_count == 2:
        return 20
    elif attempt_count == 3:
        return 30
    else:
        return 60


def get_or_create_dispatch_state(job_id: int) -> WorkforceDispatchState:
    """
    Race-safe retrieval or initialization of WorkforceDispatchState for a job.
    Uses database-level unique constraint to handle concurrent worker creations safely:
    1. Try to find existing record.
    2. If missing, attempt create within an atomic savepoint block.
    3. If IntegrityError (concurrent creator beat us), retrieve the now-existing record.
    """
    state = WorkforceDispatchState.objects.filter(job_id=job_id).first()
    if state:
        return state

    try:
        with transaction.atomic():
            state = WorkforceDispatchState.objects.create(
                job_id=job_id,
                dispatch_status=WorkforceDispatchState.DispatchStatus.NEVER_ATTEMPTED,
            )
            return state
    except IntegrityError:
        return WorkforceDispatchState.objects.get(job_id=job_id)


def dispatch_job(
    job_id_or_obj,
    max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS,
    exclude_employee_ids: Optional[List[int]] = None,
    force: bool = False,
) -> Tuple[bool, str]:
    """
    Executes automatic dispatch for a single ServiceRequest using 2-phase claim architecture:
    1. Atomically claims dispatch attempt under a short database transaction.
    2. Checks tenant, job state, date safety, active offers, and backoff retry_at (bypassed if force=True).
    3. Performs candidate evaluation outside database transaction to avoid long locks.
    4. Completes state transition atomically (schedules backoff if no candidates; creates offer if candidate found).
    """
    job_id = getattr(job_id_or_obj, "id", None) or getattr(job_id_or_obj, "pk", None) or job_id_or_obj

    try:
        return _dispatch_job_locked(job_id, max_gps_age_seconds, exclude_employee_ids, force=force)
    except DispatchRaceLost as race:
        return False, str(race)


def _dispatch_job_two_phase(job_id, max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS, exclude_employee_ids = None, force: bool = False):
    job_id = getattr(job_id, "id", None) or getattr(job_id, "pk", None) or job_id
    now = timezone.now()
    today = timezone.localdate()

    # ── Phase 1: Short Atomic Claim ──
    with transaction.atomic():
        job_obj = ServiceRequest.objects.select_for_update().filter(pk=job_id).first()
        if not job_obj:
            return False, "Job not found."

        if job_obj.status in ["completed", "cancelled"]:
            WorkforceDispatchState.objects.filter(job_id=job_id).update(
                dispatch_status=WorkforceDispatchState.DispatchStatus.CANCELLED if job_obj.status == "cancelled" else WorkforceDispatchState.DispatchStatus.COMPLETED,
                retry_at=None,
                locked_at=None,
            )
            return False, f"Job #{job_id} is {job_obj.status} and cannot be dispatched."

        if job_obj.status in ["accepted", "on_the_way", "arrived", "in_progress"] and job_obj.assigned_employee:
            WorkforceDispatchState.objects.filter(job_id=job_id).update(
                dispatch_status=WorkforceDispatchState.DispatchStatus.ASSIGNED,
                retry_at=None,
                locked_at=None,
            )
            return False, f"Job #{job_id} is already accepted and in progress with Employee #{job_obj.assigned_employee_id}."

        # Hard Safety Gate: Refuse past-dated bookings
        if job_obj.preferred_date and job_obj.preferred_date < today:
            logger.warning(
                f"[DISPATCH_SCHEDULE_EXPIRED] Job #{job_id} scheduled date {job_obj.preferred_date} is in the past. "
                f"Today is {today}. Refusing dispatch."
            )
            WorkforceDispatchState.objects.filter(job_id=job_id).update(
                dispatch_status=WorkforceDispatchState.DispatchStatus.EXPIRED,
                retry_at=None,
                locked_at=None,
            )
            return False, "SCHEDULE_DATE_EXPIRED"

        if not job_obj.preferred_date:
            created_dt = getattr(job_obj, "created_at", None)
            if created_dt:
                created_date = timezone.localtime(created_dt).date()
                if created_date < today:
                    logger.warning(
                        f"[DISPATCH_SCHEDULE_EXPIRED] Immediate Job #{job_id} created on {created_date} is stale. "
                        f"Today is {today}. Refusing dispatch."
                    )
                    WorkforceDispatchState.objects.filter(job_id=job_id).update(
                        dispatch_status=WorkforceDispatchState.DispatchStatus.EXPIRED,
                        retry_at=None,
                        locked_at=None,
                    )
                    return False, "SCHEDULE_DATE_EXPIRED"

        # Gate: Scheduled Job Hold / Closed Window Check
        win = get_scheduled_dispatch_window(job_obj, now=now)
        is_future, scheduled_dt, window_open = win
        if is_future:
            logger.info(
                f"[DISPATCH_SCHEDULED_HOLD] Job #{job_id} is scheduled for {scheduled_dt.isoformat()}. "
                f"Dispatch window opens at {window_open.isoformat()}. Holding job."
            )
            return True, f"Scheduled job held: service is at {scheduled_dt.strftime('%Y-%m-%d %H:%M')}; dispatch window opens at {window_open.strftime('%H:%M')}."

        if getattr(win, "is_closed", False):
            logger.info(
                f"[DISPATCH_SCHEDULE_WINDOW_CLOSED] Job #{job_id} scheduled offer window closed (service was at {scheduled_dt.isoformat() if scheduled_dt else 'past date'}). "
                f"Refusing new offer dispatch."
            )
            WorkforceDispatchState.objects.filter(job_id=job_id).update(
                dispatch_status=WorkforceDispatchState.DispatchStatus.EXPIRED,
                retry_at=None,
                locked_at=None,
                unassigned_reason_code="SCHEDULE_WINDOW_EXPIRED",
                unassigned_reason_message=f"Scheduled slot was {scheduled_dt.strftime('%Y-%m-%d %H:%M') if scheduled_dt else 'past date'}. Offer window closed.",
            )
            return False, f"Scheduled job offer window closed: service was at {scheduled_dt.strftime('%Y-%m-%d %H:%M') if scheduled_dt else 'past date'}."

        # Active unexpired offer check
        active_offer = WorkforceJobOffer.objects.select_for_update().filter(
            job_id=job_id,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        ).first()
        if active_offer:
            logger.info(f"[DISPATCH_OFFER_EXISTS] Job #{job_id} already has active offer #{active_offer.id} for Employee #{active_offer.employee_id}.")
            WorkforceDispatchState.objects.filter(job_id=job_id).update(
                dispatch_status=WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE,
                retry_at=None,
                locked_at=None,
            )
            return True, f"Active offer already pending for Employee #{active_offer.employee_id}."

        if job_obj.latitude is None or job_obj.longitude is None:
            if job_obj.status != "unassigned":
                apply_transition(job_obj, "unassigned")
            logger.warning(f"[DISPATCH_GPS_MISSING] Job #{job_id} is missing coordinates.")

        if not job_obj.company_id:
            job_obj.company_id = 1
            job_obj.save(update_fields=["company_id"])

        # Race-safe lock or create WorkforceDispatchState
        state = WorkforceDispatchState.objects.select_for_update().filter(job_id=job_id).first()
        if not state:
            try:
                with transaction.atomic():
                    state = WorkforceDispatchState.objects.create(
                        job_id=job_id,
                        dispatch_status=WorkforceDispatchState.DispatchStatus.NEVER_ATTEMPTED,
                    )
            except IntegrityError:
                state = WorkforceDispatchState.objects.select_for_update().get(job_id=job_id)

        # Concurrency check: another worker actively dispatching this job
        if state.dispatch_status == WorkforceDispatchState.DispatchStatus.DISPATCHING:
            if state.locked_at and (now - state.locked_at).total_seconds() < 120.0:
                logger.info(f"[DISPATCH_ALREADY_CLAIMED] Job #{job_id} is actively being dispatched by another worker.")
                return False, f"Job #{job_id} is currently being dispatched by another worker."
            logger.warning(f"[DISPATCH_CLAIM_RECOVERED] Recovered stale claim for Job #{job_id} (locked at {state.locked_at}).")

        if state.dispatch_status == WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE:
            if active_offer:
                return True, f"Active offer already pending for Job #{job_id}."

        if state.dispatch_status in [
            WorkforceDispatchState.DispatchStatus.ASSIGNED,
            WorkforceDispatchState.DispatchStatus.COMPLETED,
            WorkforceDispatchState.DispatchStatus.CANCELLED,
            WorkforceDispatchState.DispatchStatus.EXPIRED,
        ]:
            return False, f"Job #{job_id} dispatch state is {state.dispatch_status}; skipping dispatch."

        # Backoff check: if retry_at > now and not force, abort
        if not force and state.dispatch_status == WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED:
            if state.retry_at and state.retry_at > now:
                # Check if this job has a scheduled window that has just opened:
                # If window_open <= now, and state.last_attempt_at was BEFORE window_open
                # (meaning the retry state was created before the window opened),
                # allow this ONE first dispatch opportunity of the window.
                is_first_window_opportunity = (
                    window_open is not None
                    and window_open <= now
                    and (state.last_attempt_at is None or state.last_attempt_at < window_open)
                )
                if not is_first_window_opportunity:
                    remaining_s = round((state.retry_at - now).total_seconds(), 1)
                    logger.debug(f"[DISPATCH_RETRY_NOT_DUE] Job #{job_id} retry due in {remaining_s}s. Skipping.")
                    return False, f"Dispatch retry not due yet ({remaining_s}s remaining)."
                logger.info(f"[DISPATCH_WINDOW_FIRST_OPPORTUNITY] Job #{job_id} scheduled window opened at {window_open.isoformat()}. Permitting first window dispatch attempt.")

        # Claim the attempt atomically
        state.dispatch_status = WorkforceDispatchState.DispatchStatus.DISPATCHING
        state.attempt_count += 1
        state.last_attempt_at = now
        state.locked_at = now
        if force:
            state.retry_at = None
        state.save(update_fields=["dispatch_status", "attempt_count", "last_attempt_at", "locked_at", "retry_at", "updated_at"])
        attempt_num = state.attempt_count

    # ── Phase 2: Candidate Evaluation (Outside Database Transaction) ──
    try:
        WorkforceEventLog.objects.create(
            event_type="DISPATCH_STARTED",
            payload={"job_id": job_obj.id, "service": job_obj.service_category, "attempt": attempt_num}
        )

        failed_cycle_count = _count_failed_offer_cycles(job_obj)
        effective_radius_km = get_effective_radius_km(failed_cycle_count)

        # Explicitly aggregate all technicians who previously declined or rejected this job
        declined_emp_ids = set()
        try:
            declined_emp_ids.update(
                WorkforceJobOffer.objects.filter(
                    job_id=job_id,
                    status__in=[WorkforceJobOffer.Status.REJECTED, WorkforceJobOffer.Status.DECLINED],
                ).values_list("employee_id", flat=True)
            )
            declined_lifecycle_emp_ids = set(
                WorkforceJobLifecycleEvent.objects.filter(
                    job_id=job_id,
                    event_type="EMPLOYEE_JOB_DECLINED",
                    employee_id__isnull=False,
                ).values_list("employee_id", flat=True)
            )
            declined_emp_ids.update(declined_lifecycle_emp_ids)
        except Exception:
            pass
        if exclude_employee_ids:
            declined_emp_ids.update(exclude_employee_ids)

        candidates = get_eligible_candidates(
            job_obj,
            max_gps_age_seconds=max_gps_age_seconds,
            exclude_employee_ids=list(declined_emp_ids) if declined_emp_ids else None,
            radius_km=effective_radius_km,
        )

        eligible_candidates_snapshot = []
        for idx, c in enumerate(candidates):
            _emp_obj = c.get("employee")
            _emp_id = getattr(_emp_obj, "id", None)
            _emp_user = getattr(_emp_obj, "user", None)
            _emp_name = ""
            if _emp_user:
                _emp_name = _emp_user.get_full_name() or getattr(_emp_user, "username", "")
            if not _emp_name:
                _emp_name = f"Technician #{_emp_id}" if _emp_id else "Technician"

            eligible_candidates_snapshot.append({
                "employee_id": _emp_id,
                "employee_name": _emp_name,
                "distance_km": round(float(c["distance_km"]), 2) if c.get("distance_km") is not None else None,
                "score": round(float(c["score"]), 1) if c.get("score") is not None else None,
                "rank": idx + 1,
            })

        WorkforceEventLog.objects.create(
            event_type="CANDIDATES_EVALUATED",
            payload={
                "job_id": job_obj.id,
                "eligible_count": len(candidates),
                "attempt": attempt_num,
                "eligible_candidates_snapshot": eligible_candidates_snapshot,
            }
        )

        top_candidate = None
        top_emp = None
        top_dist_km = None
        top_score = None
        _skipped = []

        for _candidate in candidates:
            _emp = _candidate["employee"]
            top_candidate = _candidate
            top_emp = _emp
            top_dist_km = _candidate["distance_km"]
            top_score = _candidate["score"]
            break

    except Exception as eval_err:
        logger.exception(f"[DISPATCH_EVAL_ERROR] Error evaluating candidates for Job #{job_id}: {eval_err}")
        with transaction.atomic():
            s = WorkforceDispatchState.objects.select_for_update().filter(job_id=job_id).first()
            if s and s.dispatch_status == WorkforceDispatchState.DispatchStatus.DISPATCHING:
                delay = compute_dispatch_retry_delay(s.attempt_count)
                s.dispatch_status = WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED
                s.retry_at = timezone.now() + timedelta(seconds=delay)
                s.locked_at = None
                s.unassigned_reason_code = "DISPATCH_EVALUATION_ERROR"
                s.unassigned_reason_message = str(eval_err)[:255]
                s.save(update_fields=["dispatch_status", "retry_at", "locked_at", "unassigned_reason_code", "unassigned_reason_message", "updated_at"])
        raise

    # ── Phase 3: Short Atomic State Finalization ──
    with transaction.atomic():
        state = WorkforceDispatchState.objects.select_for_update().get(job_id=job_id)
        locked_job = ServiceRequest.objects.select_for_update().get(id=job_id)

        if locked_job.status in ["completed", "cancelled"]:
            state.dispatch_status = WorkforceDispatchState.DispatchStatus.CANCELLED if locked_job.status == "cancelled" else WorkforceDispatchState.DispatchStatus.COMPLETED
            state.retry_at = None
            state.locked_at = None
            state.save(update_fields=["dispatch_status", "retry_at", "locked_at", "updated_at"])
            return False, f"Job #{job_id} was {locked_job.status} during evaluation."

        if locked_job.assigned_employee:
            state.dispatch_status = WorkforceDispatchState.DispatchStatus.ASSIGNED
            state.retry_at = None
            state.locked_at = None
            state.save(update_fields=["dispatch_status", "retry_at", "locked_at", "updated_at"])
            return False, f"Job #{job_id} was assigned during evaluation."

        if not candidates or top_emp is None:
            if locked_job.status != "unassigned" or locked_job.assigned_employee is not None:
                locked_job.status = "unassigned"
                locked_job.assigned_employee = None
                locked_job.save(update_fields=["status", "assigned_employee"])

            delay_seconds = compute_dispatch_retry_delay(state.attempt_count)
            now_dt = timezone.now()
            retry_at = now_dt + timedelta(seconds=delay_seconds)
            reason_code, reason_message = describe_unassigned_reason(failed_cycle_count, effective_radius_km)

            state.dispatch_status = WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED
            state.retry_at = retry_at
            state.locked_at = None
            state.unassigned_reason_code = reason_code
            state.unassigned_reason_message = reason_message
            state.save(update_fields=["dispatch_status", "retry_at", "locked_at", "unassigned_reason_code", "unassigned_reason_message", "updated_at"])

            if state.attempt_count == 1:
                admin_user = None
                cid = getattr(locked_job, "company_id", None) or (locked_job.company.id if locked_job.company else None)
                if cid:
                    admin_user = get_user_model().objects.filter(
                        Q(role__in=["admin", "manager"]) | Q(is_staff=True),
                        company_id=cid,
                    ).first()
                if not admin_user:
                    admin_user = get_user_model().objects.filter(is_superuser=True).first()
                if admin_user:
                    service_name = locked_job.issue_title or locked_job.service_category or "Service"
                    WorkforceNotification.objects.create(
                        recipient=admin_user,
                        title="Automatic Dispatch: Awaiting Technician",
                        message=f"Job #{locked_job.id} ({service_name}) remains unassigned. {reason_message}",
                        notification_type="DISPATCH_UNASSIGNED",
                        company=locked_job.company,
                        related_object_id=str(locked_job.id),
                    )

            WorkforceEventLog.objects.create(
                event_type="DISPATCH_UNASSIGNED_REASON",
                payload={
                    "job_id": locked_job.id,
                    "reason_code": reason_code,
                    "reason_message": reason_message,
                    "failed_cycle_count": failed_cycle_count,
                    "effective_radius_km": effective_radius_km,
                    "attempt_count": state.attempt_count,
                    "retry_at": retry_at.isoformat(),
                },
            )
            _maybe_signal_customer_delay(locked_job, failed_cycle_count)
            return False, f"No eligible technicians available for automatic dispatch. Scheduled retry in {delay_seconds}s (attempt {state.attempt_count}). {reason_message}"

        # Candidate employee row lock
        locked_emp = Employee.objects.select_for_update().filter(pk=top_emp.pk).first()
        if not locked_emp:
            delay_seconds = compute_dispatch_retry_delay(state.attempt_count)
            state.dispatch_status = WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED
            state.retry_at = timezone.now() + timedelta(seconds=delay_seconds)
            state.locked_at = None
        # Ensure candidate does not already have an active offer for THIS same job
        existing_offer_this_job = WorkforceJobOffer.objects.filter(
            employee_id=getattr(locked_emp, "id", None),
            job_id=getattr(locked_job, "id", None),
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=timezone.now(),
        ).first()
        if existing_offer_this_job:
            state.dispatch_status = WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE
            state.retry_at = None
            state.locked_at = None
            state.save(update_fields=["dispatch_status", "retry_at", "locked_at", "updated_at"])
            return True, f"Active offer already pending for Job #{job_id} on Employee #{locked_emp.id}."

        WorkforceJobOffer.objects.filter(job_id=getattr(locked_job, "id", None), status=WorkforceJobOffer.Status.OFFERED).update(status=WorkforceJobOffer.Status.EXPIRED)

        offer_window_seconds = compute_offer_window_seconds(
            locked_job, len(candidates), failed_cycles=failed_cycle_count
        )
        expires_at = timezone.now() + timedelta(seconds=offer_window_seconds)

        try:
            offer = WorkforceJobOffer.objects.create(
                job=locked_job,
                employee=locked_emp,
                status=WorkforceJobOffer.Status.OFFERED,
                rank_score=top_score,
                expires_at=expires_at,
            )
        except IntegrityError:
            state.dispatch_status = WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED
            state.retry_at = timezone.now() + timedelta(seconds=5)
            state.locked_at = None
            state.save(update_fields=["dispatch_status", "retry_at", "locked_at", "updated_at"])
            raise DispatchRaceLost(
                f"Technician #{locked_emp.id} was offered another job concurrently."
            )

        state.dispatch_status = WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE
        state.retry_at = None
        state.locked_at = None
        state.save(update_fields=["dispatch_status", "retry_at", "locked_at", "updated_at"])

        if locked_job.status in ["draft", "new_request", "confirmed"]:
            apply_transition(locked_job, "unassigned")

    # Outside transaction: webhooks and notifications
    try:
        from workforce_api.services.customer_webhook import notify_customer_app
        notify_customer_app(
            "technician.assigned",
            locked_job,
            technician_id=str(locked_emp.id),
            vendor_name=getattr(locked_job.company, "company_name", "") if getattr(locked_job, "company", None) else "",
        )
    except Exception as webhook_err:
        logger.info(f"Could not notify Customer app of offer for Job #{locked_job.id}: {webhook_err}")

    WorkforceEventLog.objects.create(
        user=locked_emp.user,
        event_type="OFFER_CREATED",
        payload={
            "id": locked_job.id,
            "job_id": locked_job.id,
            "request_id": locked_job.request_id or f"#{locked_job.id}",
            "offer_id": offer.id,
            "employee_id": locked_emp.id,
            "service_title": locked_job.issue_title or locked_job.service_category or "Service Request",
            "service_category": locked_job.service_category or "",
            "distance_km": round(top_dist_km, 2),
            "address": locked_job.address or "",
            "expires_at": expires_at.isoformat(),
        }
    )

    loc_str = f" at {locked_job.address}" if locked_job.address else ""
    req_id_str = f" ({locked_job.request_id})" if locked_job.request_id else f" #{locked_job.id}"
    service_label = locked_job.issue_title or locked_job.service_category or "Service Request"
    expiry_str = expires_at.strftime("%H:%M:%S UTC")

    WorkforceNotification.objects.create(
        recipient=locked_emp.user,
        title="New Job Offer Available!",
        message=f"You have a new exclusive job offer for '{service_label}'{req_id_str}{loc_str} ({top_dist_km:.1f} km away). Expiry: {expiry_str}. Open your dashboard to Accept or Decline.",
        notification_type="JOB_OFFER",
        company=locked_job.company,
        related_object_id=str(locked_job.id),
    )

    logger.info(
        f"[DISPATCH_DECISION] job={locked_job.id} employee={locked_emp.id} "
        f"distance_km={top_dist_km:.2f} score={top_score:.1f} status=OFFER_CREATED"
    )
    return True, f"Job #{locked_job.id} offered to {locked_emp.user.get_full_name() or locked_emp.user.username} ({top_dist_km:.1f}km away, Score: {top_score:.1f})."


_dispatch_job_locked = _dispatch_job_two_phase


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
    today = timezone.localdate()
    expired_offers = list(
        WorkforceJobOffer.objects.filter(
            status=WorkforceJobOffer.Status.OFFERED,
        ).filter(
            Q(expires_at__lte=now) |
            Q(job__preferred_date__lt=today) |
            Q(job__preferred_date__isnull=True, job__created_at__date__lt=today)
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
            logger.info(f"[DISPATCH_OFFER_EXPIRED] Offer #{offer.id} for Job #{offer.job_id} marked EXPIRED.")

        # Check if job is past-dated
        job = offer.job
        is_past_dated = False
        if job:
            if job.preferred_date and job.preferred_date < today:
                is_past_dated = True
            elif not job.preferred_date and getattr(job, "created_at", None):
                if timezone.localtime(job.created_at).date() < today:
                    is_past_dated = True

        # Re-dispatch current-day jobs ONLY; NEVER re-dispatch past-dated jobs
        if not is_past_dated:
            logger.info(f"[DISPATCH_REDISPATCH] Triggering fallback dispatch for current-day Job #{offer.job_id}.")
            dispatch_next_candidate(offer.job_id)
        else:
            logger.info(f"[DISPATCH_EXPIRED_NO_REDISPATCH] Job #{offer.job_id} scheduled date is in the past; skipping fallback dispatch.")

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
    today = timezone.localdate()
    qs = ServiceRequest.objects.filter(
        status__in=DISPATCHABLE_STATUSES,
        assigned_employee__isnull=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).filter(
        Q(preferred_date__gte=today) |
        Q(preferred_date__isnull=True, created_at__date=today)
    )
    if company_id:
        qs = qs.filter(company_id=company_id)

    crashed_cutoff = now - timedelta(seconds=120)

    # Exclude jobs that are not dispatchable NOW based on WorkforceDispatchState
    qs = qs.exclude(
        # Active dispatch claim by a living worker:
        Q(dispatch_state__dispatch_status=WorkforceDispatchState.DispatchStatus.DISPATCHING, dispatch_state__locked_at__gt=crashed_cutoff) |
        # Inactive or completed/assigned/active-offer/expired states:
        Q(dispatch_state__dispatch_status__in=[
            WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE,
            WorkforceDispatchState.DispatchStatus.ASSIGNED,
            WorkforceDispatchState.DispatchStatus.CANCELLED,
            WorkforceDispatchState.DispatchStatus.COMPLETED,
            WorkforceDispatchState.DispatchStatus.EXPIRED,
        ])
    )

    # Find all jobs in dispatchable states
    pending_jobs = list(
        qs.exclude(
            # Exclude jobs that already have an active exclusive offer
            job_offers__status=WorkforceJobOffer.Status.OFFERED,
            job_offers__expires_at__gt=now,
        ).select_related("dispatch_state").order_by("preferred_date", "preferred_time", "-created_at").distinct()[:limit]
    )

    results = {
        "expired_offers_swept": expired_count,
        "pending_jobs_found": len(pending_jobs),
        "dispatched_count": 0,
        "unassigned_count": 0,
        "details": [],
    }

    for job in pending_jobs:
        win = get_scheduled_dispatch_window(job, now=now)
        if win.is_future:
            # Job is outside its scheduled window; do not dispatch, do not touch state
            logger.debug(f"[DISPATCH_PENDING_SCHEDULED_HELD] Job #{job.id} held outside scheduled dispatch window.")
            continue

        if getattr(win, "is_closed", False):
            # Window has closed; mark expired once so it's not repeatedly queried
            logger.info(f"[DISPATCH_PENDING_WINDOW_CLOSED] Job #{job.id} scheduled window closed. Marking expired.")
            WorkforceDispatchState.objects.filter(job_id=job.id).update(
                dispatch_status=WorkforceDispatchState.DispatchStatus.EXPIRED,
                retry_at=None,
                locked_at=None,
            )
            continue

        # Check retry backoff if in RETRY_SCHEDULED
        state = getattr(job, "dispatch_state", None)
        if state and state.dispatch_status == WorkforceDispatchState.DispatchStatus.RETRY_SCHEDULED:
            if state.retry_at and state.retry_at > now:
                # Check if this is the first window opportunity
                is_first_window_opportunity = (
                    win.window_open is not None
                    and win.window_open <= now
                    and (state.last_attempt_at is None or state.last_attempt_at < win.window_open)
                )
                if not is_first_window_opportunity:
                    # Normal retry backoff is still running; skip this job until retry_at
                    logger.debug(f"[DISPATCH_PENDING_RETRY_SKIPPED] Job #{job.id} retry due at {state.retry_at.isoformat()}. Skipping.")
                    continue

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
    Triggered when an employee becomes available/eligible:
    Finds pending unassigned/dispatchable jobs within the employee's company
    and evaluates dispatch immediately. Respects retry_at and active state.
    """
    emp_id = employee_or_id.pk if hasattr(employee_or_id, "pk") else employee_or_id
    emp = Employee.objects.filter(pk=emp_id).first()
    if not emp or not emp.is_active or not emp.is_online:
        return 0

    now = timezone.now()
    today = timezone.localdate()
    crashed_cutoff = now - timedelta(seconds=120)

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
    ).filter(
        Q(preferred_date__gte=today) |
        Q(preferred_date__isnull=True, created_at__date=today)
    ).exclude(
        job_offers__status=WorkforceJobOffer.Status.OFFERED,
        job_offers__expires_at__gt=now,
    ).exclude(
        # Exclude jobs where this employee currently holds an active offer or explicitly declined
        Q(job_offers__employee_id=emp.id, job_offers__status=WorkforceJobOffer.Status.OFFERED, job_offers__expires_at__gt=now) |
        Q(job_offers__employee_id=emp.id, job_offers__status__in=[WorkforceJobOffer.Status.REJECTED, WorkforceJobOffer.Status.DECLINED]) |
        Q(lifecycle_events__employee_id=emp.id, lifecycle_events__event_type="EMPLOYEE_JOB_DECLINED")
    ).exclude(
        Q(dispatch_state__retry_at__gt=now) |
        Q(dispatch_state__dispatch_status=WorkforceDispatchState.DispatchStatus.DISPATCHING, dispatch_state__locked_at__gt=crashed_cutoff) |
        Q(dispatch_state__dispatch_status__in=[
            WorkforceDispatchState.DispatchStatus.OFFER_ACTIVE,
            WorkforceDispatchState.DispatchStatus.ASSIGNED,
            WorkforceDispatchState.DispatchStatus.CANCELLED,
            WorkforceDispatchState.DispatchStatus.COMPLETED,
            WorkforceDispatchState.DispatchStatus.EXPIRED,
        ])
    ).distinct()

    dispatched_count = 0
    for job in pending_jobs:
        win = get_scheduled_dispatch_window(job, now=now)
        if win.is_future or getattr(win, "is_closed", False):
            continue
        logger.info(f"[DISPATCH_RECONSIDER_TRIGGER] Evaluating Job #{job.id} for Employee #{emp.id}.")
        success, msg = dispatch_job(job)
        if success:
            dispatched_count += 1

    return dispatched_count


def reconcile_booking_for_dispatch(job_id_or_obj, use_redis_geo=False):
    """Fallback entry point for post-commit dispatch triggers."""
    return dispatch_job(job_id_or_obj)
