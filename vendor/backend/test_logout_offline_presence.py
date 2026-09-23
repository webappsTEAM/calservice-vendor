"""
test_logout_offline_presence.py

Tests for Logout Auto-Offline Presence:
1. Verify technician starts ONLINE in database.
2. Authenticated POST /api/auth/logout/ automatically sets is_online=False in database.
3. Availability is reconciled to 'offline'.
4. PresenceLog record is created for offline status.
5. last_logout_at timestamp is persisted.
6. Subsequent queries confirm employee remains OFFLINE until explicit login + Go Online.
"""

import os
import uuid
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate

User = get_user_model()

from employees.models import Employee, PresenceLog
from companies.models import Company
from accounts.views import LogoutView
from workforce_api.services.workload import reconcile_employee_availability


class LogoutOfflinePresenceTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.uid = uuid.uuid4().hex[:8]
        self.company = Company.objects.create(
            company_name=f"Presence Corp {self.uid}",
            is_active=True,
        )
        self.user = User.objects.create_user(
            username=f"tech_logout_{self.uid}",
            email=f"tech_logout_{self.uid}@example.com",
            password="Password123!",
            role="employee",
        )
        self.emp = Employee.objects.create(
            user=self.user,
            company=self.company,
            employee_id=f"EMP-LO-{self.uid[:4].upper()}",
            phone=f"98{self.uid[:8]}",
            is_online=True,
            current_availability="available",
        )

    def test_logout_takes_an_online_technician_offline(self):
        """
        Signing out while ONLINE succeeds and takes the technician offline.

        This previously asserted the opposite -- that logout must be REFUSED
        with CANNOT_LOGOUT_WHILE_ONLINE until the technician toggled offline
        first -- which contradicts this module's own stated purpose ("Logout
        Auto-Offline Presence ... automatically sets is_online=False"), and
        would not have achieved the goal anyway: someone who closes the app
        or loses their phone never reaches the toggle, and refusing the
        sign-out leaves exactly the stale ONLINE row the feature exists to
        prevent. Acting on the logout is what makes presence converge.
        """
        self.emp.refresh_from_db()
        self.assertTrue(self.emp.is_online)

        req = self.factory.post("/api/auth/logout/")
        force_authenticate(req, user=self.user)
        resp = LogoutView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data.get("is_online"))

        self.emp.refresh_from_db()
        self.assertFalse(self.emp.is_online, "Signing out must clear the ONLINE flag")
        self.assertEqual(self.emp.current_availability, "offline")
        self.assertIsNotNone(self.emp.last_logout_at)

    def test_logout_succeeds_when_offline(self):
        """When technician is OFFLINE, POST /api/auth/logout/ succeeds (200 OK) and clears session"""
        self.emp.is_online = False
        self.emp.current_availability = "offline"
        self.emp.save(update_fields=["is_online", "current_availability"])

        req = self.factory.post("/api/auth/logout/")
        force_authenticate(req, user=self.user)
        resp = LogoutView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data.get("is_online"))

        # Verify database persistence
        self.emp.refresh_from_db()
        self.assertFalse(self.emp.is_online)
        self.assertIsNotNone(self.emp.last_logout_at, "last_logout_at must be populated on logout")

        # Verify PresenceLog record
        # PresenceLog records a presence STATE (is_online / availability) with
        # its created_at; there is no logout_at column on it.
        log = PresenceLog.objects.filter(employee=self.emp, is_online=False).order_by("-id").first()
        self.assertIsNotNone(log, "PresenceLog record must be written on logout")

    def test_unauthenticated_logout_is_graceful(self):
        """Anonymous logout does not crash and returns 200"""
        req = self.factory.post("/api/auth/logout/")
        resp = LogoutView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
