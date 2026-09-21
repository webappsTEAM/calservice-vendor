"""
workforce-app/backend/workforce_api/models.py
Relational database models for Workforce Scheduling, Skills, Compliance, Notifications, Events, Payroll, and Reports.
"""
from decimal import Decimal
import uuid
import django
from django.conf import settings
from django.db import IntegrityError, models, transaction
from django.utils import timezone


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
    offered_at = models.DateTimeField(db_index=True, default=timezone.now)
    expires_at = models.DateTimeField(db_index=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "workforce_job_offer"
        ordering = ["-offered_at"]
        # Declared in migration 0013 but absent from this model, so every
        # makemigrations run proposed DROPPING them -- including the
        # constraint that stops one technician holding two live offers for
        # the same job. Re-declared here to match what is actually in the
        # database.
        constraints = [
            models.CheckConstraint(
                **{
                    ("condition" if django.VERSION >= (5, 1) else "check"): (
                        models.Q(wave_number__gte=1, wave_number__lte=6)
                    ),
                    "name": "valid_wave_number_1_to_6",
                }
            ),
            models.UniqueConstraint(
                fields=("job", "employee"),
                condition=models.Q(status="OFFERED"),
                name="unique_active_job_offer_per_employee",
            ),
        ]
        indexes = [
            models.Index(fields=["job", "status", "expires_at"], name="wf_offer_job_st_exp_idx"),
            models.Index(fields=["job", "wave_id", "status", "expires_at"], name="wf_offer_job_wave_idx"),
            models.Index(fields=["employee", "status", "expires_at"], name="wf_offer_emp_st_exp_idx"),
        ]

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
        # Work area photo and appliance photo are optional evidence.
        # Mandatory gates: arrival geofence check-in, customer OTP verification, and technician presence selfie.
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

    @property
    def is_cash_collected(self) -> bool:
        """
        Canonical derived property representing whether cash has been physically collected.
        Returns True if cash_collected_at is recorded, False otherwise.
        """
        return bool(self.cash_collected_at is not None)


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
                **{
                    ("condition" if django.VERSION >= (5, 1) else "check"): (
                        models.Q(account_type="PROVIDER_HEAD", company__isnull=False, employee__isnull=True)
                        | models.Q(account_type="INDIVIDUAL_WORKER", employee__isnull=False, company__isnull=True)
                    ),
                    "name": "wallet_account_type_matches_owner",
                }
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


# ============================================================================
# RESTORED 2026-09-07 -- see commit message for the full account.
#
# Removed from this file by commit 7204699 on 2 September while their database
# tables, their migrations (0014/0019/0020) and quotation_service.py -- which
# imports several of them -- all remained. The estimation/quotation feature has
# been dead since, and `makemigrations` would have dropped the tables.
#
# Recovered verbatim from 7204699^ and verified against the live schema.
# ============================================================================

class WorkforceServiceSkillRequirement(models.Model):
    service = models.ForeignKey(
        "service_requests.Service",
        on_delete=models.CASCADE,
        related_name="skill_requirements",
    )
    skill = models.ForeignKey(
        WorkforceSkill,
        on_delete=models.CASCADE,
        related_name="service_requirements",
    )
    is_mandatory = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_service_skill_requirement"
        unique_together = ("service", "skill")

    def __str__(self):
        return f"{self.service.name} requires {self.skill.name}"


class WorkforceRateCard(models.Model):
    """
    Authoritative Rate Card configuration for Quotation Calculation.
    Defines approved unit rates, standard costs, and discount ceilings per service section.
    """
    class Section(models.TextChoices):
        MATERIAL = "MATERIAL", "Material"
        LABOUR = "LABOUR", "Labour"
        SURFACE_PREP = "SURFACE_PREP", "Surface Preparation"
        EQUIPMENT = "EQUIPMENT", "Equipment & Scaffolding"
        TRANSPORT = "TRANSPORT", "Transport & Logistics"
        OTHER = "OTHER", "Other"

    service_id = models.IntegerField(null=True, blank=True, db_index=True)
    service_category = models.CharField(max_length=100, db_index=True)
    service_name = models.CharField(max_length=150, db_index=True)
    section = models.CharField(max_length=50, choices=Section.choices, default=Section.MATERIAL)
    item_name = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    unit = models.CharField(max_length=50, default="sqft")

    # How default_rate is applied. A single rate column cannot express slab
    # pricing (epoxy 1/2/3 mm), capacity bands (water tank by litres) or size
    # bands (bathroom small/medium/large), so those carry their thresholds in
    # pricing_config and are evaluated by services/rate_card_pricing.py.
    class PricingModel(models.TextChoices):
        PER_UNIT      = "PER_UNIT",      "Rate per unit"
        FLAT          = "FLAT",          "Flat price regardless of quantity"
        TIERED        = "TIERED",        "Rate chosen by a specification tier"
        CAPACITY_BAND = "CAPACITY_BAND", "Rate or flat price by capacity band"
        SIZE_BAND     = "SIZE_BAND",     "Flat price by size band"
        QUOTE_ONLY    = "QUOTE_ONLY",    "No standard rate; priced per site"

    class WarrantyTier(models.TextChoices):
        NONE     = "NONE",     "No warranty"
        FIVE_YEAR = "5_YEAR",  "5-Year Warranty"
        TEN_YEAR  = "10_YEAR", "10-Year Warranty"

    pricing_model = models.CharField(
        max_length=20, choices=PricingModel.choices, default=PricingModel.PER_UNIT
    )
    pricing_config = models.JSONField(
        default=dict, blank=True,
        help_text="Bands for TIERED / CAPACITY_BAND / SIZE_BAND. See "
                  "services/rate_card_pricing.py for the accepted shape.",
    )
    minimum_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Quotes below this quantity are rejected -- e.g. Minor Masonry "
                  "is not viable under 500 sq.ft.",
    )
    warranty_tier = models.CharField(
        max_length=10, choices=WarrantyTier.choices, default=WarrantyTier.NONE
    )
    advance_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Overrides the category's advance_percent for quotes containing "
                  "this item. Waterproofing needs 50% up front while ordinary "
                  "painting does not, and both sit in the painting category -- so "
                  "the rule cannot live on the category alone.",
    )

    default_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    default_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    max_discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=20.00)
    is_active = models.BooleanField(default=True, db_index=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_rate_card"
        ordering = ["service_category", "section", "sort_order", "id"]

    def __str__(self):
        return f"[{self.service_category}] {self.section}: {self.item_name} (₹{self.default_rate}/{self.unit})"


def generate_quote_number():
    """
    Allocate a commercial quotation number: PQ-YYYYMMDD-NNNN.

    The dated format is a commercial requirement, so the sequence used
    previously is not enough on its own -- the suffix has to count within the
    day. next_document_number() does that atomically; see its comment.
    """
    return _dated_number("PQ", "QUOTE")


class WorkforceQuote(models.Model):
    """
    Central Commercial Quotation Model for CalTrack Workforce.
    Maintains a strict state machine, cryptographic decision token, and conversion to actual Work ServiceRequests.
    """
    class Status(models.TextChoices):
        DRAFT               = "DRAFT",               "Draft"
        PENDING_REVIEW      = "PENDING_REVIEW",      "Pending Admin Review"
        SENT_TO_CUSTOMER    = "SENT_TO_CUSTOMER",    "Sent to Customer"
        CUSTOMER_ACCEPTED   = "CUSTOMER_ACCEPTED",   "Customer Accepted"
        # SEVO back-office gate. A quote the customer accepted is a commercial
        # commitment but not yet an authorised job: it waits here until a SEVO
        # admin approves it, and only then is it converted and invoiced.
        PENDING_ADMIN_APPROVAL = "PENDING_ADMIN_APPROVAL", "Pending SEVO Admin Approval"
        ADMIN_APPROVED      = "ADMIN_APPROVED",      "Approved by SEVO Admin"
        ADMIN_REJECTED      = "ADMIN_REJECTED",      "Rejected by SEVO Admin"
        CHANGES_REQUESTED   = "CHANGES_REQUESTED",   "Changes Requested"
        DECLINED            = "DECLINED",            "Declined"
        EXPIRED             = "EXPIRED",             "Expired"
        SUPERSEDED          = "SUPERSEDED",          "Superseded"
        CONVERSION_PENDING  = "CONVERSION_PENDING",  "Conversion Pending"
        CONVERTED           = "CONVERTED",           "Converted to Work Booking"
        CANCELLED           = "CANCELLED",           "Cancelled"

    class StructuralImpact(models.TextChoices):
        NONE                 = "NONE",                 "No Structural Impact"
        SUSPECTED_STRUCTURAL = "SUSPECTED_STRUCTURAL", "Suspected Structural (Clearance Required)"
        STRUCTURAL           = "STRUCTURAL",           "Structural Demolition / Load-Bearing (Clearance Required)"

    # NOT unique on its own: a revision (v2, v3 ...) deliberately keeps the
    # same quote_number so the customer sees one document evolving. The
    # uniqueness that matters is (quote_number, quote_version) -- see Meta.
    quote_number = models.CharField(max_length=50, db_index=True)
    quote_version = models.IntegerField(default=1, db_index=True)
    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="quotes",
        db_index=True,
    )
    work_job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="converted_from_quote",
    )
    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="quotes_created",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="quotes",
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customer_quotes",
    )
    title = models.CharField(max_length=200, default="Quotation")
    description = models.TextField(blank=True, default="")
    service_category = models.CharField(max_length=150, blank=True, default="")
    service_name = models.CharField(max_length=200, blank=True, default="")

    estimated_labor_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_materials_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    inspection_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    inspection_fee_adjusted = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    net_payable = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    # Null means "use the category policy". Set when the quote contains an item
    # whose rate card demands a larger advance (waterproofing, masonry), or when
    # an admin overrides it for this specific job.
    advance_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)

    # Cryptographic decision token for customer verification
    decision_token = models.CharField(max_length=64, unique=True, null=True, blank=True, db_index=True)
    decision_expires_at = models.DateTimeField(null=True, blank=True)
    customer_decision = models.CharField(max_length=30, blank=True, default="")
    customer_decided_at = models.DateTimeField(null=True, blank=True)
    customer_decline_reason = models.TextField(blank=True, default="")
    customer_notes = models.TextField(blank=True, default="")

    # Mason Structural Clearance Gate
    structural_impact = models.CharField(
        max_length=30,
        choices=StructuralImpact.choices,
        default=StructuralImpact.NONE,
    )
    admin_cleared_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="cleared_quotes",
    )
    admin_cleared_at = models.DateTimeField(null=True, blank=True)
    admin_clearance_notes = models.TextField(blank=True, default="")

    # SEVO admin approval of the accepted quote (distinct from the structural
    # clearance above, which gates SENDING a mason quote to the customer).
    admin_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_quotes",
    )
    admin_approved_at = models.DateTimeField(null=True, blank=True)
    admin_approval_notes = models.TextField(blank=True, default="")
    admin_rejection_reason = models.TextField(blank=True, default="")
    submitted_for_approval_at = models.DateTimeField(null=True, blank=True)

    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_quote"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["quote_number", "quote_version"],
                name="workforce_quote_number_version_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["job", "status"], name="wf_quote_job_status_idx"),
            models.Index(fields=["technician", "status"], name="wf_quote_tech_status_idx"),
            models.Index(fields=["company", "status"], name="wf_quote_comp_status_idx"),
            models.Index(fields=["decision_token"], name="wf_quote_dec_token_idx"),
        ]

    def __str__(self):
        return f"{self.quote_number} (v{self.quote_version}) - {self.title} [₹{self.net_payable or self.total_amount}] - {self.status}"

    @property
    def requires_structural_clearance(self):
        return self.structural_impact in [
            self.StructuralImpact.SUSPECTED_STRUCTURAL,
            self.StructuralImpact.STRUCTURAL,
        ]

    @property
    def is_structurally_cleared(self):
        if not self.requires_structural_clearance:
            return True
        return self.admin_cleared_at is not None

    def save(self, *args, **kwargs):
        """
        Assign a quote number on first save, retrying if the unique
        constraint is hit. The inner atomic() is what makes the retry
        legal: after an IntegrityError the surrounding transaction is
        unusable unless the failed statement was rolled back to a
        savepoint first.
        """
        if self.quote_number:
            return super().save(*args, **kwargs)

        last_error = None
        for _attempt in range(5):
            self.quote_number = generate_quote_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                if "quote_number" not in str(exc):
                    raise
                last_error = exc
                self.quote_number = ""
        raise last_error


class WorkforceQuoteItem(models.Model):
    """
    Individual Line Item within a Workforce Quotation.
    """
    quote = models.ForeignKey(
        WorkforceQuote,
        on_delete=models.CASCADE,
        related_name="items",
    )
    section = models.CharField(max_length=50, default="OTHER")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    item_type = models.CharField(max_length=50, default="item")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    unit = models.CharField(max_length=50, default="unit")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    material_source = models.CharField(max_length=50, default="CALTRACK")
    is_customer_supplied = models.BooleanField(default=False)
    # Legacy boolean, kept so existing readers do not break. warranty_tier is
    # the field that carries meaning now: the business offers exactly two
    # tiers, and "true" could not say which one applied.
    warranty_applicable = models.BooleanField(default=True)
    warranty_tier = models.CharField(
        max_length=10,
        choices=[("NONE", "No warranty"), ("5_YEAR", "5-Year Warranty"), ("10_YEAR", "10-Year Warranty")],
        default="NONE",
    )
    notes = models.TextField(blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_quote_item"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit} @ ₹{self.unit_price} = ₹{self.total_amount})"


class WorkforceQuoteMeasurement(models.Model):
    """
    Dimensional & area measurement collected during physical site inspection.
    """
    quote = models.ForeignKey(
        WorkforceQuote,
        on_delete=models.CASCADE,
        related_name="measurements",
    )
    name = models.CharField(max_length=200)
    measurement_type = models.CharField(max_length=50, default="area")
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    unit = models.CharField(max_length=50, default="sqft")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_quote_measurement"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name}: {self.area or self.length or self.quantity} {self.unit}"


class WorkforceQuotePhoto(models.Model):
    """
    Inspection evidence photos captured on-site during quotation inspection.
    """
    quote = models.ForeignKey(
        WorkforceQuote,
        on_delete=models.CASCADE,
        related_name="photos",
    )
    photo_url = models.CharField(max_length=500)
    photo_type = models.CharField(max_length=50, null=True, blank=True)
    caption = models.CharField(max_length=255, blank=True, default="")
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_quote_photo"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Quote Photo #{self.id} for {self.quote.quote_number} ({self.photo_type})"


class WorkforcePaintingQuote(models.Model):
    """
    Painting-specific structured inspection & scope parameters.
    """
    quote = models.OneToOneField(
        WorkforceQuote,
        on_delete=models.CASCADE,
        related_name="painting_details",
    )
    property_type = models.CharField(max_length=100, default="Apartment")
    rooms_detail = models.JSONField(default=list, blank=True)
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    surface_condition = models.CharField(max_length=100, default="Good")
    existing_paint_condition = models.CharField(max_length=100, default="Old Emulsion")
    paint_type = models.CharField(max_length=100, null=True, blank=True)
    brand_grade = models.CharField(max_length=100, blank=True, default="Asian Paints / Berger")
    number_of_coats = models.IntegerField(default=2)
    requires_putty = models.BooleanField(default=False)
    requires_priming = models.BooleanField(default=False)
    crack_treatment = models.BooleanField(default=False)
    waterproofing_needed = models.BooleanField(default=False)
    scaffolding_required = models.BooleanField(default=False)
    color_code = models.CharField(max_length=100, null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_painting_quote"

    def __str__(self):
        return f"Painting Details for {self.quote.quote_number} ({self.area_sqft} sqft, {self.paint_type})"


class WorkforceMasonQuote(models.Model):
    """
    Masonry & Civil structured inspection & scope parameters.
    """
    quote = models.OneToOneField(
        WorkforceQuote,
        on_delete=models.CASCADE,
        related_name="mason_details",
    )
    work_type = models.CharField(max_length=100, null=True, blank=True)
    length = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    width = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    height = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    area_sqft = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_duration_days = models.IntegerField(default=1)
    requires_demolition = models.BooleanField(default=False)
    debris_disposal_included = models.BooleanField(default=False)
    structural_impact = models.CharField(max_length=50, default="NONE")
    access_difficulty = models.CharField(max_length=50, default="Standard")
    labour_count = models.IntegerField(default=2)
    materials_needed = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_mason_quote"

    def __str__(self):
        return f"Mason Details for {self.quote.quote_number} ({self.work_type}, Demolition: {self.requires_demolition})"


class WorkforceProviderJoinRequest(models.Model):
    """
    Tracks a technician's request to join an existing Service Provider organization during signup.
    Selecting a Service Provider during signup does NOT grant immediate company membership.
    The join request remains in status=PENDING until approved by the Service Provider Admin or Superadmin.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.CASCADE,
        related_name="provider_join_requests",
    )
    provider = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="technician_join_requests",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "workforce_provider_join_request"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"JoinRequest #{self.id}: Tech #{self.technician_id} -> Provider #{self.provider_id} ({self.status})"


class WorkforceSystemSetting(models.Model):
    """
    Persistent global key-value configuration for CalTrack Workforce.
    SuperAdmin managed settings (e.g. DISPATCH_RADIUS_KM).
    """
    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_system_setting"

    def __str__(self):
        return f"{self.key} = {self.value}"


# =============================================================================
# Commercial Invoicing
#
# An approved quotation becomes an invoice. The invoice is the document the
# customer pays against; the payment is what eventually reaches the provider's
# wallet (via services/commission.settle_completed_job at job completion).
#
# Amounts are FROZEN onto the invoice at issue time. They are deliberately not
# read back through the quote: a quote can be revised after the fact, and an
# issued invoice must not silently change value underneath a customer who has
# already paid it.
# =============================================================================

def generate_invoice_number():
    """
    Allocate an invoice number: INV-YYYYMMDD-NNNN.

    Matched to the quote format deliberately -- a quote and the invoice that
    follows it are one document family, and two numbering schemes inside it
    make reconciliation harder than it needs to be.
    """
    return _dated_number("INV", "INVOICE")


class WorkforceInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT          = "DRAFT",          "Draft"
        ISSUED         = "ISSUED",         "Issued"
        PARTIALLY_PAID = "PARTIALLY_PAID", "Partially Paid"
        PAID           = "PAID",           "Paid"
        CANCELLED      = "CANCELLED",      "Cancelled"
        REFUNDED       = "REFUNDED",       "Refunded"

    invoice_number = models.CharField(max_length=50, unique=True, db_index=True)

    # PROTECT: an invoice outlives the quote it came from. Deleting a quoted
    # job must not silently delete the customer's financial record.
    quote = models.ForeignKey(
        "workforce_api.WorkforceQuote",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="invoices",
    )
    # The WORK ServiceRequest this invoice bills for (not the inspection job).
    job = models.ForeignKey(
        "service_requests.ServiceRequest",
        on_delete=models.CASCADE,
        related_name="workforce_invoices",
        db_index=True,
    )
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workforce_invoices",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workforce_invoices",
    )
    technician = models.ForeignKey(
        "employees.Employee",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="workforce_invoices",
    )

    # Billing snapshot, frozen at issue. The customer's profile can change
    # later; the invoice must keep saying who it was billed to.
    bill_to_name = models.CharField(max_length=200, blank=True, default="")
    bill_to_phone = models.CharField(max_length=30, blank=True, default="")
    bill_to_email = models.EmailField(blank=True, default="")
    bill_to_address = models.TextField(blank=True, default="")

    service_category = models.CharField(max_length=150, blank=True, default="")
    service_name = models.CharField(max_length=200, blank=True, default="")

    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    inspection_fee_adjusted = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default="INR")

    # Payment schedule, from the category's advance_percent. Waterproofing and
    # masonry need half up front to buy chemicals, cement and sand before any
    # work starts; standard painting is billed in full. advance_amount equals
    # total_amount when the category takes 100% up front.
    advance_percent = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    advance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    balance_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    advance_due_at = models.DateTimeField(null=True, blank=True)
    advance_paid_at = models.DateTimeField(null=True, blank=True)
    balance_due_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    issued_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")

    notes = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_invoice"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["customer", "status"]),
        ]

    def __str__(self):
        return f"{self.invoice_number} - Rs.{self.total_amount} [{self.status}]"

    def save(self, *args, **kwargs):
        if self.invoice_number:
            return super().save(*args, **kwargs)

        last_error = None
        for _attempt in range(5):
            self.invoice_number = generate_invoice_number()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError as exc:
                if "invoice_number" not in str(exc):
                    raise
                last_error = exc
                self.invoice_number = ""
        raise last_error


class WorkforceInvoiceItem(models.Model):
    """
    Frozen copy of the quote's line items at the moment the invoice was issued.
    Copied rather than referenced so a later quote revision cannot rewrite the
    contents of an invoice the customer has already received.
    """
    invoice = models.ForeignKey(
        WorkforceInvoice, on_delete=models.CASCADE, related_name="items"
    )
    section = models.CharField(max_length=50, default="OTHER")
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    item_type = models.CharField(max_length=50, default="item")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1.00)
    unit = models.CharField(max_length=50, default="unit")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    line_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    sort_order = models.IntegerField(default=0)

    class Meta:
        db_table = "workforce_invoice_item"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.name} x {self.quantity} = Rs.{self.line_total}"


class WorkforceInvoicePayment(models.Model):
    """
    One customer payment against an invoice.

    `reference` is unique per invoice: a payment gateway callback is
    at-least-once, so the same transaction id can arrive twice. The unique
    constraint is what makes recording a payment idempotent at the database
    level rather than only in application code.
    """
    class Method(models.TextChoices):
        ONLINE = "ONLINE", "Online / Gateway"
        UPI    = "UPI",    "UPI"
        CARD   = "CARD",   "Card"
        CASH   = "CASH",   "Cash on Service"
        WALLET = "WALLET", "Customer Wallet"
        OTHER  = "OTHER",  "Other"

    class Status(models.TextChoices):
        PENDING  = "PENDING",  "Pending"
        SUCCESS  = "SUCCESS",  "Success"
        FAILED   = "FAILED",   "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    invoice = models.ForeignKey(
        WorkforceInvoice, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices, default=Method.ONLINE)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.SUCCESS, db_index=True
    )
    reference = models.CharField(max_length=200, blank=True, default="")
    gateway = models.CharField(max_length=50, blank=True, default="")
    paid_at = models.DateTimeField(null=True, blank=True)

    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_invoice_payments",
    )
    # Set once this payment has reached the provider's wallet, so the link
    # from "customer paid" to "provider credited" is inspectable in one hop.
    ledger_entry = models.ForeignKey(
        "workforce_api.WalletLedgerEntry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_invoice_payments",
    )
    notes = models.CharField(max_length=255, blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_invoice_payment"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["invoice", "reference"],
                condition=models.Q(reference__gt=""),
                name="workforce_invoice_payment_reference_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["invoice", "status"]),
        ]

    def __str__(self):
        return f"Payment Rs.{self.amount} ({self.method}) on {self.invoice_id}"


# =============================================================================
# Document numbering
#
# Quote and invoice numbers are dated and sequential within the day:
#   PQ-20260907-0001, INV-20260907-0001
#
# The counter row below is what makes that safe under concurrency. A dated
# format needs a per-day count, and computing that by reading MAX() and
# inserting is exactly the race that made quote numbering unreliable before.
# Here the read and the increment are ONE statement -- an upsert that returns
# the incremented value -- so two technicians pressing "create quote" in the
# same millisecond get different numbers without either of them blocking on a
# table lock.
# =============================================================================

class WorkforceDocumentCounter(models.Model):
    scope = models.CharField(max_length=40, db_index=True)   # "QUOTE" | "INVOICE"
    period = models.CharField(max_length=16, db_index=True)  # "20260907"
    last_value = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_document_counter"
        constraints = [
            models.UniqueConstraint(
                fields=["scope", "period"], name="workforce_document_counter_unique"
            ),
        ]

    def __str__(self):
        return f"{self.scope} {self.period}: {self.last_value}"


def next_document_number(scope, period):
    """Atomically claim the next number in (scope, period)."""
    from django.db import connection

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO workforce_document_counter (scope, period, last_value, updated_at)
                VALUES (%s, %s, 1, NOW())
                ON CONFLICT (scope, period)
                DO UPDATE SET last_value = workforce_document_counter.last_value + 1,
                              updated_at = NOW()
                RETURNING last_value
                """,
                [scope, period],
            )
            return cursor.fetchone()[0]

    # Non-PostgreSQL (SQLite under some test setups): row lock instead. Slower
    # and serialising, but correct; callers still retry on unique violation.
    with transaction.atomic():
        row, _ = WorkforceDocumentCounter.objects.select_for_update().get_or_create(
            scope=scope, period=period
        )
        row.last_value += 1
        row.save(update_fields=["last_value", "updated_at"])
        return row.last_value


def _dated_number(prefix, scope, when=None):
    when = when or timezone.localtime()
    period = when.strftime("%Y%m%d")
    return "%s-%s-%04d" % (prefix, period, next_document_number(scope, period))


# =============================================================================
# Commercial policy, editable by the SEVO admin
#
# Everything here used to be a constant somewhere in the code: the Rs.199
# inspection fee (four separate literals in service_requests/vendor_views.py),
# the 15 km / Rs.300 consultation rule, the Rs.30,000 high-value review
# threshold, the 50% advance on waterproofing and masonry.
#
# Money rules change more often than code ships, so they live in a table with
# an audit trail instead. One row per service category; the seed migration
# reproduces today's behaviour exactly so nothing moves on deploy.
# =============================================================================

class WorkforceServicePricingPolicy(models.Model):
    class ConsultationFeeMode(models.TextChoices):
        FREE          = "FREE",          "Always free"
        FLAT          = "FLAT",          "Flat fee"
        DISTANCE_BAND = "DISTANCE_BAND", "Free within radius, flat fee beyond"

    service_category = models.CharField(max_length=150, unique=True, db_index=True)
    display_name = models.CharField(max_length=200, blank=True, default="")

    consultation_fee_mode = models.CharField(
        max_length=20,
        choices=ConsultationFeeMode.choices,
        default=ConsultationFeeMode.FLAT,
    )
    consultation_fee_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.00,
        help_text="Charged when mode is FLAT.",
    )
    free_radius_km = models.DecimalField(
        max_digits=6, decimal_places=2, default=15.00,
        help_text="DISTANCE_BAND: consultation is free within this radius of the hub.",
    )
    beyond_radius_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=300.00,
        help_text="DISTANCE_BAND: charged when the site is beyond free_radius_km.",
    )
    # Hosur central hub by default.
    hub_latitude = models.FloatField(default=12.7409)
    hub_longitude = models.FloatField(default=77.8253)

    high_value_review_threshold = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Quotes above this are held for admin review BEFORE the customer "
                  "sees them. Null disables the pre-send gate for this category.",
    )
    requires_admin_approval = models.BooleanField(
        default=True,
        help_text="Whether a customer-accepted quote waits for SEVO approval "
                  "before becoming a work booking.",
    )
    advance_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=100.00,
        help_text="Share of the invoice payable up front. 50 for waterproofing "
                  "and masonry; 100 for standard painting.",
    )
    allow_customer_supplied_materials = models.BooleanField(
        default=False,
        help_text="Off by default: customer-supplied material voids the "
                  "workmanship warranty, so quote items claiming it are rejected.",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_pricing_policies",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_service_pricing_policy"
        ordering = ["service_category"]
        verbose_name_plural = "Workforce service pricing policies"

    def __str__(self):
        return f"{self.display_name or self.service_category} pricing policy"


# ── Inventory Management ─────────────────────────────────────────────────────

class InventoryItem(models.Model):
    """
    Company-scoped inventory item linked to the shared service catalogue.
    Each vendor company maintains its own stock levels, pricing overrides,
    and custom images per catalogue item (e.g. vegetables, services).
    """

    class StockUnit(models.TextChoices):
        KG      = "kg",     "Kilogram (kg)"
        GRAM    = "g",      "Gram (g)"
        LITRE   = "litre",  "Litre"
        ML      = "ml",     "Millilitre (ml)"
        PIECE   = "piece",  "Piece"
        BUNCH   = "bunch",  "Bunch"
        DOZEN   = "dozen",  "Dozen"
        BOX     = "box",    "Box"
        BAG     = "bag",    "Bag"
        PACKET  = "packet", "Packet"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    # FK into the shared service_requests_service table (managed=False mirror)
    catalogue_service_id = models.IntegerField(
        db_index=True,
        help_text="ID of the matching service_requests_service row (source of truth name/image).",
    )
    catalogue_category_id = models.IntegerField(
        db_index=True,
        help_text="ID of the matching service_requests_catalogcategory row.",
    )

    # Denormalised snapshot so we can show items even if catalogue goes offline
    name_snapshot = models.CharField(max_length=200)
    category_name_snapshot = models.CharField(max_length=200, blank=True, default="")
    catalogue_image_url = models.CharField(max_length=1000, blank=True, default="",
        help_text="Image URL copied from Service.image at time of add/sync.")

    # Vendor-level overrides
    custom_name = models.CharField(max_length=200, blank=True, default="",
        help_text="If set, overrides the catalogue display name for this company.")
    custom_image_url = models.CharField(max_length=1000, blank=True, default="",
        help_text="If set, overrides the catalogue image for this company.")
    custom_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Company-specific selling price. Null = use catalogue price.",
    )

    # Stock
    quantity_in_stock = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
    )
    unit = models.CharField(
        max_length=20,
        choices=StockUnit.choices,
        default=StockUnit.KG,
    )
    mrp = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Maximum Retail Price (MRP) for strike-through deals and discount display.",
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text="Alert threshold – item is flagged LOW STOCK when qty <= this.",
    )
    reserved_quantity = models.DecimalField(
        max_digits=12, decimal_places=3, default=0,
        help_text="Stock quantity currently reserved by active/pending checkout carts.",
    )

    notes = models.TextField(blank=True, default="")
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_inventory_item"
        unique_together = ("company", "catalogue_service_id")
        ordering = ["category_name_snapshot", "name_snapshot"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @property
    def display_name(self):
        return self.custom_name or self.name_snapshot

    @property
    def display_image(self):
        return self.custom_image_url or self.catalogue_image_url or ""

    @property
    def available_quantity(self):
        avail = (self.quantity_in_stock or Decimal("0.000")) - (self.reserved_quantity or Decimal("0.000"))
        return max(Decimal("0.000"), avail)

    @property
    def stock_status(self):
        if not self.is_available:
            return "UNAVAILABLE"
        if self.available_quantity <= 0:
            return "OUT_OF_STOCK"
        if self.low_stock_threshold and self.available_quantity <= self.low_stock_threshold:
            return "LOW_STOCK"
        return "IN_STOCK"

    def __str__(self):
        return f"{self.display_name} [{self.company}] avail={self.available_quantity}{self.unit}"


# ── Vendor Store & Marketplace Models ──────────────────────────────────────────

class VendorStore(models.Model):
    """
    Amazon-style Dedicated Seller Storefront for an onboarded vendor/supplier.
    Houses branding, delivery radius, operating hours, and store status.
    """
    company = models.OneToOneField(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="vendor_store",
    )
    store_name = models.CharField(max_length=255)
    store_slug = models.SlugField(max_length=255, unique=True, db_index=True)
    tagline = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    logo_url = models.CharField(max_length=1000, blank=True, default="")
    banner_url = models.CharField(max_length=1000, blank=True, default="")
    fssai_license_number = models.CharField(max_length=100, blank=True, default="")
    gst_number = models.CharField(max_length=50, blank=True, default="")
    store_address = models.TextField(blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_radius_km = models.DecimalField(max_digits=6, decimal_places=2, default=5.00)
    minimum_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    estimated_delivery_mins = models.IntegerField(default=30)
    is_accepting_orders = models.BooleanField(default=True, db_index=True)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    rating_average = models.DecimalField(max_digits=3, decimal_places=2, default=5.00)
    total_reviews = models.IntegerField(default=0)
    onboarding = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_store"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.store_name} ({self.company.company_name})"


class VendorDeal(models.Model):
    """
    Time-bounded or strike-through promotion on an inventory item offered by a vendor.
    """
    class DealType(models.TextChoices):
        STRIKE_THROUGH = "strike_through", "Strike-Through Discount"
        FLASH_SALE = "flash_sale", "Flash Sale"
        VOLUME_DISCOUNT = "volume_discount", "Volume Discount"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="vendor_deals",
    )
    inventory_item = models.ForeignKey(
        "workforce_api.InventoryItem",
        on_delete=models.CASCADE,
        related_name="deals",
    )
    deal_type = models.CharField(max_length=30, choices=DealType.choices, default=DealType.STRIKE_THROUGH)
    original_price = models.DecimalField(max_digits=10, decimal_places=2)
    deal_price = models.DecimalField(max_digits=10, decimal_places=2)
    deal_start_at = models.DateTimeField(null=True, blank=True)
    deal_end_at = models.DateTimeField(null=True, blank=True)
    badge_text = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_deal"
        ordering = ["-created_at"]

    @property
    def discount_percent(self):
        if self.original_price and self.original_price > 0:
            diff = self.original_price - self.deal_price
            return max(0, int(round((diff / self.original_price) * 100)))
        return 0

    def __str__(self):
        return f"{self.inventory_item.display_name} Deal: ₹{self.deal_price} (was ₹{self.original_price})"


class VendorCoupon(models.Model):
    """
    Vendor-funded discount coupon scoped specifically to orders from this vendor's store.
    """
    class DiscountType(models.TextChoices):
        PERCENT = "percent", "Percentage (%)"
        FLAT = "flat", "Flat Amount (₹)"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="vendor_coupons",
    )
    code = models.CharField(max_length=50, db_index=True)
    description = models.CharField(max_length=255, blank=True, default="")
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.PERCENT)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    max_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    usage_limit_total = models.IntegerField(null=True, blank=True)
    usage_limit_per_user = models.IntegerField(default=1)
    times_used = models.IntegerField(default=0)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_vendor_coupon"
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="unique_vendor_coupon_code"),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.company.company_name}] {self.code}: {self.discount_value}{'%' if self.discount_type == 'percent' else '₹'}"


class InventoryTransaction(models.Model):
    """
    Immutable audit ledger for all quantity changes (reservations, sales, adjustments).
    """
    class TransactionType(models.TextChoices):
        INITIAL_STOCK = "INITIAL_STOCK", "Initial Stock"
        PURCHASE = "PURCHASE", "Purchase / Restock"
        ADJUSTMENT = "ADJUSTMENT", "Manual Adjustment"
        RESERVATION = "RESERVATION", "Cart Reservation"
        RESERVATION_RELEASE = "RESERVATION_RELEASE", "Reservation Release"
        SALE = "SALE", "Order Sale"
        CANCELLATION = "CANCELLATION", "Order Cancellation Return"
        RETURN = "RETURN", "Customer Return"
        DAMAGE = "DAMAGE", "Damaged Goods"
        EXPIRED = "EXPIRED", "Expired Produce"

    inventory_item = models.ForeignKey(
        "workforce_api.InventoryItem",
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=30, choices=TransactionType.choices)
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    balance_after = models.DecimalField(max_digits=12, decimal_places=3)
    reference_id = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_inventory_transaction"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.transaction_type}] {self.inventory_item.display_name}: {self.quantity} (Bal: {self.balance_after})"


class CouponRedemption(models.Model):
    """
    Tracks atomic usage of store and platform coupons by customers.
    """
    coupon = models.ForeignKey(
        "workforce_api.VendorCoupon",
        on_delete=models.CASCADE,
        related_name="redemptions",
    )
    customer_id = models.CharField(max_length=100, db_index=True)
    order_id = models.CharField(max_length=100, blank=True, default="", db_index=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_coupon_redemption"
        ordering = ["-redeemed_at"]

    def __str__(self):
        return f"{self.customer_id} redeemed {self.coupon.code} for ₹{self.discount_amount}"


class GroceryCart(models.Model):
    """
    Customer cart with strict Single-Store Enforcement.
    """
    customer_id = models.CharField(max_length=100, unique=True, db_index=True)
    vendor_store = models.ForeignKey(
        "workforce_api.VendorStore",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="carts",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_grocery_cart"

    def __str__(self):
        return f"Cart {self.customer_id} (Store: {self.vendor_store.store_name if self.vendor_store else 'Empty'})"


class GroceryCartItem(models.Model):
    cart = models.ForeignKey(
        GroceryCart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    inventory_item = models.ForeignKey(
        "workforce_api.InventoryItem",
        on_delete=models.CASCADE,
        related_name="cart_items",
    )
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_grocery_cart_item"
        unique_together = ("cart", "inventory_item")

    def __str__(self):
        return f"{self.quantity} x {self.inventory_item.display_name}"


class GroceryOrder(models.Model):
    """
    Multi-Vendor Grocery Order with full price snapshotting and explicit 10-state machine.
    """
    class Status(models.TextChoices):
        PENDING_PAYMENT = "PENDING_PAYMENT", "Pending Payment"
        CONFIRMED = "CONFIRMED", "Confirmed"
        VENDOR_PENDING = "VENDOR_PENDING", "Vendor Pending Acceptance"
        ACCEPTED = "ACCEPTED", "Accepted by Store"
        PICKING = "PICKING", "Picking & Packing"
        PACKED = "PACKED", "Packed & Ready"
        READY_FOR_PICKUP = "READY_FOR_PICKUP", "Ready for Pickup"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"
        VENDOR_REJECTED = "VENDOR_REJECTED", "Rejected by Vendor"
        REFUNDED = "REFUNDED", "Refunded"

    class PaymentMethod(models.TextChoices):
        COD = "COD", "Cash on Delivery"
        ONLINE = "ONLINE", "Online Payment"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CAPTURED = "CAPTURED", "Captured"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    order_number = models.CharField(max_length=50, unique=True, db_index=True)
    customer_id = models.CharField(max_length=100, db_index=True)
    customer_name = models.CharField(max_length=200, blank=True, default="")
    customer_phone = models.CharField(max_length=50, blank=True, default="")
    delivery_address = models.TextField(blank=True, default="")
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    vendor_store = models.ForeignKey(
        "workforce_api.VendorStore",
        on_delete=models.CASCADE,
        related_name="orders",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING_PAYMENT,
        db_index=True,
    )
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.COD,
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    deal_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    vendor_coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    platform_coupon_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    applied_coupon_code = models.CharField(max_length=50, blank=True, default="")
    delivery_notes = models.TextField(blank=True, default="")

    placed_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    packed_at = models.DateTimeField(null=True, blank=True)
    out_for_delivery_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_grocery_order"
        ordering = ["-placed_at"]

    def __str__(self):
        return f"Order #{self.order_number} - {self.vendor_store.store_name} ({self.status}) ₹{self.total_amount}"


class GroceryOrderItem(models.Model):
    """
    Snapshot of product, SKU, pricing, deal, and unit at the moment of order placement.
    """
    order = models.ForeignKey(
        GroceryOrder,
        on_delete=models.CASCADE,
        related_name="items",
    )
    inventory_item = models.ForeignKey(
        "workforce_api.InventoryItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    product_name_snapshot = models.CharField(max_length=200)
    sku_snapshot = models.CharField(max_length=100, blank=True, default="")
    unit_snapshot = models.CharField(max_length=20, default="kg")
    quantity = models.DecimalField(max_digits=12, decimal_places=3)
    mrp_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    regular_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    deal_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "workforce_grocery_order_item"

    def __str__(self):
        return f"{self.quantity}{self.unit_snapshot} {self.product_name_snapshot} @ ₹{self.final_unit_price}"


class GroceryOrderStatusHistory(models.Model):
    order = models.ForeignKey(
        GroceryOrder,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    actor = models.CharField(max_length=100, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_grocery_order_status_history"
        ordering = ["created_at"]


class GroceryDelivery(models.Model):
    class FulfillmentMethod(models.TextChoices):
        VENDOR_DELIVERY = "VENDOR_DELIVERY", "Vendor Self-Delivery"
        PLATFORM_RIDER = "PLATFORM_RIDER", "CalServices Rider"
        THIRD_PARTY = "THIRD_PARTY", "Third-Party Logistics"
        CUSTOMER_PICKUP = "CUSTOMER_PICKUP", "Customer Pickup"

    class DeliveryStatus(models.TextChoices):
        UNASSIGNED = "UNASSIGNED", "Unassigned"
        ASSIGNED = "ASSIGNED", "Assigned to Rider"
        ARRIVED_AT_STORE = "ARRIVED_AT_STORE", "Arrived at Store"
        PICKED_UP = "PICKED_UP", "Picked Up"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"

    order = models.OneToOneField(
        GroceryOrder,
        on_delete=models.CASCADE,
        related_name="delivery",
    )
    fulfillment_method = models.CharField(
        max_length=30,
        choices=FulfillmentMethod.choices,
        default=FulfillmentMethod.VENDOR_DELIVERY,
    )
    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.UNASSIGNED,
    )
    rider_name = models.CharField(max_length=100, blank=True, default="")
    rider_phone = models.CharField(max_length=50, blank=True, default="")
    delivery_otp = models.CharField(max_length=10, blank=True, default="")
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_grocery_delivery"

    def __str__(self):
        return f"Delivery for #{self.order.order_number} ({self.status})"


class CommissionRule(models.Model):
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="commission_rules",
        help_text="Null = applies globally across all vendors.",
    )
    category_slug = models.CharField(max_length=100, default="vegetables")
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)
    fixed_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_commission_rule"

    def __str__(self):
        target = self.company.company_name if self.company else "Global"
        return f"{target} [{self.category_slug}]: {self.commission_percent}% + ₹{self.fixed_fee}"


class VendorSettlement(models.Model):
    class SettlementStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SETTLED = "SETTLED", "Settled"
        HOLD = "HOLD", "On Hold"

    settlement_number = models.CharField(max_length=50, unique=True)
    vendor_store = models.ForeignKey(
        "workforce_api.VendorStore",
        on_delete=models.CASCADE,
        related_name="settlements",
    )
    period_start = models.DateField()
    period_end = models.DateField()
    gross_sales = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    platform_commission = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    vendor_funded_discounts = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=20,
        choices=SettlementStatus.choices,
        default=SettlementStatus.PENDING,
    )
    settled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_vendor_settlement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Settlement {self.settlement_number} - {self.vendor_store.store_name}: ₹{self.net_payable} ({self.status})"


class FinancialLedgerEntry(models.Model):
    class EntryType(models.TextChoices):
        CREDIT = "CREDIT", "Credit"
        DEBIT = "DEBIT", "Debit"

    class Category(models.TextChoices):
        SALE = "SALE", "Customer Order Sale"
        COMMISSION = "COMMISSION", "Platform Commission"
        DISCOUNT_DEDUCTION = "DISCOUNT_DEDUCTION", "Store Coupon Deduction"
        PAYOUT = "PAYOUT", "Vendor Payout"
        ADJUSTMENT = "ADJUSTMENT", "Manual Adjustment"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(max_length=10, choices=EntryType.choices)
    category = models.CharField(max_length=30, choices=Category.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    order = models.ForeignKey(
        GroceryOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    settlement = models.ForeignKey(
        VendorSettlement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ledger_entries",
    )
    description = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_financial_ledger_entry"
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.entry_type} - {self.category}] ₹{self.amount} for {self.company.company_name}"


class VendorStoreReview(models.Model):
    vendor_store = models.ForeignKey(
        "workforce_api.VendorStore",
        on_delete=models.CASCADE,
        related_name="reviews",
    )
    customer_id = models.CharField(max_length=100, db_index=True)
    customer_name = models.CharField(max_length=200, blank=True, default="Anonymous")
    order = models.OneToOneField(
        GroceryOrder,
        on_delete=models.CASCADE,
        related_name="review",
    )
    rating = models.IntegerField(default=5)
    review_text = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_vendor_store_review"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.rating}★ Review for {self.vendor_store.store_name} by {self.customer_name}"


class SellerHubCategory(models.Model):
    """
    Dedicated category table for Seller Hub / Grocery Catalog.
    Completely isolated from the platform service CatalogCategory table.
    Supports unlimited nesting hierarchy with self-referencing parent FK.
    """
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, db_index=True)
    description = models.TextField(blank=True, default="")
    icon = models.CharField(max_length=100, blank=True, default="Store")
    image = models.CharField(max_length=500, blank=True, default="")
    parent = models.ForeignKey(
        "self",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="children",
        db_index=True,
    )
    sort_order = models.IntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_hub_category"
        ordering = ["sort_order", "name", "id"]
        indexes = [
            models.Index(fields=["parent", "is_active"], name="wf_seller_cat_parent_act_idx"),
            models.Index(fields=["is_active", "sort_order"], name="wf_seller_cat_act_sort_idx"),
            models.Index(fields=["slug"], name="wf_seller_cat_slug_idx"),
        ]

    def __str__(self):
        return self.name


class SellerCatalogUploadBatch(models.Model):
    """
    Tracks bulk Excel / CSV catalog upload batches.
    """
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        PARTIALLY_FAILED = "PARTIALLY_FAILED", "Partially Failed"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="seller_catalog_batches",
        db_index=True,
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_catalog_batches",
    )
    file_name = models.CharField(max_length=255)
    total_rows = models.IntegerField(default=0)
    imported_rows = models.IntegerField(default=0)
    failed_rows = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    error_report = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_catalog_upload_batch"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch #{self.id} ({self.file_name}) - {self.status}"


class SellerProduct(models.Model):
    """
    Real Relational Seller Product Catalog Record for Seller Hub merchants.
    Strictly tenant-scoped to company. Linked to SellerHubCategory (leaf only).
    """
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        SUBMITTED = "SUBMITTED", "Submitted"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        CHANGES_REQUESTED = "CHANGES_REQUESTED", "Changes Requested"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PAUSED = "PAUSED", "Paused"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="seller_products",
        db_index=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_seller_products",
    )
    category = models.ForeignKey(
        SellerHubCategory,
        on_delete=models.RESTRICT,
        related_name="products",
        db_index=True,
    )
    title = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default="")
    brand = models.CharField(max_length=150, blank=True, default="", db_index=True)
    sku = models.CharField(max_length=100, db_index=True)
    barcode = models.CharField(max_length=100, blank=True, default="", db_index=True)
    unit = models.CharField(max_length=50, default="piece")
    pack_size = models.CharField(max_length=50, default="1")
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    hsn_code = models.CharField(max_length=50, blank=True, default="")
    storage_info = models.CharField(max_length=255, blank=True, default="")
    expiry_info = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    admin_review_note = models.TextField(blank=True, default="")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_seller_products",
    )
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    upload_batch = models.ForeignKey(
        SellerCatalogUploadBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_product"
        ordering = ["-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "sku"],
                name="unique_seller_product_sku_per_company",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "status"], name="wf_seller_prod_comp_st_idx"),
            models.Index(fields=["category", "status"], name="wf_seller_prod_cat_st_idx"),
            models.Index(fields=["status", "updated_at"], name="wf_seller_prod_st_upd_idx"),
        ]

    def __str__(self):
        return f"{self.title} ({self.sku}) - {self.company.company_name}"


class SellerProductImage(models.Model):
    """
    Product images for a Seller Product.
    """
    product = models.ForeignKey(
        SellerProduct,
        on_delete=models.CASCADE,
        related_name="images",
    )
    image_url = models.CharField(max_length=500)
    is_primary = models.BooleanField(default=False)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_seller_product_image"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"Image for {self.product.title} (Primary: {self.is_primary})"


class SellerProductAuditLog(models.Model):
    """
    Immutable audit history of all reviewer and seller lifecycle actions on a product.
    """
    product = models.ForeignKey(
        SellerProduct,
        on_delete=models.CASCADE,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=50)
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_product_audit_logs",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "workforce_seller_product_audit_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Audit #{self.id} for Product #{self.product_id}: {self.action} ({self.from_status} -> {self.to_status})"


# ═══════════════════════════════════════════════════════════════════════════════
# SELLER HUB INVENTORY MANAGEMENT (Phase 3)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerInventory(models.Model):
    """
    Company-scoped real inventory balance for an approved Seller Product.
    Enforces decimal precision for weight/volume grocery items and atomic audit movements.
    """
    class StockStatus(models.TextChoices):
        IN_STOCK = "IN_STOCK", "In Stock"
        LOW_STOCK = "LOW_STOCK", "Low Stock"
        OUT_OF_STOCK = "OUT_OF_STOCK", "Out of Stock"

    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="seller_inventories",
        db_index=True,
    )
    product = models.OneToOneField(
        SellerProduct,
        on_delete=models.CASCADE,
        related_name="inventory",
        db_index=True,
    )
    on_hand_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Physical inventory on hand in warehouse / storefront.",
    )
    reserved_qty = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Stock locked for active processing.",
    )
    low_stock_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("10.000"),
        help_text="Threshold below which inventory is marked as Low Stock.",
    )
    reorder_level = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("20.000"),
        help_text="Suggested replenishment reorder point.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_inventory"
        ordering = ["-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "product"],
                name="unique_seller_product_inventory",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "on_hand_qty"], name="wf_seller_inv_comp_qty_idx"),
            models.Index(fields=["product", "on_hand_qty"], name="wf_seller_inv_prod_qty_idx"),
        ]

    def __str__(self):
        return f"Inventory for {self.product.title} ({self.company.company_name}) - {self.available_qty} {self.product.unit} available"

    @property
    def available_qty(self):
        """Calculated: On-hand Quantity - Reserved Quantity (never negative)."""
        avail = self.on_hand_qty - self.reserved_qty
        return max(Decimal("0.000"), avail)

    @property
    def stock_status(self):
        """Dynamic stock status based on on-hand and available threshold."""
        if self.on_hand_qty <= Decimal("0.000"):
            return self.StockStatus.OUT_OF_STOCK
        if self.available_qty <= self.low_stock_threshold:
            return self.StockStatus.LOW_STOCK
        return self.StockStatus.IN_STOCK


class SellerInventoryBatch(models.Model):
    """
    Grocery Lot / Batch tracking for expiry dates, cost prices, and batch-level stock depletion.
    """
    class BatchStatus(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        EXPIRING_SOON = "EXPIRING_SOON", "Expiring Soon"
        EXPIRED = "EXPIRED", "Expired"
        DEPLETED = "DEPLETED", "Depleted"

    inventory = models.ForeignKey(
        SellerInventory,
        on_delete=models.CASCADE,
        related_name="batches",
        db_index=True,
    )
    batch_number = models.CharField(max_length=100, db_index=True)
    received_date = models.DateField(default=timezone.now)
    expiry_date = models.DateField(null=True, blank=True, db_index=True)
    initial_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    current_quantity = models.DecimalField(max_digits=12, decimal_places=3)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    status = models.CharField(
        max_length=30,
        choices=BatchStatus.choices,
        default=BatchStatus.ACTIVE,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_inventory_batch"
        ordering = ["expiry_date", "-created_at"]
        indexes = [
            models.Index(fields=["inventory", "expiry_date"], name="wf_seller_batch_inv_exp_idx"),
            models.Index(fields=["inventory", "status"], name="wf_seller_batch_inv_st_idx"),
        ]

    def __str__(self):
        return f"Batch #{self.batch_number} for {self.inventory.product.title} - {self.current_quantity} remaining"

    def update_dynamic_status(self, save=True):
        """Update status dynamically based on current quantity and expiry date."""
        if self.current_quantity <= Decimal("0.000"):
            self.status = self.BatchStatus.DEPLETED
        elif self.expiry_date:
            exp_date = self.expiry_date
            if isinstance(exp_date, str):
                from datetime import datetime
                try:
                    exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                except ValueError:
                    exp_date = None
            if exp_date:
                today = timezone.now().date()
                if exp_date < today:
                    self.status = self.BatchStatus.EXPIRED
                elif exp_date <= (today + timezone.timedelta(days=30)):
                    self.status = self.BatchStatus.EXPIRING_SOON
                else:
                    self.status = self.BatchStatus.ACTIVE
            else:
                self.status = self.BatchStatus.ACTIVE
        else:
            self.status = self.BatchStatus.ACTIVE

        if save:
            self.save(update_fields=["status", "updated_at"])
        return self.status


class SellerInventoryMovement(models.Model):
    """
    Immutable ledger of every stock modification (Stock-in, adjustments, damage, expired, reservation).
    Tracks exact before/after balances, user actor, and mandatory audit reasons.
    """
    class MovementType(models.TextChoices):
        OPENING_STOCK = "OPENING_STOCK", "Opening Stock"
        STOCK_IN = "STOCK_IN", "Stock In / Purchase"
        STOCK_OUT = "STOCK_OUT", "Stock Out / Transfer"
        ADJUSTMENT_INCREASE = "ADJUSTMENT_INCREASE", "Stock Adjustment (Increase)"
        ADJUSTMENT_DECREASE = "ADJUSTMENT_DECREASE", "Stock Adjustment (Decrease)"
        DAMAGE = "DAMAGE", "Damaged / Broken Stock"
        EXPIRED = "EXPIRED", "Expired Stock Write-off"
        RESERVED = "RESERVED", "Order Stock Reserved"
        RESERVATION_RELEASED = "RESERVATION_RELEASED", "Reservation Released"
        ORDER_DEDUCTED = "ORDER_DEDUCTED", "Order Fulfilled / Stock Deducted"
        RETURN_RESTOCK = "RETURN_RESTOCK", "Customer Return Restocked"

    inventory = models.ForeignKey(
        SellerInventory,
        on_delete=models.CASCADE,
        related_name="movements",
        db_index=True,
    )
    batch = models.ForeignKey(
        SellerInventoryBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="movements",
    )
    movement_type = models.CharField(
        max_length=40,
        choices=MovementType.choices,
        db_index=True,
    )
    quantity_change = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Positive for additions, negative for reductions.",
    )
    balance_before = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="On-hand balance before the operation.",
    )
    balance_after = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="On-hand balance after the operation.",
    )
    reason = models.TextField(
        blank=True,
        default="",
        help_text="Mandatory business reason for adjustments, damages, or expiries.",
    )
    reference_id = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Optional PO number, Invoice reference, or Batch number.",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_inventory_movements",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_seller_inventory_movement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["inventory", "movement_type"], name="wf_seller_mov_inv_type_idx"),
            models.Index(fields=["inventory", "created_at"], name="wf_seller_mov_inv_dt_idx"),
        ]

    def __str__(self):
        return f"Movement #{self.id} ({self.movement_type}): {self.quantity_change} on {self.inventory.product.title}"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. SELLER HUB ORDERS & FULFILMENT (Phase 4)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerOrder(models.Model):
    """
    Seller-side fulfilment order linked to canonical customer marketplace order by source_order_id.
    Enforces strict state machine:
    NEW -> ACCEPTED -> PICKING -> PACKED -> READY_FOR_PICKUP -> HANDED_OVER -> DELIVERED
    (or CANCELLED from non-terminal states with inventory reservation release).
    """
    class Status(models.TextChoices):
        NEW = "NEW", "New Order"
        ACCEPTED = "ACCEPTED", "Accepted"
        PICKING = "PICKING", "Picking in Progress"
        PACKED = "PACKED", "Packed & Ready"
        READY_FOR_PICKUP = "READY_FOR_PICKUP", "Ready for Pickup"
        HANDED_OVER = "HANDED_OVER", "Handed Over"
        DELIVERED = "DELIVERED", "Delivered"
        CANCELLED = "CANCELLED", "Cancelled"

    class FulfillmentType(models.TextChoices):
        DELIVERY = "DELIVERY", "Delivery"
        STORE_PICKUP = "STORE_PICKUP", "Store Pickup"

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        COD = "COD", "Cash On Delivery"

    # Canonical source reference (from Sevo-customer order)
    source_order_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Immutable canonical marketplace order reference from Customer app.",
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="seller_orders",
        db_index=True,
    )
    order_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Human-readable merchant display order number (e.g. SO-2026-0001)",
    )

    # Customer snapshot (privacy minimized for packing/fulfilment)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50, blank=True, default="")
    delivery_address = models.TextField(blank=True, default="")

    # Fulfilment details
    fulfillment_type = models.CharField(
        max_length=30,
        choices=FulfillmentType.choices,
        default=FulfillmentType.DELIVERY,
    )
    delivery_slot = models.CharField(max_length=100, blank=True, default="")
    delivery_notes = models.TextField(blank=True, default="")
    handover_otp_hash = models.CharField(max_length=256, blank=True, null=True)
    handover_ref = models.CharField(max_length=100, blank=True, default="")

    # Payment & pricing snapshot (Read-only for merchant)
    payment_method = models.CharField(max_length=50, default="ONLINE")
    payment_status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PAID,
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    currency = models.CharField(max_length=10, default="INR")

    # State machine
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )

    # Notes & cancellation
    seller_notes = models.TextField(blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cancelled_seller_orders",
    )

    # Workflow timestamps
    accepted_at = models.DateTimeField(null=True, blank=True)
    picking_at = models.DateTimeField(null=True, blank=True)
    packed_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    handed_over_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_order"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="wf_seller_ord_comp_st_idx"),
            models.Index(fields=["company", "created_at"], name="wf_seller_ord_comp_dt_idx"),
            models.Index(fields=["source_order_id"], name="wf_seller_ord_src_idx"),
        ]

    def __str__(self):
        return f"SellerOrder #{self.order_number} ({self.status}) - {getattr(self.company, 'company_name', self.company.slug)}"

    ALLOWED_TRANSITIONS = {
        Status.NEW: [Status.ACCEPTED, Status.CANCELLED],
        Status.ACCEPTED: [Status.PICKING, Status.CANCELLED],
        Status.PICKING: [Status.PACKED, Status.CANCELLED],
        Status.PACKED: [Status.READY_FOR_PICKUP, Status.CANCELLED],
        Status.READY_FOR_PICKUP: [Status.HANDED_OVER, Status.CANCELLED],
        Status.HANDED_OVER: [Status.DELIVERED],
        Status.DELIVERED: [],
        Status.CANCELLED: [],
    }

    def can_transition_to(self, target_status):
        """Check whether the target status is a valid transition from current state."""
        return target_status in self.ALLOWED_TRANSITIONS.get(self.status, [])


class SellerOrderItem(models.Model):
    """
    Line items within a SellerOrder capturing product snapshots, ordered and fulfilled quantities.
    """
    order = models.ForeignKey(
        SellerOrder,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    product = models.ForeignKey(
        SellerProduct,
        on_delete=models.PROTECT,
        related_name="order_items",
    )
    product_title = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, blank=True, default="")
    pack_size = models.CharField(max_length=100, blank=True, default="")
    ordered_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Quantity ordered by customer (decimal-safe for kg, litres, etc.)",
    )
    fulfilled_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Quantity actually picked and packed by merchant.",
    )
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )
    batch = models.ForeignKey(
        SellerInventoryBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="order_items",
    )
    is_picked = models.BooleanField(default=False)
    is_packed = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "workforce_seller_order_item"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["order", "product"], name="wf_seller_item_ord_prod_idx"),
        ]

    def __str__(self):
        return f"{self.product_title} x {self.ordered_quantity} ({self.order.order_number})"


class SellerOrderAuditLog(models.Model):
    """
    Immutable audit history of state transitions, actions, notes, and actor user.
    """
    order = models.ForeignKey(
        SellerOrder,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        db_index=True,
    )
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30)
    action = models.CharField(max_length=100)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_order_audit_logs",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_seller_order_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "created_at"], name="wf_seller_ord_log_dt_idx"),
        ]

    def __str__(self):
        return f"Order #{self.order.order_number} {self.from_status}->{self.to_status} ({self.action})"


class SellerOrderStatusOutbox(models.Model):
    """
    Transactional outbox table capturing seller order status transitions.
    Guarantees reliable, at-least-once, ordered webhook delivery to Customer app.
    """
    class DeliveryStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Delivery"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Permanently Failed"

    event_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Globally unique event idempotency identifier (e.g. evt_...).",
    )
    source_order_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Canonical marketplace source order identifier.",
    )
    order = models.ForeignKey(
        SellerOrder,
        on_delete=models.CASCADE,
        related_name="status_outbox_events",
        db_index=True,
    )
    sequence = models.PositiveIntegerField(
        help_text="Per-order monotonically increasing integer sequence number.",
    )
    previous_status = models.CharField(max_length=30, blank=True, default="")
    new_status = models.CharField(max_length=30, db_index=True)
    event_type = models.CharField(max_length=100, default="seller_order.status_updated")
    payload = models.JSONField(default=dict, help_text="Sanitized webhook payload dispatched to customer backend.")
    status = models.CharField(
        max_length=30,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        db_index=True,
    )
    retry_count = models.PositiveIntegerField(default=0)
    next_retry_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "workforce_seller_order_status_outbox"
        ordering = ["sequence", "created_at"]
        indexes = [
            models.Index(fields=["status", "next_retry_at"], name="wf_so_outbox_st_rt_idx"),
            models.Index(fields=["order", "sequence"], name="wf_so_outbox_ord_seq_idx"),
            models.Index(fields=["source_order_id"], name="wf_so_outbox_src_idx"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["order", "sequence"], name="wf_so_outbox_ord_seq_uniq"),
        ]

    def __str__(self):
        return f"OutboxEvent {self.event_id} (#{self.order.order_number} seq={self.sequence} {self.previous_status}->{self.new_status} [{self.status}])"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. SELLER HUB RETURNS & REVERSE LOGISTICS (Phase 5)
# ═══════════════════════════════════════════════════════════════════════════════

class SellerReturn(models.Model):
    """
    Seller-side return case linked to SellerOrder and customer marketplace return request.
    Enforces state machine:
    REQUESTED -> UNDER_SELLER_REVIEW -> APPROVED -> PICKUP_SCHEDULED -> RECEIVED -> QUALITY_CHECK -> RESTOCKED -> CLOSED
    (or REJECTED from review, DISCARDED from QC, or ESCALATED_TO_ADMIN).
    """
    class Status(models.TextChoices):
        REQUESTED = "REQUESTED", "Return Requested"
        UNDER_SELLER_REVIEW = "UNDER_SELLER_REVIEW", "Under Seller Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        PICKUP_SCHEDULED = "PICKUP_SCHEDULED", "Pickup Scheduled"
        RECEIVED = "RECEIVED", "Received at Warehouse"
        QUALITY_CHECK = "QUALITY_CHECK", "Under Quality Inspection"
        RESTOCKED = "RESTOCKED", "Restocked to Inventory"
        DISCARDED = "DISCARDED", "Scrapped / Disposed"
        ESCALATED_TO_ADMIN = "ESCALATED_TO_ADMIN", "Escalated to Platform Admin"
        CLOSED = "CLOSED", "Case Closed"

    class QualityCheckStatus(models.TextChoices):
        PENDING = "PENDING", "Pending Inspection"
        PASSED = "PASSED", "Passed (Fit for Restock)"
        FAILED = "FAILED", "Failed (Damaged / Unusable)"
        PARTIAL_PASS = "PARTIAL_PASS", "Partial Pass"

    class Reason(models.TextChoices):
        DAMAGED = "DAMAGED", "Damaged / Broken on Delivery"
        DEFECTIVE = "DEFECTIVE", "Defective / Quality Issue"
        EXPIRED = "EXPIRED", "Expired / Spoiled Product"
        WRONG_ITEM = "WRONG_ITEM", "Incorrect Item Delivered"
        NOT_AS_DESCRIBED = "NOT_AS_DESCRIBED", "Item Not as Described"
        CUSTOMER_PREFERENCE = "CUSTOMER_PREFERENCE", "Customer Changed Mind / Unopened"
        OTHER = "OTHER", "Other Reason"

    source_return_id = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Immutable canonical marketplace return reference from Customer app.",
    )
    order = models.ForeignKey(
        SellerOrder,
        on_delete=models.CASCADE,
        related_name="returns",
        db_index=True,
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="seller_returns",
        db_index=True,
    )
    return_number = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Human-readable merchant return reference (e.g. RET-2026-0001)",
    )

    # Customer & Reason snapshot (privacy minimized)
    customer_name = models.CharField(max_length=200)
    customer_phone = models.CharField(max_length=50, blank=True, default="")
    customer_address = models.TextField(blank=True, default="")
    reason = models.CharField(
        max_length=50,
        choices=Reason.choices,
        default=Reason.DAMAGED,
    )
    customer_notes = models.TextField(blank=True, default="")
    evidence_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of photographic evidence URLs uploaded by customer.",
    )

    # State machine
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.REQUESTED,
        db_index=True,
    )

    # Review & Inspection
    seller_decision = models.CharField(max_length=50, blank=True, default="")
    seller_notes = models.TextField(blank=True, default="")
    rejection_reason = models.TextField(blank=True, default="")

    quality_check_status = models.CharField(
        max_length=30,
        choices=QualityCheckStatus.choices,
        default=QualityCheckStatus.PENDING,
    )
    quality_check_notes = models.TextField(blank=True, default="")
    quality_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="inspected_seller_returns",
    )

    restock_decision = models.CharField(max_length=50, blank=True, default="")
    restock_notes = models.TextField(blank=True, default="")
    pickup_ref = models.CharField(max_length=100, blank=True, default="")
    admin_resolution_notes = models.TextField(blank=True, default="")

    # Timestamps
    reviewed_at = models.DateTimeField(null=True, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    inspected_at = models.DateTimeField(null=True, blank=True)
    restocked_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_seller_return"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="wf_seller_ret_comp_st_idx"),
            models.Index(fields=["company", "created_at"], name="wf_seller_ret_comp_dt_idx"),
            models.Index(fields=["source_return_id"], name="wf_seller_ret_src_idx"),
            models.Index(fields=["order"], name="wf_seller_ret_ord_idx"),
        ]

    def __str__(self):
        return f"Return #{self.return_number} ({self.status}) for Order #{self.order.order_number}"

    ALLOWED_TRANSITIONS = {
        Status.REQUESTED: [Status.UNDER_SELLER_REVIEW, Status.APPROVED, Status.REJECTED, Status.ESCALATED_TO_ADMIN],
        Status.UNDER_SELLER_REVIEW: [Status.APPROVED, Status.REJECTED, Status.ESCALATED_TO_ADMIN],
        Status.APPROVED: [Status.PICKUP_SCHEDULED, Status.RECEIVED, Status.ESCALATED_TO_ADMIN],
        Status.PICKUP_SCHEDULED: [Status.RECEIVED, Status.ESCALATED_TO_ADMIN],
        Status.RECEIVED: [Status.QUALITY_CHECK],
        Status.QUALITY_CHECK: [Status.RESTOCKED, Status.DISCARDED, Status.CLOSED, Status.ESCALATED_TO_ADMIN],
        Status.RESTOCKED: [Status.CLOSED],
        Status.DISCARDED: [Status.CLOSED],
        Status.REJECTED: [Status.CLOSED, Status.ESCALATED_TO_ADMIN],
        Status.ESCALATED_TO_ADMIN: [Status.APPROVED, Status.REJECTED, Status.CLOSED],
        Status.CLOSED: [],
    }

    def can_transition_to(self, target_status):
        return target_status in self.ALLOWED_TRANSITIONS.get(self.status, [])


class SellerReturnItem(models.Model):
    """
    Line items within a return case capturing returned, restocked, and scrapped quantities.
    """
    return_case = models.ForeignKey(
        SellerReturn,
        on_delete=models.CASCADE,
        related_name="items",
        db_index=True,
    )
    order_item = models.ForeignKey(
        SellerOrderItem,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="return_items",
    )
    product = models.ForeignKey(
        SellerProduct,
        on_delete=models.PROTECT,
        related_name="returned_items",
    )
    product_title = models.CharField(max_length=255)
    sku = models.CharField(max_length=100)
    unit = models.CharField(max_length=50, blank=True, default="")
    pack_size = models.CharField(max_length=100, blank=True, default="")
    returned_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Quantity requested for return by customer (decimal-safe).",
    )
    restocked_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Quantity verified, intact, and added back to inventory balance.",
    )
    scrapped_quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        default=Decimal("0.000"),
        help_text="Quantity damaged/spoiled that was scrapped and not returned to inventory.",
    )
    item_condition = models.CharField(
        max_length=50,
        default="UNOPENED",
        help_text="Condition upon inspection: UNOPENED, OPENED_INTACT, DAMAGED, EXPIRED, WRONG_ITEM",
    )
    qc_result = models.CharField(
        max_length=30,
        default="PENDING",
        help_text="QC Inspection result: PENDING, PASSED, FAILED",
    )
    batch = models.ForeignKey(
        SellerInventoryBatch,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="returned_order_items",
    )
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "workforce_seller_return_item"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["return_case", "product"], name="wf_seller_ret_it_prod_idx"),
        ]

    def __str__(self):
        return f"ReturnItem: {self.product_title} x {self.returned_quantity} (Ret #{self.return_case.return_number})"


class SellerReturnAuditLog(models.Model):
    """
    Immutable audit history of return state transitions, reviews, QC inspections, and restock actions.
    """
    return_case = models.ForeignKey(
        SellerReturn,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        db_index=True,
    )
    from_status = models.CharField(max_length=30, blank=True, default="")
    to_status = models.CharField(max_length=30)
    action = models.CharField(max_length=100)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_return_audit_logs",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_seller_return_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["return_case", "created_at"], name="wf_seller_ret_log_dt_idx"),
        ]

    def __str__(self):
        return f"Return #{self.return_case.return_number} {self.from_status}->{self.to_status} ({self.action})"


class SellerClaim(models.Model):
    """
    Phase 6: Seller Hub Claims and Operational Disputes.
    Tracks dispute filings, transit damage, missing/wrong items, seller statements, and admin decisions.
    """
    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        SELLER_RESPONSE_REQUIRED = "SELLER_RESPONSE_REQUIRED", "Seller Response Required"
        ESCALATED = "ESCALATED", "Escalated to Admin"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"
        SETTLED = "SETTLED", "Settled"
        CLOSED = "CLOSED", "Closed"

    class ClaimType(models.TextChoices):
        DAMAGED_ITEM = "DAMAGED_ITEM", "Damaged Item"
        MISSING_ITEM = "MISSING_ITEM", "Missing / Undelivered Item"
        WRONG_ITEM = "WRONG_ITEM", "Wrong Item Delivered"
        QUALITY_ISSUE = "QUALITY_ISSUE", "Quality / Freshness Issue"
        DELIVERY_DAMAGE = "DELIVERY_DAMAGE", "Damage During Delivery / In-Transit"
        SELLER_DISPUTE = "SELLER_DISPUTE", "Seller Operational Dispute"
        SETTLEMENT_DISPUTE = "SETTLEMENT_DISPUTE", "Settlement / Fee Dispute"
        OTHER = "OTHER", "Other Claim / Dispute"

    class AdminDecision(models.TextChoices):
        PENDING = "PENDING", "Pending Decision"
        REQUEST_SELLER_RESPONSE = "REQUEST_SELLER_RESPONSE", "Request Seller Response"
        APPROVED = "APPROVED", "Claim Approved"
        REJECTED = "REJECTED", "Claim Rejected"
        SETTLED = "SETTLED", "Claim Settled"

    source_claim_id = models.CharField(
        max_length=128,
        unique=True,
        db_index=True,
        help_text="Idempotency key and external claim reference from customer/storefront"
    )
    claim_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique operational claim reference (e.g. CLM-2026-0001)"
    )
    company = models.ForeignKey(
        "companies.Company",
        on_delete=models.CASCADE,
        related_name="seller_claims",
        db_index=True,
    )
    order = models.ForeignKey(
        SellerOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
        db_index=True,
    )
    return_case = models.ForeignKey(
        SellerReturn,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="claims",
        db_index=True,
    )
    claim_type = models.CharField(
        max_length=40,
        choices=ClaimType.choices,
        default=ClaimType.DAMAGED_ITEM,
        db_index=True,
    )
    description = models.TextField(
        help_text="Detailed description of the claim issue or dispute"
    )
    claimed_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        null=True,
        blank=True,
        help_text="Read-only claimed valuation (does not mutate payment or payouts)"
    )
    evidence_urls = models.JSONField(
        default=list,
        blank=True,
        help_text="List of URLs to uploaded photographic proof or document files"
    )
    customer_name = models.CharField(max_length=255, blank=True, default="")
    customer_phone = models.CharField(max_length=32, blank=True, default="")

    # Seller Response
    seller_response = models.TextField(blank=True, default="")
    seller_responded_at = models.DateTimeField(null=True, blank=True)
    seller_responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="responded_claims",
    )

    # Admin Arbitration & Decision
    admin_decision = models.CharField(
        max_length=40,
        choices=AdminDecision.choices,
        default=AdminDecision.PENDING,
    )
    admin_decision_reason = models.TextField(
        blank=True,
        default="",
        help_text="Mandatory rationale for admin approval, rejection, or settlement"
    )
    admin_decided_at = models.DateTimeField(null=True, blank=True)
    admin_decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_claims",
    )

    # Lifecycle State
    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_claims",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    ALLOWED_TRANSITIONS = {
        Status.OPEN: [
            Status.UNDER_REVIEW,
            Status.SELLER_RESPONSE_REQUIRED,
            Status.ESCALATED,
            Status.APPROVED,
            Status.REJECTED,
            Status.CLOSED,
        ],
        Status.UNDER_REVIEW: [
            Status.SELLER_RESPONSE_REQUIRED,
            Status.ESCALATED,
            Status.APPROVED,
            Status.REJECTED,
            Status.SETTLED,
            Status.CLOSED,
        ],
        Status.SELLER_RESPONSE_REQUIRED: [
            Status.UNDER_REVIEW,
            Status.ESCALATED,
            Status.APPROVED,
            Status.REJECTED,
            Status.CLOSED,
        ],
        Status.ESCALATED: [
            Status.UNDER_REVIEW,
            Status.APPROVED,
            Status.REJECTED,
            Status.SETTLED,
            Status.CLOSED,
        ],
        Status.APPROVED: [
            Status.SETTLED,
            Status.CLOSED,
        ],
        Status.REJECTED: [
            Status.ESCALATED,
            Status.CLOSED,
        ],
        Status.SETTLED: [
            Status.CLOSED,
        ],
        Status.CLOSED: [],
    }

    class Meta:
        db_table = "workforce_seller_claim"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="wf_seller_claim_comp_st_idx"),
            models.Index(fields=["company", "claim_type"], name="wf_seller_claim_comp_tp_idx"),
            models.Index(fields=["source_claim_id"], name="wf_seller_claim_src_idx"),
            models.Index(fields=["claim_number"], name="wf_seller_claim_num_idx"),
        ]

    def can_transition_to(self, target_status):
        return target_status in self.ALLOWED_TRANSITIONS.get(self.status, [])

    def __str__(self):
        return f"Claim #{self.claim_number} ({self.get_claim_type_display()}) - {self.status}"


class SellerClaimAuditLog(models.Model):
    """
    Immutable audit history of claim lifecycle, seller responses, escalations, and admin decisions.
    """
    claim = models.ForeignKey(
        SellerClaim,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        db_index=True,
    )
    from_status = models.CharField(max_length=40, blank=True, default="")
    to_status = models.CharField(max_length=40)
    action = models.CharField(max_length=100)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seller_claim_audit_logs",
    )
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "workforce_seller_claim_audit_log"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["claim", "created_at"], name="wf_seller_clm_log_dt_idx"),
        ]

    def __str__(self):
        return f"Claim #{self.claim.claim_number} {self.from_status}->{self.to_status} ({self.action})"






