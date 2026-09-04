"""
workforce-app/backend/service_requests/models.py
ServiceRequest model pointing to shared Supabase table service_requests_servicerequest (managed=False).
"""
from decimal import Decimal
import threading
import uuid
from django.conf import settings
from django.db import models
from common.models import CompanyScopedManager

_dispatch_suppression = threading.local()


class suppress_dispatch_hook:
    """
    Context manager to prevent nested/recursive post-commit dispatch triggers
    when internal dispatch engine components update ServiceRequest records.
    """
    def __enter__(self):
        self._prev = getattr(_dispatch_suppression, "active", False)
        _dispatch_suppression.active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        _dispatch_suppression.active = self._prev

SERVICE_CATEGORIES = [
    ("hvac", "HVAC & Air Conditioning"),
    ("electrical", "Electrical & Wiring"),
    ("plumbing", "Plumbing & Sanitation"),
    ("appliance_repair", "Home Appliance Repair"),
    ("cleaning", "Cleaning & Sanitization"),
    ("carpentry", "Carpentry & Furniture"),
    ("painting", "Painting & Waterproofing"),
    ("pest_control", "Pest Control"),
    ("security", "Security & CCTV"),
    ("general", "General Maintenance"),
]


def _generate_request_id():
    last = ServiceRequest.objects.order_by("-id").first()
    num = (last.id + 1) if last and last.id else 1
    candidate = f"SR-{str(num).zfill(4)}"
    while ServiceRequest.objects.filter(request_id=candidate).exists():
        num += 1
        candidate = f"SR-{str(num).zfill(4)}"
    return candidate


# Canonical Quotation-based Service IDs and Slugs
QUOTATION_SERVICE_IDS = {
    91: "Interior Painting",
    92: "Exterior Painting",
    93: "Waterproofing",
    94: "Wood & Metal",
    95: "Texture Decor",
    35: "Brick & Block Work",
    36: "Plastering & Wall Repair",
    37: "Wall & Partition Construction",
    38: "Wall Breaking & Demolition",
}

QUOTATION_SERVICE_SLUGS = {
    "interior-painting",
    "exterior-painting",
    "waterproofing",
    "wood-metal",
    "texture-decor",
    "brick-block-work",
    "plastering-wall-repair",
    "wall-partition-construction",
    "wall-breaking-demolition",
}


def is_quotation_service(service_id=None, slug=None, name=None, category=None):
    """
    Authoritative backend check whether a service operates in QUOTATION mode.
    """
    if service_id and int(service_id) in QUOTATION_SERVICE_IDS:
        return True
    if slug and str(slug).lower().strip() in QUOTATION_SERVICE_SLUGS:
        return True
    if name:
        clean_name = str(name).lower().strip()
        for q_name in QUOTATION_SERVICE_IDS.values():
            if clean_name == q_name.lower():
                return True
    if category and str(category).lower().strip() in ["painting", "mason", "masonry", "painting & waterproofing", "masonry & civil"]:
        return True
    return False


class CatalogCategory(models.Model):

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=100, blank=True, default="")
    image = models.CharField(max_length=500, blank=True, default="")
    jobs_count_str = models.CharField(max_length=50, blank=True, default="")
    rating = models.CharField(max_length=10, blank=True, default="4.8")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = "service_requests_catalogcategory"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


class Service(models.Model):
    category = models.ForeignKey(
        CatalogCategory,
        on_delete=models.CASCADE,
        related_name="services",
        db_column="category_id"
    )
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=100, blank=True, default="")
    image = models.CharField(max_length=500, blank=True, default="")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    customization = models.JSONField(default=dict, blank=True)
    flow_type = models.CharField(max_length=50, default="STANDARD", blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_service"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name} ({self.category.name if self.category else 'No Category'})"

    @property
    def pricing_mode(self):
        return "QUOTATION" if is_quotation_service(self.id, self.slug, self.name) else "FIXED"

    @property
    def requires_inspection(self):
        return self.pricing_mode == "QUOTATION"

    @property
    def requires_measurement(self):
        return self.pricing_mode == "QUOTATION"

    @property
    def min_inspection_photos(self):
        if not self.requires_inspection:
            return 1
        if self.id in [91, 92, 93, 94, 95] or "painting" in (self.slug or "").lower():
            return 3
        return 2


class ServiceRequest(models.Model):

    class Status(models.TextChoices):
        DRAFT                 = "draft",                 "Draft"
        NEW_REQUEST           = "new_request",           "New Request"
        PENDING_PAYMENT       = "pending_payment",       "Pending Payment"
        CONFIRMED             = "confirmed",             "Confirmed"
        ASSIGNED              = "assigned",              "Assigned"
        RECEIVED              = "received",              "Received"
        ACCEPTED              = "accepted",              "Accepted"
        ON_THE_WAY            = "on_the_way",            "On The Way"
        EN_ROUTE              = "en_route",              "En Route"
        ARRIVED               = "arrived",               "Arrived"
        IN_PROGRESS           = "in_progress",           "In Progress"
        REDISPATCHING         = "redispatching",         "Redispatching"
        COMPLETED             = "completed",             "Completed"
        CANCELLED             = "cancelled",             "Cancelled"
        UNABLE_TO_COMPLETE    = "unable_to_complete",    "Unable To Complete"
        FOLLOW_UP_REQUIRED    = "follow_up_required",    "Follow Up Required"

    class Priority(models.TextChoices):
        LOW    = "low",    "Low"
        NORMAL = "normal", "Normal"
        HIGH   = "high",   "High"
        URGENT = "urgent", "Urgent"

    class PaymentMethod(models.TextChoices):
        COD    = "COD",    "Cash on Service"
        ONLINE = "ONLINE", "Online Payment"

    class PaymentStatus(models.TextChoices):
        PENDING   = "pending",   "Pending"
        COLLECTED = "collected", "Collected"
        PAID      = "paid",      "Paid"
        FAILED    = "failed",    "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class RequestKind(models.TextChoices):
        DIRECT     = "DIRECT",     "Direct Standard Job"
        ESTIMATION = "ESTIMATION", "Estimation / Inspection Job"
        WORK       = "WORK",       "Actual Work Execution Job"

    request_id = models.CharField(max_length=20, unique=True, blank=True)
    request_kind = models.CharField(
        max_length=50,
        choices=RequestKind.choices,
        default=RequestKind.DIRECT,
        db_index=True,
    )
    job_type = models.CharField(max_length=50, default="SERVICE", blank=True)
    vendor_id = models.CharField(max_length=100, blank=True, default="")
    vendor_name = models.CharField(max_length=200, blank=True, default="")
    vendor_confirmed_at = models.DateTimeField(null=True, blank=True)
    parent_request_id = models.BigIntegerField(null=True, blank=True)
    quote_number = models.CharField(max_length=50, null=True, blank=True)

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="service_requests",
        null=True, blank=True,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="service_requests_as_customer",
        null=True, blank=True,
    )
    customer_name = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, null=True)

    service_category = models.CharField(max_length=150)
    issue_title = models.CharField(max_length=300)
    description = models.TextField(blank=True, default="")
    address = models.TextField()
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=50, blank=True, null=True)
    photo = models.ImageField(upload_to="service_requests/photos/", null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cart_data = models.JSONField(default=list, blank=True)

    drop_address = models.TextField(blank=True, default="")
    drop_contact_name = models.CharField(max_length=200, blank=True, default="")
    drop_contact_phone = models.CharField(max_length=50, blank=True, default="")
    drop_contact_email = models.CharField(max_length=100, blank=True, default="")
    consignee_relationship = models.CharField(max_length=100, blank=True, default="")
    insurance_opted_in = models.BooleanField(default=False)
    logistics_leg = models.CharField(max_length=100, blank=True, default="DIRECT")
    logistics_leg_history = models.JSONField(default=list, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
        blank=True,
    )
    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        blank=True,
    )
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    payment_gateway = models.CharField(max_length=50, blank=True, null=True)
    invoice_id = models.CharField(max_length=50, blank=True, null=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW_REQUEST)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)

    assigned_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_service_requests",
    )
    technician_name = models.CharField(max_length=200, blank=True, default="")
    technician_phone = models.CharField(max_length=50, blank=True, default="")
    technician_photo = models.CharField(max_length=500, blank=True, default="")
    technician_location_name = models.CharField(max_length=200, blank=True, default="")
    start_otp = models.CharField(max_length=10, blank=True, default="")
    otp_verified = models.BooleanField(default=False)
    otp_attempt_count = models.IntegerField(default=0, blank=True)
    otp_hash = models.CharField(max_length=255, blank=True, default="")
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    payment_collected_by_name = models.CharField(max_length=200, blank=True, default="")
    collection_method = models.CharField(max_length=50, blank=True, default="")
    collection_reference = models.CharField(max_length=100, blank=True, default="")

    workforce_job_id = models.CharField(max_length=100, blank=True, default="")
    external_assignment_id = models.CharField(max_length=100, blank=True, default="")
    technician_id = models.IntegerField(null=True, blank=True)
    technician_rating = models.FloatField(null=True, blank=True)
    technician_heading = models.FloatField(null=True, blank=True, default=0.0)
    technician_speed = models.FloatField(null=True, blank=True, default=0.0)
    technician_latitude = models.FloatField(null=True, blank=True)
    technician_longitude = models.FloatField(null=True, blank=True)
    technician_accuracy = models.FloatField(null=True, blank=True)
    technician_location_updated_at = models.DateTimeField(null=True, blank=True)
    technician_last_seen_at = models.DateTimeField(null=True, blank=True)
    technician_arrived_at = models.DateTimeField(null=True, blank=True)
    tracking_token = models.UUIDField(null=True, blank=True, default=uuid.uuid4)
    accepted_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    service_zone_name_snapshot = models.CharField(max_length=200, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        managed = False
        db_table = "service_requests_servicerequest"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_id or f'SR #{self.pk}'} - {self.issue_title} ({self.status})"

    @property
    def is_estimation(self):
        """Authoritative check if this ServiceRequest is an Estimation Job."""
        if str(self.request_kind).upper() == "ESTIMATION":
            return True
        if str(self.request_kind).upper() == "WORK":
            return False
        return is_quotation_service(name=self.issue_title, category=self.service_category)

    @property
    def pricing_mode(self):
        if self.is_estimation:
            return "QUOTATION"
        return "FIXED"

    def save(self, *args, **kwargs):
        skip_dispatch = kwargs.pop("skip_dispatch", False)
        is_new = self.pk is None
        old_status = None
        if not is_new:
            old_inst = ServiceRequest.objects.filter(pk=self.pk).values("status").first()
            if old_inst:
                old_status = old_inst.get("status")

        if not self.request_id:
            self.request_id = _generate_request_id()
        super().save(*args, **kwargs)

        # Post-commit dispatch trigger: fires AFTER the transaction successfully commits.
        # This decouples dispatch from booking persistence — a dispatch failure will
        # never roll back or raise an exception during customer booking creation.
        # Only enqueues upon explicit lifecycle transitions:
        # 1. Newly created booking in a dispatchable status (unassigned)
        # 2. Status transition from non-dispatchable into dispatchable status
        # 3. Explicit redispatch status transition ('redispatching')
        # Unrelated saves (e.g. address text, notes, tokens) will NOT re-enqueue!
        from workforce_api.services.automatic_dispatch import DISPATCHABLE_STATUSES
        is_suppressed = getattr(_dispatch_suppression, "active", False) or getattr(self, "_skip_dispatch", False) or skip_dispatch
        is_dispatch_transition = (
            (is_new and self.status in DISPATCHABLE_STATUSES)
            or (old_status is not None and old_status not in DISPATCHABLE_STATUSES and self.status in DISPATCHABLE_STATUSES)
            or (self.status == "redispatching")
        )

        if not is_suppressed and is_dispatch_transition and self.assigned_employee_id is None:
            _job_id = self.pk
            _comp_id = self.company_id

            def _post_commit_dispatch():
                import logging
                _log = logging.getLogger("workforce.dispatch")
                try:
                    # Enqueue to reliable Redis Stream (workforce:dispatch:jobs)
                    from workforce_api.services.redis_dispatch import enqueue_dispatch_job
                    msg_id = enqueue_dispatch_job(_job_id, event_type="NEW_JOB", company_id=_comp_id)
                    if not msg_id:
                        # Redis unavailable: execute bounded single-job targeted fallback
                        _log.info(f"[DISPATCH_FALLBACK_DB] Redis unavailable for Job #{_job_id}. Executing bounded DB reconciliation.")
                        from workforce_api.services.automatic_dispatch import reconcile_booking_for_dispatch
                        from service_requests.models import ServiceRequest as _SR
                        _job = _SR.objects.filter(pk=_job_id).first()
                        if _job:
                            reconcile_booking_for_dispatch(_job, use_redis_geo=False)
                except Exception as _exc:
                    _log.exception(
                        f"[AUTO_DISPATCH_TRIGGER_FAILED] Post-commit dispatch failed for Job #{_job_id}: {_exc}"
                    )

            from django.db import transaction
            transaction.on_commit(_post_commit_dispatch)



    def is_ready_to_complete(self):
        """
        Authoritative completion aggregation check for a ServiceRequest.
        A ServiceRequest can become COMPLETED only when:
        1. Required proof of work is submitted.
        2. All accepted work extensions for this job are COMPLETED or RESOLVED.
        3. All specialist secondary jobs linked to this request are COMPLETED.
        4. No unresolved operational dependencies remain.
        Returns:
            (is_ready: bool, reason: str, pending_dependencies: list)
        """
        pending_dependencies = []

        # 1. Check post-service proof
        proof = getattr(self, "post_service_proof", None)
        if not proof:
            from workforce_api.models import PostServiceProof
            proof = PostServiceProof.objects.filter(job=self).first()

        if not proof or not proof.is_submitted:
            pending_dependencies.append("Post-service proof (photos and completion notes) has not been submitted.")

        # 2. Check accepted work extensions
        from workforce_api.models import WorkforceWorkExtension
        open_extensions = WorkforceWorkExtension.objects.filter(
            job=self,
            status__in=[
                WorkforceWorkExtension.Status.REQUESTED,
                WorkforceWorkExtension.Status.ADMIN_APPROVED,
                WorkforceWorkExtension.Status.PENDING_ASSIGNMENT,
                WorkforceWorkExtension.Status.CUSTOMER_ACCEPTED,
                WorkforceWorkExtension.Status.IN_PROGRESS,
            ]
        )
        for ext in open_extensions:
            pending_dependencies.append(
                f"Work extension #{ext.id} ('{ext.title}') is still in '{ext.status}' state."
            )

        # 3. Check specialist secondary jobs linked via cart_data or extension foreign keys
        cart_data = self.cart_data or []
        for item in cart_data:
            if item.get("type") == "specialist_job" and item.get("job_id"):
                s_job = ServiceRequest.objects.filter(pk=item["job_id"]).first()
                if s_job and s_job.status not in ["completed", "cancelled"]:
                    pending_dependencies.append(
                        f"Secondary specialist job #{s_job.id} is still in '{s_job.status}' state."
                    )

        for ext in WorkforceWorkExtension.objects.filter(job=self, specialist_job__isnull=False):
            if ext.specialist_job and ext.specialist_job.status not in ["completed", "cancelled"]:
                msg = f"Secondary specialist job #{ext.specialist_job.id} (Extension #{ext.id}) is still in '{ext.specialist_job.status}' state."
                if msg not in pending_dependencies:
                    pending_dependencies.append(msg)

        # 4. Check payment state machine: Payment must be verified as PAID before closing job
        try:
            from workforce_api.models import JobPayment
            pmt = getattr(self, "payment_record", None) or JobPayment.objects.filter(job=self).first()
            if pmt:
                if pmt.payment_method == JobPayment.PaymentMethod.CASH_ON_SERVICE:
                    if not pmt.is_cash_collected or pmt.payment_status not in [JobPayment.PaymentStatus.PAID, "PAID", "paid"]:
                        pending_dependencies.append("Cash on service payment collection is required before closing job.")
                elif pmt.payment_status not in [JobPayment.PaymentStatus.PAID, "PAID", "paid"]:
                    pending_dependencies.append(f"Payment is in '{pmt.payment_status}' state (must be PAID before closing job).")
            else:
                is_cash = (self.payment_method or "").lower() in ["cash", "cod", "cash_on_service", "cash_on_delivery"]
                if str(self.payment_status).lower() not in ["paid", "collected"]:
                    if is_cash:
                        pending_dependencies.append("Cash on service payment collection is required before closing job.")
                    else:
                        pending_dependencies.append(f"Payment status is '{self.payment_status}' (must be PAID before closing job).")
        except Exception as e:
            pending_dependencies.append(f"Payment verification failed: {str(e)}")

        is_ready = len(pending_dependencies) == 0
        reason = "Ready for completion." if is_ready else f"Cannot complete ServiceRequest: {'; '.join(pending_dependencies)}"
        return is_ready, reason, pending_dependencies



class EmployeeJob(models.Model):
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="employee_jobs",
        db_column="service_request_id"
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="employee_jobs",
        db_column="employee_id"
    )
    status = models.CharField(max_length=50, default="ASSIGNED")
    notes = models.TextField(blank=True, default="")
    assigned_date = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    accepted_date = models.DateTimeField(null=True, blank=True)
    started_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_employee_jobs",
        db_column="assigned_by_id"
    )

    uncompletion_reason = models.TextField(blank=True, default="")
    source_work_extension_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_employeejob"

    def __str__(self):
        return f"EmployeeJob SR-{self.service_request_id} -> Emp {self.employee_id} ({self.status})"


RequestKind = ServiceRequest.RequestKind


class Estimation(models.Model):
    """
    AC Specification & Workflow Detail (service_requests_estimation).
    Linked 1:1 with service_requests_servicerequest.
    """
    class ACType(models.TextChoices):
        SPLIT = "SPLIT", "Split AC"
        WINDOW = "WINDOW", "Window AC"
        CASSETTE = "CASSETTE", "Cassette AC"
        TOWER = "TOWER", "Tower AC"
        OTHER = "OTHER", "Other"

    class ACCapacity(models.TextChoices):
        ONE_TON = "1_TON", "1 Ton"
        ONE_POINT_FIVE_TON = "1.5_TON", "1.5 Ton"
        TWO_TON = "2_TON", "2 Ton"
        OTHER = "OTHER", "Other"

    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Requested"
        VENDOR_CONFIRMED = "VENDOR_CONFIRMED", "Vendor Confirmed"
        TECHNICIAN_ASSIGNED = "TECHNICIAN_ASSIGNED", "Technician Assigned"
        TECHNICIAN_ON_THE_WAY = "TECHNICIAN_ON_THE_WAY", "Technician On The Way"
        TECHNICIAN_ARRIVED = "TECHNICIAN_ARRIVED", "Technician Arrived"
        INSPECTION_IN_PROGRESS = "INSPECTION_IN_PROGRESS", "Inspection In Progress"
        INSPECTION_COMPLETED = "INSPECTION_COMPLETED", "Inspection Completed"
        QUOTATION_SENT = "QUOTATION_SENT", "Quotation Sent"
        CUSTOMER_APPROVED = "CUSTOMER_APPROVED", "Customer Approved"
        CUSTOMER_REJECTED = "CUSTOMER_REJECTED", "Customer Rejected"
        CONVERTED_TO_SERVICE = "CONVERTED_TO_SERVICE", "Converted To Service"
        CLOSED = "CLOSED", "Closed"
        CANCELLED = "CANCELLED", "Cancelled"

    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="estimation_details",
        db_column="service_request_id",
    )
    ac_type = models.CharField(max_length=50, choices=ACType.choices, default=ACType.SPLIT)
    ac_brand = models.CharField(max_length=100, default="")
    ac_capacity = models.CharField(max_length=50, choices=ACCapacity.choices, default=ACCapacity.ONE_POINT_FIVE_TON)
    ac_quantity = models.PositiveSmallIntegerField(default=1)
    customer_symptom = models.TextField(blank=True, default="")
    customer_notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=50, choices=Status.choices, default=Status.REQUESTED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Estimation #{self.id} for SR #{self.service_request_id} ({self.status})"


class EstimationFee(models.Model):
    """
    Inspection Visit Fee for AC Estimation (service_requests_estimationfee).
    """
    class FeeStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        COLLECTED = "COLLECTED", "Collected"
        WAIVED = "WAIVED", "Waived"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="fees",
        db_column="estimation_id",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("199.00"))
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=30, choices=FeeStatus.choices, default=FeeStatus.PENDING)
    payment_reference = models.CharField(max_length=255, blank=True, default="")
    payment_method = models.CharField(max_length=50, blank=True, default="")
    collected_at = models.DateTimeField(null=True, blank=True)
    waived_at = models.DateTimeField(null=True, blank=True)
    waived_reason = models.TextField(blank=True, default="")
    waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="waived_estimation_fees",
        db_column="waived_by_id",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimationfee"

    def __str__(self):
        return f"Fee #{self.id} (Est #{self.estimation_id}): ₹{self.amount} ({self.status})"


class Inspection(models.Model):
    """
    On-site Technician Diagnosis & Job Inspection (service_requests_inspection).
    """
    class InspectionStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="inspections",
        db_column="estimation_id",
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="technician_inspections",
        db_column="technician_id",
    )
    technician_external_id = models.CharField(max_length=100, blank=True, default="")
    technician_name = models.CharField(max_length=200, blank=True, default="")
    technician_phone = models.CharField(max_length=50, blank=True, default="")
    status = models.CharField(max_length=30, choices=InspectionStatus.choices, default=InspectionStatus.PENDING)
    diagnosis = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "service_requests_inspection"

    def __str__(self):
        return f"Inspection #{self.id} for Est #{self.estimation_id} ({self.status})"


class InspectionFinding(models.Model):
    """
    Structured defect findings discovered during inspection (service_requests_inspectionfinding).
    """
    class FindingType(models.TextChoices):
        GAS_LEAKAGE = "Gas Leakage", "Gas Leakage"
        COIL_CLEANING = "Coil Cleaning", "Coil Cleaning"
        COMPRESSOR = "Compressor", "Compressor"
        ELECTRICAL = "Electrical", "Electrical"
        CAPACITOR = "Capacitor", "Capacitor"
        FAN_MOTOR = "Fan Motor", "Fan Motor"
        DRAINAGE = "Drainage", "Drainage"
        OTHER = "Other", "Other"

    class Severity(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="findings",
        db_column="inspection_id",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="inspection_findings",
        db_column="service_id",
    )
    finding_type = models.CharField(max_length=100, default=FindingType.OTHER)
    title = models.CharField(max_length=255)
    diagnosis = models.TextField(blank=True, default="")
    severity = models.CharField(max_length=30, choices=Severity.choices, default=Severity.MEDIUM)
    description = models.TextField(blank=True, default="")
    recommended_action = models.TextField(blank=True, default="")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit = models.CharField(max_length=50, default="unit")
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "service_requests_inspectionfinding"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Finding #{self.id} ({self.finding_type}): {self.title}"


class InspectionPhoto(models.Model):
    """
    Evidence photo linked to an inspection and optional finding (service_requests_inspectionphoto).
    """
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="photos",
        db_column="inspection_id",
    )
    finding = models.ForeignKey(
        InspectionFinding,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="photos",
        db_column="finding_id",
    )
    photo = models.CharField(max_length=500)
    caption = models.CharField(max_length=255, blank=True, default="")
    uploaded_by = models.CharField(max_length=100, default="technician")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "service_requests_inspectionphoto"

    def __str__(self):
        return f"Photo #{self.id} for Inspection #{self.inspection_id}"


class EstimationQuotation(models.Model):
    """
    Formal, versioned commercial Quotation (service_requests_estimationquotation).
    """
    class QuoteStatus(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SENT = "SENT", "Sent to Customer"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    class RejectionReason(models.TextChoices):
        PRICE_TOO_HIGH = "PRICE_TOO_HIGH", "Price Too High"
        WILL_DO_LATER = "WILL_DO_LATER", "Will Do Later"
        FOUND_ALTERNATIVE = "FOUND_ALTERNATIVE", "Found Alternative"
        OTHER = "OTHER", "Other"

    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="quotations",
        db_column="estimation_id",
    )
    version = models.PositiveSmallIntegerField(default=1)
    quote_ref = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=30, choices=QuoteStatus.choices, default=QuoteStatus.DRAFT)
    vendor_id = models.CharField(max_length=100, blank=True, default="")
    technician_id = models.CharField(max_length=100, blank=True, default="")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    notes = models.TextField(blank=True, default="")
    valid_until = models.DateField(null=True, blank=True)
    customer_approved_at = models.DateTimeField(null=True, blank=True)
    customer_rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=100, blank=True, default="")
    rejection_note = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimationquotation"
        ordering = ["-version", "-created_at"]

    def __str__(self):
        return f"Quote {self.quote_ref} (v{self.version}): ₹{self.total_amount} [{self.status}]"


class EstimationQuotationItem(models.Model):
    """
    Quotation line item (service_requests_estimationquotationitem).
    """
    class ItemType(models.TextChoices):
        LABOR = "LABOR", "Labor"
        PART = "PART", "Spare Part"
        GAS = "GAS", "Refrigerant Gas"
        OTHER = "OTHER", "Other"

    quotation = models.ForeignKey(
        EstimationQuotation,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="quotation_id",
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="quotation_items",
        db_column="service_id",
    )
    catalog_service_id = models.CharField(max_length=100, blank=True, default="")
    service_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit = models.CharField(max_length=50, default="unit")
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    sort_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimationquotationitem"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.service_name} x {self.quantity} = ₹{self.line_total}"


class ServiceRequestPayment(models.Model):
    """
    Marketplace & Workforce Payment Record (service_requests_payment).
    """
    customer_id_snapshot = models.CharField(max_length=50, blank=True, default="")
    service_request_id_snapshot = models.CharField(max_length=50, blank=True, default="")
    razorpay_order_id = models.CharField(max_length=100, blank=True, default="")
    razorpay_payment_id = models.CharField(max_length=100, blank=True, default="")
    razorpay_signature = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=30, default="pending")
    method = models.CharField(max_length=50, default="ONLINE")
    gateway = models.CharField(max_length=50, default="razorpay")
    error_code = models.CharField(max_length=100, blank=True, default="")
    error_description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sr_payments",
        db_column="customer_id",
    )
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="payments",
        db_column="service_request_id",
    )

    class Meta:
        managed = False
        db_table = "service_requests_payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.id} for SR #{self.service_request_id} - ₹{self.amount} ({self.status})"


class SettingsHubInvoice(models.Model):
    """
    Invoice entity stored in settings_hub_invoice for customer download reference.
    """
    invoice_number = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=30, default="PAID")
    billing_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    pdf_url = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="invoices",
        db_column="company_id",
    )

    class Meta:
        managed = False
        db_table = "settings_hub_invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - ₹{self.amount} ({self.status})"

class BookingMessage(models.Model):
    """
    X-09: unmanaged mirror of the Customer app's service_requests.BookingMessage
    (same shared table, service_requests_booking_message) -- see that
    model's docstring for the full rationale. This app writes
    technician-sent messages here; sender_user is left null on writes from
    this side since this app's Employee model isn't a row in the Customer
    app's AUTH_USER_MODEL table.
    """

    class SenderPersona(models.TextChoices):
        CUSTOMER   = "customer",   "Customer"
        TECHNICIAN = "technician", "Technician"
        ADMIN      = "admin",      "Admin"

    booking = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="chat_messages",
    )
    sender_persona = models.CharField(max_length=15, choices=SenderPersona.choices)
    sender_name = models.CharField(max_length=200, blank=True, default="")
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at_customer = models.DateTimeField(null=True, blank=True)
    read_at_technician = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_booking_message"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.sender_persona}: {self.body[:40]}"
