"""
workforce-app/backend/service_requests/models.py
ServiceRequest model pointing to shared Supabase table service_requests_servicerequest (managed=False).
"""
from decimal import Decimal
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
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_service"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name} ({self.category.name if self.category else 'No Category'})"


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
        # Relocation / Packers & Movers legs
        ASSIGNED        = "ASSIGNED",        "Assigned"
        TEAM_EN_ROUTE   = "TEAM_EN_ROUTE",   "Team En Route"
        ARRIVED_PICKUP  = "ARRIVED_PICKUP",  "Arrived at Pickup"
        PACKING         = "PACKING",         "Packing"
        DISMANTLING     = "DISMANTLING",     "Dismantling"
        IN_TRANSIT      = "IN_TRANSIT",      "In Transit"
        ARRIVED_DROP    = "ARRIVED_DROP",    "Arrived at Drop"
        REASSEMBLY      = "REASSEMBLY",      "Reassembly"
        UNPACKING       = "UNPACKING",       "Unpacking"
        COMPLETED       = "COMPLETED",       "Completed"

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
        null=True, blank=True,
        related_name="service_requests_as_customer",
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
    # X-04: was FloatField, which silently mismatched the shared table's
    # actual NUMERIC(9,6) column (see Customer/backend/service_requests/
    # migrations/0030_servicerequest_latitude_servicerequest_longitude_and_more.py).
    # This model is managed=False (mirrors the Customer app's table), so this
    # is a Python-side type correction only -- no DB schema change, no new
    # migration, and no existing location data is touched.
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    preferred_date = models.DateField(null=True, blank=True)
    preferred_time = models.CharField(max_length=50, blank=True, null=True)
    photo = models.ImageField(upload_to="service_requests/photos/", null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cart_data = models.JSONField(default=list, blank=True)

    drop_address = models.TextField(blank=True, default="")
    # GT-D-02: the drop point's coordinates. `drop_address` is free text, so
    # without these the driver app could name the destination but not
    # navigate to it, and this app could not compute anything about the
    # second half of a trip.
    #
    # DEPLOY ORDER (hard requirement): these mirror columns added by the
    # Customer app's migration 0065_servicerequest_drop_latitude_and_more.
    # That migration must be applied to the shared database BEFORE this
    # app is deployed with these fields -- Django selects every concrete
    # field on the model, so shipping this against a database that lacks
    # the columns breaks every ServiceRequest query in this app, not just
    # logistics ones. 0065 is purely additive (two nullable DecimalFields)
    # and safe to apply on its own ahead of the rest.
    drop_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    drop_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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
    # X-04: were missing -- this app's own request_id auto-numbering only
    # makes sense in the context of what KIND of request it is, and quote
    # jobs are a first-class case the workforce app should be able to see.
    request_kind = models.CharField(max_length=30, default="standard", db_index=True,
                                     choices=[("standard", "Standard"),
                                              ("inspection", "Inspection"),
                                              ("quoted_work", "Quoted Work")])
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
    technician_name = models.CharField(max_length=200, blank=True, default="")
    technician_phone = models.CharField(max_length=50, blank=True, default="")
    technician_photo = models.CharField(max_length=500, blank=True, default="")
    # X-04: were missing from this mirror -- this is exactly the field pair
    # a technician's own live-location update would need to write to, and
    # this app previously had no way to set them via its ORM at all.
    technician_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    technician_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
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
        try:
            proof = getattr(self, "post_service_proof", None)
        except Exception:
            proof = None
        if not proof:
            from workforce_api.models import PostServiceProof
            try:
                proof = PostServiceProof.objects.filter(job=self).first()
            except Exception:
                proof = None

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

        # 5. Check TripStops (Multi-Stop GT deliveries)
        # A booking with TripStops cannot become COMPLETED until every required stop has completed_at.
        try:
            from service_requests.models import TripStop
            stops = TripStop.objects.filter(service_request=self)
            if stops.exists():
                incomplete_stops = [s for s in stops if s.completed_at is None]
                if incomplete_stops:
                    stop_descs = [f"Stop #{getattr(s, 'sequence', '?')} ({getattr(s, 'stop_type', 'STOP')})" for s in incomplete_stops]
                    pending_dependencies.append(
                        f"Required trip stops have not been completed: {', '.join(stop_descs)}."
                    )
        except Exception as e:
            pass

        is_ready = len(pending_dependencies) == 0
        reason = "Ready for completion." if is_ready else f"Cannot complete ServiceRequest: {'; '.join(pending_dependencies)}"
        return is_ready, reason, pending_dependencies


RequestKind = ServiceRequest.RequestKind


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


class TripStop(models.Model):
    """
    GT-D-01/GT-D-02: unmanaged mirror of the Customer app's
    service_requests.TripStop (same shared table,
    service_requests_trip_stop). Read by the driver app so a technician can
    see the actual stop list on a multi-stop trip, and written by it to
    record per-stop arrival/completion.

    Until this existed the vendor side had ZERO references to TripStop
    anywhere -- multi-stop routes were customer-side-only data that
    nothing on the driver side could see or advance, which is why "which
    stop is the driver at" did not exist as a concept in the platform.
    """
    class StopType(models.TextChoices):
        PICKUP   = "PICKUP",   "Pickup"
        WAYPOINT = "WAYPOINT", "Intermediate Stop"
        DROP     = "DROP",     "Drop"

    booking       = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="trip_stops")
    sequence      = models.PositiveSmallIntegerField()
    stop_type     = models.CharField(max_length=10, choices=StopType.choices, default=StopType.WAYPOINT)
    address       = models.TextField()
    contact_name  = models.CharField(max_length=200, blank=True, default="")
    contact_phone = models.CharField(max_length=20, blank=True, default="")
    latitude      = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude     = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    notes         = models.CharField(max_length=500, blank=True, default="")
    created_at    = models.DateTimeField(auto_now_add=True)
    arrived_at    = models.DateTimeField(null=True, blank=True)
    completed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "service_requests_trip_stop"
        ordering = ["booking", "sequence"]

    def __str__(self):
        return f"Stop {self.sequence} ({self.stop_type}) for booking #{self.booking_id}"


class DeliveryProof(models.Model):
    """
    GT-D-01: unmanaged mirror of the Customer app's
    service_requests.DeliveryProof (same shared table,
    service_requests_delivery_proof).

    The driver app does not write here directly -- proof capture goes
    through the Customer app's webhook receiver so that one code path owns
    validation, stop resolution and the "never raise into the webhook"
    guarantee. This mirror exists so the vendor side can READ back what
    was recorded (a technician reviewing their own completed job, an admin
    investigating a delivery dispute) without a cross-service call.
    """
    class ProofType(models.TextChoices):
        PHOTO          = "PHOTO",          "Photo of delivered goods"
        SIGNATURE      = "SIGNATURE",      "Recipient signature"
        RECIPIENT_NAME = "RECIPIENT_NAME", "Recipient name captured"
        OTP            = "OTP",            "Delivery OTP verified"
        NOTE           = "NOTE",           "Driver note"

    booking     = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="delivery_proofs")
    stop        = models.ForeignKey(TripStop, on_delete=models.SET_NULL, null=True, blank=True, related_name="delivery_proofs")
    proof_type  = models.CharField(max_length=20, choices=ProofType.choices)
    image       = models.CharField(max_length=255, blank=True, default="")
    recipient_name  = models.CharField(max_length=200, blank=True, default="")
    recipient_phone = models.CharField(max_length=30, blank=True, default="")
    notes       = models.TextField(blank=True, default="")
    captured_by_name = models.CharField(max_length=200, blank=True, default="")
    captured_by_workforce_id = models.CharField(max_length=64, blank=True, default="")
    latitude    = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    captured_at = models.DateTimeField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "service_requests_delivery_proof"
        ordering = ["booking", "captured_at", "id"]

    def __str__(self):
        return f"{self.get_proof_type_display()} for booking #{self.booking_id}"



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
