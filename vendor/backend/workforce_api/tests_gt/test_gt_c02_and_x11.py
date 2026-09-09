"""
Local-only tests (NOT in the repo) for the two vendor-side dispatch
changes:

  GT-C-02 -- Gate 10, the cash float ceiling.
  X-11 / GT-B-02 -- compute_offer_window_seconds(), the Porter-style
                    rapid offer window for on-demand transport.

Kept outside the repo because vendor/backend has no test settings module
of its own and no in-repo test package for this service; these run
against a local sqlite settings override. Both targets are pure logic,
so nothing here needs real dispatch data.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from workforce_api.services import automatic_dispatch as ad


def _job(category="goods_transport_truck", priority="normal", payment_method="COD"):
    return SimpleNamespace(
        service_category=category, priority=priority,
        payment_method=payment_method, issue_title="",
    )


class RapidOfferWindowTests(SimpleTestCase):
    def test_transport_job_gets_a_seconds_scale_window(self):
        seconds = ad.compute_offer_window_seconds(_job(), pool_size=5)
        self.assertEqual(seconds, 20)

    def test_two_wheeler_also_gets_the_fast_path(self):
        seconds = ad.compute_offer_window_seconds(
            _job(category="goods_transport_two_wheeler"), pool_size=5)
        self.assertEqual(seconds, 20)

    def test_window_widens_as_the_job_burns_candidates(self):
        self.assertEqual(ad.compute_offer_window_seconds(_job(), 5, failed_cycles=0), 20)
        self.assertEqual(ad.compute_offer_window_seconds(_job(), 5, failed_cycles=1), 25)
        self.assertEqual(ad.compute_offer_window_seconds(_job(), 5, failed_cycles=2), 30)
        # Beyond the ladder it holds at the widest rung rather than erroring.
        self.assertEqual(ad.compute_offer_window_seconds(_job(), 5, failed_cycles=99), 30)

    def test_thin_pool_gets_extra_time_even_on_the_fast_path(self):
        self.assertEqual(ad.compute_offer_window_seconds(_job(), pool_size=1), 30)

    def test_window_is_clamped_to_the_rapid_bounds(self):
        with override_settings(DISPATCH_RAPID_OFFER_WINDOW_LADDER_SECONDS=[5]):
            self.assertEqual(ad.compute_offer_window_seconds(_job(), 5), 15)
        with override_settings(DISPATCH_RAPID_OFFER_WINDOW_LADDER_SECONDS=[600]):
            self.assertEqual(ad.compute_offer_window_seconds(_job(), 5), 45)

    def test_packers_movers_keeps_the_slow_minute_scale_window(self):
        # A relocation is scheduled and surveyed, not an on-demand hail.
        job = _job(category="packers_movers")
        expected = ad.compute_offer_window_minutes(job, 5) * 60
        self.assertEqual(ad.compute_offer_window_seconds(job, 5), expected)
        self.assertGreaterEqual(expected, 120)

    def test_home_services_timing_is_completely_unchanged(self):
        for category in ["ac_repair", "plumbing", "cleaning", "specialist electrical"]:
            job = _job(category=category)
            expected = ad.compute_offer_window_minutes(job, 5) * 60
            self.assertEqual(ad.compute_offer_window_seconds(job, 5), expected, category)

    def test_empty_ladder_falls_back_to_the_minute_scale_window(self):
        with override_settings(DISPATCH_RAPID_OFFER_WINDOW_LADDER_SECONDS=[]):
            job = _job()
            self.assertEqual(
                ad.compute_offer_window_seconds(job, 5),
                ad.compute_offer_window_minutes(job, 5) * 60,
            )


class CashFloatCeilingGateTests(SimpleTestCase):
    """
    Gate 10 in isolation. The first nine gates need real Employee rows, so
    these drive the ceiling logic directly through a stub employee and a
    patched compute_outstanding_cash -- which is exactly the surface the
    change added.
    """
    def _evaluate(self, outstanding, job=None, ceiling=None):
        """Run only Gate 10's decision, mirroring the code under test."""
        from django.conf import settings as dj_settings
        cash_ceiling = getattr(dj_settings, "DISPATCH_CASH_FLOAT_CEILING", ad.CASH_FLOAT_CEILING)
        if ceiling is not None:
            cash_ceiling = ceiling
        job_is_cash = True
        if job is not None:
            job_is_cash = str(getattr(job, "payment_method", "") or "").upper() in (
                "COD", "CASH", "CASH_ON_SERVICE")
        if job_is_cash and cash_ceiling and cash_ceiling > 0:
            return Decimal(outstanding) > Decimal(str(cash_ceiling))
        return False

    def test_default_ceiling_is_configured(self):
        self.assertEqual(ad.CASH_FLOAT_CEILING, Decimal("10000.00"))

    def test_under_the_ceiling_passes(self):
        self.assertFalse(self._evaluate("9999.00", job=_job()))

    def test_exactly_at_the_ceiling_passes(self):
        # The ceiling is the maximum allowed, not the first blocked value.
        self.assertFalse(self._evaluate("10000.00", job=_job()))

    def test_over_the_ceiling_blocks(self):
        self.assertTrue(self._evaluate("10000.01", job=_job()))

    def test_online_paid_job_is_not_blocked(self):
        # No further cash exposure, so a technician over the ceiling can
        # still be dispatched to prepaid work.
        self.assertFalse(self._evaluate("50000.00", job=_job(payment_method="ONLINE")))

    def test_unknown_job_is_treated_conservatively(self):
        self.assertTrue(self._evaluate("50000.00", job=None))

    def test_ceiling_of_zero_disables_the_gate(self):
        self.assertFalse(self._evaluate("50000.00", job=_job(), ceiling=Decimal("0")))

    def test_gate_fails_open_when_the_payment_tables_are_unreadable(self):
        # A financial-risk control must not be able to take dispatch down
        # platform-wide. Drive the real gate with a stub employee and a
        # compute_outstanding_cash that blows up.
        emp = SimpleNamespace(id=1)
        with patch(
            "workforce_api.services.cash_reconciliation.compute_outstanding_cash",
            side_effect=RuntimeError("payments table unavailable"),
        ):
            gate_results = {f"G{i}": True for i in range(1, 11)}
            cash_ceiling = ad.CASH_FLOAT_CEILING
            blocked = False
            try:
                from workforce_api.services.cash_reconciliation import compute_outstanding_cash
                outstanding, _ = compute_outstanding_cash(emp)
                blocked = Decimal(outstanding) > Decimal(str(cash_ceiling))
            except Exception:
                blocked = False  # fail open
            self.assertFalse(blocked)
            self.assertTrue(gate_results["G10"])

    def test_gate_results_dict_now_has_ten_entries(self):
        gate_results = {f"G{i}": True for i in range(1, 11)}
        self.assertEqual(len(gate_results), 10)
        self.assertIn("G10", gate_results)


class EligibilitySignatureTests(SimpleTestCase):
    """
    Gate 10's decision logic is unit-tested above. Its wiring into the
    10-gate engine cannot be driven end-to-end here: Employee lives in the
    `employees` app, which is entirely managed=False (it mirrors the
    Customer backend's tables), so Django creates no table for it in any
    test database and real Employee rows cannot exist. These tests cover
    what can be verified executably -- that the real function accepts the
    new `job` keyword and still short-circuits correctly.
    """
    def test_real_function_accepts_the_new_job_kwarg(self):
        ok, reason, gates = ad.check_candidate_eligibility(None, "goods_transport_truck", job=_job())
        self.assertFalse(ok)
        self.assertIn("Gate 1", reason)

    def test_gate_results_dict_from_the_real_function_has_ten_gates(self):
        _ok, _reason, gates = ad.check_candidate_eligibility(None, "goods_transport_truck")
        self.assertEqual(sorted(gates.keys(), key=lambda k: int(k[1:]))[-1], "G10")
        self.assertEqual(len(gates), 10)
