"""
Django Management Command: run_daily_reconciliation

SEVO business plan Section 5 (Reconciliation cadence): "A daily automated
reconciliation job -- extending the payment-reconciliation audit tooling
already built into the platform -- checks gross bookings against
recognised commission, net payouts, and the actual escrow-bank balance,
flagging same-day if anything drifts." See services/reconciliation.py for
the check logic and its honest scoping note on the escrow-bank-balance
figure (informational, not an automated bank-statement comparison, since
no live bank feed exists in this codebase).

Usage:
  python manage.py run_daily_reconciliation
  python manage.py run_daily_reconciliation --date 2026-08-30
  python manage.py run_daily_reconciliation --json
"""
import json
import logging
from datetime import datetime

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


def _decimal_default(obj):
    return str(obj)


class Command(BaseCommand):
    help = "Runs the daily wallet-ledger reconciliation across all companies and reports any drift."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=str, default=None, help="Date to reconcile, YYYY-MM-DD (default: yesterday).")
        parser.add_argument("--json", action="store_true", help="Print machine-readable JSON instead of a summary.")

    def handle(self, *args, **options):
        from workforce_api.services import run_daily_reconciliation_all_companies

        target_date = None
        if options.get("date"):
            try:
                target_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError:
                self.stdout.write(self.style.ERROR(f"run_daily_reconciliation: invalid --date {options['date']!r}, expected YYYY-MM-DD"))
                return

        try:
            result = run_daily_reconciliation_all_companies(target_date=target_date)
        except Exception:
            logger.exception("run_daily_reconciliation: run failed")
            self.stdout.write(self.style.ERROR("run_daily_reconciliation: run failed -- see logs."))
            return

        if options.get("json"):
            self.stdout.write(json.dumps(result, default=_decimal_default, indent=2))
            return

        platform = result["platform"]
        total_findings = len(platform["findings"]) + sum(len(c["findings"]) for c in result["companies"])
        if total_findings == 0:
            self.stdout.write(self.style.SUCCESS(
                f"run_daily_reconciliation: {platform['date']} clean across platform and "
                f"{len(result['companies'])} companies. Expected escrow balance: "
                f"{platform['expected_escrow_balance']}"
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"run_daily_reconciliation: {platform['date']} -- {total_findings} finding(s) across "
                f"platform + {len(result['companies'])} companies. Run with --json for detail."
            ))
