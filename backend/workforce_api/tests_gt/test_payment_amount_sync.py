"""
The last link in the fare chain: a reconciled fare has to reach the amount
the driver is actually told to collect.

JobPayment rows are created with get_or_create, and `defaults` apply only on
creation -- so amount_due froze at whatever job.total_amount was the first
time any of three endpoints ran (driver opens the payment screen, customer
views payment, cash collection). Nothing updated it afterwards.

Harmless while the fare never moved after booking. Not harmless once fare
reconciliation started running at DELIVERED: a trip that ran longer, visited
an extra stop, or picked up approved extra work has its total_amount raised,
and the collection screen would still show the pre-trip number.

Uses stand-ins rather than model instances: JobPayment's table is real but
ServiceRequest here is an unmanaged mirror, and the rule under test is
arithmetic plus a status guard, not persistence.
"""
from decimal import Decimal

from django.test import SimpleTestCase

from workforce_api.models import JobPayment
from workforce_api.views import sync_payment_amount_due


class _Payment:
    def __init__(self, status, amount_due):
        self.payment_status = status
        self.amount_due = amount_due
        self.saved_fields = None

    def save(self, update_fields=None):
        self.saved_fields = update_fields


class _Job:
    def __init__(self, total, jid=1):
        self.total_amount = total
        self.id = jid


PENDING = JobPayment.PaymentStatus.PENDING
PAID = JobPayment.PaymentStatus.PAID


class PaymentAmountSyncTests(SimpleTestCase):
    def test_a_raised_fare_reaches_an_unpaid_payment(self):
        pmt, job = _Payment(PENDING, Decimal("530.00")), _Job(Decimal("584.00"))
        self.assertTrue(sync_payment_amount_due(pmt, job))
        self.assertEqual(pmt.amount_due, Decimal("584.00"))
        self.assertIn("amount_due", pmt.saved_fields)

    def test_a_lowered_fare_reaches_an_unpaid_payment(self):
        # The overcharge direction matters just as much.
        pmt, job = _Payment(PENDING, Decimal("900.00")), _Job(Decimal("700.00"))
        self.assertTrue(sync_payment_amount_due(pmt, job))
        self.assertEqual(pmt.amount_due, Decimal("700.00"))

    def test_an_unchanged_fare_writes_nothing(self):
        pmt, job = _Payment(PENDING, Decimal("530.00")), _Job(Decimal("530.00"))
        self.assertFalse(sync_payment_amount_due(pmt, job))
        self.assertIsNone(pmt.saved_fields)

    def test_a_paid_payment_is_never_rewritten(self):
        # Money has already moved. A later fare change is a refund or a
        # follow-up charge, not an edit to history.
        pmt, job = _Payment(PAID, Decimal("530.00")), _Job(Decimal("584.00"))
        self.assertFalse(sync_payment_amount_due(pmt, job))
        self.assertEqual(pmt.amount_due, Decimal("530.00"))
        self.assertIsNone(pmt.saved_fields)

    def test_a_cash_pending_payment_is_never_rewritten(self):
        # CASH_PENDING is set the moment the driver reports taking the cash
        # (an OTP is issued for the customer to confirm it), so the money has
        # already changed hands. The amount they took is a fact.
        pmt = _Payment(JobPayment.PaymentStatus.CASH_PENDING, Decimal("530.00"))
        self.assertFalse(sync_payment_amount_due(pmt, _Job(Decimal("584.00"))))
        self.assertEqual(pmt.amount_due, Decimal("530.00"))

    def test_an_authorized_payment_is_never_rewritten(self):
        # The gateway holds an authorization for a specific amount; moving
        # amount_due underneath it would desync the two.
        pmt = _Payment(JobPayment.PaymentStatus.AUTHORIZED, Decimal("530.00"))
        self.assertFalse(sync_payment_amount_due(pmt, _Job(Decimal("584.00"))))
        self.assertEqual(pmt.amount_due, Decimal("530.00"))

    def test_a_missing_total_becomes_zero_not_a_crash(self):
        # A zero total is a real data problem that surfaces loudly in
        # settlement; it must not be papered over, and must not except here.
        pmt, job = _Payment(PENDING, Decimal("530.00")), _Job(None)
        self.assertTrue(sync_payment_amount_due(pmt, job))
        self.assertEqual(pmt.amount_due, Decimal("0.00"))

    def test_missing_arguments_are_survivable(self):
        self.assertFalse(sync_payment_amount_due(None, _Job(Decimal("1.00"))))
        self.assertFalse(sync_payment_amount_due(_Payment(PENDING, Decimal("1.00")), None))

    def test_every_payment_creation_site_syncs(self):
        # The helper is worthless if a call site forgets it.
        import re
        src = open("workforce_api/views.py", encoding="utf-8", errors="replace").read()
        creations = len(re.findall(r"JobPayment\.objects(?:\.select_for_update\(\))?\.get_or_create\(", src))
        # Excludes the definition line, which matches the same text.
        syncs = len(re.findall(r"(?<!def )sync_payment_amount_due\(pmt, job\)", src))
        self.assertEqual(
            syncs, creations,
            f"{creations} JobPayment creation sites but {syncs} sync calls",
        )
