"""
workforce-app/backend/workforce_api/models.py
Relational database models for Workforce Scheduling, Skills, Compliance, Notifications, Events, Payroll, and Reports.
"""
import uuid
import django
from django.conf import settings
from django.db import models
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
    wave_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    wave_number = models.IntegerField(default=1, db_index=True)
    rank_score = models.FloatField(default=0.0)
    offered_at = models.DateTimeField(default=timezone.now, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    rejection_reason = models.TextField(blank=True, default="")

    class Meta:
        db_table = "workforce_job_offer"
        ordering = ["-offered_at"]
        constraints = [
            models.CheckConstraint(
                **{
                    ("condition" if django.VERSION >= (6, 0) else "check"): models.Q(
                        wave_number__gte=1, wave_number__lte=6
                    ),
                    "name": "valid_wave_number_1_to_6",
                }
            ),
            models.UniqueConstraint(
                fields=["job", "employee"],
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
        return f"Offer Job #{self.job_id} to {self.employee} (Wave {self.wave_number}, {self.status})"


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
        ready = bool(self.after_presence_photo)
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

    # Derived tracking state (computed and stored on each GPS update)
    # movement_status: MOVING | STATIONARY | UNKNOWN
    movement_status = models.CharField(max_length=20, default="UNKNOWN", blank=True)
    # geofence_status: OUTSIDE | APPROACHING | ARRIVING | ARRIVED
    geofence_status = models.CharField(max_length=20, default="OUTSIDE", blank=True)
    # Previous valid point for movement detection
    prev_latitude = models.FloatField(null=True, blank=True)
    prev_longitude = models.FloatField(null=True, blank=True)
    prev_captured_at = models.DateTimeField(null=True, blank=True)
    # Realtime event throttle: tracks when last JOB_LOCATION_UPDATE was emitted
    last_event_emitted_at = models.DateTimeField(null=True, blank=True)
    last_event_state_key = models.CharField(max_length=60, blank=True, default="")

    # Consecutive arrival confirmation tracking
    consecutive_arrival_fixes = models.IntegerField(default=0)
    last_fix_lat = models.FloatField(null=True, blank=True)
    last_fix_lon = models.FloatField(null=True, blank=True)
    last_fix_time = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_job_tracking_session"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "status"], name="wf_ts_job_status_idx"),
            models.Index(fields=["employee", "status"], name="wf_ts_emp_status_idx"),
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
            models.Index(fields=["tracking_session", "created_at"], name="wf_lp_session_time_idx"),
            models.Index(fields=["job", "created_at"], name="wf_lp_job_time_idx"),
            models.Index(fields=["job", "employee", "captured_at"], name="wf_lp_job_emp_cap_idx"),
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

    @property
    def is_cash_collected(self):
        """Authoritative check if cash collection is persisted or job is fully paid."""
        return bool(self.cash_collected_at is not None or self.payment_status == self.PaymentStatus.PAID)

    @property
    def is_cash_received(self):
        """Authoritative check if cash collection is persisted or job is fully paid (Phase 2 Requirement)."""
        return self.is_cash_collected

    def __str__(self):
        return f"Payment #{self.id} for Job #{self.job_id} ({self.payment_method} - {self.payment_status} - ₹{self.amount_due})"


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


# ─── 29. Estimation & Quotation Domain ────────────────────────────────────────

def generate_quote_number():
    """Generates sequential canonical quotation numbers: QT-0001, QT-0002, etc."""
    last = WorkforceQuote.objects.order_by("-id").first()
    num = (last.id + 1) if last and last.id else 1
    candidate = f"QT-{str(num).zfill(4)}"
    while WorkforceQuote.objects.filter(quote_number=candidate).exists():
        num += 1
        candidate = f"QT-{str(num).zfill(4)}"
    return candidate


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

    quote_number = models.CharField(max_length=50, unique=True, db_index=True)
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

    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "workforce_quote"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["technician", "status"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["decision_token"]),
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
        if not self.quote_number:
            self.quote_number = generate_quote_number()
        super().save(*args, **kwargs)


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
    warranty_applicable = models.BooleanField(default=True)
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


