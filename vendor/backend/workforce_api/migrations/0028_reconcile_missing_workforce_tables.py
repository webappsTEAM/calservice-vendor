"""
Reconcile physical PostgreSQL tables for workforce models that were recorded as
applied in django_migrations but missing in the remote staging database schema.

Follows the identical pattern established in 0023_own_workforce_mirror_tables
and employees.0002_own_employee_tables:
  * table already present with every expected column -> no-op;
  * table present but missing declared columns        -> STOP LOUDLY;
  * table missing                                     -> created from the live model.

Nothing is dropped, renamed, or truncated. Reverse is a deliberate no-op.
"""
from django.db import migrations

TABLES = [
    ("workforce_api", "WorkforceRequiredDocument"),
    ("workforce_api", "WorkforceEmployeeDocument"),
    ("workforce_api", "Vehicle"),
    ("workforce_api", "CashSettlement"),
    ("workforce_api", "WorkforcePayPeriod"),
    ("workforce_api", "WorkforcePayslip"),
]


def _validate_then_create(schema_editor, specs):
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
            "this app now owns (%s). Reconcile it deliberately and re-run. "
            "Nothing has been created or changed." % detail
        )

    for model in to_create:
        schema_editor.create_model(model)


def reconcile_missing_workforce_tables(apps, schema_editor):
    _validate_then_create(schema_editor, TABLES)


def noop_reverse(apps, schema_editor):
    """Never drop tables that hold live staging/production data."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0027_own_workforce_mirror_tables"),
    ]

    operations = [
        migrations.RunPython(reconcile_missing_workforce_tables, noop_reverse),
    ]
