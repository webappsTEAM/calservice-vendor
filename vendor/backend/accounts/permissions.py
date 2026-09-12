"""
workforce-app/backend/accounts/permissions.py
Role-based permission helpers.
"""
from rest_framework.permissions import BasePermission

ADMIN_ROLES = frozenset({"admin", "manager", "service_provider_admin", "service_provider", "vendor"})


def is_platform_admin(user) -> bool:
    """
    Platform Superadmin: Has cross-company operational authority.
    """
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, "is_superuser", False))


def is_vendor_admin(user) -> bool:
    """
    Vendor Admin / Manager: Has operational authority scoped strictly to their own Company.
    """
    if not user or not user.is_authenticated:
        return False
    role = str(getattr(user, "role", "")).lower()
    return role in ADMIN_ROLES or getattr(user, "is_staff", False) or getattr(user, "is_superuser", False)


def is_admin_role(user) -> bool:
    """
    Backwards-compatible helper: Returns True for either Platform Admin or Vendor Admin.
    """
    if not user or not user.is_authenticated:
        return False
    role = str(getattr(user, "role", "")).lower()
    return role in ADMIN_ROLES or getattr(user, "is_superuser", False) or getattr(user, "is_staff", False)


class IsWorkforceAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin_role(getattr(request, "user", None))


class IsWorkforceEmployee(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        role = str(getattr(user, "role", "")).lower()
        return role == "employee" or is_admin_role(user)


# ── Backward-Compatibility Aliases for Legacy Test Suites & Service Provider Modules ──
is_superadmin = is_platform_admin
is_service_provider_admin = is_vendor_admin
is_workforce_admin = is_vendor_admin


def is_workforce_employee(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    role = str(getattr(user, "role", "")).lower()
    return role == "employee" or is_admin_role(user)


