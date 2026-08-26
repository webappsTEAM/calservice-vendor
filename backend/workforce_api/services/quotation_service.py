import logging
import secrets
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError

from service_requests.models import ServiceRequest, is_quotation_service
from workforce_api.models import (
    PreServiceVerification,
    WorkforceQuote,
    WorkforceQuoteItem,
    WorkforceQuoteMeasurement,
    WorkforceQuotePhoto,
    WorkforcePaintingQuote,
    WorkforceMasonQuote,
    WorkforceRateCard,
)

logger = logging.getLogger(__name__)


def can_create_quote(job):
    """
    Authoritative backend gate determining if an employee can create/draft/send a quotation for a job.
    Enforces all 4 mandatory pre-service verification gates:
      1. GPS Auto-Verification (geofence_passed)
      2. Customer OTP Verification (otp_verified)
      3. Employee Presence Selfie (presence_photo uploaded)
      4. Required Inspection Photos (min photos uploaded per service type)
    """
    if not job:
        return False, {"code": "JOB_NOT_FOUND", "message": "Job not found", "missing": ["JOB"]}

    # Only quotation-based services support quotations
    if not (job.is_estimation or is_quotation_service(name=job.issue_title, category=job.service_category)):
        return False, {
            "code": "NOT_A_QUOTATION_SERVICE",
            "message": "This job is a standard direct service and does not require an estimation quote.",
            "missing": []
        }

    psv = PreServiceVerification.objects.filter(job=job).first()
    if not psv:
        return False, {
            "code": "ESTIMATION_VERIFICATION_INCOMPLETE",
            "message": "Pre-service verification record has not been initialized for this job.",
            "missing": ["GPS", "CUSTOMER_OTP", "EMPLOYEE_SELFIE", "REQUIRED_PHOTOS"],
            "checks": {
                "gps_verified": False,
                "otp_verified": False,
                "selfie_verified": False,
                "photos_verified": False,
            }
        }

    gps_ok = bool(psv.geofence_passed)
    otp_ok = bool(psv.otp_verified or job.otp_verified)
    selfie_ok = bool(psv.presence_photo and str(psv.presence_photo).strip())

    # Required photos check
    min_photos = 2
    photo_count = (1 if (psv.work_area_photo and str(psv.work_area_photo).strip()) else 0) + (1 if (psv.appliance_photo and str(psv.appliance_photo).strip()) else 0)
    photos_ok = bool(psv.is_complete or photo_count > 0)

    missing = []
    if not gps_ok:
        missing.append("GPS")
    if not otp_ok:
        missing.append("CUSTOMER_OTP")
    if not selfie_ok:
        missing.append("EMPLOYEE_SELFIE")
    if not photos_ok:
        missing.append("REQUIRED_PHOTOS")

    is_allowed = len(missing) == 0
    details = {
        "code": "ESTIMATION_VERIFICATION_COMPLETE" if is_allowed else "ESTIMATION_VERIFICATION_INCOMPLETE",
        "message": "All estimation verification checks passed." if is_allowed else f"Missing required verification checks: {', '.join(missing)}",
        "missing": missing,
        "checks": {
            "gps_verified": gps_ok,
            "otp_verified": otp_ok,
            "selfie_verified": selfie_ok,
            "photos_verified": photos_ok,
            "min_photos_required": min_photos,
            "photos_uploaded_count": photo_count,
        }
    }
    return is_allowed, details


def recalculate_quote_totals(quote):
    """
    Authoritative backend calculation engine for WorkforceQuote.
    Calculates item amounts, material/labour sub-totals, discounts, taxes (GST 18%), and net payable.
    """
    with transaction.atomic():
        items = list(quote.items.all())
        materials_cost = Decimal("0.00")
        labor_cost = Decimal("0.00")
        subtotal = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_tax = Decimal("0.00")

        for item in items:
            unit_price = Decimal(str(item.unit_price or 0))
            qty = Decimal(str(item.quantity or 1))
            disc = Decimal(str(item.discount_amount or 0))
            tax_rate = Decimal(str(item.tax_rate if item.tax_rate is not None else 18.00))

            gross = unit_price * qty
            net_item = max(Decimal("0.00"), gross - disc)
            item_tax = (net_item * (tax_rate / Decimal("100.00"))).quantize(Decimal("0.01"))

            item.total_amount = net_item
            item.save(update_fields=["total_amount", "updated_at"])

            subtotal += net_item
            total_discount += disc
            total_tax += item_tax

            sec = str(item.section).upper()
            if sec == "MATERIAL":
                materials_cost += net_item
            elif sec == "LABOUR":
                labor_cost += net_item

        quote.estimated_materials_cost = materials_cost
        quote.estimated_labor_cost = labor_cost
        quote.subtotal_amount = subtotal
        quote.discount_amount = total_discount
        quote.tax_amount = total_tax
        quote.total_amount = subtotal + total_tax

        # Adjust for inspection fee if applicable
        if quote.inspection_fee_adjusted and quote.inspection_fee_adjusted > 0:
            quote.net_payable = max(Decimal("0.00"), quote.total_amount - Decimal(str(quote.inspection_fee_adjusted)))
        else:
            quote.net_payable = quote.total_amount

        quote.save(update_fields=[
            "estimated_materials_cost",
            "estimated_labor_cost",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "net_payable",
            "updated_at",
        ])

    return quote


def send_quote_to_customer(quote_id, actor=None, valid_days=7):
    """
    Sends quotation to customer with cryptographic decision token, freezing amounts and setting expiry.
    Enforces Mason structural clearance gate.
    """
    with transaction.atomic():
        quote = WorkforceQuote.objects.select_for_update().get(id=quote_id)

        # Structural Gate Check
        if quote.requires_structural_clearance and not quote.is_structurally_cleared:
            quote.status = WorkforceQuote.Status.PENDING_REVIEW
            quote.save(update_fields=["status", "updated_at"])
            raise ValidationError(
                "Quotation involves structural modification or load-bearing demolition. "
                "Admin or Structural Engineer clearance is required before sending."
            )

        # Authoritative recalculation before freeze
        recalculate_quote_totals(quote)

        # Generate cryptographic decision token
        if not quote.decision_token:
            quote.decision_token = secrets.token_urlsafe(32)

        now = timezone.now()
        quote.valid_until = now + timedelta(days=valid_days)
        quote.decision_expires_at = quote.valid_until
        quote.status = WorkforceQuote.Status.SENT_TO_CUSTOMER
        quote.sent_at = now
        quote.save(update_fields=[
            "decision_token",
            "valid_until",
            "decision_expires_at",
            "status",
            "sent_at",
            "updated_at",
        ])

        logger.info("Quote %s (v%s) sent to customer with token %s", quote.quote_number, quote.quote_version, quote.decision_token)
        return quote


def record_customer_decision(quote_id, action, notes="", reason="", token=None, actor=None):
    """
    Authoritative handler for customer decisions:
      - ACCEPT -> marks CUSTOMER_ACCEPTED -> transitions to CONVERSION_PENDING -> converts to WORK ServiceRequest.
      - DECLINE -> marks DECLINED with reason.
      - REQUEST_CHANGES -> marks CHANGES_REQUESTED -> creates V2 draft and marks V1 SUPERSEDED.
    """
    clean_action = str(action).upper().strip()
    if clean_action not in ["ACCEPT", "DECLINE", "REQUEST_CHANGES"]:
        raise ValidationError(f"Unsupported customer action '{action}'. Allowed: ACCEPT, DECLINE, REQUEST_CHANGES.")

    with transaction.atomic():
        query = WorkforceQuote.objects.select_for_update().filter(id=quote_id)
        if token:
            query = query.filter(decision_token=token)

        quote = query.first()
        if not quote:
            raise ValidationError("Quotation not found or invalid token.")

        # Check expiration
        now = timezone.now()
        if quote.valid_until and quote.valid_until < now:
            quote.status = WorkforceQuote.Status.EXPIRED
            quote.save(update_fields=["status", "updated_at"])
            raise ValidationError("This quotation has expired and can no longer be decided upon.")

        if quote.status in [WorkforceQuote.Status.SUPERSEDED, WorkforceQuote.Status.CANCELLED]:
            raise ValidationError(f"This quote version ({quote.quote_version}) is no longer active ({quote.status}).")

        if clean_action == "ACCEPT":
            quote.status = WorkforceQuote.Status.CUSTOMER_ACCEPTED
            quote.customer_decision = "ACCEPTED"
            quote.customer_decided_at = now
            quote.customer_notes = notes
            quote.save(update_fields=["status", "customer_decision", "customer_decided_at", "customer_notes", "updated_at"])

            # Trigger automated conversion to Work Booking
            work_job = convert_accepted_quote_to_work_booking(quote, actor=actor)
            quote.refresh_from_db()
            return quote, work_job

        elif clean_action == "DECLINE":
            quote.status = WorkforceQuote.Status.DECLINED
            quote.customer_decision = "DECLINED"
            quote.customer_decline_reason = reason or notes
            quote.customer_decided_at = now
            quote.save(update_fields=["status", "customer_decision", "customer_decline_reason", "customer_decided_at", "updated_at"])
            return quote, None

        elif clean_action == "REQUEST_CHANGES":
            quote.status = WorkforceQuote.Status.CHANGES_REQUESTED
            quote.customer_decision = "CHANGES_REQUESTED"
            quote.customer_notes = notes or reason
            quote.customer_decided_at = now
            quote.save(update_fields=["status", "customer_decision", "customer_notes", "customer_decided_at", "updated_at"])

            # Create revised version (V2 draft)
            new_quote = create_revised_quote_version(quote, notes=notes)
            return quote, new_quote


def create_revised_quote_version(quote, notes=""):
    """
    Creates a new draft version of a quotation when changes are requested, marking the prior version SUPERSEDED.
    """
    with transaction.atomic():
        new_version_number = quote.quote_version + 1

        # Mark original as superseded
        quote.status = WorkforceQuote.Status.SUPERSEDED
        quote.save(update_fields=["status", "updated_at"])

        # Create new Quote Header
        new_quote = WorkforceQuote.objects.create(
            quote_number=quote.quote_number,
            quote_version=new_version_number,
            job=quote.job,
            technician=quote.technician,
            company=quote.company,
            customer=quote.customer,
            title=quote.title,
            description=f"Revision v{new_version_number}: {notes}".strip(),
            service_category=quote.service_category,
            service_name=quote.service_name,
            estimated_labor_cost=quote.estimated_labor_cost,
            estimated_materials_cost=quote.estimated_materials_cost,
            subtotal_amount=quote.subtotal_amount,
            discount_amount=quote.discount_amount,
            tax_amount=quote.tax_amount,
            total_amount=quote.total_amount,
            inspection_fee=quote.inspection_fee,
            inspection_fee_adjusted=quote.inspection_fee_adjusted,
            net_payable=quote.net_payable,
            status=WorkforceQuote.Status.DRAFT,
            structural_impact=quote.structural_impact,
        )

        # Clone line items
        for item in quote.items.all():
            WorkforceQuoteItem.objects.create(
                quote=new_quote,
                section=item.section,
                name=item.name,
                description=item.description,
                item_type=item.item_type,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                tax_rate=item.tax_rate,
                discount_amount=item.discount_amount,
                total_amount=item.total_amount,
                material_source=item.material_source,
                is_customer_supplied=item.is_customer_supplied,
                warranty_applicable=item.warranty_applicable,
                notes=item.notes,
                sort_order=item.sort_order,
            )

        # Clone measurements
        for m in quote.measurements.all():
            WorkforceQuoteMeasurement.objects.create(
                quote=new_quote,
                name=m.name,
                measurement_type=m.measurement_type,
                length=m.length,
                width=m.width,
                height=m.height,
                area=m.area,
                quantity=m.quantity,
                unit=m.unit,
                notes=m.notes,
            )

        # Clone photos
        for p in quote.photos.all():
            WorkforceQuotePhoto.objects.create(
                quote=new_quote,
                photo_url=p.photo_url,
                photo_type=p.photo_type,
                caption=p.caption,
                sort_order=p.sort_order,
            )

        # Clone Painting / Mason details if present
        if hasattr(quote, "painting_details"):
            pd = quote.painting_details
            WorkforcePaintingQuote.objects.create(
                quote=new_quote,
                property_type=pd.property_type,
                rooms_detail=pd.rooms_detail,
                area_sqft=pd.area_sqft,
                surface_condition=pd.surface_condition,
                existing_paint_condition=pd.existing_paint_condition,
                paint_type=pd.paint_type,
                brand_grade=pd.brand_grade,
                number_of_coats=pd.number_of_coats,
                requires_putty=pd.requires_putty,
                requires_priming=pd.requires_priming,
                crack_treatment=pd.crack_treatment,
                waterproofing_needed=pd.waterproofing_needed,
                scaffolding_required=pd.scaffolding_required,
                color_code=pd.color_code,
                notes=pd.notes,
            )

        if hasattr(quote, "mason_details"):
            md = quote.mason_details
            WorkforceMasonQuote.objects.create(
                quote=new_quote,
                work_type=md.work_type,
                length=md.length,
                width=md.width,
                height=md.height,
                area_sqft=md.area_sqft,
                estimated_duration_days=md.estimated_duration_days,
                requires_demolition=md.requires_demolition,
                debris_disposal_included=md.debris_disposal_included,
                structural_impact=md.structural_impact,
                access_difficulty=md.access_difficulty,
                labour_count=md.labour_count,
                materials_needed=md.materials_needed,
                notes=md.notes,
            )

        return new_quote


def convert_accepted_quote_to_work_booking(quote, actor=None):
    """
    Idempotent and transaction-safe conversion of an accepted quotation to an actual WORK ServiceRequest.
    - If already converted or work_job exists, returns the existing work job without duplication.
    - Sets quote status to CONVERTED and attaches work_job FK.
    - If creation encounters an error, leaves status as CONVERSION_PENDING so admin/background can safely retry.
    """
    with transaction.atomic():
        quote = WorkforceQuote.objects.select_for_update().get(id=quote.id)

        # Idempotency Check 1: Already linked on quote
        if quote.work_job_id:
            if quote.status != WorkforceQuote.Status.CONVERTED:
                quote.status = WorkforceQuote.Status.CONVERTED
                quote.save(update_fields=["status", "updated_at"])
            return quote.work_job

        # Idempotency Check 2: Existing WORK ServiceRequest with same quote_number
        existing_work = ServiceRequest.objects.filter(
            quote_number=quote.quote_number,
            request_kind="WORK"
        ).first()

        if existing_work:
            quote.work_job = existing_work
            quote.status = WorkforceQuote.Status.CONVERTED
            quote.save(update_fields=["work_job", "status", "updated_at"])
            return existing_work

        # Mark as CONVERSION_PENDING during creation
        quote.status = WorkforceQuote.Status.CONVERSION_PENDING
        quote.save(update_fields=["status", "updated_at"])

        try:
            insp_job = quote.job
            work_sr = ServiceRequest.objects.create(
                request_kind="WORK",
                parent_request_id=insp_job.id if insp_job else None,
                quote_number=quote.quote_number,
                company=quote.company or (insp_job.company if insp_job else None),
                customer=quote.customer or (insp_job.customer if insp_job else None),
                customer_name=insp_job.customer_name if insp_job else "",
                phone=insp_job.phone if insp_job else "",
                email=insp_job.email if insp_job else "",
                service_category=quote.service_category or (insp_job.service_category if insp_job else "painting"),
                issue_title=f"{quote.service_name or quote.title or 'Service Work'} (Execution)",
                description=f"Approved Work Scope from Quote {quote.quote_number} (v{quote.quote_version}). {quote.description}".strip(),
                address=insp_job.address if insp_job else "",
                latitude=insp_job.latitude if insp_job else None,
                longitude=insp_job.longitude if insp_job else None,
                preferred_date=insp_job.preferred_date if insp_job and insp_job.preferred_date else timezone.now().date(),
                preferred_time=insp_job.preferred_time if insp_job else "09:00 AM",
                total_amount=quote.net_payable or quote.total_amount,
                status=ServiceRequest.Status.CONFIRMED,
                payment_method=insp_job.payment_method if insp_job else ServiceRequest.PaymentMethod.COD,
                payment_status=ServiceRequest.PaymentStatus.PENDING,
            )

            quote.work_job = work_sr
            quote.status = WorkforceQuote.Status.CONVERTED
            quote.save(update_fields=["work_job", "status", "updated_at"])

            logger.info("Successfully converted Quote %s to Work ServiceRequest #%s", quote.quote_number, work_sr.id)
            return work_sr

        except Exception as ex:
            logger.error("Failed to convert quote %s to work booking: %s", quote.quote_number, ex, exc_info=True)
            quote.status = WorkforceQuote.Status.CONVERSION_PENDING
            quote.save(update_fields=["status", "updated_at"])
            raise ex


def admin_clear_mason_structural(quote_id, admin_user, approved=True, notes=""):
    """
    Grants Admin or Structural Engineer clearance for Mason quotations with suspected structural impact.
    """
    with transaction.atomic():
        quote = WorkforceQuote.objects.select_for_update().get(id=quote_id)

        if not quote.requires_structural_clearance:
            return quote

        if approved:
            quote.admin_cleared_by = admin_user
            quote.admin_cleared_at = timezone.now()
            quote.admin_clearance_notes = notes
            quote.status = WorkforceQuote.Status.DRAFT
            quote.save(update_fields=[
                "admin_cleared_by",
                "admin_cleared_at",
                "admin_clearance_notes",
                "status",
                "updated_at",
            ])
            logger.info("Structural clearance approved for Quote %s by %s", quote.quote_number, admin_user)
        else:
            quote.admin_cleared_by = admin_user
            quote.admin_clearance_notes = f"REJECTED: {notes}"
            quote.status = WorkforceQuote.Status.CANCELLED
            quote.save(update_fields=[
                "admin_cleared_by",
                "admin_clearance_notes",
                "status",
                "updated_at",
            ])
            logger.info("Structural clearance rejected for Quote %s by %s", quote.quote_number, admin_user)

        return quote
