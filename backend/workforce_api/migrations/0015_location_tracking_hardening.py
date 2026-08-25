"""
workforce_api/migrations/0015_location_tracking_hardening.py

Safe data migration + schema migration for location tracking hardening:
1. Removes duplicate ACTIVE tracking sessions (keeps newest by id)
2. Adds new fields to JobTrackingSession for movement/geofence state and event throttle
3. Adds DB-level partial unique constraint (one ACTIVE session per job)
4. Adds composite index to JobLocationPoint for efficient movement lookups
5. Fixes index names that were missing in migration 0008
"""
from django.db import migrations, models


def deduplicate_active_sessions(apps, schema_editor):
    """
    Safely close duplicate ACTIVE tracking sessions.
    For any job with multiple ACTIVE sessions, keep the one with the highest id
    (newest) and close the others as CANCELLED with a note.
    """
    JobTrackingSession = apps.get_model("workforce_api", "JobTrackingSession")

    # Find job_ids that have more than one ACTIVE session
    from django.db.models import Count
    duplicate_jobs = (
        JobTrackingSession.objects
        .filter(status="ACTIVE")
        .values("job_id")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
        .values_list("job_id", flat=True)
    )

    closed_count = 0
    for job_id in duplicate_jobs:
        sessions = list(
            JobTrackingSession.objects
            .filter(job_id=job_id, status="ACTIVE")
            .order_by("-id")  # newest first
        )
        # Keep the first (newest), close the rest
        for session in sessions[1:]:
            session.status = "CANCELLED"
            session.save(update_fields=["status"])
            closed_count += 1

    if closed_count:
        print(f"\n  [0015] Closed {closed_count} duplicate ACTIVE tracking session(s).")


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0014_estimation_and_quotation_schema"),
    ]

    operations = [
        # Step 1: Data migration — close duplicates before adding the constraint
        migrations.RunPython(deduplicate_active_sessions, noop_reverse),

        # Step 2: Add new fields to JobTrackingSession
        migrations.AddField(
            model_name="jobtrackingsession",
            name="movement_status",
            field=models.CharField(blank=True, default="UNKNOWN", max_length=20),
        ),
        migrations.AddField(
            model_name="jobtrackingsession",
            name="geofence_status",
            field=models.CharField(blank=True, default="OUTSIDE", max_length=20),
        ),
        migrations.AddField(
            model_name="jobtrackingsession",
            name="prev_latitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobtrackingsession",
            name="prev_longitude",
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobtrackingsession",
            name="prev_captured_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobtrackingsession",
            name="last_event_emitted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobtrackingsession",
            name="last_event_state_key",
            field=models.CharField(blank=True, default="", max_length=60),
        ),

        # Step 3: Remove the old un-named indexes from migration 0008 and add named ones
        # (Django requires names for constraint-conditional indexes)
        migrations.AlterModelOptions(
            name="jobtrackingsession",
            options={"ordering": ["-created_at"]},
        ),
        migrations.AlterModelOptions(
            name="joblocationpoint",
            options={"ordering": ["tracking_session", "sequence_number", "created_at"]},
        ),

        # Step 4: Add DB-level partial unique constraint (idempotent — uses IF NOT EXISTS)
        migrations.RunSQL(
            sql="""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = 'workforce_job_tracking_session'
                          AND indexname = 'unique_active_tracking_session_per_job'
                    ) THEN
                        CREATE UNIQUE INDEX unique_active_tracking_session_per_job
                        ON workforce_job_tracking_session (job_id)
                        WHERE (status = 'ACTIVE');
                    END IF;
                END
                $$;
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),

        # Step 5–7: Add indexes (idempotent — uses IF NOT EXISTS)
        migrations.RunSQL(
            sql="""
                CREATE INDEX IF NOT EXISTS wf_ts_job_status_idx
                    ON workforce_job_tracking_session (job_id, status);
                CREATE INDEX IF NOT EXISTS wf_ts_emp_status_idx
                    ON workforce_job_tracking_session (employee_id, status);
                CREATE INDEX IF NOT EXISTS wf_lp_job_emp_cap_idx
                    ON workforce_job_location_point (job_id, employee_id, captured_at);
                CREATE INDEX IF NOT EXISTS wf_lp_session_time_idx
                    ON workforce_job_location_point (tracking_session_id, created_at);
                CREATE INDEX IF NOT EXISTS wf_lp_job_time_idx
                    ON workforce_job_location_point (job_id, created_at);
            """,
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
