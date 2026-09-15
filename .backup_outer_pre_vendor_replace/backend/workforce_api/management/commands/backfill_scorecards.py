"""
Django Management Command: backfill_scorecards

SEVO business plan Section 4 (rating + SLA scorecards): WorkforceScorecard
rows are normally kept in sync incrementally, recalculated after each new
WorkforceJobFeedback submission (see
workforce_api/views.py:WorkforceJobFeedbackSubmitView). This command is a
one-off backfill for existing feedback rows predating this feature (so
historical ratings aren't silently excluded from day one), and can also be
re-run at any time to correct drift.

Usage:
  python manage.py backfill_scorecards
  python manage.py backfill_scorecards --company-id 3
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recomputes WorkforceScorecard rows for all employees (or one company) from WorkforceJobFeedback history."

    def add_arguments(self, parser):
        parser.add_argument("--company-id", type=int, default=None, help="Limit the backfill to one Company's employees.")

    def handle(self, *args, **options):
        from companies.models import Company
        from workforce_api.services import recalculate_all_scorecards

        company = None
        company_id = options.get("company_id")
        if company_id:
            company = Company.objects.filter(pk=company_id).first()
            if not company:
                self.stdout.write(self.style.ERROR(f"backfill_scorecards: no Company with id={company_id}"))
                return

        try:
            count = recalculate_all_scorecards(company=company)
            self.stdout.write(self.style.SUCCESS(f"backfill_scorecards: recalculated {count} scorecard(s)."))
        except Exception:
            logger.exception("backfill_scorecards: run failed")
            self.stdout.write(self.style.ERROR("backfill_scorecards: run failed -- see logs."))
