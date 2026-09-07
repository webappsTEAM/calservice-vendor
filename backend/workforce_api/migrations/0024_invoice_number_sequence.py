"""
Dedicated sequence backing WorkforceInvoice.invoice_number.

Same reasoning as 0022 for quote numbers: invoice_number is unique, and
allocating it by reading MAX() and inserting races under concurrency.
nextval() cannot hand two callers the same value.
"""
from django.db import migrations

SEQUENCE = "workforce_invoice_number_seq"

CREATE_SQL = """
CREATE SEQUENCE IF NOT EXISTS workforce_invoice_number_seq;
SELECT setval(
    'workforce_invoice_number_seq',
    (SELECT COALESCE(
        MAX(NULLIF(regexp_replace(invoice_number, '[^0-9]', '', 'g'), ''))::bigint,
        0
    ) + 1 FROM workforce_invoice),
    false
);
"""

DROP_SQL = "DROP SEQUENCE IF EXISTS workforce_invoice_number_seq;"


def create_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(CREATE_SQL)


def drop_sequence(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(DROP_SQL)


class Migration(migrations.Migration):

    dependencies = [
        ("workforce_api", "0023_estimation_admin_approval_and_invoicing"),
    ]

    operations = [
        migrations.RunPython(create_sequence, drop_sequence),
    ]
