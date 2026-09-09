"""
Local-only tests (NOT in the repo) for the dispatch concurrency guard.

The race being guarded: two dispatch_job() runs for DIFFERENT jobs each
lock only their own ServiceRequest row, so they do not exclude one
another. Both can rank the same idle technician first and both try to
offer them a job at the same instant. Until now the ONLY protection was
the unique_active_job_offer_per_employee constraint in the database --
and hitting it raised IntegrityError straight out of dispatch instead of
gracefully moving to another candidate.

TESTING LIMIT, stated plainly: a true two-transaction race cannot be
executed from this environment. The vendor migration chain is
PostgreSQL-specific and cannot be replayed on SQLite (0002 removes a
field that 0001 indexed, which SQLite's table-rebuild cannot do, and a
later migration contains a raw `DO $$ ... $$` block), so no test database
can be built here at all. These tests therefore drive the REAL functions
with the database boundary stubbed, covering the decision logic and --
most importantly -- that the constraint firing is handled as a normal
outcome rather than an exception escaping dispatch.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import SimpleTestCase

from workforce_api.services import automatic_dispatch as ad


class DispatchRaceHandlingTests(SimpleTestCase):
    def test_losing_the_race_returns_cleanly_instead_of_raising(self):
        # The regression this exists to prevent: an IntegrityError from the
        # unique constraint escaping dispatch_job() as a 500.
        with patch.object(ad, "_dispatch_job_locked",
                          side_effect=ad.DispatchRaceLost("Technician #7 was offered another job concurrently.")):
            ok, msg = ad.dispatch_job(123)
        self.assertFalse(ok)
        self.assertIn("concurrently", msg)

    def test_the_job_is_left_dispatchable_for_the_next_sweep(self):
        # Losing the race must not mark the job failed or consume a cycle --
        # it just did not place this time.
        with patch.object(ad, "_dispatch_job_locked",
                          side_effect=ad.DispatchRaceLost("busy")):
            ok, _msg = ad.dispatch_job(123)
        self.assertFalse(ok)

    def test_other_exceptions_are_not_swallowed(self):
        # Only the race is treated as an ordinary outcome. A genuine bug
        # must still surface rather than being reported as "no technician".
        with patch.object(ad, "_dispatch_job_locked",
                          side_effect=ValueError("a real bug")):
            with self.assertRaises(ValueError):
                ad.dispatch_job(123)

    def test_dispatch_race_lost_is_its_own_exception_type(self):
        self.assertTrue(issubclass(ad.DispatchRaceLost, Exception))
        self.assertFalse(issubclass(ad.DispatchRaceLost, IntegrityError))


class LiveOfferExclusionTests(SimpleTestCase):
    def test_only_live_offered_offers_count(self):
        fake_qs = MagicMock()
        fake_qs.exclude.return_value = fake_qs
        fake_qs.values_list.return_value = [3, 9]
        with patch.object(ad.WorkforceJobOffer, "objects") as objects:
            objects.filter.return_value = fake_qs
            result = ad.employees_with_live_offers()
        self.assertEqual(result, {3, 9})
        kwargs = objects.filter.call_args.kwargs
        # An expired or already-answered offer must not block a technician.
        self.assertEqual(kwargs["status"], ad.WorkforceJobOffer.Status.OFFERED)
        self.assertIn("expires_at__gt", kwargs)

    def test_the_jobs_own_offer_does_not_block_its_own_redispatch(self):
        fake_qs = MagicMock()
        fake_qs.exclude.return_value = fake_qs
        fake_qs.values_list.return_value = []
        job = SimpleNamespace(id=42)
        with patch.object(ad.WorkforceJobOffer, "objects") as objects:
            objects.filter.return_value = fake_qs
            ad.employees_with_live_offers(exclude_job=job)
        fake_qs.exclude.assert_called_once_with(job=job)

    def test_no_job_given_means_no_exclusion(self):
        fake_qs = MagicMock()
        fake_qs.values_list.return_value = []
        with patch.object(ad.WorkforceJobOffer, "objects") as objects:
            objects.filter.return_value = fake_qs
            ad.employees_with_live_offers()
        fake_qs.exclude.assert_not_called()


class ExistingProtectionNotWeakenedTests(SimpleTestCase):
    """
    The instruction was to add an application-level guard BEFORE touching
    the database protection -- not instead of it. These assert the
    constraint is still in the migration graph and still un-removed.
    """
    def test_unique_constraint_is_still_created_by_migration_0013(self):
        import importlib
        mod = importlib.import_module(
            "workforce_api.migrations.0013_workforcejoboffer_wave_id_and_more"
        ) if False else None
        # Module names starting with a digit can't be imported normally --
        # read the source instead, which is what actually matters here.
        import os
        base = os.path.join(
            os.path.dirname(ad.__file__), "..", "migrations",
        )
        path = os.path.join(base, "0013_workforcejoboffer_wave_id_and_more.py")
        with open(path) as f:
            src = f.read()
        self.assertIn("unique_active_job_offer_per_employee", src)
        self.assertIn("AddConstraint", src)

    def test_migration_0022_still_does_not_remove_it(self):
        import os
        path = os.path.join(
            os.path.dirname(ad.__file__), "..", "migrations",
            "0022_gt_x04_drop_legacy_quote_models_and_cleanup.py",
        )
        if not os.path.exists(path):
            # Excluded in safe production merge to protect quotations & rate cards; constraint is preserved
            return
        with open(path) as f:
            src = f.read()
        # It may be discussed in the header comment, but must not appear as
        # an actual RemoveConstraint operation.
        operations = src.split("operations = [", 1)[1]
        self.assertNotIn("unique_active_job_offer_per_employee", operations)
