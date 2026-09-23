"""
workforce-app/backend/workforce_api/serializers.py
DRF serializers for Workforce Signup, Onboarding Wizard, Verification Dossier, and Jobs.
"""
from decimal import Decimal
from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers
from employees.models import Employee
from service_requests.models import ServiceRequest
from .models import WalletAccount

User = get_user_model()


class WorkforceSignupSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    mobile_number = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_mobile_number(self, value):
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if User.objects.filter(mobile_number=cleaned).exists():
            raise serializers.ValidationError("An account with this mobile number already exists.")
        return cleaned


class WorkforceOnboardingDraftSerializer(serializers.Serializer):
    step = serializers.IntegerField(min_value=1, max_value=7, required=False)
    draft_data = serializers.DictField(required=True)


class WorkforceEmployeeProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    first_name = serializers.CharField(source="user.first_name", read_only=True)
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    email = serializers.CharField(source="user.email", read_only=True)
    mobile_number = serializers.CharField(source="user.mobile_number", read_only=True)
    phone = serializers.CharField(source="user.phone", read_only=True)
    bio = serializers.CharField(source="user.bio", read_only=True)
    timezone = serializers.CharField(source="user.timezone", read_only=True)
    language = serializers.CharField(source="user.language", read_only=True)
    two_fa_enabled = serializers.BooleanField(source="user.two_fa_enabled", read_only=True)
    avatar = serializers.SerializerMethodField()
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    registration_status = serializers.SerializerMethodField()
    live_availability = serializers.CharField(source="current_availability", read_only=True)
    onboarding_data = serializers.SerializerMethodField()
    approved_services = serializers.SerializerMethodField()
    all_requested_services = serializers.SerializerMethodField()
    documents_status = serializers.SerializerMethodField()
    controlled_fields = serializers.SerializerMethodField()
    is_tied = serializers.SerializerMethodField()
    is_solo = serializers.SerializerMethodField()
    tied_vendor = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = [
            "id",
            "user_id",
            "employee_id",
            "username",
            "first_name",
            "last_name",
            "email",
            "mobile_number",
            "phone",
            "bio",
            "timezone",
            "language",
            "avatar",
            "two_fa_enabled",
            "company_id",
            "company_name",
            "title",
            "country",
            "state",
            "department",
            "hourly_rate",
            "hire_date",
            "date_of_birth",
            "is_online",
            "live_availability",
            "registration_status",
            "onboarding_data",
            "approved_services",
            "all_requested_services",
            "documents_status",
            "controlled_fields",
            "is_tied",
            "is_solo",
            "tied_vendor",
            "is_active",
        ]

    def get_avatar(self, obj):
        if obj.user and obj.user.avatar:
            try:
                return obj.user.avatar.url
            except Exception:
                return str(obj.user.avatar)
        return ""

    def get_onboarding_data(self, obj):
        return (obj.bank_details or {}).get("onboarding", {
            "status": "not_started",
            "step": 1,
            "draft": {},
            "services": [],
            "documents": {},
            "correction_notes": "",
            "rejection_reason": "",
        })

    def get_registration_status(self, obj):
        ob = (obj.bank_details or {}).get("onboarding", {})
        return ob.get("status", "not_started")

    def get_approved_services(self, obj):
        ob = (obj.bank_details or {}).get("onboarding", {})
        services = ob.get("services", [])
        return [s for s in services if s.get("status") == "approved"]

    def get_all_requested_services(self, obj):
        ob = (obj.bank_details or {}).get("onboarding", {})
        return ob.get("services", [])

    def get_documents_status(self, obj):
        ob = (obj.bank_details or {}).get("onboarding", {})
        docs_dict = dict(ob.get("documents", {}))

        # Include relational WorkforceEmployeeDocument models if present
        try:
            from workforce_api.models import WorkforceEmployeeDocument
            emp_docs = WorkforceEmployeeDocument.objects.filter(employee=obj).select_related("requirement")
            for ed in emp_docs:
                cat = ed.requirement.category or ed.requirement.title.lower().replace(" ", "_")
                existing = docs_dict.get(cat, {})
                docs_dict[cat] = {
                    "category": cat,
                    "title": ed.requirement.title or existing.get("title", cat.replace("_", " ").title()),
                    "document_number": ed.document_number or existing.get("document_number", ""),
                    "file_url": ed.file_url or existing.get("file_url", ""),
                    "status": ed.status.lower() if ed.status else existing.get("status", "approved"),
                    "issue_date": str(ed.issue_date) if ed.issue_date else existing.get("issue_date"),
                    "expiry_date": str(ed.expiry_date) if ed.expiry_date else existing.get("expiry_date"),
                    "uploaded_at": ed.created_at.isoformat() if ed.created_at else existing.get("uploaded_at"),
                    "rejection_reason": ed.rejection_reason or existing.get("rejection_reason", ""),
                }
        except Exception:
            pass

        return docs_dict

    def get_controlled_fields(self, obj):
        # Fields that are locked once registration is submitted/approved
        reg_status = self.get_registration_status(obj)
        is_locked = reg_status in ["submitted", "under_review", "approved"]
        return {
            "is_locked": is_locked,
            "locked_fields": [
                "first_name",
                "last_name",
                "date_of_birth",
                "mobile_number",
                "employee_id",
                "country",
                "state",
                "department",
                "hourly_rate",
                "bank_account",
                "identity_documents",
            ] if is_locked else [],
        }

    def _get_active_vendor_rel(self, obj):
        if not hasattr(obj, "_cached_active_vendor_rel"):
            from workforce_api.models import VendorTechnicianRelationship
            obj._cached_active_vendor_rel = VendorTechnicianRelationship.objects.filter(
                technician=obj,
                status__in=[
                    VendorTechnicianRelationship.Status.ACTIVE,
                    VendorTechnicianRelationship.Status.RESIGNATION_REQUESTED,
                ],
            ).select_related("vendor").first()
        return obj._cached_active_vendor_rel

    def get_is_tied(self, obj):
        return bool(self._get_active_vendor_rel(obj))

    def get_is_solo(self, obj):
        return not self.get_is_tied(obj)

    def get_tied_vendor(self, obj):
        active_rel = self._get_active_vendor_rel(obj)
        if active_rel and active_rel.vendor:
            return {
                "id": active_rel.vendor.id,
                "company_name": getattr(active_rel.vendor, "company_name", getattr(active_rel.vendor, "name", "Vendor")),
                "engagement_type": active_rel.engagement_type,
                "started_at": active_rel.started_at,
            }
        elif getattr(obj, "company_id", None) and getattr(obj, "company", None):
            return {
                "id": obj.company.id,
                "company_name": getattr(obj.company, "company_name", getattr(obj.company, "name", "Vendor")),
                "engagement_type": "EMPLOYEE",
                "started_at": obj.hire_date,
            }
        return None



class WorkforceWorkExtensionSerializer(serializers.ModelSerializer):
    technician_name = serializers.SerializerMethodField()
    technician_id = serializers.CharField(source="technician.employee_id", read_only=True)
    required_skill_name = serializers.CharField(source="required_skill.name", read_only=True)
    admin_reviewer_name = serializers.SerializerMethodField()
    specialist_technician_name = serializers.SerializerMethodField()

    class Meta:
        from .models import WorkforceWorkExtension
        model = WorkforceWorkExtension
        fields = [
            "id",
            "job",
            "technician",
            "technician_id",
            "technician_name",
            "company",
            "title",
            "description",
            "reason",
            "estimated_labor_cost",
            "estimated_materials_cost",
            "requested_amount",
            "approved_amount",
            "final_customer_amount",
            "requires_specialist",
            "required_skill",
            "required_skill_name",
            "specialist_technician",
            "specialist_technician_name",
            "specialist_job",
            "is_critical",
            "decision_token",
            "decision_expires_at",
            "supporting_notes",
            "supporting_photo",
            "status",
            "admin_reviewed_by",
            "admin_reviewer_name",
            "admin_review_reason",
            "admin_reviewed_at",
            "customer_decided_at",
            "customer_decline_reason",
            "completed_at",
            "resolved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id", "technician", "company", "approved_amount", "final_customer_amount",
            "status", "decision_token", "decision_expires_at", "admin_reviewed_by",
            "admin_reviewed_at", "customer_decided_at", "completed_at", "resolved_at",
            "created_at", "updated_at",
        ]

    def get_technician_name(self, obj):
        if obj.technician and obj.technician.user:
            return obj.technician.user.get_full_name() or obj.technician.user.username
        return "Technician"

    def get_admin_reviewer_name(self, obj):
        if obj.admin_reviewed_by:
            return obj.admin_reviewed_by.get_full_name() or obj.admin_reviewed_by.username
        return None

    def get_specialist_technician_name(self, obj):
        if obj.specialist_technician and obj.specialist_technician.user:
            return obj.specialist_technician.user.get_full_name() or obj.specialist_technician.user.username
        return None


class CustomerWorkforceExtensionSerializer(serializers.ModelSerializer):
    """
    Sanitized, customer-facing serialization for Additional Work decisions.
    Hides internal technician labor margins, notes, and staff details.
    """
    extension_id = serializers.IntegerField(source="id", read_only=True)
    job_id = serializers.IntegerField(source="job.id", read_only=True)
    request_id = serializers.CharField(source="job.request_id", read_only=True)
    original_service = serializers.SerializerMethodField()
    admin_approved_amount = serializers.DecimalField(source="approved_amount", max_digits=10, decimal_places=2, read_only=True)
    is_expired = serializers.SerializerMethodField()

    class Meta:
        from .models import WorkforceWorkExtension
        model = WorkforceWorkExtension
        fields = [
            "extension_id",
            "job_id",
            "request_id",
            "original_service",
            "title",
            "description",
            "reason",
            "estimated_labor_cost",
            "estimated_materials_cost",
            "requested_amount",
            "admin_approved_amount",
            "final_customer_amount",
            "is_critical",
            "requires_specialist",
            "status",
            "decision_expires_at",
            "is_expired",
            "customer_decided_at",
            "customer_decline_reason",
            "created_at",
        ]

    def get_original_service(self, obj):
        return obj.job.issue_title or obj.job.service_category if obj.job else "Service"

    def get_is_expired(self, obj):
        from django.utils import timezone
        if not obj.decision_expires_at:
            return False
        return timezone.now() > obj.decision_expires_at


class WorkforceSupplementalInvoiceSerializer(serializers.ModelSerializer):
    customer_name = serializers.SerializerMethodField()

    class Meta:
        from .models import WorkforceSupplementalInvoice
        model = WorkforceSupplementalInvoice
        fields = [
            "id",
            "invoice_number",
            "job",
            "extension",
            "customer",
            "customer_name",
            "company",
            "amount",
            "actual_cost",
            "status",
            "payment_method",
            "transaction_id",
            "paid_at",
            "metadata",
            "audit_trail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "invoice_number", "created_at", "updated_at"]

    def get_customer_name(self, obj):
        if obj.customer:
            return obj.customer.get_full_name() or obj.customer.username
        return "Customer"


class WorkforceJobRescheduleSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import WorkforceJobReschedule
        model = WorkforceJobReschedule
        fields = [
            "id",
            "job",
            "delay_count",
            "delay_type",
            "original_date",
            "rescheduled_date",
            "reason",
            "customer_notified",
            "escalated_to_support",
            "escalation_notes",
            "customer_response",
            "customer_notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class JobPaymentSerializer(serializers.ModelSerializer):
    """
    Public/Employee-safe payment details serializer.
    NEVER exposes payment_confirmation_otp_hash, otp_attempts, or internal secrets.
    """
    class Meta:
        from .models import JobPayment
        model = JobPayment
        fields = [
            "id",
            "job",
            "payment_method",
            "payment_status",
            "amount_due",
            "amount_paid",
            "amount_received",
            "change_returned",
            "currency",
            "gateway_transaction_id",
            "cash_collected_at",
            "is_cash_collected",
            "customer_confirmed_at",
            "customer_confirmation_method",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PaymentCollectionEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        from .models import PaymentCollectionEvent
        model = PaymentCollectionEvent
        fields = [
            "id",
            "job_payment",
            "event_type",
            "actor_type",
            "actor_name",
            "metadata",
            "created_at",
        ]
        read_only_fields = fields

    def get_actor_name(self, obj):
        if obj.actor_user:
            return obj.actor_user.get_full_name() or obj.actor_user.username
        if obj.actor_employee:
            return obj.actor_employee.full_name
        return "System"


class WorkforceJobSerializer(serializers.ModelSerializer):
    customer_display_name = serializers.SerializerMethodField()
    phone = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    service_title = serializers.SerializerMethodField()
    job_status = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    active_offer = serializers.SerializerMethodField()
    cancellation_info = serializers.SerializerMethodField()
    extensions = serializers.SerializerMethodField()
    active_extension = serializers.SerializerMethodField()
    offer_status = serializers.SerializerMethodField()
    is_offer = serializers.SerializerMethodField()
    is_accepted_by_current_employee = serializers.SerializerMethodField()
    is_assigned_to_current_employee = serializers.SerializerMethodField()
    accepted_at = serializers.SerializerMethodField()
    distance_km = serializers.SerializerMethodField()
    cancellation_deadline = serializers.SerializerMethodField()
    offer_expires_at = serializers.SerializerMethodField()
    settlement_channel = serializers.SerializerMethodField()
    earnings_wallet_owner = serializers.SerializerMethodField()
    request_kind = serializers.CharField(read_only=True)
    is_estimation = serializers.SerializerMethodField()
    pricing_mode = serializers.SerializerMethodField()
    can_create_quote = serializers.SerializerMethodField()
    active_quote_id = serializers.SerializerMethodField()
    active_quote_number = serializers.SerializerMethodField()
    # GT: the logistics half of a job. Without these the driver app can see
    # where to collect from but not where to deliver to, and has no idea
    # which leg of the trip it is on -- the leg/stop endpoints existed but
    # nothing in the job payload told the app they applied.
    is_logistics = serializers.SerializerMethodField()
    trip_stop_count = serializers.SerializerMethodField()

    class Meta:
        model = ServiceRequest
        fields = [
            "id",
            "request_id",
            "customer_name",
            "phone",
            "email",
            "service_category",
            "issue_title",
            "service_title",
            "description",
            "cart_data",
            "status",
            "priority",
            "address",
            "latitude",
            "longitude",
            "distance_km",
            "preferred_date",
            "preferred_time",
            "total_amount",
            "payment_status",
            "payment_method",
            "payment",
            "customer_display_name",
            "active_offer",
            "cancellation_info",
            "extensions",
            "active_extension",
            "created_at",
            "updated_at",
            "otp_verified",
            # Authoritative fields
            "job_status",
            "offer_status",
            "is_offer",
            "is_accepted_by_current_employee",
            "is_assigned_to_current_employee",
            "accepted_at",
            "cancellation_deadline",
            "offer_expires_at",
            # SEVO Section 6: per-job attribution -- which wallet this job's
            # earnings settle into, independent of which employee physically
            # performed the job (see WalletLedgerEntry.worker_performed).
            "settlement_channel",
            "earnings_wallet_owner",
            # Commercial Estimation & Quotation Workflow fields
            "request_kind",
            "is_estimation",
            "pricing_mode",
            "can_create_quote",
            "active_quote_id",
            "active_quote_number",
            # Goods & Transport
            "is_logistics",
            "drop_address",
            "drop_latitude",
            "drop_longitude",
            "drop_contact_name",
            "drop_contact_phone",
            "logistics_leg",
            "logistics_leg_updated_at",
            "trip_stop_count",
        ]

    def get_is_logistics(self, obj):
        from workforce_api.services.automatic_dispatch import LOGISTICS_SERVICE_CATEGORIES
        return (obj.service_category or "").strip().lower() in LOGISTICS_SERVICE_CATEGORIES

    def get_trip_stop_count(self, obj):
        trip_stops_map = self.context.get("trip_stops_map")
        if trip_stops_map is not None:
            return trip_stops_map.get(obj.id, 0)
        try:
            from service_requests.models import TripStop
            return TripStop.objects.filter(booking=obj).count()
        except Exception:
            return 0

    def _get_context_emp(self):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return None
        return getattr(request.user, "employee_profile", None)

    def _get_emp_offer(self, obj, emp):
        if not emp:
            return None
        emp_offers_map = self.context.get("emp_offers_map")
        if emp_offers_map is not None:
            return emp_offers_map.get(obj.id)
        from .models import WorkforceJobOffer
        return WorkforceJobOffer.objects.filter(job=obj, employee=emp).order_by("-offered_at").first()

    def _resolve_wallet_channel(self, obj):
        """Cheap, best-effort: which wallet this job would settle into if
        completed right now. Never raises -- an unassigned job or one
        whose worker has no wallet yet simply has no channel to show."""
        if hasattr(obj, "_cached_wallet_channel"):
            return obj._cached_wallet_channel
        if not obj.assigned_employee_id:
            obj._cached_wallet_channel = (None, None)
            return None, None
        try:
            from workforce_api.services import resolve_payee_wallet
            wallet, channel = resolve_payee_wallet(obj)
        except Exception:
            wallet, channel = None, None
        obj._cached_wallet_channel = (wallet, channel)
        return wallet, channel

    def get_settlement_channel(self, obj):
        _wallet, channel = self._resolve_wallet_channel(obj)
        return channel

    def get_earnings_wallet_owner(self, obj):
        wallet, _channel = self._resolve_wallet_channel(obj)
        if not wallet:
            return None
        if wallet.company_id:
            return wallet.company.company_name
        emp = wallet.employee
        return emp.user.get_full_name() if emp and emp.user_id else None

    def get_job_status(self, obj):
        return obj.status

    def get_is_accepted_by_current_employee(self, obj):
        emp = self._get_context_emp()
        if not emp:
            return False
        from workforce_api.services.workload import ACTIVE_WORKLOAD_STATUSES
        is_assigned = (obj.assigned_employee_id == emp.id)
        is_active = str(obj.status).lower() in ACTIVE_WORKLOAD_STATUSES
        return bool(is_assigned and is_active)

    def get_is_assigned_to_current_employee(self, obj):
        emp = self._get_context_emp()
        if not emp:
            return False
        return bool(obj.assigned_employee_id == emp.id)

    def get_is_offer(self, obj):
        if self.get_is_accepted_by_current_employee(obj) or self.get_is_assigned_to_current_employee(obj):
            return False
        emp = self._get_context_emp()
        if not emp:
            return False
        offer = self._get_emp_offer(obj, emp)
        from django.utils import timezone
        if offer and offer.status == "OFFERED" and offer.expires_at > timezone.now():
            return True
        return False

    def get_offer_status(self, obj):
        emp = self._get_context_emp()
        if not emp:
            return None
        if self.get_is_accepted_by_current_employee(obj):
            return "ACCEPTED"
        offer = self._get_emp_offer(obj, emp)
        if not offer:
            return None
        from django.utils import timezone
        if offer.status == "OFFERED" and offer.expires_at <= timezone.now():
            return "EXPIRED"
        return offer.status

    def get_offer_expires_at(self, obj):
        if not self.get_is_offer(obj):
            return None
        emp = self._get_context_emp()
        offer = self._get_emp_offer(obj, emp)
        from django.utils import timezone
        if offer and offer.status == "OFFERED" and offer.expires_at > timezone.now():
            return offer.expires_at.isoformat()
        return None

    def get_accepted_at(self, obj):
        if not self.get_is_accepted_by_current_employee(obj):
            return None
        emp = self._get_context_emp()
        lifecycle_events_map = self.context.get("lifecycle_events_map")
        if lifecycle_events_map is not None:
            accept_event = lifecycle_events_map.get(obj.id)
        else:
            from .models import WorkforceJobLifecycleEvent
            accept_event = WorkforceJobLifecycleEvent.objects.filter(
                job=obj,
                employee=emp,
                event_type=WorkforceJobLifecycleEvent.EventType.EMPLOYEE_JOB_ACCEPTED,
            ).order_by("-created_at").first()
        if accept_event and accept_event.accepted_at:
            return accept_event.accepted_at.isoformat()
        return (obj.updated_at or obj.created_at).isoformat() if (obj.updated_at or obj.created_at) else None

    def get_cancellation_deadline(self, obj):
        if not self.get_is_accepted_by_current_employee(obj):
            return None
        if obj.status not in ["accepted", "on_the_way"]:
            return None
        emp = self._get_context_emp()
        lifecycle_events_map = self.context.get("lifecycle_events_map")
        if lifecycle_events_map is not None:
            accept_event = lifecycle_events_map.get(obj.id)
        else:
            from .models import WorkforceJobLifecycleEvent
            accept_event = WorkforceJobLifecycleEvent.objects.filter(
                job=obj,
                employee=emp,
                event_type=WorkforceJobLifecycleEvent.EventType.EMPLOYEE_JOB_ACCEPTED,
            ).order_by("-created_at").first()
        if accept_event and accept_event.cancellation_deadline:
            return accept_event.cancellation_deadline.isoformat()
        from datetime import timedelta
        from django.utils import timezone
        accepted_at = accept_event.accepted_at if accept_event else (obj.updated_at or obj.created_at)
        if accepted_at:
            deadline = accepted_at + timedelta(minutes=5)
            if deadline > timezone.now():
                return deadline.isoformat()
        return None

    def get_distance_km(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return None
        last_loc = getattr(request.user, "last_known_location", None) or {}
        emp_lat = last_loc.get("latitude") if last_loc.get("latitude") is not None else last_loc.get("lat")
        emp_lon = last_loc.get("longitude") if last_loc.get("longitude") is not None else (last_loc.get("lng") or last_loc.get("lon"))
        if emp_lat is None or emp_lon is None or obj.latitude is None or obj.longitude is None:
            return None
        try:
            from time_tracking.geo import haversine_distance
            dist_m = haversine_distance(float(emp_lat), float(emp_lon), float(obj.latitude), float(obj.longitude))
            return round(dist_m / 1000.0, 2)
        except Exception:
            return None

    def get_customer_display_name(self, obj):
        if obj.customer_name and not str(obj.customer_name).startswith("cust_"):
            return obj.customer_name
        if obj.customer:
            cust = obj.customer
            full = f"{cust.first_name or ''} {cust.last_name or ''}".strip()
            if full and not full.startswith("cust_"):
                return full
            if getattr(cust, "name", None) and not str(cust.name).startswith("cust_"):
                return cust.name
            try:
                addr = cust.saved_addresses.filter(receiver_name__isnull=False).exclude(receiver_name="").first()
                if addr and addr.receiver_name:
                    return addr.receiver_name
            except Exception:
                pass
            if cust.phone:
                return f"Customer ({str(cust.phone)[-4:]})"
            if cust.username and not str(cust.username).startswith("cust_"):
                return cust.username
        if obj.phone:
            return f"Customer ({str(obj.phone)[-4:]})"
        return obj.customer_name or "Valued Customer"

    def get_phone(self, obj):
        if obj.phone:
            return str(obj.phone)
        if obj.customer:
            cust = obj.customer
            if getattr(cust, "phone", None):
                return str(cust.phone)
            if getattr(cust, "mobile_number", None):
                return str(cust.mobile_number)
            if cust.username and cust.username.isdigit():
                return cust.username
            if cust.username and cust.username.startswith("cust_") and cust.username[5:].isdigit():
                return cust.username[5:]
        return ""

    def get_email(self, obj):
        if obj.email:
            return obj.email
        if obj.customer and getattr(obj.customer, "email", None):
            return obj.customer.email
        return ""

    def get_address(self, obj):
        if obj.address:
            return obj.address
        if obj.customer:
            try:
                addr = obj.customer.saved_addresses.first()
                if addr and getattr(addr, "address_line1", None):
                    return addr.formatted_address or addr.address_line1
            except Exception:
                pass
        return ""

    def get_service_title(self, obj):
        return obj.issue_title or obj.service_category

    def get_active_offer(self, obj):
        if self.get_is_accepted_by_current_employee(obj):
            return None
        emp = self._get_context_emp()
        if not emp:
            return None
        active_offers_map = self.context.get("active_offers_map")
        if active_offers_map is not None:
            offer = active_offers_map.get(obj.id)
        else:
            from .models import WorkforceJobOffer
            from django.utils import timezone
            offer = WorkforceJobOffer.objects.filter(job=obj, employee=emp, status="OFFERED").first()
            if offer and offer.expires_at <= timezone.now():
                offer = None
        if not offer:
            return None
        return {
            "id": offer.id,
            "status": "OFFERED",
            "offered_at": offer.offered_at.isoformat(),
            "expires_at": offer.expires_at.isoformat(),
            "is_expired": False,
        }

    def get_extensions(self, obj):
        extensions_map = self.context.get("extensions_map")
        if extensions_map is not None:
            exts = extensions_map.get(obj.id, [])
            return [
                {
                    "id": ext.id,
                    "job": ext.job_id,
                    "technician": ext.technician_id,
                    "technician_id": getattr(ext.technician, "employee_id", str(ext.technician_id)),
                    "technician_name": (f"{ext.technician.user.first_name} {ext.technician.user.last_name}".strip() or ext.technician.user.username) if ext.technician and ext.technician.user else "Technician",
                    "company": ext.company_id,
                    "title": ext.title,
                    "description": ext.description,
                    "reason": ext.reason,
                    "estimated_labor_cost": str(ext.estimated_labor_cost or "0.00"),
                    "estimated_materials_cost": str(ext.estimated_materials_cost or "0.00"),
                    "total_extension_cost": str(getattr(ext, "requested_amount", None) or getattr(ext, "approved_amount", None) or ((ext.estimated_labor_cost or 0) + (ext.estimated_materials_cost or 0)) or "0.00"),
                    "status": ext.status,
                    "requires_specialist": ext.requires_specialist,
                    "is_critical": ext.is_critical,
                    "created_at": ext.created_at.isoformat() if ext.created_at else None,
                }
                for ext in exts
            ]
        from .models import WorkforceWorkExtension
        exts = WorkforceWorkExtension.objects.filter(job=obj).order_by("-created_at")
        return WorkforceWorkExtensionSerializer(exts, many=True).data

    def get_active_extension(self, obj):
        active_extensions_map = self.context.get("active_extensions_map")
        if active_extensions_map is not None:
            active = active_extensions_map.get(obj.id)
            if active:
                return {
                    "id": active.id,
                    "job": active.job_id,
                    "technician": active.technician_id,
                    "technician_id": getattr(active.technician, "employee_id", str(active.technician_id)),
                    "technician_name": (f"{active.technician.user.first_name} {active.technician.user.last_name}".strip() or active.technician.user.username) if active.technician and active.technician.user else "Technician",
                    "company": active.company_id,
                    "title": active.title,
                    "description": active.description,
                    "reason": active.reason,
                    "estimated_labor_cost": str(active.estimated_labor_cost or "0.00"),
                    "estimated_materials_cost": str(active.estimated_materials_cost or "0.00"),
                    "total_extension_cost": str(getattr(active, "requested_amount", None) or getattr(active, "approved_amount", None) or ((active.estimated_labor_cost or 0) + (active.estimated_materials_cost or 0)) or "0.00"),
                    "status": active.status,
                    "requires_specialist": active.requires_specialist,
                    "is_critical": active.is_critical,
                    "created_at": active.created_at.isoformat() if active.created_at else None,
                }
            return None
        from .models import WorkforceWorkExtension
        active = WorkforceWorkExtension.objects.filter(
            job=obj,
            status__in=["REQUESTED", "ADMIN_APPROVED", "CUSTOMER_ACCEPTED", "IN_PROGRESS"]
        ).first()
        if active:
            return WorkforceWorkExtensionSerializer(active).data
        return None

    def get_payment(self, obj):
        payments_map = self.context.get("payments_map")
        if payments_map is not None:
            pmt = payments_map.get(obj.id)
        else:
            from .models import JobPayment
            pmt = getattr(obj, "payment_record", None)
            if not pmt:
                pmt = JobPayment.objects.filter(job=obj).first()
        if not pmt:
            is_online = (obj.payment_method or "").upper() in ["ONLINE", "PREPAID"]
            is_paid = obj.payment_status in ["paid", "collected"]
            return {
                "id": None,
                "job": obj.id,
                "payment_method": "ONLINE" if is_online else "CASH_ON_SERVICE",
                "payment_status": "PAID" if is_paid else "PENDING",
                "amount_due": str(obj.total_amount or "0.00"),
                "amount_paid": str(obj.total_amount if is_paid else "0.00"),
                "amount_received": None,
                "change_returned": None,
                "currency": "INR",
                "cash_collected_at": None,
                "customer_confirmed_at": None,
                "customer_confirmation_method": "",
            }
        return JobPaymentSerializer(pmt).data

    def get_cancellation_info(self, obj):
        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return None
        emp = getattr(request.user, "employee_profile", None)
        if not emp or obj.assigned_employee_id != emp.id:
            return None

        if obj.status not in ["accepted", "on_the_way", "en_route"]:
            return {
                "can_cancel": False,
                "reason": "Not in cancellable state",
                "remaining_seconds": 0,
            }

        emp_jobs_map = self.context.get("emp_jobs_map")
        if emp_jobs_map is not None:
            emp_job = emp_jobs_map.get(obj.id)
        else:
            from service_requests.models import EmployeeJob
            emp_job = EmployeeJob.objects.filter(service_request=obj, employee=emp).first()
        accepted_at = (emp_job.accepted_date if emp_job and emp_job.accepted_date else None) or obj.updated_at
        if not accepted_at:
            return None

        deadline = accepted_at + timedelta(minutes=5)
        now = timezone.now()
        remaining_seconds = max(0, int((deadline - now).total_seconds()))
        can_cancel = remaining_seconds > 0

        return {
            "can_cancel": can_cancel,
            "accepted_at": accepted_at.isoformat(),
            "cancellation_deadline": deadline.isoformat(),
            "remaining_seconds": remaining_seconds,
        }

    def _get_active_quote(self, obj):
        if not getattr(obj, "is_estimation", False):
            return None
        quotes_map = self.context.get("quotes_map")
        if quotes_map is not None:
            return quotes_map.get(obj.id)
        if not hasattr(obj, "_cached_active_quote"):
            from .models import WorkforceQuote
            obj._cached_active_quote = (
                WorkforceQuote.objects.filter(job=obj)
                .exclude(status__in=[WorkforceQuote.Status.SUPERSEDED, WorkforceQuote.Status.CANCELLED])
                .order_by("-quote_version")
                .first()
            )
        return obj._cached_active_quote

    def get_is_estimation(self, obj):
        return bool(getattr(obj, "is_estimation", False))

    def get_pricing_mode(self, obj):
        return getattr(obj, "pricing_mode", "FIXED")

    def get_active_quote_id(self, obj):
        q = self._get_active_quote(obj)
        return q.id if q else None

    def get_active_quote_number(self, obj):
        q = self._get_active_quote(obj)
        return q.quote_number if q else None

    def get_can_create_quote(self, obj):
        if not getattr(obj, "is_estimation", False):
            return False
        psvs_map = self.context.get("psvs_map")
        psv = psvs_map.get(obj.id) if psvs_map is not None else None
        from .services import quotation_service
        can_quote, _ = quotation_service.can_create_quote(obj, psv=psv)
        return bool(can_quote)


class WorkforceEmployeeChangeRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id = serializers.CharField(source="employee.employee_id", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()

    class Meta:
        from .models import WorkforceEmployeeChangeRequest
        model = WorkforceEmployeeChangeRequest
        fields = [
            "id",
            "employee",
            "employee_id",
            "employee_name",
            "field_name",
            "field_label",
            "old_value",
            "new_value",
            "reason",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee",
            "employee_id",
            "employee_name",
            "status",
            "admin_notes",
            "reviewed_by",
            "reviewed_by_name",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]

    def get_employee_name(self, obj):
        if obj.employee and obj.employee.user:
            return obj.employee.user.get_full_name()
        return "Technician"

    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return obj.reviewed_by.get_full_name() or obj.reviewed_by.username
        return ""


class WorkforceUserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import WorkforceUserPreference
        model = WorkforceUserPreference
        fields = [
            "id",
            "theme",
            "accent_color",
            "layout_density",
            "font_size",
            "high_contrast",
            "reduced_motion",
            "updated_at",
        ]


class WorkforceNotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import WorkforceNotificationPreference
        model = WorkforceNotificationPreference
        fields = [
            "id",
            "security_alerts",
            "login_alerts",
            "leave_updates",
            "job_assignments",
            "shift_reminders",
            "payroll_notifications",
            "weekly_digest",
            "product_updates",
            "workspace_announcements",
            "channel_email",
            "channel_in_app",
            "channel_sms",
            "updated_at",
        ]


class WorkforceJobFeedbackSerializer(serializers.ModelSerializer):
    service_title = serializers.CharField(source="job.issue_title", read_only=True)
    request_id = serializers.CharField(source="job.request_id", read_only=True)

    class Meta:
        from .models import WorkforceJobFeedback
        model = WorkforceJobFeedback
        fields = [
            "id",
            "job",
            "request_id",
            "service_title",
            "rating",
            "review",
            "csat_score",
            "resolution_ontime",
            "customer_name",
            "created_at",
        ]


class EmployeeSavedLocationSerializer(serializers.ModelSerializer):
    """Serializer for employee-owned personal saved locations."""
    latitude = serializers.FloatField()
    longitude = serializers.FloatField()

    def validate_latitude(self, value):
        from decimal import Decimal
        try:
            val = float(value)
            if not (-90.0 <= val <= 90.0):
                raise serializers.ValidationError("Latitude must be between -90 and 90.")
            return Decimal(str(round(val, 7)))
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid latitude.")

    def validate_longitude(self, value):
        from decimal import Decimal
        try:
            val = float(value)
            if not (-180.0 <= val <= 180.0):
                raise serializers.ValidationError("Longitude must be between -180 and 180.")
            return Decimal(str(round(val, 7)))
        except (ValueError, TypeError):
            raise serializers.ValidationError("Invalid longitude.")

    class Meta:
        from .models import EmployeeSavedLocation
        model = EmployeeSavedLocation
        fields = [
            "id",
            "label",
            "name",
            "address",
            "locality",
            "city",
            "state",
            "pincode",
            "landmark",
            "latitude",
            "longitude",
            "is_default",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ProviderSignupSerializer(serializers.Serializer):
    """
    SEVO business plan Section 2, "Existing Service Provider Model": a
    service-provider business (plumbing outfit, electrical contractor, etc)
    self-registers, gets its own Company row and PROVIDER_HEAD wallet, and
    can then invite its own workers to join that company (see
    WorkforceSignupSerializer, which already supports joining a specific
    company via company_id/company_slug).
    """
    business_name = serializers.CharField(max_length=255)
    contact_first_name = serializers.CharField(max_length=150)
    contact_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    mobile_number = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    business_type = serializers.ChoiceField(
        choices=["service_provider", "grocery_supplier", "hybrid"],
        required=False,
        default="service_provider",
    )
    address = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField(required=False, allow_blank=True, default="Hosur")

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_mobile_number(self, value):
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if User.objects.filter(mobile_number=cleaned).exists():
            raise serializers.ValidationError("An account with this mobile number already exists.")
        return cleaned

    def validate_business_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Business name is required.")
        return value


class WalletAccountSerializer(serializers.ModelSerializer):
    """Read/write surface for a wallet owner's own onboarding + payout
    status. Balance and withdrawal_limit are computed, never stored."""
    balance = serializers.SerializerMethodField()
    withdrawal_limit = serializers.SerializerMethodField()
    owner_role = serializers.SerializerMethodField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = WalletAccount
        fields = [
            "id",
            "account_type",
            "kyc_tier",
            "kyc_tier_updated_at",
            "payout_bank_account_name",
            "payout_bank_account_number_masked",
            "payout_ifsc",
            "payout_upi_id",
            "auto_withdrawal_enabled",
            "auto_withdrawal_frequency",
            "auto_withdrawal_day_of_week",
            "minimum_balance_alert_threshold",
            "balance",
            "withdrawal_limit",
            "owner_role",
            "owner_name",
        ]
        read_only_fields = ["id", "account_type", "kyc_tier", "kyc_tier_updated_at"]

    def get_balance(self, obj):
        return obj.current_balance()

    def get_withdrawal_limit(self, obj):
        return obj.withdrawal_limit_for_tier()

    def get_owner_role(self, obj):
        return self.context.get("owner_role", "")

    def get_owner_name(self, obj):
        if obj.company_id:
            return obj.company.company_name
        emp = obj.employee
        return emp.user.get_full_name() if emp and emp.user_id else ""


class WalletPayoutDetailsSerializer(serializers.Serializer):
    """Input serializer for setting/updating payout destination -- either a
    UPI ID, or a full bank account. Validation (at least one, valid IFSC
    shape) is delegated to services.wallet_onboarding.set_payout_details so
    there's exactly one place that decides what a "valid" payout
    destination looks like."""
    bank_account_name = serializers.CharField(required=False, allow_blank=True, default="")
    bank_account_number = serializers.CharField(required=False, allow_blank=True, default="")
    ifsc = serializers.CharField(required=False, allow_blank=True, default="")
    upi_id = serializers.CharField(required=False, allow_blank=True, default="")


class WalletWithdrawSerializer(serializers.Serializer):
    """Input serializer for an on-demand self-service withdrawal request."""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.01"))


class WalletAutoWithdrawalSettingsSerializer(serializers.Serializer):
    """Input serializer for the head-wallet standing auto-payout rule and
    minimum-balance alert floor (SEVO Section 1, head-wallet specific
    features). All fields optional so a caller can update just one."""
    auto_withdrawal_enabled = serializers.BooleanField(required=False)
    auto_withdrawal_frequency = serializers.ChoiceField(
        choices=[("DAILY", "Daily"), ("WEEKLY", "Weekly"), ("", "")], required=False, allow_blank=True,
    )
    auto_withdrawal_day_of_week = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=6)
    minimum_balance_alert_threshold = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True, min_value=Decimal("0"),
    )


# ── Multi-Vendor Grocery Marketplace Serializers ───────────────────────────────

class VendorStoreSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)

    class Meta:
        from .models import VendorStore
        model = VendorStore
        fields = [
            "id",
            "company",
            "company_name",
            "store_name",
            "store_slug",
            "tagline",
            "description",
            "logo_url",
            "banner_url",
            "fssai_license_number",
            "gst_number",
            "store_address",
            "latitude",
            "longitude",
            "delivery_radius_km",
            "minimum_order_amount",
            "estimated_delivery_mins",
            "is_accepting_orders",
            "opening_time",
            "closing_time",
            "rating_average",
            "total_reviews",
            "onboarding",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "rating_average", "total_reviews", "created_at", "updated_at"]


class GrocerySellerSignupSerializer(serializers.Serializer):
    """
    Serializer for Sevo Seller Hub (grocery store / supermarket merchant registration).
    Creates an inactive Company, inactive User, and inactive VendorStore with structured onboarding blob.
    """
    business_name = serializers.CharField(max_length=255)
    store_name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    contact_first_name = serializers.CharField(max_length=150)
    contact_last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    mobile_number = serializers.CharField(max_length=20)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=6)
    address = serializers.CharField(required=False, allow_blank=True, default="")
    city = serializers.CharField(required=False, allow_blank=True, default="Hosur")
    fssai_license_number = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    gst_number = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    categories = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )
    documents = serializers.DictField(required=False, default=dict)

    def validate_email(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate_mobile_number(self, value):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        cleaned = value.strip().replace(" ", "").replace("-", "")
        if User.objects.filter(mobile_number=cleaned).exists():
            raise serializers.ValidationError("An account with this mobile number already exists.")
        return cleaned

    def validate_business_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Business name is required.")
        return value


class GrocerySellerApplicationDetailSerializer(serializers.ModelSerializer):
    """
    Comprehensive serializer for the Admin Seller Application dossier review queue.
    """
    company_id = serializers.IntegerField(source="company.id", read_only=True)
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    company_slug = serializers.CharField(source="company.slug", read_only=True)
    is_company_active = serializers.BooleanField(source="company.is_active", read_only=True)
    owner = serializers.SerializerMethodField()
    onboarding_data = serializers.SerializerMethodField()
    registration_status = serializers.SerializerMethodField()
    documents_status = serializers.SerializerMethodField()
    categories_status = serializers.SerializerMethodField()

    class Meta:
        from .models import VendorStore
        model = VendorStore
        fields = [
            "id",
            "company_id",
            "company_name",
            "company_slug",
            "store_name",
            "store_slug",
            "tagline",
            "description",
            "logo_url",
            "banner_url",
            "fssai_license_number",
            "gst_number",
            "store_address",
            "is_accepting_orders",
            "is_company_active",
            "owner",
            "onboarding_data",
            "registration_status",
            "documents_status",
            "categories_status",
            "created_at",
            "updated_at",
        ]

    def get_owner(self, obj):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.filter(company=obj.company).order_by("id").first()
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "mobile_number": user.mobile_number or getattr(user, "phone", ""),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_active": user.is_active,
            "role": getattr(user, "role", "manager"),
        }

    def get_onboarding_data(self, obj):
        return obj.onboarding or {
            "status": "not_started",
            "step": 1,
            "draft": {},
            "categories": [],
            "documents": {},
            "correction_notes": "",
            "rejection_reason": "",
        }

    def get_registration_status(self, obj):
        ob = obj.onboarding or {}
        return ob.get("status", "not_started")

    def get_documents_status(self, obj):
        ob = obj.onboarding or {}
        return ob.get("documents", {})

    def get_categories_status(self, obj):
        ob = obj.onboarding or {}
        return ob.get("categories", [])


class VendorDealSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="inventory_item.display_name", read_only=True)
    unit = serializers.CharField(source="inventory_item.unit", read_only=True)
    discount_percent = serializers.IntegerField(read_only=True)

    class Meta:
        from .models import VendorDeal
        model = VendorDeal
        fields = [
            "id",
            "company",
            "inventory_item",
            "item_name",
            "unit",
            "deal_type",
            "original_price",
            "deal_price",
            "discount_percent",
            "deal_start_at",
            "deal_end_at",
            "badge_text",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "discount_percent", "created_at", "updated_at"]


class CatalogCategoryAdminSerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()
    inventory_items_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    subcategories_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    parent_details = serializers.SerializerMethodField()

    class Meta:
        from service_requests.models import CatalogCategory
        model = CatalogCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "jobs_count_str",
            "rating",
            "is_active",
            "sort_order",
            "parent",
            "parent_id",
            "parent_name",
            "parent_details",
            "children_count",
            "subcategories_count",
            "level",
            "depth",
            "ancestors",
            "services_count",
            "inventory_items_count",
        ]
        read_only_fields = [
            "id",
            "parent_name",
            "parent_details",
            "children_count",
            "subcategories_count",
            "level",
            "depth",
            "ancestors",
            "services_count",
            "inventory_items_count",
        ]

    def get_services_count(self, obj):
        try:
            return obj.services.count()
        except Exception:
            return 0

    def get_inventory_items_count(self, obj):
        try:
            from workforce_api.models import InventoryItem
            return InventoryItem.objects.filter(catalogue_category_id=obj.id).count()
        except Exception:
            return 0

    def get_children_count(self, obj):
        try:
            return obj.children.count()
        except Exception:
            return 0

    def get_subcategories_count(self, obj):
        return self.get_children_count(obj)

    def get_level(self, obj):
        depth = 0
        curr = getattr(obj, "parent", None)
        visited = {obj.id}
        while curr and getattr(curr, "id", None) not in visited:
            depth += 1
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)
        return depth

    def get_depth(self, obj):
        return self.get_level(obj)

    def get_ancestors(self, obj):
        ancestors_list = []
        curr = getattr(obj, "parent", None)
        visited = {obj.id}
        while curr and getattr(curr, "id", None) not in visited:
            ancestors_list.append({
                "id": curr.id,
                "name": curr.name,
                "slug": curr.slug,
                "is_active": getattr(curr, "is_active", True),
            })
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)
        ancestors_list.reverse()
        return ancestors_list

    def get_parent_name(self, obj):
        parent = getattr(obj, "parent", None)
        return parent.name if parent else None

    def get_parent_details(self, obj):
        parent = getattr(obj, "parent", None)
        if not parent:
            return None
        return {
            "id": parent.id,
            "name": parent.name,
            "slug": parent.slug,
            "is_active": getattr(parent, "is_active", True),
        }

    def validate(self, attrs):
        parent = attrs.get("parent")
        instance = getattr(self, "instance", None)

        if instance and parent:
            if parent.id == instance.id:
                raise serializers.ValidationError({
                    "parent": "A category cannot be its own parent category."
                })

            # Check circular dependency (is instance an ancestor of parent?)
            curr = parent
            visited = {instance.id}
            while curr:
                if curr.id in visited:
                    raise serializers.ValidationError({
                        "parent": f"Circular reference detected: '{parent.name}' is a child or descendant of '{instance.name}'."
                    })
                visited.add(curr.id)
                curr = getattr(curr, "parent", None)

        return attrs


class CatalogCategoryTreeSerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()
    inventory_items_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        from service_requests.models import CatalogCategory
        model = CatalogCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "is_active",
            "sort_order",
            "parent_id",
            "level",
            "children_count",
            "services_count",
            "inventory_items_count",
            "children",
        ]

    def get_services_count(self, obj):
        try:
            return obj.services.count()
        except Exception:
            return 0

    def get_inventory_items_count(self, obj):
        try:
            from workforce_api.models import InventoryItem
            return InventoryItem.objects.filter(catalogue_category_id=obj.id).count()
        except Exception:
            return 0

    def get_children_count(self, obj):
        try:
            return obj.children.count()
        except Exception:
            return 0

    def get_level(self, obj):
        depth = 0
        curr = getattr(obj, "parent", None)
        visited = {obj.id}
        while curr and getattr(curr, "id", None) not in visited:
            depth += 1
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)
        return depth

    def get_children(self, obj):
        active_only = self.context.get("active_only", False)
        qs = obj.children.all()
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "id")
        return CatalogCategoryTreeSerializer(qs, many=True, context=self.context).data


class SellerHubCategoryAdminSerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()
    products_count = serializers.SerializerMethodField()
    inventory_items_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    subcategories_count = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()
    depth = serializers.SerializerMethodField()
    ancestors = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()
    parent_details = serializers.SerializerMethodField()

    class Meta:
        from workforce_api.models import SellerHubCategory
        model = SellerHubCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "is_active",
            "sort_order",
            "parent",
            "parent_id",
            "parent_name",
            "parent_details",
            "children_count",
            "subcategories_count",
            "level",
            "depth",
            "ancestors",
            "products_count",
            "services_count",
            "inventory_items_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "parent_name",
            "parent_details",
            "children_count",
            "subcategories_count",
            "level",
            "depth",
            "ancestors",
            "products_count",
            "services_count",
            "inventory_items_count",
            "created_at",
            "updated_at",
        ]

    def get_services_count(self, obj):
        return 0

    def get_products_count(self, obj):
        try:
            return obj.products.count()
        except Exception:
            return 0

    def get_inventory_items_count(self, obj):
        try:
            from workforce_api.models import InventoryItem
            return InventoryItem.objects.filter(catalogue_category_id=obj.id).count()
        except Exception:
            return 0

    def get_children_count(self, obj):
        try:
            return obj.children.count()
        except Exception:
            return 0

    def get_subcategories_count(self, obj):
        return self.get_children_count(obj)

    def get_level(self, obj):
        depth = 0
        curr = getattr(obj, "parent", None)
        visited = {obj.id}
        while curr and getattr(curr, "id", None) not in visited:
            depth += 1
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)
        return depth

    def get_depth(self, obj):
        return self.get_level(obj)

    def get_ancestors(self, obj):
        ancestors_list = []
        curr = getattr(obj, "parent", None)
        visited = {obj.id}
        while curr and getattr(curr, "id", None) not in visited:
            ancestors_list.append({
                "id": curr.id,
                "name": curr.name,
                "slug": curr.slug,
                "is_active": getattr(curr, "is_active", True),
            })
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)
        ancestors_list.reverse()
        return ancestors_list

    def get_parent_name(self, obj):
        parent = getattr(obj, "parent", None)
        return parent.name if parent else None

    def get_parent_details(self, obj):
        parent = getattr(obj, "parent", None)
        if not parent:
            return None
        return {
            "id": parent.id,
            "name": parent.name,
            "slug": parent.slug,
            "is_active": getattr(parent, "is_active", True),
        }

    def validate(self, attrs):
        parent = attrs.get("parent")
        instance = getattr(self, "instance", None)

        if instance and parent:
            if parent.id == instance.id:
                raise serializers.ValidationError({
                    "parent": "A category cannot be its own parent category."
                })

            # Check circular dependency (is instance an ancestor of parent?)
            curr = parent
            visited = {instance.id}
            while curr:
                if curr.id in visited:
                    raise serializers.ValidationError({
                        "parent": f"Circular reference detected: '{parent.name}' is a child or descendant of '{instance.name}'."
                    })
                visited.add(curr.id)
                curr = getattr(curr, "parent", None)

        return attrs


class SellerHubCategoryTreeSerializer(serializers.ModelSerializer):
    services_count = serializers.SerializerMethodField()
    inventory_items_count = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    level = serializers.SerializerMethodField()

    class Meta:
        from workforce_api.models import SellerHubCategory
        model = SellerHubCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "is_active",
            "sort_order",
            "parent_id",
            "level",
            "children_count",
            "services_count",
            "inventory_items_count",
            "children",
        ]

    def get_services_count(self, obj):
        return 0

    def get_inventory_items_count(self, obj):
        try:
            from workforce_api.models import InventoryItem
            return InventoryItem.objects.filter(catalogue_category_id=obj.id).count()
        except Exception:
            return 0

    def get_children_count(self, obj):
        try:
            return obj.children.count()
        except Exception:
            return 0

    def get_level(self, obj):
        depth = 0
        curr = getattr(obj, "parent", None)
        visited = {obj.id}
        while curr and getattr(curr, "id", None) not in visited:
            depth += 1
            visited.add(curr.id)
            curr = getattr(curr, "parent", None)
        return depth

    def get_children(self, obj):
        active_only = self.context.get("active_only", False)
        qs = obj.children.all()
        if active_only:
            qs = qs.filter(is_active=True)
        qs = qs.order_by("sort_order", "id")
        return SellerHubCategoryTreeSerializer(qs, many=True, context=self.context).data


class SellerCatalogCategoryItemSerializer(serializers.ModelSerializer):
    has_children = serializers.SerializerMethodField()
    is_leaf = serializers.SerializerMethodField()
    path = serializers.SerializerMethodField()
    path_string = serializers.SerializerMethodField()

    class Meta:
        from workforce_api.models import SellerHubCategory
        model = SellerHubCategory
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "icon",
            "image",
            "parent_id",
            "sort_order",
            "is_active",
            "has_children",
            "is_leaf",
            "path",
            "path_string",
        ]

    def get_has_children(self, obj):
        if hasattr(obj, "_has_children"):
            return obj._has_children
        return obj.children.filter(is_active=True).exists()

    def get_is_leaf(self, obj):
        return not self.get_has_children(obj)

    def get_path(self, obj):
        if hasattr(obj, "_path"):
            return obj._path
        ancestors = []
        curr = obj
        visited = set()
        while curr and curr.id not in visited:
            visited.add(curr.id)
            ancestors.append({
                "id": curr.id,
                "name": curr.name,
                "slug": curr.slug,
            })
            curr = curr.parent
        ancestors.reverse()
        return ancestors

    def get_path_string(self, obj):
        if hasattr(obj, "_path_string"):
            return obj._path_string
        path_list = self.get_path(obj)
        return " > ".join(a["name"] for a in path_list)


class VendorCouponSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)

    class Meta:
        from .models import VendorCoupon
        model = VendorCoupon
        fields = [
            "id",
            "company",
            "company_name",
            "code",
            "description",
            "discount_type",
            "discount_value",
            "min_order_amount",
            "max_discount_amount",
            "usage_limit_total",
            "usage_limit_per_user",
            "times_used",
            "valid_from",
            "valid_until",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "company_name", "times_used", "created_at", "updated_at"]

    def validate_code(self, value):
        val = str(value).strip().upper()
        if not val:
            raise serializers.ValidationError("Coupon code cannot be empty.")
        return val

    def validate(self, attrs):
        v_from = attrs.get("valid_from") or (self.instance.valid_from if self.instance else None)
        v_until = attrs.get("valid_until") or (self.instance.valid_until if self.instance else None)
        if v_from and v_until and v_until < v_from:
            raise serializers.ValidationError({"valid_until": "End validity date must be after the start date."})
        return attrs


class GroceryOrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import GroceryOrderItem
        model = GroceryOrderItem
        fields = [
            "id",
            "inventory_item",
            "product_name_snapshot",
            "sku_snapshot",
            "unit_snapshot",
            "quantity",
            "mrp_snapshot",
            "regular_price_snapshot",
            "deal_price_snapshot",
            "final_unit_price",
            "total_price",
        ]
        read_only_fields = ["id"]


class GroceryDeliverySerializer(serializers.ModelSerializer):
    class Meta:
        from .models import GroceryDelivery
        model = GroceryDelivery
        fields = [
            "id",
            "fulfillment_method",
            "status",
            "rider_name",
            "rider_phone",
            "delivery_otp",
            "delivered_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GroceryOrderSerializer(serializers.ModelSerializer):
    items = GroceryOrderItemSerializer(many=True, read_only=True)
    delivery = GroceryDeliverySerializer(read_only=True)
    vendor_store_name = serializers.CharField(source="vendor_store.store_name", read_only=True)

    class Meta:
        from .models import GroceryOrder
        model = GroceryOrder
        fields = [
            "id",
            "order_number",
            "customer_id",
            "customer_name",
            "customer_phone",
            "delivery_address",
            "delivery_latitude",
            "delivery_longitude",
            "vendor_store",
            "vendor_store_name",
            "status",
            "payment_method",
            "payment_status",
            "subtotal",
            "deal_discount",
            "vendor_coupon_discount",
            "platform_coupon_discount",
            "delivery_fee",
            "tax",
            "total_amount",
            "applied_coupon_code",
            "delivery_notes",
            "placed_at",
            "accepted_at",
            "packed_at",
            "out_for_delivery_at",
            "delivered_at",
            "cancelled_at",
            "rejection_reason",
            "created_at",
            "updated_at",
            "items",
            "delivery",
        ]
        read_only_fields = ["id", "order_number", "placed_at", "created_at", "updated_at"]


class InventoryTransactionSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="inventory_item.display_name", read_only=True)
    unit = serializers.CharField(source="inventory_item.unit", read_only=True)

    class Meta:
        from .models import InventoryTransaction
        model = InventoryTransaction
        fields = [
            "id",
            "inventory_item",
            "product_name",
            "unit",
            "transaction_type",
            "quantity",
            "balance_after",
            "reference_id",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VendorSettlementSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="vendor_store.store_name", read_only=True)

    class Meta:
        from .models import VendorSettlement
        model = VendorSettlement
        fields = [
            "id",
            "settlement_number",
            "vendor_store",
            "store_name",
            "period_start",
            "period_end",
            "gross_sales",
            "platform_commission",
            "vendor_funded_discounts",
            "net_payable",
            "status",
            "settled_at",
            "created_at",
        ]
        read_only_fields = ["id", "settlement_number", "created_at"]


class FinancialLedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        from .models import FinancialLedgerEntry
        model = FinancialLedgerEntry
        fields = [
            "id",
            "entry_type",
            "category",
            "amount",
            "balance_after",
            "order",
            "settlement",
            "description",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class VendorStoreReviewSerializer(serializers.ModelSerializer):
    store_name = serializers.CharField(source="vendor_store.store_name", read_only=True)

    class Meta:
        from .models import VendorStoreReview
        model = VendorStoreReview
        fields = [
            "id",
            "vendor_store",
            "store_name",
            "customer_id",
            "customer_name",
            "order",
            "rating",
            "review_text",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ═══════════════════════════════════════════════════════════════════════════════
# SELLER HUB PRODUCT CATALOG & UPLOAD SERIALIZERS (Phase 2 Foundation)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import SellerProductImage
        model = SellerProductImage
        fields = [
            "id",
            "product",
            "image_url",
            "is_primary",
            "sort_order",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class SellerProductAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerProductAuditLog
        model = SellerProductAuditLog
        fields = [
            "id",
            "product",
            "action",
            "from_status",
            "to_status",
            "actor",
            "actor_name",
            "notes",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System Engine"
        name = f"{getattr(obj.actor, 'first_name', '')} {getattr(obj.actor, 'last_name', '')}".strip()
        return name or getattr(obj.actor, "username", "Reviewer")


class SellerCatalogUploadBatchSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerCatalogUploadBatch
        model = SellerCatalogUploadBatch
        fields = [
            "id",
            "company",
            "company_name",
            "uploaded_by",
            "uploaded_by_name",
            "file_name",
            "total_rows",
            "imported_rows",
            "failed_rows",
            "status",
            "error_report",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_uploaded_by_name(self, obj):
        if not obj.uploaded_by:
            return "System / Bulk API"
        name = f"{getattr(obj.uploaded_by, 'first_name', '')} {getattr(obj.uploaded_by, 'last_name', '')}".strip()
        return name or getattr(obj.uploaded_by, "username", "Seller")


class SellerLeafCategorySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    slug = serializers.CharField()
    path = serializers.CharField()
    path_string = serializers.SerializerMethodField()
    parent_name = serializers.CharField(allow_null=True)

    def get_path_string(self, obj):
        if isinstance(obj, dict):
            return obj.get("path_string") or obj.get("path", "")
        return getattr(obj, "path_string", getattr(obj, "path", ""))


class SellerProductListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_path = serializers.SerializerMethodField()
    path_string = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    primary_image = serializers.SerializerMethodField()
    images_count = serializers.SerializerMethodField()
    reviewed_by_name = serializers.SerializerMethodField()
    rejection_reason = serializers.CharField(source="admin_review_note", read_only=True)

    class Meta:
        from .models import SellerProduct
        model = SellerProduct
        fields = [
            "id",
            "company",
            "company_name",
            "category",
            "category_name",
            "category_slug",
            "category_path",
            "path_string",
            "title",
            "description",
            "brand",
            "sku",
            "barcode",
            "unit",
            "pack_size",
            "mrp",
            "selling_price",
            "tax_rate",
            "hsn_code",
            "storage_info",
            "expiry_info",
            "status",
            "admin_review_note",
            "rejection_reason",
            "primary_image",
            "images_count",
            "reviewed_by_name",
            "submitted_at",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "created_at", "updated_at"]

    def get_category_path(self, obj):
        if not obj.category:
            return ""
        path = [obj.category.name]
        curr = obj.category.parent
        while curr:
            path.insert(0, curr.name)
            curr = curr.parent
        return " > ".join(path)

    def get_path_string(self, obj):
        return self.get_category_path(obj)

    def get_primary_image(self, obj):
        images_list = getattr(obj, "_prefetched_images", None)
        if images_list is not None:
            primary = next((img.image_url for img in images_list if img.is_primary), None)
            if primary:
                return primary
            return images_list[0].image_url if images_list else ""
        img = obj.images.filter(is_primary=True).first() or obj.images.first()
        return img.image_url if img else ""

    def get_images_count(self, obj):
        images_list = getattr(obj, "_prefetched_images", None)
        if images_list is not None:
            return len(images_list)
        return obj.images.count()

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return None
        name = f"{getattr(obj.reviewed_by, 'first_name', '')} {getattr(obj.reviewed_by, 'last_name', '')}".strip()
        return name or getattr(obj.reviewed_by, "username", "Reviewer")


class SellerProductDetailSerializer(serializers.ModelSerializer):
    images = SellerProductImageSerializer(many=True, read_only=True)
    audit_logs = SellerProductAuditLogSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_path = serializers.SerializerMethodField()
    path_string = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    rejection_reason = serializers.CharField(source="admin_review_note", read_only=True)

    class Meta:
        from .models import SellerProduct
        model = SellerProduct
        fields = [
            "id",
            "company",
            "company_name",
            "category",
            "category_name",
            "category_slug",
            "category_path",
            "path_string",
            "title",
            "description",
            "brand",
            "sku",
            "barcode",
            "unit",
            "pack_size",
            "mrp",
            "selling_price",
            "tax_rate",
            "hsn_code",
            "storage_info",
            "expiry_info",
            "status",
            "admin_review_note",
            "rejection_reason",
            "reviewed_by_name",
            "submitted_at",
            "reviewed_at",
            "upload_batch",
            "images",
            "audit_logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "company", "created_at", "updated_at"]

    def get_category_path(self, obj):
        if not obj.category:
            return ""
        path = [obj.category.name]
        curr = obj.category.parent
        while curr:
            path.insert(0, curr.name)
            curr = curr.parent
        return " > ".join(path)

    def get_path_string(self, obj):
        return self.get_category_path(obj)

    def get_reviewed_by_name(self, obj):
        if not obj.reviewed_by:
            return None
        name = f"{getattr(obj.reviewed_by, 'first_name', '')} {getattr(obj.reviewed_by, 'last_name', '')}".strip()
        return name or getattr(obj.reviewed_by, "username", "Reviewer")


def is_category_leaf(category):
    """
    Unified Leaf Rule: A category is a leaf if it has no ACTIVE child categories.
    Categories with only inactive children are considered leaves.
    """
    if not category:
        return True
    if hasattr(category, "children"):
        return not category.children.filter(is_active=True).exists()
    return True


def validate_product_category_is_leaf(category, current_category=None):
    """
    Shared validator for product category assignment across single create/update,
    bulk/CSV uploads, and administrative updates.
    
    Rules:
    - Must exist.
    - Category itself must be active.
    - Entire ancestor parent chain must be active.
    - Category must be a leaf (no ACTIVE subcategories).
    - If current_category is supplied and matches category, legacy products are
      permitted to bypass validation when category is unchanged.
      
    Returns: (is_valid: bool, error_message: str or None, error_code: str or None)
    """
    if not category:
        return False, "Seller Hub category is required.", "REQUIRED"

    cat_id = getattr(category, "id", None)
    curr_cat_id = getattr(current_category, "id", None) if current_category else None

    # Legacy exemption when category is unchanged
    if curr_cat_id is not None and cat_id is not None and curr_cat_id == cat_id:
        return True, None, None

    if not getattr(category, "is_active", True):
        return False, f"Category '{getattr(category, 'name', '')}' is currently inactive.", "CATEGORY_INACTIVE"

    # Ancestor chain check
    curr = getattr(category, "parent", None)
    visited = {category.id} if hasattr(category, "id") else set()
    while curr:
        if curr.id in visited:
            break
        if not getattr(curr, "is_active", True):
            return False, f"Parent category '{curr.name}' is inactive. All parent categories must be active.", "CATEGORY_INACTIVE"
        visited.add(curr.id)
        curr = getattr(curr, "parent", None)

    # Leaf check: category must not have ACTIVE child categories
    if not is_category_leaf(category):
        return False, f"Category '{category.name}' is a parent category with active subcategories. Products must only be assigned to leaf categories.", "CATEGORY_NOT_LEAF"

    return True, None, None


class SellerProductCreateUpdateSerializer(serializers.ModelSerializer):
    images = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        write_only=True,
    )

    class Meta:
        from .models import SellerProduct
        model = SellerProduct
        fields = [
            "id",
            "category",
            "title",
            "description",
            "brand",
            "sku",
            "barcode",
            "unit",
            "pack_size",
            "mrp",
            "selling_price",
            "tax_rate",
            "hsn_code",
            "storage_info",
            "expiry_info",
            "status",
            "images",
        ]

    def validate_category(self, value):
        current_cat = self.instance.category if self.instance else None
        is_valid, err_msg, err_code = validate_product_category_is_leaf(value, current_category=current_cat)
        if not is_valid:
            raise serializers.ValidationError(err_msg, code=err_code)
        return value

    def validate(self, data):
        mrp = data.get("mrp")
        selling_price = data.get("selling_price")

        # Fallback to instance values if partial update
        if mrp is None and self.instance:
            mrp = self.instance.mrp
        if selling_price is None and self.instance:
            selling_price = self.instance.selling_price

        if mrp is not None and mrp <= 0:
            raise serializers.ValidationError({"mrp": "MRP must be greater than zero."})

        if selling_price is not None and selling_price <= 0:
            raise serializers.ValidationError({"selling_price": "Selling price must be greater than zero."})

        if mrp is not None and selling_price is not None and selling_price > mrp:
            raise serializers.ValidationError(
                {"selling_price": f"Selling price (₹{selling_price}) cannot exceed MRP (₹{mrp})."}
            )

        tax_rate = data.get("tax_rate")
        if tax_rate is not None and tax_rate < 0:
            raise serializers.ValidationError({"tax_rate": "Tax rate cannot be negative."})

        # SKU uniqueness per company check
        sku = data.get("sku")
        company = self.context.get("company")
        if sku and company:
            from .models import SellerProduct
            qs = SellerProduct.objects.filter(company=company, sku=sku)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError(
                    {"sku": f"A product with SKU '{sku}' already exists in your store catalog."}
                )

        return data


class AdminSellerApprovalListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    seller_id = serializers.IntegerField(source="id", read_only=True)
    name = serializers.CharField(source="company_name")
    company_name = serializers.CharField()
    slug = serializers.CharField()
    business_type = serializers.CharField()
    pending_count = serializers.IntegerField(default=0)
    approved_count = serializers.IntegerField(default=0)
    rejected_count = serializers.IntegerField(default=0)
    total_count = serializers.IntegerField(default=0)
    latest_submitted_at = serializers.DateTimeField(allow_null=True)


# ═══════════════════════════════════════════════════════════════════════════════
# SELLER HUB INVENTORY MANAGEMENT SERIALIZERS (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerInventoryMovementSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()
    batch_number = serializers.CharField(source="batch.batch_number", read_only=True, default=None)
    movement_type_display = serializers.CharField(source="get_movement_type_display", read_only=True)

    class Meta:
        from .models import SellerInventoryMovement
        model = SellerInventoryMovement
        fields = [
            "id",
            "inventory",
            "batch",
            "batch_number",
            "movement_type",
            "movement_type_display",
            "quantity_change",
            "balance_before",
            "balance_after",
            "reason",
            "reference_id",
            "actor",
            "actor_name",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System / Auto"
        name = f"{getattr(obj.actor, 'first_name', '')} {getattr(obj.actor, 'last_name', '')}".strip()
        return name or getattr(obj.actor, "username", "User")


class SellerInventoryBatchSerializer(serializers.ModelSerializer):
    days_until_expiry = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerInventoryBatch
        model = SellerInventoryBatch
        fields = [
            "id",
            "inventory",
            "batch_number",
            "received_date",
            "expiry_date",
            "initial_quantity",
            "current_quantity",
            "cost_price",
            "status",
            "days_until_expiry",
            "created_at",
            "updated_at",
        ]

    def get_days_until_expiry(self, obj):
        if not obj.expiry_date:
            return None
        from django.utils import timezone
        diff = obj.expiry_date - timezone.now().date()
        return diff.days


class SellerInventoryListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_sku = serializers.CharField(source="product.sku", read_only=True)
    product_brand = serializers.CharField(source="product.brand", read_only=True)
    product_barcode = serializers.CharField(source="product.barcode", read_only=True)
    product_unit = serializers.CharField(source="product.unit", read_only=True)
    product_pack_size = serializers.CharField(source="product.pack_size", read_only=True)
    product_selling_price = serializers.DecimalField(source="product.selling_price", max_digits=10, decimal_places=2, read_only=True)
    product_mrp = serializers.DecimalField(source="product.mrp", max_digits=10, decimal_places=2, read_only=True)
    product_status = serializers.CharField(source="product.status", read_only=True)
    product_category_name = serializers.CharField(source="product.category.name", read_only=True)
    product_category_path = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    available_qty = serializers.DecimalField(max_digits=12, decimal_places=3, read_only=True)
    stock_status = serializers.CharField(read_only=True)
    batches_count = serializers.SerializerMethodField()
    has_expiring_batches = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerInventory
        model = SellerInventory
        fields = [
            "id",
            "company",
            "company_name",
            "product",
            "product_title",
            "product_sku",
            "product_brand",
            "product_barcode",
            "product_unit",
            "product_pack_size",
            "product_selling_price",
            "product_mrp",
            "product_status",
            "product_category_name",
            "product_category_path",
            "product_image",
            "on_hand_qty",
            "reserved_qty",
            "available_qty",
            "low_stock_threshold",
            "reorder_level",
            "stock_status",
            "batches_count",
            "has_expiring_batches",
            "created_at",
            "updated_at",
        ]

    def get_product_category_path(self, obj):
        cat = obj.product.category
        if not cat:
            return ""
        path = [cat.name]
        curr = cat.parent
        while curr:
            path.insert(0, curr.name)
            curr = curr.parent
        return " > ".join(path)

    def get_product_image(self, obj):
        img = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        return img.image_url if img else None

    def get_batches_count(self, obj):
        return obj.batches.filter(current_quantity__gt=0).count()

    def get_has_expiring_batches(self, obj):
        from django.utils import timezone
        thirty_days = timezone.now().date() + timezone.timedelta(days=30)
        return obj.batches.filter(current_quantity__gt=0, expiry_date__lte=thirty_days).exists()


class SellerInventoryDetailSerializer(SellerInventoryListSerializer):
    batches = SellerInventoryBatchSerializer(many=True, read_only=True)
    recent_movements = serializers.SerializerMethodField()

    class Meta(SellerInventoryListSerializer.Meta):
        fields = SellerInventoryListSerializer.Meta.fields + [
            "batches",
            "recent_movements",
        ]

    def get_recent_movements(self, obj):
        qs = obj.movements.select_related("actor", "batch").order_by("-created_at")[:15]
        return SellerInventoryMovementSerializer(qs, many=True).data


class SellerInventoryAdjustSerializer(serializers.Serializer):
    movement_type = serializers.ChoiceField(
        choices=[
            ("OPENING_STOCK", "Opening Stock"),
            ("STOCK_IN", "Stock In"),
            ("ADJUSTMENT_INCREASE", "Stock Adjustment (Increase)"),
            ("ADJUSTMENT_DECREASE", "Stock Adjustment (Decrease)"),
            ("DAMAGE", "Damaged / Broken Stock"),
            ("EXPIRED", "Expired Stock Write-off"),
        ]
    )
    quantity = serializers.DecimalField(max_digits=12, decimal_places=3, min_value=Decimal("0.001"))
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    reference_id = serializers.CharField(max_length=100, required=False, allow_blank=True)
    # Optional Batch Details
    batch_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    expiry_date = serializers.DateField(required=False, allow_null=True)
    cost_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)

    def validate(self, data):
        movement_type = data.get("movement_type")
        reason = (data.get("reason") or "").strip()

        # Rule: Decreases, Damages, Expiries and Adjustments require a mandatory reason
        if movement_type in ("ADJUSTMENT_DECREASE", "DAMAGE", "EXPIRED", "ADJUSTMENT_INCREASE") and not reason:
            raise serializers.ValidationError(
                {"reason": f"A reason is mandatory when recording '{movement_type}'."}
            )

        return data


# ═══════════════════════════════════════════════════════════════════════════════
# 7. SELLER HUB ORDERS & FULFILMENT SERIALIZERS (Phase 4)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerOrderItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerOrderItem
        model = SellerOrderItem
        fields = [
            "id",
            "order",
            "product",
            "product_title",
            "sku",
            "unit",
            "pack_size",
            "ordered_quantity",
            "fulfilled_quantity",
            "unit_price",
            "line_total",
            "batch",
            "is_picked",
            "is_packed",
            "notes",
            "product_image",
            "available_stock",
        ]

    def get_product_image(self, obj):
        if not obj.product:
            return None
        img = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        return img.image_url if img else None

    def get_available_stock(self, obj):
        if not obj.product or not hasattr(obj.product, "inventory"):
            return "0.000"
        return str(obj.product.inventory.available_qty)


class SellerOrderAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerOrderAuditLog
        model = SellerOrderAuditLog
        fields = [
            "id",
            "order",
            "from_status",
            "to_status",
            "action",
            "actor",
            "actor_name",
            "notes",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System"
        name = f"{obj.actor.first_name} {obj.actor.last_name}".strip()
        return name or obj.actor.username


class SellerOrderListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    items_count = serializers.SerializerMethodField()
    items_summary = serializers.SerializerMethodField()
    handling_technician_id = serializers.IntegerField(source="handling_technician.id", read_only=True)
    handling_technician_name = serializers.SerializerMethodField()
    handling_technician_phone = serializers.SerializerMethodField()
    dispatch_job_id = serializers.IntegerField(source="dispatch_job.id", read_only=True)
    handover_otp_pending = serializers.SerializerMethodField()
    delivery_otp_pending = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerOrder
        model = SellerOrder
        fields = [
            "id",
            "source_order_id",
            "order_number",
            "company",
            "company_name",
            "customer_name",
            "customer_phone",
            "delivery_address",
            "fulfillment_type",
            "delivery_slot",
            "payment_method",
            "payment_status",
            "total_amount",
            "currency",
            "status",
            "dispatch_job_id",
            "handling_technician_id",
            "handling_technician_name",
            "handling_technician_phone",
            "handover_otp_pending",
            "delivery_otp_pending",
            "inventory_deducted",
            "items_count",
            "items_summary",
            "seller_notes",
            "cancellation_reason",
            "accepted_at",
            "picking_at",
            "packed_at",
            "ready_at",
            "assigned_at",
            "handed_over_at",
            "delivered_at",
            "cancelled_at",
            "created_at",
            "updated_at",
        ]

    def get_handling_technician_name(self, obj):
        if not obj.handling_technician:
            return None
        tech = obj.handling_technician
        if getattr(tech, "user", None):
            return tech.user.get_full_name() or tech.user.username
        return getattr(tech, "name", f"Rider #{tech.id}")

    def get_handling_technician_phone(self, obj):
        if not obj.handling_technician:
            return None
        tech = obj.handling_technician
        user = getattr(tech, "user", None)
        return getattr(user, "mobile_number", "") or getattr(user, "phone", "") or getattr(tech, "phone", "") or getattr(user, "username", "")

    def get_handover_otp_pending(self, obj):
        return bool(obj.handover_otp_hash and obj.handover_otp_used_at is None)

    def get_delivery_otp_pending(self, obj):
        return bool(obj.delivery_otp_hash and obj.delivery_otp_used_at is None)

    def get_items_count(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "items" in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache["items"])
        return obj.items.count()

    def get_items_summary(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "items" in obj._prefetched_objects_cache:
            items = list(obj._prefetched_objects_cache["items"])[:3]
            count = len(obj._prefetched_objects_cache["items"])
        else:
            items = list(obj.items.all()[:3])
            count = obj.items.count()
        summary = [f"{item.product_title} (x{item.ordered_quantity})" for item in items]
        if count > 3:
            summary.append(f"+{count - 3} more")
        return ", ".join(summary)


class SellerOrderDetailSerializer(SellerOrderListSerializer):
    items = SellerOrderItemSerializer(many=True, read_only=True)
    audit_logs = SellerOrderAuditLogSerializer(many=True, read_only=True)
    pickup_otp = serializers.SerializerMethodField()

    class Meta(SellerOrderListSerializer.Meta):
        fields = SellerOrderListSerializer.Meta.fields + [
            "items",
            "audit_logs",
            "handover_ref",
            "pickup_otp",
        ]

    def get_pickup_otp(self, obj):
        # Surface recent pickup OTP notification text if merchant is viewing
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        # Only show to merchant belonging to order company or admin
        from .models import WorkforceNotification
        if obj.handover_otp_hash and obj.handover_otp_used_at is None:
            notif = WorkforceNotification.objects.filter(
                notification_type="ORDER_PICKUP_OTP",
                related_object_id=str(obj.id),
            ).order_by("-created_at").first()
            if notif and "Pickup Handover OTP is " in notif.message:
                try:
                    return notif.message.split("Pickup Handover OTP is ")[1].split(".")[0].strip()
                except Exception:
                    pass
        return None


class SellerOrderStatusTransitionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            ("accept", "Accept Order"),
            ("start_picking", "Start Picking"),
            ("mark_packed", "Mark as Packed"),
            ("mark_ready", "Mark Ready for Pickup"),
            ("handover", "Handover to Courier/Customer"),
            ("deliver", "Mark as Delivered"),
            ("cancel", "Cancel Order"),
        ]
    )
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    cancellation_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    handover_ref = serializers.CharField(max_length=100, required=False, allow_blank=True)

    def validate(self, data):
        action = data.get("action")
        if action == "cancel":
            reason = (data.get("cancellation_reason") or "").strip()
            if not reason:
                raise serializers.ValidationError(
                    {"cancellation_reason": "A cancellation reason is required to cancel an order."}
                )
        return data


class SellerOrderItemPickSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    is_picked = serializers.BooleanField(required=False)
    is_packed = serializers.BooleanField(required=False)
    fulfilled_quantity = serializers.DecimalField(
        max_digits=12,
        decimal_places=3,
        min_value=Decimal("0.000"),
        required=False,
    )
    batch_id = serializers.IntegerField(required=False, allow_null=True)
    notes = serializers.CharField(max_length=255, required=False, allow_blank=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. SELLER HUB RETURNS & REVERSE LOGISTICS SERIALIZERS (Phase 5)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerReturnItemSerializer(serializers.ModelSerializer):
    product_image = serializers.SerializerMethodField()
    available_stock = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerReturnItem
        model = SellerReturnItem
        fields = [
            "id",
            "return_case",
            "order_item",
            "product",
            "product_title",
            "sku",
            "unit",
            "pack_size",
            "returned_quantity",
            "restocked_quantity",
            "scrapped_quantity",
            "item_condition",
            "qc_result",
            "batch",
            "notes",
            "product_image",
            "available_stock",
        ]

    def get_product_image(self, obj):
        if not obj.product:
            return None
        img = obj.product.images.filter(is_primary=True).first() or obj.product.images.first()
        return img.image_url if img else None

    def get_available_stock(self, obj):
        if not obj.product or not hasattr(obj.product, "inventory"):
            return "0.000"
        return str(obj.product.inventory.available_qty)


class SellerReturnAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerReturnAuditLog
        model = SellerReturnAuditLog
        fields = [
            "id",
            "return_case",
            "from_status",
            "to_status",
            "action",
            "actor",
            "actor_name",
            "notes",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System"
        name = f"{obj.actor.first_name} {obj.actor.last_name}".strip()
        return name or obj.actor.username


class SellerReturnListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    source_order_id = serializers.CharField(source="order.source_order_id", read_only=True)
    items_count = serializers.SerializerMethodField()
    items_summary = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerReturn
        model = SellerReturn
        fields = [
            "id",
            "source_return_id",
            "return_number",
            "order",
            "order_number",
            "source_order_id",
            "company",
            "company_name",
            "customer_name",
            "customer_phone",
            "customer_address",
            "reason",
            "status",
            "seller_decision",
            "quality_check_status",
            "restock_decision",
            "items_count",
            "items_summary",
            "created_at",
            "reviewed_at",
            "received_at",
            "inspected_at",
            "restocked_at",
            "closed_at",
            "updated_at",
        ]

    def get_items_count(self, obj):
        return obj.items.count()

    def get_items_summary(self, obj):
        items = obj.items.all()[:3]
        summary = [f"{item.product_title} (x{item.returned_quantity})" for item in items]
        if obj.items.count() > 3:
            summary.append(f"+{obj.items.count() - 3} more")
        return ", ".join(summary)


class SellerReturnDetailSerializer(SellerReturnListSerializer):
    items = SellerReturnItemSerializer(many=True, read_only=True)
    audit_logs = SellerReturnAuditLogSerializer(many=True, read_only=True)
    quality_checked_by_name = serializers.SerializerMethodField()

    class Meta(SellerReturnListSerializer.Meta):
        fields = SellerReturnListSerializer.Meta.fields + [
            "customer_notes",
            "evidence_urls",
            "seller_notes",
            "rejection_reason",
            "quality_check_notes",
            "quality_checked_by",
            "quality_checked_by_name",
            "restock_notes",
            "pickup_ref",
            "admin_resolution_notes",
            "items",
            "audit_logs",
        ]

    def get_quality_checked_by_name(self, obj):
        if not obj.quality_checked_by:
            return None
        name = f"{obj.quality_checked_by.first_name} {obj.quality_checked_by.last_name}".strip()
        return name or obj.quality_checked_by.username


class SellerReturnReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("approve", "Approve Return"),
            ("reject", "Reject Return"),
            ("escalate", "Escalate to Platform Admin"),
        ]
    )
    seller_notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    rejection_reason = serializers.CharField(max_length=500, required=False, allow_blank=True)

    def validate(self, data):
        decision = data.get("decision")
        if decision == "reject":
            reason = (data.get("rejection_reason") or "").strip()
            if not reason:
                raise serializers.ValidationError(
                    {"rejection_reason": "A rejection reason is mandatory when rejecting a return request."}
                )
        return data


class SellerReturnQualityCheckSerializer(serializers.Serializer):
    quality_check_status = serializers.ChoiceField(
        choices=[
            ("PASSED", "Passed (Fit for Restock)"),
            ("FAILED", "Failed (Damaged / Unusable)"),
            ("PARTIAL_PASS", "Partial Pass"),
        ]
    )
    quality_check_notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    # Item-level QC results
    items_qc = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of items with item_id, item_condition, qc_result, and optional notes.",
    )


class SellerReturnRestockSerializer(serializers.Serializer):
    restock_decision = serializers.ChoiceField(
        choices=[
            ("FULL_RESTOCK", "Full Restock"),
            ("PARTIAL_RESTOCK", "Partial Restock"),
            ("SCRAP_DISPOSE", "Scrap / Dispose All"),
        ]
    )
    restock_notes = serializers.CharField(max_length=500, required=False, allow_blank=True)
    # Per-item restocked vs scrapped breakdown
    items_breakdown = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of items with item_id, restocked_quantity, scrapped_quantity.",
    )


class SellerReturnIntakeSerializer(serializers.Serializer):
    source_return_id = serializers.CharField(max_length=100)
    source_order_id = serializers.CharField(max_length=100)
    reason = serializers.CharField(max_length=100, required=False, default="DAMAGED")
    customer_notes = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")
    evidence_urls = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
    )
    items = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
    )


# ==============================================================================
# PHASE 6: SELLER HUB CLAIMS SERIALIZERS
# ==============================================================================

class SellerClaimAuditLogSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerClaimAuditLog
        model = SellerClaimAuditLog
        fields = [
            "id",
            "from_status",
            "to_status",
            "action",
            "actor",
            "actor_name",
            "notes",
            "created_at",
        ]

    def get_actor_name(self, obj):
        if not obj.actor:
            return "System / Integration"
        name = f"{obj.actor.first_name} {obj.actor.last_name}".strip()
        return name or obj.actor.username


class SellerClaimListSerializer(serializers.ModelSerializer):
    company_name = serializers.CharField(source="company.company_name", read_only=True)
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    source_order_id = serializers.CharField(source="order.source_order_id", read_only=True)
    return_number = serializers.CharField(source="return_case.return_number", read_only=True)
    claim_type_display = serializers.CharField(source="get_claim_type_display", read_only=True)
    needs_seller_response = serializers.SerializerMethodField()

    class Meta:
        from .models import SellerClaim
        model = SellerClaim
        fields = [
            "id",
            "source_claim_id",
            "claim_number",
            "company",
            "company_name",
            "order",
            "order_number",
            "source_order_id",
            "return_case",
            "return_number",
            "claim_type",
            "claim_type_display",
            "description",
            "claimed_amount",
            "status",
            "seller_response",
            "seller_responded_at",
            "admin_decision",
            "admin_decided_at",
            "needs_seller_response",
            "created_at",
            "resolved_at",
            "closed_at",
            "updated_at",
        ]

    def get_needs_seller_response(self, obj):
        return obj.status == "SELLER_RESPONSE_REQUIRED"


class SellerClaimDetailSerializer(SellerClaimListSerializer):
    audit_logs = SellerClaimAuditLogSerializer(many=True, read_only=True)
    seller_responded_by_name = serializers.SerializerMethodField()
    admin_decided_by_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta(SellerClaimListSerializer.Meta):
        fields = SellerClaimListSerializer.Meta.fields + [
            "evidence_urls",
            "customer_name",
            "customer_phone",
            "seller_responded_by",
            "seller_responded_by_name",
            "admin_decision_reason",
            "admin_decided_by",
            "admin_decided_by_name",
            "created_by",
            "created_by_name",
            "audit_logs",
        ]

    def get_seller_responded_by_name(self, obj):
        if not obj.seller_responded_by:
            return None
        name = f"{obj.seller_responded_by.first_name} {obj.seller_responded_by.last_name}".strip()
        return name or obj.seller_responded_by.username

    def get_admin_decided_by_name(self, obj):
        if not obj.admin_decided_by:
            return None
        name = f"{obj.admin_decided_by.first_name} {obj.admin_decided_by.last_name}".strip()
        return name or obj.admin_decided_by.username

    def get_created_by_name(self, obj):
        if not obj.created_by:
            return "System / Customer Portal"
        name = f"{obj.created_by.first_name} {obj.created_by.last_name}".strip()
        return name or obj.created_by.username


class SellerClaimCreateSerializer(serializers.Serializer):
    order_id = serializers.IntegerField(required=False, allow_null=True)
    return_id = serializers.IntegerField(required=False, allow_null=True)
    claim_type = serializers.ChoiceField(
        choices=[
            ("DAMAGED_ITEM", "Damaged Item"),
            ("MISSING_ITEM", "Missing / Undelivered Item"),
            ("WRONG_ITEM", "Wrong Item Delivered"),
            ("QUALITY_ISSUE", "Quality / Freshness Issue"),
            ("DELIVERY_DAMAGE", "Damage During Delivery / In-Transit"),
            ("SELLER_DISPUTE", "Seller Operational Dispute"),
            ("SETTLEMENT_DISPUTE", "Settlement / Fee Dispute"),
            ("OTHER", "Other Claim / Dispute"),
        ]
    )
    description = serializers.CharField(max_length=2000)
    claimed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    evidence_urls = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
    )
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    customer_phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class SellerClaimRespondSerializer(serializers.Serializer):
    seller_response = serializers.CharField(max_length=2000)
    evidence_urls = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
    )


class SellerClaimAdminDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("REQUEST_SELLER_RESPONSE", "Request Seller Response"),
            ("APPROVE", "Approve Claim"),
            ("REJECT", "Reject Claim"),
            ("SETTLE", "Settle Claim"),
            ("CLOSE", "Close Claim"),
        ]
    )
    reason = serializers.CharField(max_length=1000)

    def validate_reason(self, value):
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("A detailed rationale is mandatory for all admin decisions.")
        return cleaned


class SellerClaimIntakeSerializer(serializers.Serializer):
    source_claim_id = serializers.CharField(max_length=128)
    source_order_id = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, default=None)
    order_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    source_return_id = serializers.CharField(max_length=100, required=False, allow_blank=True, allow_null=True, default=None)
    return_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    company_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    claim_type = serializers.CharField(max_length=40, required=False, default="DAMAGED_ITEM")
    description = serializers.CharField(max_length=2000)
    claimed_amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, default=Decimal("0.00"))
    evidence_urls = serializers.ListField(
        child=serializers.CharField(max_length=500),
        required=False,
        default=list,
    )
    customer_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    customer_phone = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")






