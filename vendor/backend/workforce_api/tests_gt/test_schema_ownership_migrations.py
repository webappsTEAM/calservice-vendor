"""
workforce_api/tests_gt/test_schema_ownership_migrations.py

Regression tests for the two state-aware ownership migrations:

    employees.0002_own_employee_tables
    workforce_api.0023_own_workforce_mirror_tables

Ten models in this app are declared managed=False, so their CreateModel
operations are state-only and create nothing; the Customer app does not create
them either (it removed its workforce models in
service_requests.0038_remove_workforce_models_and_fields). In production the
tables survive only because they predate that split. On a fresh database
nothing created them, and the vendor could not bootstrap at all.

The migrations reconcile the database WITHOUT flipping managed=True on disk
and without any state operations. These tests drive the decision logic
directly with a stubbed connection, so they are backend-independent -- the
real tables already exist in a test database, which would otherwise make every
branch untestable.
"""
import importlib

from django.test import SimpleTestCase


def _load(dotted):
    return importlib.import_module(dotted)


EMPLOYEES_MIG = "employees.migrations.0002_own_employee_tables"
WORKFORCE_MIG = "workforce_api.migrations.0027_own_workforce_mirror_tables"


class _FakeCursor:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _FakeIntrospection:
    def __init__(self, tables, columns):
        self._tables = tables
        self._columns = columns          # {table: {col, ...}}

    def table_names(self):
        return list(self._tables)

    def get_table_description(self, cursor, table):
        class Col:
            def __init__(self, name):
                self.name = name
        return [Col(c) for c in self._columns.get(table, set())]


class _FakeConnection:
    def __init__(self, tables, columns):
        self.introspection = _FakeIntrospection(tables, columns)

    def cursor(self):
        return _FakeCursor()


class _FakeSchemaEditor:
    def __init__(self, tables, columns):
        self.connection = _FakeConnection(tables, columns)
        self.created = []

    def create_model(self, model):
        self.created.append(model._meta.db_table)


class _OwnershipMigrationContract:
    """Shared contract; both migrations must satisfy every branch."""

    dotted = None

    def setUp(self):
        self.mod = _load(self.dotted)
        from django.apps import apps as live_apps
        self.models = [live_apps.get_model(a, m) for a, m in self.mod.TABLES]
        self.tables = [m._meta.db_table for m in self.models]
        self.full_columns = {
            m._meta.db_table: {f.column for f in m._meta.local_fields} for m in self.models
        }

    # ── every table already present and complete ────────────────────────

    def test_is_a_noop_when_every_table_already_exists(self):
        ed = _FakeSchemaEditor(set(self.tables), dict(self.full_columns))
        self.mod._validate_then_create(ed, self.mod.TABLES)
        self.assertEqual(ed.created, [], "migration touched an already-correct database")

    # ── fresh database ──────────────────────────────────────────────────

    def test_creates_every_table_on_a_fresh_database(self):
        ed = _FakeSchemaEditor(set(), {})
        self.mod._validate_then_create(ed, self.mod.TABLES)
        self.assertEqual(ed.created, self.tables,
                         "not every owned table was created, or the order changed")

    def test_creates_only_the_tables_that_are_missing(self):
        present = {self.tables[0]}
        ed = _FakeSchemaEditor(present, {self.tables[0]: self.full_columns[self.tables[0]]})
        self.mod._validate_then_create(ed, self.mod.TABLES)
        self.assertEqual(ed.created, self.tables[1:])

    # ── partial / mismatched schema ─────────────────────────────────────

    def test_refuses_when_an_existing_table_is_missing_a_column(self):
        broken = self.tables[0]
        cols = dict(self.full_columns)
        cols[broken] = set(list(self.full_columns[broken])[:-1])   # drop one column
        dropped = (self.full_columns[broken] - cols[broken]).pop()
        ed = _FakeSchemaEditor(set(self.tables), cols)
        with self.assertRaises(RuntimeError) as ctx:
            self.mod._validate_then_create(ed, self.mod.TABLES)
        msg = str(ctx.exception)
        self.assertIn(broken, msg)
        self.assertIn(dropped, msg)
        self.assertIn("data decision", msg)

    def test_nothing_is_created_when_the_schema_is_refused(self):
        # validate-before-create: a database with one bad table and one
        # missing table must be refused WITHOUT the missing one being made.
        broken = self.tables[0]
        cols = {broken: set(list(self.full_columns[broken])[:-1])}
        ed = _FakeSchemaEditor({broken}, cols)          # the rest are absent
        with self.assertRaises(RuntimeError):
            self.mod._validate_then_create(ed, self.mod.TABLES)
        self.assertEqual(ed.created, [], "created tables despite refusing the schema")

    # ── safety properties ───────────────────────────────────────────────

    def test_extra_unknown_columns_are_tolerated(self):
        cols = {t: set(c) | {"legacy_column_from_production"} for t, c in self.full_columns.items()}
        ed = _FakeSchemaEditor(set(self.tables), cols)
        self.mod._validate_then_create(ed, self.mod.TABLES)   # must not raise
        self.assertEqual(ed.created, [])

    def test_reverse_is_a_noop(self):
        self.assertIsNone(self.mod.noop_reverse(None, None))

    def test_models_are_left_unmanaged_afterwards(self):
        ed = _FakeSchemaEditor(set(), {})
        self.mod._validate_then_create(ed, self.mod.TABLES)
        for m in self.models:
            self.assertFalse(m._meta.managed,
                             "%s was left managed=True; models.py must be untouched"
                             % m.__name__)

    def test_the_migration_declares_no_state_operations(self):
        # State is already correct; these migrations reconcile the DATABASE only.
        ops = self.mod.Migration.operations
        self.assertEqual(len(ops), 1)
        self.assertEqual(type(ops[0]).__name__, "RunPython")


class EmployeesOwnershipMigrationTests(_OwnershipMigrationContract, SimpleTestCase):
    dotted = EMPLOYEES_MIG


class WorkforceOwnershipMigrationTests(_OwnershipMigrationContract, SimpleTestCase):
    dotted = WORKFORCE_MIG


class OwnedTableInventoryTests(SimpleTestCase):
    """The two migrations together must own every orphaned table, and no more."""

    def test_they_cover_exactly_the_ten_orphaned_models(self):
        owned = set(_load(EMPLOYEES_MIG).TABLES) | set(_load(WORKFORCE_MIG).TABLES)
        self.assertEqual(len(owned), 10)
        self.assertEqual(
            sorted(owned),
            sorted([
                ("employees", "Employee"), ("employees", "PresenceLog"),
                ("service_requests", "EmployeeJob"),
                ("service_requests", "Estimation"),
                ("service_requests", "EstimationFee"),
                ("service_requests", "EstimationQuotation"),
                ("service_requests", "EstimationQuotationItem"),
                ("service_requests", "Inspection"),
                ("service_requests", "InspectionFinding"),
                ("service_requests", "InspectionPhoto"),
            ]),
        )

    def test_no_customer_owned_mirror_is_claimed(self):
        # Mirrors of tables the CUSTOMER app owns must stay unowned here.
        owned_tables = set()
        from django.apps import apps as live_apps
        for dotted in (EMPLOYEES_MIG, WORKFORCE_MIG):
            for a, m in _load(dotted).TABLES:
                owned_tables.add(live_apps.get_model(a, m)._meta.db_table)
        for customer_owned in (
            "accounts_user", "companies_company", "service_requests_servicerequest",
            "service_requests_trip_stop", "service_requests_payment",
            "service_requests_catalogcategory", "service_requests_service",
            "settings_hub_invoice",
        ):
            self.assertNotIn(customer_owned, owned_tables)
