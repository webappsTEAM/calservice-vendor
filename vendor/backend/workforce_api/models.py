"""
workforce-app/backend/workforce_api/models.py
Relational database models for Workforce Scheduling, Skills, Compliance, Notifications, Events, Payroll, and Reports.
"""
import uuid
from django.conf import settings
from django.db import models


class WorkforceEmployeeSchedule(models.Model):
    class DayOfWeek(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="schedules",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employee_schedules",
    )
    day_of_week = models.IntegerField(choices=DayOfWeek.choices, db_index=True)
    start_time = models.TimeField(default="09:00:00")
    end_time = models.TimeField(default="18:00:00")
    is_working_day = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_employee_schedule"
        unique_together = ("employee", "day_of_week")
        ordering = ["day_of_week"]

    def __str__(self):
        return f"{self.employee} - Day {self.day_of_week} ({self.start_time}-{self.end_time})"


class WorkforceSkill(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="skills",
    )
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, blank=True)
    category = models.CharField(max_length=100, blank=True, default="General")
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_skill"
        unique_together = ("company", "name")
        ordering = ["category", "name"]

    def __str__(self):
        return f"{self.name} ({self.category})"


class WorkforceServiceCatalog(models.Model):
    category = models.CharField(max_length=150, db_index=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    duration_minutes = models.IntegerField(default=60)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_service_catalog"
        ordering = ["category", "name"]

    def __str__(self):
        return f"[{self.id}] {self.category} - {self.name} (${self.price})"


class WorkforceEmployeeSkill(models.Model):
    class ProficiencyLevel(models.TextChoices):
        BEGINNER = "BEGINNER", "Beginner"
        INTERMEDIATE = "INTERMEDIATE", "Intermediate"
        EXPERT = "EXPERT", "Expert"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="skills",
    )
    skill = models.ForeignKey(
        WorkforceSkill,
        on_delete=models.CASCADE,
        related_name="employee_skills",
    )
    proficiency_level = models.CharField(
        max_length=20,
        choices=ProficiencyLevel.choices,
        default=ProficiencyLevel.INTERMEDIATE,
    )
    is_verified = models.BooleanField(default=False, db_index=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_employee_skill"
        unique_together = ("employee", "skill")

    def __str__(self):
        return f"{self.employee} - {self.skill.name} ({self.proficiency_level})"


class WorkforceRequiredDocument(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="required_documents",
    )
    title = models.CharField(max_length=150)
    category = models.CharField(max_length=100, db_index=True)
    is_mandatory = models.BooleanField(default=True, db_index=True)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    # GT-A-02: which job service categories this requirement applies to (e.g.
    # ["mini_truck", "two_wheeler_delivery", "packers_movers"]). Empty list
    # (the default) preserves the original behaviour -- applies to every job,
    # exactly as every existing row already does. Only non-empty lists scope
    # a requirement (e.g. Driving Licence / RC / Insurance / Permit) to
    # specific categories, so Gate 3 can require vehicle documents only for
    # jobs that actually need a vehicle, without touching the blanket
    # documents (ID proof, etc.) that already apply to everyone.
    applies_to_categories = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "workforce_required_document"
        unique_together = ("company", "category")
        ordering = ["category", "title"]

    def __str__(self):
        return f"{self.title} ({'Mandatory' if self.is_mandatory else 'Optional'})"


class WorkforceEmployeeDocument(models.Model):
    class DocumentStatus(models.TextChoices):
        MISSING = "MISSING", "Missing"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="documents",
    )
    requirement = models.ForeignKey(
        WorkforceRequiredDocument,
        on_delete=models.CASCADE,
        related_name="employee_documents",
    )
    document_number = models.CharField(max_length=100, blank=True, default="")
    file_url = models.CharField(max_length=500, blank=True, default="")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING_REVIEW,
        db_index=True,
    )
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    history_log = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_employee_document"
        unique_together = ("requirement", "employee")

    def __str__(self):
        return f"{self.employee} - {self.requirement.title} ({self.status})"

    def get_computed_status(self):
        if self.status == self.DocumentStatus.REJECTED:
            return self.DocumentStatus.REJECTED
        if self.status == self.DocumentStatus.PENDING_REVIEW:
            return self.DocumentStatus.PENDING_REVIEW
        if self.expiry_date:
            from django.utils import timezone
            today = timezone.now().date()
            if self.expiry_date < today:
                return self.DocumentStatus.EXPIRED
        return self.status


class WorkforceComplianceRequirement(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="compliance_requirements",
    )
    title = models.CharField(max_length=150)
    is_mandatory = models.BooleanField(default=True, db_index=True)
    validity_days = models.IntegerField(default=365)
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_compliance_requirement"
        unique_together = ("company", "title")

    def __str__(self):
        return f"{self.title} (Mandatory: {self.is_mandatory})"


class WorkforceEmployeeCompliance(models.Model):
    class ComplianceStatus(models.TextChoices):
        MISSING = "MISSING", "Missing"
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Review"
        VALID = "VALID", "Valid"
        EXPIRING = "EXPIRING", "Expiring Soon"
        EXPIRED = "EXPIRED", "Expired"
        REJECTED = "REJECTED", "Rejected"

    requirement = models.ForeignKey(
        WorkforceComplianceRequirement,
        on_delete=models.CASCADE,
        related_name="employee_records",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="compliance_records",
    )
    document_number = models.CharField(max_length=100, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=ComplianceStatus.choices,
        default=ComplianceStatus.VALID,
        db_index=True,
    )
    file_url = models.CharField(max_length=500, blank=True, default="")
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_employee_compliance"
        unique_together = ("requirement", "employee")

    def __str__(self):
        return f"{self.employee} - {self.requirement.title} ({self.status})"

    def get_computed_status(self):
        if self.status == self.ComplianceStatus.REJECTED:
            return self.ComplianceStatus.REJECTED
        if self.status == self.ComplianceStatus.PENDING_REVIEW:
            return self.ComplianceStatus.PENDING_REVIEW
        if self.expiry_date:
            from django.utils import timezone
            today = timezone.now().date()
            if self.expiry_date < today:
                return self.ComplianceStatus.EXPIRED
            elif (self.expiry_date - today).days <= 30:
                return self.ComplianceStatus.EXPIRING
        return self.ComplianceStatus.VALID


class WorkforceNotification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        db_index=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=100, db_index=True)
    related_object_id = models.CharField(max_length=100, blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return f"To {self.recipient.username}: {self.title}"


class WorkforcePayPeriod(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PROCESSING = "PROCESSING", "Processing"
        REVIEW = "REVIEW", "In Review"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="pay_periods",
    )
    name = models.CharField(max_length=150)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_pay_period"
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.name} ({self.status})"


class WorkforcePayslip(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PROCESSING = "PROCESSING", "Processing"
        REVIEW = "REVIEW", "In Review"
        APPROVED = "APPROVED", "Approved"
        PAID = "PAID", "Paid"

    pay_period = models.ForeignKey(
        WorkforcePayPeriod,
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="payslips",
    )
    base_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    job_earnings = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    adjustments = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_pay = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_payslip"
        unique_together = ("pay_period", "employee")

    def __str__(self):
        return f"Payslip {self.employee} - {self.pay_period.name} (${self.net_pay})"


class WorkforceJobOffer(models.Model):
    class Status(models.TextChoices):
        OFFERED = "OFFERED", "Offered"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        DECLINED = "DECLINED", "Declined"
        EXPIRED = "EXPIRED", "Expired"
        SUPERSEDED = "SUPERSEDED", "Superseded"
        SUPERSEDED_BY_ACCEPTANCE = "SUPERSEDED_BY_ACCEPTANCE", "Superseded by Acceptance"
        CANCELLED = "CANCELLED", "Cancelled"

    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="job_offers",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="job_offers",
    )
    status = models.CharField(
        max_length=50,
        choices=Status.choices,
        default=Status.OFFERED,
        db_index=True,
    )
    rank_score = models.FloatField(default=0.0)
    wave_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    wave_number = models.IntegerField(default=1, db_index=True)
    offered_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "workforce_job_offer"
        ordering = ["-offered_at"]

    def __str__(self):
        return f"Offer Job #{self.job_id} to {self.employee} ({self.status})"


class WorkforceJobLifecycleEvent(models.Model):
    """
    Immutable audit event for workforce job state transitions.
    """
    class EventType(models.TextChoices):
        EMPLOYEE_JOB_ACCEPTED = "EMPLOYEE_JOB_ACCEPTED", "Employee Job Accepted"
        EMPLOYEE_JOB_CANCELLED = "EMPLOYEE_JOB_CANCELLED", "Employee Job Cancelled"
        EMPLOYEE_JOB_REDISPATCH_STARTED = "EMPLOYEE_JOB_REDISPATCH_STARTED", "Employee Job Redispatch Started"
        NEW_EMPLOYEE_ASSIGNED = "NEW_EMPLOYEE_ASSIGNED", "New Employee Assigned"

    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="lifecycle_events",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_lifecycle_events",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_lifecycle_events",
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="actor_job_lifecycle_events",
    )
    event_type = models.CharField(max_length=50, choices=EventType.choices, db_index=True)
    previous_status = models.CharField(max_length=50, blank=True, default="")
    new_status = models.CharField(max_length=50, blank=True, default="")
    accepted_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_deadline = models.DateTimeField(null=True, blank=True)
    reason_code = models.CharField(max_length=50, blank=True, default="")
    reason_text = models.TextField(blank=True, default="")
    cancellation_window_seconds = models.IntegerField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_job_lifecycle_event"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} for Job #{self.job_id} by {self.actor_user_id} at {self.created_at}"


class PreServiceVerification(models.Model):
    job = models.OneToOneField(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="pre_service_verification",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="pre_service_verifications",
    )
    geofence_passed = models.BooleanField(default=False)
    arrival_lat = models.FloatField(null=True, blank=True)
    arrival_lon = models.FloatField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)

    presence_photo = models.FileField(upload_to="pre_service/presence/", null=True, blank=True)
    appliance_photo = models.FileField(upload_to="pre_service/appliance/", null=True, blank=True)
    work_area_photo = models.FileField(upload_to="pre_service/work_area/", null=True, blank=True)

    otp_code = models.CharField(max_length=6, default="")
    otp_generated_at = models.DateTimeField(null=True, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.IntegerField(default=0)
    otp_verified = models.BooleanField(default=False)
    otp_verified_at = models.DateTimeField(null=True, blank=True)

    is_complete = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_pre_service_verification"

    def check_completion(self):
        ready = bool(
            self.geofence_passed
            and self.otp_verified
            and self.presence_photo
        )
        self.is_complete = ready
        if ready and not self.completed_at:
            from django.utils import timezone
            self.completed_at = timezone.now()
        return self.is_complete


    def __str__(self):
        return f"PreService Verification Job #{self.job_id} (Complete: {self.is_complete})"


class WorkforceWorkExtension(models.Model):
    class Status(models.TextChoices):
        REQUESTED          = "REQUESTED",          "Requested"
        ADMIN_APPROVED     = "ADMIN_APPROVED",     "Admin Approved"
        ADMIN_REJECTED     = "ADMIN_REJECTED",     "Admin Rejected"
        PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT", "Pending Assignment"
        CUSTOMER_ACCEPTED  = "CUSTOMER_ACCEPTED",  "Customer Accepted"
        CUSTOMER_DECLINED  = "CUSTOMER_DECLINED",  "Customer Declined"
        IN_PROGRESS        = "IN_PROGRESS",        "In Progress"
        COMPLETED          = "COMPLETED",          "Completed"
        RESOLVED           = "RESOLVED",           "Resolved"

    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="work_extensions",
    )
    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="work_extensions",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="work_extensions",
        null=True,
        blank=True,
    )
    title = models.CharField(max_length=200, default="Scope Extension")
    description = models.TextField(blank=True, default="")
    reason = models.TextField()

    estimated_labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estimated_materials_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    requested_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    approved_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_customer_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    requires_specialist = models.BooleanField(default=False)
    required_skill = models.ForeignKey(
        WorkforceSkill,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extensions",
    )
    specialist_technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="specialist_assigned_extensions",
    )
    specialist_job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="specialist_parent_extension",
    )
    is_critical = models.BooleanField(default=False)

    decision_token = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    decision_expires_at = models.DateTimeField(null=True, blank=True)

    supporting_notes = models.TextField(blank=True, default="")
    supporting_photo = models.FileField(upload_to="work_extensions/photos/", null=True, blank=True)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )

    admin_reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_extensions",
    )
    admin_review_reason = models.TextField(blank=True, default="")
    admin_reviewed_at = models.DateTimeField(null=True, blank=True)

    customer_decided_at = models.DateTimeField(null=True, blank=True)
    customer_decline_reason = models.TextField(blank=True, default="")

    completed_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_work_extension"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Extension #{self.id} for Job #{self.job_id}: {self.title} ({self.status})"


class WorkforceSupplementalInvoice(models.Model):
    class Status(models.TextChoices):
        ISSUED    = "ISSUED",    "Issued"
        PAID      = "PAID",      "Paid"
        CANCELLED = "CANCELLED", "Cancelled"

    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)
    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="supplemental_invoices",
    )
    extension = models.OneToOneField(
        WorkforceWorkExtension,
        on_delete=models.CASCADE,
        related_name="supplemental_invoice",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="supplemental_invoices",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="supplemental_invoices",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ISSUED,
        db_index=True,
    )
    payment_method = models.CharField(max_length=20, default="COD")
    transaction_id = models.CharField(max_length=200, blank=True, null=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    audit_trail = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_supplemental_invoice"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Supplemental Invoice {self.invoice_number} (₹{self.amount} - {self.status})"


class WorkforceJobReschedule(models.Model):
    class DelayType(models.TextChoices):
        PARTS_DELAY      = "PARTS_DELAY",      "Parts Delay"
        SPECIALIST_DELAY = "SPECIALIST_DELAY", "Specialist Delay"
        CUSTOMER_REQUEST = "CUSTOMER_REQUEST", "Customer Request"
        WEATHER_ACCESS   = "WEATHER_ACCESS",   "Weather/Access Issue"
        OTHER            = "OTHER",            "Other"

    class CustomerResponse(models.TextChoices):
        PENDING            = "PENDING",            "Pending"
        ACCEPTED           = "ACCEPTED",           "Accepted"
        OBJECTED           = "OBJECTED",           "Objected"
        CALLBACK_REQUESTED = "CALLBACK_REQUESTED", "Callback Requested"

    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="reschedules",
    )
    delay_count = models.IntegerField(default=1)
    delay_type = models.CharField(max_length=30, choices=DelayType.choices, default=DelayType.PARTS_DELAY)
    original_date = models.DateField(null=True, blank=True)
    rescheduled_date = models.DateField(null=True, blank=True)
    reason = models.TextField()
    customer_notified = models.BooleanField(default=True)
    escalated_to_support = models.BooleanField(default=False)
    escalation_notes = models.TextField(blank=True, default="")
    customer_response = models.CharField(max_length=30, choices=CustomerResponse.choices, default=CustomerResponse.PENDING)
    customer_notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_job_reschedule"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Reschedule #{self.id} for Job #{self.job_id} (Delay #{self.delay_count} - Escalated: {self.escalated_to_support})"


class PostServiceProof(models.Model):
    job = models.OneToOneField(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="post_service_proof",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="post_service_proofs",
    )
    after_presence_photo = models.FileField(upload_to="post_service/presence/", null=True, blank=True)
    after_appliance_photo = models.FileField(upload_to="post_service/appliance/", null=True, blank=True)
    after_work_area_photo = models.FileField(upload_to="post_service/work_area/", null=True, blank=True)
    completion_notes = models.TextField(blank=True, default="")
    parts_used = models.JSONField(default=list, blank=True)

    is_submitted = models.BooleanField(default=False, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_post_service_proof"

    def check_submission(self):
        ready = bool(
            self.after_presence_photo or self.after_appliance_photo or self.after_work_area_photo
        )
        if ready and not self.is_submitted:
            from django.utils import timezone
            self.is_submitted = True
            self.submitted_at = timezone.now()
        return self.is_submitted

    def __str__(self):
        return f"PostService Proof Job #{self.job_id} (Submitted: {self.is_submitted})"


class WorkforceEmployeeChangeRequest(models.Model):
    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Pending Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="change_requests",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="employee_change_requests",
        null=True,
        blank=True,
    )
    field_name = models.CharField(max_length=100, db_index=True)
    field_label = models.CharField(max_length=150, default="")
    old_value = models.TextField(blank=True, default="")
    new_value = models.TextField()
    reason = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    admin_notes = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_change_requests",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_employee_change_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ChangeRequest #{self.id} for {self.employee}: {self.field_label} ({self.status})"


class WorkforceUserPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workforce_preference",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_preferences",
    )
    theme = models.CharField(max_length=20, default="light")
    accent_color = models.CharField(max_length=30, default="blue")
    layout_density = models.CharField(max_length=20, default="comfortable")
    font_size = models.CharField(max_length=20, default="medium")
    high_contrast = models.BooleanField(default=False)
    reduced_motion = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_user_preference"

    def __str__(self):
        return f"Preferences for {self.user.username} ({self.theme}/{self.accent_color})"


class WorkforceNotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workforce_notification_preference",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="user_notification_preferences",
    )
    security_alerts = models.BooleanField(default=True)
    login_alerts = models.BooleanField(default=True)
    leave_updates = models.BooleanField(default=True)
    job_assignments = models.BooleanField(default=True)
    shift_reminders = models.BooleanField(default=True)
    payroll_notifications = models.BooleanField(default=True)
    weekly_digest = models.BooleanField(default=True)
    product_updates = models.BooleanField(default=False)
    workspace_announcements = models.BooleanField(default=True)
    channel_email = models.BooleanField(default=True)
    channel_in_app = models.BooleanField(default=True)
    channel_sms = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_notification_preference"

    def __str__(self):
        return f"Notification Preferences for {self.user.username}"


class WorkforceJobFeedback(models.Model):
    job = models.OneToOneField(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="feedback_review",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="customer_feedbacks",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workforce_feedbacks_given",
    )
    rating = models.IntegerField(default=5)
    review = models.TextField(blank=True, default="")
    csat_score = models.IntegerField(default=5)
    resolution_ontime = models.BooleanField(default=True)
    customer_name = models.CharField(max_length=150, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_job_feedback"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Feedback for Job #{self.job_id} - {self.rating} Stars ({self.employee})"


class WorkforceEventLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="workforce_event_logs",
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=100, db_index=True)
    payload = models.JSONField(default=dict, blank=True)
    ip_address = models.CharField(max_length=50, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_event_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} at {self.created_at}"


class EmployeeSavedLocation(models.Model):
    """Employee-owned personal saved locations (home, work, favourite spot, etc.).

    Strictly separate from:
      - time_tracking.Location  (company-controlled authorized geofence)
      - User.last_known_location  (live device GPS, updated automatically)
      - ServiceRequest.latitude/longitude  (customer job coordinates, read-only later)
    """

    LABEL_CHOICES = [
        ("home", "Home"),
        ("work", "Work"),
        ("other", "Other"),
    ]

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="saved_locations",
    )
    label = models.CharField(max_length=50, choices=LABEL_CHOICES, default="other")
    name = models.CharField(max_length=255)
    address = models.TextField(blank=True)
    locality = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    landmark = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_employee_saved_location"
        ordering = ["-is_default", "-created_at"]

    def __str__(self):
        return f"{self.employee_id} — {self.name} ({self.label})"


class JobTrackingSession(models.Model):
    """
    Tracks an active en-route / on-site trip for an assigned job.
    Enforces one active tracking session per job.
    """
    class SessionStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="job_tracking_sessions",
    )
    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="tracking_sessions",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="tracking_sessions",
    )
    status = models.CharField(
        max_length=20,
        choices=SessionStatus.choices,
        default=SessionStatus.ACTIVE,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    # Latest telemetry snapshot
    last_latitude = models.FloatField(null=True, blank=True)
    last_longitude = models.FloatField(null=True, blank=True)
    last_accuracy = models.FloatField(null=True, blank=True)
    last_speed = models.FloatField(null=True, blank=True)
    last_heading = models.FloatField(null=True, blank=True)
    last_captured_at = models.DateTimeField(null=True, blank=True)
    last_received_at = models.DateTimeField(null=True, blank=True)

    # Consecutive arrival confirmation tracking
    consecutive_arrival_fixes = models.IntegerField(default=0)
    last_fix_lat = models.FloatField(null=True, blank=True)
    last_fix_lon = models.FloatField(null=True, blank=True)
    last_fix_time = models.DateTimeField(null=True, blank=True)

    # Spatial & Geofence movement state
    movement_status = models.CharField(max_length=50, default="UNKNOWN")
    geofence_status = models.CharField(max_length=50, default="OUTSIDE")
    prev_latitude = models.FloatField(null=True, blank=True)
    prev_longitude = models.FloatField(null=True, blank=True)
    prev_captured_at = models.DateTimeField(null=True, blank=True)
    last_event_emitted_at = models.DateTimeField(null=True, blank=True)
    last_event_state_key = models.CharField(max_length=100, default="", blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_job_tracking_session"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["employee", "status"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["job"],
                condition=models.Q(status="ACTIVE"),
                name="unique_active_tracking_session_per_job",
            ),
        ]

    def __str__(self):
        return f"Tracking Session #{self.id} (Job #{self.job_id}, Emp #{self.employee_id}, {self.status})"


class JobLocationPoint(models.Model):
    """
    Throttled historical GPS telemetry points along an active trip.
    Persisted on meaningful movement (>20m) or interval (>30s) or lifecycle transitions.
    """
    tracking_session = models.ForeignKey(
        JobTrackingSession,
        on_delete=models.CASCADE,
        related_name="location_points",
    )
    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="telemetry_points",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="telemetry_points",
    )
    latitude = models.FloatField()
    longitude = models.FloatField()
    accuracy = models.FloatField(null=True, blank=True)
    speed = models.FloatField(null=True, blank=True)
    heading = models.FloatField(null=True, blank=True)
    captured_at = models.DateTimeField(db_index=True)
    received_at = models.DateTimeField(auto_now_add=True)
    sequence_number = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_job_location_point"
        ordering = ["tracking_session", "sequence_number", "created_at"]
        indexes = [
            models.Index(fields=["tracking_session", "created_at"]),
            models.Index(fields=["job", "created_at"]),
        ]

    def __str__(self):
        return f"Point #{self.sequence_number} for Session #{self.tracking_session_id} ({self.latitude}, {self.longitude})"


class JobPayment(models.Model):
    """
    Authoritative Payment State Machine Model for Workforce Jobs.
    Maintains separate lifecycle from GPS dispatch, travel, and arrival.
    Supports ONLINE (gateway-verified) and CASH_ON_SERVICE (with dual confirmation: Direct or separate Payment OTP).
    """
    class PaymentMethod(models.TextChoices):
        ONLINE = "ONLINE", "Online Payment"
        CASH_ON_SERVICE = "CASH_ON_SERVICE", "Cash on Service"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        AUTHORIZED = "AUTHORIZED", "Authorized"
        PAID = "PAID", "Paid"
        CASH_PENDING = "CASH_PENDING", "Cash Collection Pending"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"
        CANCELLED = "CANCELLED", "Cancelled"

    job = models.OneToOneField(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="payment_record",
        unique=True,
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="job_payments",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="job_payments",
    )
    payment_method = models.CharField(
        max_length=30,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH_ON_SERVICE,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    amount_due = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
    )
    amount_received = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    change_returned = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    currency = models.CharField(
        max_length=10,
        default="INR",
    )
    gateway_transaction_id = models.CharField(
        max_length=200,
        blank=True,
        null=True,
    )
    cash_collected_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    cash_collected_by = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collected_payments",
    )
    customer_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    customer_confirmation_method = models.CharField(
        max_length=50,
        blank=True,
        default="",
    )
    # Hashed OTP storage using Django make_password / check_password (never plaintext)
    payment_confirmation_otp_hash = models.CharField(
        max_length=256,
        blank=True,
        null=True,
    )
    otp_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    otp_attempts = models.IntegerField(
        default=0,
    )
    otp_used_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    # GT-C-02: "cash collected by a driver is never reconciled". PAID
    # CASH_ON_SERVICE rows sit here forever with nothing tracking whether the
    # technician has actually handed that cash to the office. reconciled
    # flips True (and reconciled_in points at the CashSettlement) the moment
    # this payment is included in a settlement -- see
    # CashSettlement/compute_outstanding_cash in services/__init__.py.
    reconciled = models.BooleanField(default=False, db_index=True)
    reconciled_in = models.ForeignKey(
        "CashSettlement",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reconciled_payments",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_job_payment"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "payment_status"]),
            models.Index(fields=["employee", "payment_status"]),
            models.Index(fields=["company", "payment_status"]),
        ]

    def __str__(self):
        return f"Payment #{self.id} for Job #{self.job_id} ({self.payment_method} - {self.payment_status} - ₹{self.amount_due})"


class CashSettlement(models.Model):
    """
    GT-C-02: a single "technician handed in cash" event. expected_amount is
    computed at creation time from every unreconciled PAID CASH_ON_SERVICE
    JobPayment for this employee (see
    services.compute_outstanding_cash) -- discrepancy is what actually
    surfaces a shortfall/overage instead of it silently going unnoticed.
    """
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="cash_settlements",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="cash_settlements",
    )
    expected_amount = models.DecimalField(max_digits=10, decimal_places=2)
    deposited_amount = models.DecimalField(max_digits=10, decimal_places=2)
    discrepancy = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cash_settlements_recorded",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_cash_settlement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Settlement #{self.id} for Employee #{self.employee_id}: expected {self.expected_amount}, deposited {self.deposited_amount}"


class PaymentCollectionEvent(models.Model):
    """
    Immutable Audit Trail for all Payment & Cash Collection Lifecycle Events.
    """
    class EventType(models.TextChoices):
        PAYMENT_CREATED = "PAYMENT_CREATED", "Payment Record Created"
        PAYMENT_PENDING = "PAYMENT_PENDING", "Payment Pending"
        CASH_COLLECTION_STARTED = "CASH_COLLECTION_STARTED", "Cash Collection Started"
        CASH_REPORTED = "CASH_REPORTED", "Cash Collection Reported"
        CUSTOMER_CONFIRMATION_SENT = "CUSTOMER_CONFIRMATION_SENT", "Customer Confirmation Sent"
        CUSTOMER_CONFIRMED = "CUSTOMER_CONFIRMED", "Customer Confirmed Payment"
        CASH_COLLECTED = "CASH_COLLECTED", "Cash Collected"
        PAYMENT_PAID = "PAYMENT_PAID", "Payment Marked Paid"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment Failed"
        PAYMENT_REFUNDED = "PAYMENT_REFUNDED", "Payment Refunded"
        PAYMENT_DISPUTED = "PAYMENT_DISPUTED", "Payment Disputed by Customer"

    job_payment = models.ForeignKey(
        JobPayment,
        on_delete=models.CASCADE,
        related_name="events",
    )
    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    actor_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    event_type = models.CharField(
        max_length=50,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_payment_collection_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job_payment", "created_at"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self):
        return f"PaymentEvent #{self.id} ({self.event_type}) for Payment #{self.job_payment_id}"


class Vehicle(models.Model):
    """
    GT-A-01: a driver is currently modeled as "an Employee with a job title" --
    there is no vehicle at all: no type, no registration number, no capacity.
    This is the minimal vehicle record needed for goods/transport dispatch and
    document-expiry gating (insurance, permit, PUC), without inventing a full
    fleet-management module the product hasn't asked for.
    """
    class VehicleType(models.TextChoices):
        TWO_WHEELER   = "two_wheeler",   "Two Wheeler"
        THREE_WHEELER = "three_wheeler", "Three Wheeler / Auto"
        MINI_TRUCK    = "mini_truck",    "Mini Truck"
        PICKUP        = "pickup",        "Pickup Van"
        TRUCK         = "truck",         "Truck"
        OTHER         = "other",         "Other"

    employee = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="vehicles",
    )
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.OTHER)
    registration_number = models.CharField(max_length=30, db_index=True)
    capacity_kg = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    capacity_label = models.CharField(max_length=50, blank=True, default="")

    # Document expiry -- checked the same way employee documents already are
    # (see automatic_dispatch.py Gate 3), but vehicle documents are properties
    # of the vehicle, not the person, so they live here rather than being
    # forced into WorkforceEmployeeDocument.
    insurance_expiry = models.DateField(null=True, blank=True)
    permit_expiry = models.DateField(null=True, blank=True)
    puc_expiry = models.DateField(null=True, blank=True)
    rc_verified = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vehicle"
        unique_together = ("company", "registration_number")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.registration_number} ({self.get_vehicle_type_display()})"

    def is_document_current(self, as_of=None):
        """True only if every expiry this vehicle has on file is still valid.
        A vehicle with no expiry dates recorded at all returns True -- absence
        of data is not treated as expiry, matching how WorkforceEmployeeDocument
        expiry checks already behave (missing expiry_date never fails Gate 3)."""
        from django.utils import timezone as _tz
        today = as_of or _tz.now().date()
        for d in (self.insurance_expiry, self.permit_expiry, self.puc_expiry):
            if d and d < today:
                return False
        return True


# ============================================================================
# SEVO Business Plan implementation -- Wallet infrastructure (Section 1 of
# SEVO_Business_Operational_Plan.docx).
#
# Deliberately NOT a self-issued stored-value instrument (see the plan for
# why: building one would make SEVO an RBI-regulated PPI issuer). These
# models are a ledger view over money that actually sits in a RazorpayX
# nodal/current account. "Wallet balance" shown in-app is computed from
# WalletLedgerEntry rows; the real money movement happens through
# WithdrawalRequest -> RazorpayXPayoutAdapter (workforce_api/services/payouts.py).
# ============================================================================

class WalletAccount(models.Model):
    """
    One ledger account per payee. Two kinds:
      - PROVIDER_HEAD: one per Company (provider business) -- every job any
        worker on that provider's team completes credits this single
        account (the "head wallet" from the operational brief).
      - INDIVIDUAL_WORKER: one per Employee who onboarded directly, with no
        provider umbrella -- credited only by jobs that Employee personally
        completed.
    """

    class AccountType(models.TextChoices):
        PROVIDER_HEAD = "PROVIDER_HEAD", "Provider Head Wallet"
        INDIVIDUAL_WORKER = "INDIVIDUAL_WORKER", "Individual Worker Wallet"

    class KYCTier(models.TextChoices):
        TIER_0_PROVISIONAL = "TIER_0", "Tier 0 - Provisional"
        TIER_1_VERIFIED = "TIER_1", "Tier 1 - Verified"
        TIER_2_TRUSTED = "TIER_2", "Tier 2 - Trusted"

    account_type = models.CharField(max_length=30, choices=AccountType.choices, db_index=True)

    # Exactly one of these is set, matching account_type.
    company = models.OneToOneField(
        "companies.Company", on_delete=models.CASCADE, null=True, blank=True,
        related_name="head_wallet",
    )
    employee = models.OneToOneField(
        "employees.Employee", on_delete=models.CASCADE, null=True, blank=True,
        related_name="individual_wallet",
    )

    kyc_tier = models.CharField(
        max_length=10, choices=KYCTier.choices, default=KYCTier.TIER_0_PROVISIONAL, db_index=True,
    )
    kyc_tier_updated_at = models.DateTimeField(null=True, blank=True)

    # Bank/UPI destination for payouts. Name-match to KYC identity is
    # enforced at onboarding-review time (human review), not re-derived here.
    payout_bank_account_name = models.CharField(max_length=200, blank=True, default="")
    payout_bank_account_number_masked = models.CharField(max_length=50, blank=True, default="")
    payout_ifsc = models.CharField(max_length=20, blank=True, default="")
    payout_upi_id = models.CharField(max_length=100, blank=True, default="")

    # RazorpayX identifiers, populated once the fund account is registered
    # with RazorpayX. Blank until RazorpayX credentials exist and the
    # fund-account-creation step has actually run -- see services/payouts.py.
    razorpayx_contact_id = models.CharField(max_length=100, blank=True, default="")
    razorpayx_fund_account_id = models.CharField(max_length=100, blank=True, default="")

    # Scheduled withdrawals + minimum balance alerts (operational brief,
    # head-wallet specific features).
    auto_withdrawal_enabled = models.BooleanField(default=False)
    auto_withdrawal_frequency = models.CharField(
        max_length=10,
        choices=[("DAILY", "Daily"), ("WEEKLY", "Weekly")],
        blank=True, default="",
    )
    auto_withdrawal_day_of_week = models.IntegerField(
        null=True, blank=True,
        help_text="0=Monday .. 6=Sunday. Only used when frequency=WEEKLY.",
    )
    minimum_balance_alert_threshold = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )
    low_balance_alert_sent_at = models.DateTimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_wallet_account"
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(account_type="PROVIDER_HEAD", company__isnull=False, employee__isnull=True)
                    | models.Q(account_type="INDIVIDUAL_WORKER", employee__isnull=False, company__isnull=True)
                ),
                name="wallet_account_type_matches_owner",
            ),
        ]
        indexes = [
            models.Index(fields=["account_type", "kyc_tier"]),
        ]

    def __str__(self):
        owner = self.company.company_name if self.company_id else (
            getattr(self.employee, "full_name", None) or f"Employee #{self.employee_id}"
        )
        return f"{self.get_account_type_display()} - {owner}"

    def current_balance(self):
        """Sum of RELEASED ledger entries only -- HELD entries (pending
        dispute window, see WalletLedgerEntry.status) are not withdrawable
        yet and must not appear in the balance the owner can act on."""
        from django.db.models import Sum
        result = self.ledger_entries.filter(status=WalletLedgerEntry.Status.RELEASED).aggregate(
            total=Sum("signed_amount")
        )
        return result["total"] or 0

    def withdrawal_limit_for_tier(self):
        """Daily withdrawal ceiling by KYC tier (Section 1 table). This is
        SEVO's own risk policy, not an RBI PPI balance cap -- money is never
        resting in a SEVO-owned instrument, it moves straight to the
        owner's own bank account via RazorpayX."""
        return {
            self.KYCTier.TIER_0_PROVISIONAL: 5000,
            self.KYCTier.TIER_1_VERIFIED: 50000,
            self.KYCTier.TIER_2_TRUSTED: None,  # no platform-imposed cap
        }.get(self.kyc_tier, 5000)


class WalletLedgerEntry(models.Model):
    """
    Immutable, append-only ledger row. Every completed job produces exactly
    one JOB_CREDIT entry (net of commission) plus one COMMISSION_DEBIT entry
    recorded separately for auditability (Section 6: per-job attribution).

    `worker_performed` records who actually did the job even when the
    payee is a provider's head wallet -- captured purely for rating,
    dispute evidence and safety audit trail. It never changes who gets
    paid.
    """

    class EntryType(models.TextChoices):
        JOB_CREDIT = "JOB_CREDIT", "Job Earnings Credit"
        COMMISSION_DEBIT = "COMMISSION_DEBIT", "SEVO Commission"
        WITHDRAWAL_DEBIT = "WITHDRAWAL_DEBIT", "Withdrawal to Bank/UPI"
        CLAWBACK_DEBIT = "CLAWBACK_DEBIT", "Dispute Clawback"
        REFUND_ADJUSTMENT = "REFUND_ADJUSTMENT", "Refund Adjustment"
        PROMO_CREDIT = "PROMO_CREDIT", "Promotional Credit"
        COD_COMMISSION_PAYABLE = "COD_COMMISSION_PAYABLE", "Cash Job Commission Payable"

    class Status(models.TextChoices):
        HELD = "HELD", "Held (dispute window)"
        RELEASED = "RELEASED", "Released (withdrawable)"
        CLAWED_BACK = "CLAWED_BACK", "Clawed back"

    wallet = models.ForeignKey(WalletAccount, on_delete=models.CASCADE, related_name="ledger_entries")
    job = models.ForeignKey(
        "service_requests.ServiceRequest", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="wallet_ledger_entries",
    )
    worker_performed = models.ForeignKey(
        "employees.Employee", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="jobs_performed_ledger_entries",
        help_text="Who actually did the job, independent of which wallet was paid.",
    )

    entry_type = models.CharField(max_length=30, choices=EntryType.choices, db_index=True)
    # Positive for credits, negative for debits -- signed so SUM() gives the
    # balance directly without a CASE expression at every read site.
    signed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    gross_job_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    commission_rate_applied = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True,
        help_text="e.g. 0.1000 for 10%. Recorded per-entry since the rate can change (promo -> standard).",
    )

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RELEASED, db_index=True)
    hold_release_at = models.DateTimeField(
        null=True, blank=True,
        help_text="JOB_CREDIT entries are held until this timestamp (dispute window) before counting toward balance.",
    )

    notes = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_wallet_ledger_entry"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["wallet", "status", "created_at"]),
            models.Index(fields=["job", "entry_type"]),
        ]

    def __str__(self):
        return f"{self.get_entry_type_display()} {self.signed_amount} -> wallet #{self.wallet_id}"


class WithdrawalRequest(models.Model):
    """
    A withdrawal from a WalletAccount's RELEASED balance to the owner's own
    bank account / UPI, via RazorpayX Payouts. See
    workforce_api/services/payouts.py for the adapter that actually talks
    to RazorpayX -- this row tracks the request/response lifecycle so a
    request is never lost if the payout API call fails or times out.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
        AWAITING_RAZORPAYX_ACTIVATION = (
            "AWAITING_RAZORPAYX_ACTIVATION",
            "Awaiting RazorpayX activation",
        )

    wallet = models.ForeignKey(WalletAccount, on_delete=models.CASCADE, related_name="withdrawal_requests")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=35, choices=Status.choices, default=Status.PENDING, db_index=True)
    is_scheduled = models.BooleanField(default=False, help_text="True if triggered by an auto-withdrawal rule rather than an on-demand request.")

    razorpayx_payout_id = models.CharField(max_length=100, blank=True, default="")
    razorpayx_utr = models.CharField(max_length=100, blank=True, default="", help_text="Bank UTR once settled, from RazorpayX webhook.")
    failure_reason = models.CharField(max_length=255, blank=True, default="")

    debit_ledger_entry = models.OneToOneField(
        WalletLedgerEntry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="withdrawal_request",
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workforce_withdrawal_request"
        ordering = ["-requested_at"]
        indexes = [models.Index(fields=["wallet", "status"])]

    def __str__(self):
        return f"Withdrawal #{self.id} - {self.wallet_id} - {self.amount} ({self.status})"


class SocialSecurityRegistration(models.Model):
    """
    Section 8 compliance scaffolding: tracks each individual worker's
    progress toward the Code on Social Security 2020 / 2026 Central Rules
    90-day (single aggregator) / 120-day (multiple aggregators) eligibility
    threshold, and whether SEVO has registered them on the government
    portal. Actual portal submission (Shram Suvidha / e-Shram) is a manual
    external step -- this model gives an accurate, exportable worklist for
    whoever does that submission, not an automated integration with a
    government system SEVO doesn't have API access to.
    """

    class RegistrationStatus(models.TextChoices):
        NOT_YET_ELIGIBLE = "NOT_YET_ELIGIBLE", "Not yet eligible (<90 days)"
        ELIGIBLE_PENDING_REGISTRATION = "ELIGIBLE_PENDING", "Eligible, registration pending"
        REGISTERED = "REGISTERED", "Registered on government portal"

    employee = models.OneToOneField(
        "employees.Employee", on_delete=models.CASCADE, related_name="social_security_registration",
    )
    days_worked_current_fy = models.PositiveIntegerField(default=0)
    financial_year_start = models.DateField()
    status = models.CharField(
        max_length=25, choices=RegistrationStatus.choices,
        default=RegistrationStatus.NOT_YET_ELIGIBLE, db_index=True,
    )
    registered_at = models.DateTimeField(null=True, blank=True)
    registered_by = models.CharField(max_length=150, blank=True, default="", help_text="Admin who submitted the portal registration.")
    portal_reference_id = models.CharField(max_length=100, blank=True, default="")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_social_security_registration"

    def __str__(self):
        return f"{self.employee_id}: {self.days_worked_current_fy}d ({self.status})"


class WorkforceScorecard(models.Model):
    """
    SEVO business plan Section 4 (Job Lifecycle / SLAs): "A missed SLA
    triggers ... a scorecard mark against the provider/worker -- visible
    in their own dashboard, not just used silently against them" and the
    Days 31-60 roadmap item "Rating and SLA scorecards go live and start
    feeding the dispatch-ranking algorithm."

    WorkforceJobFeedback (one row per customer-rated job) is the raw
    signal; this is the persisted, cheap-to-query rollup per employee,
    recalculated via services/scorecards.py whenever new feedback comes
    in. Kept separate (rather than computed live like
    WorkforcePerformanceMeView does for a single employee's own
    dashboard) because automatic_dispatch.py needs to bulk-fetch this for
    every dispatch candidate on every job -- an aggregate query per
    candidate would not scale.

    `resolution_ontime` on WorkforceJobFeedback (customer-reported at
    rating time) is the on-time/SLA-met signal used here -- there is no
    stored arrival/completion duration target per service category in
    this codebase to derive a stricter, non-self-reported breach from.
    """

    class Tier(models.TextChoices):
        UNRATED = "UNRATED", "Unrated"
        BRONZE = "BRONZE", "Bronze"
        SILVER = "SILVER", "Silver"
        GOLD = "GOLD", "Gold"

    employee = models.OneToOneField(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="scorecard",
    )
    rating_count = models.PositiveIntegerField(default=0)
    average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    csat_average = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    sla_met_count = models.PositiveIntegerField(default=0)
    sla_breach_count = models.PositiveIntegerField(default=0)
    sla_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tier = models.CharField(max_length=10, choices=Tier.choices, default=Tier.UNRATED, db_index=True)
    last_recalculated_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_scorecard"

    def __str__(self):
        return f"Scorecard(employee={self.employee_id}) rating={self.average_rating} sla={self.sla_score} tier={self.tier}"


# ─────────────────────────────────────────────────────────────────────────────
# TECHNICIAN-VENDOR NETWORK MODELS
# ─────────────────────────────────────────────────────────────────────────────

class VendorCriteria(models.Model):
    """
    Saved, reusable search/requirement set created by a vendor (Company).
    """
    vendor = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_criteria",
    )
    name = models.CharField(max_length=150)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_criteria"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.vendor.company_name} - {self.name}"


class CriteriaTerm(models.Model):
    """
    Individual attribute condition within a VendorCriteria set.
    Terms with the same group_id are OR'd together. Distinct groups are AND'd together.
    """
    class AttributeType(models.TextChoices):
        SKILL = "SKILL", "Skill"
        SERVICE_CATEGORY = "SERVICE_CATEGORY", "Service Category"
        LOCATION = "LOCATION", "Location / City"
        EXPERIENCE_YEARS = "EXPERIENCE_YEARS", "Experience (Years)"
        AVAILABILITY = "AVAILABILITY", "Availability"
        EMPLOYMENT_TYPE = "EMPLOYMENT_TYPE", "Employment Type"
        MIN_RATING = "MIN_RATING", "Minimum Rating"

    class Operator(models.TextChoices):
        EQUALS = "EQUALS", "Equals"
        IN = "IN", "In"
        GTE = "GTE", "Greater Than or Equal"
        LTE = "LTE", "Less Than or Equal"
        CONTAINS = "CONTAINS", "Contains"

    criteria = models.ForeignKey(
        VendorCriteria,
        on_delete=models.CASCADE,
        related_name="terms",
    )
    attribute_type = models.CharField(
        max_length=40,
        choices=AttributeType.choices,
        default=AttributeType.SKILL,
    )
    operator = models.CharField(
        max_length=20,
        choices=Operator.choices,
        default=Operator.EQUALS,
    )
    value = models.JSONField(default=dict)
    group_id = models.IntegerField(default=1, db_index=True)

    class Meta:
        db_table = "workforce_criteria_term"

    def __str__(self):
        return f"CriteriaTerm({self.attribute_type} {self.operator} {self.value}, group={self.group_id})"


class VendorInvitation(models.Model):
    """
    Disposable, request-scoped invitation sent from a vendor (Company)
    to a technician (by email and/or Employee foreign key).
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    class Channel(models.TextChoices):
        DIRECT_EMAIL = "DIRECT_EMAIL", "Direct Email"
        MATCHING_RESULT = "MATCHING_RESULT", "Matching Result"

    vendor = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="sent_technician_invitations",
    )
    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="received_vendor_invitations",
    )
    invited_email = models.EmailField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    channel = models.CharField(
        max_length=30,
        choices=Channel.choices,
        default=Channel.DIRECT_EMAIL,
    )
    matched_criteria = models.ForeignKey(
        VendorCriteria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invitations",
    )
    message = models.TextField(blank=True, default="")
    token = models.CharField(max_length=128, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_invitation"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Invitation #{self.id} from {self.vendor.company_name} to {self.invited_email} [{self.status}]"


class VendorTechnicianRelationship(models.Model):
    """
    Durable, many-to-many operational connection between a vendor (Company)
    and an independent technician (Employee).
    """
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        RESIGNATION_REQUESTED = "RESIGNATION_REQUESTED", "Resignation Requested"
        RESIGNED = "RESIGNED", "Resigned"
        SUSPENDED = "SUSPENDED", "Suspended"
        TERMINATED = "TERMINATED", "Terminated"

    class EngagementType(models.TextChoices):
        PER_JOB = "PER_JOB", "Per Job"
        PART_TIME = "PART_TIME", "Part Time"
        FULL_TIME = "FULL_TIME", "Full Time"
        ON_CALL = "ON_CALL", "On Call"

    class PaymentModel(models.TextChoices):
        DIRECT_TO_TECHNICIAN = "DIRECT_TO_TECHNICIAN", "Direct to Technician"
        THROUGH_VENDOR = "THROUGH_VENDOR", "Through Vendor"

    vendor = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_relationships",
    )
    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="vendor_relationships",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    source_invitation = models.ForeignKey(
        VendorInvitation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resulting_relationships",
    )
    scope_skills = models.JSONField(default=list, blank=True)
    engagement_type = models.CharField(
        max_length=30,
        choices=EngagementType.choices,
        default=EngagementType.PER_JOB,
    )
    payment_model = models.CharField(
        max_length=30,
        choices=PaymentModel.choices,
        default=PaymentModel.DIRECT_TO_TECHNICIAN,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_vendor_relationships",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_technician_relationship"
        unique_together = ("vendor", "technician")
        ordering = ["-started_at"]

    def __str__(self):
        return f"Relationship: {self.vendor.company_name} <-> {self.technician} [{self.status}]"


class VendorRelievingRequest(models.Model):
    """
    Formal Multi-Party Resignation & Relieving Lifecycle:
    1. Technician requests resignation with reason & details.
    2. Vendor verifies internal job dues & approves settlement clearance.
    3. SEVO Platform Superadmin verifies platform job settlements & approves clearance.
    4. Mutual legal release signoff completed between Vendor & Technician.
    5. Technician is unlinked to become an independent Solo Worker + Individual Wallet is provisioned.
    """
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Resignation Requested"
        VENDOR_APPROVED = "VENDOR_APPROVED", "Vendor Approved Dues Clearance"
        SEVO_APPROVED = "SEVO_APPROVED", "SEVO Admin Cleared"
        COMPLETED = "COMPLETED", "Completed & Relieved"
        REJECTED = "REJECTED", "Rejected"
        CANCELLED = "CANCELLED", "Cancelled"

    class ReasonCategory(models.TextChoices):
        TRANSITION_TO_SOLO = "TRANSITION_TO_SOLO", "Transitioning to Independent Solo Worker"
        RELOCATION = "RELOCATION", "Relocation / Moving"
        PERSONAL = "PERSONAL", "Personal / Family Reasons"
        RATE_DISPUTE = "RATE_DISPUTE", "Compensation / Rate Dispute"
        CAREER_GROWTH = "CAREER_GROWTH", "Career Growth / Alternative Opportunities"
        OTHER = "OTHER", "Other"

    relationship = models.ForeignKey(
        VendorTechnicianRelationship,
        on_delete=models.CASCADE,
        related_name="relieving_requests",
    )
    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="relieving_requests",
    )
    vendor = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="relieving_requests",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )
    reason_category = models.CharField(
        max_length=40,
        choices=ReasonCategory.choices,
        default=ReasonCategory.TRANSITION_TO_SOLO,
    )
    resignation_notes = models.TextField(blank=True, default="")
    desired_relieving_date = models.DateField(null=True, blank=True)

    # Vendor approval & settlement
    vendor_settlement_notes = models.TextField(blank=True, default="")
    vendor_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_vendor_relievings",
    )
    vendor_approved_at = models.DateTimeField(null=True, blank=True)

    # SEVO Admin audit & approval
    sevo_audit_notes = models.TextField(blank=True, default="")
    sevo_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleared_sevo_relievings",
    )
    sevo_approved_at = models.DateTimeField(null=True, blank=True)

    # Mutual Legal Signoff
    worker_signoff_ack = models.BooleanField(default=False)
    worker_signed_at = models.DateTimeField(null=True, blank=True)
    vendor_signoff_ack = models.BooleanField(default=False)
    vendor_signed_at = models.DateTimeField(null=True, blank=True)

    rejection_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_relieving_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Relieving Request #{self.id}: {self.technician} from {self.vendor.company_name} [{self.status}]"


