"""
Dedicated sequence backing WorkforceQuote.quote_number.

quote_number is unique. The previous allocator read MAX(id) and then
inserted, which two concurrent creates can both pass - the loser gets a
500 from a unique-constraint violation. A sequence removes the race:
nextval() is atomic and never returns the same value twice.

Seeded past the highest number already issued so existing quotes keep
their numbers.
"""
from django.db import migrations

SEQUENCE = "workforce_quote_number_seq"

CREATE_SQL = """
CREATE SEQUENCE IF NOT EXISTS %(seq)s;
SELECT setval(
    '%(seq)s',
    (SELECT COALESCE(
        MAX(NULLIF(regexp_replace(quote_number, '[^0-9]', '', 'g'), ''))::bigint,
        0
    ) + 1 FROM workforce_quote),
    false
);
""" % {"seq": SEQUENCE}

DROP_SQL = "DROP SEQUENCE IF EXISTS %s;" % SEQUENCE


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
        ('workforce_api', '0021_merge_20260902_1216'),
        ('workforce_api', '0021_merge_20260902_1700'),
    ]

    operations = [
        migrations.RunPython(create_sequence, drop_sequence),
    ]
