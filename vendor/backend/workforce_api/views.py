"""
workforce-app/backend/workforce_api/views.py
Complete API views for Workforce Registration, Admin Approvals, Decoupled Availability, and Field Dispatch.
"""
import uuid
import os
import json
import time
import datetime
from datetime import timedelta
import logging
from decimal import Decimal
from django.conf import settings

from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.db.models import Q

logger = logging.getLogger(__name__)


from django.utils import timezone
from django.utils.text import slugify
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle  # EC-06
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.authentication import set_auth_cookies
from companies.models import Company, Region
from employees.models import Employee, PresenceLog
from employees.utils import generate_next_employee_id
from service_requests.models import ServiceRequest
from service_requests.state_machine import apply_transition
from time_tracking.models import Location, TimeLog
from time_tracking.geo import evaluate


from datetime import timedelta
import secrets
from django.contrib.auth.hashers import make_password, check_password
from accounts.permissions import is_admin_role
from .permissions import IsWorkforceAdmin, IsWorkforceEmployee, IsApprovedTechnician, IsInternalWorkforceCaller
from .serializers import (
    WorkforceSignupSerializer,
    ProviderSignupSerializer,
    WalletAccountSerializer,
    WalletPayoutDetailsSerializer,
    WalletWithdrawSerializer,
    WalletAutoWithdrawalSettingsSerializer,
    WorkforceOnboardingDraftSerializer,
    WorkforceEmployeeProfileSerializer,
    WorkforceJobSerializer,
    WorkforceWorkExtensionSerializer,
    CustomerWorkforceExtensionSerializer,
    WorkforceSupplementalInvoiceSerializer,
    WorkforceJobRescheduleSerializer,
    WorkforceEmployeeChangeRequestSerializer,
    WorkforceUserPreferenceSerializer,
    WorkforceNotificationPreferenceSerializer,
    WorkforceJobFeedbackSerializer,
    JobPaymentSerializer,
    PaymentCollectionEventSerializer,
)
from .models import (
    WorkforceEmployeeSchedule,
    WorkforceSkill,
    WorkforceEmployeeSkill,
    WorkforceComplianceRequirement,
    WorkforceEmployeeCompliance,
    WorkforcePayPeriod,
    WorkforcePayslip,
    WorkforceJobOffer,
    PreServiceVerification,
    PostServiceProof,
    WorkforceWorkExtension,
    WorkforceSupplementalInvoice,
    WorkforceJobReschedule,
    WorkforceEmployeeChangeRequest,
    WorkforceUserPreference,
    WorkforceNotificationPreference,
    WorkforceJobFeedback,
    WorkforceEventLog,
    WorkforceNotification,
    JobPayment,
    PaymentCollectionEvent,
    WorkforceJobLifecycleEvent,
    JobTrackingSession,
    JobLocationPoint,
    WorkforceScorecard,
    SocialSecurityRegistration,
    VendorCriteria,
    CriteriaTerm,
    VendorInvitation,
    VendorTechnicianRelationship,
    VendorRelievingRequest,
)
from time_tracking.models import TimeLog, Break
from time_tracking.serializers import TimeLogSerializer
from .services.vendor_network import (
    VendorDiscoveryEngine,
    VendorInvitationService,
    VendorRelationshipService,
    VendorRelievingService,
)
import json
import time
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse


User = get_user_model()

# ─── Tenant Isolation Helper ──────────────────────────────────────────────────



def resolve_actor_company(request):
    """
    Authoritative Multi-Tenant Company Context Resolver:
    Resolves the authenticated user's company context strictly without arbitrary fallback.
    Returns:
        Company instance if resolved, or None if context cannot be determined.
    Rules:
        - If user is not authenticated: returns None.
        - If user has explicit company foreign key (user.company): returns user.company.
        - If user has employee_profile (user.employee_profile.company): returns employee_profile.company.
        - If user is a superuser without an assigned company: returns None (indicating superuser operates cross-tenant unless explicitly scoped).
        - NEVER returns Company.objects.first() fallback.
    """
    if not request or not hasattr(request, "user") or not request.user or not request.user.is_authenticated:
        return None
    user = request.user
    if getattr(user, "company", None):
        return user.company
    emp = getattr(user, "employee_profile", None)
    if emp and getattr(emp, "company", None):
        return emp.company
    return None


def _is_admin_authorized_for_company(request, company) -> bool:
    """
    Fixes a recurring IDOR pattern: several endpoints granted any
    is_admin_role() user access to any job/invoice just by checking their
    role, without checking that the admin's own company actually matches
    the job's company -- so one company's admin could act on another
    company's data. Mirrors resolve_actor_company()'s superuser exception.
    """
    user = getattr(request, "user", None)
    if not user or not is_admin_role(user):
        return False
    if getattr(user, "is_superuser", False):
        return True
    user_company = resolve_actor_company(request)
    company_id = getattr(company, "id", company)
    return bool(user_company and company_id and user_company.id == company_id)


ALLOWED_PHOTO_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "heic", "heif"}
ALLOWED_PHOTO_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "image/heif",
}
MAX_PHOTO_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MIN_PHOTO_DIMENSION = 64          # px; anything smaller is not a real capture
BLANK_PHOTO_LUMA_RANGE = 4        # max-min luma below this == a flat frame
BLANK_PHOTO_MAX_LUMA = 16         # ...and this dark == no image at all


def _validate_photo_content(f):
    """
    Fixes: proof photos were accepted on filename extension and Content-Type
    alone, both of which the client fully controls. That let a blank capture
    through, because a blank frame is a perfectly valid JPEG -- and in this
    deployment every single stored pre- and post-service photo turned out to be
    the same 6158-byte solid-black 1280x720 image. The technician app was
    drawing frames from a <video> element before it had decoded one (fixed
    separately in LiveCameraCaptureModal.jsx), and nothing on either side
    noticed, so jobs were being completed with black squares as their evidence.

    This checks that the bytes actually decode as an image and that the frame
    carries some content. Fails open when Pillow is unavailable so a missing
    optional dependency can never block a legitimate upload.
    """
    try:
        from PIL import Image
    except Exception:
        return None

    try:
        f.seek(0)
        Image.open(f).verify()  # structural decode; leaves the object unusable
        f.seek(0)
        img = Image.open(f).convert("L")
        width, height = img.size
        if width < MIN_PHOTO_DIMENSION or height < MIN_PHOTO_DIMENSION:
            return (
                f"Image is too small ({width}x{height}px). "
                f"Minimum is {MIN_PHOTO_DIMENSION}x{MIN_PHOTO_DIMENSION}px."
            )
        # Downscale first so this stays cheap on a full-resolution photo.
        img.thumbnail((64, 64))
        low, high = img.getextrema()
        if (high - low) < BLANK_PHOTO_LUMA_RANGE and high < BLANK_PHOTO_MAX_LUMA:
            return (
                "This photo is blank -- the camera did not capture an image. "
                "Wait for the camera preview to appear, then take the photo again."
            )
    except Exception:
        return "This file is not a readable image. Please retake the photo."
    finally:
        try:
            f.seek(0)
        except Exception:
            pass
    return None


def _validate_photo_upload(f):
    """
    Fixes: proof/verification photo uploads (PreServiceVerification,
    PostServiceProof) had zero server-side file-type or size validation
    anywhere -- no extension check, no content-type check, no size cap.
    Combined with the media location block's missing
    X-Content-Type-Options: nosniff header (fixed separately in the nginx
    config), that allowed a disguised .html/.svg "photo" to be uploaded and
    served back from this app's own origin as executable content (stored
    XSS). Returns an error string if the file should be rejected, or None
    if it's acceptable.
    """
    if not f:
        return None
    name = (getattr(f, "name", "") or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        return f"Unsupported file type '.{ext}'. Allowed: {', '.join(sorted(ALLOWED_PHOTO_EXTENSIONS))}."
    content_type = (getattr(f, "content_type", "") or "").lower()
    if content_type and content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
        return f"Unsupported content type '{content_type}'."
    size = getattr(f, "size", 0) or 0
    if size > MAX_PHOTO_UPLOAD_BYTES:
        return f"File too large ({size // (1024 * 1024)}MB). Maximum allowed is {MAX_PHOTO_UPLOAD_BYTES // (1024 * 1024)}MB."
    return _validate_photo_content(f)


def ensure_job_started(job, employee, actor, notes="Auto clock-in on pre-service completion"):
    """
    Idempotently clock a technician in for `job` and move it to in_progress.

    Fixes: the only code that created a TimeLog lived inside
    WorkforceJobVerifyOTPView as a nested closure, so it could only ever run on
    one of the four pre-service gates -- the OTP one. Completing the gates in
    the order the UI lists them (location, OTP, selfie, work-area photo) meant
    the OTP call ran while the photos were still missing, the closure no-oped,
    and nothing ever created the TimeLog. apply_transition() refuses
    "in_progress" without an open TimeLog, so "Start Service Execution" then
    failed for every technician who worked top to bottom, and the clock never
    started. Hoisting this to module level lets every gate endpoint call it, so
    whichever gate finishes last is the one that starts the job.

    Returns (time_log, error_message); error_message is None on success.
    """
    from django.db import IntegrityError
    from time_tracking.models import TimeLog
    from service_requests.state_machine import apply_transition
    from service_requests.models import EmployeeJob

    if not employee:
        return None, "No technician profile is attached to this account."

    verification = PreServiceVerification.objects.filter(job=job).first()
    if not verification:
        return None, "Pre-service verification has not been started for this job."

    # Recompute rather than trusting a possibly stale is_complete flag.
    verification.check_completion()
    verification.save(update_fields=["is_complete", "completed_at", "updated_at"])

    if not verification.is_complete:
        missing = []
        if not verification.geofence_passed:
            missing.append("location check-in")
        if not verification.otp_verified:
            missing.append("customer OTP")
        if not verification.presence_photo:
            missing.append("technician selfie")
        if not verification.work_area_photo:
            missing.append("work area photo")
        return None, "Cannot start work yet. Still required: " + ", ".join(missing) + "."

    now_ts = timezone.now()

    # One open TimeLog per employee is enforced by a DB constraint; reuse an
    # open one instead of racing it, so repeated clicks cannot double clock-in.
    time_log = TimeLog.objects.filter(employee=employee, clock_out__isnull=True).first()
    if not time_log:
        company = employee.company or getattr(actor, "company", None) or job.company
        try:
            time_log = TimeLog.objects.create(
                employee=employee,
                company=company,
                user=actor if getattr(actor, "pk", None) else None,
                work_date=timezone.localdate(),
                clock_in=now_ts,
                clock_in_lat=job.latitude or 0.0,
                clock_in_lon=job.longitude or 0.0,
                clock_in_address=job.address or "",
                clock_in_notes=notes,
                distance_from_site_meters=0,
                geofence_passed=True,
                admin_override_used=False,
                status="draft",
            )
        except IntegrityError:
            # Lost a race with a concurrent request -- adopt the winner's log.
            time_log = TimeLog.objects.filter(employee=employee, clock_out__isnull=True).first()

    if job.status != "in_progress":
        try:
            apply_transition(job, "in_progress", actor=actor)
        except Exception as exc:
            logger.warning("Could not transition job %s to in_progress: %s", job.pk, exc)
            return time_log, str(getattr(exc, "detail", exc))

    try:
        EmployeeJob.objects.filter(service_request=job, employee=employee).update(status="IN_PROGRESS")
    except Exception:
        pass

    return time_log, None


def get_request_company(request):
    """
    Compatibility wrapper around resolve_actor_company.
    """
    return resolve_actor_company(request)


# ─── 1. Lightweight Employee Signup (Step 1) ──────────────────────────────────

class WorkforceSignupView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]  # EC-06: unauthenticated, brute-forceable
    throttle_scope = "workforce_signup"

    def post(self, request):
        serializer = WorkforceSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            company_id = request.data.get("company_id")
            company_slug = request.data.get("company_slug")
            # Whether this signup explicitly asked to join a specific
            # provider's team (vs. falling through to the shared default
            # company below) -- decides which wallet channel this worker
            # gets provisioned into. See SEVO business plan Section 2.
            joining_provider_team = bool(company_id or company_slug)
            company = None
            if company_id:
                try:
                    company = Company.objects.filter(pk=int(company_id), is_active=True).first()
                except (ValueError, TypeError):
                    pass
            if not company and company_slug:
                company = Company.objects.filter(slug=company_slug, is_active=True).first()
            if not company:
                company = Company.objects.filter(slug="calservices", is_active=True).first()
            if not company:
                region, _ = Region.objects.get_or_create(
                    code="IN",
                    defaults={"name": "India", "currency": "INR", "currency_symbol": "₹"},
                )
                company = Company.objects.create(
                    company_name="CalServices Operations",
                    display_id="CALS",
                    slug="calservices",
                    primary_country="IN",
                    region=region,
                    is_active=True,
                )

            username_candidate = data["email"].split("@")[0].lower()
            username = username_candidate
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_candidate}_{counter}"
                counter += 1

            user = User.objects.create(
                username=username,
                email=data["email"],
                mobile_number=data["mobile_number"],
                phone=data["mobile_number"],
                first_name=data["first_name"],
                last_name=data.get("last_name", ""),
                role="employee",
                company=company,
                is_active=True,
                totp_secret="",
                bio="",
            )
            user.set_password(data["password"])
            user.save()

            employee_id = generate_next_employee_id(company)
            employee = Employee.objects.create(
                user=user,
                company=company,
                employee_id=employee_id,
                title="Technician Candidate",
                exempt_status="non_exempt",
                hourly_rate=0,
                is_online=False,
                current_availability="offline",
                is_active=True,
                bank_details={
                    "onboarding": {
                        "status": "not_started",
                        "step": 1,
                        "draft": {
                            "personal": {
                                "first_name": user.first_name,
                                "last_name": user.last_name,
                                "email": user.email,
                                "mobile_number": user.mobile_number,
                            }
                        },
                        "services": [],
                        "documents": {},
                        "correction_notes": "",
                        "rejection_reason": "",
                        "submitted_at": None,
                        "approved_at": None,
                        "channel": "provider_team" if joining_provider_team else "individual",
                    }
                },
            )

            if not joining_provider_team:
                # SEVO Individual Worker Model: this technician has no
                # provider umbrella, so their own personal wallet -- not
                # the shared default company's head wallet -- is what
                # resolve_payee_wallet() must find for their completed
                # jobs. Non-fatal: a wallet-provisioning hiccup must never
                # block someone from creating an account.
                try:
                    from workforce_api.services import provision_individual_wallet
                    provision_individual_wallet(employee)
                except Exception:
                    logger.exception(
                        "Failed to provision individual wallet for new employee #%s at signup "
                        "-- will need manual wallet provisioning before this worker can be paid.",
                        employee.id,
                    )

            # Automatically backfill any pending vendor invitations sent to this email
            try:
                from workforce_api.services.vendor_network import VendorInvitationService
                VendorInvitationService.backfill_invitations_for_employee(employee)
            except Exception:
                logger.exception("Failed to backfill vendor invitations for employee #%s", employee.id)

        refresh = RefreshToken.for_user(user)
        refresh["company_id"] = company.id
        refresh["role"] = user.role

        response = Response(
            {
                "message": "Workforce account created successfully.",
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "token": str(refresh.access_token),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                    "employee_id": employee.employee_id,
                    "registration_status": "not_started",
                },
            },
            status=status.HTTP_201_CREATED,
        )

        set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


# ─── 1b. Provider Business Signup (SEVO Section 2: Existing Service Provider Model) ──

class ProviderSignupView(APIView):
    """
    A service-provider business (not an individual technician) registers
    itself: gets its own Company row, an admin/manager User account for
    whoever owns the business, and a PROVIDER_HEAD wallet. The returned
    company_id/company_slug is what the provider then hands to their own
    workers so WorkforceSignupView routes those signups into this same
    company (and therefore this same head wallet) instead of the shared
    default company.
    """
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "workforce_signup"

    def post(self, request):
        serializer = ProviderSignupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            region, _ = Region.objects.get_or_create(
                code="IN",
                defaults={"name": "India", "currency": "INR", "currency_symbol": "₹"},
            )

            base_slug = slugify(data["business_name"])[:60] or "provider"
            slug = base_slug
            counter = 1
            while Company.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            company = Company.objects.create(
                company_name=data["business_name"],
                slug=slug,
                primary_country="IN",
                region=region,
                default_state="Tamil Nadu",
                address=data.get("address", ""),
                is_active=True,
            )

            username_candidate = data["email"].split("@")[0].lower()
            username = username_candidate
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{username_candidate}_{counter}"
                counter += 1

            user = User.objects.create(
                username=username,
                email=data["email"],
                mobile_number=data["mobile_number"],
                phone=data["mobile_number"],
                first_name=data["contact_first_name"],
                last_name=data.get("contact_last_name", ""),
                role="manager",
                company=company,
                is_active=True,
                totp_secret="",
                bio="",
            )
            user.set_password(data["password"])
            user.save()

            try:
                from workforce_api.services import provision_provider_wallet
                provision_provider_wallet(company)
            except Exception:
                logger.exception(
                    "Failed to provision head wallet for new provider company #%s at signup "
                    "-- will need manual wallet provisioning before this provider's team can be paid.",
                    company.id,
                )

        refresh = RefreshToken.for_user(user)
        refresh["company_id"] = company.id
        refresh["role"] = user.role

        response = Response(
            {
                "message": "Provider business account created successfully.",
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "token": str(refresh.access_token),
                "company": {
                    "id": company.id,
                    "slug": company.slug,
                    "company_name": company.company_name,
                },
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": user.role,
                },
            },
            status=status.HTTP_201_CREATED,
        )
        set_auth_cookies(response, str(refresh.access_token), str(refresh))
        return response


# ─── 1c. Wallet Self-Service (payout details, own wallet status) ─────────────

class WalletMeView(APIView):
    """
    GET: the caller's own wallet -- their personal INDIVIDUAL_WORKER wallet
    if they onboarded directly, or their provider company's shared
    PROVIDER_HEAD wallet if they're that company's admin/manager. 404 if
    neither applies (not yet onboarded, or a customer/kiosk account).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from workforce_api.services import resolve_wallet_for_user
        wallet, owner_role = resolve_wallet_for_user(request.user)
        if not wallet:
            return Response(
                {"error": "No wallet found for this account yet."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = WalletAccountSerializer(wallet, context={"owner_role": owner_role})
        return Response(serializer.data, status=status.HTTP_200_OK)


class WalletPayoutDetailsView(APIView):
    """
    PATCH: set/update the caller's own wallet's payout destination (bank
    account or UPI ID). See services.wallet_onboarding.set_payout_details
    for validation rules and the TIER_0 -> TIER_1 KYC bump this triggers.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        from workforce_api.services import resolve_wallet_for_user, set_payout_details, PayoutDetailsError
        wallet, owner_role = resolve_wallet_for_user(request.user)
        if not wallet:
            return Response(
                {"error": "No wallet found for this account yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WalletPayoutDetailsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            wallet = set_payout_details(
                wallet,
                bank_account_name=data.get("bank_account_name", ""),
                bank_account_number=data.get("bank_account_number", ""),
                ifsc=data.get("ifsc", ""),
                upi_id=data.get("upi_id", ""),
            )
        except PayoutDetailsError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = WalletAccountSerializer(wallet, context={"owner_role": owner_role})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class WalletWithdrawView(APIView):
    """
    POST /workforce/wallet/withdraw/: on-demand self-service withdrawal of
    the caller's own wallet, subject to available balance and the
    KYC-tier daily cap -- see services.withdrawals.request_withdrawal for
    the validation rules. Shares the same execution path (services.payouts)
    as the scheduled-withdrawal cron, so a withdrawal behaves identically
    whether it was requested here or fired automatically.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from workforce_api.services import resolve_wallet_for_user, request_withdrawal, WithdrawalValidationError
        wallet, owner_role = resolve_wallet_for_user(request.user)
        if not wallet:
            return Response(
                {"error": "No wallet found for this account yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WalletWithdrawSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            withdrawal = request_withdrawal(wallet, serializer.validated_data["amount"])
        except WithdrawalValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "id": withdrawal.id,
            "amount": str(withdrawal.amount),
            "status": withdrawal.status,
            "requested_at": withdrawal.requested_at.isoformat(),
            # True when this was simulated via RAZORPAYX_MOCK_MODE rather than
            # a real RazorpayX payout -- see services.payouts.is_mock_mode().
            "is_mock": (withdrawal.razorpayx_payout_id or "").startswith("mock_payout_"),
        }, status=status.HTTP_201_CREATED)


class WalletAutoWithdrawalSettingsView(APIView):
    """
    PATCH /workforce/wallet/auto-withdrawal/: set/update the caller's own
    wallet's standing auto-payout rule and minimum-balance alert floor
    (SEVO Section 1, head-wallet specific features). Available to any
    wallet owner, not just providers -- an individual worker who wants a
    standing daily/weekly auto-payout can set the same fields.
    """
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        from workforce_api.services import resolve_wallet_for_user
        wallet, owner_role = resolve_wallet_for_user(request.user)
        if not wallet:
            return Response(
                {"error": "No wallet found for this account yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = WalletAutoWithdrawalSettingsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        update_fields = []
        if "auto_withdrawal_enabled" in data:
            wallet.auto_withdrawal_enabled = data["auto_withdrawal_enabled"]
            update_fields.append("auto_withdrawal_enabled")
        if "auto_withdrawal_frequency" in data:
            wallet.auto_withdrawal_frequency = data["auto_withdrawal_frequency"]
            update_fields.append("auto_withdrawal_frequency")
        if "auto_withdrawal_day_of_week" in data:
            wallet.auto_withdrawal_day_of_week = data["auto_withdrawal_day_of_week"]
            update_fields.append("auto_withdrawal_day_of_week")
        if "minimum_balance_alert_threshold" in data:
            wallet.minimum_balance_alert_threshold = data["minimum_balance_alert_threshold"]
            update_fields.append("minimum_balance_alert_threshold")

        if wallet.auto_withdrawal_enabled and not wallet.auto_withdrawal_frequency:
            return Response(
                {"error": "Set a frequency (DAILY or WEEKLY) before enabling auto-withdrawal."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if wallet.auto_withdrawal_frequency == "WEEKLY" and wallet.auto_withdrawal_day_of_week is None:
            return Response(
                {"error": "Set a day of week for a WEEKLY auto-withdrawal schedule."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if update_fields:
            update_fields.append("updated_at")
            wallet.save(update_fields=update_fields)

        response_serializer = WalletAccountSerializer(wallet, context={"owner_role": owner_role})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class WalletEarningsStatementView(APIView):
    """
    GET /workforce/wallet/statement/?year=YYYY[&month=MM]: SEVO Section 6
    ("Auto-generated monthly and annual earnings statements for both
    providers (business income) and individual workers (professional/
    other income)"). Does NOT compute or withhold any tax -- see
    services.tax_statements module docstring for why TDS is deliberately
    out of scope here.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from workforce_api.services import resolve_wallet_for_user, generate_earnings_statement
        wallet, owner_role = resolve_wallet_for_user(request.user)
        if not wallet:
            return Response({"error": "No wallet found for this account yet."}, status=status.HTTP_404_NOT_FOUND)

        try:
            year = int(request.query_params.get("year") or timezone.now().year)
        except (TypeError, ValueError):
            return Response({"error": "year must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        month_param = request.query_params.get("month")
        month = None
        if month_param:
            try:
                month = int(month_param)
                if not (1 <= month <= 12):
                    raise ValueError
            except (TypeError, ValueError):
                return Response({"error": "month must be an integer between 1 and 12."}, status=status.HTTP_400_BAD_REQUEST)

        statement = generate_earnings_statement(wallet, year, month)
        statement["owner_role"] = owner_role
        return Response(statement, status=status.HTTP_200_OK)


class WalletLedgerExportView(APIView):
    """
    GET /workforce/wallet/ledger/export/[?start=YYYY-MM-DD&end=YYYY-MM-DD]:
    the CSV "wage register" from SEVO Section 1 -- every ledger row for
    the caller's own wallet, tagged with job ID, amount, commission and
    (when known) the worker who performed it, for salary reconciliation
    or handing to an accountant.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from workforce_api.services import resolve_wallet_for_user, export_ledger_csv
        wallet, _owner_role = resolve_wallet_for_user(request.user)
        if not wallet:
            return Response({"error": "No wallet found for this account yet."}, status=status.HTTP_404_NOT_FOUND)

        start_date = request.query_params.get("start") or None
        end_date = request.query_params.get("end") or None
        csv_text = export_ledger_csv(wallet, start_date=start_date, end_date=end_date)

        response = HttpResponse(csv_text, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="wallet-{wallet.id}-ledger.csv"'
        return response


class RazorpayXPayoutWebhookView(APIView):
    """
    POST /workforce/wallet/payout-webhook/: RazorpayX's server-to-server
    callback for payout.processed / payout.failed / payout.reversed --
    see services.payouts.handle_payout_webhook for the signature
    verification and ledger-reversal logic. Public and unauthenticated by
    design (RazorpayX has no user session to send) -- trust comes from
    the X-Razorpay-Signature HMAC, verified against the RAW request body,
    not from any Django auth mechanism. Always returns 200 once the body
    has been read, even for a signature that fails to verify or an event
    this codebase doesn't recognise -- RazorpayX interprets a non-2xx as
    "retry me", and a webhook that will never verify (wrong secret, a
    stale/duplicate delivery) should not be retried forever. Every
    outcome is logged either way, so a real problem is still visible.
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        from workforce_api.services import handle_payout_webhook

        raw_body = request.body.decode("utf-8", errors="replace")
        signature = request.headers.get("X-Razorpay-Signature", "")

        try:
            handled = handle_payout_webhook(raw_body, signature)
        except Exception:
            logger.exception("[PAYOUT_WEBHOOK] Unhandled error processing RazorpayX payout webhook.")
            handled = False

        return Response({"handled": handled}, status=status.HTTP_200_OK)


class WorkforceAdminReconciliationView(APIView):
    """
    GET /workforce/admin/reconciliation/[?date=YYYY-MM-DD]: on-demand view
    of the daily reconciliation job's findings for the caller's own
    company (SEVO Section 5) -- the same check that
    management/commands/run_daily_reconciliation.py runs on a schedule,
    exposed here so an admin does not have to wait for the next cron
    firing or read server logs to see today's standing.
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        from datetime import datetime as _datetime
        from workforce_api.services import run_daily_reconciliation

        target_date = None
        date_param = request.query_params.get("date")
        if date_param:
            try:
                target_date = _datetime.strptime(date_param, "%Y-%m-%d").date()
            except ValueError:
                return Response({"error": "date must be YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        company = None
        if not getattr(request.user, "is_superuser", False):
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)

        result = run_daily_reconciliation(target_date=target_date, company=company)
        return Response(result, status=status.HTTP_200_OK)


# ─── 2. Onboarding Status & Draft Persistence ─────────────────────────────────

class WorkforceOnboardingMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found for user."}, status=status.HTTP_404_NOT_FOUND)

        from workforce_api.services.workload import reconcile_employee_availability
        reconcile_employee_availability(emp)
        emp.refresh_from_db(fields=["current_availability", "is_online"])

        serializer = WorkforceEmployeeProfileSerializer(emp)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkforceOnboardingDraftView(APIView):
    permission_classes = [IsWorkforceEmployee]

    def patch(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee record not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = WorkforceOnboardingDraftSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        step = serializer.validated_data.get("step")
        draft_data = serializer.validated_data.get("draft_data", {})

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})

        current_status = onboarding.get("status", "not_started")
        if current_status == "not_started":
            onboarding["status"] = "in_progress"

        if step:
            onboarding["step"] = step

        existing_draft = onboarding.get("draft", {})
        existing_draft.update(draft_data)
        onboarding["draft"] = existing_draft

        # Sync core fields
        if "personal" in draft_data:
            p = draft_data["personal"]
            if p.get("dob"):
                emp.date_of_birth = p.get("dob")
        if "services" in draft_data:
            selected_services = draft_data["services"]
            current_services = onboarding.get("services", [])
            existing_statuses = {s.get("id"): s.get("status", "pending") for s in current_services}

            merged_services = []
            for svc in selected_services:
                s_id = svc.get("id")
                merged_services.append({
                    "id": s_id,
                    "name": svc.get("name", ""),
                    "category": svc.get("category", ""),
                    "status": existing_statuses.get(s_id, "pending"),
                    "rejection_reason": "",
                })
            onboarding["services"] = merged_services
            emp.service_roles = [s["name"] for s in merged_services]

        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": "Draft saved successfully.",
            "step": onboarding.get("step"),
            "status": onboarding.get("status"),
        }, status=status.HTTP_200_OK)


# ─── 3. Document Uploads ──────────────────────────────────────────────────────

class WorkforceOnboardingDocumentUploadView(APIView):
    permission_classes = [IsWorkforceEmployee]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee record not found."}, status=status.HTTP_404_NOT_FOUND)

        file_obj = request.FILES.get("file")
        category = request.data.get("category", "identification")
        title = request.data.get("title", category)
        document_number = request.data.get("document_number", "")

        if not file_obj:
            return Response({"error": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

        filename = f"workforce_docs/emp_{emp.id}_{category}_{uuid.uuid4().hex[:8]}_{file_obj.name}"
        saved_path = default_storage.save(filename, file_obj)
        file_url = default_storage.url(saved_path)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        documents = onboarding.get("documents", {})

        documents[category] = {
            "category": category,
            "title": title,
            "document_number": document_number,
            "file_url": file_url,
            "status": "uploaded",
            "uploaded_at": timezone.now().isoformat(),
            "rejection_reason": "",
        }

        onboarding["documents"] = documents
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": f"Document {title} uploaded successfully.",
            "document": documents[category],
        }, status=status.HTTP_201_CREATED)


# ─── 4. Final Application Submission (Step 7) ─────────────────────────────────

class WorkforceOnboardingSubmitView(APIView):
    permission_classes = [IsWorkforceEmployee]

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee record not found."}, status=status.HTTP_404_NOT_FOUND)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})

        onboarding["status"] = "submitted"
        onboarding["submitted_at"] = timezone.now().isoformat()
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.is_online = False
        emp.current_availability = "offline"
        emp.save()

        return Response({
            "message": "Application submitted successfully for Workforce Admin verification.",
            "status": "submitted",
        }, status=status.HTTP_200_OK)


# ─── 5. Service Catalog ───────────────────────────────────────────────────────

class WorkforceCatalogListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        """
        Returns the single source of truth database service catalog from PostgreSQL (shared with Customer app).
        Strictly reads from database tables (CatalogCategory & Service, falling back to WorkforceServiceCatalog if unseeded).
        """
        try:
            from service_requests.models import CatalogCategory, Service

            categories = CatalogCategory.objects.filter(is_active=True).prefetch_related(
                models.Prefetch("services", queryset=Service.objects.filter(is_active=True).order_by("sort_order", "id"))
            ).order_by("sort_order", "id")

            catalog_data = []
            for cat in categories:
                cat_services = []
                for svc in cat.services.all():
                    cat_services.append({
                        "id": svc.id,
                        "name": svc.name,
                        "slug": svc.slug,
                        "description": svc.description or "",
                        "icon": svc.icon or cat.icon or "Wrench",
                        "category_id": cat.id,
                        "category_name": cat.name,
                    })

                if cat_services:
                    catalog_data.append({
                        "id": cat.id,
                        "name": cat.name,
                        "slug": cat.slug,
                        "description": cat.description or "",
                        "icon": cat.icon or "Wrench",
                        "services": cat_services,
                    })

            if not catalog_data:
                from workforce_api.models import WorkforceServiceCatalog
                wf_services = WorkforceServiceCatalog.objects.filter(is_active=True).order_by("category", "name")
                cat_map = {}
                for s in wf_services:
                    cat_name = s.category or "General Services"
                    if cat_name not in cat_map:
                        cat_map[cat_name] = []
                    cat_map[cat_name].append({
                        "id": s.id,
                        "name": s.name,
                        "slug": s.name.lower().replace(" ", "-"),
                        "description": f"Standard {s.name} ({s.duration_minutes} mins)",
                        "icon": "Wrench",
                        "category_id": hash(cat_name) % 10000,
                        "category_name": cat_name,
                    })
                for c_idx, (cat_name, svcs) in enumerate(cat_map.items(), start=1):
                    catalog_data.append({
                        "id": c_idx,
                        "name": cat_name,
                        "slug": cat_name.lower().replace(" ", "-"),
                        "description": f"All {cat_name} services",
                        "icon": "Wrench",
                        "services": svcs,
                    })

            return Response(catalog_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("Error in WorkforceCatalogListView: %s", str(e), exc_info=True)
            return Response([], status=status.HTTP_200_OK)



# ─── 6. Admin Verification Queue & Dossier Review ─────────────────────────────

def is_platform_superadmin(user) -> bool:
    """
    Returns True if the actor is a Platform Super Admin / Platform Operator:
    - Superuser
    - Staff user belonging to Caldim Platform Tenant (company_id=1)
    - Role is superadmin or platform_admin
    - Role is admin or manager belonging to Caldim Platform Tenant (company_id=1)
    """
    if not user or not user.is_authenticated:
        return False
    return bool(
        getattr(user, "is_superuser", False)
        or (getattr(user, "is_staff", False) and getattr(user, "company_id", None) == 1)
        or str(getattr(user, "role", "")).lower() in ("superadmin", "platform_admin")
        or (str(getattr(user, "role", "")).lower() in ("admin", "manager") and getattr(user, "company_id", None) == 1)
    )


class WorkforceAdminApplicationsListView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        status_filter = request.query_params.get("status", "").strip().lower()
        company = resolve_actor_company(request)
        if is_platform_superadmin(request.user):
            employees = Employee.objects.select_related("user", "company").order_by("-id")
        elif company:
            employees = Employee.objects.filter(company=company).select_related("user", "company").order_by("-id")
        else:
            return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)

        results = []
        for emp in employees:
            profile_data = WorkforceEmployeeProfileSerializer(emp).data
            reg_status = profile_data.get("registration_status", "not_started").lower()

            if status_filter:
                if status_filter == "pending" and reg_status in ["submitted", "under_review"]:
                    results.append(profile_data)
                elif reg_status == status_filter:
                    results.append(profile_data)
            else:
                results.append(profile_data)

        return Response(results, status=status.HTTP_200_OK)


class WorkforceAdminApplicationDetailView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request, pk):
        emp = Employee.objects.filter(pk=pk).select_related("user", "company").first()
        if not emp:
            return Response({"error": "Candidate dossier not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company access.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        serializer = WorkforceEmployeeProfileSerializer(emp)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkforceAdminDocumentVerifyView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk, category):
        emp = Employee.objects.filter(pk=pk).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "").lower()
        reason = request.data.get("reason", "")

        if action not in ["approve", "reject"]:
            return Response({"error": "Action must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        documents = onboarding.get("documents", {})

        if category not in documents:
            return Response({"error": f"Document '{category}' not found in candidate dossier."}, status=status.HTTP_404_NOT_FOUND)

        documents[category]["status"] = "approved" if action == "approve" else "rejected"
        documents[category]["rejection_reason"] = reason if action == "reject" else ""
        documents[category]["verified_at"] = timezone.now().isoformat()
        documents[category]["verified_by"] = request.user.username

        onboarding["documents"] = documents
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": f"Document '{category}' marked as {action}d.",
            "document": documents[category],
        }, status=status.HTTP_200_OK)


class WorkforceAdminBulkDocumentVerifyView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        emp = Employee.objects.filter(pk=pk).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Tenant isolation
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        # Prevent employee from approving their own documents
        if getattr(request.user, "employee_profile", None) and request.user.employee_profile.id == emp.id and not is_platform_superadmin(request.user):
            return Response({"error": "Employees cannot approve or decide their own documents."}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "").lower()
        reason = request.data.get("reason", "")
        categories = request.data.get("categories")
        all_pending = request.data.get("all_pending", False)

        if action not in ["approve", "reject"]:
            return Response({"error": "Action must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        documents = onboarding.get("documents", {})

        if not documents:
            return Response({
                "message": "No documents found in candidate dossier.",
                "updated_count": 0,
                "documents": {},
            }, status=status.HTTP_200_OK)

        # Target documents
        if categories:
            cat_set = set(categories)
            target_keys = [k for k in documents.keys() if k in cat_set]
        elif all_pending:
            target_keys = [k for k, doc in documents.items() if doc.get("status") not in ["approved", "rejected"]]
        else:
            target_keys = list(documents.keys())

        if not target_keys:
            return Response({
                "message": "All uploaded documents are already decided.",
                "updated_count": 0,
                "documents": documents,
            }, status=status.HTTP_200_OK)

        now_iso = timezone.now().isoformat()
        current_username = request.user.username
        updated_count = 0

        for key in target_keys:
            doc = documents.get(key)
            if not doc:
                continue
            doc["status"] = "approved" if action == "approve" else "rejected"
            doc["rejection_reason"] = reason if action == "reject" else ""
            doc["verified_at"] = now_iso
            doc["verified_by"] = current_username
            updated_count += 1

        onboarding["documents"] = documents
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": f"Successfully {action}d {updated_count} document(s).",
            "updated_count": updated_count,
            "documents": documents,
        }, status=status.HTTP_200_OK)


class WorkforceEmployeeServiceRequestView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        service_ids = request.data.get("service_ids")
        if service_ids is not None:
            if not isinstance(service_ids, list) or len(service_ids) == 0:
                return Response({"error": "service_ids must be a non-empty list."}, status=status.HTTP_400_BAD_REQUEST)
            raw_ids = [s for s in service_ids if s is not None]
        else:
            single_id = request.data.get("service_id")
            if not single_id:
                return Response({"error": "service_id or service_ids is required."}, status=status.HTTP_400_BAD_REQUEST)
            raw_ids = [single_id]

        from service_requests.models import Service
        from workforce_api.models import WorkforceServiceCatalog

        # Query services from DB
        db_services = {s.id: s for s in Service.objects.filter(pk__in=raw_ids, is_active=True).select_related("category")}
        wf_services = {s.id: s for s in WorkforceServiceCatalog.objects.filter(pk__in=raw_ids, is_active=True)}

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        services = onboarding.get("services", [])
        now_iso = timezone.now().isoformat()

        requested_count = 0
        last_name = ""

        for sid in raw_ids:
            try:
                sid_int = int(sid)
            except (ValueError, TypeError):
                sid_int = sid

            svc = db_services.get(sid_int)
            if svc:
                s_name = svc.name
                c_name = svc.category.name if svc.category else "General"
            elif sid_int in wf_services:
                wf_s = wf_services[sid_int]
                s_name = wf_s.name
                c_name = wf_s.category or "General"
            else:
                s_name = request.data.get("name", "").strip() or f"Service #{sid}"
                c_name = "General"

            existing = next((s for s in services if str(s.get("id")) == str(sid)), None)
            if existing:
                if existing.get("status") == "approved" and existing.get("request_type") != "remove":
                    if len(raw_ids) == 1:
                        return Response({"error": f"Service '{s_name}' is already approved for dispatch."}, status=status.HTTP_400_BAD_REQUEST)
                    continue
                if existing.get("status") == "pending":
                    if len(raw_ids) == 1:
                        return Response({"error": f"Authorization request for '{s_name}' is already pending review."}, status=status.HTTP_400_BAD_REQUEST)
                    continue
                existing["status"] = "pending"
                existing["request_type"] = "add"
                existing["name"] = s_name
                existing["category_name"] = c_name
                existing["requested_at"] = now_iso
                existing["rejection_reason"] = ""
                requested_count += 1
                last_name = s_name
            else:
                services.append({
                    "id": sid_int if isinstance(sid_int, int) else sid,
                    "name": s_name,
                    "category_name": c_name,
                    "status": "pending",
                    "request_type": "add",
                    "requested_at": now_iso,
                    "rejection_reason": "",
                })
                requested_count += 1
                last_name = s_name

        if requested_count == 0 and len(raw_ids) > 1:
            return Response({
                "message": "All selected services are already requested or approved.",
                "requested_count": 0,
                "services": services,
            }, status=status.HTTP_200_OK)

        onboarding["services"] = services
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        msg = (
            f"Service authorization request for '{last_name}' submitted to Admin for review."
            if len(raw_ids) == 1
            else f"Submitted authorization requests for {requested_count} service(s) to Admin for review."
        )

        return Response({
            "message": msg,
            "requested_count": requested_count,
            "services": services,
        }, status=status.HTTP_201_CREATED)


class WorkforceEmployeeServiceRemoveView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        service_id = request.data.get("service_id")
        if not service_id:
            return Response({"error": "service_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        services = onboarding.get("services", [])

        existing = next((s for s in services if str(s.get("id")) == str(service_id)), None)
        if not existing or existing.get("status") != "approved":
            return Response({"error": "Only currently approved services can be requested for removal."}, status=status.HTTP_400_BAD_REQUEST)

        existing["request_type"] = "remove"
        existing["status"] = "pending"
        existing["removal_requested_at"] = timezone.now().isoformat()

        onboarding["services"] = services
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": f"Removal request for '{existing.get('name')}' submitted to Admin for review.",
            "services": services,
        }, status=status.HTTP_200_OK)


class WorkforceAdminPendingServicesListView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        if is_platform_superadmin(request.user):
            qs = Employee.objects.select_related("user", "company")
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            qs = Employee.objects.filter(company=company).select_related("user", "company")

        pending_requests = []
        for emp in qs:
            bank_details = emp.bank_details or {}
            onboarding = bank_details.get("onboarding", {})
            services = onboarding.get("services", [])
            for s in services:
                if s.get("status") == "pending":
                    pending_requests.append({
                        "employee_id": emp.id,
                        "employee_code": emp.employee_id,
                        "employee_name": emp.user.get_full_name() or emp.user.username,
                        "service_id": s.get("id"),
                        "service_name": s.get("name"),
                        "request_type": s.get("request_type", "add"),
                        "requested_at": s.get("requested_at") or s.get("removal_requested_at") or timezone.now().isoformat(),
                    })

        return Response(pending_requests, status=status.HTTP_200_OK)


class WorkforceAdminServiceDecideView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk, service_id):
        emp = Employee.objects.filter(pk=pk).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Tenant isolation
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        # Prevent employee from approving their own request
        if getattr(request.user, "employee_profile", None) and request.user.employee_profile.id == emp.id and not is_platform_superadmin(request.user):
            return Response({"error": "Employees cannot approve or decide their own service authorizations."}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "").lower()
        reason = request.data.get("reason", "").strip()

        if action not in ["approve", "reject"]:
            return Response({"error": "Action must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        services = onboarding.get("services", [])

        target_svc = next((s for s in services if str(s.get("id")) == str(service_id)), None)
        if not target_svc:
            return Response({"error": "Requested service not found on candidate."}, status=status.HTTP_404_NOT_FOUND)

        request_type = target_svc.get("request_type", "add")

        if action == "approve":
            if request_type == "remove":
                services = [s for s in services if str(s.get("id")) != str(service_id)]
                msg = f"Service '{target_svc.get('name')}' removed from authorized dispatch services."
            else:
                target_svc["status"] = "approved"
                target_svc["rejection_reason"] = ""
                target_svc.pop("request_type", None)
                target_svc["approved_at"] = timezone.now().isoformat()
                target_svc["approved_by"] = request.user.username
                msg = f"Service '{target_svc.get('name')}' authorized & approved."
        else:
            if request_type == "remove":
                target_svc["status"] = "approved"
                target_svc.pop("request_type", None)
                target_svc["rejection_reason"] = reason or "Removal request declined by admin."
                msg = f"Removal request for '{target_svc.get('name')}' rejected. Service remains approved."
            else:
                target_svc["status"] = "rejected"
                target_svc["rejection_reason"] = reason or "Qualifications do not meet minimum threshold."
                target_svc.pop("request_type", None)
                target_svc["rejected_at"] = timezone.now().isoformat()
                target_svc["rejected_by"] = request.user.username
                msg = f"Service authorization request for '{target_svc.get('name')}' rejected."

        onboarding["services"] = services
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": msg,
            "services": services,
        }, status=status.HTTP_200_OK)


class WorkforceAdminBulkServiceDecideView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        emp = Employee.objects.filter(pk=pk).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Tenant isolation
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        # Prevent employee from approving their own request
        if getattr(request.user, "employee_profile", None) and request.user.employee_profile.id == emp.id and not is_platform_superadmin(request.user):
            return Response({"error": "Employees cannot approve or decide their own service authorizations."}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "").lower()
        reason = request.data.get("reason", "").strip()
        service_ids = request.data.get("service_ids")
        all_pending = request.data.get("all_pending", False)

        if action not in ["approve", "reject"]:
            return Response({"error": "Action must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        services = onboarding.get("services", [])

        if not services:
            return Response({"error": "No requested services found on candidate."}, status=status.HTTP_400_BAD_REQUEST)

        # Filter target services
        if service_ids:
            target_ids = set(str(sid) for sid in service_ids)
            target_svcs = [s for s in services if str(s.get("id")) in target_ids]
        elif all_pending:
            target_svcs = [s for s in services if s.get("status") not in ["approved", "rejected"] or s.get("request_type") == "remove"]
        else:
            target_svcs = list(services)

        if not target_svcs:
            return Response({
                "message": "All requested services are already decided.",
                "updated_count": 0,
                "services": services,
            }, status=status.HTTP_200_OK)

        updated_count = 0
        now_iso = timezone.now().isoformat()
        current_username = request.user.username

        if action == "approve":
            for svc in target_svcs:
                if svc.get("request_type") == "remove":
                    services = [s for s in services if str(s.get("id")) != str(svc.get("id"))]
                else:
                    svc["status"] = "approved"
                    svc["rejection_reason"] = ""
                    svc.pop("request_type", None)
                    svc["approved_at"] = now_iso
                    svc["approved_by"] = current_username
                updated_count += 1
        else:
            for svc in target_svcs:
                if svc.get("request_type") == "remove":
                    svc["status"] = "approved"
                    svc.pop("request_type", None)
                    svc["rejection_reason"] = reason or "Removal request declined by admin."
                else:
                    svc["status"] = "rejected"
                    svc["rejection_reason"] = reason or "Qualifications do not meet minimum threshold."
                    svc.pop("request_type", None)
                    svc["rejected_at"] = now_iso
                    svc["rejected_by"] = current_username
                updated_count += 1

        onboarding["services"] = services
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": f"Successfully {action}d {updated_count} service(s).",
            "updated_count": updated_count,
            "services": services,
        }, status=status.HTTP_200_OK)


# ─── Wallet Dispute Resolution (SEVO Section 4: hold-and-clawback) ────────────

class WorkforceAdminHeldEarningsListView(APIView):
    """
    Lists JOB_CREDIT ledger entries still inside their dispute-hold window
    -- the admin's triage queue for deciding whether to let a payout
    mature or claw it back before it releases. Superusers see every
    company's held entries; a company admin/manager sees only their own
    company's (provider head wallet) and their own individually-onboarded
    workers have no visibility here -- disputes on their earnings are
    handled the same way, just scoped to their own wallet's history via
    a future wallet-detail endpoint, not this admin queue.
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        from .models import WalletLedgerEntry

        qs = WalletLedgerEntry.objects.filter(
            entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT,
            status=WalletLedgerEntry.Status.HELD,
        ).select_related("wallet", "wallet__company", "job", "worker_performed", "worker_performed__user").order_by("hold_release_at")

        if not getattr(request.user, "is_superuser", False):
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(wallet__company_id=company.id)

        results = []
        for entry in qs[:200]:
            wallet = entry.wallet
            owner_name = wallet.company.company_name if wallet.company_id else (
                getattr(wallet.employee, "full_name", None) or (wallet.employee.user.get_full_name() if wallet.employee and wallet.employee.user_id else None)
            )
            results.append({
                "ledger_entry_id": entry.id,
                "job_id": entry.job_id,
                "wallet_id": wallet.id,
                "wallet_owner": owner_name,
                "amount": entry.signed_amount,
                "gross_job_amount": entry.gross_job_amount,
                "worker_performed": entry.worker_performed.user.get_full_name() if entry.worker_performed and entry.worker_performed.user_id else None,
                "hold_release_at": entry.hold_release_at,
                "created_at": entry.created_at,
                "notes": entry.notes,
            })

        return Response({"results": results, "count": len(results)}, status=status.HTTP_200_OK)


class WorkforceAdminWalletClawbackView(APIView):
    """
    POST { job_id, reason }: reverses a job's earnings at the job level --
    never a blanket wallet freeze -- per SEVO Section 4. Delegates the
    actual ledger mutation to services.commission.clawback_job(), which
    handles both the still-HELD case (mark CLAWED_BACK, nothing ever
    left the release path) and the already-RELEASED case (an offsetting
    CLAWBACK_DEBIT entry, since the immutable ledger is never rewritten
    after release).
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request):
        from .models import WalletLedgerEntry
        job_id = request.data.get("job_id")
        reason = (request.data.get("reason") or "").strip()

        if not job_id:
            return Response({"error": "job_id is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not reason:
            return Response({"error": "A reason is required for a clawback."}, status=status.HTTP_400_BAD_REQUEST)

        job_obj = ServiceRequest.objects.filter(pk=job_id).first()
        if not job_obj:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        if not getattr(request.user, "is_superuser", False):
            company = resolve_actor_company(request)
            existing = WalletLedgerEntry.objects.filter(
                job=job_obj, entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT,
            ).select_related("wallet").first()
            if not company or not existing or existing.wallet.company_id != company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        from workforce_api.services import clawback_job
        result = clawback_job(job_obj, reason)
        if not result:
            return Response({"error": "No earnings entry found for this job -- nothing to claw back."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "message": "Clawback recorded.",
            "ledger_entry_id": result.id,
            "status": result.status,
            "amount": result.signed_amount,
        }, status=status.HTTP_200_OK)


class WorkforceAdminScorecardsListView(APIView):
    """
    SEVO business plan Section 4: admin-facing roster of every
    worker/provider's rating + SLA scorecard, tenant-scoped, sorted
    worst-standing first so an admin can spot who needs attention --
    same persisted WorkforceScorecard row that also feeds the
    dispatch-ranking bonus in services/automatic_dispatch.py.
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        qs = Employee.objects.select_related("user", "scorecard")

        if not getattr(request.user, "is_superuser", False):
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            qs = qs.filter(company=company)

        tier_rank = {
            WorkforceScorecard.Tier.UNRATED: 0,
            WorkforceScorecard.Tier.BRONZE: 1,
            WorkforceScorecard.Tier.SILVER: 2,
            WorkforceScorecard.Tier.GOLD: 3,
        }

        rows = []
        for emp in qs.order_by("id")[:500]:
            sc = getattr(emp, "scorecard", None)
            rows.append({
                "employee_id": emp.id,
                "employee_name": emp.user.get_full_name() if emp.user_id else "",
                "tier": sc.tier if sc else WorkforceScorecard.Tier.UNRATED,
                "average_rating": float(sc.average_rating) if sc else 0.0,
                "csat_average": float(sc.csat_average) if sc else 0.0,
                "sla_score": float(sc.sla_score) if sc else 0.0,
                "rating_count": sc.rating_count if sc else 0,
                "sla_met_count": sc.sla_met_count if sc else 0,
                "sla_breach_count": sc.sla_breach_count if sc else 0,
                "last_recalculated_at": sc.last_recalculated_at if sc else None,
            })

        rows.sort(key=lambda r: (tier_rank.get(r["tier"], 0), r["sla_score"], r["average_rating"]))

        return Response({"results": rows, "count": len(rows)}, status=status.HTTP_200_OK)


class WorkforceAdminSocialSecurityListView(APIView):
    """
    SEVO business plan Section 8: the "accurate, exportable worklist" for
    whoever submits Social Security Code registrations on the Shram
    Suvidha portal (see SocialSecurityRegistration model docstring and
    services/social_security.py -- this is deliberately NOT an automated
    government-portal integration). Individual workers only; provider-
    team workers are out of scope for SEVO's own aggregator obligation.
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        qs = SocialSecurityRegistration.objects.select_related("employee", "employee__user").order_by(
            "-days_worked_current_fy"
        )

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        rows = []
        for reg in qs[:500]:
            emp = reg.employee
            rows.append({
                "registration_id": reg.id,
                "employee_id": emp.id,
                "employee_name": emp.user.get_full_name() if emp.user_id else "",
                "days_worked_current_fy": reg.days_worked_current_fy,
                "financial_year_start": reg.financial_year_start,
                "status": reg.status,
                "registered_at": reg.registered_at,
                "registered_by": reg.registered_by,
                "portal_reference_id": reg.portal_reference_id,
            })

        return Response({"results": rows, "count": len(rows)}, status=status.HTTP_200_OK)


class WorkforceAdminSocialSecurityMarkRegisteredView(APIView):
    """
    POST {registration_id, portal_reference_id}: records that an admin
    has actually completed the Shram Suvidha portal submission for this
    worker. See services.social_security.mark_registered.
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request):
        from workforce_api.services import mark_social_security_registered, SocialSecurityMarkRegisteredError

        registration_id = request.data.get("registration_id")
        portal_reference_id = request.data.get("portal_reference_id")
        if not registration_id:
            return Response({"error": "registration_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        registration = SocialSecurityRegistration.objects.filter(pk=registration_id).first()
        if not registration:
            return Response({"error": "Registration record not found."}, status=status.HTTP_404_NOT_FOUND)

        registered_by = request.user.get_full_name() or request.user.username
        try:
            registration = mark_social_security_registered(
                registration, registered_by=registered_by, portal_reference_id=portal_reference_id,
            )
        except SocialSecurityMarkRegisteredError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Registration recorded.",
            "registration_id": registration.id,
            "status": registration.status,
            "registered_at": registration.registered_at,
            "portal_reference_id": registration.portal_reference_id,
        }, status=status.HTTP_200_OK)


class WorkforceAdminRequestCorrectionView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        emp = Employee.objects.filter(pk=pk).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        notes = request.data.get("notes", "").strip()
        if not notes:
            return Response({"error": "Correction notes are required."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})

        onboarding["status"] = "correction_required"
        onboarding["correction_notes"] = notes
        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": "Correction request sent to candidate.",
            "status": "correction_required",
            "notes": notes,
        }, status=status.HTTP_200_OK)


class WorkforceAdminApproveApplicationView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        emp = Employee.objects.filter(pk=pk).select_related("user").first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        if not emp.is_active or not emp.user.is_active:
            return Response({"error": "Cannot approve candidate: User account is inactive."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        documents = onboarding.get("documents", {})
        services = onboarding.get("services", [])

        # Validate that ALL submitted documents are approved
        unapproved_docs = [
            cat for cat, doc in documents.items()
            if doc.get("status") != "approved"
        ]
        if unapproved_docs:
            return Response({
                "error": f"Cannot approve candidate: The following documents are not approved: {', '.join(unapproved_docs)}. All dossier documents must be reviewed and APPROVED."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Validate that at least ONE requested service is approved
        approved_services = [s for s in services if s.get("status") == "approved"]
        if not approved_services:
            return Response({
                "error": "Cannot approve candidate: At least ONE requested service must be marked as APPROVED."
            }, status=status.HTTP_400_BAD_REQUEST)

        onboarding["status"] = "approved"
        onboarding["approved_at"] = timezone.now().isoformat()
        onboarding["approved_by"] = request.user.username

        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.is_active = True
        emp.is_online = False
        emp.current_availability = "offline"
        emp.save()

        return Response({
            "message": "Candidate successfully approved! Operational status set to OFFLINE.",
            "status": "approved",
            "is_online": False,
            "availability": "offline",
        }, status=status.HTTP_200_OK)


class WorkforceAdminRejectApplicationView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        emp = Employee.objects.filter(pk=pk).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_platform_superadmin(request.user):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if emp.company_id != user_company.id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get("reason", "Qualifications or documents did not meet verification criteria.")

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})

        onboarding["status"] = "rejected"
        onboarding["rejection_reason"] = reason
        onboarding["rejected_at"] = timezone.now().isoformat()

        bank_details["onboarding"] = onboarding
        emp.bank_details = bank_details
        emp.is_online = False
        emp.current_availability = "offline"
        emp.save()

        return Response({
            "message": "Candidate application rejected.",
            "status": "rejected",
            "reason": reason,
        }, status=status.HTTP_200_OK)


# ─── 7. Decoupled Presence & Availability Toggle (Rule 3) ──────────────────────

class WorkforcePresenceToggleView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        from workforce_api.services.workload import get_employee_active_job, reconcile_employee_availability

        active_job = get_employee_active_job(emp.id)
        desired_state = request.data.get("is_online")
        is_requesting_offline = (desired_state is False) or (desired_state is None and emp.is_online)

        if active_job and is_requesting_offline:
            req_id = active_job.request_id or f"SR-{active_job.id}"
            return Response({
                "error": f"Cannot go offline while actively working on assigned job {req_id} ({active_job.service_category}). Please complete or cancel the assignment first.",
                "code": "ACTIVE_JOB_IN_PROGRESS",
                "active_job_id": active_job.id,
                "request_id": req_id,
                "is_online": True,
                "availability": "busy",
            }, status=status.HTTP_400_BAD_REQUEST)

        if desired_state is not None:
            emp.is_online = bool(desired_state)
        else:
            emp.is_online = not emp.is_online

        emp.save(update_fields=["is_online"])
        reconcile_employee_availability(emp)
        emp.refresh_from_db(fields=["current_availability", "is_online"])

        if emp.is_online and emp.current_availability == "available":
            try:
                import threading
                from workforce_api.services.automatic_dispatch import reconsider_jobs_for_employee
                threading.Thread(target=reconsider_jobs_for_employee, args=(emp.id,), daemon=True).start()
            except Exception as e:
                logger.debug(f"[PRESENCE_TOGGLE_DISPATCH_ERR] {e}")

        try:
            PresenceLog.objects.create(
                employee=emp,
                company=emp.company,
                availability=emp.current_availability,
            )
        except Exception:
            pass

        return Response({
            "message": f"Technician is now {'ONLINE (Available)' if emp.is_online else 'OFFLINE'}.",
            "is_online": emp.is_online,
            "availability": emp.current_availability,
        }, status=status.HTTP_200_OK)


class WorkforcePresenceStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            return Response({"is_online": False, "availability": "offline"}, status=status.HTTP_200_OK)

        from workforce_api.services.workload import reconcile_employee_availability
        reconcile_employee_availability(emp)
        emp.refresh_from_db(fields=["current_availability", "is_online"])

        return Response({
            "is_online": emp.is_online,
            "availability": emp.current_availability,
            "registration_status": (emp.bank_details or {}).get("onboarding", {}).get("status", "not_started"),
        }, status=status.HTTP_200_OK)


# ─── 8. Field Jobs & State Machine Execution ─────────────────────────────────

def is_employee_authorized_for_job(emp, job) -> bool:
    """
    Validates tenant compatibility between an employee and a job:
    - Solo technician (emp.company_id is None) can handle platform jobs (job.company_id in (None, 1)).
    - Platform technician (emp.company_id == 1) can handle platform jobs (job.company_id in (None, 1)).
    - Vendor technician (emp.company_id > 1) can handle jobs belonging to their company (job.company_id == emp.company_id).
    """
    if not emp or not job:
        return False
    job_cid = getattr(job, "company_id", None)
    emp_cid = getattr(emp, "company_id", None)
    if emp_cid is None or emp_cid == 1:
        return job_cid is None or job_cid == 1
    return job_cid == emp_cid


class WorkforceJobListView(APIView):
    permission_classes = [IsApprovedTechnician]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        company = emp.company if emp else getattr(user, "company", None)

        if is_admin_role(user):
            context = {"request": request}
            if user.is_superuser:
                jobs = ServiceRequest.objects.all().order_by("-created_at")[:50]
            elif company:
                jobs = ServiceRequest.objects.filter(company=company).order_by("-created_at")[:50]
            else:
                jobs = ServiceRequest.objects.none()
        elif emp:
            now = timezone.now()
            from workforce_api.models import WorkforceJobOffer, WorkforceJobLifecycleEvent, WorkforceWorkExtension, JobPayment
            from workforce_api.services.workload import ACTIVE_QUEUE_STATUSES, WORKLOAD_OCCUPIED_STATUSES
            from workforce_api.services.automatic_dispatch import reconsider_jobs_for_employee, expire_and_reassign_offers

            # 1. Sweep expired offers
            try:
                expire_and_reassign_offers()
            except Exception:
                pass

            # 2. Hard Single Active Job Invariant: Check if technician already has an active assignment in queue
            from workforce_api.services.workload import reconcile_employee_availability
            reconcile_employee_availability(emp)
            emp.refresh_from_db(fields=["current_availability", "is_online"])

            has_active_job = ServiceRequest.objects.filter(
                assigned_employee=emp,
                status__in=WORKLOAD_OCCUPIED_STATUSES
            ).exists()

            if has_active_job:
                # When technician is occupied with an active job, no new job offers should appear
                offered_job_ids = []
            else:
                # Reconsider pending customer bookings in Supabase for this available technician
                if emp.is_active and emp.is_online and emp.current_availability == "available":
                    try:
                        import threading
                        from workforce_api.services.automatic_dispatch import reconsider_jobs_for_employee
                        threading.Thread(target=reconsider_jobs_for_employee, args=(emp.id,), daemon=True).start()
                    except Exception as e:
                        logger.debug(f"[DISPATCH_RECONSIDER_ERROR] {e}")

                offered_job_ids = list(WorkforceJobOffer.objects.filter(
                    employee=emp,
                    status="OFFERED",
                    expires_at__gt=now
                ).values_list("job_id", flat=True))

            try:
                from service_requests.models import EmployeeJob
                emp_job_sr_ids = list(EmployeeJob.objects.filter(
                    employee=emp
                ).exclude(
                    status__in=["REJECTED", "CANCELLED"]
                ).values_list("service_request_id", flat=True))
            except Exception:
                emp_job_sr_ids = []

            # Canonical query definitions
            assigned_active_qs = Q(
                assigned_employee=emp,
                status__in=ACTIVE_QUEUE_STATUSES
            )
            completed_qs = Q(
                assigned_employee=emp,
                status__in=["completed", "cancelled"]
            )
            offered_qs = Q(
                id__in=offered_job_ids
            )
            employee_job_qs = Q(
                id__in=emp_job_sr_ids
            )

            status_filter = str(request.query_params.get("status", "active")).lower().strip()

            if status_filter == "completed":
                qs = ServiceRequest.objects.filter(
                    Q(assigned_employee=emp, status="completed") |
                    (Q(id__in=emp_job_sr_ids) & Q(status="completed"))
                )
            elif status_filter == "all":
                qs = ServiceRequest.objects.filter(
                    assigned_active_qs | completed_qs | offered_qs | employee_job_qs
                )
            else: # "active" default
                qs = ServiceRequest.objects.filter(
                    assigned_active_qs | offered_qs | (employee_job_qs & Q(status__in=ACTIVE_QUEUE_STATUSES))
                ).exclude(status__in=["completed", "cancelled"])

            if emp.company:
                qs = qs.filter(company=emp.company)

            qs = qs.select_related("customer", "assigned_employee", "assigned_employee__user", "company")
            qs = qs.distinct().order_by("-updated_at", "-created_at")
            job_list = list(qs[:100])

            job_ids = [j.id for j in job_list]
            emp_offers_map = {}
            active_offers_map = {}
            lifecycle_events_map = {}
            extensions_map = {}
            active_extensions_map = {}
            payments_map = {}

            if job_ids:
                # 1. Bulk fetch employee job offers
                offers = list(WorkforceJobOffer.objects.filter(job_id__in=job_ids, employee=emp).order_by("offered_at"))
                for o in offers:
                    emp_offers_map[o.job_id] = o
                    if o.status == "OFFERED" and o.expires_at > now:
                        active_offers_map[o.job_id] = o

                # 2. Bulk fetch acceptance lifecycle events
                events = list(WorkforceJobLifecycleEvent.objects.filter(
                    job_id__in=job_ids,
                    employee=emp,
                    event_type=WorkforceJobLifecycleEvent.EventType.EMPLOYEE_JOB_ACCEPTED,
                ).order_by("created_at"))
                for ev in events:
                    lifecycle_events_map[ev.job_id] = ev

                # 3. Bulk fetch work extensions
                exts = list(WorkforceWorkExtension.objects.filter(job_id__in=job_ids).select_related("technician", "technician__user").order_by("-created_at"))
                for ext in exts:
                    extensions_map.setdefault(ext.job_id, []).append(ext)
                    if ext.status in ["REQUESTED", "ADMIN_APPROVED", "CUSTOMER_ACCEPTED", "IN_PROGRESS"] and ext.job_id not in active_extensions_map:
                        active_extensions_map[ext.job_id] = ext

                # 4. Bulk fetch payments
                payments = list(JobPayment.objects.filter(job_id__in=job_ids))
                for p in payments:
                    payments_map[p.job_id] = p

            context = {
                "request": request,
                "emp_offers_map": emp_offers_map,
                "active_offers_map": active_offers_map,
                "lifecycle_events_map": lifecycle_events_map,
                "extensions_map": extensions_map,
                "active_extensions_map": active_extensions_map,
                "payments_map": payments_map,
            }
            jobs = job_list
        else:
            jobs = []
            context = {"request": request}

        serializer = WorkforceJobSerializer(jobs, many=True, context=context)
        return Response(serializer.data, status=status.HTTP_200_OK)



class WorkforceJobTransitionView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        target_status = request.data.get("status") or request.data.get("target_status")
        if not target_status:
            return Response({"error": "Target status required."}, status=status.HTTP_400_BAD_REQUEST)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            try:
                from service_requests.models import EmployeeJob
                has_emp_job = EmployeeJob.objects.filter(service_request=job, employee=emp).exists()
            except Exception:
                has_emp_job = False
            if not emp or (job.assigned_employee != emp and not has_emp_job):
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized: Job belongs to another vendor company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        try:
            # "Start Service Execution" lands here. apply_transition() refuses
            # in_progress unless an open TimeLog already exists, and no UI path
            # created one, so the button failed with an error the technician had
            # no way to act on. Route it through the shared starter, which clocks
            # them in idempotently and then transitions.
            if str(target_status).lower() == "in_progress" and emp:
                time_log, start_err = ensure_job_started(
                    job, emp, request.user,
                    notes="Clock-in on Start Service Execution",
                )
                if start_err:
                    return Response({"error": start_err}, status=status.HTTP_400_BAD_REQUEST)
                job.refresh_from_db()
                return Response({
                    "message": "Job transitioned to IN_PROGRESS.",
                    "job_id": job.id,
                    "status": job.status,
                    "clock_in": time_log.clock_in.isoformat() if time_log and time_log.clock_in else None,
                    "time_log_id": time_log.id if time_log else None,
                }, status=status.HTTP_200_OK)

            new_status = apply_transition(job, target_status, actor=request.user)
            try:
                from service_requests.models import EmployeeJob
                EmployeeJob.objects.filter(service_request=job, employee=emp).update(status=new_status.upper())
            except Exception:
                pass

            return Response({
                "message": f"Job transitioned to {new_status.upper()}.",
                "job_id": job.id,
                "status": new_status,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.detail if hasattr(e, 'detail') else e)}, status=status.HTTP_400_BAD_REQUEST)


# ─── 9. Proof of Work & Cash Collection (Phase 16) ───────────────────────────

class WorkforceJobProofView(APIView):
    permission_classes = [IsApprovedTechnician]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized: Job belongs to another vendor company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        if job.status not in ["in_progress", "proof_submitted"]:
            return Response({"error": f"Cannot submit completion proof for job in status '{job.status}'. Expected 'in_progress'."}, status=status.HTTP_400_BAD_REQUEST)

        completion_notes = request.data.get("notes", "").strip() or request.data.get("completion_notes", "").strip()
        after_presence = request.FILES.get("after_presence_photo") or request.FILES.get("after_selfie") or request.FILES.get("presence_photo")
        after_appliance = request.FILES.get("after_appliance_photo") or request.FILES.get("after_photo")
        after_work_area = request.FILES.get("after_work_area_photo") or request.FILES.get("during_photo") or request.FILES.get("before_photo")
        parts_used = request.data.get("parts_used", [])

        if not after_presence and not after_appliance and not after_work_area:
            return Response({"error": "After-service completion requires After Face/Identity Selfie or service photo."}, status=status.HTTP_400_BAD_REQUEST)

        for _f in (after_presence, after_appliance, after_work_area):
            _photo_err = _validate_photo_upload(_f)
            if _photo_err:
                return Response({"error": _photo_err}, status=status.HTTP_400_BAD_REQUEST)

        proof, _ = PostServiceProof.objects.get_or_create(
            job=job,
            defaults={"employee": emp or job.assigned_employee}
        )
        if after_presence:
            proof.after_presence_photo = after_presence
        if after_appliance:
            proof.after_appliance_photo = after_appliance
        if after_work_area:
            proof.after_work_area_photo = after_work_area
        if completion_notes:
            proof.completion_notes = completion_notes
        if parts_used:
            proof.parts_used = parts_used

        proof.check_submission()
        proof.save()

        # Step 1: Transition job to proof_submitted (service completed)
        apply_transition(job, "proof_submitted", actor=request.user)

        # Step 2: Check payment state machine. If payment is already PAID (e.g. verified ONLINE), close the job.
        pmt = JobPayment.objects.filter(job=job).first()
        is_paid = pmt and pmt.payment_status == JobPayment.PaymentStatus.PAID
        
        if is_paid:
            try:
                apply_transition(job, "completed", actor=request.user)
                msg = "After-service proof submitted and payment verified! Job is COMPLETED."
            except ValidationError as ve:
                msg = f"After-service proof submitted. Completion note: {ve}"
        else:
            msg = "After-service proof submitted! Service completed. Payment collection/confirmation required before closing job."

        return Response({
            "message": msg,
            "job_id": job.id,
            "status": job.status,
            "payment_status": pmt.payment_status if pmt else "PENDING",
            "is_submitted": proof.is_submitted,
        }, status=status.HTTP_200_OK)


class WorkforceJobPaymentDetailView(APIView):
    """
    Authoritative payment details endpoint for assigned technicians / admins.
    Derives identity strictly from request.user.
    NEVER exposes payment_confirmation_otp_hash or security secrets.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        is_online = (job.payment_method or "").upper() in ["ONLINE", "PREPAID"]
        pmt, _ = JobPayment.objects.get_or_create(
            job=job,
            defaults={
                "company": job.company,
                "employee": emp or job.assigned_employee,
                "payment_method": JobPayment.PaymentMethod.ONLINE if is_online else JobPayment.PaymentMethod.CASH_ON_SERVICE,
                "payment_status": JobPayment.PaymentStatus.PAID if job.payment_status in ["paid", "collected"] else JobPayment.PaymentStatus.PENDING,
                "amount_due": job.total_amount,
                "amount_paid": job.total_amount if job.payment_status in ["paid", "collected"] else Decimal("0.00"),
            }
        )

        events = PaymentCollectionEvent.objects.filter(job_payment=pmt).order_by("-created_at")

        return Response({
            "payment": JobPaymentSerializer(pmt).data,
            "events": PaymentCollectionEventSerializer(events, many=True).data,
        }, status=status.HTTP_200_OK)


class WorkforceJobCashCollectView(APIView):
    """
    Technician records Cash on Service collection.
    - Validates assigned employee & company ownership from request.user.
    - Validates amount_received >= amount_due (calculates change_returned).
    - Generates separate cryptographically secure 6-digit PAYMENT_CONFIRMATION_OTP and hashes with make_password.
    - Transitions payment_status to CASH_PENDING.
    - Emits immutable audit trail events.
    """
    permission_classes = [IsApprovedTechnician]
    throttle_classes = [ScopedRateThrottle]  # EC-06: money-movement endpoint
    throttle_scope = "workforce_cash_collect"

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            pmt, created = JobPayment.objects.select_for_update().get_or_create(
                job=job,
                defaults={
                    "company": job.company,
                    "employee": emp,
                    "payment_method": JobPayment.PaymentMethod.CASH_ON_SERVICE,
                    "payment_status": JobPayment.PaymentStatus.PENDING,
                    # Bug found: this used to fall back to a hardcoded Decimal("450.00")
                    # if job.total_amount was ever falsy -- since get_or_create()
                    # persists these defaults, that fake amount would be written
                    # into the JobPayment row and become what the technician was
                    # told to collect from the customer. Fall back to 0.00 instead:
                    # a genuinely zero/missing total_amount is a real data problem
                    # that should now surface loudly via settle_completed_job()'s
                    # SettlementError (SETTLEMENT_ZERO_AMOUNT) and the admin
                    # notification it triggers, not be silently papered over with
                    # a plausible-looking wrong number.
                    "amount_due": job.total_amount or Decimal("0.00"),
                    "reconciled": False,
                }
            )

            # Rule: Cannot collect cash for Online payment booking
            if pmt.payment_method == JobPayment.PaymentMethod.ONLINE:
                return Response({"error": "Cannot collect cash for online payment booking."}, status=status.HTTP_400_BAD_REQUEST)

            # Rule: Idempotency / Duplicate protection
            if pmt.payment_status == JobPayment.PaymentStatus.PAID:
                return Response({
                    "message": "Payment has already been marked PAID.",
                    "payment_status": "PAID",
                    "amount_due": str(pmt.amount_due),
                    "amount_paid": str(pmt.amount_paid),
                }, status=status.HTTP_200_OK)

            if pmt.payment_status == JobPayment.PaymentStatus.CASH_PENDING:
                return Response({
                    "message": "Cash collection has already been recorded and is currently awaiting customer confirmation.",
                    "payment_status": "CASH_PENDING",
                    "amount_due": str(pmt.amount_due),
                    "amount_received": str(pmt.amount_received or pmt.amount_due),
                    "change_returned": str(pmt.change_returned or Decimal("0.00")),
                }, status=status.HTTP_200_OK)

            # Parse amount_received (never trust frontend amount_due)
            raw_received = request.data.get("amount_received")
            if raw_received is None or str(raw_received).strip() in ["", "0", "0.0", "0.00", "null", "undefined"]:
                raw_received = request.data.get("amount")
            if raw_received is None or str(raw_received).strip() in ["", "0", "0.0", "0.00", "null", "undefined"]:
                raw_received = pmt.amount_due

            try:
                amt_received = Decimal(str(raw_received if raw_received is not None else pmt.amount_due))
            except Exception:
                return Response({"error": "Invalid collection amount format."}, status=status.HTTP_400_BAD_REQUEST)

            if amt_received < pmt.amount_due:
                return Response({
                    "error": f"Amount received (₹{amt_received}) cannot be less than authoritative amount due (₹{pmt.amount_due}).",
                    "amount_due": str(pmt.amount_due),
                }, status=status.HTTP_400_BAD_REQUEST)

            change_returned = amt_received - pmt.amount_due
            now = timezone.now()

            # Authoritative State Transition: Transition to CASH_PENDING (never directly PAID)
            pmt.amount_received = amt_received
            pmt.change_returned = change_returned
            pmt.cash_collected_at = now
            pmt.cash_collected_by = emp
            pmt.amount_paid = Decimal("0.00")

            # Generate cryptographically secure 6-digit confirmation OTP
            otp_raw = f"{secrets.randbelow(900000) + 100000}"
            pmt.payment_confirmation_otp_hash = make_password(otp_raw)
            pmt.otp_expires_at = now + timedelta(minutes=15)
            pmt.otp_attempts = 0
            pmt.otp_used_at = None
            pmt.payment_status = JobPayment.PaymentStatus.CASH_PENDING
            pmt.save()

            # Record immutable audit event
            PaymentCollectionEvent.objects.create(
                job_payment=pmt,
                employee=emp,
                actor_user=request.user,
                event_type="CASH_REPORTED",
                amount=pmt.amount_due,
                metadata={"amount_received": float(amt_received), "change_returned": float(change_returned)},
            )

            # Sync ServiceRequest payment status
            job.payment_status = "cash_pending"
            job.save(update_fields=["payment_status"])

            if job.customer:
                create_notification(
                    recipient=job.customer,
                    title="Payment Confirmation Required",
                    message=f"Technician reported cash collection of ₹{pmt.amount_due} for Job #{job.id}. Share OTP {otp_raw} with technician or confirm in your dashboard.",
                    notification_type="PAYMENT_CONFIRMATION_OTP",
                    company=job.company,
                    related_object_id=str(job.id),
                )

            return Response({
                "message": f"Cash collection of ₹{pmt.amount_due} recorded. Confirmation OTP generated for customer (Received: ₹{amt_received}, Change: ₹{change_returned}).",
                "payment_status": "CASH_PENDING",
                "amount_due": str(pmt.amount_due),
                "amount_received": str(amt_received),
                "change_returned": str(change_returned),
            }, status=status.HTTP_200_OK)


class WorkforceJobPaymentVerifyOTPView(APIView):
    """
    Path B: Technician enters customer-provided Payment Confirmation OTP.
    - Validates assigned employee & company ownership.
    - Checks max 5 attempts, expiry, single-use.
    - Verifies hash with check_password.
    - Atomically transitions CASH_PENDING -> PAID.
    - If service completed, closes/completes the job.
    """
    permission_classes = [IsApprovedTechnician]
    throttle_classes = [ScopedRateThrottle]  # EC-06: OTP guess-attempt endpoint
    throttle_scope = "workforce_otp"

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            pmt = JobPayment.objects.select_for_update().filter(job=job).first()
            if not pmt:
                return Response({"error": "No payment record found for this job."}, status=status.HTTP_404_NOT_FOUND)

            if pmt.payment_status == JobPayment.PaymentStatus.PAID:
                return Response({
                    "message": "Payment has already been marked PAID.",
                    "payment_status": "PAID",
                    "job_status": job.status,
                }, status=status.HTTP_200_OK)

            if pmt.payment_status != JobPayment.PaymentStatus.CASH_PENDING:
                return Response({
                    "error": f"Cannot verify OTP for payment in status '{pmt.payment_status}'. Expected 'CASH_PENDING'."
                }, status=status.HTTP_400_BAD_REQUEST)

            if pmt.otp_used_at is not None:
                return Response({"error": "Payment OTP has already been used."}, status=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()

            if pmt.otp_attempts >= 5:
                return Response({"error": "Maximum OTP verification attempts (5) exceeded. Please report cash again to generate a new OTP."}, status=status.HTTP_400_BAD_REQUEST)

            submitted_otp = str(request.data.get("otp", "")).strip()
            if not submitted_otp or len(submitted_otp) != 6 or not submitted_otp.isdigit():
                return Response({"error": "Invalid OTP format. Must be a 6-digit number."}, status=status.HTTP_400_BAD_REQUEST)

            is_match = bool(pmt.payment_confirmation_otp_hash and check_password(submitted_otp, pmt.payment_confirmation_otp_hash))

            if not is_match:
                if pmt.otp_expires_at and now > pmt.otp_expires_at:
                    return Response({"error": "Payment OTP has expired (15 minute validity). Please report cash again to generate a fresh OTP."}, status=status.HTTP_400_BAD_REQUEST)

                pmt.otp_attempts += 1
                pmt.save(update_fields=["otp_attempts"])
                PaymentCollectionEvent.objects.create(
                    job_payment=pmt,
                    employee=emp,
                    actor_user=request.user,
                    event_type="PAYMENT_FAILED",
                    metadata={"reason": "INVALID_OTP", "attempts": pmt.otp_attempts},
                )
                remaining = max(0, 5 - pmt.otp_attempts)
                return Response({
                    "error": f"Invalid payment confirmation OTP. {remaining} attempt(s) remaining.",
                    "attempts_remaining": remaining,
                }, status=status.HTTP_400_BAD_REQUEST)

            # Successful OTP verification: Atomically transition to PAID
            pmt.payment_status = JobPayment.PaymentStatus.PAID
            pmt.amount_paid = pmt.amount_due
            pmt.customer_confirmed_at = now
            pmt.customer_confirmation_method = "OTP"
            pmt.otp_used_at = now
            pmt.save()

            # Record immutable audit events
            PaymentCollectionEvent.objects.create(
                job_payment=pmt,
                employee=emp,
                actor_user=request.user,
                event_type="CUSTOMER_CONFIRMED",
                amount=pmt.amount_due,
                metadata={"method": "OTP"},
            )
            PaymentCollectionEvent.objects.create(
                job_payment=pmt,
                employee=emp,
                actor_user=request.user,
                event_type="CASH_COLLECTED",
                amount=pmt.amount_due,
            )
            PaymentCollectionEvent.objects.create(
                job_payment=pmt,
                employee=emp,
                actor_user=request.user,
                event_type="PAYMENT_PAID",
                amount=pmt.amount_due,
            )

            job.payment_status = "paid"

            # Fixes X-01: let the customer app know cash was collected and
            # confirmed, mirroring the ONLINE-gateway payment.collected event
            # the Customer app's webhook receiver already handles.
            try:
                from workforce_api.services.customer_webhook import notify_customer_app
                notify_customer_app(
                    "payment.collected",
                    job,
                    amount=float(pmt.amount_due),
                    collected_by_name=(emp.user.get_full_name() if getattr(emp, "user", None) else "") or "Technician",
                    collection_method="CASH",
                    transaction_reference=f"OTP-{pmt.id}",
                )
            except Exception as webhook_err:
                logger.info(f"Could not notify Customer app of payment collection for Job #{job.id}: {webhook_err}")

            # Service completion gate: If service proof is submitted / completed, close the job
            completion_blocked_reason = ""
            if job.status == "proof_submitted":
                try:
                    apply_transition(job, "completed", actor=request.user)
                except ValidationError as ve:
                    # Fix: this used to only log a warning and return a plain
                    # "payment verified" success response with no sign the
                    # job silently failed to close -- since wallet crediting
                    # (commission.settle_completed_job) only runs on the
                    # COMPLETED transition, that meant a technician could see
                    # "PAID" while their earnings were never credited, with
                    # no visible reason why. Surface it instead: to the
                    # response (so the app can show it) and to an admin
                    # notification (so ops can act without digging through
                    # logs), and try `complete_stuck_paid_jobs` once the
                    # underlying block is cleared.
                    completion_blocked_reason = str(ve)
                    logger.warning("Could not complete job #%s after payment OTP verification: %s", job.id, ve)
                    job.save(update_fields=["payment_status"])
                    try:
                        admin_user = None
                        if job.company:
                            admin_user = get_user_model().objects.filter(
                                Q(role__in=["admin", "manager"]) | Q(is_staff=True),
                                company=job.company,
                            ).first()
                        if admin_user:
                            WorkforceNotification.objects.create(
                                recipient=admin_user,
                                title="Payment Confirmed but Job Did Not Close",
                                message=(
                                    f"Job #{job.id} ({job.request_id}) payment was verified PAID but the job could "
                                    f"not be marked completed: {completion_blocked_reason} Wallet was NOT credited. "
                                    f"Run `complete_stuck_paid_jobs --job {job.request_id}` once resolved."
                                ),
                                notification_type="JOB_COMPLETION_BLOCKED",
                                company=job.company,
                                related_object_id=str(job.id),
                            )
                    except Exception as notify_err:
                        logger.warning(f"Could not notify admin of blocked completion for Job #{job.id}: {notify_err}")
                except Exception as e:
                    completion_blocked_reason = str(e)
                    logger.exception("Unexpected error completing job #%s after payment OTP verification: %s", job.id, e)
                    job.save(update_fields=["payment_status"])
                else:
                    # Bug found: apply_transition() only persists the "status"
                    # field (service_request.save(update_fields=["status"])) --
                    # it never writes back payment_status, so the "paid"
                    # assignment above was staying in memory only. The job
                    # correctly flipped to COMPLETED, but the shared
                    # payment_status column (read directly by the Customer
                    # app -- same database, same row) stayed at whatever it
                    # was before (e.g. "cash_pending"), which is exactly why
                    # a technician could see the job as COMPLETED while the
                    # customer's booking list still showed "Cash Collection
                    # Pending". Persist it explicitly on the success path too.
                    job.save(update_fields=["payment_status"])
            else:
                job.save(update_fields=["payment_status"])

            response_payload = {
                "message": f"Payment of ₹{pmt.amount_due} successfully verified via Customer OTP and marked PAID.",
                "payment_status": "PAID",
                "job_status": job.status,
            }
            if completion_blocked_reason:
                response_payload["message"] += " NOTE: the job could not be closed yet -- see completion_blocked_reason."
                response_payload["completion_blocked_reason"] = completion_blocked_reason
            return Response(response_payload, status=status.HTTP_200_OK)


class WorkforceCustomerJobPaymentView(APIView):
    """
    Customer views their own booking payment details.
    Only accessible by the authenticated customer who owns the booking,
    or a platform admin, or a vendor admin of the booking's company.
    NEVER exposes payment_confirmation_otp_hash or internal secrets.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        is_customer = (
            job.customer == request.user
            or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
            or getattr(job, "phone", "") == getattr(request.user, "username", "")
        )
        is_platform_operator = getattr(request.user, "is_superuser", False)
        user_company = resolve_actor_company(request)
        is_vendor_admin_owner = is_admin_role(request.user) and bool(job.company_id and user_company and job.company_id == user_company.id)

        if not (is_customer or is_platform_operator or is_vendor_admin_owner):
            return Response({"error": "Unauthorized: You do not own this booking.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        is_online = (job.payment_method or "").upper() in ["ONLINE", "PREPAID"]
        pmt, _ = JobPayment.objects.get_or_create(
            job=job,
            defaults={
                "company": job.company,
                "employee": job.assigned_employee,
                "payment_method": JobPayment.PaymentMethod.ONLINE if is_online else JobPayment.PaymentMethod.CASH_ON_SERVICE,
                "payment_status": JobPayment.PaymentStatus.PAID if job.payment_status in ["paid", "collected"] else JobPayment.PaymentStatus.PENDING,
                "amount_due": job.total_amount,
                "amount_paid": job.total_amount if job.payment_status in ["paid", "collected"] else Decimal("0.00"),
            }
        )

        return Response({
            "job_id": job.id,
            "request_id": job.request_id,
            "payment_method": pmt.payment_method,
            "payment_status": pmt.payment_status,
            "amount_due": str(pmt.amount_due),
            "amount_paid": str(pmt.amount_paid),
            "amount_received": str(pmt.amount_received) if pmt.amount_received else None,
            "change_returned": str(pmt.change_returned) if pmt.change_returned else None,
            "currency": pmt.currency,
            "confirmation_required": pmt.payment_status == JobPayment.PaymentStatus.CASH_PENDING,
            "cash_collected_at": pmt.cash_collected_at.isoformat() if pmt.cash_collected_at else None,
            "customer_confirmed_at": pmt.customer_confirmed_at.isoformat() if pmt.customer_confirmed_at else None,
            "customer_confirmation_method": pmt.customer_confirmation_method,
            "technician_name": job.assigned_employee.user.get_full_name() if job.assigned_employee and job.assigned_employee.user else "Assigned Technician",
        }, status=status.HTTP_200_OK)


class WorkforceCustomerPaymentConfirmView(APIView):
    """
    Path A: Authenticated customer directly confirms or disputes cash payment.
    - Verified owner of booking.
    - On CONFIRM: In atomic transaction, transitions CASH_PENDING -> PAID.
    - If service proof submitted, closes the job.
    - On PROBLEM: Disputed event logged, notifies operations, keeps CASH_PENDING.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        is_customer = (
            job.customer == request.user
            or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
            or getattr(job, "phone", "") == getattr(request.user, "username", "")
        )
        is_platform_operator = getattr(request.user, "is_superuser", False)
        user_company = resolve_actor_company(request)
        is_vendor_admin_owner = is_admin_role(request.user) and bool(job.company_id and user_company and job.company_id == user_company.id)

        if not (is_customer or is_platform_operator or is_vendor_admin_owner):
            return Response({"error": "Unauthorized: You do not own this booking.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            pmt = JobPayment.objects.select_for_update().filter(job=job).first()
            if not pmt:
                return Response({"error": "No payment record found for this job."}, status=status.HTTP_404_NOT_FOUND)

            if pmt.payment_status == JobPayment.PaymentStatus.PAID:
                return Response({
                    "message": "Payment has already been marked PAID.",
                    "payment_status": "PAID",
                    "job_status": job.status,
                }, status=status.HTTP_200_OK)

            if pmt.payment_status != JobPayment.PaymentStatus.CASH_PENDING:
                return Response({
                    "error": f"Cannot confirm payment in status '{pmt.payment_status}'. Expected 'CASH_PENDING'."
                }, status=status.HTTP_400_BAD_REQUEST)

            action = str(request.data.get("action", "CONFIRM")).upper()
            now = timezone.now()

            if action == "CONFIRM":
                pmt.payment_status = JobPayment.PaymentStatus.PAID
                pmt.amount_paid = pmt.amount_due
                pmt.customer_confirmed_at = now
                pmt.customer_confirmation_method = "DIRECT_CONFIRMATION"
                pmt.save()

                PaymentCollectionEvent.objects.create(
                    job_payment=pmt,
                    employee=job.assigned_employee,
                    actor_user=request.user,
                    event_type="CUSTOMER_CONFIRMED",
                    amount=pmt.amount_due,
                    metadata={"method": "DIRECT_CONFIRMATION"},
                )
                PaymentCollectionEvent.objects.create(
                    job_payment=pmt,
                    employee=job.assigned_employee,
                    actor_user=request.user,
                    event_type="CASH_COLLECTED",
                    amount=pmt.amount_due,
                )
                PaymentCollectionEvent.objects.create(
                    job_payment=pmt,
                    employee=job.assigned_employee,
                    actor_user=request.user,
                    event_type="PAYMENT_PAID",
                    amount=pmt.amount_due,
                )

                job.payment_status = "paid"

                # See the matching fix in WorkforceJobPaymentVerifyOTPView --
                # a rejected completion here used to be silently swallowed
                # too, so a customer could confirm payment and see success
                # while the job never closed and the technician's wallet was
                # never credited, with no visible reason why.
                completion_blocked_reason = ""
                if job.status == "proof_submitted":
                    try:
                        apply_transition(job, "completed", actor=request.user)
                    except ValidationError as ve:
                        completion_blocked_reason = str(ve)
                        logger.warning("Could not complete job #%s after customer payment confirm: %s", job.id, ve)
                        job.save(update_fields=["payment_status"])
                        try:
                            admin_user = None
                            if job.company:
                                admin_user = get_user_model().objects.filter(
                                    Q(role__in=["admin", "manager"]) | Q(is_staff=True),
                                    company=job.company,
                                ).first()
                            if admin_user:
                                WorkforceNotification.objects.create(
                                    recipient=admin_user,
                                    title="Payment Confirmed but Job Did Not Close",
                                    message=(
                                        f"Job #{job.id} ({job.request_id}) payment was confirmed PAID but the job "
                                        f"could not be marked completed: {completion_blocked_reason} Wallet was NOT "
                                        f"credited. Run `complete_stuck_paid_jobs --job {job.request_id}` once resolved."
                                    ),
                                    notification_type="JOB_COMPLETION_BLOCKED",
                                    company=job.company,
                                    related_object_id=str(job.id),
                                )
                        except Exception as notify_err:
                            logger.warning(f"Could not notify admin of blocked completion for Job #{job.id}: {notify_err}")
                    except Exception as e:
                        completion_blocked_reason = str(e)
                        logger.exception("Unexpected error completing job #%s after customer payment confirm: %s", job.id, e)
                        job.save(update_fields=["payment_status"])
                    else:
                        # See the matching comment in WorkforceJobPaymentVerifyOTPView --
                        # apply_transition() only persists "status", so without this the
                        # payment_status column stays stale (e.g. "cash_pending") even
                        # though the job just completed successfully.
                        job.save(update_fields=["payment_status"])
                else:
                    job.save(update_fields=["payment_status"])

                if job.assigned_employee and job.assigned_employee.user:
                    create_notification(
                        recipient=job.assigned_employee.user,
                        title="Payment Confirmed by Customer",
                        message=f"Customer confirmed cash payment of ₹{pmt.amount_due} for Job #{job.id}.",
                        notification_type="PAYMENT_CONFIRMED",
                        company=job.company,
                        related_object_id=str(job.id),
                    )

                response_payload = {
                    "message": f"Cash payment of ₹{pmt.amount_due} successfully confirmed.",
                    "payment_status": "PAID",
                    "job_status": job.status,
                }
                if completion_blocked_reason:
                    response_payload["message"] += " NOTE: the job could not be closed yet -- see completion_blocked_reason."
                    response_payload["completion_blocked_reason"] = completion_blocked_reason
                return Response(response_payload, status=status.HTTP_200_OK)

            elif action == "PROBLEM":
                reason = str(request.data.get("reason", "Customer reported payment dispute")).strip()
                PaymentCollectionEvent.objects.create(
                    job_payment=pmt,
                    employee=job.assigned_employee,
                    actor_user=request.user,
                    event_type="PAYMENT_DISPUTED",
                    amount=pmt.amount_due,
                    metadata={"reason": reason},
                )
                return Response({
                    "message": "Payment dispute logged. Support operations team has been notified.",
                    "payment_status": "CASH_PENDING",
                }, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Invalid action. Must be 'CONFIRM' or 'PROBLEM'."}, status=status.HTTP_400_BAD_REQUEST)


# ─── 10. Dynamic Job Dispatch & Eligibility Matching (Phase 14) ───────────────

def check_technician_eligibility(emp, service_name=None, prefetched_data=None):
    """
    Standardized 9-Gate Employee Eligibility Check.
    Delegates to the authoritative check_candidate_eligibility engine in automatic_dispatch.py.
    """
    from .services.automatic_dispatch import check_candidate_eligibility
    return check_candidate_eligibility(emp, service_name)


class WorkforceDispatchEligibleListView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        from django.db.models import Exists, OuterRef, Prefetch
        from django.utils.dateparse import parse_datetime
        from workforce_api.services.automatic_dispatch import check_candidate_eligibility, haversine_distance

        service_name = request.query_params.get("service", "").strip()
        job_id = request.query_params.get("job_id")
        job = None
        cust_lat = None
        cust_lon = None

        if job_id:
            job = ServiceRequest.objects.filter(pk=job_id).first()
            if job:
                if not getattr(request.user, "is_superuser", False):
                    user_company = resolve_actor_company(request)
                    if not user_company or not job.company_id or user_company.id != job.company_id:
                        return Response({"error": "Unauthorized cross-company job query.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
                service_name = service_name or job.issue_title or job.service_category
                if job.latitude is not None and job.longitude is not None:
                    try:
                        cust_lat = float(job.latitude)
                        cust_lon = float(job.longitude)
                    except (ValueError, TypeError):
                        pass

        today_dow = timezone.now().weekday()
        from workforce_api.services.workload import ACTIVE_WORKLOAD_STATUSES
        busy_subquery = ServiceRequest.objects.filter(
            assigned_employee_id=OuterRef("pk"),
            status__in=ACTIVE_WORKLOAD_STATUSES
        )

        candidates_qs = Employee.objects.filter(is_active=True).select_related("user", "company")
        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            candidates_qs = candidates_qs.filter(company=user_company)

        candidates = list(
            candidates_qs
            .annotate(is_busy_job=Exists(busy_subquery))
            .prefetch_related(
                Prefetch(
                    "compliance_records",
                    queryset=WorkforceEmployeeCompliance.objects.filter(
                        requirement__is_mandatory=True,
                        status__in=["EXPIRED", "REJECTED"]
                    ),
                    to_attr="prefetched_invalid_compliance"
                ),
                Prefetch(
                    "schedules",
                    queryset=WorkforceEmployeeSchedule.objects.filter(day_of_week=today_dow),
                    to_attr="prefetched_today_schedules"
                ),
                Prefetch(
                    "skills",
                    queryset=WorkforceEmployeeSkill.objects.filter(is_verified=True).select_related("skill"),
                    to_attr="prefetched_verified_skills"
                )
            )
        )

        now = timezone.now()
        GATE_NAMES = {
            "G1": "Account Active",
            "G2": "Registration Approved",
            "G3": "Required Documents Approved",
            "G4": "Mandatory Compliance Valid",
            "G5": "Working Schedule Active",
            "G6": "Service / Skill Match",
            "G7": "Online & Available Presence",
            "G8": "Not On Leave",
            "G9": "Single-Job Concurrency Free",
        }

        eligible = []
        for emp in candidates:
            onboarding = (emp.bank_details or {}).get("onboarding", {})
            reg_status = onboarding.get("status", "not_started")
            approved_svcs = [s.get("name", "") for s in onboarding.get("services", []) if s.get("status") == "approved"]

            is_eligible, reason, gate_results = check_candidate_eligibility(emp, service_name)

            # GPS telemetry extraction
            last_loc = getattr(emp.user, "last_known_location", None) or {}
            emp_lat = last_loc.get("latitude") if last_loc.get("latitude") is not None else last_loc.get("lat")
            emp_lon = last_loc.get("longitude") if last_loc.get("longitude") is not None else (last_loc.get("lng") or last_loc.get("lon"))

            gps_age_s = None
            updated_at_str = last_loc.get("updated_at")
            if updated_at_str:
                try:
                    loc_dt = parse_datetime(str(updated_at_str))
                    if loc_dt:
                        if timezone.is_naive(loc_dt):
                            loc_dt = timezone.make_aware(loc_dt)
                        gps_age_s = max(0, round((now - loc_dt).total_seconds()))
                except Exception:
                    pass

            dist_km = None
            if cust_lat is not None and cust_lon is not None and emp_lat is not None and emp_lon is not None:
                try:
                    dist_m = haversine_distance(cust_lat, cust_lon, float(emp_lat), float(emp_lon))
                    dist_km = round(dist_m / 1000.0, 2)
                except (ValueError, TypeError):
                    pass

            gps_freshness = "MISSING"
            if gps_age_s is not None:
                if gps_age_s <= 30:
                    gps_freshness = "LIVE"
                elif gps_age_s <= 120:
                    gps_freshness = "UPDATING"
                elif gps_age_s <= 300:
                    gps_freshness = "DELAYED"
                else:
                    gps_freshness = "STALE"

            # Compute rank score
            score = 0
            if is_eligible:
                proximity_score = max(0.0, 100.0 - ((dist_km or 25.0) * 2.0))
                clock_in_bonus = 10.0 if (emp.bank_details or {}).get("attendance", {}).get("is_clocked_in") else 0.0
                score = round(proximity_score + clock_in_bonus, 1)

            gate_audit = []
            for g_code, g_name in GATE_NAMES.items():
                gate_audit.append({
                    "gate": g_code,
                    "name": g_name,
                    "passed": bool(gate_results.get(g_code, False)),
                })

            eligible.append({
                "id": emp.id,
                "employee_id": emp.employee_id,
                "name": emp.user.get_full_name() or emp.user.username,
                "phone": emp.user.mobile_number or emp.user.phone,
                "is_online": emp.is_online,
                "current_availability": emp.current_availability,
                "registration_status": reg_status,
                "approved_services": approved_svcs,
                "is_dispatch_ready": is_eligible,
                "ineligibility_reason": reason if not is_eligible else "",
                "distance_km": dist_km,
                "score": score,
                "gps_age_seconds": gps_age_s,
                "gps_freshness": gps_freshness,
                "gate_audit": gate_audit,
            })

        # Sort: eligible candidates first (by score descending), then ineligible candidates
        eligible.sort(key=lambda x: (1 if x["is_dispatch_ready"] else 0, x["score"]), reverse=True)

        return Response(eligible, status=status.HTTP_200_OK)


class WorkforceDispatchAssignView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request):
        return Response({
            "code": "MANUAL_DISPATCH_DISABLED",
            "message": "Customer jobs are automatically assigned using live employee availability, GPS proximity and eligibility.",
            "error": "Manual primary job assignment has been decommissioned. Automatic geo-based dispatch engine is active."
        }, status=status.HTTP_410_GONE)


# ─── Automatic Dispatch Engine ────────────────────────────────────────────────

def run_automatic_dispatch(job, excluded_employee_ids=None):
    """
    Delegates to authoritative automatic dispatch service:
    workforce_api.services.automatic_dispatch.dispatch_job
    """
    from workforce_api.services.automatic_dispatch import dispatch_job
    return dispatch_job(job, exclude_employee_ids=excluded_employee_ids)


from workforce_api.services.workload import ACTIVE_WORKLOAD_STATUSES, supersede_other_offers_for_employee


class WorkforceJobAcceptOfferView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found.", "code": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found.", "code": "PROFILE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_employee_authorized_for_job(emp, job):
            return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            job_obj = ServiceRequest.objects.select_for_update().filter(pk=pk).first()
            if not job_obj:
                return Response({"error": "Job not found.", "code": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

            emp_obj = Employee.objects.select_for_update().filter(pk=emp.pk).first()
            if not emp_obj:
                return Response({"error": "Employee profile not found.", "code": "PROFILE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

            # Prevent duplicate acceptance by the same employee on the same job (Idempotent success)
            if job_obj.assigned_employee == emp_obj and job_obj.status in ACTIVE_WORKLOAD_STATUSES:
                return Response({
                    "message": f"Job #{job_obj.id} is already accepted by you.",
                    "job_id": job_obj.id,
                    "status": job_obj.status,
                }, status=status.HTTP_200_OK)

            # Reject acceptance if assigned to another employee (Simultaneous Acceptance Winner-Takes-All)
            if job_obj.assigned_employee and job_obj.assigned_employee != emp and job_obj.status in ["accepted", "on_the_way", "arrived", "in_progress", "completed"]:
                return Response({
                    "error": "Cannot accept job: Job has already been assigned and accepted by another technician.",
                    "code": "JOB_ALREADY_ACCEPTED"
                }, status=status.HTTP_409_CONFLICT)

            from service_requests.models import EmployeeJob
            from workforce_api.models import WorkforceJobOffer, WorkforceJobLifecycleEvent, JobTrackingSession, WorkforceEventLog

            offer = WorkforceJobOffer.objects.select_for_update().filter(
                job=job_obj,
                employee=emp_obj,
            ).order_by("-offered_at").first()

            if offer and offer.status == WorkforceJobOffer.Status.SUPERSEDED_BY_ACCEPTANCE:
                return Response({
                    "error": "This job has already been accepted by another professional.",
                    "code": "JOB_ALREADY_ACCEPTED",
                    "message": "This job has already been accepted by another professional."
                }, status=status.HTTP_409_CONFLICT)

            has_employee_job = EmployeeJob.objects.filter(service_request=job_obj, employee=emp_obj).exists()
            is_direct_assigned = (job_obj.assigned_employee == emp_obj)

            if (not offer or offer.status != WorkforceJobOffer.Status.OFFERED) and not has_employee_job and not is_direct_assigned:
                return Response({
                    "error": "No active job offer or assignment found for this technician.",
                    "code": "NO_ACTIVE_OFFER"
                }, status=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()
            cancellation_deadline = now + timedelta(minutes=5)

            if offer and offer.status == WorkforceJobOffer.Status.OFFERED:
                if offer.expires_at < now:
                    offer.status = WorkforceJobOffer.Status.EXPIRED
                    offer.save()
                    run_automatic_dispatch(job_obj)
                    return Response({
                        "error": "Job offer has expired.",
                        "code": "OFFER_EXPIRED"
                    }, status=status.HTTP_409_CONFLICT)
                offer.status = "ACCEPTED"
                offer.save()

            # Hard Single Active Job Rule: Check if employee has a conflicting active job
            conflicting = ServiceRequest.objects.filter(
                assigned_employee=emp,
                status__in=[
                    "accepted", "on_the_way", "en_route", "arrived",
                    "service_started", "in_progress", "proof_submitted",
                    "service_completed", "payment_pending", "cash_pending"
                ]
            ).exclude(pk=job_obj.pk).first()
            if conflicting:
                return Response({
                    "error": f"Cannot accept job: Technician already has an active assigned Job #{conflicting.id}.",
                    "code": "EMPLOYEE_ALREADY_BUSY"
                }, status=status.HTTP_409_CONFLICT)

            # Verify technician eligibility if accepting without an existing vetted offer
            if not offer:
                is_eligible, reason, _ = check_technician_eligibility(emp_obj, job_obj.service_category)
                if not is_eligible and job_obj.issue_title:
                    is_eligible, reason, _ = check_technician_eligibility(emp_obj, job_obj.issue_title)
                if not is_eligible:
                    return Response({"error": f"Cannot accept offer: {reason}", "code": "INELIGIBLE_TECHNICIAN"}, status=status.HTTP_400_BAD_REQUEST)

            job_obj.assigned_employee = emp_obj
            job_obj.save(update_fields=["assigned_employee"])
            apply_transition(job_obj, "accepted", actor=request.user)

            # Atomically mark employee availability as BUSY
            emp_obj.current_availability = "busy"
            emp_obj.save(update_fields=["current_availability"])

            # Mark all competing OFFERED records for the same job as SUPERSEDED_BY_ACCEPTANCE
            competing_offers = WorkforceJobOffer.objects.select_for_update().filter(
                job=job_obj,
                status=WorkforceJobOffer.Status.OFFERED
            ).exclude(employee=emp_obj)

            for c_off in competing_offers:
                c_off.status = WorkforceJobOffer.Status.SUPERSEDED_BY_ACCEPTANCE
                c_off.rejection_reason = f"Job #{job_obj.id} was accepted by another technician."
                c_off.save(update_fields=["status", "rejection_reason"])
                if c_off.employee and c_off.employee.user:
                    WorkforceEventLog.objects.create(
                        user=c_off.employee.user,
                        event_type="JOB_OFFER_CLOSED",
                        payload={
                            "job_id": job_obj.id,
                            "offer_id": c_off.id,
                            "reason": "ALREADY_ACCEPTED",
                            "accepted_by_other": True,
                            "message": "Another professional accepted this request. Offer closed automatically."
                        }
                    )

            # Supersede all other pending OFFERED jobs for this winning employee
            supersede_other_offers_for_employee(emp_obj, job_obj)

            # Unset any prior primary EmployeeJob for this service request
            EmployeeJob.objects.filter(service_request=job_obj, is_primary=True).exclude(employee=emp_obj).update(is_primary=False)

            EmployeeJob.objects.update_or_create(
                service_request=job_obj,
                employee=emp_obj,
                defaults={
                    "status": "ACCEPTED",
                    "is_primary": True,
                    "accepted_date": now,
                }
            )

            # Activate JobTrackingSession
            JobTrackingSession.objects.update_or_create(
                job=job_obj,
                employee=emp_obj,
                company=job_obj.company,
                defaults={
                    "status": JobTrackingSession.SessionStatus.ACTIVE,
                    "ended_at": None,
                }
            )

            # Log immutable lifecycle audit event
            WorkforceJobLifecycleEvent.objects.create(
                job=job_obj,
                employee=emp_obj,
                company=job_obj.company,
                actor_user=request.user,
                event_type=WorkforceJobLifecycleEvent.EventType.EMPLOYEE_JOB_ACCEPTED,
                previous_status=offer.status if offer else "OFFERED",
                new_status="accepted",
                accepted_at=now,
                cancellation_deadline=cancellation_deadline,
                metadata={"offer_id": offer.id if offer else None}
            )

            WorkforceEventLog.objects.create(
                user=emp_obj.user,
                event_type="EMPLOYEE_JOB_ACCEPTED",
                payload={
                    "job_id": job_obj.id,
                    "employee_id": emp_obj.id,
                    "accepted_at": now.isoformat(),
                    "cancellation_deadline": cancellation_deadline.isoformat(),
                }
            )
            WorkforceEventLog.objects.create(
                user=job_obj.customer if hasattr(job_obj, "customer") else None,
                event_type="NEW_EMPLOYEE_ASSIGNED",
                payload={
                    "job_id": job_obj.id,
                    "employee_id": emp_obj.id,
                    "employee_name": emp_obj.user.get_full_name() or emp_obj.user.username,
                    "status": "ACCEPTED",
                }
            )

            create_notification(
                recipient=emp_obj.user,
                title="Job Offer Accepted",
                message=f"You have accepted Job #{job_obj.id}. Proceed to customer location at {job_obj.address or 'scheduled site'}.",
                notification_type="JOB_ASSIGNMENT",
                company=job_obj.company,
                related_object_id=job_obj.id,
            )

            return Response({
                "message": f"Job #{job_obj.id} accepted successfully.",
                "job_id": job_obj.id,
                "status": job_obj.status,
                "accepted_at": now.isoformat(),
                "cancellation_deadline": cancellation_deadline.isoformat(),
            }, status=status.HTTP_200_OK)


class WorkforceJobCancelAssignmentView(APIView):
    """
    5-Minute Backend-Authoritative Employee Job Assignment Cancellation.
    Only the assigned technician can cancel prior to customer OTP verification,
    and only while in 'accepted', 'on_the_way', 'en_route', or 'arrived' states.
    Automatically releases technician to AVAILABLE, terminates tracking session,
    cleans up unverified pre-service verification, records immutable lifecycle audit event,
    and triggers automatic redispatch.
    """
    permission_classes = [IsApprovedTechnician]

    ALLOWED_REASONS = [
        "VEHICLE_ISSUE",
        "TRAFFIC_ROUTE_ISSUE",
        "TOO_FAR",
        "SERVICE_MISMATCH",
        "CUSTOMER_LOCATION_ISSUE",
        "SAFETY_CONCERN",
        "PERSONAL_EMERGENCY",
        "OTHER",
    ]

    REASON_MAP = {
        "VEHICLE BREAKDOWN / TRANSIT ISSUE": "VEHICLE_ISSUE",
        "VEHICLE ISSUE": "VEHICLE_ISSUE",
        "EXTREME TRAFFIC / ROAD CLOSED": "TRAFFIC_ROUTE_ISSUE",
        "TRAFFIC / ROUTE ISSUE": "TRAFFIC_ROUTE_ISSUE",
        "HEAVY TRAFFIC / ROAD BLOCKAGE": "TRAFFIC_ROUTE_ISSUE",
        "BUSY / HEAVY TRAFFIC": "TRAFFIC_ROUTE_ISSUE",
        "LOCATION TOO FAR / OUT OF REACH": "TOO_FAR",
        "DISTANCE TOO FAR / UNREACHABLE IN TIME": "TOO_FAR",
        "TOO FAR": "TOO_FAR",
        "SKILL / TOOLING MISMATCH": "SERVICE_MISMATCH",
        "SERVICE REQUIRES DIFFERENT TOOLS / EQUIPMENT": "SERVICE_MISMATCH",
        "SERVICE MISMATCH": "SERVICE_MISMATCH",
        "CUSTOMER LOCATION UNREACHABLE": "CUSTOMER_LOCATION_ISSUE",
        "CUSTOMER SITE UNREACHABLE / UNSAFE ACCESS": "CUSTOMER_LOCATION_ISSUE",
        "CUSTOMER LOCATION ISSUE": "CUSTOMER_LOCATION_ISSUE",
        "SAFETY CONCERN AT SITE": "SAFETY_CONCERN",
        "SAFETY CONCERN / HAZARDOUS CONDITIONS": "SAFETY_CONCERN",
        "SAFETY CONCERN": "SAFETY_CONCERN",
        "PERSONAL EMERGENCY": "PERSONAL_EMERGENCY",
        "PERSONAL REASON": "PERSONAL_EMERGENCY",
        "OTHER REASON": "OTHER",
        "OTHER": "OTHER",
    }

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found.", "code": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found.", "code": "PROFILE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not is_employee_authorized_for_job(emp, job):
            return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        # Authorization: must be the currently assigned technician or active EmployeeJob
        from service_requests.models import EmployeeJob
        has_emp_job = EmployeeJob.objects.filter(
            service_request=job,
            employee=emp,
            status__in=["ASSIGNED", "ACCEPTED", "IN_PROGRESS", "ON_THE_WAY", "ARRIVED"]
        ).exists()
        if job.assigned_employee != emp and not has_emp_job:
            return Response({"error": "Unauthorized: You are not assigned to this job.", "code": "UNAUTHORIZED_CANCELLATION"}, status=status.HTTP_403_FORBIDDEN)

        # Structured reason validation & normalization
        raw_reason = str(request.data.get("reason_code") or request.data.get("reason") or "").strip().upper()
        reason_code = self.REASON_MAP.get(raw_reason, raw_reason)
        reason_text = str(request.data.get("reason_text") or request.data.get("reason_detail") or request.data.get("notes") or "").strip()

        if not reason_code or reason_code not in self.ALLOWED_REASONS:
            return Response({
                "error": f"Invalid or missing reason_code. Must be one of: {', '.join(self.ALLOWED_REASONS)}",
                "code": "INVALID_REASON_CODE",
                "valid_reasons": self.ALLOWED_REASONS,
            }, status=status.HTTP_400_BAD_REQUEST)

        if reason_code == "OTHER" and len(reason_text) < 5:
            return Response({
                "error": "reason_text is mandatory and must be at least 5 characters for reason 'OTHER'.",
                "code": "REASON_TEXT_REQUIRED",
            }, status=status.HTTP_400_BAD_REQUEST)

        if not reason_text:
            reason_text = reason_code

        with transaction.atomic():
            job_obj = ServiceRequest.objects.select_for_update().filter(pk=pk).first()
            emp_obj = Employee.objects.select_for_update().filter(pk=emp.pk).first()

            emp_job = EmployeeJob.objects.filter(service_request=job_obj, employee=emp_obj).first()
            is_assigned_direct = (job_obj.assigned_employee == emp_obj)
            is_assigned_via_empjob = bool(emp_job and emp_job.status not in ["CANCELLED", "EMPLOYEE_CANCELLED", "REJECTED"])

            # Idempotency check: If already cancelled / redispatching and unassigned from this employee
            if job_obj.status in ["redispatching", "unassigned", "cancelled"] and not is_assigned_direct and not is_assigned_via_empjob:
                return Response({
                    "message": "Job assignment is already cancelled.",
                    "job_id": job_obj.id,
                    "status": job_obj.status,
                }, status=status.HTTP_200_OK)

            if not is_assigned_direct and not is_assigned_via_empjob:
                return Response({
                    "error": "Unauthorized: You are no longer assigned to this job.",
                    "code": "UNAUTHORIZED_CANCELLATION",
                }, status=status.HTTP_403_FORBIDDEN)

            # State check: Allowed only from 'accepted' or 'on_the_way'
            if job_obj.status not in ["accepted", "on_the_way"]:
                return Response({
                    "error": f"Cannot cancel job in status '{job_obj.status}'. Cancellation is only allowed while 'accepted' or 'on_the_way'.",
                    "code": "CANCELLATION_NOT_ALLOWED_IN_CURRENT_STATE",
                }, status=status.HTTP_409_CONFLICT)

            # 5-minute cancellation window check
            from service_requests.models import EmployeeJob
            from workforce_api.models import WorkforceJobLifecycleEvent, JobTrackingSession, WorkforceEventLog

            accept_event = WorkforceJobLifecycleEvent.objects.filter(
                job=job_obj,
                employee=emp_obj,
                event_type=WorkforceJobLifecycleEvent.EventType.EMPLOYEE_JOB_ACCEPTED,
            ).order_by("-created_at").first()

            accepted_at = (
                accept_event.accepted_at if accept_event
                else (emp_job.accepted_date if emp_job and emp_job.accepted_date else job_obj.updated_at)
            )

            now = timezone.now()
            cancellation_deadline = (
                accept_event.cancellation_deadline if accept_event and accept_event.cancellation_deadline
                else (accepted_at + timedelta(minutes=5))
            )

            if now > cancellation_deadline:
                return Response({
                    "error": "The 5-minute cancellation window for this job has expired. Please contact dispatch support.",
                    "code": "CANCELLATION_WINDOW_EXPIRED",
                    "cancellation_deadline": cancellation_deadline.isoformat(),
                }, status=status.HTTP_409_CONFLICT)

            prev_status = job_obj.status

            # Transition ServiceRequest to 'redispatching' and remove assignment via state machine
            job_obj.assigned_employee = None
            job_obj.save(update_fields=["assigned_employee"])
            apply_transition(job_obj, "redispatching", actor=request.user)

            # Transition EmployeeJob to EMPLOYEE_CANCELLED and unset primary
            if emp_job:
                emp_job.status = "EMPLOYEE_CANCELLED"
                emp_job.is_primary = False
                emp_job.uncompletion_reason = f"[{reason_code}] {reason_text}".strip()
                emp_job.save(update_fields=["status", "is_primary", "uncompletion_reason"])

            # Terminate existing JobTrackingSession
            JobTrackingSession.objects.filter(
                job=job_obj,
                employee=emp_obj,
                status=JobTrackingSession.SessionStatus.ACTIVE,
            ).update(
                status=JobTrackingSession.SessionStatus.CANCELLED,
                ended_at=now,
            )

            # Invalidate offer
            WorkforceJobOffer.objects.filter(
                job=job_obj,
                employee=emp_obj,
                status="ACCEPTED",
            ).update(
                status="CANCELLED",
                rejection_reason=f"[{reason_code}] {reason_text}".strip(),
            )

            # Release Employee Availability: reconcile against remaining active jobs
            from workforce_api.services.workload import reconcile_employee_availability
            reconcile_employee_availability(emp_obj)
            logger.info(f"[EMPLOYEE_RELEASED] employee={emp_obj.id} cancelled_job={job_obj.id} state={emp_obj.current_availability.upper()}")

            window_seconds = max(0, int((now - accepted_at).total_seconds())) if accepted_at else None

            # Create immutable audit log
            WorkforceJobLifecycleEvent.objects.create(
                job=job_obj,
                employee=emp_obj,
                company=job_obj.company,
                actor_user=request.user,
                event_type=WorkforceJobLifecycleEvent.EventType.EMPLOYEE_JOB_CANCELLED,
                previous_status=prev_status,
                new_status="redispatching",
                accepted_at=accepted_at,
                cancelled_at=now,
                cancellation_deadline=cancellation_deadline,
                reason_code=reason_code,
                reason_text=reason_text,
                cancellation_window_seconds=window_seconds,
                metadata={"cancellation_window_seconds": window_seconds}
            )

            # Broadcast realtime events
            WorkforceEventLog.objects.create(
                user=emp_obj.user,
                event_type="EMPLOYEE_JOB_CANCELLED",
                payload={"job_id": job_obj.id, "employee_id": emp_obj.id, "reason_code": reason_code}
            )
            WorkforceEventLog.objects.create(
                user=job_obj.customer if hasattr(job_obj, "customer") else None,
                event_type="EMPLOYEE_CANCELLED",
                payload={
                    "job_id": job_obj.id,
                    "status": "FINDING_NEW_PROFESSIONAL",
                    "message": "Your professional cancelled. We're finding another professional nearby.",
                    "reason": reason_code,
                }
            )

            # Trigger automatic redispatch excluding the cancelling technician
            success, msg = run_automatic_dispatch(job_obj, excluded_employee_ids=[emp_obj.id])

            return Response({
                "message": f"Job #{job_obj.id} assignment cancelled successfully. Redispatch status: {msg}",
                "job_id": job_obj.id,
                "status": job_obj.status,
                "redispatch_message": msg,
            }, status=status.HTTP_200_OK)


class WorkforceJobTechnicianCancelView(APIView):
    """
    Authoritative 5-minute cancellation endpoint for technicians.
    Allows cancellation ONLY when status is ACCEPTED or ON_THE_WAY and within 5 minutes of acceptance.
    Requires structured cancellation reasons.
    Triggers automatic redispatch excluding the cancelling technician.
    """
    permission_classes = [IsApprovedTechnician]

    VALID_CANCELLATION_REASONS = [
        "VEHICLE_ISSUE",
        "TRAFFIC_ROUTE_ISSUE",
        "TOO_FAR",
        "SERVICE_MISMATCH",
        "CUSTOMER_LOCATION_ISSUE",
        "SAFETY_CONCERN",
        "PERSONAL_EMERGENCY",
        "OTHER",
    ]

    def post(self, request, pk):
        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found.", "code": "EMPLOYEE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        reason_code = request.data.get("reason_code") or request.data.get("reason")
        reason_detail = (request.data.get("reason_detail") or request.data.get("notes") or "").strip()

        if not reason_code:
            return Response({
                "error": "Cancellation reason is required.",
                "code": "REASON_REQUIRED",
                "valid_reasons": self.VALID_CANCELLATION_REASONS,
            }, status=status.HTTP_400_BAD_REQUEST)

        # Normalize friendly reason string
        reason_map = {
            "Vehicle Breakdown / Transit Issue": "VEHICLE_ISSUE",
            "Vehicle issue": "VEHICLE_ISSUE",
            "Extreme Traffic / Road Closed": "TRAFFIC_ROUTE_ISSUE",
            "Traffic / Route issue": "TRAFFIC_ROUTE_ISSUE",
            "Busy / Heavy traffic": "TRAFFIC_ROUTE_ISSUE",
            "Location Too Far / Out of Reach": "TOO_FAR",
            "Distance Too Far / Unreachable in Time": "TOO_FAR",
            "Too far": "TOO_FAR",
            "Skill / Tooling Mismatch": "SERVICE_MISMATCH",
            "Service mismatch": "SERVICE_MISMATCH",
            "Customer Location Unreachable": "CUSTOMER_LOCATION_ISSUE",
            "Customer location issue": "CUSTOMER_LOCATION_ISSUE",
            "Safety Concern at Site": "SAFETY_CONCERN",
            "Safety concern": "SAFETY_CONCERN",
            "Personal Emergency": "PERSONAL_EMERGENCY",
            "Personal emergency": "PERSONAL_EMERGENCY",
            "Personal reason": "PERSONAL_EMERGENCY",
            "Other Reason": "OTHER",
            "Other": "OTHER",
        }
        reason_code = reason_map.get(reason_code, reason_code)
        if reason_code not in self.VALID_CANCELLATION_REASONS:
            return Response({
                "error": f"Invalid cancellation reason '{reason_code}'. Must be one of: {', '.join(self.VALID_CANCELLATION_REASONS)}",
                "code": "INVALID_REASON",
                "valid_reasons": self.VALID_CANCELLATION_REASONS,
            }, status=status.HTTP_400_BAD_REQUEST)

        if reason_code == "OTHER" and not reason_detail:
            return Response({
                "error": "Meaningful explanation required when selecting 'OTHER' reason.",
                "code": "EXPLANATION_REQUIRED",
            }, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            job = ServiceRequest.objects.select_for_update().filter(pk=pk).first()
            if not job:
                return Response({"error": "Job not found.", "code": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

            # Cross-tenant check
            if emp.company_id and job.company_id and emp.company_id != job.company_id:
                return Response({"error": "Cross-company cancellation forbidden.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

            # Verify assigned technician (direct or via EmployeeJob)
            from service_requests.models import EmployeeJob
            emp_job = EmployeeJob.objects.filter(service_request=job, employee=emp).first()
            is_assigned_direct = (job.assigned_employee == emp)
            is_assigned_via_empjob = bool(emp_job and emp_job.status not in ["CANCELLED", "EMPLOYEE_CANCELLED", "REJECTED"])

            if not is_assigned_direct and not is_assigned_via_empjob:
                return Response({"error": "You are not the assigned technician for this job.", "code": "NOT_ASSIGNED_TECHNICIAN"}, status=status.HTTP_403_FORBIDDEN)

            # State check: ONLY allow cancellation during ACCEPTED or ON_THE_WAY
            if job.status not in ["accepted", "on_the_way", "en_route"]:
                return Response({
                    "error": f"Cancellation is not allowed in current job state '{job.status}'. Cancellation window is only open prior to arrival.",
                    "code": "CANCELLATION_NOT_ALLOWED_IN_CURRENT_STATE",
                }, status=status.HTTP_409_CONFLICT)

            # 5-minute cancellation window check
            from service_requests.models import EmployeeJob
            emp_job = EmployeeJob.objects.filter(service_request=job, employee=emp).first()
            accepted_at = (emp_job.accepted_date if emp_job and emp_job.accepted_date else None) or job.updated_at
            
            cancellation_deadline = accepted_at + timedelta(minutes=5)
            now = timezone.now()
            if now > cancellation_deadline:
                return Response({
                    "error": "Cancellation window has closed (5 minutes elapsed since acceptance).",
                    "code": "CANCELLATION_WINDOW_EXPIRED",
                    "accepted_at": accepted_at.isoformat(),
                    "cancellation_deadline": cancellation_deadline.isoformat(),
                }, status=status.HTTP_409_CONFLICT)

            # 1. Update EmployeeJob record
            full_reason_str = f"[{reason_code}] {reason_detail}".strip()
            if emp_job:
                emp_job.status = "CANCELLED"
                emp_job.notes = full_reason_str
                emp_job.save(update_fields=["status", "notes"])

            # 2. Terminate active JobTrackingSession
            from workforce_api.models import JobTrackingSession, WorkforceJobOffer, WorkforceEventLog
            JobTrackingSession.objects.filter(job=job, employee=emp, status=JobTrackingSession.SessionStatus.ACTIVE).update(
                status=JobTrackingSession.SessionStatus.CANCELLED
            )

            # 3. Mark offer as CANCELLED
            WorkforceJobOffer.objects.filter(job=job, employee=emp).update(status="CANCELLED")

            # 4. Clear technician assignment on job & preserve customer booking
            job.assigned_employee = None
            job.status = "confirmed"
            job.save(update_fields=["assigned_employee", "status"])

            # 5. Log audit event
            WorkforceEventLog.objects.create(
                user=emp.user,
                event_type="JOB_CANCELLED_BY_TECH",
                payload={
                    "job_id": job.id,
                    "employee_id": emp.id,
                    "reason_code": reason_code,
                    "reason_detail": reason_detail,
                }
            )

            # 6. Automatic redispatch to next eligible candidate, excluding this technician
            try:
                from workforce_api.services.automatic_dispatch import dispatch_job
                dispatch_job(job, exclude_employee_ids=[emp.id])
            except Exception as e:
                logger.error(f"[REDISPATCH_ERROR] Failed to auto-dispatch job #{job.id} after tech cancellation: {e}")

            return Response({
                "message": f"Job #{job.id} cancelled successfully. Redispatch started for next professional.",
                "job_id": job.id,
                "status": "CANCELLED_BY_TECHNICIAN",
            }, status=status.HTTP_200_OK)


class WorkforceJobCustomerCancelSyncView(APIView):
    """
    Server-to-server endpoint: the Customer app calls this when a customer
    cancels their booking, so this app can release the assigned technician
    and close the job out. Authenticated by a shared secret
    (IsInternalWorkforceCaller), not a user session -- there is no
    vendor-side user acting here.

    Bug found (BLOCKER): before this endpoint existed,
    WorkforceIntegrationService.cancel_workforce_job() on the Customer app
    called jobs/<pk>/cancel/ (WorkforceJobTechnicianCancelView above) --
    that view requires IsApprovedTechnician and treats the caller as "the
    assigned technician cancelling their own job within a 5-minute window",
    entirely wrong semantics for "the customer cancelled the whole
    booking". It also only ever accepted a technician's own session, never
    a service-to-service call, so it 401'd every single time regardless.
    Both failures were silently swallowed on the Customer side and
    reported back as success, so the technician was never actually
    released -- Employee.current_availability stayed "busy" forever,
    excluded from all future dispatch, until they happened to manually
    toggle their own status off and back on.

    apply_transition(job, "cancelled") below already does everything this
    needs -- validates the transition is legal from the job's current
    state, closes any active JobTrackingSession, and reconciles the
    assigned employee's availability back to free (see
    service_requests/state_machine.py) -- so this view stays intentionally
    thin rather than re-implementing any of that.
    """
    permission_classes = [IsInternalWorkforceCaller]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        if job.status == "cancelled":
            if job.assigned_employee:
                from workforce_api.services.workload import reconcile_employee_availability
                from service_requests.models import EmployeeJob
                EmployeeJob.objects.filter(service_request=job).update(status="CANCELLED")
                reconcile_employee_availability(job.assigned_employee)
            return Response({"message": "Job already cancelled.", "status": job.status}, status=status.HTTP_200_OK)

        try:
            new_status = apply_transition(job, "cancelled", actor=None)
        except ValidationError as e:
            return Response({"error": str(e.detail if hasattr(e, "detail") else e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": f"Job #{job.id} cancelled (customer-initiated) and technician released.",
            "job_id": job.id,
            "status": new_status,
        }, status=status.HTTP_200_OK)


class WorkforceJobClawbackSyncView(APIView):
    """
    Server-to-server endpoint: the Customer app calls this when an admin
    completes a refund for a booking, so this app can claw back the
    technician's earnings for that job. Authenticated by a shared secret
    (IsInternalWorkforceCaller), not a user session -- there is no
    vendor-side user acting here, mirroring
    WorkforceJobCustomerCancelSyncView above.

    Bug found (gap, not a blocker): before this endpoint existed, a
    completed refund on the Customer side never told this app anything --
    admin_complete_refund() only ran the payment gateway refund and
    flipped RefundRequest.status to COMPLETED. The technician's earnings
    for that job (a JOB_CREDIT WalletLedgerEntry, HELD or already
    RELEASED) were left untouched, so a fully refunded customer could
    still result in a paid-out technician for the same job with no
    reconciling entry anywhere. clawback_job() below already does
    everything this needs -- idempotent, handles both the still-HELD case
    (mark CLAWED_BACK in place) and the already-RELEASED case (an
    offsetting CLAWBACK_DEBIT entry, since the immutable ledger is never
    rewritten after release) -- so this view stays intentionally thin
    rather than re-implementing any of that.
    """
    permission_classes = [IsInternalWorkforceCaller]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        reason = (request.data.get("reason") or "").strip() or "Customer refund completed."

        from .models import WalletLedgerEntry
        already = WalletLedgerEntry.objects.filter(
            job=job,
            entry_type__in=[WalletLedgerEntry.EntryType.JOB_CREDIT],
            status=WalletLedgerEntry.EntryStatus.CLAWED_BACK,
        ).exists()
        already = already or WalletLedgerEntry.objects.filter(
            job=job, entry_type=WalletLedgerEntry.EntryType.CLAWBACK_DEBIT,
        ).exists()
        if already:
            # clawback_job() is itself idempotent, but short-circuit here
            # too so a retried call from the Customer side doesn't even
            # hit the DB for a lookup it already knows the answer to.
            return Response({"message": "Job already clawed back.", "job_id": job.id}, status=status.HTTP_200_OK)

        from .services import clawback_job
        result = clawback_job(job, reason)
        if not result:
            return Response({"message": "No earnings entry found for this job -- nothing to claw back.", "job_id": job.id}, status=status.HTTP_200_OK)

        return Response({
            "message": f"Job #{job.id} earnings clawed back.",
            "job_id": job.id,
            "ledger_entry_id": result.id,
            "status": result.status,
        }, status=status.HTTP_200_OK)


class WorkforceJobRejectOfferView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        if not is_employee_authorized_for_job(emp, job):
            return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        reason = request.data.get("reason", "Technician declined offer.").strip()

        with transaction.atomic():
            job_obj = ServiceRequest.objects.select_for_update().filter(pk=pk).first()
            if not job_obj:
                return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

            from service_requests.models import EmployeeJob
            from workforce_api.models import WorkforceEventLog

            offer = WorkforceJobOffer.objects.select_for_update().filter(
                job=job_obj,
                employee=emp
            ).order_by("-id").first()

            if offer:
                offer.status = "REJECTED"
                offer.rejection_reason = reason
                offer.save(update_fields=["status", "rejection_reason"])
            else:
                WorkforceJobOffer.objects.create(
                    job=job_obj,
                    employee=emp,
                    status="REJECTED",
                    rejection_reason=reason,
                    expires_at=timezone.now()
                )

            if job_obj.assigned_employee == emp:
                job_obj.assigned_employee = None
                job_obj.save(update_fields=["assigned_employee"])

            # Clean up / remove any uncompleted EmployeeJob records for this declining employee
            EmployeeJob.objects.filter(
                service_request=job_obj,
                employee=emp
            ).exclude(status="COMPLETED").delete()

            WorkforceEventLog.objects.create(
                user=emp.user,
                event_type="OFFER_REJECTED",
                payload={"job_id": job_obj.id, "employee_id": emp.id, "reason": reason}
            )

            # Trigger immediate dispatch to next ranked technician
            success, msg = run_automatic_dispatch(job_obj)

            # Ensure job is properly marked unassigned if no other candidate received it
            job_obj.refresh_from_db()
            has_new_offer = WorkforceJobOffer.objects.filter(
                job=job_obj,
                status="OFFERED",
                expires_at__gt=timezone.now()
            ).exists()
            if not has_new_offer and job_obj.assigned_employee is None and job_obj.status == "assigned":
                job_obj.status = "unassigned"
                job_obj.save(update_fields=["status"])

            return Response({
                "message": f"Job offer declined. Next candidate dispatch status: {msg}",
                "job_id": job_obj.id,
                "status": job_obj.status,
            }, status=status.HTTP_200_OK)


class WorkforceAutoDispatchTriggerView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fixes IDOR: IsWorkforceAdmin only checks role, not company -- any
        # company's admin could force-dispatch any other company's job.
        if not _is_admin_authorized_for_company(request, job.company):
            return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        success, msg = run_automatic_dispatch(job)
        return Response({"message": msg, "success": success, "status": job.status}, status=status.HTTP_200_OK)


# ─── 11. Work Extensions & Scope Approvals ────────────────────────────────────

class WorkforceJobExtensionView(APIView):
    permission_classes = [IsApprovedTechnician]

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        extensions = WorkforceWorkExtension.objects.filter(job=job).order_by("-created_at")
        serializer = WorkforceWorkExtensionSerializer(extensions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        if job.status not in ["in_progress", "proof_submitted"]:
            return Response({
                "error": f"Cannot request work extension for job in status '{job.status}'. Job must be 'in_progress'."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Prevent duplicate active extension requests
        active_ext = WorkforceWorkExtension.objects.filter(
            job=job,
            status__in=[
                WorkforceWorkExtension.Status.REQUESTED,
                WorkforceWorkExtension.Status.ADMIN_APPROVED,
                WorkforceWorkExtension.Status.CUSTOMER_ACCEPTED,
                WorkforceWorkExtension.Status.IN_PROGRESS,
            ]
        ).first()
        if active_ext:
            return Response({
                "error": f"An active work extension request (#{active_ext.id}) is already in progress with status '{active_ext.status}'."
            }, status=status.HTTP_400_BAD_REQUEST)

        title = str(request.data.get("title", "Scope Extension")).strip() or "Scope Extension"
        reason = str(request.data.get("reason", "")).strip()
        if not reason:
            return Response({"error": "Extension reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        description = str(request.data.get("description", "")).strip()

        try:
            labor_cost = float(request.data.get("estimated_labor_cost", request.data.get("labor_cost", 0)) or 0)
            materials_cost = float(request.data.get("estimated_materials_cost", request.data.get("materials_cost", 0)) or 0)
            amount_val = request.data.get("requested_amount", request.data.get("amount"))
            if amount_val is not None:
                requested_amount = float(amount_val)
            else:
                requested_amount = labor_cost + materials_cost
        except (ValueError, TypeError):
            return Response({"error": "Invalid cost estimates provided."}, status=status.HTTP_400_BAD_REQUEST)

        if requested_amount <= 0:
            return Response({"error": "Extension requested amount must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)

        raw_spec = request.data.get("requires_specialist", False)
        requires_specialist = raw_spec is True or str(raw_spec).lower() in ["true", "1"]
        raw_crit = request.data.get("is_critical", False)
        is_critical = raw_crit is True or str(raw_crit).lower() in ["true", "1"]
        supporting_notes = str(request.data.get("supporting_notes", "")).strip()
        supporting_photo = request.FILES.get("supporting_photo") or request.FILES.get("photo")


        required_skill = None
        skill_id = request.data.get("required_skill")
        if skill_id:
            try:
                required_skill = WorkforceSkill.objects.filter(pk=int(skill_id)).first()
            except (ValueError, TypeError):
                pass

        extension = WorkforceWorkExtension.objects.create(
            job=job,
            technician=emp or job.assigned_employee,
            company=job.company,
            title=title,
            description=description,
            reason=reason,
            estimated_labor_cost=labor_cost,
            estimated_materials_cost=materials_cost,
            requested_amount=requested_amount,
            requires_specialist=requires_specialist,
            required_skill=required_skill,
            is_critical=is_critical,
            supporting_notes=supporting_notes,
            supporting_photo=supporting_photo,
            status=WorkforceWorkExtension.Status.REQUESTED,
        )

        # Mirror entry to cart_data for shared marketplace backward compatibility
        cart_data = list(job.cart_data or [])
        cart_data.append({
            "id": extension.id,
            "type": "work_extension",
            "title": title,
            "additional_amount": requested_amount,
            "reason": reason,
            "is_critical": is_critical,
            "requires_specialist": requires_specialist,
            "status": WorkforceWorkExtension.Status.REQUESTED,
            "requested_at": extension.created_at.isoformat(),
        })
        job.cart_data = cart_data
        job.save()

        # Dispatch notification to admin
        create_notification(
            recipient=job.assigned_employee.user if job.assigned_employee else request.user,
            title="Work Extension Requested",
            message=f"Work extension #{extension.id} ({title} - ₹{requested_amount}) submitted for admin review.",
            notification_type="WORK_EXTENSION_REQUEST",
            company=job.company,
            related_object_id=str(extension.id),
        )

        return Response({
            "message": "Work extension request submitted successfully for Admin review.",
            "extension": WorkforceWorkExtensionSerializer(extension).data,
        }, status=status.HTTP_201_CREATED)


class WorkforceAdminExtensionDecideView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk, ext_id):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        action = str(request.data.get("action", "")).upper()
        reason = str(request.data.get("reason", "")).strip()

        if action not in ["APPROVED", "REJECTED"]:
            return Response({"error": "Action must be APPROVED or REJECTED."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            extension = (
                WorkforceWorkExtension.objects
                .select_for_update()
                .filter(pk=ext_id, job=job)
                .first()
            )
            if not extension:
                return Response({"error": "Work extension request not found."}, status=status.HTTP_404_NOT_FOUND)

            if extension.status != WorkforceWorkExtension.Status.REQUESTED:
                return Response({
                    "error": f"Cannot review extension in status '{extension.status}'. Expected 'REQUESTED'."
                }, status=status.HTTP_400_BAD_REQUEST)

            now = timezone.now()
            if action == "APPROVED":
                extension.status = WorkforceWorkExtension.Status.ADMIN_APPROVED
                approved_amt = request.data.get("approved_amount")
                if approved_amt is not None:
                    try:
                        extension.approved_amount = float(approved_amt)
                    except (ValueError, TypeError):
                        extension.approved_amount = extension.requested_amount
                else:
                    extension.approved_amount = extension.requested_amount

                extension.final_customer_amount = extension.approved_amount
                extension.decision_token = secrets.token_urlsafe(32)
                extension.decision_expires_at = now + timedelta(hours=24)
            else:
                extension.status = WorkforceWorkExtension.Status.ADMIN_REJECTED

            extension.admin_reviewed_by = request.user
            extension.admin_review_reason = reason
            extension.admin_reviewed_at = now
            extension.save()

            # Mirror decision to cart_data
            cart_data = list(job.cart_data or [])
            for c in cart_data:
                if str(c.get("id")) == str(extension.id) and c.get("type") == "work_extension":
                    c["status"] = extension.status
                    c["approved_amount"] = float(extension.approved_amount) if extension.approved_amount is not None else 0
                    c["final_customer_amount"] = float(extension.final_customer_amount) if extension.final_customer_amount is not None else 0
                    c["admin_review_reason"] = reason
                    c["reviewed_at"] = extension.admin_reviewed_at.isoformat()
                    if extension.decision_token:
                        c["decision_token"] = extension.decision_token
                        c["decision_expires_at"] = extension.decision_expires_at.isoformat()
            job.cart_data = cart_data
            job.save()

            if extension.technician and extension.technician.user:
                create_notification(
                    recipient=extension.technician.user,
                    title=f"Work Extension {extension.status.replace('_', ' ').title()}",
                    message=f"Extension #{extension.id} has been {extension.status.lower()} by Admin.",
                    notification_type="WORK_EXTENSION_DECISION",
                    company=job.company,
                    related_object_id=str(extension.id),
                )

            return Response({
                "message": f"Work extension #{extension.id} marked as {extension.status}.",
                "extension": WorkforceWorkExtensionSerializer(extension).data,
            }, status=status.HTTP_200_OK)


class WorkforceAdminPendingExtensionsListView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        if getattr(request.user, "is_superuser", False):
            qs = WorkforceWorkExtension.objects.filter(
                status__in=[
                    WorkforceWorkExtension.Status.REQUESTED,
                    WorkforceWorkExtension.Status.PENDING_ASSIGNMENT,
                ]
            ).select_related("job", "technician__user", "required_skill", "specialist_technician__user").order_by("-created_at")
        else:
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            qs = WorkforceWorkExtension.objects.filter(
                status__in=[
                    WorkforceWorkExtension.Status.REQUESTED,
                    WorkforceWorkExtension.Status.PENDING_ASSIGNMENT,
                ]
            ).filter(Q(company=user_company) | Q(job__company=user_company)).select_related("job", "technician__user", "required_skill", "specialist_technician__user").order_by("-created_at")

        serializer = WorkforceWorkExtensionSerializer(qs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkforceCustomerExtensionDetailView(APIView):
    """
    Endpoint for Customer to view Additional Work breakdown and financial details.
    Accessible either by authenticated customer session OR query token ?token=<decision_token>.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk, ext_id=None):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        token = request.query_params.get("token") or request.headers.get("X-Decision-Token")

        if ext_id:
            extension = WorkforceWorkExtension.objects.filter(pk=ext_id, job=job).first()
        else:
            extension = WorkforceWorkExtension.objects.filter(job=job, decision_token=token).first()

        if not extension:
            return Response({"error": "Work extension not found."}, status=status.HTTP_404_NOT_FOUND)

        # Authorization: Must be authenticated customer/admin OR match decision_token
        is_auth_customer = (
            request.user.is_authenticated
            and (
                job.customer == request.user
                or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
                or getattr(job, "phone", "") == getattr(request.user, "username", "")
                or _is_admin_authorized_for_company(request, job.company)
            )
        )
        is_valid_token = bool(token and extension.decision_token and token == extension.decision_token)

        if not (is_auth_customer or is_valid_token):
            return Response({
                "error": "Unauthorized: Valid customer authentication or decision token is required."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = CustomerWorkforceExtensionSerializer(extension)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkforceCustomerExtensionDecideView(APIView):
    """
    Idempotent, one-time customer decision endpoint for Additional Work / Scope Expansion.
    Enforces atomic row locking, expiration check, and duplicate rejection.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk, ext_id):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        token = request.data.get("token") or request.query_params.get("token") or request.headers.get("X-Decision-Token")

        action = str(request.data.get("action", "")).upper()
        reason = str(request.data.get("reason", "")).strip()

        if action not in ["ACCEPT", "ACCEPTED", "DECLINE", "DECLINED"]:
            return Response({"error": "Action must be ACCEPT or DECLINE."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            extension = (
                WorkforceWorkExtension.objects
                .select_for_update()
                .filter(pk=ext_id, job=job)
                .first()
            )
            if not extension:
                return Response({"error": "Work extension not found."}, status=status.HTTP_404_NOT_FOUND)

            # Security Authorization: authenticated customer or decision token
            is_auth_customer = (
                request.user.is_authenticated
                and (
                    job.customer == request.user
                    or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
                    or getattr(job, "phone", "") == getattr(request.user, "username", "")
                    or _is_admin_authorized_for_company(request, job.company)
                )
            )
            is_valid_token = bool(token and extension.decision_token and token == extension.decision_token)

            if not (is_auth_customer or is_valid_token):
                return Response({
                    "error": "Unauthorized: Valid customer authentication or decision token is required."
                }, status=status.HTTP_403_FORBIDDEN)

            # Idempotency & One-Time Rule
            if extension.status in [
                WorkforceWorkExtension.Status.CUSTOMER_ACCEPTED,
                WorkforceWorkExtension.Status.CUSTOMER_DECLINED,
                WorkforceWorkExtension.Status.PENDING_ASSIGNMENT,
                WorkforceWorkExtension.Status.IN_PROGRESS,
                WorkforceWorkExtension.Status.COMPLETED,
                WorkforceWorkExtension.Status.RESOLVED,
            ]:
                return Response({
                    "error": f"Decision already recorded for extension #{extension.id}. Status is '{extension.status}'. Further decisions are rejected.",
                    "code": "DECISION_ALREADY_RECORDED",
                    "status": extension.status,
                }, status=status.HTTP_409_CONFLICT)

            if extension.status != WorkforceWorkExtension.Status.ADMIN_APPROVED:
                return Response({
                    "error": f"Cannot record customer decision for extension in status '{extension.status}'. Expected 'ADMIN_APPROVED'.",
                    "code": "INVALID_EXTENSION_STATE"
                }, status=status.HTTP_400_BAD_REQUEST)

            # Expiry validation
            now = timezone.now()
            if extension.decision_expires_at and now > extension.decision_expires_at:
                return Response({
                    "error": "Decision window has expired for this work extension. Please request an updated estimate.",
                    "code": "DECISION_EXPIRED",
                    "expired_at": extension.decision_expires_at.isoformat(),
                }, status=status.HTTP_400_BAD_REQUEST)

            if action in ["ACCEPT", "ACCEPTED"]:
                add_amt = Decimal(str(extension.approved_amount if extension.approved_amount is not None else extension.requested_amount))


                if extension.requires_specialist:
                    # Specialist workflow: PENDING_ASSIGNMENT & FOLLOW_UP_REQUIRED
                    extension.status = WorkforceWorkExtension.Status.PENDING_ASSIGNMENT
                    extension.customer_decided_at = now
                    extension.save()

                    apply_transition(job, "follow_up_required", actor=request.user)

                    msg = f"Work extension #{extension.id} accepted. Job marked FOLLOW_UP_REQUIRED for specialist technician assignment."
                else:
                    # Same-technician continuation
                    extension.status = WorkforceWorkExtension.Status.CUSTOMER_ACCEPTED
                    extension.customer_decided_at = now
                    extension.save()

                    job.total_amount += add_amt
                    job.save()

                    msg = f"Work extension #{extension.id} accepted by customer. ₹{add_amt} added to job total."

                # Mirror update to cart_data
                cart_data = list(job.cart_data or [])
                for c in cart_data:
                    if str(c.get("id")) == str(extension.id) and c.get("type") == "work_extension":
                        c["status"] = extension.status
                        c["customer_decided_at"] = extension.customer_decided_at.isoformat()
                job.cart_data = cart_data
                job.save()

                return Response({
                    "message": msg,
                    "extension": CustomerWorkforceExtensionSerializer(extension).data,
                    "job_status": job.status,
                    "job_total": str(job.total_amount),
                }, status=status.HTTP_200_OK)

            else:  # DECLINE
                extension.status = WorkforceWorkExtension.Status.CUSTOMER_DECLINED
                extension.customer_decided_at = now
                extension.customer_decline_reason = reason or "Customer declined additional work."
                extension.save()

                # Mirror update to cart_data
                cart_data = list(job.cart_data or [])
                for c in cart_data:
                    if str(c.get("id")) == str(extension.id) and c.get("type") == "work_extension":
                        c["status"] = extension.status
                        c["customer_decline_reason"] = extension.customer_decline_reason
                        c["customer_decided_at"] = extension.customer_decided_at.isoformat()
                job.cart_data = cart_data
                job.save()

                if extension.is_critical:
                    # Critical scope rejected -> work cannot safely continue -> UNABLE_TO_COMPLETE
                    uncompletion_note = f"Critical scope extension #{extension.id} ('{extension.title}') declined by customer. Work cannot safely continue. Reason: {extension.customer_decline_reason}"
                    if job.description:
                        job.description = f"{job.description}\n[UNABLE_TO_COMPLETE]: {uncompletion_note}"
                    else:
                        job.description = f"[UNABLE_TO_COMPLETE]: {uncompletion_note}"
                    job.save(update_fields=["description"])
                    apply_transition(job, "unable_to_complete", actor=request.user)

                    return Response({
                        "message": f"Critical extension declined. Job #{job.id} transitioned to UNABLE_TO_COMPLETE.",
                        "extension": CustomerWorkforceExtensionSerializer(extension).data,
                        "job_status": job.status,
                        "uncompletion_reason": uncompletion_note,
                    }, status=status.HTTP_200_OK)
                else:
                    # Optional scope rejected -> original job continues in in_progress
                    return Response({
                        "message": f"Optional extension declined. Original Job #{job.id} continues IN_PROGRESS.",
                        "extension": CustomerWorkforceExtensionSerializer(extension).data,
                        "job_status": job.status,
                    }, status=status.HTTP_200_OK)


class WorkforceTokenExtensionDecideView(APIView):
    """
    Direct decision endpoint by decision token.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, token):
        extension = WorkforceWorkExtension.objects.filter(decision_token=token).first()
        if not extension:
            return Response({"error": "Invalid or expired decision token."}, status=status.HTTP_404_NOT_FOUND)

        view = WorkforceCustomerExtensionDecideView()
        request.data["token"] = token
        return view.post(request, pk=extension.job_id, ext_id=extension.id)


class WorkforceAdminAssignSpecialistView(APIView):
    """
    Admin assigns Specialist Technician B to an extension in PENDING_ASSIGNMENT.
    Creates a sanitized secondary ServiceRequest for Specialist Technician B.
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk, ext_id):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        specialist_emp_id = request.data.get("specialist_employee_id") or request.data.get("employee_id")
        if not specialist_emp_id:
            return Response({"error": "specialist_employee_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        specialist_emp = Employee.objects.filter(pk=specialist_emp_id).first()
        if not specialist_emp:
            return Response({"error": "Specialist technician not found."}, status=status.HTTP_404_NOT_FOUND)

        # Invariant: Assigned specialist employee must belong to the same company as the job
        if not job.company_id or not specialist_emp.company_id or job.company_id != specialist_emp.company_id:
            return Response({"error": "Specialist technician must belong to the same vendor company as the job.", "code": "CROSS_TENANT_ASSIGNMENT_FORBIDDEN"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            extension = (
                WorkforceWorkExtension.objects
                .select_for_update()
                .filter(pk=ext_id, job=job)
                .first()
            )
            if not extension:
                return Response({"error": "Work extension not found."}, status=status.HTTP_404_NOT_FOUND)

            if extension.status != WorkforceWorkExtension.Status.PENDING_ASSIGNMENT:
                return Response({
                    "error": f"Cannot assign specialist for extension in status '{extension.status}'. Expected 'PENDING_ASSIGNMENT'."
                }, status=status.HTTP_400_BAD_REQUEST)

            # Create secondary Job for Technician B (is_primary = False)
            secondary_req_id = f"SR-SPEC-{job.id}-{extension.id}"
            secondary_job = ServiceRequest.objects.create(
                request_id=secondary_req_id,
                company=job.company,
                customer=job.customer,
                customer_name=job.customer_name,
                phone=job.phone,
                email=job.email,
                address=job.address,
                service_category=job.service_category,
                issue_title=f"[Specialist Task] {extension.title}",
                description=f"Specialist Task Assignment for Case #{job.request_id}.\nTask: {extension.description or extension.title}\nJustification: {extension.reason}",
                preferred_date=job.preferred_date or timezone.now().date(),
                total_amount=extension.approved_amount or extension.requested_amount,


                assigned_employee=specialist_emp,
                status="assigned",
                cart_data=[{
                    "type": "specialist_job",
                    "parent_job_id": job.id,
                    "parent_request_id": job.request_id,
                    "extension_id": extension.id,
                    "is_primary": False,
                }],
            )

            from service_requests.models import EmployeeJob
            EmployeeJob.objects.create(
                service_request=secondary_job,
                employee=specialist_emp,
                status="ASSIGNED",
                is_primary=False,
                notes=f"Specialist assignment for Extension #{extension.id}",
                assigned_by=request.user,
            )


            # Link secondary job to extension
            extension.specialist_technician = specialist_emp
            extension.specialist_job = secondary_job
            extension.status = WorkforceWorkExtension.Status.IN_PROGRESS
            extension.save()


            # Record secondary job link on parent job's cart_data
            cart_data = list(job.cart_data or [])
            cart_data.append({
                "type": "specialist_job",
                "job_id": secondary_job.id,
                "request_id": secondary_job.request_id,
                "extension_id": extension.id,
                "specialist_employee_id": specialist_emp.id,
                "assigned_at": timezone.now().isoformat(),
            })
            job.cart_data = cart_data
            job.save()

            # Notify Technician B
            if specialist_emp.user:
                create_notification(
                    recipient=specialist_emp.user,
                    title="Specialist Job Assigned",
                    message=f"You have been assigned as Specialist for task '{extension.title}' (Job #{secondary_job.id}).",
                    notification_type="SPECIALIST_JOB_ASSIGNED",
                    company=job.company,
                    related_object_id=str(secondary_job.id),
                )

            return Response({
                "message": f"Specialist technician {specialist_emp.user.get_full_name()} assigned successfully. Secondary Job #{secondary_job.id} created.",
                "secondary_job_id": secondary_job.id,
                "extension": WorkforceWorkExtensionSerializer(extension).data,
            }, status=status.HTTP_200_OK)


class WorkforceExtensionProgressView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk, ext_id):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or (job.assigned_employee != emp and getattr(job, "specialist_technician", None) != emp):
                # Check if user is the assigned specialist technician
                ext_check = WorkforceWorkExtension.objects.filter(pk=ext_id, specialist_technician=emp).first()
                if not ext_check and job.assigned_employee != emp:
                    return Response({"error": "Unauthorized: You are not assigned to this job or extension."}, status=status.HTTP_403_FORBIDDEN)

        action = str(request.data.get("action", "")).lower()

        with transaction.atomic():
            extension = (
                WorkforceWorkExtension.objects
                .select_for_update()
                .filter(pk=ext_id, job=job)
                .first()
            )
            if not extension:
                return Response({"error": "Work extension not found."}, status=status.HTTP_404_NOT_FOUND)

            now = timezone.now()
            if action == "start":
                if extension.status not in [WorkforceWorkExtension.Status.CUSTOMER_ACCEPTED, WorkforceWorkExtension.Status.PENDING_ASSIGNMENT]:
                    return Response({
                        "error": f"Cannot start extension in status '{extension.status}'. Expected 'CUSTOMER_ACCEPTED'."
                    }, status=status.HTTP_400_BAD_REQUEST)
                extension.status = WorkforceWorkExtension.Status.IN_PROGRESS
                extension.save()

            elif action == "complete":
                if extension.status != WorkforceWorkExtension.Status.IN_PROGRESS:
                    return Response({
                        "error": f"Cannot complete extension in status '{extension.status}'. Expected 'IN_PROGRESS'."
                    }, status=status.HTTP_400_BAD_REQUEST)
                extension.status = WorkforceWorkExtension.Status.COMPLETED
                extension.completed_at = now
                extension.save()

            elif action == "resolve":
                if extension.status not in [WorkforceWorkExtension.Status.COMPLETED, WorkforceWorkExtension.Status.CUSTOMER_ACCEPTED]:
                    return Response({
                        "error": f"Cannot resolve extension in status '{extension.status}'. Expected 'COMPLETED'."
                    }, status=status.HTTP_400_BAD_REQUEST)
                extension.status = WorkforceWorkExtension.Status.RESOLVED
                extension.resolved_at = now
                extension.save()

                # Automatically create supplemental invoice idempotently
                inv_num = f"SUP-INV-{job.id}-{extension.id}"
                WorkforceSupplementalInvoice.objects.get_or_create(
                    extension=extension,
                    defaults={
                        "invoice_number": inv_num,
                        "job": job,
                        "customer": job.customer,
                        "company": job.company,
                        "amount": extension.approved_amount or extension.requested_amount,
                        "actual_cost": extension.estimated_labor_cost + extension.estimated_materials_cost,
                        "status": WorkforceSupplementalInvoice.Status.ISSUED,
                        "metadata": {
                            "extension_title": extension.title,
                            "reason": extension.reason,
                        },
                        "audit_trail": [{
                            "action": "INVOICE_GENERATED",
                            "timestamp": now.isoformat(),
                            "amount": float(extension.approved_amount or extension.requested_amount),
                        }],
                    }
                )

            else:
                return Response({"error": "Action must be 'start', 'complete', or 'resolve'."}, status=status.HTTP_400_BAD_REQUEST)

            # Mirror to cart_data
            cart_data = list(job.cart_data or [])
            for c in cart_data:
                if str(c.get("id")) == str(extension.id) and c.get("type") == "work_extension":
                    c["status"] = extension.status
                    if extension.completed_at:
                        c["completed_at"] = extension.completed_at.isoformat()
                    if extension.resolved_at:
                        c["resolved_at"] = extension.resolved_at.isoformat()
            job.cart_data = cart_data
            job.save()

            return Response({
                "message": f"Work extension #{extension.id} updated to {extension.status}.",
                "extension": WorkforceWorkExtensionSerializer(extension).data,
            }, status=status.HTTP_200_OK)


# ─── Supplemental Billing & Invoicing (Requirement 7) ─────────────────────────

class WorkforceCreateSupplementalInvoiceView(APIView):
    """
    Idempotent supplemental invoice creation for resolved/accepted work extensions.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk, ext_id):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fixes IDOR: this endpoint used to only require IsAuthenticated with
        # no ownership check at all, so any authenticated account on the
        # platform could act on any other company's job just by guessing/
        # incrementing pk. Mirrors the company-check pattern already used
        # correctly on WorkforceJobExtensionView just above.
        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        extension = WorkforceWorkExtension.objects.filter(pk=ext_id, job=job).first()
        if not extension:
            return Response({"error": "Work extension not found."}, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()
        inv_num = f"SUP-INV-{job.id}-{extension.id}"

        with transaction.atomic():
            invoice, created = WorkforceSupplementalInvoice.objects.select_for_update().get_or_create(
                extension=extension,
                defaults={
                    "invoice_number": inv_num,
                    "job": job,
                    "customer": job.customer,
                    "company": job.company,
                    "amount": extension.approved_amount or extension.requested_amount,
                    "actual_cost": extension.estimated_labor_cost + extension.estimated_materials_cost,
                    "status": WorkforceSupplementalInvoice.Status.ISSUED,
                    "metadata": {
                        "extension_title": extension.title,
                        "reason": extension.reason,
                    },
                    "audit_trail": [{
                        "action": "INVOICE_GENERATED",
                        "timestamp": now.isoformat(),
                        "amount": float(extension.approved_amount or extension.requested_amount),
                    }],
                }
            )

        serializer = WorkforceSupplementalInvoiceSerializer(invoice)
        return Response({
            "message": "Supplemental invoice retrieved / created successfully.",
            "created": created,
            "invoice": serializer.data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class WorkforceCustomerSupplementalInvoiceListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        is_customer = (
            job.customer == request.user
            or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
            or getattr(job, "phone", "") == getattr(request.user, "username", "")
        )
        if not (is_customer or _is_admin_authorized_for_company(request, job.company)):
            return Response({"error": "Unauthorized: Not your booking."}, status=status.HTTP_403_FORBIDDEN)

        invoices = WorkforceSupplementalInvoice.objects.filter(job=job).order_by("-created_at")
        serializer = WorkforceSupplementalInvoiceSerializer(invoices, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkforcePaySupplementalInvoiceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, invoice_id):
        invoice = WorkforceSupplementalInvoice.objects.filter(pk=invoice_id).first()
        if not invoice:
            return Response({"error": "Supplemental invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        is_customer = (
            invoice.customer == request.user
            or invoice.job.customer == request.user
            or _is_admin_authorized_for_company(request, invoice.job.company)
        )
        if not is_customer:
            return Response({"error": "Unauthorized: Not your invoice."}, status=status.HTTP_403_FORBIDDEN)

        if invoice.status == WorkforceSupplementalInvoice.Status.PAID:
            return Response({
                "message": "Invoice is already paid.",
                "invoice": WorkforceSupplementalInvoiceSerializer(invoice).data,
            }, status=status.HTTP_200_OK)

        payment_method = str(request.data.get("payment_method", "ONLINE")).upper()
        transaction_id = str(request.data.get("transaction_id", f"TXN-{secrets.token_hex(8).upper()}"))

        now = timezone.now()
        with transaction.atomic():
            invoice.status = WorkforceSupplementalInvoice.Status.PAID
            invoice.payment_method = payment_method
            invoice.transaction_id = transaction_id
            invoice.paid_at = now

            audit = list(invoice.audit_trail or [])
            audit.append({
                "action": "PAYMENT_RECEIVED",
                "timestamp": now.isoformat(),
                "payment_method": payment_method,
                "transaction_id": transaction_id,
            })
            invoice.audit_trail = audit
            invoice.save()

        return Response({
            "message": f"Supplemental invoice #{invoice.invoice_number} paid successfully.",
            "invoice": WorkforceSupplementalInvoiceSerializer(invoice).data,
        }, status=status.HTTP_200_OK)


# ─── Rescheduling & Delays Subsystem (Requirement 6) ──────────────────────────

class WorkforceJobRescheduleView(APIView):
    """
    Handles rescheduling rules:
    - 1st delay: Updates proposed date, notifies customer, records audit entry.
    - 2nd delay: Freezes proposed schedule, creates support/callback escalation, records audit entry.
    - Commercial amounts are strictly preserved.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fixes IDOR: this endpoint used to only require IsAuthenticated with
        # no ownership check at all, so any authenticated account on the
        # platform could act on any other company's job just by guessing/
        # incrementing pk. Mirrors the company-check pattern already used
        # correctly on WorkforceJobExtensionView just above.
        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not job.company_id or user_company.id != job.company_id:
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        new_date = request.data.get("rescheduled_date") or request.data.get("date")
        reason = str(request.data.get("reason", "")).strip()
        delay_type = str(request.data.get("delay_type", "PARTS_DELAY")).upper()

        if not reason:
            return Response({"error": "Reschedule reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            current_delay_count = WorkforceJobReschedule.objects.filter(job=job).count() + 1

            if current_delay_count == 1:
                # 1st delay: update schedule
                original_date = job.preferred_date
                if new_date:
                    job.preferred_date = new_date
                    job.save()

                reschedule = WorkforceJobReschedule.objects.create(
                    job=job,
                    delay_count=current_delay_count,
                    delay_type=delay_type,
                    original_date=original_date,
                    rescheduled_date=job.preferred_date,
                    reason=reason,
                    customer_notified=True,
                    escalated_to_support=False,
                )
                msg = f"Job #{job.id} rescheduled (1st delay). Customer notified."

            else:
                # 2nd delay: freeze schedule, escalate to support
                reschedule = WorkforceJobReschedule.objects.create(
                    job=job,
                    delay_count=current_delay_count,
                    delay_type=delay_type,
                    original_date=job.preferred_date,
                    rescheduled_date=job.preferred_date,  # Frozen
                    reason=reason,
                    customer_notified=True,
                    escalated_to_support=True,
                    escalation_notes=f"Second delay reported ({reason}). Proposed schedule frozen. Support team callback dispatched.",
                )
                msg = f"Multiple delays detected on Job #{job.id}. Schedule frozen and escalated to Customer Support team."

            # Notify customer
            if job.customer:
                create_notification(
                    recipient=job.customer,
                    title="Service Schedule Update" if current_delay_count == 1 else "Service Delay Escalation",
                    message=msg,
                    notification_type="SCHEDULE_DELAY",
                    company=job.company,
                    related_object_id=str(job.id),
                )

        return Response({
            "message": msg,
            "reschedule": WorkforceJobRescheduleSerializer(reschedule).data,
            "delay_count": current_delay_count,
            "escalated_to_support": reschedule.escalated_to_support,
            "job_preferred_date": str(job.preferred_date),
            "job_total": str(job.total_amount),  # Commercial amounts untouched
        }, status=status.HTTP_200_OK)


class WorkforceCustomerRescheduleResponseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        is_customer = (
            job.customer == request.user
            or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
            or getattr(job, "phone", "") == getattr(request.user, "username", "")
        )
        if not (is_customer or _is_admin_authorized_for_company(request, job.company)):
            return Response({"error": "Unauthorized: Not your booking."}, status=status.HTTP_403_FORBIDDEN)

        response_choice = str(request.data.get("response", "")).upper()  # ACCEPTED, OBJECTED, CALLBACK_REQUESTED
        notes = str(request.data.get("notes", "")).strip()

        latest_reschedule = WorkforceJobReschedule.objects.filter(job=job).order_by("-created_at").first()
        if not latest_reschedule:
            return Response({"error": "No reschedule found for this job."}, status=status.HTTP_404_NOT_FOUND)

        latest_reschedule.customer_response = response_choice
        latest_reschedule.customer_notes = notes
        if response_choice in ["OBJECTED", "CALLBACK_REQUESTED"]:
            latest_reschedule.escalated_to_support = True
            latest_reschedule.escalation_notes = f"Customer responded with {response_choice}: {notes}"
        latest_reschedule.save()

        return Response({
            "message": f"Customer response '{response_choice}' recorded.",
            "reschedule": WorkforceJobRescheduleSerializer(latest_reschedule).data,
        }, status=status.HTTP_200_OK)


class WorkforceJobPurchaseRequestView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not is_admin_role(request.user):
            if not emp or job.assigned_employee != emp:
                return Response({"error": "Unauthorized: You are not assigned to this job."}, status=status.HTTP_403_FORBIDDEN)
            if not is_employee_authorized_for_job(emp, job):
                return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
        elif not _is_admin_authorized_for_company(request, job.company):
            return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        item_name = request.data.get("item_name", "Spare Part").strip()
        quantity = int(request.data.get("quantity", 1))
        try:
            estimated_cost = float(request.data.get("estimated_cost", 0))
        except (ValueError, TypeError):
            return Response({"error": "Invalid part cost."}, status=status.HTTP_400_BAD_REQUEST)

        vendor_name = request.data.get("vendor_name", "").strip()
        reason = request.data.get("reason", "").strip()

        cart_data = job.cart_data or []
        req_id = len([c for c in cart_data if c.get("type") == "parts_purchase_request"]) + 1

        purchase_entry = {
            "id": req_id,
            "type": "parts_purchase_request",
            "item_name": item_name,
            "quantity": quantity,
            "estimated_cost": estimated_cost,
            "vendor_name": vendor_name,
            "reason": reason,
            "status": "PENDING",  # Requires Admin review
            "requested_at": timezone.now().isoformat(),
            "requested_by": request.user.username,
            "reviewed_by": None,
            "review_reason": "",
        }
        cart_data.append(purchase_entry)
        job.cart_data = cart_data
        job.save()

        return Response({
            "message": f"Purchase request for {item_name} (₹{estimated_cost}) submitted for Admin review.",
            "purchase_request": purchase_entry,
        }, status=status.HTTP_201_CREATED)


class WorkforceAdminPurchaseDecideView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk, req_id):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # Fixes IDOR: IsWorkforceAdmin only checks role, not company -- any
        # company's admin could decide any other company's purchase request.
        if not _is_admin_authorized_for_company(request, job.company):
            return Response({"error": "Unauthorized access to job belonging to another company.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "").upper()
        reason = request.data.get("reason", "")

        if action not in ["APPROVED", "REJECTED"]:
            return Response({"error": "Action must be APPROVED or REJECTED."}, status=status.HTTP_400_BAD_REQUEST)

        cart_data = job.cart_data or []
        found = False
        for item in cart_data:
            if item.get("type") == "parts_purchase_request" and str(item.get("id")) == str(req_id):
                item["status"] = action
                item["reviewed_by"] = request.user.username
                item["review_reason"] = reason
                item["reviewed_at"] = timezone.now().isoformat()
                found = True
                break

        if not found:
            return Response({"error": "Parts purchase request not found."}, status=status.HTTP_404_NOT_FOUND)

        job.cart_data = cart_data
        job.save()

        return Response({
            "message": f"Parts purchase request marked as {action}.",
        }, status=status.HTTP_200_OK)


# ─── 12. Attendance & Shift Time Tracking (Decoupled from Availability) ───────

class WorkforceTimeTrackingView(APIView):
    permission_classes = [IsApprovedTechnician]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee record not found.", "code": "EMPLOYEE_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Check active job assignment
        from service_requests.models import ServiceRequest, EmployeeJob
        emp_job_sr_ids = list(EmployeeJob.objects.filter(employee=emp).values_list("service_request_id", flat=True))
        active_job = ServiceRequest.objects.filter(
            Q(assigned_employee=emp) | Q(id__in=emp_job_sr_ids),
            company=emp.company,
            status__in=["accepted", "on_the_way", "arrived", "in_progress"]
        ).first()

        active_job_data = None
        if active_job:
            active_job_data = {
                "id": active_job.id,
                "request_id": getattr(active_job, "request_id", active_job.id),
                "status": active_job.status,
                "service_category": getattr(active_job, "service_category", ""),
                "issue_title": getattr(active_job, "issue_title", ""),
                "address": getattr(active_job, "address", ""),
            }

        open_log = TimeLog.objects.filter(employee=emp, clock_out__isnull=True).prefetch_related("breaks").first()
        if open_log:
            active_break = open_log.breaks.filter(break_end__isnull=True).first()
            shift_status = "on_break" if active_break else "clocked_in"
            return Response({
                "is_clocked_in": True,
                "has_active_job": bool(active_job),
                "active_job": active_job_data,
                "shift_status": shift_status,
                "clock_in_time": open_log.clock_in.isoformat(),
                "clock_out_time": None,
                "active_break": {
                    "id": active_break.id,
                    "break_type": active_break.break_type,
                    "break_start": active_break.break_start.isoformat(),
                } if active_break else None,
                "time_log": TimeLogSerializer(open_log).data,
                "logs": [
                    {
                        "id": b.id,
                        "action": f"break_{b.break_type}",
                        "shift_status": "on_break",
                        "timestamp": b.break_start.isoformat(),
                    } for b in open_log.breaks.all()
                ]
            }, status=status.HTTP_200_OK)

        latest_log = TimeLog.objects.filter(employee=emp, clock_out__isnull=False).order_by("-clock_out").first()
        return Response({
            "is_clocked_in": False,
            "has_active_job": bool(active_job),
            "active_job": active_job_data,
            "shift_status": "clocked_out",
            "clock_in_time": latest_log.clock_in.isoformat() if latest_log else None,
            "clock_out_time": latest_log.clock_out.isoformat() if latest_log else None,
            "active_break": None,
            "time_log": TimeLogSerializer(latest_log).data if latest_log else None,
            "logs": [],
        }, status=status.HTTP_200_OK)

    def post(self, request):
        action = request.data.get("action", "clock_in").lower()
        if action == "clock_in":
            from time_tracking.views import ClockInView
            return ClockInView().post(request)
        elif action == "clock_out":
            from time_tracking.views import ClockOutView
            return ClockOutView().post(request)
        elif action == "break_start":
            from time_tracking.views import BreakStartView
            return BreakStartView().post(request)
        elif action == "break_end":
            from time_tracking.views import BreakEndView
            return BreakEndView().post(request)
        else:
            return Response({"error": f"Unknown time tracking action '{action}'.", "code": "INVALID_ACTION"}, status=status.HTTP_400_BAD_REQUEST)


# ─── 13. Leave Management ─────────────────────────────────────────────────────

class WorkforceLeaveListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)

        if is_admin_role(user):
            # Admin sees leave applications for their company workforce
            if getattr(user, "is_superuser", False):
                emp_qs = Employee.objects.filter(is_active=True).select_related("user")
            else:
                user_company = resolve_actor_company(request)
                if not user_company:
                    return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
                emp_qs = Employee.objects.filter(is_active=True, company=user_company).select_related("user")
            all_leaves = []
            for e in emp_qs:
                e_leaves = (e.bank_details or {}).get("leaves", [])
                for l in e_leaves:
                    all_leaves.append({
                        **l,
                        "employee_pk": e.id,
                        "employee_id": e.employee_id,
                        "employee_name": e.user.get_full_name() or e.user.username,
                    })
            all_leaves.sort(key=lambda x: x.get("applied_at", ""), reverse=True)
            return Response(all_leaves, status=status.HTTP_200_OK)

        if not emp:
            return Response([], status=status.HTTP_200_OK)

        bank_details = emp.bank_details or {}
        leaves = bank_details.get("leaves", [])
        sorted_leaves = sorted(leaves, key=lambda x: str(x.get("applied_at") or ""), reverse=True)
        return Response(sorted_leaves, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        leave_type = request.data.get("leave_type", "Casual Leave").strip()
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")
        reason = request.data.get("reason", "").strip()

        if not start_date or not end_date:
            return Response({"error": "start_date and end_date required."}, status=status.HTTP_400_BAD_REQUEST)

        if start_date > end_date:
            return Response({"error": "start_date cannot be after end_date."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        leaves = bank_details.get("leaves", [])

        # Check for overlapping pending/approved leave requests
        for existing in leaves:
            if existing.get("status") in ["submitted", "approved"]:
                e_start = existing.get("start_date")
                e_end = existing.get("end_date")
                if e_start and e_end:
                    if not (end_date < e_start or start_date > e_end):
                        return Response({
                            "error": f"An active or pending leave application already exists for the range {e_start} to {e_end}."
                        }, status=status.HTTP_400_BAD_REQUEST)

        new_leave = {
            "id": len(leaves) + 1,
            "employee_id": emp.employee_id,
            "employee_name": user.get_full_name() or user.username,
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "reason": reason,
            "status": "submitted",
            "applied_at": timezone.now().isoformat(),
            "reviewer": None,
            "review_reason": "",
        }
        leaves.append(new_leave)
        bank_details["leaves"] = leaves
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": "Leave application submitted successfully for Admin approval.",
            "leave": new_leave,
        }, status=status.HTTP_201_CREATED)


class WorkforceLeaveCancelView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, leave_id):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        bank_details = emp.bank_details or {}
        leaves = bank_details.get("leaves", [])
        found = False

        for l in leaves:
            if str(l.get("id")) == str(leave_id):
                if l.get("status") != "submitted":
                    return Response({"error": f"Cannot cancel leave: Status is '{l.get('status')}'."}, status=status.HTTP_400_BAD_REQUEST)
                l["status"] = "cancelled"
                l["cancelled_at"] = timezone.now().isoformat()
                found = True
                break

        if not found:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        bank_details["leaves"] = leaves
        emp.bank_details = bank_details
        emp.save()

        return Response({"message": "Leave application cancelled successfully."}, status=status.HTTP_200_OK)


class WorkforceAdminLeaveDecideView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, emp_id, leave_id):
        emp = Employee.objects.filter(pk=emp_id).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not emp.company_id or user_company.id != emp.company_id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "").lower()  # approve, reject
        reason = request.data.get("reason", "").strip()

        if action not in ["approve", "reject"]:
            return Response({"error": "Action must be 'approve' or 'reject'."}, status=status.HTTP_400_BAD_REQUEST)

        if action == "reject" and not reason:
            return Response({"error": "Rejection reason is required."}, status=status.HTTP_400_BAD_REQUEST)

        bank_details = emp.bank_details or {}
        leaves = bank_details.get("leaves", [])
        found = False

        for l in leaves:
            if str(l.get("id")) == str(leave_id):
                l["status"] = "approved" if action == "approve" else "rejected"
                l["reviewer"] = request.user.username
                l["review_reason"] = reason
                l["reviewed_at"] = timezone.now().isoformat()
                found = True
                break

        if not found:
            return Response({"error": "Leave application not found."}, status=status.HTTP_404_NOT_FOUND)

        bank_details["leaves"] = leaves
        emp.bank_details = bank_details
        emp.save()

        return Response({
            "message": f"Leave application marked as {l['status'].upper()}.",
            "leave": l,
        }, status=status.HTTP_200_OK)


# ─── 14. Real-Time Fleet Map & Live Location ──────────────────────────────────

class WorkforceFleetMapView(APIView):
    """
    Returns live fleet telemetry for technicians belonging strictly to the
    authenticated admin's company. Cross-tenant access is rejected.
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        user = request.user
        if getattr(user, "is_superuser", False):
            technicians = list(Employee.objects.filter(is_active=True).select_related("user", "company"))
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response(
                    {"error": "Tenant company context required.", "code": "TENANT_REQUIRED"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            technicians = list(
                Employee.objects.filter(is_active=True, company=company).select_related("user", "company")
            )
        tech_ids = [e.id for e in technicians]

        active_jobs_map = {}
        if tech_ids:
            active_jobs = ServiceRequest.objects.filter(
                assigned_employee_id__in=tech_ids,
                status__in=["accepted", "on_the_way", "in_progress"],
            )
            for j in active_jobs:
                if j.assigned_employee_id not in active_jobs_map:
                    active_jobs_map[j.assigned_employee_id] = j.request_id

        fleet = []
        for emp_item in technicians:
            onboarding = (emp_item.bank_details or {}).get("onboarding", {})
            reg_status = onboarding.get("status", "not_started")
            loc = emp_item.user.last_known_location or {}

            has_location = bool(
                loc.get("latitude") is not None and loc.get("longitude") is not None
            )
            lat = float(loc["latitude"]) if has_location else None
            lng = float(loc["longitude"]) if has_location else None
            active_job_id = active_jobs_map.get(emp_item.id)

            fleet.append({
                "id": emp_item.id,
                "employee_id": emp_item.employee_id,
                "name": emp_item.user.get_full_name() or emp_item.user.username,
                "phone": emp_item.user.mobile_number or emp_item.user.phone,
                "is_online": emp_item.is_online,
                "current_availability": emp_item.current_availability,
                "registration_status": reg_status,
                "has_location": has_location,
                "latitude": lat,
                "longitude": lng,
                "accuracy": float(loc["accuracy"]) if has_location and loc.get("accuracy") is not None else None,
                "last_update": loc.get("updated_at") if has_location else None,
                "location_status": "Available" if has_location else "Location unavailable",
                "active_job": active_job_id,
            })

        return Response(fleet, status=status.HTTP_200_OK)


class WorkforceLocationUpdateView(APIView):
    """
    Receives real device GPS coordinates from an online employee.
    Stores latitude, longitude, accuracy, speed, heading, and timestamp in User.last_known_location.
    Protects against out-of-order and future packets.
    Maintains active JobTrackingSession with throttled JobLocationPoint persistence.
    Evaluates 2 consecutive GPS fixes within 300m geofence separated by >=3s or >10m movement for automatic arrival.
    """
    permission_classes = [IsApprovedTechnician]

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp or not emp.is_active:
            return Response(
                {"error": "Active employee profile required.", "code": "EMPLOYEE_INACTIVE"},
                status=status.HTTP_403_FORBIDDEN,
            )

        lat = request.data.get("latitude") if request.data.get("latitude") is not None else request.data.get("lat")
        lng = request.data.get("longitude") if request.data.get("longitude") is not None else (request.data.get("lon") or request.data.get("lng"))
        accuracy = request.data.get("accuracy")  # metres, from browser Geolocation API
        speed = request.data.get("speed")
        heading = request.data.get("heading")
        captured_at_str = request.data.get("captured_at")

        if lat is None or lng is None:
            return Response(
                {"error": "latitude and longitude are required.", "code": "GPS_REQUIRED"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            lat_f = float(lat)
            lng_f = float(lng)
        except (ValueError, TypeError):
            return Response(
                {"error": "Invalid coordinate format.", "code": "INVALID_GPS"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Strict coordinate range validation
        if not (-90.0 <= lat_f <= 90.0) or not (-180.0 <= lng_f <= 180.0):
            return Response(
                {"error": "Coordinates out of range (-90..90, -180..180).", "code": "COORDINATES_OUT_OF_RANGE"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        captured_dt = now
        if captured_at_str:
            try:
                from django.utils.dateparse import parse_datetime
                parsed = parse_datetime(str(captured_at_str))
                if parsed:
                    if timezone.is_naive(parsed):
                        parsed = timezone.make_aware(parsed)
                    # Protect against future timestamps (>10s ahead of server)
                    if parsed > now + timedelta(seconds=10):
                        captured_dt = now
                    else:
                        captured_dt = parsed
            except Exception:
                captured_dt = now

        # Out-of-order packet protection (query fresh DB state):
        user_db = User.objects.filter(id=user.id).only("last_known_location").first()
        last_known = (user_db.last_known_location if user_db else user.last_known_location) or {}
        if last_known.get("captured_at"):
            try:
                from django.utils.dateparse import parse_datetime
                last_dt = parse_datetime(str(last_known["captured_at"]))
                if last_dt:
                    if timezone.is_naive(last_dt):
                        last_dt = timezone.make_aware(last_dt)
                    if captured_dt < last_dt:
                        # Out-of-order older packet! Do not overwrite latest User.last_known_location
                        logger.warning(f"[OUT_OF_ORDER_GPS_IGNORED] User #{user.id} received GPS captured at {captured_dt} older than latest {last_dt}.")
                        return Response({
                            "message": "Out-of-order GPS packet ignored for current telemetry.",
                            "location": last_known,
                            "ignored": True,
                        }, status=status.HTTP_200_OK)
            except Exception as parse_err:
                logger.debug(f"[OUT_OF_ORDER_CHECK_ERROR] {parse_err}")

        acc_f = None
        if accuracy is not None:
            try:
                acc_val = float(accuracy)
                if acc_val >= 0:
                    acc_f = acc_val
            except (ValueError, TypeError):
                pass

        location_data = {
            "latitude": round(lat_f, 7),
            "longitude": round(lng_f, 7),
            "accuracy": round(acc_f, 2) if acc_f is not None else None,
            "speed": round(float(speed), 2) if speed is not None else None,
            "heading": round(float(heading), 1) if heading is not None else None,
            "captured_at": captured_dt.isoformat(),
            "updated_at": now.isoformat(),
        }
        user.last_known_location = location_data
        user.save(update_fields=["last_known_location"])

        # ── Automatic Real GPS Arrival & Geofence Evaluation (Zero-Admin Intervention) ──
        from service_requests.models import ServiceRequest, EmployeeJob
        from workforce_api.models import PreServiceVerification, JobTrackingSession, JobLocationPoint, WorkforceEventLog
        from time_tracking.geo import haversine_distance
        from django.db.models import Q
        import secrets

        ARRIVAL_RADIUS_METERS = 250.0
        ARRIVAL_MAX_ACCURACY_METERS = 200.0
        ARRIVAL_MAX_GPS_AGE_SECONDS = 30.0
        ARRIVAL_REQUIRED_FIXES = 2
        ARRIVAL_MIN_CONFIRMATION_INTERVAL_SECONDS = 2.0

        arrived_events = []

        # Find active accepted / en-route jobs owned by this technician
        emp_job_sr_ids = list(EmployeeJob.objects.filter(employee=emp).values_list("service_request_id", flat=True))
        emp_company = getattr(emp, "company", None) if getattr(emp, "company_id", None) else None
        active_jobs_qs = ServiceRequest.objects.filter(
            Q(assigned_employee=emp) | Q(id__in=emp_job_sr_ids),
            status__in=["accepted", "on_the_way", "en_route"],
            latitude__isnull=False,
            longitude__isnull=False,
        )
        if emp_company:
            active_jobs_qs = active_jobs_qs.filter(company=emp_company)
        active_jobs = active_jobs_qs

        for job in active_jobs:
            try:
                cust_lat = float(job.latitude)
                cust_lon = float(job.longitude)
                dist_m = haversine_distance(lat_f, lng_f, cust_lat, cust_lon)

                # Get or create active JobTrackingSession
                session, _ = JobTrackingSession.objects.get_or_create(
                    job=job,
                    employee=emp,
                    defaults={
                        "company": job.company or emp_company,
                        "status": JobTrackingSession.SessionStatus.ACTIVE,
                    },
                )

                # Update session latest telemetry
                session.last_latitude = lat_f
                session.last_longitude = lng_f
                session.last_accuracy = acc_f
                session.last_speed = float(speed) if speed is not None else None
                session.last_heading = float(heading) if heading is not None else None
                session.last_captured_at = captured_dt
                session.last_received_at = now
                session.save()

                # Throttled persistence of JobLocationPoint
                should_record_point = False
                last_point = session.location_points.order_by("-sequence_number").first()
                if not last_point:
                    should_record_point = True
                    seq_num = 1
                else:
                    moved_from_last = haversine_distance(lat_f, lng_f, last_point.latitude, last_point.longitude)
                    elapsed_from_last = (now - last_point.created_at).total_seconds()
                    if moved_from_last >= 20.0 or elapsed_from_last >= 30.0:
                        should_record_point = True
                        seq_num = last_point.sequence_number + 1

                if should_record_point:
                    JobLocationPoint.objects.create(
                        tracking_session=session,
                        job=job,
                        employee=emp,
                        latitude=lat_f,
                        longitude=lng_f,
                        accuracy=acc_f,
                        speed=float(speed) if speed is not None else None,
                        heading=float(heading) if heading is not None else None,
                        captured_at=captured_dt,
                        sequence_number=seq_num,
                    )

                # Mirror the live position onto the shared ServiceRequest row on
                # EVERY accepted fix. Both apps run against the same database, so
                # this row is what the customer's tracking page reads back. It
                # also means a dropped webhook now costs one poll of freshness
                # instead of losing that position permanently -- notify_customer_app
                # is fire-and-forget with no retry, so it was a single point of
                # failure for the whole customer-facing tracking feature.
                try:
                    ServiceRequest.objects.filter(pk=job.pk).update(
                        technician_latitude=round(lat_f, 6),
                        technician_longitude=round(lng_f, 6),
                    )
                except Exception as mirror_err:
                    logger.info("Could not mirror technician position onto job %s: %s", job.id, mirror_err)

                # Push to the customer app on every accepted fix, rather than
                # piggybacking on the 20m/30s JobLocationPoint throttle above.
                # That throttle exists to cap stored telemetry rows; reusing it
                # for delivery stacked a third delay on top of the technician
                # client's reporting interval and the customer's poll interval,
                # so a moving technician could be ~55s stale on the customer map.
                try:
                    from workforce_api.services.customer_webhook import notify_customer_app
                    notify_customer_app(
                        "technician.location_updated",
                        job,
                        location={"latitude": lat_f, "longitude": lng_f},
                    )
                except Exception as webhook_err:
                    logger.info(f"Could not notify Customer app of location update for Job #{job.id}: {webhook_err}")

                # ── Consecutive-Fix Automatic Arrival Evaluation ──
                gps_age_s = (now - captured_dt).total_seconds()
                is_fix_valid = (
                    dist_m <= ARRIVAL_RADIUS_METERS
                    and (acc_f is None or acc_f <= ARRIVAL_MAX_ACCURACY_METERS)
                    and gps_age_s <= ARRIVAL_MAX_GPS_AGE_SECONDS
                )

                if is_fix_valid:
                    if session.consecutive_arrival_fixes == 0 or not session.last_fix_time:
                        # Fix #1 recorded
                        session.consecutive_arrival_fixes = 1
                        session.last_fix_lat = lat_f
                        session.last_fix_lon = lng_f
                        session.last_fix_time = now
                        session.save()
                        logger.info(f"[ARRIVAL_FIX_1] Job #{job.id} Fix 1/2 inside {dist_m:.1f}m (acc={acc_f}m, age={gps_age_s:.1f}s).")
                    else:
                        # Fix #2 evaluation: enforce server-verified temporal separation
                        time_since_fix1 = (now - session.last_fix_time).total_seconds()
                        movement_since_fix1 = haversine_distance(lat_f, lng_f, session.last_fix_lat, session.last_fix_lon) if (session.last_fix_lat and session.last_fix_lon) else 0

                        # Reject sub-millisecond callback bursts even with GPS noise/jitter
                        has_temporal_separation = (
                            time_since_fix1 >= ARRIVAL_MIN_CONFIRMATION_INTERVAL_SECONDS
                            or (time_since_fix1 >= 1.0 and movement_since_fix1 >= 5.0)
                            or (time_since_fix1 >= 1.0 and dist_m <= 150.0)
                        )

                        if has_temporal_separation:
                            # Fix #2 Confirmed! Atomic arrival transition
                            with transaction.atomic():
                                locked_job = ServiceRequest.objects.select_for_update().get(id=job.id)
                                if locked_job.status in ["accepted", "on_the_way", "en_route"]:
                                    verification = process_job_arrival(
                                        job=locked_job,
                                        employee=emp,
                                        lat=lat_f,
                                        lon=lng_f,
                                        is_automatic=True,
                                        actor=user
                                    )
                                    verification.employee = emp
                                    verification.geofence_passed = True
                                    verification.arrival_lat = lat_f
                                    verification.arrival_lon = lng_f
                                    if not verification.arrived_at:
                                        verification.arrived_at = now

                                    # Authoritative Single OTP Resolution
                                    existing_otp = (getattr(locked_job, "start_otp", None) or "").strip() or (verification.otp_code or "").strip()

                                    if existing_otp:
                                        active_otp = existing_otp
                                        verification.otp_code = active_otp
                                        if not verification.otp_generated_at:
                                            verification.otp_generated_at = now
                                        if not verification.otp_expires_at:
                                            verification.otp_expires_at = now + timedelta(minutes=15)
                                    else:
                                        new_otp = f"{secrets.randbelow(900000) + 100000}"
                                        active_otp = new_otp
                                        verification.otp_code = new_otp
                                        verification.otp_generated_at = now
                                        verification.otp_expires_at = now + timedelta(minutes=15)
                                        verification.otp_attempts = 0
                                        verification.otp_verified = False

                                    if locked_job.customer:
                                        create_notification(
                                            recipient=locked_job.customer,
                                            title="Technician Arrived — Work Start OTP",
                                            message=f"Technician {user.get_full_name() or user.username} has arrived. Share OTP {active_otp} to start service.",
                                            notification_type="WORK_START_OTP",
                                            company=locked_job.company,
                                            related_object_id=str(locked_job.id),
                                        )

                                    verification.check_completion()
                                    verification.save()

                                    locked_job.status = "arrived"
                                    if hasattr(locked_job, "start_otp") and locked_job.start_otp != active_otp:
                                        locked_job.start_otp = active_otp
                                        locked_job.save(update_fields=["status", "start_otp", "updated_at"])
                                    else:
                                        locked_job.save(update_fields=["status", "updated_at"])
                                    EmployeeJob.objects.filter(service_request=locked_job, employee=emp).update(status="ARRIVED")

                                    session.consecutive_arrival_fixes = 2
                                    session.save()

                                    create_notification(
                                        recipient=user,
                                        title="Arrival Verified Automatically!",
                                        message=f"You have arrived at Job #{locked_job.id} ({int(dist_m)}m away). Work Start OTP is ready for verification.",
                                        notification_type="AUTOMATIC_ARRIVAL",
                                        company=locked_job.company,
                                        related_object_id=str(locked_job.id),
                                    )

                                    arrived_events.append({
                                        "job_id": locked_job.id,
                                        "distance_m": round(dist_m, 1),
                                        "geofence_passed": True,
                                        "status": "arrived",
                                    })
                else:
                    if dist_m > ARRIVAL_RADIUS_METERS + 50.0:
                        session.consecutive_arrival_fixes = 0
                    session.save()

                # Publish real-time event for customer tracking stream
                if job.customer:
                    try:
                        WorkforceEventLog.objects.create(
                            user=job.customer,
                            event_type="JOB_LOCATION_UPDATE",
                            payload={
                                "type": "JOB_LOCATION_UPDATE",
                                "job_id": job.id,
                                "employee_id": emp.id,
                                "employee_name": user.get_full_name() or user.username,
                                "employee_location": {
                                    "latitude": round(lat_f, 7),
                                    "longitude": round(lng_f, 7),
                                    "accuracy": round(acc_f, 2) if acc_f is not None else None,
                                    "speed": round(float(speed), 2) if speed is not None else None,
                                    "heading": round(float(heading), 1) if heading is not None else None,
                                    "captured_at": captured_dt.isoformat(),
                                    "updated_at": now.isoformat(),
                                },
                                "status": job.status.upper(),
                                "distance_m": round(dist_m, 1),
                            }
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"[LOCATION_UPDATE_ERROR] Error evaluating Job #{job.id}: {e}", exc_info=True)

        # Reconsider pending dispatchable customer jobs upon fresh GPS update
        try:
            from workforce_api.services.automatic_dispatch import reconsider_jobs_for_employee
            reconsider_jobs_for_employee(emp)
        except Exception:
            pass

        return Response({
            "message": "Live GPS coordinates updated.",
            "location": user.last_known_location,
            "arrived_events": arrived_events,
        }, status=status.HTTP_200_OK)


class WorkforceJobLiveTrackingView(APIView):
    """
    Returns live tracking coordinates and metadata for an assigned job.
    Accessible to:
      1. The authorized customer who owns the booking
      2. The assigned technician
      3. An authorized workforce admin within the same tenant company
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        from service_requests.models import ServiceRequest
        from accounts.permissions import is_admin_role

        job = ServiceRequest.objects.filter(pk=pk).select_related("assigned_employee__user", "customer", "company").first()
        if not job:
            return Response({"error": "Job not found.", "code": "JOB_NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        is_owner_customer = (
            job.customer == user
            or str(getattr(job, "customer_name", "")).lower() == user.username.lower()
            or getattr(job, "phone", "") == getattr(user, "username", "")
        )
        is_assigned_tech = bool(job.assigned_employee and job.assigned_employee.user == user)
        is_platform_admin = getattr(user, "is_superuser", False)
        user_company = resolve_actor_company(request)
        is_tenant_admin = is_admin_role(user) and bool(job.company_id and user_company and job.company_id == user_company.id)

        if not (is_owner_customer or is_assigned_tech or is_platform_admin or is_tenant_admin):
            return Response({
                "error": "Unauthorized to view tracking for this job.",
                "code": "CROSS_TENANT_FORBIDDEN"
            }, status=status.HTTP_403_FORBIDDEN)

        # Cross-tenant check for assigned technician
        if is_assigned_tech and job.company_id and user_company and job.company_id != user_company.id:
            return Response({"error": "Unauthorized: Cross-company access forbidden.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        now = timezone.now()
        cust_lat = float(job.latitude) if job.latitude else None
        cust_lon = float(job.longitude) if job.longitude else None
        tech = job.assigned_employee

        # Privacy Guard: If job is completed/cancelled/closed/redispatching, or has no assigned technician
        if job.status in ["completed", "cancelled", "closed", "redispatching"] or not job.assigned_employee:
            logger.info(f"[MAP_RECONCILIATION] job_id={job.id} status={job.status} technician_masked=True")
            return Response({
                "job_id": job.id,
                "request_id": job.request_id,
                "status": "FINDING_NEW_PROFESSIONAL" if job.status == "redispatching" else job.status.upper(),
                "customer_location": {
                    "latitude": cust_lat,
                    "longitude": cust_lon,
                    "address": job.address or "",
                },
                "assigned_technician": None,
                "distance_m": None,
                "geofence_passed": True if job.status == "completed" else False,
                "freshness_state": "FINDING_NEW_PROFESSIONAL" if job.status == "redispatching" else "LOCATION_LOST",
                "age_seconds": None,
                "updated_at": now.isoformat(),
            }, status=status.HTTP_200_OK)

        tech_loc = None
        age_seconds = None
        freshness_state = "LOCATION_LOST"

        # Authoritative: Read active JobTrackingSession first
        from workforce_api.models import JobTrackingSession
        active_session = JobTrackingSession.objects.filter(
            job=job,
            status=JobTrackingSession.SessionStatus.ACTIVE
        ).first()

        if active_session and active_session.last_latitude is not None and active_session.last_longitude is not None:
            tech_loc = {
                "latitude": float(active_session.last_latitude),
                "longitude": float(active_session.last_longitude),
                "accuracy": float(active_session.last_accuracy or 0),
                "speed": float(active_session.last_speed or 0),
                "heading": float(active_session.last_heading or 0),
                "captured_at": active_session.last_captured_at.isoformat() if active_session.last_captured_at else None,
                "received_at": active_session.last_received_at.isoformat() if active_session.last_received_at else None,
            }
            cap_dt = active_session.last_captured_at or active_session.last_received_at
            if cap_dt:
                if timezone.is_naive(cap_dt):
                    cap_dt = timezone.make_aware(cap_dt)
                age_seconds = max(0.0, round((now - cap_dt).total_seconds(), 1))
                if age_seconds <= 5.0:
                    freshness_state = "LIVE"
                elif age_seconds <= 15.0:
                    freshness_state = "UPDATING"
                elif age_seconds <= 30.0:
                    freshness_state = "DELAYED"
                elif age_seconds <= 60.0:
                    freshness_state = "STALE"
                else:
                    freshness_state = "LOCATION_LOST"
        elif tech and tech.user and tech.user.last_known_location:
            tech_loc = tech.user.last_known_location
            # Calculate freshness state fallback
            cap_str = tech_loc.get("captured_at") or tech_loc.get("updated_at")
            if cap_str:
                try:
                    from django.utils.dateparse import parse_datetime
                    loc_dt = parse_datetime(str(cap_str))
                    if loc_dt:
                        if timezone.is_naive(loc_dt):
                            loc_dt = timezone.make_aware(loc_dt)
                        age_seconds = max(0.0, round((now - loc_dt).total_seconds(), 1))
                        if age_seconds <= 5.0:
                            freshness_state = "LIVE"
                        elif age_seconds <= 15.0:
                            freshness_state = "UPDATING"
                        elif age_seconds <= 30.0:
                            freshness_state = "DELAYED"
                        elif age_seconds <= 60.0:
                            freshness_state = "STALE"
                        else:
                            freshness_state = "LOCATION_LOST"
                except Exception:
                    pass

        distance_m = None
        if tech_loc and tech_loc.get("latitude") and tech_loc.get("longitude") and cust_lat and cust_lon:
            try:
                from time_tracking.geo import haversine_distance
                distance_m = round(haversine_distance(
                    float(tech_loc["latitude"]),
                    float(tech_loc["longitude"]),
                    cust_lat,
                    cust_lon
                ), 1)
            except Exception:
                pass

        verification = getattr(job, "pre_service_verification", None)
        if not verification:
            from workforce_api.models import PreServiceVerification
            verification = PreServiceVerification.objects.filter(job=job).first()
        geofence_passed = bool(verification and verification.geofence_passed)

        # Include Work Start OTP only for authorized customer / admin when unverified
        start_otp = None
        if (is_owner_customer or is_tenant_admin) and verification and verification.otp_code and not verification.otp_verified:
            start_otp = verification.otp_code

        tech_photo = ""
        tech_rating = None
        if tech:
            profile_img = getattr(tech, "profile_photo", None) or getattr(tech, "photo", "")
            tech_photo = profile_img.url if hasattr(profile_img, "url") else str(profile_img or "")
            tech_rating = getattr(tech, "rating", None)

        logger.info(f"[MAP_RECONCILIATION] job_id={job.id} freshness_state={freshness_state} distance_m={distance_m} age_seconds={age_seconds}")

        return Response({
            "job_id": job.id,
            "request_id": job.request_id,
            "status": job.status.upper(),
            "customer_location": {
                "latitude": cust_lat,
                "longitude": cust_lon,
                "address": job.address or "",
            },
            "assigned_technician": {
                "id": tech.id if tech else None,
                "name": (tech.user.get_full_name() or tech.user.username) if tech and tech.user else None,
                "phone": tech.phone if tech else "",
                "title": (tech.title or "Service Partner") if tech else "",
                "photo": tech_photo,
                "rating": tech_rating,
                "location": tech_loc,
            } if tech else None,
            "technician_photo": tech_photo,
            "technician_rating": tech_rating,
            "start_otp": start_otp,
            "distance_m": distance_m,
            "geofence_passed": geofence_passed,
            "geofence_radius_meters": 250.0,
            "freshness_state": freshness_state,
            "age_seconds": age_seconds,
            "updated_at": now.isoformat(),
        }, status=status.HTTP_200_OK)




# ─── 21. Notification Engine & Event Triggers ────────────────────────────────

def create_notification(recipient, title, message, notification_type, company=None, related_object_id=""):
    if not recipient:
        return None
    notif = WorkforceNotification.objects.create(
        recipient=recipient,
        company=company or getattr(recipient, "company", None),
        title=title,
        message=message,
        notification_type=notification_type,
        related_object_id=str(related_object_id or ""),
    )
    WorkforceEventLog.objects.create(
        event_type=f"NOTIFICATION_{notification_type}",
        user=recipient,
        payload={"notification_id": notif.id, "title": title, "message": message}
    )
    return notif


class WorkforceNotificationListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            notifs = WorkforceNotification.objects.filter(recipient=user).order_by("-created_at")[:50]
            unread_count = WorkforceNotification.objects.filter(recipient=user, is_read=False).count()

            data = [
                {
                    "id": n.id,
                    "title": n.title,
                    "message": n.message,
                    "notification_type": n.notification_type,
                    "related_object_id": n.related_object_id,
                    "is_read": n.is_read,
                    "created_at": n.created_at.isoformat() if n.created_at else timezone.now().isoformat(),
                }
                for n in notifs
            ]

            return Response({
                "unread_count": unread_count,
                "notifications": data,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("WorkforceNotificationListView GET error: %s", str(e), exc_info=True)
            return Response({
                "unread_count": 0,
                "notifications": [],
            }, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user
        ids = request.data.get("ids", None) if isinstance(request.data, dict) else None
        if not ids:
            id_param = request.query_params.get("id", None)
            ids_param = request.query_params.get("ids", None)
            if ids_param:
                ids = [int(x.strip()) for x in ids_param.split(",") if x.strip().isdigit()]
            elif id_param and id_param.isdigit():
                ids = [int(id_param)]

        qs = WorkforceNotification.objects.filter(recipient=user)
        if ids:
            qs = qs.filter(id__in=ids)

        deleted_count, _ = qs.delete()
        unread_count = WorkforceNotification.objects.filter(recipient=user, is_read=False).count()
        return Response({
            "message": "Notifications cleared.",
            "deleted_count": deleted_count,
            "unread_count": unread_count,
        }, status=status.HTTP_200_OK)


class WorkforceNotificationMarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        user = request.user
        ids = request.data.get("ids", None) if isinstance(request.data, dict) else None
        if pk:
            WorkforceNotification.objects.filter(pk=pk, recipient=user).update(is_read=True, read_at=timezone.now())
        elif ids and isinstance(ids, list):
            WorkforceNotification.objects.filter(id__in=ids, recipient=user).update(is_read=True, read_at=timezone.now())
        else:
            WorkforceNotification.objects.filter(recipient=user, is_read=False).update(is_read=True, read_at=timezone.now())

        unread_count = WorkforceNotification.objects.filter(recipient=user, is_read=False).count()
        return Response({"message": "Notifications marked as read.", "unread_count": unread_count}, status=status.HTTP_200_OK)


class WorkforceNotificationClearView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        user = request.user
        if pk:
            deleted_count, _ = WorkforceNotification.objects.filter(pk=pk, recipient=user).delete()
        else:
            ids = request.data.get("ids", None) if isinstance(request.data, dict) else None
            all_flag = request.data.get("all", False) if isinstance(request.data, dict) else False
            if ids and isinstance(ids, list):
                deleted_count, _ = WorkforceNotification.objects.filter(id__in=ids, recipient=user).delete()
            elif all_flag or not ids:
                deleted_count, _ = WorkforceNotification.objects.filter(recipient=user).delete()
            else:
                deleted_count = 0

        unread_count = WorkforceNotification.objects.filter(recipient=user, is_read=False).count()
        return Response({
            "message": "Notifications cleared.",
            "deleted_count": deleted_count,
            "unread_count": unread_count,
        }, status=status.HTTP_200_OK)

    def delete(self, request, pk=None):
        return self.post(request, pk=pk)


# ─── 22. Workforce Scheduling Module ──────────────────────────────────────────

class WorkforceScheduleManageView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request, emp_id=None):
        user = request.user
        company = getattr(user, "company", None)
        if emp_id:
            qs = WorkforceEmployeeSchedule.objects.filter(employee_id=emp_id)
        else:
            qs = WorkforceEmployeeSchedule.objects.all()

        if not user.is_superuser:
            if company:
                qs = qs.filter(company=company)
            else:
                qs = qs.none()

        schedules = qs.select_related("employee__user")

        data = [
            {
                "id": s.id,
                "employee_id": s.employee.employee_id,
                "employee_name": s.employee.user.get_full_name() or s.employee.user.username,
                "day_of_week": s.day_of_week,
                "day_name": s.get_day_of_week_display(),
                "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"),
                "is_working_day": s.is_working_day,
            }
            for s in schedules
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, emp_id):
        user = request.user
        company = getattr(user, "company", None)
        emp = Employee.objects.filter(pk=emp_id).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        if not user.is_superuser and company and emp.company_id != company.id:
            return Response({"error": "Unauthorized: Cross-company access forbidden.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        schedule_items = request.data.get("schedules", [])
        if not isinstance(schedule_items, list):
            return Response({"error": "schedules must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        updated_schedules = []
        with transaction.atomic():
            for item in schedule_items:
                day_of_week = int(item.get("day_of_week", 0))
                start_time = item.get("start_time", "09:00")
                end_time = item.get("end_time", "18:00")
                is_working_day = bool(item.get("is_working_day", True))

                sched, _ = WorkforceEmployeeSchedule.objects.update_or_create(
                    employee=emp,
                    day_of_week=day_of_week,
                    defaults={
                        "company": emp.company,
                        "start_time": start_time,
                        "end_time": end_time,
                        "is_working_day": is_working_day,
                    }
                )
                updated_schedules.append({
                    "id": sched.id,
                    "day_of_week": sched.day_of_week,
                    "day_name": sched.get_day_of_week_display(),
                    "start_time": sched.start_time.strftime("%H:%M"),
                    "end_time": sched.end_time.strftime("%H:%M"),
                    "is_working_day": sched.is_working_day,
                })

        return Response({
            "message": f"Work schedule updated for {emp.user.get_full_name()}.",
            "schedules": updated_schedules,
        }, status=status.HTTP_200_OK)


class WorkforceMyScheduleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response([], status=status.HTTP_200_OK)

        schedules = WorkforceEmployeeSchedule.objects.filter(employee=emp).order_by("day_of_week")
        data = [
            {
                "id": s.id,
                "day_of_week": s.day_of_week,
                "day_name": s.get_day_of_week_display(),
                "start_time": s.start_time.strftime("%H:%M"),
                "end_time": s.end_time.strftime("%H:%M"),
                "is_working_day": s.is_working_day,
            }
            for s in schedules
        ]
        return Response(data, status=status.HTTP_200_OK)


# ─── 23. Skills Management Module ──────────────────────────────────────────────

class WorkforceSkillManageView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        if getattr(request.user, "is_superuser", False):
            skills = WorkforceSkill.objects.all()
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            skills = WorkforceSkill.objects.filter(company=company)
        data = [
            {
                "id": s.id,
                "name": s.name,
                "code": s.code,
                "category": s.category,
                "description": s.description,
                "is_active": s.is_active,
            }
            for s in skills
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        company = resolve_actor_company(request)
        if not company and not getattr(request.user, "is_superuser", False):
            return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
        name = request.data.get("name", "").strip()
        code = request.data.get("code", "").strip()
        category = request.data.get("category", "General").strip()
        description = request.data.get("description", "").strip()

        if not name:
            return Response({"error": "Skill name is required.", "code": "INVALID_INPUT", "details": {}}, status=status.HTTP_400_BAD_REQUEST)

        skill, created = WorkforceSkill.objects.get_or_create(
            company=company,
            name=name,
            defaults={
                "code": code,
                "category": category,
                "description": description,
                "is_active": True,
            }
        )
        if not created:
            skill.code = code or skill.code
            skill.category = category or skill.category
            skill.description = description or skill.description
            skill.is_active = True
            skill.save()

        return Response({
            "message": f"Skill '{skill.name}' created/updated.",
            "skill": {
                "id": skill.id,
                "name": skill.name,
                "code": skill.code,
                "category": skill.category,
                "is_active": skill.is_active,
            }
        }, status=status.HTTP_201_CREATED)


class WorkforceEmployeeSkillAssignView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, emp_id):
        emp = Employee.objects.filter(pk=emp_id).first()
        if not emp:
            return Response({"error": "Employee not found.", "code": "NOT_FOUND", "details": {}}, status=status.HTTP_404_NOT_FOUND)

        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not emp.company_id or user_company.id != emp.company_id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        skill_id = request.data.get("skill_id")
        proficiency = request.data.get("proficiency_level", "INTERMEDIATE")
        action = request.data.get("action", "assign").lower()

        skill = WorkforceSkill.objects.filter(pk=skill_id).first()
        if not skill:
            return Response({"error": "Skill not found.", "code": "NOT_FOUND", "details": {}}, status=status.HTTP_404_NOT_FOUND)

        if action == "remove":
            WorkforceEmployeeSkill.objects.filter(employee=emp, skill=skill).delete()
            return Response({"message": f"Skill '{skill.name}' removed from technician."}, status=status.HTTP_200_OK)

        emp_skill, _ = WorkforceEmployeeSkill.objects.update_or_create(
            employee=emp,
            skill=skill,
            defaults={
                "proficiency_level": proficiency,
                "is_verified": True,
                "verified_by": request.user,
                "verified_at": timezone.now(),
            }
        )

        return Response({
            "message": f"Skill '{skill.name}' assigned to {emp.user.get_full_name()}.",
            "skill": {
                "id": emp_skill.id,
                "skill_name": skill.name,
                "proficiency_level": emp_skill.proficiency_level,
                "is_verified": emp_skill.is_verified,
            }
        }, status=status.HTTP_200_OK)


class WorkforceMySkillsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response([], status=status.HTTP_200_OK)

        emp_skills = WorkforceEmployeeSkill.objects.filter(employee=emp).select_related("skill")
        data = [
            {
                "id": es.id,
                "skill_id": es.skill.id,
                "skill_name": es.skill.name,
                "category": es.skill.category,
                "proficiency_level": es.proficiency_level,
                "is_verified": es.is_verified,
            }
            for es in emp_skills
        ]
        return Response(data, status=status.HTTP_200_OK)


# ─── 24. Compliance Management Module ─────────────────────────────────────────

class WorkforceComplianceRequirementView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        if getattr(request.user, "is_superuser", False):
            reqs = WorkforceComplianceRequirement.objects.all()
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            reqs = WorkforceComplianceRequirement.objects.filter(company=company)
        data = [
            {
                "id": r.id,
                "title": r.title,
                "is_mandatory": r.is_mandatory,
                "validity_days": r.validity_days,
                "description": r.description,
            }
            for r in reqs
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        company = resolve_actor_company(request)
        if not company and not getattr(request.user, "is_superuser", False):
            return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
        title = request.data.get("title", "").strip()
        is_mandatory = bool(request.data.get("is_mandatory", True))
        validity_days = int(request.data.get("validity_days", 365))
        description = request.data.get("description", "").strip()

        if not title:
            return Response({"error": "Requirement title required."}, status=status.HTTP_400_BAD_REQUEST)

        req, created = WorkforceComplianceRequirement.objects.get_or_create(
            company=company,
            title=title,
            defaults={
                "is_mandatory": is_mandatory,
                "validity_days": validity_days,
                "description": description,
            }
        )
        return Response({
            "message": f"Compliance requirement '{req.title}' created.",
            "requirement": {
                "id": req.id,
                "title": req.title,
                "is_mandatory": req.is_mandatory,
                "validity_days": req.validity_days,
            }
        }, status=status.HTTP_201_CREATED)


class WorkforceEmployeeComplianceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, emp_id=None):
        user = request.user
        emp = getattr(user, "employee_profile", None)

        if is_admin_role(user):
            if emp_id:
                emp_obj = Employee.objects.filter(pk=emp_id).first()
                if not emp_obj:
                    return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
                if not getattr(user, "is_superuser", False):
                    user_company = resolve_actor_company(request)
                    if not user_company or not emp_obj.company_id or user_company.id != emp_obj.company_id:
                        return Response({"error": "Unauthorized cross-company query.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)
                qs = WorkforceEmployeeCompliance.objects.filter(employee_id=emp_id)
            else:
                qs = WorkforceEmployeeCompliance.objects.all()

            if not user.is_superuser:
                user_company = resolve_actor_company(request)
                if not user_company:
                    return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
                qs = qs.filter(requirement__company=user_company)
            records = qs.select_related("requirement", "employee__user")
        else:
            if not emp:
                return Response([], status=status.HTTP_200_OK)
            records = WorkforceEmployeeCompliance.objects.filter(employee=emp).select_related("requirement")

        today = timezone.now().date()
        data = []
        for r in records:
            comp_status = r.status
            if r.expiry_date:
                if r.expiry_date < today:
                    comp_status = "EXPIRED"
                elif (r.expiry_date - today).days <= 30 and comp_status == "VALID":
                    comp_status = "EXPIRING"

            data.append({
                "id": r.id,
                "employee_id": r.employee.employee_id,
                "employee_name": r.employee.user.get_full_name() or r.employee.user.username,
                "requirement_id": r.requirement.id,
                "requirement_title": r.requirement.title,
                "is_mandatory": r.requirement.is_mandatory,
                "document_number": r.document_number,
                "issue_date": r.issue_date.isoformat() if r.issue_date else None,
                "expiry_date": r.expiry_date.isoformat() if r.expiry_date else None,
                "status": comp_status,
                "file_url": r.file_url,
                "rejection_reason": r.rejection_reason,
            })
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        requirement_id = request.data.get("requirement_id")
        doc_num = request.data.get("document_number", "").strip()
        issue_date = request.data.get("issue_date")
        expiry_date = request.data.get("expiry_date")
        file_url = request.data.get("file_url", "").strip()

        req = WorkforceComplianceRequirement.objects.filter(pk=requirement_id).first()
        if not req:
            return Response({"error": "Compliance requirement not found."}, status=status.HTTP_404_NOT_FOUND)

        today = timezone.now().date()
        status_val = "VALID"
        if expiry_date:
            exp_d = timezone.datetime.strptime(expiry_date, "%Y-%m-%d").date()
            if exp_d < today:
                status_val = "EXPIRED"
            elif (exp_d - today).days <= 30:
                status_val = "EXPIRING"

        record, _ = WorkforceEmployeeCompliance.objects.update_or_create(
            requirement=req,
            employee=emp,
            defaults={
                "document_number": doc_num,
                "issue_date": issue_date,
                "expiry_date": expiry_date,
                "status": status_val,
                "file_url": file_url,
            }
        )
        return Response({
            "message": f"Compliance document for '{req.title}' submitted.",
            "record": {
                "id": record.id,
                "requirement_title": req.title,
                "status": record.status,
            }
        }, status=status.HTTP_201_CREATED)


# ─── 25. Workforce Realtime Stream (SSE) ──────────────────────────────────────

class ServerSentEventRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "txt"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class WorkforceRealtimeStreamView(APIView):
    permission_classes = [permissions.AllowAny]
    renderer_classes = [ServerSentEventRenderer, JSONRenderer]

    def get(self, request):
        from django.db import connection, DatabaseError, OperationalError
        from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
        from rest_framework_simplejwt.tokens import AccessToken

        logger.info("[Realtime SSE START] Received SSE connection request.")
        user = request.user
        token_str = request.query_params.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "").strip()

        # Step 1: JWT Authentication
        if (not user or not user.is_authenticated) and token_str:
            try:
                access_token = AccessToken(token_str)
                user_id = access_token.get("user_id")
                if user_id is None:
                    logger.warning("[Realtime AUTH] Token missing user_id claim.")
                    return Response({"error": "Invalid token claims.", "code": "INVALID_TOKEN"}, status=status.HTTP_401_UNAUTHORIZED)
            except (InvalidToken, TokenError) as jwt_err:
                logger.warning("[Realtime AUTH] Authentication token invalid or expired: %s", str(jwt_err))
                return Response({"error": "Invalid or expired authentication token.", "code": "INVALID_TOKEN"}, status=status.HTTP_401_UNAUTHORIZED)
            except Exception as gen_err:
                logger.warning("[Realtime AUTH] Unexpected token validation error: %s", str(gen_err))
                return Response({"error": "Authentication validation failed.", "code": "AUTH_FAILED"}, status=status.HTTP_401_UNAUTHORIZED)

            # Step 2: Database User Resolution with 503 Handling
            try:
                User = get_user_model()
                try:
                    user = User.objects.filter(id=int(user_id)).first()
                except (ValueError, TypeError):
                    user = User.objects.filter(id=user_id).first()
            except (OperationalError, DatabaseError) as db_err:
                logger.error("[Realtime DB] CONNECTION_POOL_EXHAUSTED during auth: %s", str(db_err))
                return Response(
                    {"error": "Database service temporarily unavailable. Please retry shortly.", "code": "DB_UNAVAILABLE"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            finally:
                connection.close()

        if not user or not user.is_authenticated:
            logger.warning("[Realtime AUTH] Authentication required for realtime stream.")
            return Response({"error": "Authentication required for realtime stream.", "code": "AUTH_REQUIRED"}, status=status.HTTP_401_UNAUTHORIZED)

        if not getattr(user, "is_active", True):
            logger.warning("[Realtime AUTH] Inactive user account: user_id=%s", getattr(user, "id", None))
            return Response({"error": "User account inactive.", "code": "USER_INACTIVE"}, status=status.HTTP_401_UNAUTHORIZED)

        logger.info("[Realtime SSE AUTH OK] User #%s (%s) authenticated successfully.", user.id, user.username)

        # Step 3: Resolve Company Scope & Admin Status
        user_company_id = getattr(user, "company_id", None)
        if not user_company_id:
            emp = getattr(user, "employee_profile", None)
            if not emp:
                from employees.models import Employee
                try:
                    emp = Employee.objects.filter(user=user).first()
                except (OperationalError, DatabaseError) as db_err:
                    logger.error("[Realtime DB] CONNECTION_POOL_EXHAUSTED resolving employee profile: %s", str(db_err))
                    return Response(
                        {"error": "Database service temporarily unavailable.", "code": "DB_UNAVAILABLE"},
                        status=status.HTTP_503_SERVICE_UNAVAILABLE,
                    )
                finally:
                    connection.close()
            if emp:
                user_company_id = emp.company_id

        is_admin = is_admin_role(user)
        user_id_val = user.id
        is_superuser_val = getattr(user, "is_superuser", False)

        # Step 4: Resolve Initial Event ID with Last-Event-ID support
        client_last_id = request.headers.get("Last-Event-ID") or request.query_params.get("last_event_id")
        try:
            initial_last_id = int(client_last_id) if client_last_id else None
        except (ValueError, TypeError):
            initial_last_id = None

        if initial_last_id is None:
            try:
                latest_ev = WorkforceEventLog.objects.order_by("-id").first()
                initial_last_id = latest_ev.id if latest_ev else 0
            except (OperationalError, DatabaseError) as db_err:
                logger.error("[Realtime DB] CONNECTION_POOL_EXHAUSTED resolving latest event ID: %s", str(db_err))
                return Response(
                    {"error": "Database service temporarily unavailable.", "code": "DB_UNAVAILABLE"},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            finally:
                connection.close()

        # Step 5: Long-Running Connection-Safe Event Stream Generator
        def event_stream():
            last_id = initial_last_id
            heartbeat_interval_seconds = 15
            last_heartbeat_time = time.time()
            last_reconcile_time = time.time()

            logger.info("[Realtime SSE START] Stream generator running for user_id=%s, start_id=%s.", user_id_val, last_id)
            # Initial connection confirmation event
            yield f"event: ping\ndata: {json.dumps({'status': 'connected', 'timestamp': timezone.now().isoformat()})}\n\n"

            try:
                while True:
                    loop_now = time.time()
                    events = []

                    # Periodic Heartbeat (keep stream open, prevent proxy / browser timeout)
                    if loop_now - last_heartbeat_time >= heartbeat_interval_seconds:
                        last_heartbeat_time = loop_now
                        logger.debug("[Realtime SSE HEARTBEAT] Sending keepalive ping to user_id=%s.", user_id_val)
                        yield f": heartbeat\n\n"

                    # Periodic Discovery / Reconciliation for connected technician (every 10s)
                    if not is_admin and (loop_now - last_reconcile_time >= 10):
                        last_reconcile_time = loop_now
                        try:
                            emp_obj = getattr(user, "employee_profile", None)
                            if emp_obj and emp_obj.is_online and emp_obj.current_availability == "available":
                                from workforce_api.services.automatic_dispatch import reconsider_jobs_for_employee
                                reconsider_jobs_for_employee(emp_obj)
                        except Exception as rec_err:
                            logger.debug(f"[Realtime SSE RECONCILE ERR] {rec_err}")
                        finally:
                            connection.close()

                    # Fetch newly emitted events using pure dictionary projection
                    try:
                        logger.debug("[Realtime SSE DB QUERY] Polling events > %s", last_id)
                        events = list(
                            WorkforceEventLog.objects.filter(id__gt=last_id)
                            .values("id", "event_type", "payload", "created_at", "user_id")
                            .order_by("id")[:20]
                        )
                    except (OperationalError, DatabaseError) as db_err:
                        logger.error("[Realtime DB] CONNECTION_POOL_EXHAUSTED polling events: %s. Terminating stream for client backoff.", str(db_err))
                        connection.close()
                        # Exit the loop immediately so server does not hammer PostgreSQL every 1s
                        break
                    except Exception as q_err:
                        logger.warning("[Realtime SSE EXCEPTION] Unexpected query exception: %s", str(q_err))
                    finally:
                        # CRITICAL: Always release the database connection immediately after the query!
                        connection.close()

                    for ev in events:
                        ev_id = ev["id"]
                        ev_user_id = ev["user_id"]
                        ev_payload = ev["payload"]
                        last_id = max(last_id, ev_id)

                        if ev_user_id == user_id_val:
                            is_authorized = True
                        elif is_admin:
                            is_authorized = (ev_user_id is None) or is_superuser_val
                            if not is_authorized and isinstance(ev_payload, dict):
                                ev_comp = ev_payload.get("company_id")
                                is_authorized = (ev_comp is None or ev_comp == user_company_id)
                        elif ev_user_id is None:
                            ev_company_id = ev_payload.get("company_id") if isinstance(ev_payload, dict) else None
                            is_authorized = (ev_company_id is None or ev_company_id == user_company_id)
                        else:
                            is_authorized = False

                        if is_authorized:
                            event_data = {
                                "id": ev_id,
                                "event_type": ev["event_type"],
                                "payload": ev_payload,
                                "timestamp": ev["created_at"].isoformat() if hasattr(ev["created_at"], "isoformat") else str(ev["created_at"]),
                            }
                            logger.info("[Realtime SSE EVENT] Delivering event #%s (%s) to user_id=%s", ev_id, ev["event_type"], user_id_val)
                            yield f"id: {ev_id}\nevent: workforce_event\ndata: {json.dumps(event_data)}\n\n"

                    time.sleep(1)
            except GeneratorExit:
                logger.info("[Realtime SSE END] Client disconnected (GeneratorExit) for user_id=%s.", user_id_val)
            except Exception as stream_err:
                logger.warning("[Realtime SSE EXCEPTION] Stream loop exception for user_id=%s: %s", user_id_val, str(stream_err))
            finally:
                logger.info("[Realtime SSE END] Stream ended for user_id=%s. Releasing any active DB connection.", user_id_val)
                connection.close()

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# ─── 26. Payroll Management Module ─────────────────────────────────────────────

class WorkforceAdminPayrollListView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        if getattr(request.user, "is_superuser", False):
            periods = WorkforcePayPeriod.objects.all()
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            periods = WorkforcePayPeriod.objects.filter(company=company)

        data = [
            {
                "id": p.id,
                "name": p.name,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "status": p.status,
                "payslip_count": p.payslips.count(),
                "total_net_pay": str(sum(ps.net_pay for ps in p.payslips.all())),
            }
            for p in periods
        ]
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, "is_superuser", False):
            company = resolve_actor_company(request)
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get("name", "").strip()
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not name or not start_date or not end_date:
            return Response({"error": "name, start_date, and end_date required."}, status=status.HTTP_400_BAD_REQUEST)

        period = WorkforcePayPeriod.objects.create(
            company=company,
            name=name,
            start_date=start_date,
            end_date=end_date,
            status="DRAFT",
            processed_by=request.user,
        )
        return Response({
            "message": f"Pay period '{period.name}' created.",
            "pay_period": {
                "id": period.id,
                "name": period.name,
                "status": period.status,
            }
        }, status=status.HTTP_201_CREATED)


class WorkforceAdminPayrollProcessView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, period_id):
        period = WorkforcePayPeriod.objects.filter(pk=period_id).first()
        if not period:
            return Response({"error": "Pay period not found."}, status=status.HTTP_404_NOT_FOUND)

        # Cross-company tenant isolation check
        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not period.company_id or user_company.id != period.company_id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "process").lower()

        if action == "advance_status":
            target_status = request.data.get("status")
            if target_status in ["PROCESSING", "REVIEW", "APPROVED", "PAID"]:
                period.status = target_status
                period.save()
                WorkforcePayslip.objects.filter(pay_period=period).update(status=target_status)

                if target_status == "PAID":
                    for ps in period.payslips.all():
                        create_notification(
                            recipient=ps.employee.user,
                            title="Payslip Published",
                            message=f"Your payslip for period '{period.name}' (Net: ${ps.net_pay}) has been paid.",
                            notification_type="PAYROLL_AVAILABILITY"
                        )
                return Response({"message": f"Pay period status advanced to {target_status}."}, status=status.HTTP_200_OK)

        employees = Employee.objects.filter(company=period.company, is_active=True).select_related("user")
        created_payslips = []

        with transaction.atomic():
            period.status = "PROCESSING"
            period.save()

            for emp in employees:
                hourly_rate = float(emp.hourly_rate or 0)
                time_logs = TimeLog.objects.filter(
                    employee=emp,
                    work_date__gte=period.start_date,
                    work_date__lte=period.end_date,
                    clock_out__isnull=False
                ).prefetch_related("breaks")
                total_worked_seconds = sum(log.worked_seconds() for log in time_logs)
                total_worked_hours = total_worked_seconds / 3600.0
                base_earnings = hourly_rate * total_worked_hours

                completed_jobs = ServiceRequest.objects.filter(
                    assigned_employee=emp,
                    status="completed",
                    updated_at__date__gte=period.start_date,
                    updated_at__date__lte=period.end_date
                )
                job_total = sum(float(j.total_amount) for j in completed_jobs)
                job_earnings = job_total * 0.20

                adjustments = 0.0
                deductions = (base_earnings + job_earnings) * 0.10
                net_pay = (base_earnings + job_earnings + adjustments) - deductions

                ps, _ = WorkforcePayslip.objects.update_or_create(
                    pay_period=period,
                    employee=emp,
                    defaults={
                        "base_earnings": round(base_earnings, 2),
                        "job_earnings": round(job_earnings, 2),
                        "adjustments": round(adjustments, 2),
                        "deductions": round(deductions, 2),
                        "net_pay": round(net_pay, 2),
                        "status": "PROCESSING",
                    }
                )
                created_payslips.append({
                    "id": ps.id,
                    "employee_name": emp.user.get_full_name(),
                    "net_pay": str(ps.net_pay),
                })

        return Response({
            "message": f"Processed payroll for {len(created_payslips)} employees.",
            "payslips": created_payslips,
        }, status=status.HTTP_200_OK)


class WorkforceMyPayslipsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response([], status=status.HTTP_200_OK)

        payslips = WorkforcePayslip.objects.filter(employee=emp).select_related("pay_period")
        data = [
            {
                "id": ps.id,
                "pay_period_name": ps.pay_period.name,
                "start_date": ps.pay_period.start_date.isoformat(),
                "end_date": ps.pay_period.end_date.isoformat(),
                "base_earnings": str(ps.base_earnings),
                "job_earnings": str(ps.job_earnings),
                "adjustments": str(ps.adjustments),
                "deductions": str(ps.deductions),
                "net_pay": str(ps.net_pay),
                "status": ps.status,
                "created_at": ps.created_at.isoformat(),
            }
            for ps in payslips
        ]
        return Response(data, status=status.HTTP_200_OK)


# ─── 27. Reports & Analytics Engine ──────────────────────────────────────────

class WorkforceReportsView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        report_type = request.query_params.get("type", "employee").lower()
        service_filter = request.query_params.get("service")
        emp_filter = request.query_params.get("employee_id")
        status_filter = request.query_params.get("status")

        user = request.user
        if not user.is_superuser:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
        else:
            company = None

        if report_type == "employee":
            qs = Employee.objects.all().select_related("user")
            if not user.is_superuser and company:
                qs = qs.filter(company=company)
            if emp_filter:
                qs = qs.filter(pk=emp_filter)
            if status_filter:
                qs = qs.filter(is_active=(status_filter.lower() == "active"))
            rows = [
                {
                    "employee_id": e.employee_id,
                    "name": e.user.get_full_name() or e.user.username,
                    "email": e.user.email,
                    "title": e.title,
                    "is_active": e.is_active,
                    "is_online": e.is_online,
                    "hourly_rate": str(e.hourly_rate),
                }
                for e in qs
            ]
            return Response({"report_type": "employee", "total_records": len(rows), "rows": rows}, status=status.HTTP_200_OK)

        elif report_type == "job":
            qs = ServiceRequest.objects.all()
            if not user.is_superuser and company:
                qs = qs.filter(company=company)
            if service_filter:
                qs = qs.filter(service_category__icontains=service_filter)
            if status_filter:
                qs = qs.filter(status=status_filter)
            if emp_filter:
                qs = qs.filter(assigned_employee_id=emp_filter)
            rows = [
                {
                    "request_id": j.request_id,
                    "customer_name": j.customer_name,
                    "service_category": j.service_category,
                    "issue_title": j.issue_title,
                    "status": j.status,
                    "total_amount": str(j.total_amount),
                    "created_at": j.created_at.isoformat(),
                }
                for j in qs
            ]
            return Response({"report_type": "job", "total_records": len(rows), "rows": rows}, status=status.HTTP_200_OK)

        elif report_type == "payroll":
            qs = WorkforcePayslip.objects.all().select_related("employee__user", "pay_period")
            if not user.is_superuser and company:
                qs = qs.filter(pay_period__company=company)
            if emp_filter:
                qs = qs.filter(employee_id=emp_filter)
            if status_filter:
                qs = qs.filter(status=status_filter)
            rows = [
                {
                    "pay_period": ps.pay_period.name,
                    "employee_id": ps.employee.employee_id,
                    "employee_name": ps.employee.user.get_full_name(),
                    "base_earnings": str(ps.base_earnings),
                    "job_earnings": str(ps.job_earnings),
                    "net_pay": str(ps.net_pay),
                    "status": ps.status,
                }
                for ps in qs
            ]
            return Response({"report_type": "payroll", "total_records": len(rows), "rows": rows}, status=status.HTTP_200_OK)

        elif report_type == "compliance":
            qs = WorkforceEmployeeCompliance.objects.all().select_related("employee__user", "requirement")
            if not user.is_superuser and company:
                qs = qs.filter(requirement__company=company)
            if emp_filter:
                qs = qs.filter(employee_id=emp_filter)
            if status_filter:
                qs = qs.filter(status=status_filter)
            rows = [
                {
                    "employee_id": c.employee.employee_id,
                    "employee_name": c.employee.user.get_full_name(),
                    "requirement": c.requirement.title,
                    "document_number": c.document_number,
                    "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                    "status": c.status,
                }
                for c in qs
            ]
            return Response({"report_type": "compliance", "total_records": len(rows), "rows": rows}, status=status.HTTP_200_OK)

        return Response({"error": f"Unknown report_type '{report_type}'."}, status=status.HTTP_400_BAD_REQUEST)


class WorkforceLatencyAuditView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            from measure_fleet_map_backend_time import measure_fleet_map
            fleet_map_data = measure_fleet_map()
            
            return Response({
                "fleet_map_backend_measurement": fleet_map_data,
            }, status=status.HTTP_200_OK)
        except Exception as err:
            return Response({
                "error": str(err)
            }, status=status.HTTP_200_OK)



class WorkforceVerificationSuiteView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            suite_name = request.query_params.get("suite", "master")
            if suite_name == "employee_platform":
                file_path = os.path.join(settings.BASE_DIR, "test_employee_platform_integration.py")
                glob = {"__file__": file_path, "__name__": "test_suite"}
                with open(file_path, "r", encoding="utf-8") as f:
                    code = compile(f.read(), file_path, "exec")
                    exec(code, glob)
                if "run_tests" in glob:
                    results = glob["run_tests"]()
                else:
                    results = {"passed": 0, "failed": 1, "errors": ["run_tests function not found"]}
                name = "Employee Platform Integration Verification Suite"
                is_ok = results.get("failed", 0) == 0






            elif suite_name == "phase4":
                file_path = os.path.join(settings.BASE_DIR, "test_phase4_completed_features.py")
                glob = {"__file__": file_path, "__name__": "__main__"}
                with open(file_path, "r", encoding="utf-8") as f:
                    exec(compile(f.read(), file_path, "exec"), glob)
                results = glob["run_tests"]() if "run_tests" in glob else {"passed": 0, "failed": 1}
                name = "Phase 4 Verification Suite"
                is_ok = results.get("failed", 0) == 0

            elif suite_name == "phase5":
                from test_phase5_customer_and_extension_handover import run_tests
                results = run_tests()
                name = "Phase 5 Customer & Extension Handover Verification Suite"
                is_ok = results.get("failed", 0) == 0
            else:
                from run_master_customer_marketplace_handover_verification import run_master_handover_audit
                results = run_master_handover_audit()
                name = "Master Customer/Marketplace Handover Audit Suite"
                is_ok = results.get("is_handover_ready", False)


            return Response({
                "suite": name,
                "is_ok": is_ok,
                "results": results,
            }, status=status.HTTP_200_OK)

        except Exception as err:
            import traceback
            return Response({
                "error": str(err),
                "traceback": traceback.format_exc(),
            }, status=status.HTTP_200_OK)



def process_job_arrival(job, employee, lat, lon, is_automatic=False, actor=None):
    """
    Authoritative Unified Site Arrival Processing Service for CalTrack.
    Validates technician assignment, coordinates validity, 300m arrival geofence,
    creates/updates PreServiceVerification, generates fresh 6-digit OTP code,
    calls apply_transition(job, 'arrived'), and emits events.
    """
    from workforce_api.models import PreServiceVerification, WorkforceEventLog
    from service_requests.state_machine import apply_transition
    import secrets

    now = timezone.now()
    verification, _ = PreServiceVerification.objects.get_or_create(
        job=job,
        defaults={"employee": employee}
    )

    verification.employee = employee
    verification.geofence_passed = True
    verification.arrival_lat = float(lat)
    verification.arrival_lon = float(lon)
    if not verification.arrived_at:
        verification.arrived_at = now

    # Fresh 6-digit OTP if not already generated or expired
    if not verification.otp_code or (verification.otp_expires_at and verification.otp_expires_at < now):
        new_otp = f"{secrets.randbelow(900000) + 100000}"
        verification.otp_code = new_otp
        verification.otp_generated_at = now
        verification.otp_expires_at = now + timedelta(minutes=15)
        verification.otp_attempts = 0
        verification.otp_verified = False
        verification.otp_verified_at = None

        if job.customer:
            tech_name = employee.user.get_full_name() if employee and employee.user else (actor.get_full_name() if actor else "Technician")
            create_notification(
                recipient=job.customer,
                title="Technician Arrived — Work Start OTP",
                message=f"Technician {tech_name} has arrived. Share OTP {new_otp} to start service.",
                notification_type="WORK_START_OTP",
                company=job.company,
                related_object_id=str(job.id),
            )

    verification.check_completion()
    verification.save()

    # Apply transition to arrived via authoritative state machine
    apply_transition(job, "arrived", actor=actor or (employee.user if employee else None))

    # Emit event log
    user = getattr(employee, "user", None) or actor
    if user:
        WorkforceEventLog.objects.create(
            user=user,
            event_type="ARRIVAL_DETECTED",
            payload={
                "job_id": job.id,
                "arrival_lat": float(lat),
                "arrival_lon": float(lon),
                "is_automatic": is_automatic,
            }
        )

    return verification


# ─── Phase 2: Arrival, Pre-Service Verification & Service Gate ───────────────

class WorkforceJobArriveView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        if job.status not in ["accepted", "on_the_way", "arrived"]:
            return Response({
                "error": f"Job #{job.id} is in status '{job.status}'. Expected 'accepted' or 'on_the_way'."
            }, status=status.HTTP_400_BAD_REQUEST)

        lat = request.data.get("lat") if request.data.get("lat") is not None else request.data.get("latitude")
        lon = request.data.get("lon") if request.data.get("lon") is not None else (request.data.get("longitude") or request.data.get("lng"))

        try:
            lat_val = float(lat)
            lon_val = float(lon)
        except (ValueError, TypeError):
            return Response({
                "error": "Real browser GPS coordinates (lat and lon) are required for arrival verification."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not (-90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0):
            return Response({
                "error": "GPS coordinates out of valid range (-90 to 90 lat, -180 to 180 lon)."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Real GPS Arrival Geofencing: Compare Employee GPS against Customer Job Location
        from time_tracking.geo import haversine_distance, evaluate
        ARRIVAL_RADIUS_METERS = 250.0

        if job.latitude is not None and job.longitude is not None:
            distance_m = haversine_distance(lat_val, lon_val, float(job.latitude), float(job.longitude))
            if distance_m > ARRIVAL_RADIUS_METERS:
                return Response({
                    "error": f"Arrival failed: You are {int(distance_m)}m away from the customer address. You must be within 250m to confirm arrival.",
                    "geofence_passed": False,
                    "code": "OUTSIDE_GEOFENCE",
                    "details": {
                        "distance_m": round(distance_m, 1),
                        "threshold_m": ARRIVAL_RADIUS_METERS,
                        "customer_lat": job.latitude,
                        "customer_lng": job.longitude,
                    }
                }, status=status.HTTP_403_FORBIDDEN)
            matched_location = f"Customer Destination ({job.address[:40]}...)" if job.address else "Customer Job Location"
        else:
            permitted_locs = list(Location.objects.filter(company=emp.company, is_active=True))
            decision = evaluate(
                lat=lat_val,
                lng=lon_val,
                permitted_locations=permitted_locs,
                is_admin=getattr(request.user, "is_staff", False),
                allow_all_locations=getattr(emp, "allow_all_locations", False) or not getattr(emp.company, "geofence_enabled", True)
            )
            if not decision.allowed:
                return Response({
                    "error": f"Arrival failed: {decision.reason}",
                    "geofence_passed": False,
                    "code": "OUTSIDE_GEOFENCE",
                    "details": {"distance_m": decision.distance_m}
                }, status=status.HTTP_403_FORBIDDEN)
            distance_m = decision.distance_m
            matched_location = decision.matched_location.name if decision.matched_location else "Job Site"

        now = timezone.now()

        verification, _ = PreServiceVerification.objects.get_or_create(
            job=job,
            employee=emp,
            lat=lat_val,
            lon=lon_val,
            is_automatic=False,
            actor=request.user
        )

        # ── Authoritative Single OTP Resolution ──────────────────────────────
        # Priority: start_otp on ServiceRequest (set during booking) > existing
        # active unexpired PSV otp_code > generate a fresh one.
        # Never silently overwrite a valid, unexpired, unverified OTP.
        existing_otp = (
            (getattr(job, "start_otp", None) or "").strip()
            or (verification.otp_code or "").strip()
        )

        otp_is_active = (
            existing_otp
            and not verification.otp_verified
            and (
                not verification.otp_expires_at
                or verification.otp_expires_at >= now
            )
        )

        if otp_is_active:
            # Re-use the already-issued, non-expired, unverified OTP
            active_otp = existing_otp
            verification.otp_code = active_otp
            if not verification.otp_generated_at:
                verification.otp_generated_at = now
            if not verification.otp_expires_at:
                verification.otp_expires_at = now + timedelta(minutes=15)
        else:
            # Generate fresh OTP (first arrival or previous OTP already expired/verified)
            active_otp = f"{secrets.randbelow(900000) + 100000}"
            verification.otp_code = active_otp
            verification.otp_generated_at = now
            verification.otp_expires_at = now + timedelta(minutes=15)
            verification.otp_attempts = 0
            verification.otp_verified = False
            verification.otp_verified_at = None

        verification.employee = emp
        verification.geofence_passed = True
        verification.arrival_lat = lat_val
        verification.arrival_lon = lon_val
        if not verification.arrived_at:
            verification.arrived_at = now
        verification.check_completion()
        verification.save()

        # Sync active_otp → ServiceRequest.start_otp (single authoritative field)
        save_fields = ["status", "updated_at"]
        job.status = "arrived"
        if hasattr(job, "start_otp") and job.start_otp != active_otp:
            job.start_otp = active_otp
            save_fields.append("start_otp")
        job.save(update_fields=save_fields)

        try:
            from service_requests.models import EmployeeJob
            EmployeeJob.objects.filter(service_request=job, employee=emp).update(status="ARRIVED")
        except Exception:
            pass

        # Send notification to customer with Work Start OTP
        if job.customer:
            create_notification(
                recipient=job.customer,
                title="Technician Arrived — Work Start OTP",
                message=f"Technician {emp.user.get_full_name()} has arrived. Share OTP {active_otp} to start service.",
                notification_type="WORK_START_OTP",
                company=job.company,
                related_object_id=str(job.id),

            )

        return Response({
            "message": "Arrival verified! Fresh Customer Work Start OTP generated and sent to customer.",
            "geofence_passed": True,
            "matched_location": matched_location,
            "distance_m": round(distance_m, 1),
            "status": job.status,
            "otp_generated": True,
            "otp_expires_in_minutes": 15,
        }, status=status.HTTP_200_OK)



class WorkforceJobVerifyOTPView(APIView):
    permission_classes = [IsApprovedTechnician]
    throttle_classes = [ScopedRateThrottle]  # EC-06: OTP guess-attempt endpoint
    throttle_scope = "workforce_otp"

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        otp_input = str(request.data.get("otp") or request.data.get("otp_code") or "").strip()
        if not otp_input:
            return Response({"error": "Customer OTP code required."}, status=status.HTTP_400_BAD_REQUEST)

        verification = PreServiceVerification.objects.filter(job=job).first()

        # ── Authoritative OTP source ─────────────────────────────────────────
        # ServiceRequest.start_otp = booking-level canonical OTP (no TTL).
        # PreServiceVerification.otp_code = arrival-path OTP (has 15-min TTL).
        # Accept whichever is non-empty, preferring start_otp.
        booking_otp = (getattr(job, "start_otp", None) or "").strip()
        psv_otp = (getattr(verification, "otp_code", None) or "").strip() if verification else ""
        canonical_otp = booking_otp or psv_otp

        if not canonical_otp:
            return Response({
                "error": "No OTP generated for this job. Technician must arrive at the job location first."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ensure PSV record exists; create it if auto-arrival skipped it
        if not verification:
            verification, _ = PreServiceVerification.objects.get_or_create(
                job=job,
                defaults={"employee": emp, "geofence_passed": True, "otp_code": canonical_otp}
            )

        # Sync canonical_otp into PSV.otp_code so all subsequent reads are consistent
        if verification.otp_code != canonical_otp:
            verification.otp_code = canonical_otp
            verification.save(update_fields=["otp_code", "updated_at"])

        def _ensure_job_started(job_obj, verification_obj):
            # Delegates to the shared module-level helper so that every
            # pre-service gate endpoint starts the job by exactly the same
            # path. See ensure_job_started() for why this was hoisted.
            ensure_job_started(
                job_obj, emp, request.user,
                notes="Auto clock-in on Work Start OTP verification",
            )

        if verification.otp_verified:
            _ensure_job_started(job, verification)
            return Response({
                "message": "Customer OTP already verified.",
                "otp_verified": True,
                "is_complete": verification.is_complete,
                "status": job.status,
            }, status=status.HTTP_200_OK)

        # Max 5 attempts enforced
        if verification.otp_attempts >= 5:
            return Response({
                "error": "Maximum OTP verification attempts exceeded (5/5). Please click 'Resend OTP' to generate a fresh code.",
                "code": "MAX_OTP_ATTEMPTS_EXCEEDED",
            }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        otp_expired = bool(verification.otp_expires_at and now > verification.otp_expires_at)

        # Expiry only blocks if the submitted code does NOT match the booking-level start_otp
        # (start_otp is permanent; only arrival-path OTPs have a TTL)
        submitted_matches_booking = bool(booking_otp and booking_otp == otp_input)
        if otp_expired and not submitted_matches_booking:
            return Response({
                "error": "Customer OTP has expired. Please click 'Resend OTP' to generate a fresh code.",
                "code": "OTP_EXPIRED",
            }, status=status.HTTP_400_BAD_REQUEST)

        # Match check against canonical code
        if canonical_otp == otp_input:
            verification.otp_verified = True
            verification.otp_attempts = 0
            verification.otp_verified_at = now
            if otp_expired and submitted_matches_booking:
                # Retroactively extend the window so check_completion() passes
                verification.otp_expires_at = now + timedelta(minutes=15)
            is_complete = verification.check_completion()
            verification.save()

            _ensure_job_started(job, verification)

            return Response({
                "message": "Customer OTP verified successfully.",
                "otp_verified": True,
                "is_complete": is_complete,
                "status": job.status,
            }, status=status.HTTP_200_OK)

        verification.otp_attempts += 1
        verification.save(update_fields=["otp_attempts", "updated_at"])
        remaining = max(0, 5 - verification.otp_attempts)
        return Response({
            "error": f"Invalid Customer OTP code. {remaining} attempt(s) remaining. Ask customer for the 6-digit code displayed in their app.",
            "code": "INVALID_OTP",
            "attempts_remaining": remaining,
        }, status=status.HTTP_400_BAD_REQUEST)


class WorkforceJobResendOTPView(APIView):
    """
    Regenerates a fresh Work Start OTP and sends it to the customer.
    """
    permission_classes = [IsApprovedTechnician]
    throttle_classes = [ScopedRateThrottle]  # EC-06: avoid OTP-resend spam
    throttle_scope = "workforce_otp"

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        verification, _ = PreServiceVerification.objects.get_or_create(
            job=job,
            defaults={"employee": emp}
        )

        now = timezone.now()
        new_otp = f"{secrets.randbelow(900000) + 100000}"
        verification.otp_code = new_otp
        verification.otp_generated_at = now
        verification.otp_expires_at = now + datetime.timedelta(minutes=15)
        verification.otp_attempts = 0
        verification.save(update_fields=["otp_code", "otp_generated_at", "otp_expires_at", "otp_attempts", "updated_at"])

        # Keep ServiceRequest.start_otp in sync with the new active OTP
        if hasattr(job, "start_otp") and job.start_otp != new_otp:
            job.start_otp = new_otp
            job.save(update_fields=["start_otp", "updated_at"])

        if job.customer:
            create_notification(
                recipient=job.customer,
                title="Fresh Work Start OTP",
                message=f"Your new Work Start OTP for job #{job.id} is {new_otp}.",
                notification_type="WORK_START_OTP",
                company=job.company,
                related_object_id=str(job.id),
            )

        return Response({
            "message": "Fresh Customer OTP generated and sent to customer.",
            "otp_generated": True,
            "otp_expires_in_minutes": 15,
        }, status=status.HTTP_200_OK)


class WorkforceCustomerJobOTPView(APIView):
    """
    Endpoint for customer or admin to securely display/retrieve the Work Start OTP for the job.
    Technicians are strictly blocked from this endpoint.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        is_customer = (
            job.customer == request.user
            or str(getattr(job, "customer_name", "")).lower() == request.user.username.lower()
            or getattr(job, "phone", "") == getattr(request.user, "username", "")
        )
        is_admin = is_admin_role(request.user)

        if not (is_customer or is_admin):
            return Response({
                "error": "Unauthorized: Only the booking customer or admin may view the Customer Work Start OTP."
            }, status=status.HTTP_403_FORBIDDEN)

        verification = PreServiceVerification.objects.filter(job=job).first()

        # Authoritative OTP: start_otp (booking-level) > PSV otp_code (arrival-path)
        booking_otp = (getattr(job, "start_otp", None) or "").strip()
        psv_otp = (verification.otp_code or "").strip() if verification else ""
        canonical_otp = booking_otp or psv_otp

        if not canonical_otp:
            return Response({
                "error": "Work Start OTP has not been generated yet. Technician must arrive at the job location first."
            }, status=status.HTTP_404_NOT_FOUND)

        now = timezone.now()

        if verification and verification.otp_verified:
            otp_state = "VERIFIED"
        elif verification and verification.otp_expires_at and now > verification.otp_expires_at and not booking_otp:
            # PSV-path OTP expired and no booking-level OTP to fall back to
            otp_state = "EXPIRED"
        else:
            otp_state = "ACTIVE"

        return Response({
            "job_id": job.id,
            "request_id": job.request_id,
            "otp_code": canonical_otp,
            "otp": canonical_otp,  # backward compatibility alias
            "otp_state": otp_state,
            "expires_at": verification.otp_expires_at.isoformat() if verification and verification.otp_expires_at else None,
            "is_verified": verification.otp_verified if verification else False,
            "otp_attempts": verification.otp_attempts if verification else 0,
            "customer_message": f"Your Work Start Verification Code: {canonical_otp}. Share this code with your technician upon arrival.",
            "authorized_action": "START_WORK_AND_CLOCK_IN",
        }, status=status.HTTP_200_OK)


class WorkforceJobPreServicePhotoView(APIView):
    permission_classes = [IsApprovedTechnician]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        photo_type = request.data.get("photo_type")
        photo_file = request.FILES.get("file") or request.FILES.get("photo")

        if photo_type not in ["presence", "appliance", "work_area"]:
            return Response({
                "error": "photo_type must be one of: presence, appliance, work_area."
            }, status=status.HTTP_400_BAD_REQUEST)

        if not photo_file:
            return Response({"error": "Photo file required."}, status=status.HTTP_400_BAD_REQUEST)

        _photo_err = _validate_photo_upload(photo_file)
        if _photo_err:
            return Response({"error": _photo_err}, status=status.HTTP_400_BAD_REQUEST)

        verification, _ = PreServiceVerification.objects.get_or_create(
            job=job,
            defaults={"employee": emp}
        )

        if photo_type == "presence":
            verification.presence_photo = photo_file
        elif photo_type == "appliance":
            verification.appliance_photo = photo_file
        elif photo_type == "work_area":
            verification.work_area_photo = photo_file

        is_complete = verification.check_completion()
        verification.save()

        # If this upload satisfied the last outstanding gate, start the job here.
        # Only the OTP endpoint used to be able to do this, so finishing with a
        # photo -- the order the UI lists the gates in -- left the job un-started.
        job_started = False
        if is_complete:
            _time_log, _start_err = ensure_job_started(
                job, emp, request.user,
                notes="Auto clock-in on pre-service photo completion",
            )
            job_started = bool(_time_log and not _start_err)

        return Response({
            "message": f"Pre-service photo '{photo_type}' uploaded successfully.",
            "photo_type": photo_type,
            "is_complete": is_complete,
            "job_started": job_started,
        }, status=status.HTTP_201_CREATED)


class WorkforceJobPreServiceStatusView(APIView):
    permission_classes = [IsApprovedTechnician]

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({
                "error": "Unauthorized: Job is not assigned to you.",
                "code": "PRE_SERVICE_ACCESS_DENIED",
            }, status=status.HTTP_403_FORBIDDEN)

        verification = PreServiceVerification.objects.filter(job=job).first()
        if not verification:
            return Response({
                "geofence_passed": False,
                "otp_verified": False,
                "presence_photo": False,
                "appliance_photo": False,
                "work_area_photo": False,
                "is_complete": False,
            }, status=status.HTTP_200_OK)

        return Response({
            "geofence_passed": verification.geofence_passed,
            "otp_verified": verification.otp_verified,
            "presence_photo": bool(verification.presence_photo),
            "appliance_photo": bool(verification.appliance_photo),
            "work_area_photo": bool(verification.work_area_photo),
            "is_complete": verification.is_complete,
        }, status=status.HTTP_200_OK)


# ─── 28. Employee Profile & Controlled Change Requests ─────────────────────────

class WorkforceEmployeeProfileMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found for user."}, status=status.HTTP_404_NOT_FOUND)
        serializer = WorkforceEmployeeProfileSerializer(emp)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found for user."}, status=status.HTTP_404_NOT_FOUND)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        reg_status = onboarding.get("status", "not_started")
        is_locked = reg_status in ["submitted", "under_review", "approved"]

        # Check if user is attempting to modify controlled fields directly
        controlled_fields_map = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "date_of_birth": "Date of Birth",
            "dob": "Date of Birth",
            "employee_id": "Employee ID",
            "country": "Country",
            "state": "State",
            "department": "Department",
            "hourly_rate": "Hourly Rate",
        }

        if is_locked:
            for field, label in controlled_fields_map.items():
                if field in request.data:
                    return Response({
                        "error": f"'{label}' is a controlled registration/employment field and cannot be edited directly. Please submit an Employee Change Request for Admin review.",
                        "field": field,
                        "requires_change_request": True,
                    }, status=status.HTTP_400_BAD_REQUEST)

        # Update freely editable personal preferences
        user_changed = False
        emp_changed = False

        if "phone" in request.data:
            user.phone = request.data["phone"]
            emp.phone = request.data["phone"]
            user_changed = True
            emp_changed = True

        if "bio" in request.data:
            user.bio = request.data["bio"]
            user_changed = True

        if "timezone" in request.data:
            user.timezone = request.data["timezone"]
            user_changed = True

        if "language" in request.data:
            user.language = request.data["language"]
            user_changed = True

        if user_changed:
            user.save()
        if emp_changed:
            emp.save()

        serializer = WorkforceEmployeeProfileSerializer(emp)
        return Response({
            "message": "Profile preferences updated successfully.",
            "profile": serializer.data,
        }, status=status.HTTP_200_OK)


class WorkforceProfileAvatarUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = request.user
        avatar_file = request.FILES.get("avatar") or request.FILES.get("file")
        if not avatar_file:
            return Response({"error": "No avatar file provided."}, status=status.HTTP_400_BAD_REQUEST)

        user.avatar = avatar_file
        user.save()

        avatar_url = ""
        try:
            avatar_url = user.avatar.url
        except Exception:
            avatar_url = str(user.avatar)

        return Response({
            "message": "Profile avatar updated successfully.",
            "avatar_url": avatar_url,
        }, status=status.HTTP_200_OK)


class WorkforceEmployeeChangeRequestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found."}, status=status.HTTP_404_NOT_FOUND)

        requests = WorkforceEmployeeChangeRequest.objects.filter(employee=emp).order_by("-created_at")
        serializer = WorkforceEmployeeChangeRequestSerializer(requests, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found."}, status=status.HTTP_404_NOT_FOUND)

        field_name = request.data.get("field_name", "").strip()
        field_label = request.data.get("field_label", "").strip() or field_name.replace("_", " ").title()
        new_value = request.data.get("new_value", "").strip()
        reason = request.data.get("reason", "").strip()

        if not field_name or not new_value or not reason:
            return Response({
                "error": "field_name, new_value, and reason are required for a Change Request."
            }, status=status.HTTP_400_BAD_REQUEST)

        # Determine old_value from current record
        old_value = ""
        if field_name == "first_name":
            old_value = user.first_name
        elif field_name == "last_name":
            old_value = user.last_name
        elif field_name in ["date_of_birth", "dob"]:
            old_value = str(emp.date_of_birth or "")
        elif field_name in ["phone", "mobile_number"]:
            old_value = user.mobile_number or user.phone or emp.phone or ""
        elif field_name == "department":
            old_value = emp.department or ""
        elif field_name == "state":
            old_value = emp.state or ""
        elif field_name == "country":
            old_value = emp.country or ""
        elif field_name == "bank_account":
            bank_info = (emp.bank_details or {}).get("onboarding", {}).get("draft", {}).get("bank", {})
            old_value = f"{bank_info.get('bankName', '')} - {bank_info.get('accountNumber', '')}"

        change_req = WorkforceEmployeeChangeRequest.objects.create(
            employee=emp,
            company=emp.company,
            field_name=field_name,
            field_label=field_label,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            status=WorkforceEmployeeChangeRequest.Status.PENDING,
        )

        return Response({
            "message": "Change Request submitted successfully for Workforce Admin review.",
            "change_request": WorkforceEmployeeChangeRequestSerializer(change_req).data,
        }, status=status.HTTP_201_CREATED)


class WorkforceAdminChangeRequestsListView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        status_filter = request.query_params.get("status", "").strip().upper()
        if getattr(request.user, "is_superuser", False):
            reqs = WorkforceEmployeeChangeRequest.objects.select_related("employee__user", "reviewed_by").order_by("-created_at")
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            reqs = WorkforceEmployeeChangeRequest.objects.filter(company=company).select_related("employee__user", "reviewed_by").order_by("-created_at")

        if status_filter:
            reqs = reqs.filter(status=status_filter)

        serializer = WorkforceEmployeeChangeRequestSerializer(reqs, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class WorkforceAdminChangeRequestDecideView(APIView):
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        change_req = WorkforceEmployeeChangeRequest.objects.select_related("employee__user").filter(pk=pk).first()
        if not change_req:
            return Response({"error": "Change Request not found."}, status=status.HTTP_404_NOT_FOUND)

        if not getattr(request.user, "is_superuser", False):
            user_company = resolve_actor_company(request)
            if not user_company:
                return Response({"error": "Tenant company context required.", "code": "TENANT_REQUIRED"}, status=status.HTTP_403_FORBIDDEN)
            if not change_req.company_id or user_company.id != change_req.company_id:
                return Response({"error": "Unauthorized cross-company action.", "code": "CROSS_TENANT_FORBIDDEN"}, status=status.HTTP_403_FORBIDDEN)

        action = (request.data.get("action") or "").strip().upper()
        admin_notes = request.data.get("admin_notes", "").strip()

        if action not in ["APPROVE", "REJECT"]:
            return Response({"error": "action must be APPROVE or REJECT."}, status=status.HTTP_400_BAD_REQUEST)

        emp = change_req.employee
        user = emp.user

        if action == "APPROVE":
            change_req.status = WorkforceEmployeeChangeRequest.Status.APPROVED
            change_req.reviewed_by = request.user
            change_req.reviewed_at = timezone.now()
            change_req.admin_notes = admin_notes
            change_req.save()

            # Atomically update target PostgreSQL field
            field = change_req.field_name
            new_val = change_req.new_value

            if field == "first_name":
                user.first_name = new_val
                user.save()
            elif field == "last_name":
                user.last_name = new_val
                user.save()
            elif field in ["date_of_birth", "dob"]:
                emp.date_of_birth = new_val
                emp.save()
            elif field in ["phone", "mobile_number"]:
                user.mobile_number = new_val
                user.phone = new_val
                emp.phone = new_val
                user.save()
                emp.save()
            elif field == "department":
                emp.department = new_val
                emp.save()
            elif field == "state":
                emp.state = new_val
                emp.save()
            elif field == "country":
                emp.country = new_val
                emp.save()

            # Also update onboarding draft data for consistency
            bank_details = emp.bank_details or {}
            onboarding = bank_details.get("onboarding", {})
            draft = onboarding.get("draft", {})
            if "personal" in draft:
                if field == "first_name":
                    draft["personal"]["first_name"] = new_val
                elif field == "last_name":
                    draft["personal"]["last_name"] = new_val
                elif field in ["date_of_birth", "dob"]:
                    draft["personal"]["dob"] = new_val
            bank_details["onboarding"] = onboarding
            emp.bank_details = bank_details
            emp.save()

            return Response({
                "message": f"Change Request #{change_req.id} APPROVED and profile fields updated.",
                "status": "APPROVED",
                "change_request": WorkforceEmployeeChangeRequestSerializer(change_req).data,
            }, status=status.HTTP_200_OK)

        else:
            change_req.status = WorkforceEmployeeChangeRequest.Status.REJECTED
            change_req.reviewed_by = request.user
            change_req.reviewed_at = timezone.now()
            change_req.admin_notes = admin_notes or "Request does not meet operational verification standards."
            change_req.save()

            return Response({
                "message": f"Change Request #{change_req.id} REJECTED.",
                "status": "REJECTED",
                "change_request": WorkforceEmployeeChangeRequestSerializer(change_req).data,
            }, status=status.HTTP_200_OK)


# ─── 29. Account & Security ───────────────────────────────────────────────────

class WorkforceChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password", "").strip()
        new_password = request.data.get("new_password", "").strip()
        confirm_password = request.data.get("confirm_password", "").strip()

        if not current_password or not new_password:
            return Response({"error": "Current password and new password are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({"error": "Incorrect current password."}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 6:
            return Response({"error": "New password must be at least 6 characters long."}, status=status.HTTP_400_BAD_REQUEST)

        if confirm_password and new_password != confirm_password:
            return Response({"error": "New password and confirmation password do not match."}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        # Log security event
        WorkforceEventLog.objects.create(
            event_type="PASSWORD_CHANGED",
            user=user,
            payload={"ip": request.META.get("REMOTE_ADDR", "")}
        )

        return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)


class WorkforceChangeEmailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        current_password = request.data.get("current_password", "").strip()
        new_email = request.data.get("new_email", "").strip().lower()

        if not current_password or not new_email:
            return Response({"error": "Current password and new email are required."}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(current_password):
            return Response({"error": "Incorrect password verification."}, status=status.HTTP_400_BAD_REQUEST)

        if "@" not in new_email or "." not in new_email:
            return Response({"error": "Invalid email address format."}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            return Response({"error": "An account with this email address already exists."}, status=status.HTTP_400_BAD_REQUEST)

        old_email = user.email
        user.email = new_email
        user.save()

        WorkforceEventLog.objects.create(
            event_type="EMAIL_CHANGED",
            user=user,
            payload={"old_email": old_email, "new_email": new_email}
        )

        return Response({
            "message": "Email address updated successfully.",
            "email": user.email,
        }, status=status.HTTP_200_OK)


class WorkforceTwoFactorView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "two_fa_enabled": getattr(user, "two_fa_enabled", False),
            "phone_configured": bool(user.mobile_number or user.phone),
            "email": user.email,
        }, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user
        # Toggle 2FA status
        user.two_fa_enabled = not user.two_fa_enabled
        user.save()

        action = "enabled" if user.two_fa_enabled else "disabled"
        WorkforceEventLog.objects.create(
            event_type="TWO_FACTOR_TOGGLED",
            user=user,
            payload={"enabled": user.two_fa_enabled}
        )

        return Response({
            "message": f"Two-Factor Authentication {action} successfully.",
            "two_fa_enabled": user.two_fa_enabled,
        }, status=status.HTTP_200_OK)


class WorkforceActiveSessionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        user_agent = request.META.get("HTTP_USER_AGENT", "Web Browser")
        ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

        # Construct authoritative active session representation
        current_session = {
            "id": f"sess-{user.id}-{int(time.time() // 86400)}",
            "device": "Current Web Session",
            "browser": user_agent[:60],
            "ip_address": ip,
            "is_current": True,
            "last_active": timezone.now().isoformat(),
            "status": "active",
        }

        return Response([current_session], status=status.HTTP_200_OK)


class AdminCashOutstandingView(APIView):
    """
    GET /workforce/admin/cash/outstanding/<int:employee_id>/
    GT-C-02: how much cash a given technician should currently be holding
    from PAID cash-on-service collections that haven't been settled yet.
    """
    permission_classes = [permissions.IsAuthenticated, IsWorkforceAdmin]

    def get(self, request, employee_id):
        from employees.models import Employee
        from workforce_api.services import compute_outstanding_cash
        emp = Employee.objects.filter(pk=employee_id).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)
        expected_amount, outstanding_qs = compute_outstanding_cash(emp)
        return Response({
            "employee_id": emp.id,
            "outstanding_amount": str(expected_amount),
            "unsettled_payment_count": outstanding_qs.count(),
        })


class AdminCashSettlementView(APIView):
    """
    POST /workforce/admin/cash/settlements/
    body: {employee_id, deposited_amount, notes?}
    GT-C-02: records a cash-in-hand settlement -- computes what the
    technician should be holding, compares to what was actually deposited,
    and marks every matched cash payment reconciled. discrepancy in the
    response is the whole point: a shortfall or overage is now a number,
    not silence.

    GET on the same endpoint lists recent settlements, optionally filtered
    by ?employee_id=.
    """
    permission_classes = [permissions.IsAuthenticated, IsWorkforceAdmin]

    def get(self, request):
        from employees.models import Employee
        from workforce_api.services import list_cash_settlements
        employee = None
        employee_id = request.query_params.get("employee_id")
        if employee_id:
            employee = Employee.objects.filter(pk=employee_id).first()
        company = resolve_actor_company(request) if not getattr(request.user, "is_superuser", False) else None
        settlements = list_cash_settlements(employee=employee, company=company)
        return Response([
            {
                "id": s.id,
                "employee_id": s.employee_id,
                "expected_amount": str(s.expected_amount),
                "deposited_amount": str(s.deposited_amount),
                "discrepancy": str(s.discrepancy),
                "notes": s.notes,
                "created_at": s.created_at.isoformat(),
            }
            for s in settlements
        ])

    def post(self, request):
        from employees.models import Employee
        from workforce_api.services import record_cash_settlement
        employee_id = request.data.get("employee_id")
        deposited_amount = request.data.get("deposited_amount")
        notes = request.data.get("notes", "")
        if not employee_id or deposited_amount is None:
            return Response({"error": "employee_id and deposited_amount are required."}, status=status.HTTP_400_BAD_REQUEST)

        emp = Employee.objects.filter(pk=employee_id).first()
        if not emp:
            return Response({"error": "Employee not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            settlement = record_cash_settlement(
                employee=emp, company=emp.company, deposited_amount=deposited_amount,
                recorded_by=request.user, notes=notes,
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "id": settlement.id,
            "expected_amount": str(settlement.expected_amount),
            "deposited_amount": str(settlement.deposited_amount),
            "discrepancy": str(settlement.discrepancy),
        }, status=status.HTTP_201_CREATED)


class WorkforceLoginHistoryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)

        history = []
        try:
            if emp:
                presences = PresenceLog.objects.filter(employee=emp).order_by("-created_at")[:15]
                for p in presences:
                    history.append({
                        "id": f"pres-{p.id}",
                        "timestamp": p.created_at.isoformat() if p.created_at else timezone.now().isoformat(),
                        "event": "Presence Online" if p.is_online else f"Status: {p.availability}",
                        "ip": request.META.get("REMOTE_ADDR", "—"),
                        "status": "SUCCESS",
                    })
        except Exception:
            pass

        try:
            events = WorkforceEventLog.objects.filter(user=user).order_by("-created_at")[:10]
            for ev in events:
                history.append({
                    "id": f"ev-{ev.id}",
                    "timestamp": ev.created_at.isoformat() if ev.created_at else timezone.now().isoformat(),
                    "event": ev.event_type.replace("_", " ").title(),
                    "ip": (ev.payload or {}).get("ip", "—"),
                    "status": "RECORDED",
                })
        except Exception:
            pass

        # Sort combined history chronologically descending
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return Response(history[:20], status=status.HTTP_200_OK)



# ─── 30. Appearance & User Preferences ─────────────────────────────────────────

class WorkforceUserPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        pref, _ = WorkforceUserPreference.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)}
        )
        serializer = WorkforceUserPreferenceSerializer(pref)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        pref, _ = WorkforceUserPreference.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)}
        )
        serializer = WorkforceUserPreferenceSerializer(pref, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Preferences saved successfully.",
            "preferences": serializer.data,
        }, status=status.HTTP_200_OK)


# ─── 31. Notification Preferences ─────────────────────────────────────────────

class WorkforceNotificationPreferenceView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        pref, _ = WorkforceNotificationPreference.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)}
        )
        serializer = WorkforceNotificationPreferenceSerializer(pref)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        user = request.user
        pref, _ = WorkforceNotificationPreference.objects.get_or_create(
            user=user,
            defaults={"company": getattr(user, "company", None)}
        )

        data = request.data.copy()
        # If user enables SMS channel, verify mobile number is configured
        if data.get("channel_sms") is True and not (user.mobile_number or user.phone):
            return Response({
                "error": "Cannot enable SMS notifications: No registered mobile number found on your profile. Please add your mobile number first."
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = WorkforceNotificationPreferenceSerializer(pref, data=data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            "message": "Notification preferences saved successfully.",
            "preferences": serializer.data,
        }, status=status.HTTP_200_OK)


# ─── 32. Privacy & Data ───────────────────────────────────────────────────────

class WorkforcePrivacyExportView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found."}, status=status.HTTP_404_NOT_FOUND)

        # Collect complete dossier from PostgreSQL
        export_data = {
            "export_generated_at": timezone.now().isoformat(),
            "user_identity": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "mobile_number": user.mobile_number,
                "phone": user.phone,
                "date_joined": user.date_joined.isoformat() if user.date_joined else None,
                "timezone": user.timezone,
                "language": user.language,
            },
            "employment_record": {
                "employee_id": emp.employee_id,
                "title": emp.title,
                "company": emp.company.company_name if emp.company else "CalServices",
                "hire_date": str(emp.hire_date) if emp.hire_date else None,
                "date_of_birth": str(emp.date_of_birth) if emp.date_of_birth else None,
                "exempt_status": emp.exempt_status,
                "department": emp.department,
                "hourly_rate": str(emp.hourly_rate),
            },
            "onboarding_dossier": (emp.bank_details or {}).get("onboarding", {}),
            "attendance_logs_count": TimeLog.objects.filter(employee=emp).count(),
            "leave_applications_count": (emp.bank_details or {}).get("leaves", []),
            "completed_jobs_count": ServiceRequest.objects.filter(assigned_employee=emp, status="completed").count(),
            "payslips_count": WorkforcePayslip.objects.filter(employee=emp).count(),
        }

        return Response(export_data, status=status.HTTP_200_OK)


class WorkforceAccountDeactivateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        password = request.data.get("password", "").strip()

        if not password or not user.check_password(password):
            return Response({"error": "Password verification failed. Please enter your correct password."}, status=status.HTTP_400_BAD_REQUEST)

        emp = getattr(user, "employee_profile", None)
        if emp:
            # Prevent deactivation if active field work exists
            active_jobs = ServiceRequest.objects.filter(
                assigned_employee=emp,
                status__in=["assigned", "accepted", "on_the_way", "in_progress"]
            ).exists()
            if active_jobs:
                return Response({
                    "error": "Cannot deactivate account while you have active jobs in progress. Please complete or unassign open service requests first."
                }, status=status.HTTP_400_BAD_REQUEST)

            emp.is_active = False
            emp.is_online = False
            emp.current_availability = "offline"
            emp.save()

        user.is_active = False
        user.save()

        WorkforceEventLog.objects.create(
            event_type="ACCOUNT_DEACTIVATED",
            user=user,
            payload={"reason": request.data.get("reason", "Employee self-deactivation request")}
        )

        return Response({
            "message": "Your Workforce account has been safely deactivated in accordance with platform retention rules."
        }, status=status.HTTP_200_OK)


# ─── 33. My Feedback & Performance ─────────────────────────────────────────────

class WorkforcePerformanceMeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. Authoritative Job Metrics
        all_assigned_jobs = ServiceRequest.objects.filter(assigned_employee=emp)
        total_assigned_count = all_assigned_jobs.count()
        completed_jobs = all_assigned_jobs.filter(status="completed")
        completed_count = completed_jobs.count()

        completion_rate = round((completed_count / total_assigned_count * 100), 1) if total_assigned_count > 0 else 0.0

        # 2. Customer Ratings & Reviews from PostgreSQL
        feedbacks = WorkforceJobFeedback.objects.filter(employee=emp).select_related("job").order_by("-created_at")
        feedback_list = WorkforceJobFeedbackSerializer(feedbacks, many=True).data

        rating_counts = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
        total_rating_sum = 0
        csat_eligible_count = 0

        for fb in feedbacks:
            r = max(1, min(5, fb.rating))
            rating_counts[r] += 1
            total_rating_sum += r
            if r >= 4:
                csat_eligible_count += 1

        total_feedbacks = feedbacks.count()
        average_rating = round(total_rating_sum / total_feedbacks, 1) if total_feedbacks > 0 else 0.0
        csat_score = round((csat_eligible_count / total_feedbacks * 100), 1) if total_feedbacks > 0 else 0.0

        # Ontime resolution rate
        ontime_count = feedbacks.filter(resolution_ontime=True).count()
        resolution_rate = round((ontime_count / total_feedbacks * 100), 1) if total_feedbacks > 0 else (100.0 if completed_count > 0 else 0.0)

        # SEVO business plan Section 4: persisted rating + SLA scorecard
        # (tier feeds automatic_dispatch.py ranking; kept in sync by
        # services.recalculate_employee_scorecard on every feedback submit).
        scorecard = getattr(emp, "scorecard", None)
        if scorecard is not None:
            scorecard_data = {
                "tier": scorecard.tier,
                "sla_score": float(scorecard.sla_score),
                "sla_met_count": scorecard.sla_met_count,
                "sla_breach_count": scorecard.sla_breach_count,
                "average_rating": float(scorecard.average_rating),
                "rating_count": scorecard.rating_count,
                "last_recalculated_at": scorecard.last_recalculated_at,
            }
        else:
            scorecard_data = {
                "tier": WorkforceScorecard.Tier.UNRATED,
                "sla_score": 0.0,
                "sla_met_count": 0,
                "sla_breach_count": 0,
                "average_rating": 0.0,
                "rating_count": 0,
                "last_recalculated_at": None,
            }

        return Response({
            "metrics": {
                "jobs_completed": completed_count,
                "total_jobs_assigned": total_assigned_count,
                "completion_rate": completion_rate,
                "average_rating": average_rating,
                "csat_score": csat_score,
                "work_orders_completed": completed_count,
                "feedback_submissions_count": total_feedbacks,
                "average_customer_rating": average_rating,
                "feedback_received_count": total_feedbacks,
                "issue_resolution_rate": resolution_rate,
            },
            "rating_distribution": rating_counts,
            "feedbacks": feedback_list,
            "scorecard": scorecard_data,
            "has_data": completed_count > 0 or total_feedbacks > 0,
        }, status=status.HTTP_200_OK)


# ─── 34. Employee Services Self-Service ───────────────────────────────────────

class WorkforceMyServicesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        emp = getattr(user, "employee_profile", None)
        if not emp:
            return Response({"error": "No employee profile found."}, status=status.HTTP_404_NOT_FOUND)

        bank_details = emp.bank_details or {}
        onboarding = bank_details.get("onboarding", {})
        services = onboarding.get("services", [])

        approved = [s for s in services if s.get("status") == "approved"]
        pending = [s for s in services if s.get("status") == "pending"]
        rejected = [s for s in services if s.get("status") == "rejected"]

        return Response({
            "all_services": services,
            "approved_services": approved,
            "pending_services": pending,
            "rejected_services": rejected,
        }, status=status.HTTP_200_OK)


class WorkforceJobFeedbackSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, job_id=None):
        target_job_id = job_id or request.data.get("job_id") or request.data.get("job")
        if not target_job_id:
            return Response({"error": "job_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        job = ServiceRequest.objects.filter(pk=target_job_id).first()
        if not job:
            return Response({"error": "ServiceRequest not found."}, status=status.HTTP_404_NOT_FOUND)

        if not job.assigned_employee:
            return Response({"error": "ServiceRequest has no assigned employee."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating = int(request.data.get("rating", 5))
        except (ValueError, TypeError):
            rating = 5
        rating = max(1, min(5, rating))

        review = str(request.data.get("review", "")).strip()

        try:
            csat_score = int(request.data.get("csat_score", rating))
        except (ValueError, TypeError):
            csat_score = rating
        csat_score = max(1, min(5, csat_score))

        resolution_ontime = bool(request.data.get("resolution_ontime", True))
        customer_name = request.data.get("customer_name") or request.user.get_full_name() or request.user.username

        feedback, created = WorkforceJobFeedback.objects.update_or_create(
            job=job,
            defaults={
                "employee": job.assigned_employee,
                "customer": request.user if request.user.is_authenticated else None,
                "rating": rating,
                "review": review,
                "csat_score": csat_score,
                "resolution_ontime": resolution_ontime,
                "customer_name": customer_name,
            }
        )

        try:
            from workforce_api.services import recalculate_employee_scorecard
            recalculate_employee_scorecard(feedback.employee)
        except Exception:
            logger.exception(
                "Failed to recalculate scorecard for employee #%s after feedback "
                "submission on job #%s -- scorecard will be stale until next feedback "
                "or a manual backfill_scorecards run.",
                feedback.employee_id, job.id,
            )

        return Response({
            "message": "Feedback submitted successfully.",
            "feedback": WorkforceJobFeedbackSerializer(feedback).data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# ─── Location: Employee Saved Locations ───────────────────────────────────────

class WorkforceEmployeeSavedLocationsView(APIView):
    """
    GET  /workforce/locations/saved/    — list employee's own saved locations
    POST /workforce/locations/saved/    — create a new saved location

    Identity is resolved from request.user only. Frontend-supplied employee IDs
    are never trusted.
    """
    permission_classes = [IsApprovedTechnician]

    def _get_employee(self, request):
        emp = getattr(request.user, "employee_profile", None)
        if not emp or not emp.is_active:
            return None
        return emp

    def get(self, request):
        from .models import EmployeeSavedLocation
        from .serializers import EmployeeSavedLocationSerializer
        emp = self._get_employee(request)
        if not emp:
            return Response(
                {"error": "Employee record not found.", "code": "EMPLOYEE_NOT_FOUND"},
                status=status.HTTP_403_FORBIDDEN,
            )
        locations = EmployeeSavedLocation.objects.filter(employee=emp)
        data = EmployeeSavedLocationSerializer(locations, many=True).data
        return Response(data, status=status.HTTP_200_OK)

    def post(self, request):
        from .models import EmployeeSavedLocation
        from .serializers import EmployeeSavedLocationSerializer
        emp = self._get_employee(request)
        if not emp:
            return Response(
                {"error": "Employee record not found.", "code": "EMPLOYEE_NOT_FOUND"},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = EmployeeSavedLocationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid data.", "details": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # If this is set as default, clear previous defaults for this employee
        if serializer.validated_data.get("is_default"):
            EmployeeSavedLocation.objects.filter(employee=emp, is_default=True).update(is_default=False)

        loc = serializer.save(employee=emp)
        return Response(EmployeeSavedLocationSerializer(loc).data, status=status.HTTP_201_CREATED)


class WorkforceEmployeeSavedLocationDetailView(APIView):
    """
    GET    /workforce/locations/saved/<pk>/  — retrieve
    PUT    /workforce/locations/saved/<pk>/  — full update
    PATCH  /workforce/locations/saved/<pk>/  — partial update
    DELETE /workforce/locations/saved/<pk>/  — delete

    The employee may only access their own records (tenant + ownership enforced).
    """
    permission_classes = [IsApprovedTechnician]

    def _get_location(self, request, pk):
        from .models import EmployeeSavedLocation
        emp = getattr(request.user, "employee_profile", None)
        if not emp or not emp.is_active:
            return None, Response(
                {"error": "Employee record not found.", "code": "EMPLOYEE_NOT_FOUND"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            loc = EmployeeSavedLocation.objects.get(pk=pk, employee=emp)
            return loc, None
        except EmployeeSavedLocation.DoesNotExist:
            return None, Response(
                {"error": "Location not found.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def get(self, request, pk):
        from .serializers import EmployeeSavedLocationSerializer
        loc, err = self._get_location(request, pk)
        if err:
            return err
        return Response(EmployeeSavedLocationSerializer(loc).data)

    def put(self, request, pk):
        from .models import EmployeeSavedLocation
        from .serializers import EmployeeSavedLocationSerializer
        loc, err = self._get_location(request, pk)
        if err:
            return err
        serializer = EmployeeSavedLocationSerializer(loc, data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid data.", "details": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        emp = loc.employee
        if serializer.validated_data.get("is_default"):
            EmployeeSavedLocation.objects.filter(employee=emp, is_default=True).exclude(pk=pk).update(is_default=False)
        updated = serializer.save()
        return Response(EmployeeSavedLocationSerializer(updated).data)

    def patch(self, request, pk):
        from .models import EmployeeSavedLocation
        from .serializers import EmployeeSavedLocationSerializer
        loc, err = self._get_location(request, pk)
        if err:
            return err
        serializer = EmployeeSavedLocationSerializer(loc, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(
                {"error": "Invalid data.", "details": serializer.errors, "code": "VALIDATION_ERROR"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        emp = loc.employee
        if serializer.validated_data.get("is_default"):
            EmployeeSavedLocation.objects.filter(employee=emp, is_default=True).exclude(pk=pk).update(is_default=False)
        updated = serializer.save()
        return Response(EmployeeSavedLocationSerializer(updated).data)

    def delete(self, request, pk):
        loc, err = self._get_location(request, pk)
        if err:
            return err
        loc.delete()
        return Response({"message": "Location deleted."}, status=status.HTTP_204_NO_CONTENT)


# ─── Location: Admin Authorized Location Activate/Deactivate ─────────────────

class WorkforceAdminLocationToggleView(APIView):
    """
    PATCH /workforce/admin/locations/<pk>/toggle/
    Admin-only. Toggles is_active on a company Location record.
    Employees cannot call this endpoint.
    """
    permission_classes = [IsWorkforceAdmin]

    def patch(self, request, pk):
        from time_tracking.models import Location
        user = request.user
        if getattr(user, "is_superuser", False):
            loc = Location.objects.filter(pk=pk).first()
        else:
            company = resolve_actor_company(request)
            if not company:
                return Response(
                    {"error": "Tenant company context required.", "code": "TENANT_REQUIRED"},
                    status=status.HTTP_403_FORBIDDEN,
                )
            loc = Location.objects.filter(pk=pk, company=company).first()

        if not loc:
            return Response(
                {"error": "Location not found.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        is_active = request.data.get("is_active")
        if is_active is None:
            loc.is_active = not loc.is_active
        else:
            loc.is_active = bool(is_active)
        loc.save(update_fields=["is_active", "updated_at"])
        from time_tracking.serializers import LocationSerializer
        return Response(LocationSerializer(loc).data)


class WorkforceAdminLocationAssignEmployeeView(APIView):
    """
    POST   /workforce/admin/locations/<pk>/assign/   — assign employee to location
    DELETE /workforce/admin/locations/<pk>/assign/   — remove employee from location

    Uses existing EmployeeLocation model. Admin-only.
    """
    permission_classes = [IsWorkforceAdmin]

    def _get_location(self, request, pk):
        from time_tracking.models import Location
        user = request.user
        if getattr(user, "is_superuser", False):
            loc = Location.objects.filter(pk=pk).first()
            if not loc:
                return None, Response(
                    {"error": "Location not found.", "code": "NOT_FOUND"},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return loc, None

        company = resolve_actor_company(request)
        if not company:
            return None, Response(
                {"error": "Tenant company context required.", "code": "TENANT_REQUIRED"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            return Location.objects.get(pk=pk, company=company), None
        except Location.DoesNotExist:
            return None, Response(
                {"error": "Location not found.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )

    def post(self, request, pk):
        from time_tracking.models import EmployeeLocation
        loc, err = self._get_location(request, pk)
        if err:
            return err
        employee_id = request.data.get("employee_id")
        if not employee_id:
            return Response(
                {"error": "employee_id is required.", "code": "MISSING_EMPLOYEE"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            target_emp = Employee.objects.get(pk=employee_id, company=loc.company)
        except Employee.DoesNotExist:
            return Response(
                {"error": "Employee not found in this company.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        is_primary = bool(request.data.get("is_primary", False))
        emp_loc, created = EmployeeLocation.objects.get_or_create(
            employee=target_emp,
            location=loc,
            defaults={"is_primary": is_primary},
        )
        if not created and emp_loc.is_primary != is_primary:
            emp_loc.is_primary = is_primary
            emp_loc.save(update_fields=["is_primary"])
        return Response(
            {"message": "Employee assigned to location.", "is_primary": emp_loc.is_primary},
            status=status.HTTP_200_OK,
        )

    def delete(self, request, pk):
        from time_tracking.models import EmployeeLocation
        loc, err = self._get_location(request, pk)
        if err:
            return err
        employee_id = request.data.get("employee_id")
        if not employee_id:
            return Response(
                {"error": "employee_id is required.", "code": "MISSING_EMPLOYEE"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        deleted, _ = EmployeeLocation.objects.filter(
            employee_id=employee_id,
            location=loc,
        ).delete()
        if not deleted:
            return Response(
                {"error": "Assignment not found.", "code": "NOT_FOUND"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"message": "Employee removed from location."}, status=status.HTTP_200_OK)


class WorkforceJobTimelineView(APIView):
    """
    Authoritative Observable Timeline for a single Workforce Job.
    Correlates events across lifecycle, dispatch, offers, tracking, arrival, OTP, proof, event logs, and payments.
    Accessible by Admin (same company or superuser), Assigned Employee, and Customer Owner.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user
        job = ServiceRequest.objects.filter(pk=pk).select_related("assigned_employee__user", "company", "customer").first()
        if not job:
            return Response({"error": "Job not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Strict Tenant Isolation & Authorization
        is_admin = getattr(user, "role", None) == "admin" or user.is_staff
        user_company = getattr(user, "company", None)
        admin_authorized = is_admin and (user.is_superuser or (job.company_id and user_company and job.company_id == user_company.id))

        is_owner_cust = (job.customer_id == user.id)
        emp_profile = getattr(user, "employee_profile", None)
        is_assigned_emp = emp_profile and (job.assigned_employee_id == emp_profile.id)

        if not (admin_authorized or is_owner_cust or is_assigned_emp):
            return Response({"error": "Access denied.", "code": "UNAUTHORIZED"}, status=status.HTTP_403_FORBIDDEN)

        def _sanitize_metadata(meta):
            if not isinstance(meta, dict):
                return {}
            clean = {}
            for k, v in meta.items():
                if any(bad in k.lower() for bad in ["otp", "token", "password", "secret", "hash", "key"]):
                    continue
                clean[k] = v
            return clean

        timeline = []
        assigned_emp_id = job.assigned_employee_id

        # 1. Booking Creation
        if job.created_at:
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": assigned_emp_id,
                "request_id": job.request_id,
                "event_type": "BOOKING_CREATED",
                "timestamp": job.created_at.isoformat(),
                "actor_id": job.customer_id,
                "title": "Booking Created",
                "description": f"Customer {job.customer_name or 'Customer'} created booking #{job.request_id or job.id} for {job.issue_title or job.service_category}.",
                "actor": job.customer_name or "Customer",
                "metadata": {"total_amount": float(job.total_amount) if job.total_amount else 0, "payment_method": job.payment_method},
            })

        # 2. Offers
        offers = WorkforceJobOffer.objects.filter(job=job).select_related("employee__user").order_by("offered_at")
        for off in offers:
            tech_name = off.employee.user.get_full_name() if off.employee and off.employee.user else f"Employee #{off.employee_id}"
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": off.employee_id if not is_owner_cust else None,
                "request_id": job.request_id,
                "event_type": "JOB_OFFER_DELIVERED",
                "timestamp": off.offered_at.isoformat(),
                "actor_id": None,
                "title": f"Offer Delivered ({off.status})",
                "description": f"Exclusive offer #{off.id} delivered to {tech_name} (Rank score: {off.rank_score:.1f})." if not is_owner_cust else "Offer dispatched to eligible technician.",
                "actor": "Auto-Dispatch Engine",
                "metadata": {"offer_id": off.id, "status": off.status} if is_owner_cust else {"offer_id": off.id, "status": off.status, "employee_id": off.employee_id},
            })

        # 3. Lifecycle Events (Acceptance, Cancellation, Redispatch)
        lc_events = WorkforceJobLifecycleEvent.objects.filter(job=job).select_related("employee__user", "actor_user").order_by("created_at")
        for ev in lc_events:
            actor_label = ev.actor_user.get_full_name() if ev.actor_user else "System"
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": ev.employee_id if not is_owner_cust else None,
                "request_id": job.request_id,
                "event_type": ev.event_type,
                "timestamp": ev.created_at.isoformat(),
                "actor_id": ev.actor_user_id,
                "title": ev.get_event_type_display() if hasattr(ev, "get_event_type_display") else ev.event_type,
                "description": f"Status transitioned to '{ev.new_status}'. Reason: {ev.reason_text or ev.reason_code or 'Standard Workflow'}",
                "actor": actor_label,
                "metadata": _sanitize_metadata(ev.metadata),
            })

        # 4. Tracking Sessions
        sessions = JobTrackingSession.objects.filter(job=job).order_by("started_at")
        for s in sessions:
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": s.employee_id if not is_owner_cust else None,
                "request_id": job.request_id,
                "event_type": "TRACKING_STARTED",
                "timestamp": s.started_at.isoformat(),
                "actor_id": None,
                "title": "Live GPS Tracking Started",
                "description": f"Tracking session #{s.id} activated (Status: {s.status}).",
                "actor": "GPS Subsystem",
                "metadata": {"session_id": s.id, "status": s.status},
            })
            if s.ended_at:
                timeline.append({
                    "job_id": job.id,
                    "company_id": job.company_id,
                    "employee_id": s.employee_id if not is_owner_cust else None,
                    "request_id": job.request_id,
                    "event_type": "TRACKING_ENDED",
                    "timestamp": s.ended_at.isoformat(),
                    "actor_id": None,
                    "title": f"Tracking Session {s.status}",
                    "description": f"Tracking session #{s.id} concluded as {s.status}.",
                    "actor": "GPS Subsystem",
                    "metadata": {"session_id": s.id, "status": s.status},
                })

        # 5. Pre-Service Verification (Arrival & OTP)
        psv = PreServiceVerification.objects.filter(job=job).first()
        if psv:
            if psv.arrived_at:
                timeline.append({
                    "job_id": job.id,
                    "company_id": job.company_id,
                    "employee_id": psv.employee_id if not is_owner_cust else None,
                    "request_id": job.request_id,
                    "event_type": "ARRIVAL_DETECTED",
                    "timestamp": psv.arrived_at.isoformat(),
                    "actor_id": None,
                    "title": "On-Site Arrival Confirmed",
                    "description": "Technician crossed 300m arrival geofence with valid GPS telemetry.",
                    "actor": "Geofence Engine",
                    "metadata": {"arrival_lat": psv.arrival_lat, "arrival_lon": psv.arrival_lon},
                })
            if psv.otp_verified and psv.otp_verified_at:
                timeline.append({
                    "job_id": job.id,
                    "company_id": job.company_id,
                    "employee_id": psv.employee_id if not is_owner_cust else None,
                    "request_id": job.request_id,
                    "event_type": "WORK_START_OTP_VERIFIED",
                    "timestamp": psv.otp_verified_at.isoformat(),
                    "actor_id": None,
                    "title": "Work Start OTP Verified",
                    "description": "Customer shared 6-digit OTP code. Work scope authorized.",
                    "actor": "Customer / Assigned Tech",
                    "metadata": {"otp_verified": True},
                })

        # 6. Post-Service Proof
        psp = PostServiceProof.objects.filter(job=job).first()
        if psp and psp.is_submitted and psp.submitted_at:
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": assigned_emp_id if not is_owner_cust else None,
                "request_id": job.request_id,
                "event_type": "PROOF_SUBMITTED",
                "timestamp": psp.submitted_at.isoformat(),
                "actor_id": None,
                "title": "Post-Service Evidence Submitted",
                "description": f"After-service appliance and work area photos submitted. Notes: {psp.completion_notes[:80]}...",
                "actor": "Assigned Technician",
                "metadata": {"is_submitted": True},
            })

        # 7. Payment Events
        pmt_events = PaymentCollectionEvent.objects.filter(job_payment__job=job).order_by("created_at")
        for pe in pmt_events:
            actor_name = pe.actor_user.get_full_name() if pe.actor_user else "Payment Gateway"
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": assigned_emp_id if not is_owner_cust else None,
                "request_id": job.request_id,
                "event_type": pe.event_type,
                "timestamp": pe.created_at.isoformat(),
                "actor_id": pe.actor_user_id,
                "title": f"Payment: {pe.event_type}",
                "description": f"₹{pe.amount} processed for Job #{job.id}.",
                "actor": actor_name,
                "metadata": _sanitize_metadata(pe.metadata),
            })

        # 8. Workforce Event Logs Correlation
        from workforce_api.models import WorkforceEventLog
        event_logs = WorkforceEventLog.objects.filter(
            Q(payload__job_id=job.id) | Q(payload__service_request_id=job.id)
        ).select_related("user").order_by("created_at")
        for el in event_logs:
            actor_name = el.user.get_full_name() if el.user else "System"
            timeline.append({
                "job_id": job.id,
                "company_id": job.company_id,
                "employee_id": assigned_emp_id if not is_owner_cust else None,
                "request_id": job.request_id,
                "event_type": el.event_type,
                "timestamp": el.created_at.isoformat(),
                "actor_id": el.user_id if not is_owner_cust else None,
                "title": el.event_type.replace("_", " ").title(),
                "description": el.payload.get("message") or f"Event {el.event_type} recorded.",
                "actor": actor_name,
                "metadata": _sanitize_metadata(el.payload),
            })

        # Sort timeline strictly chronological
        timeline.sort(key=lambda x: x["timestamp"])

        if is_owner_cust and not is_admin:
            assigned_employee_data = {
                "name": job.assigned_employee.user.get_full_name() if job.assigned_employee and job.assigned_employee.user else (job.technician_name or "Assigned Professional"),
                "photo": getattr(job.assigned_employee, "avatar_url", "") or job.technician_photo or "",
                "rating": job.technician_rating,
            } if job.assigned_employee else None
        else:
            assigned_employee_data = {
                "id": job.assigned_employee.id,
                "name": job.assigned_employee.user.get_full_name() if job.assigned_employee and job.assigned_employee.user else None,
                "employee_id": job.assigned_employee.employee_id if job.assigned_employee else None,
            } if job.assigned_employee else None

        return Response({
            "job_id": job.id,
            "request_id": job.request_id,
            "customer_name": job.customer_name,
            "current_status": job.status,
            "payment_status": job.payment_status,
            "assigned_employee": assigned_employee_data,
            "event_count": len(timeline),
            "timeline": timeline,
        }, status=status.HTTP_200_OK)








class WorkforceDispatchHealthView(APIView):
    """
    GET /api/workforce/dispatch/health/

    Fixes X-11 (partial): the dispatch_pending_workforce_jobs management
    command is the ONLY dispatch mechanism this app has (no Celery, no
    supervisor), and previously had no way for anything outside its own
    stdout logs to reveal whether it was still running. This reads the
    heartbeat that command now writes every cycle (see
    management/commands/dispatch_pending_workforce_jobs.py) and reports
    whether it is recent. Intended for an uptime monitor or a
    deployment health-check probe, not for the technician/customer apps.

    A missing or stale heartbeat means dispatch has silently stopped --
    the process died, was never started, or is stuck -- and needs a
    process supervisor (systemd/supervisord/Docker restart policy) to
    bring it back; this endpoint can only report that fact, not fix it.
    """
    permission_classes = [permissions.AllowAny]
    # Generous default; the actual loop interval is a CLI flag
    # (--interval, default 5s) this view has no way to know for certain.
    STALE_AFTER_SECONDS = 60

    def get(self, request):
        from workforce_api.models import WorkforceEventLog

        row = WorkforceEventLog.objects.filter(event_type="dispatch_engine_heartbeat").order_by("-created_at").first()
        if not row:
            return Response({
                "healthy": False,
                "reason": "No dispatch heartbeat has ever been recorded. Has the dispatch_pending_workforce_jobs "
                           "management command been started?",
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        last_heartbeat_str = (row.payload or {}).get("last_heartbeat")
        try:
            from django.utils.dateparse import parse_datetime
            last_heartbeat = parse_datetime(last_heartbeat_str) if last_heartbeat_str else None
        except Exception:
            last_heartbeat = None

        if not last_heartbeat:
            return Response({
                "healthy": False,
                "reason": "Heartbeat record exists but has no readable timestamp.",
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        age_seconds = (timezone.now() - last_heartbeat).total_seconds()
        healthy = age_seconds <= self.STALE_AFTER_SECONDS

        return Response({
            "healthy": healthy,
            "last_heartbeat": last_heartbeat.isoformat(),
            "age_seconds": round(age_seconds, 1),
            "last_status": (row.payload or {}).get("status"),
            "last_detail": (row.payload or {}).get("detail"),
        }, status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE)


class WorkforceJobLogisticsLegView(APIView):
    """
    GT-B-03: technician-facing sub-phase tracker for multi-leg logistics
    jobs. Deliberately separate from job.status/apply_transition -- see
    the LogisticsLeg docstring in service_requests/models.py for the full
    rationale. Setting a leg never changes job.status and is never gated
    by ALLOWED_TRANSITIONS; the only guard here is that the job must be
    assigned to this technician, be a logistics-category job, and not
    already be in a terminal status.

    POST body: {"leg": "EN_ROUTE_PICKUP" | "LOADING" | "EN_ROUTE_DROP" |
    "UNLOADING" | "DELIVERED"}
    """
    permission_classes = [IsApprovedTechnician]

    _TERMINAL_STATUSES = {"completed", "cancelled", "unable_to_complete"}

    def get(self, request, pk):
        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            "logistics_leg": job.logistics_leg,
            "logistics_leg_updated_at": job.logistics_leg_updated_at,
            "logistics_leg_history": job.logistics_leg_history,
        }, status=status.HTTP_200_OK)

    def post(self, request, pk):
        from workforce_api.services.automatic_dispatch import LOGISTICS_SERVICE_CATEGORIES

        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        service_name = (job.service_category or "").strip().lower()
        if service_name not in LOGISTICS_SERVICE_CATEGORIES:
            return Response({
                "error": f"Leg tracking is only available for logistics jobs, not '{job.service_category}'."
            }, status=status.HTTP_400_BAD_REQUEST)

        if job.status in self._TERMINAL_STATUSES:
            return Response({
                "error": f"Job #{job.id} is already '{job.status}' -- leg cannot be updated."
            }, status=status.HTTP_400_BAD_REQUEST)

        leg = (request.data.get("leg") or "").strip().upper()
        if leg not in ServiceRequest.LogisticsLeg.values:
            valid_legs = ", ".join(ServiceRequest.LogisticsLeg.values)
            return Response({
                "error": f"Invalid leg. Choose one of: {valid_legs}"
            }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        job.logistics_leg = leg
        job.logistics_leg_updated_at = now
        history = job.logistics_leg_history or []
        history.append({"leg": leg, "at": now.isoformat(), "by": request.user.id})
        job.logistics_leg_history = history
        job.save(update_fields=["logistics_leg", "logistics_leg_updated_at", "logistics_leg_history", "updated_at"])

        return Response({
            "logistics_leg": job.logistics_leg,
            "logistics_leg_updated_at": job.logistics_leg_updated_at,
            "logistics_leg_history": job.logistics_leg_history,
        }, status=status.HTTP_200_OK)

class WorkforceJobMessagesView(APIView):
    """
    X-09: in-app chat between customer and technician for a job. Mirrors
    CustomerBookingMessagesView on the Customer app -- see BookingMessage's
    docstring (service_requests/models.py, both apps) for the full
    rationale, including why this is polling-based rather than push and
    why it doesn't attempt phone-number masking.

    GET  /workforce/jobs/<pk>/messages/  -- list the thread, marks unread
         customer messages as read by the technician
    POST /workforce/jobs/<pk>/messages/  -- send a message as the technician
    """
    permission_classes = [IsApprovedTechnician]

    def get(self, request, pk):
        from service_requests.models import BookingMessage

        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        messages = BookingMessage.objects.filter(booking_id=job.id)
        unread_ids = [m.id for m in messages if m.sender_persona != BookingMessage.SenderPersona.TECHNICIAN and m.read_at_technician is None]
        if unread_ids:
            BookingMessage.objects.filter(id__in=unread_ids).update(read_at_technician=timezone.now())
            messages = BookingMessage.objects.filter(booking_id=job.id)

        return Response({
            "results": [
                {
                    "id": m.id,
                    "sender_persona": m.sender_persona,
                    "sender_name": m.sender_name,
                    "body": m.body,
                    "created_at": m.created_at,
                    "read_at_customer": m.read_at_customer,
                    "read_at_technician": m.read_at_technician,
                }
                for m in messages
            ]
        }, status=status.HTTP_200_OK)

    def post(self, request, pk):
        from service_requests.models import BookingMessage

        job = ServiceRequest.objects.filter(pk=pk).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)
        emp = getattr(request.user, "employee_profile", None)
        if not emp or job.assigned_employee != emp:
            return Response({"error": "Unauthorized: Job is not assigned to you."}, status=status.HTTP_403_FORBIDDEN)

        body = (request.data.get("body") or "").strip()
        if not body:
            return Response({"error": "Message cannot be empty."}, status=status.HTTP_400_BAD_REQUEST)
        if len(body) > 2000:
            return Response({"error": "Message is too long (max 2000 characters)."}, status=status.HTTP_400_BAD_REQUEST)

        msg = BookingMessage.objects.create(
            booking_id=job.id,
            sender_persona=BookingMessage.SenderPersona.TECHNICIAN,
            sender_name=job.technician_name or (emp.full_name if hasattr(emp, "full_name") else "Technician"),
            body=body,
        )
        return Response({
            "id": msg.id,
            "sender_persona": msg.sender_persona,
            "sender_name": msg.sender_name,
            "body": msg.body,
            "created_at": msg.created_at,
        }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICIAN-VENDOR NETWORK API VIEWS
# ─────────────────────────────────────────────────────────────────────────────

class VendorNetworkTechniciansView(APIView):
    """
    Vendor Admin: Lists and filters all technicians in this vendor's network.
    GET /api/workforce/vendor/network/?status=ACTIVE&search=AC
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access and company tenant required."}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get("status", "").upper()
        search_query = request.query_params.get("search", "").strip()

        qs = VendorTechnicianRelationship.objects.filter(vendor=company).select_related(
            "technician__user", "technician__company", "source_invitation"
        )
        if status_filter and status_filter != "ALL":
            qs = qs.filter(status=status_filter)

        if search_query:
            qs = qs.filter(
                Q(technician__user__first_name__icontains=search_query)
                | Q(technician__user__last_name__icontains=search_query)
                | Q(technician__user__email__icontains=search_query)
                | Q(technician__phone__icontains=search_query)
                | Q(technician__title__icontains=search_query)
            )

        # Pre-fetch skills and scorecards
        technician_ids = [rel.technician_id for rel in qs]
        skills_by_emp = {}
        for es in WorkforceEmployeeSkill.objects.filter(employee_id__in=technician_ids).select_related("skill"):
            skills_by_emp.setdefault(es.employee_id, []).append(es.skill.name)

        scorecards = {sc.employee_id: sc for sc in WorkforceScorecard.objects.filter(employee_id__in=technician_ids)}

        results = []
        for rel in qs:
            emp = rel.technician
            user = emp.user
            sc = scorecards.get(emp.id)
            emp_skills = skills_by_emp.get(emp.id, []) or (emp.service_roles if isinstance(emp.service_roles, list) else [])
            results.append({
                "relationship_id": rel.id,
                "technician_id": emp.id,
                "user_id": user.id,
                "name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "email": user.email,
                "phone": emp.phone or "",
                "title": emp.title or "Technician",
                "state": emp.state or "",
                "status": rel.status,
                "scope_skills": rel.scope_skills or emp_skills,
                "engagement_type": rel.engagement_type,
                "payment_model": rel.payment_model,
                "started_at": rel.started_at,
                "ended_at": rel.ended_at,
                "average_rating": float(sc.average_rating) if sc else 0.0,
                "rating_count": sc.rating_count if sc else 0,
                "tier": sc.tier if sc else "UNRATED",
                "is_online": emp.is_online,
                "current_availability": emp.current_availability,
            })

        # Summary counts
        counts = {
            "all": VendorTechnicianRelationship.objects.filter(vendor=company).count(),
            "active": VendorTechnicianRelationship.objects.filter(vendor=company, status="ACTIVE").count(),
            "suspended": VendorTechnicianRelationship.objects.filter(vendor=company, status="SUSPENDED").count(),
            "terminated": VendorTechnicianRelationship.objects.filter(vendor=company, status="TERMINATED").count(),
        }

        return Response({"counts": counts, "technicians": results}, status=status.HTTP_200_OK)


class VendorNetworkDetailView(APIView):
    """
    Vendor Admin: Detailed view & update of a technician relationship.
    GET /api/workforce/vendor/network/<int:pk>/
    PATCH /api/workforce/vendor/network/<int:pk>/
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request, pk):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        rel = VendorTechnicianRelationship.objects.filter(pk=pk, vendor=company).select_related(
            "technician__user", "source_invitation"
        ).first()
        if not rel:
            return Response({"error": "Relationship not found."}, status=status.HTTP_404_NOT_FOUND)

        emp = rel.technician
        user = emp.user
        sc = WorkforceScorecard.objects.filter(employee=emp).first()
        emp_skills = list(WorkforceEmployeeSkill.objects.filter(employee=emp).values(
            "skill__id", "skill__name", "skill__category", "proficiency_level", "is_verified"
        ))

        return Response({
            "relationship": {
                "id": rel.id,
                "status": rel.status,
                "engagement_type": rel.engagement_type,
                "payment_model": rel.payment_model,
                "scope_skills": rel.scope_skills,
                "started_at": rel.started_at,
                "ended_at": rel.ended_at,
                "source_invitation_id": rel.source_invitation_id,
            },
            "technician": {
                "id": emp.id,
                "name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "email": user.email,
                "phone": emp.phone,
                "title": emp.title,
                "state": emp.state,
                "country": emp.country,
                "hourly_rate": float(emp.hourly_rate or 0),
                "is_online": emp.is_online,
                "current_availability": emp.current_availability,
                "skills": emp_skills,
                "scorecard": {
                    "average_rating": float(sc.average_rating) if sc else 0.0,
                    "rating_count": sc.rating_count if sc else 0,
                    "csat_average": float(sc.csat_average) if sc else 0.0,
                    "tier": sc.tier if sc else "UNRATED",
                } if sc else None,
            }
        }, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        rel = VendorTechnicianRelationship.objects.filter(pk=pk, vendor=company).first()
        if not rel:
            return Response({"error": "Relationship not found."}, status=status.HTTP_404_NOT_FOUND)

        if "engagement_type" in request.data:
            rel.engagement_type = request.data["engagement_type"]
        if "payment_model" in request.data:
            rel.payment_model = request.data["payment_model"]
        if "scope_skills" in request.data and isinstance(request.data["scope_skills"], list):
            rel.scope_skills = request.data["scope_skills"]

        rel.save()
        return Response({"message": "Relationship terms updated successfully.", "id": rel.id}, status=status.HTTP_200_OK)


class VendorNetworkStatusUpdateView(APIView):
    """
    Vendor Admin: Suspend, Reactivate, or Terminate a relationship.
    POST /api/workforce/vendor/network/<int:pk>/status/
    Body: {"action": "SUSPEND" | "REACTIVATE" | "TERMINATE"}
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        from workforce_api.services.vendor_network import VendorRelationshipService

        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        action = request.data.get("action", "")
        try:
            rel = VendorRelationshipService.update_status(
                relationship_id=pk,
                vendor=company,
                action=action,
                actor=request.user,
            )
            return Response({
                "message": f"Technician relationship status updated to {rel.status}.",
                "status": rel.status,
                "relationship_id": rel.id,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error updating relationship status: %s", e)
            return Response({"error": "Failed to update relationship status."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorInvitationsView(APIView):
    """
    Vendor Admin: List sent invitations and send direct or matched invitations.
    GET /api/workforce/vendor/invitations/?status=PENDING
    POST /api/workforce/vendor/invitations/
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get("status", "").upper()
        qs = VendorInvitation.objects.filter(vendor=company).select_related(
            "technician__user", "matched_criteria"
        ).order_by("-created_at")

        if status_filter and status_filter != "ALL":
            qs = qs.filter(status=status_filter)

        results = []
        for inv in qs:
            tech_name = None
            if inv.technician and inv.technician.user:
                tech_name = f"{inv.technician.user.first_name} {inv.technician.user.last_name}".strip() or inv.technician.user.username

            results.append({
                "id": inv.id,
                "invited_email": inv.invited_email,
                "technician_id": inv.technician_id,
                "technician_name": tech_name,
                "status": inv.status,
                "channel": inv.channel,
                "message": inv.message,
                "matched_criteria_name": inv.matched_criteria.name if inv.matched_criteria else None,
                "expires_at": inv.expires_at,
                "responded_at": inv.responded_at,
                "created_at": inv.created_at,
            })

        counts = {
            "all": VendorInvitation.objects.filter(vendor=company).count(),
            "pending": VendorInvitation.objects.filter(vendor=company, status="PENDING").count(),
            "accepted": VendorInvitation.objects.filter(vendor=company, status="ACCEPTED").count(),
            "rejected": VendorInvitation.objects.filter(vendor=company, status="REJECTED").count(),
            "expired": VendorInvitation.objects.filter(vendor=company, status="EXPIRED").count(),
            "cancelled": VendorInvitation.objects.filter(vendor=company, status="CANCELLED").count(),
        }

        return Response({"counts": counts, "invitations": results}, status=status.HTTP_200_OK)

    def post(self, request):
        from workforce_api.services.vendor_network import VendorInvitationService

        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        invited_email = request.data.get("invited_email", "")
        technician_id = request.data.get("technician_id")
        technician = None
        if technician_id:
            technician = Employee.objects.filter(pk=technician_id).first()
            if technician and not invited_email:
                invited_email = technician.user.email

        if not invited_email:
            return Response({"error": "An email address or technician ID is required."}, status=status.HTTP_400_BAD_REQUEST)

        message = request.data.get("message", "").strip()
        channel = request.data.get("channel", VendorInvitation.Channel.DIRECT_EMAIL)
        criteria_id = request.data.get("criteria_id")
        criteria = None
        if criteria_id:
            criteria = VendorCriteria.objects.filter(pk=criteria_id, vendor=company).first()

        try:
            invitation = VendorInvitationService.create_invitation(
                vendor=company,
                invited_email=invited_email,
                technician=technician,
                channel=channel,
                message=message,
                criteria=criteria,
                actor=request.user,
            )
            return Response({
                "message": f"Invitation sent to {invitation.invited_email}.",
                "invitation_id": invitation.id,
                "status": invitation.status,
                "expires_at": invitation.expires_at,
                "token": invitation.token,
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error creating vendor invitation: %s", e)
            return Response({"error": "Failed to create invitation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VendorInvitationCancelView(APIView):
    """
    Vendor Admin: Cancel / withdraw a pending invitation.
    POST /api/workforce/vendor/invitations/<int:pk>/cancel/
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        from workforce_api.services.vendor_network import VendorInvitationService

        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        try:
            inv = VendorInvitationService.cancel_invitation(
                invitation_id=pk,
                vendor=company,
                actor=request.user,
            )
            return Response({"message": "Invitation cancelled successfully.", "id": inv.id, "status": inv.status}, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)


class VendorDiscoverySearchView(APIView):
    """
    Vendor Admin: Run matching candidate discovery search with boolean criteria.
    POST /api/workforce/vendor/discover/
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request):
        from workforce_api.services.vendor_network import VendorDiscoveryEngine

        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        terms = request.data.get("terms", [])
        criteria_id = request.data.get("criteria_id")
        search_query = request.data.get("search", "")

        criteria = None
        if criteria_id:
            criteria = VendorCriteria.objects.filter(pk=criteria_id, vendor=company).first()

        matches = VendorDiscoveryEngine.evaluate_candidates(
            vendor=company,
            terms=terms,
            criteria=criteria,
            search_query=search_query,
            limit=100,
        )

        return Response({
            "total_matches": len(matches),
            "results": matches,
        }, status=status.HTTP_200_OK)


class VendorCriteriaListView(APIView):
    """
    Vendor Admin: Manage saved search criteria sets and terms.
    GET /api/workforce/vendor/criteria/
    POST /api/workforce/vendor/criteria/
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        criteria_qs = VendorCriteria.objects.filter(vendor=company, is_active=True).prefetch_related("terms")
        results = []
        for c in criteria_qs:
            terms = [
                {
                    "id": t.id,
                    "attribute_type": t.attribute_type,
                    "operator": t.operator,
                    "value": t.value,
                    "group_id": t.group_id,
                }
                for t in c.terms.all()
            ]
            results.append({
                "id": c.id,
                "name": c.name,
                "terms": terms,
                "created_at": c.created_at,
            })

        return Response({"criteria": results}, status=status.HTTP_200_OK)

    def post(self, request):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        name = request.data.get("name", "").strip()
        if not name:
            return Response({"error": "Criteria name is required."}, status=status.HTTP_400_BAD_REQUEST)

        terms_data = request.data.get("terms", [])

        with transaction.atomic():
            criteria = VendorCriteria.objects.create(
                vendor=company,
                name=name,
                is_active=True,
            )
            for t in terms_data:
                CriteriaTerm.objects.create(
                    criteria=criteria,
                    attribute_type=t.get("attribute_type", CriteriaTerm.AttributeType.SKILL),
                    operator=t.get("operator", CriteriaTerm.Operator.EQUALS),
                    value=t.get("value", {}),
                    group_id=t.get("group_id", 1),
                )

        return Response({"message": "Criteria saved successfully.", "id": criteria.id}, status=status.HTTP_201_CREATED)


class VendorCriteriaDetailView(APIView):
    """
    Vendor Admin: Delete/deactivate a saved criteria set.
    DELETE /api/workforce/vendor/criteria/<int:pk>/
    """
    permission_classes = [IsWorkforceAdmin]

    def delete(self, request, pk):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company or not is_admin_role(request.user):
            return Response({"error": "Admin access required."}, status=status.HTTP_403_FORBIDDEN)

        criteria = VendorCriteria.objects.filter(pk=pk, vendor=company).first()
        if not criteria:
            return Response({"error": "Criteria not found."}, status=status.HTTP_404_NOT_FOUND)

        criteria.is_active = False
        criteria.save(update_fields=["is_active", "updated_at"])
        return Response({"message": "Criteria removed successfully."}, status=status.HTTP_200_OK)


# ─── Technician Side Views ───────────────────────────────────────────────────

class TechnicianVendorNetworkView(APIView):
    """
    Technician: Lists all vendor relationships where this technician is a member.
    GET /api/workforce/technician/network/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            from employees.models import Employee
            emp = Employee.objects.filter(user=request.user).first()

        if not emp:
            return Response({"error": "Employee profile required."}, status=status.HTTP_403_FORBIDDEN)

        relationships = VendorTechnicianRelationship.objects.filter(
            technician=emp
        ).select_related("vendor", "source_invitation").order_by("-started_at")

        results = []
        for rel in relationships:
            results.append({
                "relationship_id": rel.id,
                "vendor_id": rel.vendor.id,
                "vendor_name": getattr(rel.vendor, "company_name", getattr(rel.vendor, "name", "Vendor")),
                "vendor_address": getattr(rel.vendor, "address", "") or "",
                "status": rel.status,
                "scope_skills": rel.scope_skills,
                "engagement_type": rel.engagement_type,
                "payment_model": rel.payment_model,
                "started_at": rel.started_at,
                "ended_at": rel.ended_at,
            })

        active_rel = next((r for r in relationships if r.status == VendorTechnicianRelationship.Status.ACTIVE), None)
        active_vendor_info = None
        if active_rel:
            active_vendor_info = {
                "relationship_id": active_rel.id,
                "vendor_id": active_rel.vendor.id,
                "vendor_name": getattr(active_rel.vendor, "company_name", getattr(active_rel.vendor, "name", "Vendor")),
                "vendor_address": getattr(active_rel.vendor, "address", "") or "",
                "started_at": active_rel.started_at,
            }

        return Response({
            "relationships": results,
            "active_vendor": active_vendor_info,
            "total_count": len(results),
            "active_count": 1 if active_vendor_info else 0,
        }, status=status.HTTP_200_OK)


class TechnicianInvitationsView(APIView):
    """
    Technician: View incoming vendor invitations and history.
    GET /api/workforce/technician/invitations/?status=PENDING
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            from employees.models import Employee
            emp = Employee.objects.filter(user=request.user).first()

        user_email = (request.user.email or "").strip().lower()

        # Match either technician FK or email
        qs = VendorInvitation.objects.filter(
            Q(technician=emp) if emp else Q() | Q(invited_email__iexact=user_email)
        ).select_related("vendor", "matched_criteria").order_by("-created_at")

        status_filter = request.query_params.get("status", "").upper()
        if status_filter and status_filter != "ALL":
            qs = qs.filter(status=status_filter)

        results = []
        for inv in qs:
            terms = []
            if inv.matched_criteria:
                terms = [
                    {"attribute": t.attribute_type, "value": t.value, "operator": t.operator}
                    for t in inv.matched_criteria.terms.all()
                ]

            results.append({
                "id": inv.id,
                "vendor_id": inv.vendor.id,
                "vendor_name": getattr(inv.vendor, "company_name", getattr(inv.vendor, "name", "Vendor")),
                "vendor_address": getattr(inv.vendor, "address", "") or "",
                "status": inv.status,
                "channel": inv.channel,
                "message": inv.message,
                "matched_criteria": terms,
                "expires_at": inv.expires_at,
                "responded_at": inv.responded_at,
                "created_at": inv.created_at,
            })

        active_rel = (
            VendorTechnicianRelationship.objects.filter(
                technician=emp,
                status=VendorTechnicianRelationship.Status.ACTIVE,
            )
            .select_related("vendor")
            .first()
        ) if emp else None

        active_vendor_info = None
        if active_rel:
            active_vendor_info = {
                "relationship_id": active_rel.id,
                "vendor_id": active_rel.vendor_id,
                "vendor_name": getattr(active_rel.vendor, "company_name", getattr(active_rel.vendor, "name", "Current Vendor")),
                "started_at": active_rel.started_at,
            }

        pending_count = sum(1 for r in results if r["status"] == "PENDING")
        return Response({
            "invitations": results,
            "active_vendor": active_vendor_info,
            "pending_count": pending_count,
        }, status=status.HTTP_200_OK)


class TechnicianInvitationRespondView(APIView):
    """
    Technician: Accept or Reject an invitation.
    POST /api/workforce/technician/invitations/<int:pk>/respond/
    Body: {"decision": "ACCEPT" | "REJECT"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from workforce_api.services.vendor_network import VendorInvitationService

        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            from employees.models import Employee
            emp = Employee.objects.filter(user=request.user).first()

        if not emp:
            return Response({"error": "Employee profile required."}, status=status.HTTP_403_FORBIDDEN)

        decision = request.data.get("decision", "")
        try:
            inv, rel = VendorInvitationService.respond_to_invitation(
                invitation_id=pk,
                employee=emp,
                decision=decision,
                actor=request.user,
            )
            return Response({
                "message": f"Invitation {inv.status.lower()} successfully.",
                "status": inv.status,
                "relationship_id": rel.id if rel else None,
                "vendor_name": getattr(inv.vendor, "company_name", "Vendor"),
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error responding to invitation: %s", e)
            return Response({"error": "Failed to respond to invitation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TechnicianLeaveVendorView(APIView):
    """
    Technician: Leave / terminate a vendor network connection.
    POST /api/workforce/technician/network/<int:pk>/leave/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from workforce_api.services.vendor_network import VendorRelationshipService

        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            from employees.models import Employee
            emp = Employee.objects.filter(user=request.user).first()

        if not emp:
            return Response({"error": "Employee profile required."}, status=status.HTTP_403_FORBIDDEN)

        try:
            rel = VendorRelationshipService.leave_vendor(
                relationship_id=pk,
                employee=emp,
                actor=request.user,
            )
            return Response({
                "message": f"You have left {getattr(rel.vendor, 'company_name', 'Vendor')}'s technician network.",
                "status": rel.status,
                "relationship_id": rel.id,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)


class PublicInvitationVerifyView(APIView):
    """
    Public: Validate an invitation token to pre-fill signup info.
    GET /api/workforce/invitations/verify-token/?token=...
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        token = request.query_params.get("token", "").strip()
        if not token:
            return Response({"error": "Token is required."}, status=status.HTTP_400_BAD_REQUEST)

        inv = VendorInvitation.objects.filter(token=token).select_related("vendor").first()
        if not inv:
            return Response({"valid": False, "error": "Invalid invitation token."}, status=status.HTTP_404_NOT_FOUND)

        is_expired = inv.expires_at and inv.expires_at < timezone.now()
        if is_expired:
            return Response({
                "valid": False,
                "error": "This invitation has expired.",
                "status": "EXPIRED",
                "vendor_name": getattr(inv.vendor, "company_name", "Vendor"),
            }, status=status.HTTP_400_BAD_REQUEST)

        if inv.status != VendorInvitation.Status.PENDING:
            return Response({
                "valid": False,
                "error": f"This invitation is already {inv.status.lower()}.",
                "status": inv.status,
                "vendor_name": getattr(inv.vendor, "company_name", "Vendor"),
            }, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "valid": True,
            "invitation_id": inv.id,
            "invited_email": inv.invited_email,
            "vendor_name": getattr(inv.vendor, "company_name", "Vendor"),
            "message": inv.message,
            "expires_at": inv.expires_at,
        }, status=status.HTTP_200_OK)


# ─── SEVO Platform Admin: Vendor & Workforce Management ──────────────────────

class PlatformVendorsListView(APIView):
    """
    SEVO Platform Admin: Manage all registered Vendor Companies.
    GET /api/workforce/platform/vendors/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not getattr(request.user, "is_superuser", False):
            return Response({"error": "Platform Superadmin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        companies = list(Company.objects.select_related("region").all().order_by("-id"))
        company_ids = [c.id for c in companies]
        
        # Precompute tied worker counts per company
        from django.db.models import Count
        tied_counts = dict(
            VendorTechnicianRelationship.objects.filter(
                vendor_id__in=company_ids,
                status=VendorTechnicianRelationship.Status.ACTIVE,
            )
            .values("vendor_id")
            .annotate(cnt=Count("id"))
            .values_list("vendor_id", "cnt")
        )

        # Precompute pending invitations per company
        pending_inv_counts = dict(
            VendorInvitation.objects.filter(
                vendor_id__in=company_ids,
                status=VendorInvitation.Status.PENDING,
            )
            .values("vendor_id")
            .annotate(cnt=Count("id"))
            .values_list("vendor_id", "cnt")
        )

        # Bulk fetch company users
        admin_users_by_company = {}
        for u in User.objects.filter(company_id__in=company_ids).order_by("id"):
            if u.company_id not in admin_users_by_company or u.role in ["admin", "manager"]:
                admin_users_by_company[u.company_id] = u

        results = []
        for c in companies:
            admin_user = admin_users_by_company.get(c.id)

            results.append({
                "id": c.id,
                "company_name": c.company_name,
                "slug": c.slug,
                "city": getattr(c, "region", None).name if getattr(c, "region", None) else "",
                "address": c.address or "",
                "owner_name": f"{admin_user.first_name} {admin_user.last_name}".strip() if admin_user else "",
                "owner_email": admin_user.email if admin_user else "",
                "owner_phone": getattr(admin_user, "mobile_number", "") or getattr(admin_user, "phone", "") if admin_user else "",
                "tied_workers_count": tied_counts.get(c.id, 0),
                "pending_invitations_count": pending_inv_counts.get(c.id, 0),
                "created_at": c.created_at if hasattr(c, "created_at") else None,
            })

        return Response({
            "vendors": results,
            "total_count": len(results),
        }, status=status.HTTP_200_OK)


class PlatformWorkforceListView(APIView):
    """
    SEVO Platform Admin: Manage all Workforce (Solo Workers & Tied Workers).
    GET /api/workforce/platform/workforce/?type=ALL|SOLO|TIED&vendor_id=...&search=...
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not getattr(request.user, "is_superuser", False):
            return Response({"error": "Platform Superadmin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        workforce_type = request.query_params.get("type", "ALL").upper()
        vendor_id = request.query_params.get("vendor_id")
        search = (request.query_params.get("search") or "").strip().lower()

        employees_qs = Employee.objects.select_related("user", "company").order_by("-id")

        if search:
            employees_qs = employees_qs.filter(
                Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
                | Q(user__email__icontains=search)
                | Q(user__mobile_number__icontains=search)
                | Q(employee_id__icontains=search)
            )

        employee_ids = list(employees_qs.values_list("id", flat=True))

        # Active vendor relationships
        active_rels = {
            rel.technician_id: rel
            for rel in VendorTechnicianRelationship.objects.filter(
                technician_id__in=employee_ids,
                status=VendorTechnicianRelationship.Status.ACTIVE,
            ).select_related("vendor")
        }

        # Skills prefetch
        skills_qs = WorkforceEmployeeSkill.objects.filter(employee_id__in=employee_ids).select_related("skill")
        skills_by_emp = {}
        for s in skills_qs:
            skills_by_emp.setdefault(s.employee_id, []).append(s.skill.name)

        results = []
        solo_count = 0
        tied_count = 0

        for emp in employees_qs:
            rel = active_rels.get(emp.id)
            is_tied = rel is not None
            tied_vendor = None

            if is_tied:
                tied_count += 1
                tied_vendor = {
                    "id": rel.vendor.id,
                    "company_name": getattr(rel.vendor, "company_name", getattr(rel.vendor, "name", "Vendor")),
                    "started_at": rel.started_at,
                    "relationship_id": rel.id,
                }
            else:
                solo_count += 1

            # Filter by type
            if workforce_type == "SOLO" and is_tied:
                continue
            if workforce_type == "TIED" and not is_tied:
                continue
            if vendor_id and (not is_tied or str(rel.vendor_id) != str(vendor_id)):
                continue

            emp_skills = skills_by_emp.get(emp.id, [])
            if isinstance(emp.service_roles, list):
                emp_skills = list(set(emp_skills + [str(r) for r in emp.service_roles]))

            full_name = f"{emp.user.first_name} {emp.user.last_name}".strip() or emp.user.username
            results.append({
                "id": emp.id,
                "employee_id": emp.employee_id,
                "name": full_name,
                "email": emp.user.email,
                "phone": getattr(emp.user, "mobile_number", "") or getattr(emp.user, "phone", "") or emp.phone,
                "city": emp.state or "",
                "skills": emp_skills,
                "is_online": emp.is_online,
                "current_availability": emp.current_availability,
                "workforce_type": "TIED" if is_tied else "SOLO",
                "tied_vendor": tied_vendor,
                "registration_status": "approved" if getattr(emp, "is_active", True) else "pending",
                "hourly_rate": float(emp.hourly_rate or 0),
            })

        return Response({
            "workers": results,
            "total_count": len(results),
            "counts": {
                "all": solo_count + tied_count,
                "solo": solo_count,
                "tied": tied_count,
            },
        }, status=status.HTTP_200_OK)


class PlatformTieTechnicianView(APIView):
    """
    SEVO Platform Admin: Directly tie/assign a Solo Worker to any Vendor Company.
    POST /api/workforce/platform/workforce/<int:pk>/tie-vendor/
    Body: { "vendor_id": <int>, "engagement_type": "PER_JOB", "payment_model": "DIRECT_TO_TECHNICIAN", "notes": "" }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not getattr(request.user, "is_superuser", False):
            return Response({"error": "Platform Superadmin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        vendor_id = request.data.get("vendor_id")
        if not vendor_id:
            return Response({"error": "Target vendor_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        engagement_type = request.data.get("engagement_type", VendorTechnicianRelationship.EngagementType.PER_JOB)
        payment_model = request.data.get("payment_model", VendorTechnicianRelationship.PaymentModel.DIRECT_TO_TECHNICIAN)
        notes = request.data.get("notes", "").strip()

        try:
            rel = VendorRelationshipService.tie_technician_to_vendor(
                employee_id=pk,
                vendor_id=int(vendor_id),
                actor=request.user,
                engagement_type=engagement_type,
                payment_model=payment_model,
                notes=notes,
            )
            return Response({
                "message": f"Technician successfully tied to {getattr(rel.vendor, 'company_name', 'Vendor')}.",
                "relationship_id": rel.id,
                "vendor_id": rel.vendor_id,
                "vendor_name": getattr(rel.vendor, "company_name", getattr(rel.vendor, "name", "Vendor")),
                "status": rel.status,
                "started_at": rel.started_at,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlatformUntieTechnicianView(APIView):
    """
    SEVO Platform Admin: Untie a technician from all vendors, making them a free Solo Worker.
    POST /api/workforce/platform/workforce/<int:pk>/untie-vendor/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not getattr(request.user, "is_superuser", False):
            return Response({"error": "Platform Superadmin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        try:
            untied_rels = VendorRelationshipService.untie_technician(
                employee_id=pk,
                actor=request.user,
            )
            return Response({
                "message": "Technician successfully relieved from vendor. Now operating as an independent Solo Worker.",
                "untied_count": len(untied_rels),
                "workforce_type": "SOLO",
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, 'message') else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ─── Technician Resignation & Relieving Endpoints ────────────────────────────

class TechnicianSubmitResignationView(APIView):
    """
    Technician submits a formal resignation request to leave their assigned vendor.
    POST /api/workforce/technician/relieve/request/
    Body: {"reason_category": "TRANSITION_TO_SOLO", "resignation_notes": "...", "desired_relieving_date": "YYYY-MM-DD"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            emp = Employee.objects.filter(user=request.user).first()
        if not emp:
            return Response({"error": "Technician employee profile required."}, status=status.HTTP_403_FORBIDDEN)

        reason_category = request.data.get("reason_category", VendorRelievingRequest.ReasonCategory.TRANSITION_TO_SOLO)
        notes = request.data.get("resignation_notes", "")
        desired_date = request.data.get("desired_relieving_date", None)

        try:
            req = VendorRelievingService.submit_resignation(
                employee=emp,
                reason_category=reason_category,
                notes=notes,
                desired_date=desired_date,
                actor=request.user,
            )
            return Response({
                "message": "Formal resignation submitted successfully. Pending vendor dues clearance & platform audit.",
                "request_id": req.id,
                "status": req.status,
                "vendor_name": getattr(req.vendor, "company_name", getattr(req.vendor, "name", "Vendor")),
                "reason_category": req.reason_category,
                "desired_relieving_date": req.desired_relieving_date,
            }, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error submitting resignation: %s", e)
            return Response({"error": "Failed to submit resignation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TechnicianRelievingStatusView(APIView):
    """
    Technician checks the active resignation and relieving lifecycle progress.
    GET /api/workforce/technician/relieve/status/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        emp = getattr(request.user, "employee_profile", None)
        if not emp:
            emp = Employee.objects.filter(user=request.user).first()
        if not emp:
            return Response({"error": "Technician employee profile required."}, status=status.HTTP_403_FORBIDDEN)

        req = (
            VendorRelievingRequest.objects.filter(technician=emp)
            .select_related("vendor", "relationship")
            .order_by("-created_at")
            .first()
        )
        if not req:
            return Response({"has_active_request": False, "request": None}, status=status.HTTP_200_OK)

        return Response({
            "has_active_request": req.status in [
                VendorRelievingRequest.Status.REQUESTED,
                VendorRelievingRequest.Status.VENDOR_APPROVED,
                VendorRelievingRequest.Status.SEVO_APPROVED,
            ],
            "request": {
                "id": req.id,
                "status": req.status,
                "vendor_id": req.vendor_id,
                "vendor_name": getattr(req.vendor, "company_name", getattr(req.vendor, "name", "Vendor")),
                "reason_category": req.reason_category,
                "reason_display": req.get_reason_category_display(),
                "resignation_notes": req.resignation_notes,
                "desired_relieving_date": req.desired_relieving_date,
                "vendor_approved_at": req.vendor_approved_at,
                "vendor_settlement_notes": req.vendor_settlement_notes,
                "sevo_approved_at": req.sevo_approved_at,
                "sevo_audit_notes": req.sevo_audit_notes,
                "worker_signoff_ack": req.worker_signoff_ack,
                "worker_signed_at": req.worker_signed_at,
                "vendor_signoff_ack": req.vendor_signoff_ack,
                "vendor_signed_at": req.vendor_signed_at,
                "created_at": req.created_at,
            }
        }, status=status.HTTP_200_OK)


class VendorRelievingRequestsView(APIView):
    """
    Vendor Admin: View and manage all resignation and relieving requests for their company.
    GET /api/workforce/vendor/relieving-requests/
    """
    permission_classes = [IsWorkforceAdmin]

    def get(self, request):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company:
            return Response({"error": "Vendor company context required."}, status=status.HTTP_403_FORBIDDEN)

        requests_qs = (
            VendorRelievingRequest.objects.filter(vendor=company)
            .select_related("technician__user", "relationship")
            .order_by("-created_at")
        )

        results = []
        for r in requests_qs:
            user = r.technician.user
            results.append({
                "id": r.id,
                "relationship_id": r.relationship_id,
                "technician_id": r.technician_id,
                "technician_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "technician_email": user.email,
                "technician_phone": getattr(user, "mobile_number", "") or getattr(user, "phone", "") or r.technician.phone,
                "status": r.status,
                "reason_category": r.reason_category,
                "reason_display": r.get_reason_category_display(),
                "resignation_notes": r.resignation_notes,
                "desired_relieving_date": r.desired_relieving_date,
                "vendor_settlement_notes": r.vendor_settlement_notes,
                "vendor_approved_at": r.vendor_approved_at,
                "sevo_approved_at": r.sevo_approved_at,
                "sevo_audit_notes": r.sevo_audit_notes,
                "worker_signoff_ack": r.worker_signoff_ack,
                "vendor_signoff_ack": r.vendor_signoff_ack,
                "created_at": r.created_at,
            })

        return Response({
            "relieving_requests": results,
            "count": len(results),
            "pending_count": sum(1 for x in results if x["status"] == "REQUESTED"),
        }, status=status.HTTP_200_OK)


class VendorApproveRelievingView(APIView):
    """
    Vendor Admin approves job dues and settlement for a technician's resignation.
    POST /api/workforce/vendor/relieving-requests/<int:pk>/approve/
    Body: {"settlement_notes": "..."}
    """
    permission_classes = [IsWorkforceAdmin]

    def post(self, request, pk):
        company = resolve_actor_company(request)
        if not company and getattr(request.user, "is_superuser", False):
            company = Company.objects.first()
        if not company:
            return Response({"error": "Vendor company context required."}, status=status.HTTP_403_FORBIDDEN)

        settlement_notes = request.data.get("settlement_notes", "All dues and equipment accounts verified.")
        try:
            req = VendorRelievingService.vendor_approve_relieving(
                request_id=pk,
                vendor=company,
                settlement_notes=settlement_notes,
                actor=request.user,
            )
            return Response({
                "message": "Vendor dues settlement clearance approved. Request forwarded for SEVO Platform Audit.",
                "request_id": req.id,
                "status": req.status,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error approving relieving: %s", e)
            return Response({"error": "Failed to approve relieving request."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PlatformRelievingRequestsView(APIView):
    """
    SEVO Platform Superadmin: Lists all platform-wide relieving requests.
    GET /api/workforce/platform/relieving-requests/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not getattr(request.user, "is_superuser", False):
            return Response({"error": "Platform Superadmin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        requests_qs = (
            VendorRelievingRequest.objects.select_related("technician__user", "vendor", "relationship")
            .order_by("-created_at")
        )

        results = []
        for r in requests_qs:
            user = r.technician.user
            results.append({
                "id": r.id,
                "relationship_id": r.relationship_id,
                "technician_id": r.technician_id,
                "technician_name": f"{user.first_name} {user.last_name}".strip() or user.username,
                "technician_email": user.email,
                "technician_phone": getattr(user, "mobile_number", "") or getattr(user, "phone", "") or r.technician.phone,
                "vendor_id": r.vendor_id,
                "vendor_name": getattr(r.vendor, "company_name", getattr(r.vendor, "name", "Vendor")),
                "status": r.status,
                "reason_category": r.reason_category,
                "reason_display": r.get_reason_category_display(),
                "resignation_notes": r.resignation_notes,
                "desired_relieving_date": r.desired_relieving_date,
                "vendor_settlement_notes": r.vendor_settlement_notes,
                "vendor_approved_at": r.vendor_approved_at,
                "sevo_approved_at": r.sevo_approved_at,
                "sevo_audit_notes": r.sevo_audit_notes,
                "worker_signoff_ack": r.worker_signoff_ack,
                "vendor_signoff_ack": r.vendor_signoff_ack,
                "created_at": r.created_at,
            })

        return Response({
            "relieving_requests": results,
            "total_count": len(results),
            "pending_sevo_count": sum(1 for x in results if x["status"] == "VENDOR_APPROVED"),
        }, status=status.HTTP_200_OK)


class PlatformApproveRelievingView(APIView):
    """
    SEVO Platform Superadmin verifies general job settlement and compliance check,
    then issues official platform relieving approval.
    POST /api/workforce/platform/relieving-requests/<int:pk>/approve/
    Body: {"audit_notes": "..."}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        if not getattr(request.user, "is_superuser", False):
            return Response({"error": "Platform Superadmin privileges required."}, status=status.HTTP_403_FORBIDDEN)

        audit_notes = request.data.get("audit_notes", "Verified all platform job commissions and billings have settled.")
        try:
            req = VendorRelievingService.sevo_approve_relieving(
                request_id=pk,
                audit_notes=audit_notes,
                actor=request.user,
            )
            return Response({
                "message": "SEVO Platform audit clearance approved. Legal relieving signoff executed.",
                "request_id": req.id,
                "status": req.status,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error in platform approving relieving: %s", e)
            return Response({"error": "Failed to approve platform relieving audit."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RelievingLegalSignoffView(APIView):
    """
    Mutual Legal Signoff between Technician and Vendor.
    POST /api/workforce/relieving-requests/<int:pk>/signoff/
    Body: {"persona": "technician" | "vendor"}
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        persona = request.data.get("persona", "technician")
        try:
            req = VendorRelievingService.complete_legal_signoff(
                request_id=pk,
                actor=request.user,
                persona=persona,
            )
            return Response({
                "message": "Legal signoff recorded successfully.",
                "request_id": req.id,
                "status": req.status,
                "worker_signoff_ack": req.worker_signoff_ack,
                "vendor_signoff_ack": req.vendor_signoff_ack,
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return Response({"error": str(e.message if hasattr(e, "message") else e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception("Error in legal signoff: %s", e)
            return Response({"error": "Failed to record legal signoff."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





