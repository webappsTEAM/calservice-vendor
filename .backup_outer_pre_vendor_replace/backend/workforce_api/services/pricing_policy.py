"""
Commercial policy resolution.

Everything here answers a question that used to be answered by a literal in the
code: what does the consultation cost, does this quote need admin eyes before
the customer sees it, how much is payable up front. The answers now come from
WorkforceServicePricingPolicy, which a SEVO admin edits in the app.

Categories are matched case-insensitively, and an unknown category falls back
to a permissive default rather than raising -- a service nobody has configured
yet must still be bookable.
"""
import logging
from decimal import Decimal

from workforce_api.models import WorkforceServicePricingPolicy

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")

# Used when no policy row exists for a category. Deliberately matches the
# behaviour of the code before policies existed: no consultation fee, no
# pre-send threshold, full payment up front, admin approval on.
DEFAULT_POLICY = {
    "consultation_fee_mode": WorkforceServicePricingPolicy.ConsultationFeeMode.FREE,
    "consultation_fee_amount": ZERO,
    "high_value_review_threshold": None,
    "requires_admin_approval": True,
    "advance_percent": Decimal("100.00"),
    "allow_customer_supplied_materials": False,
}


def _normalise(category):
    return str(category or "").strip().lower()


def policy_for(category):
    """The policy row for a service category, or None."""
    key = _normalise(category)
    if not key:
        return None
    return (
        WorkforceServicePricingPolicy.objects
        .filter(service_category__iexact=key, is_active=True)
        .first()
    )


def policy_value(category, field):
    policy = policy_for(category)
    if policy is None:
        return DEFAULT_POLICY[field]
    return getattr(policy, field)


# --------------------------------------------------------------------------- #
# consultation fee
# --------------------------------------------------------------------------- #
def consultation_fee_for(category, latitude=None, longitude=None):
    """
    What the customer pays for the site visit.

    Returns (amount, explanation) -- the explanation is stored on the fee record
    so a customer questioning the charge can be given a straight answer months
    later, rather than someone re-deriving it from the code.
    """
    policy = policy_for(category)
    if policy is None:
        return ZERO, "No pricing policy configured for this category; consultation free."

    mode = policy.consultation_fee_mode
    Mode = WorkforceServicePricingPolicy.ConsultationFeeMode

    if mode == Mode.FREE:
        return ZERO, "Consultation is free for this category."

    if mode == Mode.FLAT:
        return Decimal(policy.consultation_fee_amount).quantize(CENT), (
            f"Flat consultation fee for {policy.service_category}."
        )

    # DISTANCE_BAND
    if latitude is None or longitude is None:
        # No coordinates is not a licence to charge: default to the free side,
        # and say so, rather than silently billing the customer for a distance
        # nobody measured.
        return ZERO, "Site coordinates unavailable; distance-based fee waived."

    distance_km = _haversine_km(
        policy.hub_latitude, policy.hub_longitude, float(latitude), float(longitude)
    )
    if distance_km <= float(policy.free_radius_km):
        return ZERO, (
            f"Site is {distance_km:.1f} km from the hub, within the "
            f"{policy.free_radius_km} km free radius."
        )
    return Decimal(policy.beyond_radius_amount).quantize(CENT), (
        f"Site is {distance_km:.1f} km from the hub, beyond the "
        f"{policy.free_radius_km} km free radius."
    )


def _haversine_km(lat1, lon1, lat2, lon2):
    from math import asin, cos, radians, sin, sqrt

    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * r * asin(sqrt(a))


# --------------------------------------------------------------------------- #
# gates and schedule
# --------------------------------------------------------------------------- #
def needs_pre_send_review(category, amount):
    """Whether a quote of this size must be seen by an admin before it is sent."""
    threshold = policy_value(category, "high_value_review_threshold")
    if threshold is None:
        return False, None
    return Decimal(str(amount or 0)) > Decimal(threshold), Decimal(threshold)


def requires_admin_approval(category):
    return bool(policy_value(category, "requires_admin_approval"))


def advance_percent(category):
    return Decimal(str(policy_value(category, "advance_percent")))


def allows_customer_supplied_materials(category):
    return bool(policy_value(category, "allow_customer_supplied_materials"))


def split_advance_and_balance(total, category, percent=None):
    """(advance, balance) for a total. `percent` overrides the category default."""
    total = Decimal(str(total or 0)).quantize(CENT)
    pct = Decimal(str(percent)) if percent is not None else advance_percent(category)
    if pct >= Decimal("100"):
        return total, ZERO
    advance = (total * pct / Decimal("100")).quantize(CENT)
    return advance, (total - advance).quantize(CENT)
