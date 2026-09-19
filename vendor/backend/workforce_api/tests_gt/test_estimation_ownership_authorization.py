"""
GT audit Update 13b: cross-tenant ownership on the vendor estimation/survey
flow (service_requests/vendor_views.py).

_get_target_estimation() resolves a raw ServiceRequest/Estimation pk with no
company scoping at all, and every detail/action view in that file used to
call it and then act on the result behind nothing but
permission_classes=[IsAuthenticated] (or, for the invoice endpoint,
permission_classes=[AllowAny] and NO check at all). That let any
authenticated actor from any company read another company's
estimation/customer/quotation detail, overwrite ServiceRequest.vendor_id via
the confirm endpoint to hijack a lead already claimed by someone else, and
let anyone on the internet fetch any invoice by guessing a numeric id.

Source-level, for the same reason as the driver-trip-endpoint tests
(test_gt_endpoint_authorization.py): ServiceRequest here is an unmanaged
mirror of a table another app owns, so there is no local schema to build
APITestCase fixtures against. _may_access_estimation/_actor_vendor_key are
plain functions taking simple objects, so they're also unit-tested directly
against stubs, the same pattern test_gt_endpoint_authorization.py uses for
is_employee_authorized_for_job.

IMPORTANT, same caveat as every other test file added during this audit:
these were written by reading the exact source of the fixed file and
reasoning through each branch. They have NOT been executed -- device_bash
has been unavailable for this entire session. Do not describe these as
"passing" until `python manage.py test workforce_api.tests_gt` (or
whatever this app's test runner path actually is) has been run.
"""
import re

from django.test import SimpleTestCase

SOURCE = "service_requests/vendor_views.py"

# Every view in vendor_views.py that resolves a target via
# _get_target_estimation() and then reads/mutates it. VendorEstimationInvoiceView
# is deliberately excluded -- it is AllowAny by design (customer-app use case)
# and gets its own bespoke tracking_token-or-ownership check instead of the
# plain _may_access_estimation gate every other view uses.
GATED_VIEWS = [
    "VendorEstimationDetailView",
    "VendorEstimationConfirmView",
    "VendorEstimationAssignTechnicianView",
    "VendorEstimationStartJourneyView",
    "VendorEstimationArrivedView",
    "VendorEstimationVerifyOtpView",
    "VendorEstimationFindingsView",
    "VendorEstimationPhotosView",
    "VendorEstimationInspectionCompleteView",
    "VendorEstimationQuotationView",
    "VendorEstimationQuotationSendView",
    "VendorEstimationQuotationReviseView",
    "VendorEstimationFeeCollectView",
    "VendorEstimationFeeWaiveView",
    "VendorEstimationCustomerDecideView",
]


def _source():
    with open(SOURCE, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def _class_body(name, src=None):
    src = src if src is not None else _source()
    lines = src.splitlines()
    start = next(i for i, l in enumerate(lines) if re.match(rf"class {name}\(", l))
    end = next(
        (i for i, l in enumerate(lines) if i > start and re.match(r"class \w+\(", l)),
        len(lines),
    )
    return "\n".join(lines[start:end])


class EstimationViewOwnershipGateTests(SimpleTestCase):
    """Every non-invoice estimation view must call the new ownership gate
    after resolving its target and before doing anything else with it."""

    def test_every_gated_view_checks_ownership_after_resolving_the_target(self):
        src = _source()
        for name in GATED_VIEWS:
            body = _class_body(name, src)
            self.assertIn(
                "_get_target_estimation(pk)", body,
                f"{name} should resolve its target via _get_target_estimation",
            )
            self.assertIn(
                "_may_access_estimation(sr, request)", body,
                f"{name} is missing the GT audit Update 13b ownership gate",
            )
            self.assertIn(
                "_estimation_ownership_denied(pk)", body,
                f"{name} should deny with the identical-404 helper, not a bespoke response",
            )

    def test_the_ownership_check_runs_right_after_the_not_found_guard(self):
        # Cheap proxy for ordering: the ownership gate must sit immediately
        # after the "sr not found" guard (docstrings/decorators above it
        # push the absolute line number around, so we check adjacency, not
        # an absolute line count).
        src = _source()
        for name in GATED_VIEWS:
            body = _class_body(name, src)
            lines = body.splitlines()
            not_found_idx = next(i for i, l in enumerate(lines) if '"code": "NOT_FOUND"' in l)
            deny_idx = next(i for i, l in enumerate(lines) if "_estimation_ownership_denied(pk)" in l)
            self.assertLess(
                not_found_idx, deny_idx,
                f"{name}: the not-found guard should come before the ownership gate",
            )
            # The gate's own "if" line is the very next non-blank line after
            # the not-found guard's return statement.
            gate_if_idx = deny_idx - 1
            self.assertIn(
                "_may_access_estimation(sr, request)", lines[gate_if_idx],
                f"{name}: ownership gate should run immediately after the not-found guard, "
                "before any read or mutation of sr/est",
            )
            self.assertEqual(
                not_found_idx + 1, gate_if_idx,
                f"{name}: something sits between the not-found guard and the ownership gate",
            )

    def test_invoice_view_does_not_use_the_plain_gate_but_has_its_own(self):
        # AllowAny by design -- it must not use _may_access_estimation() as
        # its ONLY gate (an anonymous caller has no meaningful "actor"), but
        # it must still check something: the tracking_token capability.
        body = _class_body("VendorEstimationInvoiceView")
        self.assertIn("tracking_token", body)
        self.assertIn("_may_access_estimation", body)  # used for the authenticated-owner fallback
        self.assertIn("request.user.is_authenticated", body)

    def test_invoice_view_is_still_reachable_without_login(self):
        # This must stay AllowAny -- the fix is a capability check, not a
        # login requirement, per the documented customer-app use case.
        body = _class_body("VendorEstimationInvoiceView")
        self.assertIn("permission_classes = [permissions.AllowAny]", body)


class MayAccessEstimationUnitTests(SimpleTestCase):
    """Direct unit tests of the pure ownership-decision function against
    stub objects, mirroring test_gt_endpoint_authorization.py's approach
    for is_employee_authorized_for_job."""

    def _fn(self):
        from service_requests.vendor_views import _may_access_estimation, _actor_vendor_key
        return _may_access_estimation, _actor_vendor_key

    class _SR:
        def __init__(self, vendor_id=""):
            self.vendor_id = vendor_id

    class _User:
        def __init__(self, company_id="", user_id=1, is_superuser=False, is_authenticated=True):
            self.company_id = company_id
            self.id = user_id
            self.is_superuser = is_superuser
            self.is_authenticated = is_authenticated

    class _Request:
        def __init__(self, user):
            self.user = user

    def test_unclaimed_lead_is_visible_to_any_authenticated_actor(self):
        may_access, _ = self._fn()
        sr = self._SR(vendor_id="")
        actor_a = self._Request(self._User(company_id="7"))
        actor_b = self._Request(self._User(company_id="9"))
        self.assertTrue(may_access(sr, actor_a))
        self.assertTrue(may_access(sr, actor_b))

    def test_claimed_lead_is_visible_only_to_the_claiming_company(self):
        may_access, _ = self._fn()
        sr = self._SR(vendor_id="7")
        same_company = self._Request(self._User(company_id="7"))
        other_company = self._Request(self._User(company_id="9"))
        self.assertTrue(may_access(sr, same_company))
        self.assertFalse(may_access(sr, other_company))

    def test_superuser_bypasses_ownership_entirely(self):
        may_access, _ = self._fn()
        sr = self._SR(vendor_id="7")
        su = self._Request(self._User(company_id="9", is_superuser=True))
        self.assertTrue(may_access(sr, su))

    def test_actor_vendor_key_falls_back_to_user_id_when_no_company(self):
        _, actor_key = self._fn()
        req = self._Request(self._User(company_id="", user_id=42))
        self.assertEqual(actor_key(req), "42")

    def test_actor_vendor_key_prefers_company_id_when_present(self):
        _, actor_key = self._fn()
        req = self._Request(self._User(company_id="7", user_id=42))
        self.assertEqual(actor_key(req), "7")

    def test_a_solo_actor_cannot_read_another_solo_actors_claimed_lead(self):
        # Two different individual (non-company) actors who each fall back
        # to their own user id -- claiming as user 42 must not be readable
        # by user 43, exactly like two different companies.
        may_access, _ = self._fn()
        sr = self._SR(vendor_id="42")
        claimer = self._Request(self._User(company_id="", user_id=42))
        stranger = self._Request(self._User(company_id="", user_id=43))
        self.assertTrue(may_access(sr, claimer))
        self.assertFalse(may_access(sr, stranger))
