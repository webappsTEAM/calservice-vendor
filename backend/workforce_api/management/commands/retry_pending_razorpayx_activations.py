"""
Django Management Command: retry_pending_razorpayx_activations

SEVO business plan Section 1: every withdrawal made before RazorpayX
credentials existed on an environment queues as
WithdrawalRequest.Status.AWAITING_RAZORPAYX_ACTIVATION instead of failing
(see services/payouts.py -- is_configured() / execute_withdrawal()). This
command is the sweep that retries those once real credentials are added
-- run it once after activating RazorpayX on an environment, and
optionally on a schedule afterwards as a safety net for anything that
slips through (e.g. a brief RazorpayX outage during ensure_fund_account).

Usage:
  python manage.py retry_pending_razorpayx_activations
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Retries every withdrawal stuck in AWAITING_RAZORPAYX_ACTIVATION now that RazorpayX credentials exist."

    def handle(self, *args, **options):
        from workforce_api.services import retry_pending_activations, razorpayx_is_configured

        if not razorpayx_is_configured():
            self.stdout.write(self.style.WARNING(
                "retry_pending_razorpayx_activations: RazorpayX still isn't configured on this "
                "environment (RAZORPAYX_KEY_ID / RAZORPAYX_KEY_SECRET / RAZORPAYX_ACCOUNT_NUMBER) -- nothing to do."
            ))
            return

        try:
            count = retry_pending_activations()
            self.stdout.write(self.style.SUCCESS(
                f"retry_pending_razorpayx_activations: retried {count} withdrawal(s)."
            ))
        except Exception:
            logger.exception("retry_pending_razorpayx_activations: run failed")
            self.stdout.write(self.style.ERROR("retry_pending_razorpayx_activations: run failed -- see logs."))
