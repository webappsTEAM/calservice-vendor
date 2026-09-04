"""
Detects jobs stuck in an assigned-but-not-arrived state for longer than an
expected arrival window, and treats them as a technician no-show: releases
the non-responsive technician, kicks off automatic redispatch to a new
candidate (excluding the no-show technician), and notifies the job's
company admins.

Root cause this addresses: nothing in this codebase ever detected a
no-show/arrival-timeout despite design docs describing the feature -- a
technician who accepted a job and then went unresponsive (phone died, app
crashed, simply never showed up) left the job silently stuck in
ASSIGNED/ACCEPTED/ON_THE_WAY/EN_ROUTE forever. The customer saw no
progress, no admin was told, and the technician's availability was never
freed for other work.

Anchor timestamp: EmployeeJob.assigned_date (auto_now_add, always set the
moment a job is assigned) is used as the fallback anchor; EmployeeJob.
accepted_date (set by state_machine.apply_transition() the moment the
technician accepts) is preferred when present, since "accepted but never
arrived" is the clearer no-show signal than "assigned but not yet
accepted" (the latter is also covered -- an offer that's simply never
accepted -- by the existing expire_and_reassign_offers() dispatch-offer
expiry, a different and already-handled case).

This command is safe to run repeatedly and safe to run broadly: it only
acts on jobs that are still, right now, in one of the no-show-candidate
statuses and still past the threshold -- a job that already moved on
(arrived, cancelled, completed by the time this runs) is simply skipped
next time round, and re-running against an already-redispatched job is a
no-op because it's no longer in one of those statuses.

Scheduling: this environment has no live server to install a cron job or
Celery beat schedule on, so this command is NOT wired to run automatically.
To actually enable no-show detection in production, schedule it on the
deployment host, e.g. a crontab entry running every 5 minutes:

    */5 * * * * cd /path/to/vendor/backend && python manage.py detect_job_no_shows >> /var/log/caltrack/no_show_detection.log 2>&1

Usage:
  python manage.py detect_job_no_shows --job AC4964 --dry-run                 # diagnose one job
  python manage.py detect_job_no_shows --job AC4964                          # act on that one job if stuck
  python manage.py detect_job_no_shows --dry-run                             # see every stuck job company-wide
  python manage.py detect_job_no_shows                                      # act on every stuck job (default 45-minute threshold)
  python manage.py detect_job_no_shows --threshold-minutes 30                # use a tighter window
"""
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from service_requests.models import ServiceRequest, EmployeeJob
from service_requests.state_machine import apply_transition

# Statuses where a job has been handed to a specific technician but hasn't
# yet reached ARRIVED -- i.e. exactly the window in which a no-show can
# happen. Matches ALLOWED_TRANSITIONS' "-> redispatching" set in
# state_machine.py, so every status this command acts on is guaranteed to
# be a legal transition source.
NO_SHOW_CANDIDATE_STATUSES = ["assigned", "accepted", "on_the_way", "en_route"]

DEFAULT_THRESHOLD_MINUTES = 45


class Command(BaseCommand):
    help = "Detects technician no-shows (assigned/accepted but never arrived past the expected window) and triggers redispatch + admin notification."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Only report which jobs look like no-shows -- makes no changes.",
        )
        parser.add_argument(
            "--job", type=str, default=None,
            help="Only check this one job, by its request_id (e.g. AC4964).",
        )
        parser.add_argument(
            "--threshold-minutes", type=int, default=DEFAULT_THRESHOLD_MINUTES,
            help=f"How long a job may sit assigned-but-not-arrived before being treated as a no-show (default {DEFAULT_THRESHOLD_MINUTES}).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        only_job = options["job"]
        threshold_minutes = options["threshold_minutes"]

        qs = ServiceRequest.objects.filter(
            status__in=NO_SHOW_CANDIDATE_STATUSES,
            assigned_employee__isnull=False,
        ).select_related("assigned_employee", "assigned_employee__user", "company")
        if only_job:
            qs = qs.filter(request_id=only_job)

        if not qs.exists():
            self.stdout.write(self.style.WARNING(
                f"No job found matching request_id={only_job!r} in an assigned-but-not-arrived status."
                if only_job else
                "No jobs currently assigned-but-not-arrived."
            ))
            return

        now = timezone.now()
        cutoff = now - timezone.timedelta(minutes=threshold_minutes)

        flagged, redispatched, still_ok = 0, 0, 0

        for job in qs:
            emp_job = (
                EmployeeJob.objects
                .filter(service_request=job, is_primary=True)
                .order_by("-assigned_date")
                .first()
            )
            anchor = (emp_job.accepted_date if emp_job and emp_job.accepted_date else None) or (
                emp_job.assigned_date if emp_job else job.updated_at
            )
            if not anchor or anchor > cutoff:
                still_ok += 1
                continue

            elapsed_minutes = int((now - anchor).total_seconds() // 60)
            flagged += 1
            self.stdout.write(
                f"  NO-SHOW  {job.request_id} (status={job.status}, "
                f"employee={job.assigned_employee_id}, stuck for {elapsed_minutes}m, threshold={threshold_minutes}m)"
            )

            if dry_run:
                continue

            self._handle_no_show(job, emp_job, elapsed_minutes)
            redispatched += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. flagged={flagged} redispatched={redispatched} still_ok={still_ok} "
                f"threshold_minutes={threshold_minutes} dry_run={dry_run}"
            )
        )

    def _handle_no_show(self, job, emp_job, elapsed_minutes):
        from workforce_api.models import WorkforceEventLog, WorkforceNotification

        no_show_employee = job.assigned_employee
        no_show_employee_id = job.assigned_employee_id
        try:
            employee_label = (
                getattr(no_show_employee, "full_name", None)
                or (no_show_employee.user.get_full_name() if getattr(no_show_employee, "user", None) else None)
                or f"Employee #{no_show_employee_id}"
            )
        except Exception:
            employee_label = f"Employee #{no_show_employee_id}"

        try:
            WorkforceEventLog.objects.create(
                event_type="JOB_NO_SHOW_DETECTED",
                payload={
                    "job_id": job.id,
                    "request_id": job.request_id,
                    "employee_id": no_show_employee_id,
                    "elapsed_minutes": elapsed_minutes,
                    "previous_status": job.status,
                },
            )
        except Exception as log_err:
            self.stdout.write(self.style.WARNING(f"    Could not write WorkforceEventLog for {job.request_id}: {log_err}"))

        try:
            # Matches WorkforceJobCancelAssignmentView's established pattern
            # for this exact "release the technician, go back to dispatch"
            # transition: clear assigned_employee before transitioning, so
            # the job doesn't sit in 'redispatching' still pointing at the
            # no-show technician (customer tracking, admin views, etc. all
            # read assigned_employee directly).
            job.assigned_employee = None
            job.save(update_fields=["assigned_employee"])
            apply_transition(job, "redispatching", actor=None)
        except ValidationError as ve:
            self.stdout.write(self.style.ERROR(f"    -> could not transition {job.request_id} to redispatching: {ve}"))
            return

        dispatch_message = "Redispatch not attempted."
        try:
            from workforce_api.services.automatic_dispatch import dispatch_job
            success, msg = dispatch_job(job, exclude_employee_ids=[no_show_employee_id])
            dispatch_message = msg
            self.stdout.write(self.style.SUCCESS(
                f"    -> {job.request_id}: released {employee_label}, redispatch {'started' if success else 'pending'}: {msg}"
            ))
        except Exception as dispatch_err:
            dispatch_message = f"Redispatch attempt raised an error: {dispatch_err}"
            self.stdout.write(self.style.ERROR(f"    -> {job.request_id}: {dispatch_message}"))

        try:
            admins = list(
                job.company.users.filter(Q(role__in=["admin", "manager"]) | Q(is_staff=True))
                if job.company else []
            )
            for admin_user in admins:
                WorkforceNotification.objects.create(
                    recipient=admin_user,
                    title=f"Technician No-Show — {job.request_id}",
                    message=(
                        f"{employee_label} did not arrive for job {job.request_id} "
                        f"({elapsed_minutes} minutes past the expected window). The job has been "
                        f"released and sent back to dispatch. {dispatch_message}"
                    ),
                    notification_type="JOB_NO_SHOW_DETECTED",
                    company=job.company,
                    related_object_id=str(job.pk),
                )
        except Exception as notify_err:
            self.stdout.write(self.style.WARNING(f"    Could not notify admins for {job.request_id}: {notify_err}"))
