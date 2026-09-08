"""
Give the vendor app real ownership of the employees_* tables.

employees.Employee and employees.PresenceLog are declared managed=False, so
0001_initial's CreateModel operations are state-only: they record the models
in Django's migration state and create nothing. The Customer app does not
create them either -- it removed its workforce models in
service_requests.0038_remove_workforce_models_and_fields and the concern moved
here, but this app was wired up as an unmanaged MIRROR rather than as the new
owner. In production the tables survive only because they predate that split;
on a fresh database nothing creates them, and time_tracking.0001_initial then
fails with `relation "employees_employee" does not exist`.

This migration does NOT flip managed=True on the models. It carries no state
operations at all -- the state is already correct -- and only reconciles the
database to it, exactly like the Customer app's
0071_restore_package_service_column:

  * table already present, all expected columns present -> no-op;
  * table present but missing columns the model declares -> STOP LOUDLY,
    because guessing at a partial production schema is how data gets lost;
  * table missing -> created from the live model, with its FKs and indexes.

Nothing is ever dropped, renamed, truncated or altered. Reverse is a
deliberate no-op: these tables hold live production data.

Employee's external FKs (accounts.User, companies.Company) point at tables the
Customer app owns, so the Customer app must migrate first -- which is already
the required deployment order.
"""
from django.db import migrations

# (app_label, model_name) in FK dependency order.
TABLES = [
    ("employees", "Employee"),
    ("employees", "PresenceLog"),
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


def own_employee_tables(apps, schema_editor):
    _validate_then_create(schema_editor, TABLES)


def noop_reverse(apps, schema_editor):
    """Never drop tables that hold live production data."""
    return


class Migration(migrations.Migration):

    dependencies = [
        ("employees", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(own_employee_tables, noop_reverse),
    ]
