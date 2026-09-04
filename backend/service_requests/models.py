"""
workforce-app/backend/service_requests/models.py
ServiceRequest model pointing to shared Supabase table service_requests_servicerequest (managed=False).
"""
from django.conf import settings
from django.db import models
from common.models import CompanyScopedManager

# HS-E-06: these labels previously drifted from the Customer app's own
# static SERVICE_CATEGORIES list (same slugs, e.g. "hvac" here read
# "HVAC & Air Conditioning" while the Customer app said just "HVAC") --
# a technician-facing screen and a customer-facing one could show two
# different names for the exact same category slug. Both are only a
# fallback anyway (CatalogCategory, the shared DB table, is tried first
# on both sides) but when it IS used it should say the same thing.
# Synced to match Customer/backend/service_requests/models.py exactly.
SERVICE_CATEGORIES = [
    ("plumbing", "Plumbing"),
    ("electrical", "Electrical"),
    ("carpentry", "Carpentry"),
    ("hvac", "HVAC"),
    ("cleaning", "Cleaning"),
    ("pest_control", "Pest Control"),
    ("painting", "Painting"),
    ("appliance_repair", "Appliance Repair"),
    ("security", "Security Systems"),
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
    flow_type = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        managed = False
        db_table = "service_requests_catalogcategory"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.name


QUOTATION_SERVICE_IDS = {
    35: "Masonry Wall Repair",
    36: "Tile Laying & Replacement",
    37: "Plastering & Masonry Work",
    38: "Brickwork Construction",
    91: "Interior Full Home Painting",
    92: "Exterior Wall Painting",
    93: "Waterproofing & Primer Coating",
    94: "Wood & Metal Polish",
}


def is_quotation_service(service_or_id=None, name=None, category=None, **kwargs):
    if service_or_id is not None:
        if isinstance(service_or_id, int) and service_or_id in QUOTATION_SERVICE_IDS:
            return True
        if hasattr(service_or_id, "id") and getattr(service_or_id, "id") in QUOTATION_SERVICE_IDS:
            return True
        if hasattr(service_or_id, "name") and not name:
            name = getattr(service_or_id, "name")
        if hasattr(service_or_id, "category") and not category:
            cat = getattr(service_or_id, "category")
            category = cat.name if hasattr(cat, "name") else str(cat)
    if name:
        lower_name = str(name).lower()
        if any(kw in lower_name for kw in ["paint", "mason", "estimation", "inspection", "waterproof"]):
            return True
    if category:
        lower_cat = str(category).lower()
        if any(kw in lower_cat for kw in ["paint", "mason", "estimation", "inspection"]):
            return True
    return False


class RequestKind(models.TextChoices):
    STANDARD     = "standard",     "Standard"
    INSPECTION   = "inspection",   "Inspection"
    QUOTED_WORK  = "quoted_work",  "Quoted Work"
    ESTIMATION   = "estimation",   "Estimation"
    WORK         = "work",         "Work"


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
        if self.id in QUOTATION_SERVICE_IDS or is_quotation_service(self):
            return "QUOTATION"
        return "FIXED"


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

    # GT-B-03: mirrors the Customer app's ServiceRequest.LogisticsLeg
    # exactly (same field, same choices, same shared table) -- see that
    # model's docstring for the full rationale. This is the technician-
    # facing side: WorkforceJobLogisticsLegView (workforce_api/views.py)
    # is what actually sets this.
    class LogisticsLeg(models.TextChoices):
        EN_ROUTE_PICKUP = "EN_ROUTE_PICKUP", "En Route to Pickup"
        LOADING         = "LOADING",         "Loading"
        EN_ROUTE_DROP   = "EN_ROUTE_DROP",   "En Route to Drop"
        UNLOADING       = "UNLOADING",       "Unloading"
        DELIVERED       = "DELIVERED",       "Delivered"

    # X-04: mirrors the Customer app's ServiceRequest.CancellationReason
    # exactly, so cancellation_reason (added below) can carry the same
    # choices on both sides of the shared table.
    class CancellationReason(models.TextChoices):
        CHANGE_OF_PLANS   = "CHANGE_OF_PLANS",   "Change of plans / Booked by mistake"
        EXPECTED_FASTER    = "EXPECTED_FASTER",    "Expected faster service / Partner too far"
        WRONG_SERVICE      = "WRONG_SERVICE",      "Selected wrong service, date, or address"
        FOUND_ALTERNATIVE  = "FOUND_ALTERNATIVE",  "Found alternative service / Solved myself"
        PRICE_OR_PAYMENT   = "PRICE_OR_PAYMENT",   "Price or payment issue"
        OTHER              = "OTHER",              "Other reason"

    class PaymentMethod(models.TextChoices):
        COD    = "COD",    "Cash on Service"
        ONLINE = "ONLINE", "Online Payment"

    class PaymentStatus(models.TextChoices):
        PENDING   = "pending",   "Pending"
        COLLECTED = "collected", "Collected"
        PAID      = "paid",      "Paid"
        FAILED    = "failed",    "Failed"
        CANCELLED = "cancelled", "Cancelled"
        # HS-C-03/HS-C-06: were missing from this mirror -- this app's own
        # PaymentStatus was a strict subset of the Customer app's (this table
        # is shared). CASH_PENDING is the important one: this app writes it
        # onto the shared column directly (see WorkforceJob*PaymentView-style
        # code in workforce_api/views.py) whenever a technician reports cash
        # collected but the customer has not yet confirmed it -- it was never
        # a formally recognized value on either side of this mirror.
        PROCESSING         = "processing",         "Processing"
        REFUNDED           = "refunded",           "Refunded"
        PARTIALLY_REFUNDED = "partially_refunded", "Partially Refunded"
        CASH_PENDING       = "cash_pending",       "Cash Collection Pending"

    request_id = models.CharField(max_length=20, unique=True, blank=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="service_requests",
        null=True, blank=True,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="sr_payments",
        db_column="customer_id",
    )
    customer_name = models.CharField(max_length=200, blank=True, default="")
    phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(blank=True, null=True)
    # X-04: was missing from this mirror -- vendor-side code that needs to
    # look up the customer's permanent ID (e.g. for a payslip/invoice
    # reference) had no field to read it from.
    customer_code = models.CharField(max_length=30, blank=True, null=True, db_index=True)

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
    # X-04: these were all missing from this mirror even though they exist
    # on the shared table -- a technician handling a logistics job had no
    # way, via this app's ORM, to see who they're actually handing goods to
    # (drop_contact_*) or what the declared value / insurance status is.
    drop_contact_name = models.CharField(max_length=200, blank=True, default="")
    drop_contact_phone = models.CharField(max_length=20, blank=True, default="")
    drop_contact_email = models.EmailField(blank=True, default="")
    declared_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    consignee_relationship = models.CharField(max_length=100, blank=True, default="")
    insurance_opted_in = models.BooleanField(default=False)
    insurance_premium = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    insurance_liability_cap = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    logistics_leg = models.CharField(max_length=20, choices=LogisticsLeg.choices, blank=True, default="")
    logistics_leg_updated_at = models.DateTimeField(null=True, blank=True)
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
    # X-04: was missing -- payroll/earnings code on this side could not
    # tell WHEN a cash payment was actually collected, only who collected it
    # (payment_collected_by_name, already present below).
    payment_collected_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.NEW_REQUEST)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL)
    job_type = models.CharField(max_length=50, blank=True, default="SERVICE", db_index=True)
    # X-04: were missing -- this app's own request_id auto-numbering only
    # makes sense in the context of what KIND of request it is, and quote
    # jobs are a first-class case the workforce app should be able to see.
    request_kind = models.CharField(max_length=30, default="standard", db_index=True,
                                     choices=[("standard", "Standard"),
                                              ("inspection", "Inspection"),
                                              ("quoted_work", "Quoted Work"),
                                              ("estimation", "Estimation"),
                                              ("work", "Work")])
    quote_number = models.CharField(max_length=100, blank=True, null=True, unique=True, db_index=True)

    # X-04: pricing snapshot fields, all missing from this mirror -- a
    # technician-facing payslip/earnings view that wants to show what a
    # coupon actually discounted, or the true subtotal/final breakdown,
    # had no field to read any of it from.
    coupon_code_snapshot = models.CharField(max_length=50, blank=True, default="")
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    # X-04: cancellation fields, all missing from this mirror -- without
    # these a technician-side "why was this job cancelled" view (e.g. after
    # WorkforceJobArriveView-style checks) had nothing to read, even though
    # the Customer app records this in full on every cancellation.
    cancelled_at = models.DateTimeField(null=True, blank=True, db_index=True)
    cancelled_by_persona = models.CharField(max_length=30, blank=True, choices=[("customer", "Customer"), ("admin", "Admin"), ("employee", "Employee")])
    cancellation_reason = models.CharField(max_length=50, blank=True, choices=CancellationReason.choices)
    cancellation_note = models.TextField(blank=True)
    cancelled_at_status = models.CharField(max_length=30, blank=True)

    # X-04: service-zone-at-booking-time snapshot, missing from this mirror.
    service_zone_id_snapshot = models.IntegerField(null=True, blank=True, db_index=False)
    service_zone_name_snapshot = models.CharField(max_length=150, blank=True, default="")

    assigned_employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_service_requests",
    )
    technician_id = models.BigIntegerField(null=True, blank=True)
    technician_name = models.CharField(max_length=200, blank=True, default="")
    technician_phone = models.CharField(max_length=50, blank=True, default="")
    technician_photo = models.CharField(max_length=500, blank=True, default="")
    # X-04: were missing from this mirror -- this is exactly the field pair
    # a technician's own live-location update would need to write to, and
    # this app previously had no way to set them via its ORM at all.
    technician_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    technician_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    technician_speed = models.FloatField(null=True, blank=True)
    technician_accuracy = models.FloatField(null=True, blank=True)
    technician_heading = models.FloatField(null=True, blank=True)
    technician_location_updated_at = models.DateTimeField(null=True, blank=True)
    technician_last_seen_at = models.DateTimeField(null=True, blank=True)
    technician_arrived_at = models.DateTimeField(null=True, blank=True)
    technician_location_name = models.CharField(max_length=200, blank=True, default="")
    start_otp = models.CharField(max_length=10, blank=True, default="")
    otp_verified = models.BooleanField(default=False)
    otp_attempt_count = models.IntegerField(default=0, blank=True)
    otp_hash = models.CharField(max_length=255, blank=True, default="")
    # X-04: were missing -- this app could set/read otp_verified but never
    # see when the OTP actually expires or when it was verified.
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_verified_at = models.DateTimeField(null=True, blank=True)
    # X-04: was missing -- the UUID a customer's tracking link is built
    # from; a technician-side deep link to the same tracking page had
    # nothing to read this from.
    tracking_token = models.UUIDField(null=True, blank=True, unique=True, db_index=True)
    payment_collected_by_name = models.CharField(max_length=200, blank=True, default="")
    collection_method = models.CharField(max_length=50, blank=True, default="")
    collection_reference = models.CharField(max_length=100, blank=True, default="")

    # X-04: workforce_job_id/external_assignment_id/technician_rating were
    # the only genuinely new fields in what used to be a second block here --
    # that block also re-declared technician_name/phone/photo and
    # payment_collected_by_name/collection_method/collection_reference a
    # second time (Django silently keeps only the last definition of a
    # repeated attribute name, so those duplicates were dead code) and gave
    # technician_photo a different type the second time around (TextField
    # vs the correct CharField(max_length=500) above, matching the
    # Customer app's real column) -- removed rather than fixed in place,
    # since the first declarations above are already correct.
    workforce_job_id = models.CharField(max_length=100, blank=True, default="")
    external_assignment_id = models.CharField(max_length=100, blank=True, default="")
    technician_rating = models.FloatField(null=True, blank=True)

    vendor_id = models.CharField(max_length=100, blank=True, null=True)
    vendor_name = models.CharField(max_length=200, blank=True, null=True)
    vendor_confirmed_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = CompanyScopedManager()

    class Meta:
        managed = False
        db_table = "service_requests_servicerequest"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request_id or f'SR #{self.pk}'} - {self.issue_title} ({self.status})"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.request_id:
            self.request_id = _generate_request_id()
        super().save(*args, **kwargs)

        if is_new and self.status in ["new_request", "confirmed", "draft"]:
            try:
                from workforce_api.services.automatic_dispatch import dispatch_job
                dispatch_job(self)
            except Exception as e:
                import logging
                logging.getLogger("workforce.dispatch").exception(
                    f"[AUTO_DISPATCH_TRIGGER_FAILED] Failed to trigger automatic dispatch for Job #{self.id}: {e}"
                )
        elif self.status in ["cancelled", "completed", "unable_to_complete"]:
            try:
                from service_requests.models import EmployeeJob
                from workforce_api.models import JobTrackingSession
                from django.utils import timezone
                EmployeeJob.objects.filter(service_request=self).exclude(
                    status__in=["COMPLETED", "CANCELLED", "REJECTED"]
                ).update(status=self.status.upper())

                closing_session_status = (
                    JobTrackingSession.SessionStatus.COMPLETED
                    if self.status == "completed"
                    else JobTrackingSession.SessionStatus.CANCELLED
                )
                JobTrackingSession.objects.filter(
                    job=self, status=JobTrackingSession.SessionStatus.ACTIVE
                ).update(status=closing_session_status, ended_at=timezone.now())

                if self.assigned_employee:
                    from workforce_api.services.workload import reconcile_employee_availability
                    reconcile_employee_availability(self.assigned_employee)
            except Exception as e:
                import logging
                logging.getLogger("workforce.cancel").warning(
                    f"[TERMINAL_STATUS_CLEANUP_ERR] Failed cleanup for Job #{self.id}: {e}"
                )



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
                if pmt.payment_status == JobPayment.PaymentStatus.CASH_PENDING:
                    pending_dependencies.append("Cash payment collection has been reported but is awaiting customer confirmation.")
                elif pmt.payment_status == JobPayment.PaymentStatus.PENDING and pmt.payment_method == JobPayment.PaymentMethod.CASH_ON_SERVICE:
                    pending_dependencies.append("Cash on service payment collection and confirmation is required before closing job.")
                elif pmt.payment_status not in [JobPayment.PaymentStatus.PAID, "PAID", "paid"]:
                    pending_dependencies.append(f"Payment is in '{pmt.payment_status}' state (must be PAID before closing job).")
            else:
                if str(self.payment_status).lower() not in ["paid", "collected"]:
                    pending_dependencies.append(f"Payment status is '{self.payment_status}' (must be PAID before closing job).")
        except Exception as e:
            pending_dependencies.append(f"Payment verification failed: {str(e)}")

        is_ready = len(pending_dependencies) == 0
        reason = "Ready for completion." if is_ready else f"Cannot complete ServiceRequest: {'; '.join(pending_dependencies)}"
        return is_ready, reason, pending_dependencies

    @property
    def is_estimation(self):
        return (
            getattr(self, "job_type", "") == "ESTIMATION"
            or str(self.request_kind).lower() in ["estimation", "inspection"]
            or is_quotation_service(name=self.issue_title, category=self.service_category)
        )

    @property
    def is_work_job(self):
        return not self.is_estimation

    @property
    def pricing_mode(self):
        return "QUOTATION" if self.is_estimation else "FIXED"


class EmployeeJob(models.Model):
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="employee_jobs",
        db_column="service_request_id",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="employee_jobs",
        db_column="employee_id",
    )
    status = models.CharField(max_length=50, default="ASSIGNED")
    notes = models.TextField(blank=True, default="")
    assigned_date = models.DateTimeField(null=True, blank=True)
    accepted_date = models.DateTimeField(null=True, blank=True)
    started_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    is_primary = models.BooleanField(default=True)
    assigned_by_id = models.BigIntegerField(null=True, blank=True)
    uncompletion_reason = models.TextField(blank=True, default="")
    source_work_extension_id = models.BigIntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_employeejob"
        ordering = ["-assigned_date"]

    def __str__(self):
        return f"EmployeeJob SR-{self.service_request_id} -> Emp {self.employee_id} ({self.status})"


class ServiceRequestPayment(models.Model):
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="payments",
        db_column="service_request_id",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="customer_id",
        related_name="sr_payments_list",
    )
    customer_id_snapshot = models.CharField(max_length=100, blank=True, default="")
    service_request_id_snapshot = models.CharField(max_length=100, blank=True, default="")
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=50, default="PENDING")
    method = models.CharField(max_length=50, default="CASH")
    gateway = models.CharField(max_length=50, default="MANUAL")
    error_code = models.CharField(max_length=100, blank=True, default="")
    error_description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "service_requests_payment"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment #{self.id} for SR-{self.service_request_id}: ₹{self.amount} ({self.status})"


class SettingsHubInvoice(models.Model):
    invoice_number = models.CharField(max_length=100, unique=True, null=True, blank=True)
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="company_id",
        related_name="hub_invoices",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=50, default="PAID")
    billing_date = models.DateField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    pdf_url = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "settings_hub_invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invoice {self.invoice_number} - ₹{self.amount} ({self.status})"


class Estimation(models.Model):
    service_request = models.ForeignKey(
        ServiceRequest,
        on_delete=models.CASCADE,
        related_name="estimations",
        db_column="service_request_id",
        null=True,
        blank=True,
    )
    ac_type = models.CharField(max_length=100, blank=True, null=True)
    ac_brand = models.CharField(max_length=100, blank=True, null=True)
    ac_capacity = models.CharField(max_length=100, blank=True, null=True)
    ac_quantity = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    customer_symptom = models.TextField(blank=True, null=True)
    customer_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="draft", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Estimation #{self.id} for SR #{self.service_request_id} ({self.status})"


class EstimationFee(models.Model):
    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="fees",
        db_column="estimation_id",
        null=True,
        blank=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    currency = models.CharField(max_length=10, default="INR", null=True, blank=True)
    status = models.CharField(max_length=50, default="pending", null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    waived_at = models.DateTimeField(null=True, blank=True)
    waived_reason = models.TextField(blank=True, null=True)
    waived_by_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimationfee"
        ordering = ["-created_at"]

    def __str__(self):
        return f"EstimationFee #{self.id} - ₹{self.amount} ({self.status})"


class Inspection(models.Model):
    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="inspections",
        db_column="estimation_id",
        null=True,
        blank=True,
    )
    technician = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="technician_id",
        related_name="ac_inspections",
    )
    technician_external_id = models.CharField(max_length=100, blank=True, null=True)
    technician_name = models.CharField(max_length=200, blank=True, null=True)
    technician_phone = models.CharField(max_length=50, blank=True, null=True)
    status = models.CharField(max_length=50, default="pending", null=True, blank=True)
    diagnosis = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_inspection"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Inspection #{self.id} for Est #{self.estimation_id} ({self.status})"


class InspectionFinding(models.Model):
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="findings",
        db_column="inspection_id",
        null=True,
        blank=True,
    )
    service_id = models.BigIntegerField(null=True, blank=True)
    finding_type = models.CharField(max_length=50, blank=True, null=True)
    title = models.CharField(max_length=255)
    diagnosis = models.TextField(blank=True, null=True)
    severity = models.CharField(max_length=50, blank=True, null=True, default="low")
    description = models.TextField(blank=True, null=True)
    recommended_action = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True, default="unit")
    sort_order = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_inspectionfinding"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Finding: {self.title} ({self.severity})"


class InspectionPhoto(models.Model):
    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="photos",
        db_column="inspection_id",
        null=True,
        blank=True,
    )
    finding_id = models.BigIntegerField(null=True, blank=True)
    photo = models.CharField(max_length=500)
    caption = models.CharField(max_length=255, blank=True, null=True)
    uploaded_by = models.CharField(max_length=100, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_inspectionphoto"
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Photo #{self.id} for Inspection #{self.inspection_id}"


class EstimationQuotation(models.Model):
    estimation = models.ForeignKey(
        Estimation,
        on_delete=models.CASCADE,
        related_name="quotations",
        db_column="estimation_id",
        null=True,
        blank=True,
    )
    version = models.PositiveSmallIntegerField(default=1, null=True, blank=True)
    quote_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=50, default="draft", null=True, blank=True)
    vendor_id = models.CharField(max_length=100, blank=True, null=True)
    technician_id = models.CharField(max_length=100, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    currency = models.CharField(max_length=10, default="INR", null=True, blank=True)
    notes = models.TextField(blank=True, null=True)
    valid_until = models.DateField(null=True, blank=True)
    customer_approved_at = models.DateTimeField(null=True, blank=True)
    customer_rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=100, blank=True, null=True)
    rejection_note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimationquotation"
        ordering = ["-version"]

    def __str__(self):
        return f"Quotation {self.quote_ref} v{self.version} ({self.status}) - ₹{self.total_amount}"


class EstimationQuotationItem(models.Model):
    quotation = models.ForeignKey(
        EstimationQuotation,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="quotation_id",
        null=True,
        blank=True,
    )
    service_id = models.BigIntegerField(null=True, blank=True)
    catalog_service_id = models.CharField(max_length=100, blank=True, null=True)
    service_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, null=True, blank=True)
    unit = models.CharField(max_length=50, blank=True, null=True, default="unit")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, null=True, blank=True)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_estimationquotationitem"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.service_name} x {self.quantity} = ₹{self.line_total}"
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
