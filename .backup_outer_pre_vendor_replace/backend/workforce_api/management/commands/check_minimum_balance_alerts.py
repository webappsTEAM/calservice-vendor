"""
Django Management Command: check_minimum_balance_alerts

SEVO business plan Section 1 (head-wallet specific features): "Minimum
balance alerts: providers can set a floor (e.g. 'alert me if my
withdrawable balance drops below Rs 5,000') so they never get caught
short on a payday." This command is the daily sweep that fires those
alerts -- see services/withdrawals.py:check_minimum_balance_alerts for
the actual logic and its 24-hour re-alert cooldown. Run it once a day
(cron/systemd timer), same deployment pattern as release_wallet_holds.

Usage:
  python manage.py check_minimum_balance_alerts
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Sends a low-balance notification for every wallet under its own alert threshold."

    def handle(self, *args, **options):
        from workforce_api.services import check_minimum_balance_alerts

        try:
            count = check_minimum_balance_alerts()
            self.stdout.write(self.style.SUCCESS(
                f"check_minimum_balance_alerts: sent {count} alert(s)."
            ))
        except Exception:
            logger.exception("check_minimum_balance_alerts: run failed")
            self.stdout.write(self.style.ERROR("check_minimum_balance_alerts: run failed -- see logs."))
