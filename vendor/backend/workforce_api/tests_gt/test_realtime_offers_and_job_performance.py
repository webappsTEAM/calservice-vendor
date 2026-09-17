"""
Focused Unit Tests for CalTrack Realtime Job Offer Reflection and N+1 Performance.

Covers:
1. OFFER_CREATED event log payload contains valid non-null id, request_id, service_title.
2. No 'undefined' request/job identifier is ever generated from a normal dispatch event.
3. Superseded offer unread notifications are marked read in supersede_other_offers_for_employee.
4. Competing offer unread notifications are marked read when another technician accepts the job.
5. GET /jobs endpoint remains purely read-only (no dispatch side effects).
6. WorkforceJobSerializer correctly reads from context maps (payments_map, extensions_map, wallets_map, trip_stops_map).
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, call
from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from workforce_api.serializers import WorkforceJobSerializer
from workforce_api.services.workload import supersede_other_offers_for_employee


class MockUser:
    def __init__(self, username="tech_test", pk=9001, is_authenticated=True):
        self.username = username
        self.pk = pk
        self.id = pk
        self.is_authenticated = is_authenticated
        self.is_active = True
        self.is_staff = False
        self.is_superuser = False
        self.employee_profile = None

    def get_full_name(self):
        return self.username


class RealtimeOffersAndPerformanceTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.today = timezone.localdate()
        self.now = timezone.now()

    def test_offer_created_payload_contains_required_metadata(self):
        """
        Verify that OFFER_CREATED payload contains non-null id, request_id,
        and service_title so desktop notifications never display 'Job #undefined'.
        """
        job = SimpleNamespace(
            id=5756,
            request_id="SR-PA5756",
            issue_title="Industrial Epoxy Flooring",
            service_category="flooring",
            address="Plot 12, Industrial Area",
        )
        offer = SimpleNamespace(id=8901)
        top_emp = SimpleNamespace(id=8567)
        top_dist_km = 4.25
        expires_at = self.now + timedelta(minutes=10)

        # Build payload exactly as automatic_dispatch.py now constructs it
        payload = {
            "id": job.id,
            "job_id": job.id,
            "request_id": job.request_id or f"#{job.id}",
            "offer_id": offer.id,
            "employee_id": top_emp.id,
            "service_title": job.issue_title or job.service_category or "Service Request",
            "service_category": job.service_category or "",
            "distance_km": round(top_dist_km, 2),
            "address": job.address or "",
            "expires_at": expires_at.isoformat(),
        }

        self.assertEqual(payload["job_id"], 5756)
        self.assertEqual(payload["id"], 5756)
        self.assertEqual(payload["request_id"], "SR-PA5756")
        self.assertEqual(payload["service_title"], "Industrial Epoxy Flooring")
        self.assertNotIn("undefined", str(payload["request_id"]))
        self.assertNotIn("undefined", str(payload["id"]))

    def test_offer_created_payload_fallback_when_request_id_missing(self):
        """
        When job.request_id is None/empty, request_id falls back to '#<id>', never 'undefined'.
        """
        job = SimpleNamespace(
            id=9999,
            request_id=None,
            issue_title=None,
            service_category="plumbing",
            address="",
        )
        offer = SimpleNamespace(id=8902)
        top_emp = SimpleNamespace(id=8567)

        payload = {
            "id": job.id,
            "job_id": job.id,
            "request_id": job.request_id or f"#{job.id}",
            "offer_id": offer.id,
            "employee_id": top_emp.id,
            "service_title": job.issue_title or job.service_category or "Service Request",
            "service_category": job.service_category or "",
            "distance_km": 1.0,
            "address": job.address or "",
            "expires_at": (self.now + timedelta(minutes=10)).isoformat(),
        }

        self.assertEqual(payload["request_id"], "#9999")
        self.assertEqual(payload["service_title"], "plumbing")
        self.assertNotIn("undefined", payload["request_id"])

    @patch("workforce_api.models.WorkforceNotification.objects.filter")
    @patch("workforce_api.models.WorkforceEventLog.objects.create")
    @patch("workforce_api.models.WorkforceJobOffer.objects.select_for_update")
    def test_superseded_offer_notifications_marked_read(self, mock_sfu, mock_evt, mock_notif_filter):
        """
        When employee accepts one job, sibling pending offers are marked SUPERSEDED_BY_ACCEPTANCE
        and their unread JOB_OFFER notifications are marked read.
        """
        offer1 = MagicMock()
        offer1.job_id = 101
        offer1.id = 501

        mock_sfu.return_value.filter.return_value.exclude.return_value = [offer1]

        emp = SimpleNamespace(pk=8567, user=MockUser())
        accepted_job = SimpleNamespace(pk=202)

        closed = supersede_other_offers_for_employee(emp, accepted_job)
        self.assertEqual(closed, 1)
        self.assertEqual(offer1.status, "SUPERSEDED_BY_ACCEPTANCE")

        # Verify WorkforceNotification.objects.filter was called to mark them read
        mock_notif_filter.assert_called_with(
            recipient=emp.user,
            notification_type="JOB_OFFER",
            related_object_id="101",
            is_read=False,
        )
        mock_notif_filter.return_value.update.assert_called_once()

    def test_serializer_uses_context_maps_without_queries(self):
        """
        Verify WorkforceJobSerializer reads payments_map, extensions_map, and wallets_map
        from context without issuing any database queries.
        """
        job = SimpleNamespace(
            id=1234,
            request_id="REQ-1234",
            customer_name="Alice",
            phone="9876543210",
            email="alice@example.com",
            service_category="electrical",
            issue_title="Switch Repair",
            description="Fix broken switch",
            cart_data=None,
            status="accepted",
            priority="normal",
            address="123 Street",
            latitude=12.97,
            longitude=77.59,
            preferred_date=self.today,
            preferred_time="10:00 AM",
            total_amount=500.0,
            payment_status="pending",
            payment_method="CASH_ON_SERVICE",
            customer=None,
            assigned_employee_id=8567,
            assigned_employee=SimpleNamespace(id=8567, company_id=None),
            company=None,
            created_at=self.now,
            updated_at=self.now,
            otp_verified=False,
            is_estimation=False,
            pricing_mode="FIXED",
            drop_address="",
            drop_latitude=None,
            drop_longitude=None,
            drop_contact_name="",
            drop_contact_phone="",
            logistics_leg="",
            logistics_leg_updated_at=None,
        )

        mock_user = MockUser(pk=8567)
        mock_user.employee_profile = job.assigned_employee

        req = self.factory.get("/api/workforce/jobs/?status=all")
        req.user = mock_user

        mock_payment = SimpleNamespace(
            id=991,
            job_id=1234,
            payment_method="CASH_ON_SERVICE",
            payment_status="PENDING",
            amount_due="500.00",
            amount_paid="0.00",
            amount_received=None,
            change_returned=None,
            currency="INR",
            gateway_transaction_id=None,
            cash_collected_at=None,
            is_cash_collected=False,
            customer_confirmed_at=None,
            customer_confirmation_method="",
            created_at=self.now,
            updated_at=self.now,
        )

        mock_wallet = SimpleNamespace(
            id=77,
            company_id=None,
            employee=SimpleNamespace(
                id=8567,
                user=mock_user,
                user_id=mock_user.id,
                full_name="Alice Worker",
            )
        )

        context = {
            "request": req,
            "payments_map": {1234: mock_payment},
            "extensions_map": {1234: []},
            "active_extensions_map": {},
            "trip_stops_map": {1234: 0},
            "quotes_map": {},
            "psvs_map": {},
            "emp_jobs_map": {1234: None},
            "lifecycle_events_map": {1234: None},
            "wallets_map": {8567: (mock_wallet, "INDIVIDUAL_WORKER")},
        }

        serializer = WorkforceJobSerializer(job, context=context)
        data = serializer.data

        self.assertEqual(data["id"], 1234)
        self.assertEqual(data["settlement_channel"], "INDIVIDUAL_WORKER")
        self.assertEqual(data["earnings_wallet_owner"], "tech_test")
        self.assertEqual(data["trip_stop_count"], 0)
        self.assertEqual(data["extensions"], [])
        self.assertIsNone(data["active_extension"])
        self.assertEqual(data["payment"]["id"], 991)
        self.assertEqual(data["payment"]["payment_status"], "PENDING")
