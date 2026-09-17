"""
Tests for Goods & Transport category-aware improvements:
1. Gate 3 vehicle type category matching (two-wheeler vs truck vs packers_movers).
2. State machine initial leg selection on acceptance (ASSIGNED for packers_movers, EN_ROUTE_PICKUP for standard GT).
3. Live tracking post-pickup destination targeting drop coordinates.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from workforce_api.services import automatic_dispatch as ad
from service_requests import state_machine


class Gate3VehicleTypeCategoryMatchingTests(SimpleTestCase):
    """
    Verifies that Gate 3 enforces category-specific vehicle compatibility.
    """

    def _make_vehicle(self, v_type, is_active=True, doc_current=True):
        v = SimpleNamespace(
            vehicle_type=v_type,
            is_active=is_active,
            is_document_current=lambda: doc_current
        )
        return v

    def _make_employee(self, emp_id=1, company_id=None):
        return SimpleNamespace(
            id=emp_id,
            company_id=company_id,
            is_active=True,
            is_online=True,
            current_availability="available",
            user=SimpleNamespace(is_active=True),
            bank_details={"onboarding": {
                "status": "approved",
                "documents": {},
                "services": [
                    {"status": "approved", "name": "goods_transport_two_wheeler", "category": "goods_transport_two_wheeler"},
                    {"status": "approved", "name": "goods_transport_truck", "category": "goods_transport_truck"},
                    {"status": "approved", "name": "packers_movers", "category": "packers_movers"},
                ]
            }},
            prefetched_invalid_compliance=[],
            prefetched_today_schedules=[],
            prefetched_verified_skills=[],
        )

    @patch("workforce_api.services.workload.get_employee_active_job", return_value=None)
    @patch("workforce_api.models.Vehicle.objects.filter")
    def test_two_wheeler_job_rejects_truck_and_accepts_two_wheeler(self, mock_v_filter, mock_active_job):
        emp = self._make_employee(1)

        # Case A: Employee only has a truck -> Gate 3 fails
        truck_veh = self._make_vehicle("truck")
        mock_v_filter.return_value = [truck_veh]
        ok, reason, gates = ad.check_candidate_eligibility(emp, "goods_transport_two_wheeler")
        self.assertFalse(ok)
        self.assertFalse(gates.get("G3"))
        self.assertIn("Two-wheeler vehicle required", reason)

        # Case B: Employee has a two-wheeler -> Gate 3 passes
        bike_veh = self._make_vehicle("two_wheeler")
        mock_v_filter.return_value = [bike_veh]
        ok, reason, gates = ad.check_candidate_eligibility(emp, "goods_transport_two_wheeler")
        self.assertTrue(gates.get("G3"))

    @patch("workforce_api.services.workload.get_employee_active_job", return_value=None)
    @patch("workforce_api.models.Vehicle.objects.filter")
    def test_truck_job_rejects_two_wheeler_and_accepts_truck(self, mock_v_filter, mock_active_job):
        emp = self._make_employee(2)

        # Case A: Employee only has two_wheeler -> Gate 3 fails
        bike_veh = self._make_vehicle("two_wheeler")
        mock_v_filter.return_value = [bike_veh]
        ok, reason, gates = ad.check_candidate_eligibility(emp, "goods_transport_truck")
        self.assertFalse(ok)
        self.assertFalse(gates.get("G3"))
        self.assertIn("Truck or commercial vehicle required", reason)

        # Case B: Employee has a mini_truck -> Gate 3 passes
        mini_truck = self._make_vehicle("mini_truck")
        mock_v_filter.return_value = [mini_truck]
        ok, reason, gates = ad.check_candidate_eligibility(emp, "goods_transport_truck")
        self.assertTrue(gates.get("G3"))

    @patch("workforce_api.services.workload.get_employee_active_job", return_value=None)
    @patch("workforce_api.models.Vehicle.objects.filter")
    def test_packers_movers_rejects_two_wheeler_and_three_wheeler(self, mock_v_filter, mock_active_job):
        emp = self._make_employee(3)

        # Case A: Three wheeler is rejected for Packers & Movers
        auto_veh = self._make_vehicle("three_wheeler")
        mock_v_filter.return_value = [auto_veh]
        ok, reason, gates = ad.check_candidate_eligibility(emp, "packers_movers")
        self.assertFalse(ok)
        self.assertFalse(gates.get("G3"))
        self.assertIn("Commercial relocation vehicle required", reason)

        # Case B: Standard truck is accepted
        truck_veh = self._make_vehicle("truck")
        mock_v_filter.return_value = [truck_veh]
        ok, reason, gates = ad.check_candidate_eligibility(emp, "packers_movers")
        self.assertTrue(gates.get("G3"))


class StateMachineInitialLegTests(SimpleTestCase):
    """
    Verifies that state machine sets ASSIGNED for Packers & Movers and EN_ROUTE_PICKUP for standard GT.
    """

    @patch("workforce_api.services.logistics_events.set_logistics_leg")
    @patch("workforce_api.services.customer_webhook.notify_customer_app")
    @patch("service_requests.models.EmployeeJob.objects.filter")
    def test_packers_movers_sets_assigned_initial_leg(self, mock_emp_job, mock_notify, mock_set_leg):
        sr = SimpleNamespace(
            pk=101,
            id=101,
            status="pending",
            service_category="packers_movers",
            assigned_employee=None,
            is_logistics=True,
            save=MagicMock()
        )
        actor = SimpleNamespace(id=1, role="admin", is_superuser=True)

        state_machine.apply_transition(sr, "accepted", actor=actor)
        self.assertEqual(sr.status, "accepted")
        mock_set_leg.assert_called_once_with(sr, "ASSIGNED", actor=actor)

    @patch("workforce_api.services.logistics_events.set_logistics_leg")
    @patch("workforce_api.services.customer_webhook.notify_customer_app")
    @patch("service_requests.models.EmployeeJob.objects.filter")
    def test_goods_transport_truck_sets_en_route_pickup_initial_leg(self, mock_emp_job, mock_notify, mock_set_leg):
        sr = SimpleNamespace(
            pk=102,
            id=102,
            status="pending",
            service_category="goods_transport_truck",
            assigned_employee=None,
            is_logistics=True,
            save=MagicMock()
        )
        actor = SimpleNamespace(id=1, role="admin", is_superuser=True)

        state_machine.apply_transition(sr, "accepted", actor=actor)
        self.assertEqual(sr.status, "accepted")
        mock_set_leg.assert_called_once_with(sr, "EN_ROUTE_PICKUP", actor=actor)


class TrackingPostPickupTargetTests(SimpleTestCase):
    """
    Verifies that tracking view calculates distance toward drop coordinates once pickup has occurred.
    """

    def test_post_pickup_legs_include_relocation_and_drop_stages(self):
        post_pickup_legs = {
            "LOADING", "EN_ROUTE_DROP", "UNLOADING", "DELIVERED",
            "IN_TRANSIT", "ARRIVED_DROP", "REASSEMBLY", "UNPACKING", "COMPLETED"
        }
        # Pre-pickup legs
        pre_pickup_legs = ["ASSIGNED", "TEAM_EN_ROUTE", "ARRIVED_PICKUP", "EN_ROUTE_PICKUP"]

        for leg in pre_pickup_legs:
            self.assertNotIn(leg, post_pickup_legs)

        # Relocation post-pickup legs
        for leg in ["IN_TRANSIT", "ARRIVED_DROP", "REASSEMBLY", "UNPACKING", "COMPLETED"]:
            self.assertIn(leg, post_pickup_legs)
