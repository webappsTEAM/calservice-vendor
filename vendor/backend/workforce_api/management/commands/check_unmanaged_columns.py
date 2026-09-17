"""
Verify that every field on a managed = False model is a real database column.

Django does not create or migrate these tables -- the database is the source of
truth and the model is a description of it. Two failure modes follow, and
neither announces itself:

  * A field declared here with no column behind it makes every query on that
    model fail, because Django puts the column in the SELECT list.
  * A column the model does not declare is invisible. Assigning to it sets a
    plain Python attribute and save() writes nothing -- which is exactly how
    quote approval came to assign subtotal_amount, discount_amount,
    final_amount and payment_collected_at and persist none of them.

Run this against a database before deploying a change to any unmanaged model.

    python manage.py check_unmanaged_columns
    python manage.py check_unmanaged_columns --strict   # also fail on extras
"""
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = "Check managed=False models against the actual database schema."

    def add_arguments(self, parser):
        parser.add_argument(
            "--strict", action="store_true",
            help="Also fail when the table has columns no model field declares.",
        )
        parser.add_argument(
            "--app", default=None,
            help="Limit to one app label.",
        )

    def handle(self, *args, **options):
        unmanaged = [
            m for m in apps.get_models()
            if not m._meta.managed
            and (not options["app"] or m._meta.app_label == options["app"])
        ]
        if not unmanaged:
            self.stdout.write("No unmanaged models found.")
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name, column_name
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                """
            )
            actual = {}
            for table, column in cursor.fetchall():
                actual.setdefault(table, set()).add(column)

        missing_tables, missing_columns, extra_columns = [], [], []

        for model in sorted(unmanaged, key=lambda m: m._meta.db_table):
            table = model._meta.db_table
            if table not in actual:
                missing_tables.append((model, table))
                continue

            declared = {
                f.column for f in model._meta.concrete_fields
                if getattr(f, "column", None)
            }
            gone = sorted(declared - actual[table])
            if gone:
                missing_columns.append((model, table, gone))
            spare = sorted(actual[table] - declared)
            if spare:
                extra_columns.append((model, table, spare))

        for model, table, cols in extra_columns:
            self.stdout.write(self.style.WARNING(
                f"{model._meta.label}: table {table} has {len(cols)} column(s) the "
                f"model does not declare, so this copy cannot read or write them: "
                f"{', '.join(cols)}"
            ))

        problems = []
        for model, table in missing_tables:
            problems.append(f"{model._meta.label}: table {table} does not exist.")
        for model, table, cols in missing_columns:
            problems.append(
                f"{model._meta.label}: declares {len(cols)} field(s) with no column "
                f"in {table} -- every query on this model will fail: {', '.join(cols)}"
            )
        if options["strict"]:
            for model, table, cols in extra_columns:
                problems.append(
                    f"{model._meta.label}: {table} has undeclared columns: {', '.join(cols)}"
                )

        if problems:
            raise CommandError(
                "Unmanaged models do not match the database:\n\n  "
                + "\n  ".join(problems)
            )

        self.stdout.write(self.style.SUCCESS(
            f"All {len(unmanaged)} unmanaged models match the database schema."
            + (f" ({len(extra_columns)} with undeclared extra columns — see warnings above.)"
               if extra_columns else "")
        ))
