"""
Diagnoses and repairs a ServiceRequest that reached COMPLETED status but
whose wallet settlement never happened -- i.e. no JOB_CREDIT WalletLedgerEntry
exists for it, so the technician/provider's wallet was never credited even
though the job shows as done.

Root cause this addresses: service_requests/state_machine.py's
apply_transition() calls workforce_api/services/commission.py's
settle_completed_job() the instant a job's status flips to "completed", but
that call is wrapped in a broad try/except -- if settlement raises for any
reason (no resolvable payee wallet, no JobPayment record, a transient DB
error, etc.), the exception was only logged. The job stays COMPLETED, but
the wallet is never touched and there was previously no way to tell short of
reading the server logs.

This command is safe to run repeatedly and safe to run broadly:
settle_completed_job() is itself idempotent (it first checks for an existing
JOB_CREDIT entry for the job and does nothing if one is already there), so
running this against jobs that already settled correctly is a no-op.

Usage:
  python manage.py retry_failed_settlements --job AC4964 --dry-run   # diagnose one job
  python manage.py retry_failed_settlements --job AC4964             # settle that one job
  python manage.py retry_failed_settlements --dry-run                # see every unsettled completed job company-wide
  python manage.py retry_failed_settlements                          # settle every completed job that's still missing its credit
"""
from django.core.management.base import BaseCommand

from service_requests.models import ServiceRequest
from workforce_api.models import WalletLedgerEntry
from workforce_api.services.commission import settle_completed_job


class Command(BaseCommand):
    help = "Diagnoses and settles COMPLETED jobs that are missing their JOB_CREDIT wallet ledger entry."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Only report which completed jobs are missing settlement -- makes no changes.",
        )
        parser.add_argument(
            "--job", type=str, default=None,
            help="Only check this one job, by its request_id (e.g. AC4964).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        only_job = options["job"]

        settled_job_ids = set(
            WalletLedgerEntry.objects.filter(
                entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT,
            ).values_list("job_id", flat=True)
        )

        qs = ServiceRequest.objects.filter(status="completed").exclude(id__in=settled_job_ids)
        if only_job:
            qs = qs.filter(request_id=only_job)

        if not qs.exists():
            self.stdout.write(self.style.WARNING(
                f"No unsettled completed job found matching request_id={only_job!r}."
                if only_job else
                "No completed jobs are currently missing their wallet settlement."
            ))
            return

        settled, still_failing = 0, 0
        for job in qs:
            self.stdout.write(f"  UNSETTLED  {job.request_id} (assigned_employee={job.assigned_employee_id})")

            if dry_run:
                continue

            try:
                entry = settle_completed_job(job)
                if entry:
                    settled += 1
                    self.stdout.write(self.style.SUCCESS(
                        f"    -> SETTLED {job.request_id} -- net {entry.signed_amount} credited to wallet #{entry.wallet_id} (HELD until {entry.hold_release_at})."
                    ))
                else:
                    still_failing += 1
                    self.stdout.write(self.style.ERROR(
                        f"    -> still could not settle {job.request_id} -- see server logs for [SETTLEMENT_NO_WALLET] / [SETTLEMENT_NO_PAYMENT] / [SETTLEMENT_ZERO_AMOUNT]."
                    ))
            except Exception as e:
                still_failing += 1
                self.stdout.write(self.style.ERROR(f"    -> exception settling {job.request_id}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Done. settled={settled} still_failing={still_failing} dry_run={dry_run}")
        )
