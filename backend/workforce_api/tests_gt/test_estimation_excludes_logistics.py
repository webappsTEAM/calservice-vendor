"""
The AC-estimation module must not swallow Goods & Transport bookings.

`service_category__icontains="ac"` looks like a reasonable way to find AC
jobs until you notice that "packers_movers" contains the substring "ac"
(p-AC-kers). Every Packers & Movers booking therefore matched the AC
estimation queryset, and _serialize_estimation reads
sr.technician_arrived_at -- a column dropped from the shared schema and not
present on this app's ServiceRequest mirror. One Packers & Movers booking
in the database was enough to 500 the whole vendor estimation dashboard.

Source-level tests: this app's ServiceRequest is an unmanaged mirror of a
table another app owns, so there is no local schema to build a fixture
against.
"""
import re

from django.test import SimpleTestCase

SOURCE = "service_requests/vendor_views.py"


def _source():
    with open(SOURCE, encoding="utf-8", errors="replace") as fh:
        return fh.read()


class EstimationCategoryFilterTests(SimpleTestCase):
    def test_the_substring_trap_is_real(self):
        # The premise, stated as a test so nobody "simplifies" the exclusion
        # back out on the grounds that it looks redundant.
        self.assertIn("ac", "packers_movers")
        self.assertNotIn("ac", "goods_transport_truck")

    def test_every_ac_queryset_excludes_logistics_categories(self):
        src = _source()
        # Matched inside models.Q(...) specifically, so the prose in the
        # comment above each filter is not counted as a filter.
        ac_filters = re.findall(r'models\.Q\(service_category__icontains="ac"\)', src)
        exclusions = re.findall(r"~models\.Q\(service_category__in=_LOGISTICS_CATEGORIES\)", src)
        self.assertTrue(ac_filters, "the AC filter should still exist")
        self.assertEqual(
            len(exclusions), len(ac_filters),
            "every service_category__icontains='ac' filter needs the logistics exclusion "
            f"({len(ac_filters)} filters, {len(exclusions)} exclusions)",
        )

    def test_the_lazy_estimation_create_skips_logistics(self):
        src = _source()
        self.assertIn("_is_logistics = ", src)
        self.assertRegex(src, r"if not est and not _is_logistics")

    def test_the_logistics_set_covers_every_bookable_category(self):
        from service_requests.vendor_views import _LOGISTICS_CATEGORIES
        from workforce_api.services.automatic_dispatch import LOGISTICS_SERVICE_CATEGORIES

        # A local copy is fine, a DIVERGENT local copy is not.
        self.assertEqual(_LOGISTICS_CATEGORIES, set(LOGISTICS_SERVICE_CATEGORIES))

    def test_arrived_at_is_read_defensively(self):
        # The mirror has no technician_arrived_at column; a bare attribute
        # read raises AttributeError and a bare save raises FieldDoesNotExist.
        src = _source()
        self.assertNotRegex(src, r'^\s*"arrived_at": sr\.technician_arrived_at\.', )
        self.assertIn('getattr(sr, "technician_arrived_at", None)', src)
        self.assertIn('hasattr(sr, "technician_arrived_at")', src)

    def test_the_mirror_really_lacks_the_column(self):
        from django.apps import apps

        model = apps.get_model("service_requests", "ServiceRequest")
        names = {f.name for f in model._meta.get_fields()}
        self.assertNotIn(
            "technician_arrived_at", names,
            "if this column is back on the mirror, the defensive reads above can be simplified",
        )
