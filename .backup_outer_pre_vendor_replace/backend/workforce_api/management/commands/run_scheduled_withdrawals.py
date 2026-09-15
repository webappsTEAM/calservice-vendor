"""
Django Management Command: run_scheduled_withdrawals

SEVO business plan Section 1 (head-wallet specific features): "Scheduled
withdrawals: providers can set a standing daily/weekly auto-payout to
their bank account timed to their own wage-payment day." This command is
the daily sweep that fires those standing rules -- see
services/withdrawals.py:run_scheduled_withdrawals for the actual logic.
Run it once a day (cron/systemd timer), same deployment pattern as
release_wallet_holds.

Usage:
  python manage.py run_scheduled_withdrawals
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fires every wallet's standing auto-withdrawal rule that is due today."

    def handle(self, *args, **options):
        from workforce_api.services import run_scheduled_withdrawals

        try:
            count = run_scheduled_withdrawals()
            self.stdout.write(self.style.SUCCESS(
                f"run_scheduled_withdrawals: created {count} scheduled withdrawal request(s)."
            ))
        except Exception:
            logger.exception("run_scheduled_withdrawals: run failed")
            self.stdout.write(self.style.ERROR("run_scheduled_withdrawals: run failed -- see logs."))
