"""
workforce-app/backend/workforce_api/permissions.py
Role and lifecycle state based authorization guards for Workforce API.
"""
from rest_framework.permissions import BasePermission
from accounts.permissions import is_admin_role
from workforce_api.services.registration import is_employee_approved, get_employee_registration_status


class IsWorkforceAdmin(BasePermission):
    def has_permission(self, request, view):
        return is_admin_role(getattr(request, "user", None))


class IsWorkforceEmployee(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        role = str(getattr(user, "role", "")).lower()
        if role in ("employee", "technician") or is_admin_role(user):
            return True
        emp = getattr(user, "employee_profile", None)
        if not emp:
            from employees.models import Employee
            try:
                emp = Employee.objects.filter(user=user).first()
            except Exception:
                emp = None
        return bool(emp and getattr(emp, "is_active", True) and getattr(user, "is_active", True))


class IsPlatformSuperAdmin(BasePermission):
    """
    Authorizes Platform Superadmin actors (cross-tenant platform operators).
    """
    def has_permission(self, request, view):
        from accounts.permissions import is_superadmin
        return is_superadmin(getattr(request, "user", None))


class IsVendorAdmin(BasePermission):
    """
    Authorizes a Service Provider Admin.
    Requires user to have an admin role AND an assigned company/provider tenant.
    Platform superadmins are also permitted.
    """
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        from accounts.permissions import is_superadmin, is_service_provider_admin
        return is_superadmin(user) or is_service_provider_admin(user)


IsSuperadmin = IsPlatformSuperAdmin
IsServiceProviderAdmin = IsVendorAdmin


class IsApprovedTechnician(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if is_admin_role(user):
            return True

        emp = getattr(user, "employee_profile", None)
        if not emp:
            from employees.models import Employee
            try:
                emp = Employee.objects.filter(user=user).first()
            except Exception:
                emp = None
        if not emp or not getattr(emp, "is_active", True) or not getattr(user, "is_active", True):
            return False

        return is_employee_approved(emp)
