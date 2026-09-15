"""
Django Management Command: release_wallet_holds

SEVO business plan Section 4 (dispute hold-and-clawback): a completed
job's JOB_CREDIT ledger entry is created HELD (see
services/commission.py:settle_completed_job) and only becomes
withdrawable once its dispute window (SEVO_DISPUTE_HOLD_HOURS, default
48h) has passed with no clawback. This command is the periodic sweep
that matures those entries -- run it on a schedule (cron/systemd timer),
same deployment pattern as dispatch_pending_workforce_jobs.

Usage:
  Single pass:
    python manage.py release_wallet_holds --once

  Continuous loop (default: every 15 minutes):
    python manage.py release_wallet_holds --loop --interval 900
"""
import time
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Releases wallet ledger entries whose dispute-hold window has passed."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run a single pass and exit.")
        parser.add_argument("--loop", action="store_true", help="Run continuously.")
        parser.add_argument("--interval", type=int, default=900, help="Seconds between passes when looping (default 900 = 15 min).")

    def handle(self, *args, **options):
        from workforce_api.services import release_due_holds

        if options.get("loop"):
            interval = options["interval"]
            self.stdout.write(self.style.SUCCESS(f"release_wallet_holds: looping every {interval}s"))
            while True:
                self._run_once()
                time.sleep(interval)
        else:
            self._run_once()

    def _run_once(self):
        from workforce_api.services import release_due_holds

        try:
            count = release_due_holds()
            self.stdout.write(self.style.SUCCESS(f"release_wallet_holds: released {count} ledger entr{'y' if count == 1 else 'ies'}."))
        except Exception:
            logger.exception("release_wallet_holds: pass failed")
            self.stdout.write(self.style.ERROR("release_wallet_holds: pass failed -- see logs."))
