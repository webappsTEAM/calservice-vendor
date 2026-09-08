"""
Give the vendor app real ownership of the eight workforce tables that live
under the `service_requests` label but that the Customer app does not create.

Why the migration lives in workforce_api and not in service_requests:
both apps declare an app labelled `service_requests` and they SHARE one
database, so they share one django_migrations table. 95 rows are already
recorded there under app='service_requests' -- all written by the Customer
app. A vendor migration under that label would collide with the Customer's
history by (app, name) and be treated as already applied. workforce_api is a
vendor-only label, so the bookkeeping is unambiguous.

The models themselves stay managed=False and are NOT modified: this migration
carries no state operations, only the database reconciliation, exactly like
the Customer app's 0071_restore_package_service_column and the sibling
employees.0002.

  * table already present with every expected column -> no-op;
  * table present but missing declared columns        -> STOP LOUDLY;
  * table missing                                     -> created from the
                                                         live model.

Nothing is dropped, renamed, truncated or altered, and reverse is a
deliberate no-op. Every external FK target (service_requests_servicerequest,
accounts_user, service_requests_service, employees_employee) is owned by the
Customer app or by employees.0002, both of which run first.
"""
from django.db import migrations

# (app_label, model_name) in FK dependency order -- Estimation before the
# things that point at it, Inspection before its findings and photos.
TABLES = [
    ("service_requests", "EmployeeJob"),
    ("service_requests", "Estimation"),
    ("service_requests", "EstimationFee"),
    ("service_requests", "EstimationQuotation"),
    ("service_requests", "EstimationQuotationItem"),
    ("service_requests", "Inspection"),
    ("service_requests", "InspectionFinding"),
    ("service_requests", "InspectionPhoto"),
]


def _validate_then_create(schema_editor, specs):
    """
    Two passes on purpose: every existing table is validated BEFORE anything
    is created, so a database with a partial schema is refused without having
    been half-modified first.
    """
    from django.apps import apps as live_apps

    connection = schema_editor.connection
    existing = set(connection.introspection.table_names())

    mismatches = []
    to_create = []
    for app_label, model_name in specs:
        model = live_apps.get_model(app_label, model_name)
        table = model._meta.db_table
        expected = {f.column for f in model._meta.local_fields}
        if table not in existing:
            to_create.append(model)
            continue
        with connection.cursor() as cursor:
            actual = {c.name for c in connection.introspection.get_table_description(cursor, table)}
        missing = sorted(expected - actual)
        if missing:
            mismatches.append((table, missing))

    if mismatches:
        detail = "; ".join("%s is missing %s" % (t, ", ".join(c)) for t, c in mismatches)
        raise RuntimeError(
            "Refusing to continue: an existing table does not match the model "
            "this app now owns (%s). Adding columns to a populated production "
            "table is a data decision, not a schema one -- reconcile it "
            "deliberately and re-run. Nothing has been created or changed."
            % detail
        )

    for model in to_create:
        was_managed = model._meta.managed
        model._meta.managed = True          # in-memory only; models.py is untouched
        try:
            schema_editor.create_model(model)
        finally:
            model._meta.managed = was_managed


def own_workforce_mirror_tables(apps, schema_editor):
    _validate_then_create(schema_editor, TABLES)


def noop_reverse(apps, schema_editor):
    """Never drop tables that hold live production data."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0022_gt_x04_drop_legacy_quote_models_and_cleanup"),
        # employees_employee must exist before service_requests_employeejob
        # can point a ForeignKey at it.
        ("employees", "0002_own_employee_tables"),
    ]

    operations = [
        migrations.RunPython(own_workforce_mirror_tables, noop_reverse),
    ]
