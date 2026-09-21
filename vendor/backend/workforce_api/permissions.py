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


class IsGrocerySupplier(BasePermission):
    """
    Authorizes an authenticated Vendor Admin/Manager who is registered as a Grocery Supplier.
    Service providers (AC, electrical, cleaning, plumbing, etc.) without grocery capability
    are strictly rejected with 403 Forbidden.
    """
    message = "This module is restricted to verified Grocery Suppliers."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        if not is_admin_role(user):
            return False

        emp = getattr(user, "employee_profile", None)
        company = emp.company if emp else getattr(user, "company", None)
        if not company:
            return False

        # Platform company exception (has access to all modules)
        if company.id == 1 or getattr(company, "slug", "") in (
            "calservices",
            "caldim-platform",
            "caldim-engineering-pvt-ltd",
            "caldim-services",
        ):
            return True

        btype = getattr(company, "business_type", "") or ""
        if btype in ("grocery_supplier", "hybrid"):
            return True

        modules = getattr(company, "selected_modules", []) or []
        if any(m in modules for m in ("grocery_supplier", "grocery_inventory", "groceries")):
            return True

        industry = (getattr(company, "industry", "") or "").lower()
        if any(k in industry for k in ("grocery", "vegetable", "produce", "farm", "supermarket")):
            return True

        return False


class IsInternalWorkforceCaller(BasePermission):
    """
    Authorizes server-to-server calls from the Customer app's
    WorkforceIntegrationService -- there is no vendor-side user session for
    these calls, the Customer app is acting on a customer's behalf.
    Authenticated by a shared secret or API key (Bearer token), not a session/JWT.
    Fail-closed.
    """
    def has_permission(self, request, view):
        import hmac
        import os
        from django.conf import settings

        provided = ""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            provided = auth_header[len("Bearer "):].strip()

        if not provided or provided == "wf_integration_key_default":
            return False

        expected_secret = getattr(settings, "WORKFORCE_WEBHOOK_SECRET", "") or ""
        if expected_secret == "wf_integration_key_default":
            expected_secret = ""

        expected_api_key = getattr(settings, "WORKFORCE_API_KEY", "") or os.getenv("WORKFORCE_API_KEY", "")
        if expected_api_key == "wf_integration_key_default":
            expected_api_key = ""

        valid_secret = False
        if expected_secret:
            try:
                valid_secret = hmac.compare_digest(provided.encode("utf-8"), expected_secret.encode("utf-8"))
            except Exception:
                valid_secret = False

        valid_api_key = False
        if expected_api_key:
            try:
                valid_api_key = hmac.compare_digest(provided.encode("utf-8"), expected_api_key.encode("utf-8"))
            except Exception:
                valid_api_key = False

        return valid_secret or valid_api_key


class IsMarketplaceIntegrationCaller(BasePermission):
    """
    Authorizes server-to-server integration calls from Sevo-customer marketplace backend.
    Enforces shared secret / webhook token authentication with strict fail-closed behavior.
    Accepts EXACTLY:
      - Authorization: Bearer <secret> (validated against WORKFORCE_WEBHOOK_SECRET)
      - X-Workforce-Webhook-Secret: <secret> (validated against WORKFORCE_WEBHOOK_SECRET)
      - X-Workforce-Api-Key: <key> (validated against WORKFORCE_API_KEY)
    """
    def has_permission(self, request, view):
        import hmac
        import os
        from django.conf import settings

        # 1. Authorization: Bearer <secret>
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            provided_secret = auth_header[len("Bearer "):].strip()
            if provided_secret and provided_secret != "wf_integration_key_default":
                expected_secret = getattr(settings, "WORKFORCE_WEBHOOK_SECRET", "") or ""
                if expected_secret and expected_secret != "wf_integration_key_default":
                    try:
                        if hmac.compare_digest(provided_secret.encode("utf-8"), expected_secret.encode("utf-8")):
                            return True
                    except Exception:
                        pass
            return False

        # 2. X-Workforce-Webhook-Secret: <secret>
        webhook_header = request.META.get("HTTP_X_WORKFORCE_WEBHOOK_SECRET", "").strip()
        if webhook_header:
            if webhook_header != "wf_integration_key_default":
                expected_secret = getattr(settings, "WORKFORCE_WEBHOOK_SECRET", "") or ""
                if expected_secret and expected_secret != "wf_integration_key_default":
                    try:
                        if hmac.compare_digest(webhook_header.encode("utf-8"), expected_secret.encode("utf-8")):
                            return True
                    except Exception:
                        pass
            return False

        # 3. X-Workforce-Api-Key: <key>
        api_key_header = request.META.get("HTTP_X_WORKFORCE_API_KEY", "").strip()
        if api_key_header:
            if api_key_header != "wf_integration_key_default":
                expected_api_key = getattr(settings, "WORKFORCE_API_KEY", "") or os.getenv("WORKFORCE_API_KEY", "")
                if expected_api_key and expected_api_key != "wf_integration_key_default":
                    try:
                        if hmac.compare_digest(api_key_header.encode("utf-8"), expected_api_key.encode("utf-8")):
                            return True
                    except Exception:
                        pass
            return False

        return False


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
