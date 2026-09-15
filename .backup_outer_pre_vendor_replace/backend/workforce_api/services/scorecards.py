"""
Worker/provider rating + SLA scorecards -- SEVO business plan Section 4:
"A missed SLA triggers ... a scorecard mark against the provider/worker --
visible in their own dashboard, not just used silently against them", and
the Days 31-60 roadmap item "Rating and SLA scorecards go live and start
feeding the dispatch-ranking algorithm."

WorkforceJobFeedback (one row per customer-rated job) is the raw signal.
This module rolls it up into a single persisted WorkforceScorecard row per
employee so:
  - the admin dashboard can list/sort every worker's standing in one query
    (see views.WorkforceAdminScorecardsListView)
  - automatic_dispatch.py can bulk-fetch scorecards for every dispatch
    candidate without an aggregate query per candidate

Recalculation is triggered after every WorkforceJobFeedback submission
(see views.WorkforceJobFeedbackSubmitView) -- always wrapped in
try/except by the caller, same non-fatal-to-the-request pattern as
provision_individual_wallet in wallet_onboarding.py.
"""
import logging

from django.db import transaction
from django.db.models import Avg, Count, Q
from django.utils import timezone

logger = logging.getLogger(__name__)


def _tier_for(average_rating, sla_score, rating_count):
    from workforce_api.models import WorkforceScorecard

    # Require a minimum sample so a single job's rating can't swing a
    # worker to Gold or Bronze off one data point.
    if rating_count < 3:
        return WorkforceScorecard.Tier.UNRATED
    if average_rating >= 4.5 and sla_score >= 90:
        return WorkforceScorecard.Tier.GOLD
    if average_rating >= 3.5 and sla_score >= 70:
        return WorkforceScorecard.Tier.SILVER
    return WorkforceScorecard.Tier.BRONZE


@transaction.atomic
def recalculate_employee_scorecard(employee):
    """
    Idempotent full recompute of one employee's scorecard from
    WorkforceJobFeedback. Cheap enough to call synchronously after every
    feedback submission -- there's no periodic-recompute requirement, but
    recalculate_all_scorecards() below exists for backfill/drift-correction.
    """
    from workforce_api.models import WorkforceJobFeedback, WorkforceScorecard

    agg = WorkforceJobFeedback.objects.filter(employee=employee).aggregate(
        rating_count=Count("id"),
        average_rating=Avg("rating"),
        csat_avg=Avg("csat_score"),
        sla_met=Count("id", filter=Q(resolution_ontime=True)),
        sla_breach=Count("id", filter=Q(resolution_ontime=False)),
    )

    rating_count = agg["rating_count"] or 0
    average_rating = round(float(agg["average_rating"] or 0), 2)
    csat_average = round(float(agg["csat_avg"] or 0), 2)
    sla_met = agg["sla_met"] or 0
    sla_breach = agg["sla_breach"] or 0
    sla_score = round((sla_met / rating_count) * 100, 2) if rating_count else 0.0

    tier = _tier_for(average_rating, sla_score, rating_count)

    scorecard, _created = WorkforceScorecard.objects.update_or_create(
        employee=employee,
        defaults={
            "rating_count": rating_count,
            "average_rating": average_rating,
            "csat_average": csat_average,
            "sla_met_count": sla_met,
            "sla_breach_count": sla_breach,
            "sla_score": sla_score,
            "tier": tier,
            "last_recalculated_at": timezone.now(),
        },
    )
    return scorecard


def recalculate_all_scorecards(company=None):
    """
    Bulk recompute across every employee (optionally scoped to one
    Company) -- used by the backfill_scorecards management command so
    historical feedback predating this feature isn't silently ignored,
    and safe to re-run periodically to correct any drift.
    """
    from employees.models import Employee

    qs = Employee.objects.all()
    if company is not None:
        qs = qs.filter(company=company)

    count = 0
    for employee in qs.iterator():
        try:
            recalculate_employee_scorecard(employee)
            count += 1
        except Exception:
            logger.exception("recalculate_all_scorecards: failed for employee #%s", employee.id)
    return count
