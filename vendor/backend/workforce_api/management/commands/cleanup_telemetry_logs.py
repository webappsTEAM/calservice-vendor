"""
Retention/cleanup command for the two tables that grow without bound and
have no TTL: JobLocationPoint (per-trip GPS telemetry) and the
JOB_LOCATION_UPDATE rows in WorkforceEventLog (a generic event/audit
table shared by many event types -- this command only ever touches the
JOB_LOCATION_UPDATE rows in it, never the others, since those are a
genuine audit trail (dispatch decisions, no-show detections, lifecycle
events, etc.) that this command has no business pruning).

Root cause this addresses: JobLocationPoint is written on every
meaningful GPS movement for every active job trip (see its docstring --
throttled to >20m movement or >30s interval, but still continuous for the
duration of every single job), and WorkforceEventLog's JOB_LOCATION_UPDATE
rows are written by the customer-facing realtime broadcast path
(services/realtime.py). Neither table had any cleanup mechanism, so both
grow forever -- eventually degrading query performance on tables that are
read constantly (live tracking) and consuming unbounded storage for data
that has no operational value once a job is long completed and its trip
history is no longer being displayed.

Deletion is batched (default 5,000 rows per batch) rather than a single
bulk DELETE, so this never holds a long-running lock on a table that live
job tracking is actively reading from and writing to.

This command is safe to run repeatedly: it only ever deletes rows already
past the retention window, so running it twice in a row the second run
simply finds nothing left to delete.

Scheduling: like detect_job_no_shows, this environment has no live server
to install a scheduler on. To actually enable retention in production,
schedule this on the deployment host, e.g. a nightly crontab entry:

    17 3 * * * cd /path/to/vendor/backend && python manage.py cleanup_telemetry_logs >> /var/log/caltrack/telemetry_cleanup.log 2>&1

Usage:
  python manage.py cleanup_telemetry_logs --dry-run                          # report what would be deleted, change nothing
  python manage.py cleanup_telemetry_logs                                    # delete rows past the default 90-day retention window
  python manage.py cleanup_telemetry_logs --retention-days 30                # use a shorter window
  python manage.py cleanup_telemetry_logs --batch-size 2000                  # smaller batches on a heavily-loaded DB
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

DEFAULT_RETENTION_DAYS = 90
DEFAULT_BATCH_SIZE = 5000
# Safety cap on how many batches a single invocation will run, so a
# first-ever run against years of unpruned backlog can't turn into an
# unbounded, unattended loop -- it'll just need to be run again (the next
# invocation picks up exactly where this one left off, since it always
# targets the oldest remaining rows first).
MAX_BATCHES_PER_RUN = 200


class Command(BaseCommand):
    help = "Deletes JobLocationPoint rows and JOB_LOCATION_UPDATE WorkforceEventLog rows older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Only report how many rows are past retention -- makes no changes.",
        )
        parser.add_argument(
            "--retention-days", type=int, default=DEFAULT_RETENTION_DAYS,
            help=f"Delete rows older than this many days (default {DEFAULT_RETENTION_DAYS}).",
        )
        parser.add_argument(
            "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
            help=f"Rows deleted per batch (default {DEFAULT_BATCH_SIZE}).",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        retention_days = options["retention_days"]
        batch_size = options["batch_size"]

        cutoff = timezone.now() - timezone.timedelta(days=retention_days)

        self.stdout.write(f"Retention cutoff: {cutoff.isoformat()} ({retention_days} days)")

        location_deleted = self._cleanup_location_points(cutoff, batch_size, dry_run)
        event_deleted = self._cleanup_location_events(cutoff, batch_size, dry_run)

        self.stdout.write(self.style.SUCCESS(
            f"Done. job_location_points_deleted={location_deleted} "
            f"job_location_update_events_deleted={event_deleted} dry_run={dry_run}"
        ))

    def _cleanup_location_points(self, cutoff, batch_size, dry_run):
        from workforce_api.models import JobLocationPoint

        qs = JobLocationPoint.objects.filter(captured_at__lt=cutoff)
        total = qs.count()
        if total == 0:
            self.stdout.write("  JobLocationPoint: nothing past retention.")
            return 0

        self.stdout.write(f"  JobLocationPoint: {total} row(s) past retention.")
        if dry_run:
            return 0

        return self._batched_delete(JobLocationPoint, {"captured_at__lt": cutoff}, batch_size, "JobLocationPoint")

    def _cleanup_location_events(self, cutoff, batch_size, dry_run):
        from workforce_api.models import WorkforceEventLog

        qs = WorkforceEventLog.objects.filter(event_type="JOB_LOCATION_UPDATE", created_at__lt=cutoff)
        total = qs.count()
        if total == 0:
            self.stdout.write("  WorkforceEventLog[JOB_LOCATION_UPDATE]: nothing past retention.")
            return 0

        self.stdout.write(f"  WorkforceEventLog[JOB_LOCATION_UPDATE]: {total} row(s) past retention.")
        if dry_run:
            return 0

        return self._batched_delete(
            WorkforceEventLog,
            {"event_type": "JOB_LOCATION_UPDATE", "created_at__lt": cutoff},
            batch_size,
            "WorkforceEventLog[JOB_LOCATION_UPDATE]",
        )

    def _batched_delete(self, model, filter_kwargs, batch_size, label):
        deleted_total = 0
        for _ in range(MAX_BATCHES_PER_RUN):
            batch_ids = list(
                model.objects.filter(**filter_kwargs).order_by("pk").values_list("pk", flat=True)[:batch_size]
            )
            if not batch_ids:
                break
            deleted_count, _ = model.objects.filter(pk__in=batch_ids).delete()
            deleted_total += len(batch_ids)
            self.stdout.write(f"    {label}: deleted batch of {len(batch_ids)} (running total {deleted_total}).")
        else:
            self.stdout.write(self.style.WARNING(
                f"    {label}: hit the {MAX_BATCHES_PER_RUN}-batch safety cap for this run -- "
                f"more rows may remain past retention. Run this command again to continue."
            ))
        return deleted_total
