"""
Diagnoses and repairs a ServiceRequest that's stuck in PROOF_SUBMITTED (or
IN_PROGRESS) with its payment already PAID but the job never actually
transitioned to COMPLETED.

Root cause this addresses: WorkforceJobPaymentVerifyOTPView and
WorkforceCustomerPaymentConfirmView (workforce_api/views.py) both attempt
apply_transition(job, "completed") the moment payment is confirmed, but if
that transition is rejected by ServiceRequest.is_ready_to_complete()'s gate
(an open work extension, an unfinished specialist secondary job, proof not
actually submitted, or a genuine payment-state mismatch), the rejection was
only logged as a warning -- the technician/customer still saw a "payment
confirmed" success response with no indication the job silently failed to
close. Since wallet crediting (services/commission.py:settle_completed_job)
only runs on the COMPLETED transition, a job stuck like this never pays out
even though the customer has genuinely paid.

This command is safe to run repeatedly and safe to run broadly: it never
force-completes anything -- it only acts on jobs where
ServiceRequest.is_ready_to_complete() genuinely returns True right now, and
for anything still blocked it prints the exact reason instead of guessing.

Usage:
  python manage.py complete_stuck_paid_jobs --job AC4964 --dry-run   # diagnose one job
  python manage.py complete_stuck_paid_jobs --job AC4964             # fix that one job
  python manage.py complete_stuck_paid_jobs --dry-run                # see every stuck job company-wide
  python manage.py complete_stuck_paid_jobs                          # fix every stuck job that is actually ready
"""
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError

from service_requests.models import ServiceRequest
from service_requests.state_machine import apply_transition


class Command(BaseCommand):
    help = "Diagnoses and completes jobs stuck in PROOF_SUBMITTED/IN_PROGRESS with payment already PAID."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Only report what is/isn't ready to complete -- makes no changes.",
        )
        parser.add_argument(
            "--job", type=str, default=None,
            help="Only check this one job, by its request_id (e.g. AC4964).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        only_job = options["job"]

        qs = ServiceRequest.objects.filter(status__in=["proof_submitted", "in_progress"])
        if only_job:
            qs = qs.filter(request_id=only_job)

        if not qs.exists():
            self.stdout.write(self.style.WARNING(
                f"No job found matching request_id={only_job!r} in status proof_submitted/in_progress."
                if only_job else
                "No jobs currently in status proof_submitted/in_progress."
            ))
            return

        completed, still_blocked = 0, 0
        for job in qs:
            is_ready, reason, pending_dependencies = job.is_ready_to_complete()

            if not is_ready:
                still_blocked += 1
                self.stdout.write(f"  BLOCKED  {job.request_id} (status={job.status})")
                for dep in pending_dependencies:
                    self.stdout.write(f"      - {dep}")
                continue

            self.stdout.write(f"  READY    {job.request_id} (status={job.status})")
            if dry_run:
                continue

            try:
                apply_transition(job, "completed")
                completed += 1
                self.stdout.write(self.style.SUCCESS(
                    f"    -> COMPLETED {job.request_id} -- wallet settlement now triggered."
                ))
            except ValidationError as ve:
                still_blocked += 1
                self.stdout.write(self.style.ERROR(f"    -> still blocked at transition time: {ve}"))

        self.stdout.write(
            self.style.SUCCESS(f"Done. completed={completed} still_blocked={still_blocked} dry_run={dry_run}")
        )
