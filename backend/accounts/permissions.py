"""
workforce-app/backend/accounts/permissions.py
Role-based permission helpers and DRF permission classes.
"""
from rest_framework.permissions import BasePermission

ADMIN_ROLES = frozenset({"superadmin", "super_admin", "service_provider_admin", "admin", "manager"})


def is_superadmin(user) -> bool:
    """
    SUPERADMIN: Platform-wide administrator with global authority.
    Detection rule: user.is_superuser == True OR role in ["superadmin", "super_admin"].
    """
    if not user or not user.is_authenticated:
        return False
    return bool(getattr(user, "is_superuser", False) or str(getattr(user, "role", "")).lower() in ["superadmin", "super_admin"])


def is_service_provider_admin(user) -> bool:
    """
    SERVICE_PROVIDER_ADMIN: Authority scoped strictly to user.company.
    Must belong to exactly one Service Provider (Company).
    """
    if not user or not user.is_authenticated:
        return False
    if is_superadmin(user):
        return False
    role = str(getattr(user, "role", "")).lower()
    return role in ["service_provider_admin", "admin", "manager"] and bool(getattr(user, "company_id", None))


def is_workforce_admin(user) -> bool:
    """
    True if user is either SUPERADMIN or SERVICE_PROVIDER_ADMIN (or staff).
    """
    if not user or not user.is_authenticated:
        return False
    if is_superadmin(user):
        return True
    if is_service_provider_admin(user):
        return True
    role = str(getattr(user, "role", "")).lower()
    return role in ["admin", "manager"] or getattr(user, "is_staff", False)


def is_workforce_employee(user) -> bool:
    """
    True if user is an employee (independent or provider) or workforce admin.
    """
    if not user or not user.is_authenticated:
        return False
    role = str(getattr(user, "role", "")).lower()
    return role in ["employee", "technician"] or is_workforce_admin(user)


# ── Backwards-compatible aliases ──────────────────────────────────────────────
def is_platform_admin(user) -> bool:
    """Alias for is_superadmin."""
    return is_superadmin(user)


def is_vendor_admin(user) -> bool:
    """Alias for is_service_provider_admin or is_superadmin."""
    return is_service_provider_admin(user) or is_superadmin(user)


def is_admin_role(user) -> bool:
    """Alias for is_workforce_admin."""
    return is_workforce_admin(user)


# ── DRF Permission Classes ───────────────────────────────────────────────────
class IsSuperadmin(BasePermission):
    def has_permission(self, request, view):
        return is_superadmin(getattr(request, "user", None))


class IsServiceProviderAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return is_service_provider_admin(user) or is_superadmin(user)


class IsWorkforceAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_workforce_admin(getattr(request, "user", None))


class IsWorkforceEmployee(BasePermission):
    def has_permission(self, request, view):
        return is_workforce_employee(getattr(request, "user", None))


