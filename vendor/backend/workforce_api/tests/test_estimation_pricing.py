"""
The commercial rules: consultation fee, high-value gate, slab pricing,
minimum area, warranty tiers, customer-supplied material, advance schedule.

Boundary cases are tested exactly (999/1000/1001 litres, 14.9/15.1 km) because
every one of these is a number someone will be billed by.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from companies.models import Company
from employees.models import Employee
from service_requests.models import ServiceRequest
from workforce_api.models import (
    PreServiceVerification,
    WorkforceInvoice,
    WorkforceQuote,
    WorkforceQuoteItem,
    WorkforceRateCard,
    WorkforceServicePricingPolicy,
)
from workforce_api.services import (
    invoice_service,
    pricing_policy,
    quotation_service,
    rate_card_pricing,
)

User = get_user_model()


class SeedDataTests(TestCase):
    """The seed migration must actually have run and produced usable rows."""

    def test_policies_are_seeded(self):
        self.assertTrue(WorkforceServicePricingPolicy.objects.filter(service_category="painting").exists())
        self.assertTrue(WorkforceServicePricingPolicy.objects.filter(service_category="mason").exists())

        ac = WorkforceServicePricingPolicy.objects.get(service_category="AC Services")
        self.assertEqual(ac.consultation_fee_mode, "FLAT")
        self.assertEqual(ac.consultation_fee_amount, Decimal("199.00"))

    def test_all_six_masonry_services_have_rate_cards(self):
        names = set(
            WorkforceRateCard.objects.filter(service_category="mason")
            .values_list("item_name", flat=True)
        )
        self.assertEqual(names, {
            "Bathroom Tile Fixing",
            "Minor Masonry & Small Construction",
            "Brick & Block Work",
            "Plastering & Wall Repair",
            "Wall & Partition Construction",
            "Wall Breaking & Demolition",
        })

    def test_the_four_legacy_masonry_services_are_quote_only(self):
        for name in ("Brick & Block Work", "Plastering & Wall Repair",
                     "Wall & Partition Construction", "Wall Breaking & Demolition"):
            card = WorkforceRateCard.objects.get(service_category="mason", item_name=name)
            self.assertEqual(card.pricing_model, "QUOTE_ONLY", name)
            self.assertEqual(card.default_rate, Decimal("0.00"), name)

    def test_painting_rate_cards_match_the_plan(self):
        expected = {
            "3 mm Tar Sheet / Gas Heating Waterproofing": (Decimal("100.00"), "10_YEAR"),
            "Terrace Waterproofing - 4 Coat": (Decimal("50.00"), "5_YEAR"),
            "Terrace Waterproofing - 2 Coat": (Decimal("20.00"), "NONE"),
            "Roof Repair / Patch Work": (Decimal("25.00"), "NONE"),
            "PU Coating / Dampness Treatment": (Decimal("35.00"), "NONE"),
            "Premium Interior Emulsion": (Decimal("15.00"), "NONE"),
            "Ceiling Painting": (Decimal("12.00"), "NONE"),
            "Weatherproof Exterior Emulsion": (Decimal("18.00"), "NONE"),
            "PU Coat Gates, Doors & Grills": (Decimal("85.00"), "NONE"),
            "Royal Texture Play / Stencil Design": (Decimal("120.00"), "NONE"),
        }
        for name, (rate, warranty) in expected.items():
            card = WorkforceRateCard.objects.get(service_category="painting", item_name=name)
            self.assertEqual(card.default_rate, rate, name)
            self.assertEqual(card.warranty_tier, warranty, name)


class ConsultationFeeTests(TestCase):
    def test_ac_is_a_flat_199(self):
        amount, why = pricing_policy.consultation_fee_for("AC Services")
        self.assertEqual(amount, Decimal("199.00"))
        self.assertIn("Flat", why)

    def test_painting_is_free_inside_the_radius(self):
        # ~2 km north of the Hosur hub
        amount, why = pricing_policy.consultation_fee_for("painting", 12.7600, 77.8253)
        self.assertEqual(amount, Decimal("0.00"))
        self.assertIn("within", why)

    def test_painting_is_charged_beyond_the_radius(self):
        # ~28 km north of the hub
        amount, why = pricing_policy.consultation_fee_for("painting", 13.0000, 77.8253)
        self.assertEqual(amount, Decimal("300.00"))
        self.assertIn("beyond", why)

    def test_the_boundary_is_the_radius_itself(self):
        """14.9 km free, 15.1 km charged. One degree of latitude is ~111.19 km."""
        inside = 12.7409 + (14.9 / 111.19)
        outside = 12.7409 + (15.1 / 111.19)
        self.assertEqual(pricing_policy.consultation_fee_for("painting", inside, 77.8253)[0], Decimal("0.00"))
        self.assertEqual(pricing_policy.consultation_fee_for("painting", outside, 77.8253)[0], Decimal("300.00"))

    def test_missing_coordinates_never_charge_the_customer(self):
        amount, why = pricing_policy.consultation_fee_for("painting", None, None)
        self.assertEqual(amount, Decimal("0.00"))
        self.assertIn("waived", why)

    def test_an_unconfigured_category_is_free_not_an_error(self):
        amount, _ = pricing_policy.consultation_fee_for("underwater basket weaving")
        self.assertEqual(amount, Decimal("0.00"))

    def test_admin_can_change_the_fee(self):
        policy = WorkforceServicePricingPolicy.objects.get(service_category="AC Services")
        policy.consultation_fee_amount = Decimal("249.00")
        policy.save()
        self.assertEqual(pricing_policy.consultation_fee_for("AC Services")[0], Decimal("249.00"))


class RateCardPricingTests(TestCase):
    def _card(self, name, category="painting"):
        return WorkforceRateCard.objects.get(service_category=category, item_name=name)

    def test_per_unit(self):
        total, unit, _ = rate_card_pricing.price_line(
            self._card("Premium Interior Emulsion"), Decimal("450")
        )
        self.assertEqual(unit, Decimal("15.00"))
        self.assertEqual(total, Decimal("6750.00"))

    def test_epoxy_tiers(self):
        card = self._card("Industrial Epoxy Flooring")
        for tier, rate in (("1mm", "60.00"), ("2mm", "90.00"), ("3mm", "110.00")):
            total, unit, _ = rate_card_pricing.price_line(card, Decimal("100"), tier=tier)
            self.assertEqual(unit, Decimal(rate), tier)
            self.assertEqual(total, Decimal(rate) * 100)

    def test_epoxy_without_a_tier_is_refused(self):
        with self.assertRaises(ValidationError):
            rate_card_pricing.price_line(self._card("Industrial Epoxy Flooring"), Decimal("100"))

    def test_water_tank_capacity_bands_at_the_boundaries(self):
        card = self._card("Water Tank Waterproofing")
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("999"))[0], Decimal("1700.00"))
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("1000"))[0], Decimal("1700.00"))
        # 1001 L falls into the per-litre band
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("1001"))[0], Decimal("1501.50"))
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("5000"))[0], Decimal("7500.00"))
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("10000"))[0], Decimal("17000.00"))

    def test_bathroom_tile_size_bands(self):
        card = self._card("Bathroom Tile Fixing", category="mason")
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("49"))[0], Decimal("10000.00"))
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("80"))[0], Decimal("10000.00"))
        self.assertEqual(rate_card_pricing.price_line(card, Decimal("81"))[0], Decimal("20000.00"))

    def test_minor_masonry_minimum_area(self):
        card = self._card("Minor Masonry & Small Construction", category="mason")
        with self.assertRaises(ValidationError) as ctx:
            rate_card_pricing.price_line(card, Decimal("499"))
        self.assertIn("minimum", str(ctx.exception).lower())

        total, unit, _ = rate_card_pricing.price_line(card, Decimal("500"))
        self.assertEqual(unit, Decimal("120.00"))
        self.assertEqual(total, Decimal("60000.00"))

    def test_quote_only_services_refuse_a_rate(self):
        card = self._card("Brick & Block Work", category="mason")
        with self.assertRaises(ValidationError) as ctx:
            rate_card_pricing.price_line(card, Decimal("100"))
        self.assertIn("priced on site", str(ctx.exception))

    def test_zero_quantity_is_refused(self):
        with self.assertRaises(ValidationError):
            rate_card_pricing.price_line(self._card("Ceiling Painting"), Decimal("0"))


class QuoteRulesTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(company_name="Vendor")
        self.customer = User.objects.create_user(username="c", email="c@x.test", password="x")
        self.tech_user = User.objects.create_user(username="t", email="t@x.test", password="x", role="employee")
        self.admin = User.objects.create_user(username="a", email="a@x.test", password="x", role="admin")
        self.admin.is_staff = self.admin.is_superuser = True
        self.admin.save()
        self.tech = Employee.objects.create(
            user=self.tech_user, company=self.company, employee_id="E1",
            # IsApprovedTechnician gates on this, not on is_active.
            bank_details={"onboarding": {"status": "approved"}},
        )

        self.job = ServiceRequest.objects.create(
            request_kind=ServiceRequest.RequestKind.ESTIMATION,
            company=self.company, customer=self.customer, customer_name="C",
            phone="9", service_category="painting", issue_title="Interior Painting",
            address="A", preferred_date=timezone.now().date(), preferred_time="10:00 AM",
            assigned_employee=self.tech, status="in_progress",
        )
        PreServiceVerification.objects.create(
            job=self.job, employee=self.tech, geofence_passed=True, otp_verified=True,
            presence_photo="p.jpg", work_area_photo="w.jpg", is_complete=True,
        )

    def _quote(self, unit_price, quantity=1, advance_percent=None):
        q = WorkforceQuote.objects.create(
            job=self.job, technician=self.tech, company=self.company,
            customer=self.customer, service_category="painting",
            service_name="Interior Painting", advance_percent=advance_percent,
        )
        WorkforceQuoteItem.objects.create(
            quote=q, section="LABOUR", name="work", quantity=Decimal(str(quantity)),
            unit_price=Decimal(str(unit_price)), tax_rate=Decimal("18.00"),
        )
        quotation_service.recalculate_quote_totals(q)
        q.refresh_from_db()
        return q

    def test_quote_number_is_dated(self):
        q = self._quote(100)
        today = timezone.localtime().strftime("%Y%m%d")
        self.assertRegex(q.quote_number, rf"^PQ-{today}-\d{{4}}$")

    def test_quote_numbers_increment_within_the_day(self):
        a = self._quote(100).quote_number
        b = self._quote(100).quote_number
        self.assertNotEqual(a, b)
        self.assertEqual(int(b.rsplit("-", 1)[1]), int(a.rsplit("-", 1)[1]) + 1)

    def test_high_value_painting_quote_is_held_before_sending(self):
        """Painting threshold is Rs.30,000. 28,000 + 18% GST = 33,040."""
        quote = self._quote(28000)
        self.assertEqual(quote.total_amount, Decimal("33040.00"))
        with self.assertRaises(ValidationError) as ctx:
            quotation_service.send_quote_to_customer(quote.id)
        self.assertIn("review threshold", str(ctx.exception))
        quote.refresh_from_db()
        self.assertEqual(quote.status, WorkforceQuote.Status.PENDING_REVIEW)
        self.assertIsNone(quote.decision_token)

    def test_a_quote_under_the_threshold_sends_straight_through(self):
        quote = self._quote(1000)
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        self.assertEqual(quote.status, WorkforceQuote.Status.SENT_TO_CUSTOMER)

    def test_admin_release_sends_the_held_quote(self):
        quote = self._quote(28000)
        with self.assertRaises(ValidationError):
            quotation_service.send_quote_to_customer(quote.id)

        quote = quotation_service.release_high_value_quote(quote.id, self.admin, approve=True)
        self.assertEqual(quote.status, WorkforceQuote.Status.SENT_TO_CUSTOMER)
        self.assertIsNotNone(quote.decision_token)
        self.assertIsNotNone(quote.admin_cleared_at)

    def test_admin_rejection_cancels_the_held_quote(self):
        quote = self._quote(28000)
        with self.assertRaises(ValidationError):
            quotation_service.send_quote_to_customer(quote.id)
        quote = quotation_service.release_high_value_quote(
            quote.id, self.admin, approve=False, notes="measurements look wrong"
        )
        self.assertEqual(quote.status, WorkforceQuote.Status.CANCELLED)

    def test_customer_supplied_material_is_rejected(self):
        quote = self._quote(1000)
        client = APIClient()
        client.force_authenticate(self.tech_user)
        resp = client.post(
            f"/api/workforce/quotes/{quote.id}/items/bulk/",
            {"items": [{"name": "Paint", "quantity": 1, "unit_price": 100,
                        "is_customer_supplied": True}]},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.assertEqual(resp.data["code"], "CUSTOMER_SUPPLIED_NOT_ALLOWED")

    def test_warranty_tier_is_validated_and_stored(self):
        quote = self._quote(1000)
        client = APIClient()
        client.force_authenticate(self.tech_user)

        bad = client.post(
            f"/api/workforce/quotes/{quote.id}/items/bulk/",
            {"items": [{"name": "X", "quantity": 1, "unit_price": 1, "warranty_tier": "3_YEAR"}]},
            format="json",
        )
        self.assertEqual(bad.status_code, 400, bad.content)

        ok = client.post(
            f"/api/workforce/quotes/{quote.id}/items/bulk/",
            {"items": [{"name": "Tar sheet", "quantity": 1, "unit_price": 100,
                        "warranty_tier": "10_YEAR"}]},
            format="json",
        )
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.data["items"][0]["warranty_tier"], "10_YEAR")
        self.assertTrue(ok.data["items"][0]["warranty_applicable"])


class AdvanceScheduleTests(QuoteRulesTests):
    def _approved_invoice(self, unit_price, advance_percent=None):
        quote = self._quote(unit_price, advance_percent=advance_percent)
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        quote, _ = quotation_service.record_customer_decision(
            quote.id, "ACCEPT", token=quote.decision_token
        )
        _, work_job, invoice = quotation_service.admin_review_quote(quote.id, self.admin, approve=True)
        return work_job, invoice

    def test_painting_bills_in_full(self):
        _, invoice = self._approved_invoice(1000)
        self.assertEqual(invoice.advance_percent, Decimal("100.00"))
        self.assertEqual(invoice.advance_amount, invoice.total_amount)
        self.assertEqual(invoice.balance_amount, Decimal("0.00"))

    def test_waterproofing_quote_takes_half_up_front(self):
        _, invoice = self._approved_invoice(1000, advance_percent=Decimal("50.00"))
        self.assertEqual(invoice.advance_amount, Decimal("590.00"))
        self.assertEqual(invoice.balance_amount, Decimal("590.00"))
        self.assertEqual(invoice.advance_amount + invoice.balance_amount, invoice.total_amount)

    def test_execution_is_blocked_until_the_advance_is_paid(self):
        work_job, invoice = self._approved_invoice(1000, advance_percent=Decimal("50.00"))

        reason = invoice_service.blocking_reason_for_execution(work_job)
        self.assertIsNotNone(reason)
        self.assertIn("Advance", reason)

        invoice_service.record_invoice_payment(invoice, Decimal("590.00"), reference="adv")
        self.assertIsNone(invoice_service.blocking_reason_for_execution(work_job))

    def test_advance_is_marked_paid_across_instalments(self):
        _, invoice = self._approved_invoice(1000, advance_percent=Decimal("50.00"))
        invoice, _, _ = invoice_service.record_invoice_payment(invoice, Decimal("300.00"), reference="a")
        self.assertIsNone(invoice.advance_paid_at)
        invoice, _, _ = invoice_service.record_invoice_payment(invoice, Decimal("290.00"), reference="b")
        self.assertIsNotNone(invoice.advance_paid_at)

    def test_invoice_number_is_dated(self):
        _, invoice = self._approved_invoice(1000)
        today = timezone.localtime().strftime("%Y%m%d")
        self.assertRegex(invoice.invoice_number, rf"^INV-{today}-\d{{4}}$")


class AdminSettingsApiTests(QuoteRulesTests):
    """The endpoints the SEVO admin screens call."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def test_pricing_policies_are_listed(self):
        resp = self.client.get("/api/workforce/settings/pricing-policies/")
        self.assertEqual(resp.status_code, 200, resp.content)
        categories = {p["service_category"] for p in resp.data}
        self.assertIn("painting", categories)
        self.assertIn("AC Services", categories)

    def test_admin_can_change_the_consultation_fee_through_the_api(self):
        policy = WorkforceServicePricingPolicy.objects.get(service_category="AC Services")
        resp = self.client.patch(
            f"/api/workforce/settings/pricing-policies/{policy.id}/",
            {"consultation_fee_amount": "249.00"}, format="json",
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(pricing_policy.consultation_fee_for("AC Services")[0], Decimal("249.00"))

    def test_invalid_policy_values_are_refused(self):
        policy = WorkforceServicePricingPolicy.objects.get(service_category="painting")
        for payload in ({"advance_percent": "150"},
                        {"consultation_fee_mode": "SOMETIMES"},
                        {"beyond_radius_amount": "-10"}):
            resp = self.client.patch(
                f"/api/workforce/settings/pricing-policies/{policy.id}/", payload, format="json"
            )
            self.assertEqual(resp.status_code, 400, (payload, resp.content))

    def test_a_vendor_admin_cannot_edit_pricing(self):
        vendor_admin = User.objects.create_user(username="va", email="va@x.test", password="x", role="admin")
        Employee.objects.create(user=vendor_admin, company=self.company, employee_id="EA")
        client = APIClient()
        client.force_authenticate(vendor_admin)
        self.assertEqual(client.get("/api/workforce/settings/pricing-policies/").status_code, 403)

    def test_rate_cards_are_served_to_the_builder(self):
        resp = self.client.get("/api/workforce/rate-cards/?category=mason")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(len(resp.data), 6)

    def test_rate_card_pricing_endpoint_matches_the_service(self):
        card = WorkforceRateCard.objects.get(
            service_category="mason", item_name="Minor Masonry & Small Construction"
        )
        ok = self.client.post("/api/workforce/rate-cards/price/",
                              {"rate_card_id": card.id, "quantity": 500}, format="json")
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertEqual(ok.data["line_total"], 60000.0)

        refused = self.client.post("/api/workforce/rate-cards/price/",
                                   {"rate_card_id": card.id, "quantity": 499}, format="json")
        self.assertEqual(refused.status_code, 400, refused.content)
        self.assertEqual(refused.data["code"], "PRICING_REFUSED")

    def test_pre_send_review_queue_and_release(self):
        quote = self._quote(28000)
        with self.assertRaises(ValidationError):
            quotation_service.send_quote_to_customer(quote.id)

        queue = self.client.get("/api/workforce/quotes/pending-review/")
        self.assertEqual(queue.status_code, 200, queue.content)
        self.assertEqual([q["id"] for q in queue.data], [quote.id])

        released = self.client.post(
            f"/api/workforce/quotes/{quote.id}/pre-send-review/",
            {"action": "APPROVE"}, format="json",
        )
        self.assertEqual(released.status_code, 200, released.content)
        self.assertEqual(released.data["quote"]["status"], "SENT_TO_CUSTOMER")

        self.assertEqual(self.client.get("/api/workforce/quotes/pending-review/").data, [])

    def test_admin_quote_metrics(self):
        resp = self.client.get("/api/workforce/admin/quotes/metrics/")
        self.assertEqual(resp.status_code, 200, resp.content)
        for key in ("by_status", "awaiting_admin_approval", "awaiting_pre_send_review",
                    "total_quotes", "invoices_outstanding_amount"):
            self.assertIn(key, resp.data)


class InvoicePdfTests(AdvanceScheduleTests):
    def test_pdf_renders_for_the_signed_in_owner(self):
        _, invoice = self._approved_invoice(1000)
        client = APIClient()
        client.force_authenticate(self.admin)
        resp = client.get(f"/api/workforce/invoices/{invoice.id}/pdf/")
        self.assertEqual(resp.status_code, 200, resp.content[:200])
        self.assertEqual(resp["Content-Type"], "application/pdf")
        body = b"".join(resp.streaming_content) if resp.streaming else resp.content
        self.assertTrue(body.startswith(b"%PDF"), body[:20])
        self.assertGreater(len(body), 1000)

    def test_customer_can_fetch_it_with_the_quotation_token(self):
        quote = self._quote(1000)
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        token = quote.decision_token
        quotation_service.record_customer_decision(quote.id, "ACCEPT", token=token)
        _, _, invoice = quotation_service.admin_review_quote(quote.id, self.admin, approve=True)

        anon = APIClient()
        ok = anon.get(f"/api/workforce/invoices/{invoice.id}/pdf/?token={token}")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok["Content-Type"], "application/pdf")

        # A token belonging to a different quote must not open this invoice.
        other = self._quote(500)
        quotation_service.send_quote_to_customer(other.id)
        other.refresh_from_db()
        wrong = anon.get(f"/api/workforce/invoices/{invoice.id}/pdf/?token={other.decision_token}")
        self.assertEqual(wrong.status_code, 404)

        self.assertEqual(anon.get(f"/api/workforce/invoices/{invoice.id}/pdf/").status_code, 404)


class QuoteApiFieldTests(QuoteRulesTests):
    """Fields the Quotation Builder posts and the API must actually honour."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(self.tech_user)

    def test_advance_percent_is_accepted_on_create_and_patch(self):
        resp = self.client.post(
            "/api/workforce/quotes/",
            {"job_id": self.job.id, "title": "T", "service_category": "painting",
             "advance_percent": "50"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        quote = WorkforceQuote.objects.get(pk=resp.data["id"])
        self.assertEqual(quote.advance_percent, Decimal("50.00"))

        patched = self.client.patch(f"/api/workforce/quotes/{quote.id}/",
                                    {"advance_percent": "100"}, format="json")
        self.assertEqual(patched.status_code, 200, patched.content)
        quote.refresh_from_db()
        self.assertEqual(quote.advance_percent, Decimal("100.00"))

    def test_absent_advance_percent_leaves_the_policy_in_charge(self):
        """Null and 0 mean different things: null is 'no opinion'."""
        resp = self.client.post(
            "/api/workforce/quotes/",
            {"job_id": self.job.id, "title": "T", "service_category": "painting"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertIsNone(WorkforceQuote.objects.get(pk=resp.data["id"]).advance_percent)

    def test_out_of_range_advance_percent_is_refused(self):
        resp = self.client.post(
            "/api/workforce/quotes/",
            {"job_id": self.job.id, "title": "T", "service_category": "painting",
             "advance_percent": "150"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400, resp.content)

    def test_inspection_fee_adjusted_is_no_longer_dropped(self):
        quote = self._quote(1000)
        resp = self.client.patch(f"/api/workforce/quotes/{quote.id}/",
                                 {"inspection_fee_adjusted": "199.00"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        quote.refresh_from_db()
        self.assertEqual(quote.inspection_fee_adjusted, Decimal("199.00"))
        # and it must actually reduce what the customer pays
        self.assertEqual(quote.net_payable, quote.total_amount - Decimal("199.00"))

    def test_the_quote_advance_overrides_the_category_policy(self):
        """A waterproofing line in a painting quote still needs 50% up front."""
        quote = self._quote(1000, advance_percent=Decimal("50.00"))
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        quotation_service.record_customer_decision(quote.id, "ACCEPT", token=quote.decision_token)
        _, _, invoice = quotation_service.admin_review_quote(quote.id, self.admin, approve=True)

        self.assertEqual(pricing_policy.advance_percent("painting"), Decimal("100.00"))
        self.assertEqual(invoice.advance_percent, Decimal("50.00"))
        self.assertEqual(invoice.advance_amount, Decimal("590.00"))


class EstimationProjectionTests(QuoteRulesTests):
    """
    A quote raised in the workforce builder must appear in the tables the
    customer application reads, and must not appear there twice.
    """

    def setUp(self):
        super().setUp()
        from service_requests.models import Estimation, EstimationQuotation
        self.Estimation = Estimation
        self.EstimationQuotation = EstimationQuotation

    def _sent_quote(self, amount=1000):
        quote = self._quote(amount)
        quotation_service.send_quote_to_customer(quote.id)
        quote.refresh_from_db()
        return quote

    def test_sending_a_quote_creates_the_customer_projection(self):
        quote = self._sent_quote()

        projected = self.EstimationQuotation.objects.get(
            quote_ref=f"{quote.quote_number}-V1"
        )
        self.assertEqual(projected.status, "SENT")
        self.assertEqual(projected.total_amount, quote.net_payable)
        self.assertEqual(projected.subtotal, quote.subtotal_amount)
        self.assertEqual(projected.tax_amount, quote.tax_amount)
        self.assertEqual(projected.items.count(), 1)
        self.assertEqual(projected.version, 1)

    def test_a_painting_job_is_not_given_invented_ac_specifications(self):
        self._sent_quote()
        est = self.Estimation.objects.get(service_request=self.job)
        self.assertEqual(est.ac_type, "OTHER")
        self.assertEqual(est.ac_capacity, "OTHER")
        self.assertEqual(est.ac_brand, "")
        self.assertIn("not applicable", est.customer_notes)
        self.assertEqual(est.status, "QUOTATION_SENT")

    def test_the_projection_follows_the_customer_decision(self):
        quote = self._sent_quote()
        quotation_service.record_customer_decision(
            quote.id, "ACCEPT", token=quote.decision_token
        )
        projected = self.EstimationQuotation.objects.get(quote_ref=f"{quote.quote_number}-V1")
        self.assertEqual(projected.status, "APPROVED")
        self.assertIsNotNone(projected.customer_approved_at)
        self.assertEqual(
            self.Estimation.objects.get(service_request=self.job).status, "CUSTOMER_APPROVED"
        )

    def test_a_decline_is_projected_with_its_reason(self):
        quote = self._sent_quote()
        quotation_service.record_customer_decision(
            quote.id, "DECLINE", reason="too expensive", token=quote.decision_token
        )
        projected = self.EstimationQuotation.objects.get(quote_ref=f"{quote.quote_number}-V1")
        self.assertEqual(projected.status, "REJECTED")
        self.assertEqual(projected.rejection_note, "too expensive")

    def test_a_revision_is_projected_as_its_own_reference(self):
        quote = self._sent_quote()
        _, revised = quotation_service.record_customer_decision(
            quote.id, "REQUEST_CHANGES", notes="cheaper paint", token=quote.decision_token
        )
        refs = set(
            self.EstimationQuotation.objects
            .filter(quote_ref__startswith=quote.quote_number)
            .values_list("quote_ref", flat=True)
        )
        self.assertEqual(refs, {f"{quote.quote_number}-V1", f"{quote.quote_number}-V2"})
        v1 = self.EstimationQuotation.objects.get(quote_ref=f"{quote.quote_number}-V1")
        v2 = self.EstimationQuotation.objects.get(quote_ref=f"{quote.quote_number}-V2")
        self.assertEqual(v1.status, "SUPERSEDED")
        self.assertEqual(v2.status, "DRAFT")
        self.assertEqual(v2.version, 2)
        self.assertEqual(revised.quote_version, 2)

    def test_projecting_twice_does_not_duplicate(self):
        quote = self._sent_quote()
        quotation_service.send_quote_to_customer(quote.id)
        self.assertEqual(
            self.EstimationQuotation.objects.filter(
                quote_ref=f"{quote.quote_number}-V1"
            ).count(),
            1,
        )

    def test_a_quote_from_the_ac_path_is_not_projected_back(self):
        """
        vendor_views._sync_workforce_quote already created that WorkforceQuote
        from an EstimationQuotation. Projecting it back would give the customer
        the same quotation twice, under QTE-...-V1-V1.
        """
        from service_requests.models import Estimation, EstimationQuotation

        est = Estimation.objects.create(
            service_request=self.job, ac_type="SPLIT", ac_brand="General",
            ac_capacity="1.5_TON", ac_quantity=1, status="INSPECTION_COMPLETED",
        )
        EstimationQuotation.objects.create(
            estimation=est, version=1, quote_ref="QTE-AC1-V1", status="SENT",
            subtotal=Decimal("100"), total_amount=Decimal("118"),
        )
        quote = WorkforceQuote.objects.create(
            job=self.job, technician=self.tech, company=self.company,
            customer=self.customer, quote_number="QTE-AC1-V1", quote_version=1,
            service_category="painting",
        )
        quotation_service.send_quote_to_customer(quote.id)

        self.assertFalse(
            EstimationQuotation.objects.filter(quote_ref="QTE-AC1-V1-V1").exists(),
            "the AC-originated quote was projected back and duplicated",
        )
        self.assertEqual(EstimationQuotation.objects.filter(quote_ref="QTE-AC1-V1").count(), 1)

    def test_a_projection_failure_never_breaks_the_quote(self):
        """The projection is a convenience copy; the quote is the commitment."""
        from unittest.mock import patch

        quote = self._quote(1000)
        with patch(
            "workforce_api.services.estimation_projection.project_quote",
            side_effect=RuntimeError("customer tables unavailable"),
        ):
            sent = quotation_service.send_quote_to_customer(quote.id)
        self.assertEqual(sent.status, WorkforceQuote.Status.SENT_TO_CUSTOMER)
        self.assertIsNotNone(sent.decision_token)
