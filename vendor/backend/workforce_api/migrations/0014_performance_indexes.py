"""
0014_performance_indexes.py

Adds composite database indexes on high-frequency query patterns identified
from the actual ORM filter/ordering operations in workforce_api/views.py.

Priority tables and patterns:
  - WorkforceNotification: (recipient_id, created_at) — notification list + unread count
  - WorkforceJobOffer:     (employee_id, status, expires_at) — active offer lookup
  - WorkforceJobOffer:     (job_id, employee_id) — per-job offer retrieval
  - WorkforceJobLifecycleEvent: (job_id, employee_id, event_type) — acceptance event lookup
  - WorkforceWorkExtension: (job_id,) — bulk extension fetch
  - JobPayment:            (job_id,) — bulk payment fetch
  - WorkforceEventLog:     (user_id, event_type) — event audit queries
  - WorkforceEmployeeCompliance: (employee_id, requirement_id) — compliance gate checks

Note: ServiceRequest (jobs) and Employee tables are managed=False (Supabase-owned).
      Their indexes must be created via Supabase SQL editor, not Django migrations.
      Those patterns are documented in a comment at the bottom of this file.

Cross-database note (added 2026-09-16): every index below was originally a
migrations.RunSQL using Postgres's `CREATE INDEX CONCURRENTLY IF NOT EXISTS`
(non-blocking index build -- the whole point of `atomic = False` on this
migration). SQLite has no CONCURRENTLY keyword at all, which broke
`manage.py test` outright. _make_index_ops() below keeps the exact original
Postgres DDL (byte-for-byte, same non-concurrent-safe behavior in
production) and only swaps in a plain `CREATE INDEX IF NOT EXISTS` (no
CONCURRENTLY -- meaningless on SQLite's single-writer model anyway) when
running on SQLite.
"""
from django.db import migrations


def _make_index_ops(name, postgres_sql, reverse_sql, sqlite_sql=None):
    """
    Returns a migrations.RunPython pair that runs `postgres_sql` verbatim on
    Postgres and `sqlite_sql` (or `postgres_sql` with "CONCURRENTLY " simply
    stripped, when no override is given) on every other backend.
    """
    sqlite_fallback = sqlite_sql or postgres_sql.replace("CONCURRENTLY ", "")

    def forwards(apps, schema_editor):
        if schema_editor.connection.vendor == "postgresql":
            schema_editor.execute(postgres_sql)
        else:
            schema_editor.execute(sqlite_fallback)

    def backwards(apps, schema_editor):
        schema_editor.execute(reverse_sql)

    forwards.__name__ = f"forwards_{name}"
    backwards.__name__ = f"backwards_{name}"
    return migrations.RunPython(forwards, backwards)


class Migration(migrations.Migration):

    atomic = False

    dependencies = [
        ("workforce_api", "0013_workforcejoboffer_wave_id_and_more"),
    ]

    operations = [
        # ── WorkforceNotification ──────────────────────────────────────────────
        # Used by: WorkforceNotificationListView
        #   filter(recipient=user).order_by("-created_at")[:50]
        _make_index_ops(
            "notification_recipient_created",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforce_notification_recipient_created
                ON workforce_notification (recipient_id, created_at DESC);
            """,
            "DROP INDEX IF EXISTS idx_workforce_notification_recipient_created;",
        ),

        # ── WorkforceJobOffer: active offer lookup ─────────────────────────────
        # Used by: WorkforceJobListView (employee path)
        #   filter(employee=emp, status="OFFERED", expires_at__gt=now)
        _make_index_ops(
            "joboffer_employee_status_expires",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforcejoboffer_employee_status_expires
                ON workforce_job_offer (employee_id, status, expires_at)
                WHERE status = 'OFFERED';
            """,
            "DROP INDEX IF EXISTS idx_workforcejoboffer_employee_status_expires;",
        ),

        # ── WorkforceJobOffer: per-job offer retrieval ─────────────────────────
        # Used by: WorkforceJobSerializer._get_emp_offer and bulk fetch
        #   filter(job_id__in=job_ids, employee=emp)
        _make_index_ops(
            "joboffer_job_employee",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforcejoboffer_job_employee
                ON workforce_job_offer (job_id, employee_id);
            """,
            "DROP INDEX IF EXISTS idx_workforcejoboffer_job_employee;",
        ),

        # ── WorkforceJobLifecycleEvent: acceptance event lookup ───────────────
        # Used by: WorkforceJobListView (employee path) bulk fetch
        #   filter(job_id__in=job_ids, employee=emp, event_type=EMPLOYEE_JOB_ACCEPTED)
        _make_index_ops(
            "joblifecycle_job_emp_type",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforcejob_lifecycle_job_emp_type
                ON workforce_job_lifecycle_event (job_id, employee_id, event_type);
            """,
            "DROP INDEX IF EXISTS idx_workforcejob_lifecycle_job_emp_type;",
        ),

        # ── WorkforceWorkExtension: bulk fetch per job list ────────────────────
        # Used by: WorkforceJobListView (employee path)
        #   filter(job_id__in=job_ids).order_by("-created_at")
        _make_index_ops(
            "workextension_job_created",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforceworkextension_job_created
                ON workforce_work_extension (job_id, created_at DESC);
            """,
            "DROP INDEX IF EXISTS idx_workforceworkextension_job_created;",
        ),

        # ── JobPayment: bulk fetch per job list ────────────────────────────────
        # Used by: WorkforceJobListView (employee path)
        #   filter(job_id__in=job_ids)
        _make_index_ops(
            "jobpayment_job_id",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_jobpayment_job_id
                ON workforce_job_payment (job_id);
            """,
            "DROP INDEX IF EXISTS idx_jobpayment_job_id;",
        ),

        # ── WorkforceEmployeeCompliance: eligibility gate G4 ──────────────────
        # Used by: WorkforceDispatchEligibleListView prefetch
        #   filter(requirement__is_mandatory=True) on employee
        _make_index_ops(
            "compliance_emp_req",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforce_compliance_emp_req
                ON workforce_employee_compliance (employee_id, requirement_id);
            """,
            "DROP INDEX IF EXISTS idx_workforce_compliance_emp_req;",
        ),

        # ── WorkforceNotification: is_read flag lookup ─────────────────────────
        # Used by: mark-read and clear operations
        #   filter(recipient=user, is_read=False)
        _make_index_ops(
            "notification_recipient_unread",
            """
                CREATE INDEX CONCURRENTLY IF NOT EXISTS
                    idx_workforce_notification_recipient_unread
                ON workforce_notification (recipient_id, is_read)
                WHERE is_read = FALSE;
            """,
            "DROP INDEX IF EXISTS idx_workforce_notification_recipient_unread;",
        ),
    ]

    # ── Supabase-managed tables (managed=False) ────────────────────────────────
    # These tables are managed by the Supabase project, not Django.
    # The following indexes should be created via the Supabase SQL Editor:
    #
    # -- ServiceRequest (jobs): status filter + ordering
    # CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_company_status_created
    #   ON service_requests_servicerequest (company_id, status, created_at DESC);
    #
    # -- ServiceRequest: assigned employee + status (dispatch queries)
    # CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sr_assigned_employee_status
    #   ON service_requests_servicerequest (assigned_employee_id, status)
    #   WHERE status NOT IN ('completed', 'cancelled');
    #
    # -- Employee: company + is_active (fleet map, dispatch candidate queries)
    # CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employee_company_active
    #   ON employees_employee (company_id, is_active)
    #   WHERE is_active = TRUE;
    #
    # -- Employee: is_online + company (fleet map filter)
    # CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_employee_company_online
    #   ON employees_employee (company_id, is_online);
