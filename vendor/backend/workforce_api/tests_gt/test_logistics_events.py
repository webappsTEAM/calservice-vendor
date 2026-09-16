"""
Local-only tests (NOT in the repo) for the vendor/driver side of the
Goods & Transport lifecycle: leg progression rules and the four events
this app emits to the Customer app.

Kept outside the repo for the same reason as the dispatch tests: vendor/
backend has no test-settings module of its own, and the models involved
are unmanaged mirrors with no tables in a test database -- so these cover
the pure rules and the emission contract with stubs, which is the surface
the change actually added.
"""
from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from workforce_api.services import logistics_events as le


class LegOrderingRuleTests(SimpleTestCase):
    def test_sequence_matches_the_customer_apps_ordering(self):
        # These two lists must agree; a drift here silently breaks
        # out-of-order protection on one side only.
        self.assertEqual(
            le.LEG_SEQUENCE,
            ["EN_ROUTE_PICKUP", "LOADING", "EN_ROUTE_DROP", "UNLOADING", "DELIVERED"],
        )

    def test_first_leg_is_always_allowed(self):
        ok, _ = le.can_advance_to("", "EN_ROUTE_PICKUP")
        self.assertTrue(ok)
        ok, _ = le.can_advance_to("", "DELIVERED")
        self.assertTrue(ok)

    def test_forward_moves_are_allowed(self):
        ok, _ = le.can_advance_to("EN_ROUTE_PICKUP", "LOADING")
        self.assertTrue(ok)

    def test_skipping_forward_is_allowed(self):
        # A driver who never signals LOADING must not be stuck.
        ok, _ = le.can_advance_to("EN_ROUTE_PICKUP", "UNLOADING")
        self.assertTrue(ok)

    def test_backwards_moves_are_rejected(self):
        ok, reason = le.can_advance_to("UNLOADING", "EN_ROUTE_PICKUP")
        self.assertFalse(ok)
        self.assertIn("backwards", reason)

    def test_repeat_is_allowed_by_the_rule_and_handled_as_a_no_op(self):
        ok, _ = le.can_advance_to("LOADING", "LOADING")
        self.assertTrue(ok)

    def test_invalid_leg_is_rejected(self):
        ok, reason = le.can_advance_to("", "EN_ROUTE_MOON")
        self.assertFalse(ok)
        self.assertIn("Invalid leg", reason)


class _StubJob:
    """Stands in for the unmanaged ServiceRequest mirror (no test table)."""
    def __init__(self, leg="", category="goods_transport_truck"):
        self.id = 1
        self.request_id = "GT0001"
        self.service_category = category
        self.logistics_leg = leg
        self.logistics_leg_updated_at = None
        self.logistics_leg_history = []
        self.saved_fields = []

    def save(self, update_fields=None):
        self.saved_fields.append(tuple(update_fields or ()))


class SetLogisticsLegTests(SimpleTestCase):
    def test_sets_the_leg_and_appends_history_once(self):
        job = _StubJob()
        with patch.object(le, "emit_leg_changed") as emit:
            changed, err = le.set_logistics_leg(job, "EN_ROUTE_PICKUP",
                                                actor=SimpleNamespace(id=7))
        self.assertTrue(changed)
        self.assertEqual(err, "")
        self.assertEqual(job.logistics_leg, "EN_ROUTE_PICKUP")
        self.assertEqual(len(job.logistics_leg_history), 1)
        self.assertEqual(job.logistics_leg_history[0]["by"], 7)
        emit.assert_called_once()

    def test_repeat_is_idempotent_and_emits_nothing(self):
        job = _StubJob(leg="LOADING")
        with patch.object(le, "emit_leg_changed") as emit:
            changed, err = le.set_logistics_leg(job, "LOADING")
        self.assertFalse(changed)
        self.assertEqual(err, "")
        self.assertEqual(job.logistics_leg_history, [])
        emit.assert_not_called()

    def test_backwards_move_is_refused_with_a_reason(self):
        job = _StubJob(leg="DELIVERED")
        with patch.object(le, "emit_leg_changed") as emit:
            changed, err = le.set_logistics_leg(job, "EN_ROUTE_PICKUP")
        self.assertFalse(changed)
        self.assertIn("backwards", err)
        self.assertEqual(job.logistics_leg, "DELIVERED")
        emit.assert_not_called()

    def test_invalid_leg_is_refused(self):
        job = _StubJob()
        changed, err = le.set_logistics_leg(job, "NOT_A_LEG")
        self.assertFalse(changed)
        self.assertIn("Invalid leg", err)

    def test_lowercase_input_is_normalised(self):
        job = _StubJob()
        with patch.object(le, "emit_leg_changed"):
            changed, _ = le.set_logistics_leg(job, "  en_route_pickup  ")
        self.assertTrue(changed)
        self.assertEqual(job.logistics_leg, "EN_ROUTE_PICKUP")

    def test_a_webhook_failure_never_undoes_the_leg(self):
        job = _StubJob()
        with patch.object(le, "emit_leg_changed", side_effect=RuntimeError("down")):
            with self.assertRaises(RuntimeError):
                le.set_logistics_leg(job, "LOADING")
        # The row was already saved before emission -- the shared table
        # stays correct even when the webhook cannot be delivered.
        self.assertEqual(job.logistics_leg, "LOADING")


class _StubStop:
    def __init__(self, arrived=None, completed=None):
        self.id = 11
        self.sequence = 1
        self.stop_type = "DROP"
        self.arrived_at = arrived
        self.completed_at = completed
        self.saved_fields = []

    def save(self, update_fields=None):
        self.saved_fields.append(tuple(update_fields or ()))


class StopProgressTests(SimpleTestCase):
    def test_arrival_is_stamped_and_emitted(self):
        job, stop = _StubJob(), _StubStop()
        with patch.object(le, "emit_stop_progress") as emit:
            changed = le.record_stop_progress(job, stop, completed=False)
        self.assertTrue(changed)
        self.assertIsNotNone(stop.arrived_at)
        self.assertIsNone(stop.completed_at)
        emit.assert_called_once_with(job, stop, False)

    def test_completion_without_a_prior_arrival_stamps_both(self):
        job, stop = _StubJob(), _StubStop()
        with patch.object(le, "emit_stop_progress"):
            le.record_stop_progress(job, stop, completed=True)
        self.assertIsNotNone(stop.arrived_at)
        self.assertIsNotNone(stop.completed_at)

    def test_existing_timestamps_are_never_rewritten(self):
        from django.utils import timezone
        earlier = timezone.now()
        job, stop = _StubJob(), _StubStop(arrived=earlier, completed=earlier)
        with patch.object(le, "emit_stop_progress"):
            changed = le.record_stop_progress(job, stop, completed=True)
        self.assertFalse(changed)
        self.assertEqual(stop.arrived_at, earlier)
        self.assertEqual(stop.completed_at, earlier)

    def test_emits_even_on_a_no_op_so_a_missed_delivery_can_be_retried(self):
        from django.utils import timezone
        stop = _StubStop(arrived=timezone.now(), completed=timezone.now())
        with patch.object(le, "emit_stop_progress") as emit:
            le.record_stop_progress(_StubJob(), stop, completed=True)
        emit.assert_called_once()


class CompletionProofEmissionTests(SimpleTestCase):
    def _capture(self, **kwargs):
        with patch("workforce_api.services.customer_webhook.notify_customer_app") as notify:
            le.emit_completion_proof(_StubJob(), **kwargs)
        self.assertTrue(notify.called)
        return notify.call_args

    def test_payload_carries_every_kind_of_evidence(self):
        args, kwargs = self._capture(
            notes="Left at reception",
            photo_url="https://vendor.example/p.jpg",
            signature_url="https://vendor.example/s.png",
            recipient_name="Priya R",
            recipient_phone="9876543210",
            otp_verified=True,
            technician_name="Ravi K",
            workforce_employee_id=4471,
            location={"latitude": "12.9", "longitude": "77.6"},
        )
        self.assertEqual(args[0], "job.completion_proof_submitted")
        self.assertEqual(kwargs["photo_url"], "https://vendor.example/p.jpg")
        self.assertEqual(kwargs["signature_url"], "https://vendor.example/s.png")
        self.assertEqual(kwargs["recipient_name"], "Priya R")
        self.assertTrue(kwargs["otp_verified"])
        self.assertEqual(kwargs["workforce_employee_id"], "4471")
        self.assertEqual(kwargs["location"], {"latitude": "12.9", "longitude": "77.6"})

    def test_absent_evidence_is_omitted_rather_than_sent_empty(self):
        _args, kwargs = self._capture(notes="just a note")
        for absent in ("photo_url", "signature_url", "recipient_name",
                       "recipient_phone", "stop_id", "location"):
            self.assertNotIn(absent, kwargs)
        self.assertEqual(kwargs["notes"], "just a note")

    def test_stop_reference_is_included_when_given(self):
        _args, kwargs = self._capture(stop=_StubStop())
        self.assertEqual(kwargs["stop_id"], 11)
        self.assertEqual(kwargs["stop_sequence"], 1)

    def test_emission_failure_never_raises_into_the_caller(self):
        with patch("workforce_api.services.customer_webhook.notify_customer_app",
                   side_effect=RuntimeError("customer app down")):
            le.emit_completion_proof(_StubJob(), notes="x")  # must not raise
