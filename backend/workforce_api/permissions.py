"""
workforce-app/backend/workforce_api/permissions.py
Role and lifecycle state based authorization guards for Workforce API.
"""
from rest_framework.permissions import BasePermission
from accounts.permissions import is_admin_role


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
        user = getattr(request, "user", None)
        return bool(user and user.is_authenticated and getattr(user, "is_superuser", False))


class IsVendorAdmin(BasePermission):
    """
    Authorizes a Vendor Admin/Manager.
    Requires user to have an admin role AND an assigned company tenant.
    Platform superusers are also permitted.
    """
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        role = str(getattr(user, "role", "")).lower()
        has_admin_role = is_admin_role(user)
        has_company = getattr(user, "company_id", None) is not None or getattr(getattr(user, "employee_profile", None), "company_id", None) is not None
        return has_admin_role and has_company


class IsInternalWorkforceCaller(BasePermission):
    """
    Authorizes server-to-server calls from the Customer app's
    WorkforceIntegrationService -- there is no vendor-side user session for
    these calls, the Customer app is acting on a customer's behalf (e.g.
    "the customer cancelled their booking, release the technician").
    Authenticated by a shared secret, not a session/JWT.

    Reuses WORKFORCE_WEBHOOK_SECRET rather than introducing a second shared
    secret: it's the same value already used (in the other direction) to
    authenticate this app's webhook calls INTO the Customer app, so both
    apps already need to have it configured identically, and it now fails
    closed in production if unset (see workforce_core/settings.py).
    """
    def has_permission(self, request, view):
        import hmac
        from django.conf import settings
        provided = request.META.get("HTTP_AUTHORIZATION", "")
        if provided.startswith("Bearer "):
            provided = provided[len("Bearer "):].strip()
        else:
            provided = ""
        expected = getattr(settings, "WORKFORCE_WEBHOOK_SECRET", "") or ""
        return bool(provided and expected and hmac.compare_digest(provided, expected))



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

        ob_data = (emp.bank_details or {}).get("onboarding", {}) if isinstance(emp.bank_details, dict) else {}
        ob_status = str(ob_data.get("status", "")).lower() if isinstance(ob_data, dict) else ""
        # HS-A-04 fix: this class is named "IsApprovedTechnician" and every call
        # site relies on it to gate technician-facing job/work endpoints on real
        # admin approval (see AdminApproveCandidateView, which requires every
        # onboarding document AND at least one requested service to be marked
        # "approved" before setting onboarding.status = "approved"). The previous
        # "or emp.is_active" clause made that gate meaningless: Employee.is_active
        # defaults to True at signup (WorkforceSignupView), before any vetting
        # happens, so effectively every freshly-signed-up technician passed this
        # check regardless of onboarding.status (which defaults to "not_started").
        # Confirmed there is no legacy population relying on the old behavior:
        # bank_details.onboarding is always initialized at signup and the only
        # place that writes status="approved" is the real admin-approval flow.
        return ob_status == "approved"
