"""
Django Management Command: update_social_security_eligibility

SEVO business plan Section 8 (Labour classification, Code on Social
Security 2020): individual workers become eligible for benefits once
they cross 90 days worked with SEVO in a financial year. This command is
the daily sweep that recounts each individual worker's days-worked and
flags anyone who has newly crossed the threshold as
ELIGIBLE_PENDING_REGISTRATION, ready for an admin to actually complete
the Shram Suvidha portal submission (see
WorkforceAdminSocialSecurityMarkRegisteredView) -- run it on a schedule
(cron/systemd timer), same deployment pattern as release_wallet_holds.

Usage:
  python manage.py update_social_security_eligibility
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Recomputes days-worked and Social Security Code eligibility status for every individual worker."

    def handle(self, *args, **options):
        from workforce_api.services import recompute_all_social_security

        try:
            count = recompute_all_social_security()
            self.stdout.write(self.style.SUCCESS(
                f"update_social_security_eligibility: recomputed {count} individual worker(s)."
            ))
        except Exception:
            logger.exception("update_social_security_eligibility: run failed")
            self.stdout.write(self.style.ERROR("update_social_security_eligibility: run failed -- see logs."))
