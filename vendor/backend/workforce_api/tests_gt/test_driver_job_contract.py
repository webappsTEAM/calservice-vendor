"""
The contract the Flutter driver app depends on.

A logistics job is only workable on a phone if the job payload says it IS a
logistics job, says where to deliver to, and says which leg the trip is on.
Before these fields existed the leg and stop endpoints were reachable but
undiscoverable: the app had no way to tell a delivery from a repair, and
showed the pickup address as the only location on the screen.

Binding `.fields` is the check that matters -- `manage.py check` does not
instantiate serializer fields, so a ModelSerializer naming a column the
unmanaged mirror lacks passes `check` and then 500s on the first real
request. That is exactly what would have happened here: the mirror was
missing drop_latitude/drop_longitude.
"""
from django.test import SimpleTestCase

from workforce_api.serializers import WorkforceJobSerializer


DRIVER_REQUIRED_FIELDS = [
    "is_logistics",
    "drop_address",
    "drop_latitude",
    "drop_longitude",
    "drop_contact_name",
    "drop_contact_phone",
    "logistics_leg",
    "logistics_leg_updated_at",
    "trip_stop_count",
]


class DriverJobContractTests(SimpleTestCase):
    def test_serializer_binds_every_declared_field(self):
        # Fails loudly if any declared name cannot be resolved against the
        # model -- the failure mode `manage.py check` cannot see.
        fields = WorkforceJobSerializer().fields
        self.assertGreater(len(fields), 0)

    def test_logistics_fields_are_exposed_to_the_driver_app(self):
        fields = WorkforceJobSerializer().fields
        missing = [f for f in DRIVER_REQUIRED_FIELDS if f not in fields]
        self.assertEqual(
            missing, [],
            "The driver app cannot work a logistics job without these: %s" % missing,
        )

    def test_pickup_location_is_still_exposed(self):
        # The drop point is an addition, not a replacement.
        fields = WorkforceJobSerializer().fields
        for f in ("address", "latitude", "longitude"):
            self.assertIn(f, fields)
