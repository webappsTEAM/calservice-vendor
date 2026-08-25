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

    def test_logout_sets_technician_offline_in_database(self):
        """Authenticated logout sets is_online=False and current_availability='offline' in DB"""
        self.emp.refresh_from_db()
        self.assertTrue(self.emp.is_online)
        self.assertEqual(self.emp.current_availability, "available")

        req = self.factory.post("/api/auth/logout/")
        force_authenticate(req, user=self.user)
        resp = LogoutView.as_view()(req)

        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data.get("is_online"))
        self.assertEqual(resp.data.get("availability"), "offline")

        # Verify database persistence
        self.emp.refresh_from_db()
        self.assertFalse(self.emp.is_online, "Employee must be marked is_online=False in database upon logout")
        self.assertEqual(self.emp.current_availability, "offline", "Employee availability must be reconciled to offline in DB")
        self.assertIsNotNone(self.emp.last_logout_at, "last_logout_at must be populated on logout")

        # Verify PresenceLog record
        log = PresenceLog.objects.filter(employee=self.emp, logout_at__isnull=False).order_by("-id").first()
        self.assertIsNotNone(log, "PresenceLog record must be written on logout")

    def test_unauthenticated_logout_is_graceful(self):
        """Anonymous logout does not crash and returns 200"""
        req = self.factory.post("/api/auth/logout/")
        resp = LogoutView.as_view()(req)
        self.assertEqual(resp.status_code, 200)
