"""
workforce-app/backend/service_requests/vendor_views.py

REST API ViewSets & endpoints for Vendor AC Inspection & Estimation Workflow:
- List & Filter Estimation Leads
- Estimation Detail
- Accept / Confirm Lead
- Assign Technician
- Start Journey & Mark Arrived
- Verify Customer Start OTP
- Save Structured Findings & Upload Defect Photos
- Complete Inspection
- Build, Preview, & Send Formal Versioned Quotation
- Revise Quotation
- Collect or Waive ₹199 Inspection Visit Fee
- Customer Decision Simulator/Receiver
- Available Technicians List
"""
from decimal import Decimal
import logging
import os
import uuid

from django.conf import settings
from django.core.files.storage import default_storage
from django.db import models, transaction
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from service_requests.models import (
    ServiceRequest,
    Estimation,
    EstimationFee,
    Inspection,
    InspectionFinding,
    InspectionPhoto,
    EstimationQuotation,
    EstimationQuotationItem,
    Service,
)
from employees.models import Employee

logger = logging.getLogger("workforce.vendor_estimation")


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 15
    page_size_query_param = "page_size"
    max_page_size = 100


def _serialize_estimation(sr, est=None, full_detail=False):
    """
    Serializes a ServiceRequest & linked Estimation detail into a comprehensive
    vendor-side JSON response.
    """
    if est is None:
        est = getattr(sr, "estimation_details", None)
        if callable(est):
            est = est.first()
        elif hasattr(est, "first"):
            est = est.first()
        else:
            est = Estimation.objects.filter(service_request=sr).first()

    # Fee details
    fee_obj = est.fees.first() if est else None
    fee_data = {
        "id": fee_obj.id if fee_obj else None,
        "amount": float(fee_obj.amount) if fee_obj else 199.00,
        "currency": fee_obj.currency if fee_obj else "INR",
        "status": fee_obj.status if fee_obj else "PENDING",
        "payment_method": fee_obj.payment_method if fee_obj else "",
        "payment_reference": fee_obj.payment_reference if fee_obj else "",
        "waived_reason": fee_obj.waived_reason if fee_obj else "",
        "collected_at": fee_obj.collected_at.isoformat() if fee_obj and fee_obj.collected_at else None,
        "waived_at": fee_obj.waived_at.isoformat() if fee_obj and fee_obj.waived_at else None,
    }

    # Latest quotation
    latest_quote = est.quotations.order_by("-version").first() if est else None
    latest_quote_data = None
    if latest_quote:
        latest_quote_data = {
            "id": latest_quote.id,
            "version": latest_quote.version,
            "quote_ref": latest_quote.quote_ref,
            "status": latest_quote.status,
            "subtotal": float(latest_quote.subtotal),
            "tax_amount": float(latest_quote.tax_amount),
            "discount_amount": float(latest_quote.discount_amount),
            "total_amount": float(latest_quote.total_amount),
            "currency": latest_quote.currency,
            "notes": latest_quote.notes,
            "valid_until": latest_quote.valid_until.isoformat() if latest_quote.valid_until else None,
            "customer_approved_at": latest_quote.customer_approved_at.isoformat() if latest_quote.customer_approved_at else None,
            "customer_rejected_at": latest_quote.customer_rejected_at.isoformat() if latest_quote.customer_rejected_at else None,
            "rejection_reason": latest_quote.rejection_reason,
            "rejection_note": latest_quote.rejection_note,
            "items_count": latest_quote.items.count(),
        }

    # Technician details
    tech_data = {
        "id": sr.technician_id,
        "name": sr.technician_name or (sr.assigned_employee.user.get_full_name() if sr.assigned_employee and sr.assigned_employee.user else ""),
        "phone": sr.technician_phone or (sr.assigned_employee.phone if sr.assigned_employee else ""),
        "location_name": sr.technician_location_name,
        "latitude": sr.technician_latitude,
        "longitude": sr.technician_longitude,
        "arrived_at": sr.technician_arrived_at.isoformat() if sr.technician_arrived_at else None,
    }

    # AC specification
    ac_details = {
        "ac_type": est.ac_type if est else "SPLIT",
        "ac_brand": est.ac_brand if est else "General",
        "ac_capacity": est.ac_capacity if est else "1.5_TON",
        "ac_quantity": est.ac_quantity if est else 1,
        "customer_symptom": est.customer_symptom if est else sr.issue_title,
        "customer_notes": est.customer_notes if est else sr.description,
    }

    data = {
        "id": sr.id,
        "estimation_id": est.id if est else None,
        "request_id": sr.request_id,
        "job_type": sr.job_type or "ESTIMATION",
        "status": (est.status if est else sr.status).upper(),
        "sr_status": sr.status.lower(),
        "customer_name": sr.customer_name or "Valued Customer",
        "phone": sr.phone,
        "email": sr.email,
        "address": sr.address,
        "latitude": sr.latitude,
        "longitude": sr.longitude,
        "preferred_date": sr.preferred_date.isoformat() if sr.preferred_date else None,
        "preferred_time": sr.preferred_time or "10:00 AM - 01:00 PM",
        "start_otp": sr.start_otp,
        "otp_verified": sr.otp_verified,
        "vendor_id": sr.vendor_id,
        "vendor_name": sr.vendor_name,
        "vendor_confirmed_at": sr.vendor_confirmed_at.isoformat() if sr.vendor_confirmed_at else None,
        "total_amount": float(sr.total_amount),
        "ac_details": ac_details,
        "fee": fee_data,
        "technician": tech_data,
        "latest_quotation": latest_quote_data,
        "created_at": sr.created_at.isoformat() if sr.created_at else None,
        "updated_at": sr.updated_at.isoformat() if sr.updated_at else None,
    }

    if full_detail and est:
        # Inspection
        inspection = est.inspections.order_by("-id").first()
        data["inspection"] = None
        data["findings"] = []
        data["photos"] = []
        if inspection:
            data["inspection"] = {
                "id": inspection.id,
                "status": inspection.status,
                "technician_id": inspection.technician_id,
                "technician_external_id": inspection.technician_external_id,
                "technician_name": inspection.technician_name,
                "technician_phone": inspection.technician_phone,
                "diagnosis": inspection.diagnosis,
                "notes": inspection.notes,
                "started_at": inspection.started_at.isoformat() if inspection.started_at else None,
                "completed_at": inspection.completed_at.isoformat() if inspection.completed_at else None,
            }

            # Findings
            for f in inspection.findings.all():
                data["findings"].append({
                    "id": f.id,
                    "finding_type": f.finding_type,
                    "title": f.title,
                    "diagnosis": f.diagnosis,
                    "severity": f.severity,
                    "description": f.description,
                    "recommended_action": f.recommended_action,
                    "quantity": float(f.quantity),
                    "unit": f.unit,
                    "service_id": f.service_id,
                    "sort_order": f.sort_order,
                })

            # Photos
            for p in inspection.photos.all():
                data["photos"].append({
                    "id": p.id,
                    "photo": p.photo,
                    "caption": p.caption,
                    "finding_id": p.finding_id,
                    "uploaded_by": p.uploaded_by,
                    "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else None,
                })

        # All Quotations
        data["quotations"] = []
        for q in est.quotations.all():
            items = []
            for item in q.items.all():
                items.append({
                    "id": item.id,
                    "title": item.service_name,
                    "service_name": item.service_name,
                    "description": item.description,
                    "item_type": getattr(item, "catalog_service_id", "") or "LABOR",
                    "quantity": float(item.quantity),
                    "unit": item.unit,
                    "unit_price": float(item.unit_price),
                    "tax_rate": float(item.tax_rate),
                    "tax_amount": float(item.tax_amount),
                    "discount_amount": float(item.discount_amount),
                    "line_total": float(item.line_total),
                    "sort_order": item.sort_order,
                })
            data["quotations"].append({
                "id": q.id,
                "version": q.version,
                "quote_ref": q.quote_ref,
                "status": q.status,
                "vendor_id": q.vendor_id,
                "technician_id": q.technician_id,
                "subtotal": float(q.subtotal),
                "tax_amount": float(q.tax_amount),
                "discount_amount": float(q.discount_amount),
                "total_amount": float(q.total_amount),
                "currency": q.currency,
                "notes": q.notes,
                "valid_until": q.valid_until.isoformat() if q.valid_until else None,
                "customer_approved_at": q.customer_approved_at.isoformat() if q.customer_approved_at else None,
                "customer_rejected_at": q.customer_rejected_at.isoformat() if q.customer_rejected_at else None,
                "rejection_reason": q.rejection_reason,
                "rejection_note": q.rejection_note,
                "items": items,
                "created_at": q.created_at.isoformat() if q.created_at else None,
            })

    return data


def _get_target_estimation(pk):
    """
    Resolves ServiceRequest and linked Estimation by ID (either ServiceRequest.id or Estimation.id).
    Returns (sr, est).
    """
    sr = ServiceRequest.objects.filter(pk=pk).first()
    if sr:
        est = Estimation.objects.filter(service_request=sr).first()
        if not est and (sr.job_type == "ESTIMATION" or "ac" in sr.service_category.lower() or "ac" in sr.issue_title.lower()):
            # Lazily ensure linked Estimation detail exists
            est = Estimation.objects.create(
                service_request=sr,
                ac_type="SPLIT",
                ac_brand="General",
                ac_capacity="1.5_TON",
                ac_quantity=1,
                customer_symptom=sr.issue_title,
                status=sr.status.upper(),
            )
            # Ensure ₹199 inspection fee record exists
            EstimationFee.objects.get_or_create(
                estimation=est,
                defaults={"amount": Decimal("199.00"), "currency": "INR", "status": "PENDING"}
            )
        return sr, est

    # Attempt lookup by Estimation.id directly
    est = Estimation.objects.filter(pk=pk).first()
    if est:
        return est.service_request, est

    return None, None


class VendorEstimationListView(APIView):
    """
    GET /api/vendor/estimations/?status=<STATUS>&date=<YYYY-MM-DD>&search=<QUERY>
    Lists estimation requests with filtering and pagination.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = ServiceRequest.objects.filter(
            models.Q(job_type="ESTIMATION") | models.Q(request_kind="ESTIMATION") | models.Q(service_category__icontains="ac")
        ).distinct()

        # Status filter
        status_filter = request.query_params.get("status", "").strip().lower()
        if status_filter and status_filter != "all":
            # Map common statuses
            if status_filter in ["requested", "new"]:
                qs = qs.filter(status__in=["requested", "new_request", "unassigned", "confirmed"])
            elif status_filter in ["vendor_confirmed", "confirmed"]:
                qs = qs.filter(status="vendor_confirmed")
            elif status_filter in ["assigned", "technician_assigned"]:
                qs = qs.filter(status__in=["technician_assigned", "assigned"])
            elif status_filter in ["in_progress", "inspection_in_progress", "arrived", "on_the_way"]:
                qs = qs.filter(status__in=[
                    "technician_on_the_way", "technician_arrived",
                    "inspection_in_progress", "in_progress"
                ])
            elif status_filter in ["quotation_sent"]:
                qs = qs.filter(status="quotation_sent")
            elif status_filter in ["completed", "customer_approved", "closed"]:
                qs = qs.filter(status__in=["customer_approved", "completed", "closed"])
            else:
                qs = qs.filter(status__iexact=status_filter)

        # Date filter
        date_param = request.query_params.get("date", "").strip()
        if date_param:
            try:
                qs = qs.filter(preferred_date=date_param)
            except Exception:
                pass

        # Search query
        search = request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(
                models.Q(customer_name__icontains=search)
                | models.Q(phone__icontains=search)
                | models.Q(request_id__icontains=search)
                | models.Q(issue_title__icontains=search)
                | models.Q(address__icontains=search)
            )

        qs = qs.order_by("-id")

        # Metric counts across entire dataset
        all_est_qs = ServiceRequest.objects.filter(
            models.Q(job_type="ESTIMATION") | models.Q(request_kind="ESTIMATION") | models.Q(service_category__icontains="ac")
        )
        metrics = {
            "all": all_est_qs.count(),
            "requested": all_est_qs.filter(status__in=["requested", "new_request", "unassigned", "confirmed"]).count(),
            "assigned": all_est_qs.filter(status__in=["technician_assigned", "assigned", "vendor_confirmed"]).count(),
            "in_progress": all_est_qs.filter(status__in=["technician_on_the_way", "technician_arrived", "inspection_in_progress", "in_progress", "inspection_completed"]).count(),
            "quotation_sent": all_est_qs.filter(status="quotation_sent").count(),
            "completed": all_est_qs.filter(status__in=["completed", "customer_approved", "closed"]).count(),
        }

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(qs, request)
        results = [_serialize_estimation(sr) for sr in page]

        response = paginator.get_paginated_response(results)
        response.data["metrics"] = metrics
        return response


class VendorEstimationDetailView(APIView):
    """
    GET /api/vendor/estimations/{id}/
    Detailed view of a single estimation including findings, photos, and quotations.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        data = _serialize_estimation(sr, est, full_detail=True)
        return Response(data)


class VendorEstimationConfirmView(APIView):
    """
    POST /api/vendor/estimations/{id}/confirm/
    Atomically updates vendor_id and advances status to VENDOR_CONFIRMED.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Lock rows
        sr = ServiceRequest.objects.select_for_update().get(pk=sr.pk)
        if est:
            est = Estimation.objects.select_for_update().get(pk=est.pk)

        vendor_id = str(request.data.get("vendor_id") or getattr(request.user, "company_id", "") or request.user.id)
        vendor_name = str(request.data.get("vendor_name") or (request.user.company.company_name if getattr(request.user, "company", None) else request.user.get_full_name()))

        now = timezone.now()
        sr.vendor_id = vendor_id
        sr.vendor_name = vendor_name
        sr.vendor_confirmed_at = now
        sr.status = "vendor_confirmed"
        sr.save(update_fields=["vendor_id", "vendor_name", "vendor_confirmed_at", "status", "updated_at"])

        if est:
            est.status = "VENDOR_CONFIRMED"
            est.save(update_fields=["status", "updated_at"])

        logger.info(f"[VENDOR_ESTIMATION] Lead #{sr.id} confirmed by vendor {vendor_name} ({vendor_id})")
        return Response({
            "success": True,
            "message": "Estimation lead confirmed successfully.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorEstimationAssignTechnicianView(APIView):
    """
    POST /api/vendor/estimations/{id}/assign-technician/
    Body: { technician_id, technician_name, technician_phone }
    Creates or updates service_requests_inspection record and advances status to TECHNICIAN_ASSIGNED.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        tech_id = request.data.get("technician_id")
        tech_name = request.data.get("technician_name")
        tech_phone = request.data.get("technician_phone")

        # If technician_id is an Employee PK or User PK, populate details
        user_tech = None
        if tech_id:
            try:
                emp = Employee.objects.filter(pk=tech_id).select_related("user").first()
                if emp:
                    tech_name = tech_name or emp.user.get_full_name()
                    tech_phone = tech_phone or emp.phone
                    user_tech = emp.user
                else:
                    from accounts.models import User
                    u = User.objects.filter(pk=tech_id).first()
                    if u:
                        tech_name = tech_name or u.get_full_name()
                        tech_phone = tech_phone or u.phone
                        user_tech = u
            except Exception as e:
                logger.warning(f"Could not resolve technician user: {e}")

        if not tech_name:
            return Response({"error": "technician_name is required.", "code": "INVALID_INPUT"}, status=status.HTTP_400_BAD_REQUEST)

        user_tech_id = user_tech.id if user_tech else None

        sr = ServiceRequest.objects.select_for_update().get(pk=sr.pk)
        sr.technician_name = tech_name
        sr.technician_phone = tech_phone or ""
        sr.technician_id = user_tech_id
        sr.status = "technician_assigned"
        sr.save(update_fields=["technician_name", "technician_phone", "technician_id", "status", "updated_at"])

        if est:
            est = Estimation.objects.select_for_update().get(pk=est.pk)
            est.status = "TECHNICIAN_ASSIGNED"
            est.save(update_fields=["status", "updated_at"])

            # Create or update Inspection record
            inspection, _ = Inspection.objects.get_or_create(
                estimation=est,
                defaults={
                    "technician": user_tech,
                    "technician_external_id": str(tech_id or ""),
                    "technician_name": tech_name,
                    "technician_phone": tech_phone or "",
                    "status": "PENDING",
                    "diagnosis": "",
                    "notes": "",
                }
            )
            inspection.technician = user_tech
            inspection.technician_name = tech_name
            inspection.technician_phone = tech_phone or ""
            inspection.technician_external_id = str(tech_id or "")
            inspection.save()

        logger.info(f"[VENDOR_ESTIMATION] Technician {tech_name} assigned to Estimation #{sr.id}")
        return Response({
            "success": True,
            "message": f"Technician {tech_name} assigned successfully.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorEstimationStartJourneyView(APIView):
    """
    POST /api/vendor/estimations/{id}/start-journey/
    Advances status to TECHNICIAN_ON_THE_WAY.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        sr.status = "technician_on_the_way"
        sr.save(update_fields=["status", "updated_at"])
        if est:
            est.status = "TECHNICIAN_ON_THE_WAY"
            est.save(update_fields=["status", "updated_at"])

        return Response({
            "success": True,
            "message": "Trip started. Status set to TECHNICIAN_ON_THE_WAY.",
            "data": _serialize_estimation(sr, est)
        })


class VendorEstimationArrivedView(APIView):
    """
    POST /api/vendor/estimations/{id}/arrived/
    Advances status to TECHNICIAN_ARRIVED.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        sr.status = "technician_arrived"
        sr.technician_arrived_at = timezone.now()
        sr.save(update_fields=["status", "technician_arrived_at", "updated_at"])
        if est:
            est.status = "TECHNICIAN_ARRIVED"
            est.save(update_fields=["status", "updated_at"])

        return Response({
            "success": True,
            "message": "Technician arrived on-site.",
            "data": _serialize_estimation(sr, est)
        })


class VendorEstimationVerifyOtpView(APIView):
    """
    POST /api/vendor/estimations/{id}/verify-otp/
    Body: { otp: "123456" }
    Validates against service_requests_servicerequest.start_otp.
    On match, advances status to INSPECTION_IN_PROGRESS.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        provided_otp = str(request.data.get("otp", "")).strip()
        expected_otp = str(sr.start_otp or "").strip()

        if not provided_otp:
            return Response({"error": "OTP is required.", "code": "OTP_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

        # Allow matching if expected_otp matches or fallback test bypass in development
        is_match = (provided_otp == expected_otp) or (settings.DEBUG and provided_otp in ["123456", "000000"])

        if not is_match:
            return Response({
                "error": "Invalid start OTP. Please verify with customer.",
                "code": "INVALID_OTP"
            }, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        sr.otp_verified = True
        sr.otp_verified_at = now
        sr.status = "inspection_in_progress"
        sr.started_at = sr.started_at or now
        sr.save(update_fields=["otp_verified", "otp_verified_at", "status", "started_at", "updated_at"])

        if est:
            est.status = "INSPECTION_IN_PROGRESS"
            est.save(update_fields=["status", "updated_at"])

            inspection, _ = Inspection.objects.get_or_create(
                estimation=est,
                defaults={"technician_name": sr.technician_name, "status": "IN_PROGRESS", "diagnosis": "", "notes": ""}
            )
            inspection.status = "IN_PROGRESS"
            inspection.started_at = inspection.started_at or now
            inspection.save()

        logger.info(f"[VENDOR_ESTIMATION] OTP verified for Estimation #{sr.id}. Status -> INSPECTION_IN_PROGRESS")
        return Response({
            "success": True,
            "message": "OTP verified successfully. Inspection commenced.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorEstimationFindingsView(APIView):
    """
    POST /api/vendor/estimations/{id}/inspection/findings/
    Body: [{ finding_type, title, severity, description, recommended_action, quantity, unit, service_id }]
    Saves structured inspection findings.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        findings_data = request.data
        if isinstance(findings_data, dict) and "findings" in findings_data:
            findings_data = findings_data["findings"]

        if not isinstance(findings_data, list):
            return Response({"error": "Body must be a list of findings or object with 'findings' array.", "code": "INVALID_FORMAT"}, status=status.HTTP_400_BAD_REQUEST)

        inspection, _ = Inspection.objects.get_or_create(
            estimation=est,
            defaults={"technician_name": sr.technician_name, "status": "IN_PROGRESS", "diagnosis": "", "notes": ""}
        )

        # Clear existing findings for clean overwrite / update
        inspection.findings.all().delete()

        created_findings = []
        for idx, item in enumerate(findings_data):
            title = item.get("title") or item.get("finding_type") or "AC Defect"
            f = InspectionFinding.objects.create(
                inspection=inspection,
                finding_type=item.get("finding_type", "Other"),
                title=title,
                diagnosis=item.get("diagnosis", ""),
                severity=item.get("severity", "MEDIUM").upper(),
                description=item.get("description", ""),
                recommended_action=item.get("recommended_action", ""),
                quantity=Decimal(str(item.get("quantity", 1.0))),
                unit=item.get("unit", "unit"),
                sort_order=idx,
                service_id=item.get("service_id") if item.get("service_id") else None,
            )
            created_findings.append({
                "id": f.id,
                "finding_type": f.finding_type,
                "title": f.title,
                "severity": f.severity,
                "description": f.description,
                "recommended_action": f.recommended_action,
                "quantity": float(f.quantity),
                "unit": f.unit,
            })

        return Response({
            "success": True,
            "count": len(created_findings),
            "findings": created_findings,
        })


class VendorEstimationPhotosView(APIView):
    """
    POST /api/vendor/estimations/{id}/inspection/photos/
    Multipart photo upload.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        inspection, _ = Inspection.objects.get_or_create(
            estimation=est,
            defaults={"technician_name": sr.technician_name, "status": "IN_PROGRESS", "diagnosis": "", "notes": ""}
        )

        file_obj = request.FILES.get("photo") or request.FILES.get("file")
        caption = request.data.get("caption", "")
        finding_id = request.data.get("finding_id")

        if not file_obj:
            # Allow fallback string url if passed in JSON body
            photo_url = request.data.get("photo_url") or request.data.get("photo")
            if not photo_url:
                return Response({"error": "No photo file or photo_url provided.", "code": "PHOTO_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            filename = f"inspection_{est.id}_{uuid.uuid4().hex[:8]}_{file_obj.name}"
            saved_path = default_storage.save(f"service_requests/inspection_photos/{filename}", file_obj)
            photo_url = default_storage.url(saved_path)

        photo_rec = InspectionPhoto.objects.create(
            inspection=inspection,
            finding_id=finding_id if finding_id and str(finding_id).isdigit() else None,
            photo=photo_url,
            caption=caption or "Defect photo",
            uploaded_by=request.user.username or "vendor",
        )

        return Response({
            "success": True,
            "photo": {
                "id": photo_rec.id,
                "photo": photo_rec.photo,
                "caption": photo_rec.caption,
                "finding_id": photo_rec.finding_id,
                "uploaded_at": photo_rec.uploaded_at.isoformat(),
            }
        }, status=status.HTTP_201_CREATED)


class VendorEstimationInspectionCompleteView(APIView):
    """
    POST /api/vendor/estimations/{id}/inspection/complete/
    Body: { diagnosis_summary, notes }
    Advances status to INSPECTION_COMPLETED.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        diagnosis_summary = request.data.get("diagnosis_summary") or request.data.get("diagnosis") or "Inspection completed."
        notes = request.data.get("notes", "")

        now = timezone.now()
        inspection, _ = Inspection.objects.get_or_create(
            estimation=est,
            defaults={"technician_name": sr.technician_name, "status": "IN_PROGRESS"}
        )
        inspection.diagnosis = diagnosis_summary
        inspection.notes = notes
        inspection.status = "COMPLETED"
        inspection.completed_at = now
        inspection.save()

        sr.status = "inspection_completed"
        sr.save(update_fields=["status", "updated_at"])

        est.status = "INSPECTION_COMPLETED"
        est.save(update_fields=["status", "updated_at"])

        logger.info(f"[VENDOR_ESTIMATION] Inspection completed for #{sr.id}")
        return Response({
            "success": True,
            "message": "Inspection marked completed. Ready to build quotation.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorEstimationQuotationView(APIView):
    """
    POST /api/vendor/estimations/{id}/quotation/ (Draft / Preview / Save)
    Creates or updates a versioned quotation with line items and calculated totals.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        data = request.data
        items_data = data.get("items", [])
        if not items_data:
            return Response({"error": "At least one quotation line item is required.", "code": "ITEMS_REQUIRED"}, status=status.HTTP_400_BAD_REQUEST)

        valid_until = data.get("valid_until") or (timezone.now() + timezone.timedelta(days=7)).date()
        tax_rate_percent = Decimal(str(data.get("tax_rate_percent", 18.0)))
        discount_amount = Decimal(str(data.get("discount_amount", 0.0)))
        notes = str(data.get("notes") or "Includes 90-day warranty on parts and labor.")

        # Calculate line items
        subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        computed_items = []

        for idx, item in enumerate(items_data):
            title = str(item.get("title") or item.get("service_name") or f"Item #{idx + 1}")
            qty = Decimal(str(item.get("quantity", 1)))
            unit_price = Decimal(str(item.get("unit_price", 0)))
            item_tax_rate = Decimal(str(item.get("tax_rate", tax_rate_percent)))
            item_discount = Decimal(str(item.get("discount_amount", 0)))

            line_base = (qty * unit_price).quantize(Decimal("0.01"))
            line_tax = (line_base * (item_tax_rate / Decimal("100"))).quantize(Decimal("0.01"))
            line_total = (line_base + line_tax - item_discount).quantize(Decimal("0.01"))

            subtotal += line_base
            total_tax += line_tax

            computed_items.append({
                "service_name": title,
                "description": item.get("description", ""),
                "item_type": item.get("item_type", "LABOR"),
                "quantity": qty,
                "unit": item.get("unit", "unit"),
                "unit_price": unit_price,
                "tax_rate": item_tax_rate,
                "tax_amount": line_tax,
                "discount_amount": item_discount,
                "line_total": line_total,
                "service_id": item.get("service_id") if item.get("service_id") else None,
                "sort_order": idx,
            })

        total_amount = max(Decimal("0.00"), subtotal + total_tax - discount_amount)

        # Check existing draft quote for this estimation to update, or increment version
        existing_draft = est.quotations.filter(status="DRAFT").order_by("-version").first()
        if existing_draft:
            quote = existing_draft
            quote.subtotal = subtotal
            quote.tax_amount = total_tax
            quote.discount_amount = discount_amount
            quote.total_amount = total_amount
            quote.valid_until = valid_until
            quote.notes = notes
            quote.save()
            quote.items.all().delete()
        else:
            highest_version = est.quotations.order_by("-version").values_list("version", flat=True).first() or 0
            new_version = highest_version + 1
            quote_ref = f"QTE-{sr.request_id or f'AC{sr.id}'}-V{new_version}"

            quote = EstimationQuotation.objects.create(
                estimation=est,
                version=new_version,
                quote_ref=quote_ref,
                status="DRAFT",
                vendor_id=sr.vendor_id or str(request.user.id),
                technician_id=str(sr.technician_id or ""),
                subtotal=subtotal,
                tax_amount=total_tax,
                discount_amount=discount_amount,
                total_amount=total_amount,
                currency="INR",
                notes=notes,
                valid_until=valid_until,
                rejection_reason="",
                rejection_note="",
            )

        for c_item in computed_items:
            EstimationQuotationItem.objects.create(
                quotation=quote,
                catalog_service_id=c_item["item_type"],
                service_name=c_item["service_name"],
                description=c_item["description"],
                quantity=c_item["quantity"],
                unit=c_item["unit"],
                unit_price=c_item["unit_price"],
                tax_rate=c_item["tax_rate"],
                tax_amount=c_item["tax_amount"],
                discount_amount=c_item["discount_amount"],
                line_total=c_item["line_total"],
                sort_order=c_item["sort_order"],
                service_id=c_item["service_id"],
            )

        logger.info(f"[VENDOR_ESTIMATION] Quotation #{quote.id} ({quote.quote_ref}) saved. Total: ₹{quote.total_amount}")
        return Response({
            "success": True,
            "message": f"Quotation {quote.quote_ref} saved as DRAFT.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        }, status=status.HTTP_201_CREATED)


class VendorEstimationQuotationSendView(APIView):
    """
    POST /api/vendor/estimations/{id}/quotation/{quote_id}/send/
    Publishes quotation to customer. Advances status to QUOTATION_SENT.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, quote_id):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        quote = est.quotations.filter(pk=quote_id).first()
        if not quote:
            return Response({"error": f"Quotation #{quote_id} not found on Estimation #{pk}.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        quote.status = "SENT"
        quote.save(update_fields=["status", "updated_at"])

        sr.status = "quotation_sent"
        sr.total_amount = quote.total_amount
        sr.save(update_fields=["status", "total_amount", "updated_at"])

        est.status = "QUOTATION_SENT"
        est.save(update_fields=["status", "updated_at"])

        logger.info(f"[VENDOR_ESTIMATION] Quotation {quote.quote_ref} sent to customer for Estimation #{sr.id}")
        return Response({
            "success": True,
            "message": f"Quotation {quote.quote_ref} sent to customer.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorEstimationQuotationReviseView(APIView):
    """
    POST /api/vendor/estimations/{id}/quotation/{quote_id}/revise/
    Clones a rejected/superseded quote into a new incremented version (DRAFT).
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk, quote_id):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        orig_quote = est.quotations.filter(pk=quote_id).first()
        if not orig_quote:
            return Response({"error": f"Quotation #{quote_id} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        # Mark previous quote superseded
        if orig_quote.status in ["SENT", "REJECTED"]:
            orig_quote.status = "SUPERSEDED"
            orig_quote.save(update_fields=["status", "updated_at"])

        highest_version = est.quotations.order_by("-version").values_list("version", flat=True).first() or orig_quote.version
        new_version = highest_version + 1
        new_ref = f"QTE-{sr.request_id or f'AC{sr.id}'}-V{new_version}"

        new_quote = EstimationQuotation.objects.create(
            estimation=est,
            version=new_version,
            quote_ref=new_ref,
            status="DRAFT",
            vendor_id=orig_quote.vendor_id,
            technician_id=orig_quote.technician_id,
            subtotal=orig_quote.subtotal,
            tax_amount=orig_quote.tax_amount,
            discount_amount=orig_quote.discount_amount,
            total_amount=orig_quote.total_amount,
            currency=orig_quote.currency,
            notes=orig_quote.notes,
            valid_until=(timezone.now() + timezone.timedelta(days=7)).date(),
            rejection_reason="",
            rejection_note="",
        )

        for it in orig_quote.items.all():
            EstimationQuotationItem.objects.create(
                quotation=new_quote,
                catalog_service_id=it.catalog_service_id,
                service_name=it.service_name,
                description=it.description,
                quantity=it.quantity,
                unit=it.unit,
                unit_price=it.unit_price,
                tax_rate=it.tax_rate,
                tax_amount=it.tax_amount,
                discount_amount=it.discount_amount,
                line_total=it.line_total,
                sort_order=it.sort_order,
                service_id=it.service_id,
            )

        return Response({
            "success": True,
            "message": f"Revised Quotation {new_ref} created.",
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorEstimationFeeCollectView(APIView):
    """
    POST /api/vendor/estimations/{id}/fee/collect/
    Body: { payment_method: "CASH" | "UPI", payment_reference: "..." }
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        fee = est.fees.first()
        if not fee:
            fee = EstimationFee.objects.create(
                estimation=est,
                amount=Decimal("199.00"),
                currency="INR",
                status="PENDING",
            )

        method = request.data.get("payment_method", "CASH").upper()
        ref = request.data.get("payment_reference", "")

        fee.status = "COLLECTED"
        fee.payment_method = method
        fee.payment_reference = ref
        fee.collected_at = timezone.now()
        fee.save()

        return Response({
            "success": True,
            "message": f"Inspection fee of ₹{fee.amount} marked COLLECTED ({method}).",
            "fee": {
                "id": fee.id,
                "amount": float(fee.amount),
                "status": fee.status,
                "payment_method": fee.payment_method,
                "payment_reference": fee.payment_reference,
                "collected_at": fee.collected_at.isoformat(),
            }
        })


class VendorEstimationFeeWaiveView(APIView):
    """
    POST /api/vendor/estimations/{id}/fee/waive/
    Body: { reason: "..." }
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        fee = est.fees.first()
        if not fee:
            fee = EstimationFee.objects.create(
                estimation=est,
                amount=Decimal("199.00"),
                currency="INR",
                status="PENDING",
            )

        reason = request.data.get("reason") or "Inspection fee waived by vendor."

        fee.status = "WAIVED"
        fee.waived_reason = reason
        fee.waived_at = timezone.now()
        fee.waived_by = request.user if request.user.is_authenticated else None
        fee.save()

        return Response({
            "success": True,
            "message": f"Inspection fee of ₹{fee.amount} marked WAIVED.",
            "fee": {
                "id": fee.id,
                "amount": float(fee.amount),
                "status": fee.status,
                "waived_reason": fee.waived_reason,
                "waived_at": fee.waived_at.isoformat(),
            }
        })


class VendorEstimationCustomerDecideView(APIView):
    """
    POST /api/vendor/estimations/{id}/customer-decide/
    Body: { decision: "APPROVE" | "REJECT", rejection_reason: "...", rejection_note: "..." }
    Simulates / receives the Customer's decision on the latest Quotation.
    """
    permission_classes = [permissions.IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        sr, est = _get_target_estimation(pk)
        if not sr or not est:
            return Response({"error": f"Estimation #{pk} not found.", "code": "NOT_FOUND"}, status=status.HTTP_404_NOT_FOUND)

        decision = str(request.data.get("decision", "APPROVE")).upper()
        rejection_reason = request.data.get("rejection_reason", "PRICE_TOO_HIGH")
        rejection_note = request.data.get("rejection_note", "")

        quote = est.quotations.order_by("-version").first()
        if not quote:
            return Response({"error": "No quotation exists for this estimation to decide upon.", "code": "NO_QUOTE"}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()
        if decision == "APPROVE":
            quote.status = "APPROVED"
            quote.customer_approved_at = now
            quote.save(update_fields=["status", "customer_approved_at", "updated_at"])

            sr.status = "customer_approved"
            sr.save(update_fields=["status", "updated_at"])

            est.status = "CUSTOMER_APPROVED"
            est.save(update_fields=["status", "updated_at"])

            message = "Quotation approved by customer. Ready to commence repair service."
        else:
            quote.status = "REJECTED"
            quote.customer_rejected_at = now
            quote.rejection_reason = rejection_reason
            quote.rejection_note = rejection_note
            quote.save(update_fields=["status", "customer_rejected_at", "rejection_reason", "rejection_note", "updated_at"])

            sr.status = "customer_rejected"
            sr.save(update_fields=["status", "updated_at"])

            est.status = "CUSTOMER_REJECTED"
            est.save(update_fields=["status", "updated_at"])

            message = f"Quotation rejected by customer: {rejection_reason}."

        return Response({
            "success": True,
            "decision": decision,
            "message": message,
            "data": _serialize_estimation(sr, est, full_detail=True)
        })


class VendorTechniciansListView(APIView):
    """
    GET /api/vendor/technicians/
    Returns list of eligible technicians/employees for assignment.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        company_id = getattr(request.user, "company_id", None)
        qs = Employee.objects.all().select_related("user")
        if company_id:
            qs = qs.filter(company_id=company_id)

        technicians = []
        for emp in qs[:50]:
            user = emp.user
            technicians.append({
                "id": emp.id,
                "employee_id": emp.employee_id,
                "name": user.get_full_name() if user else emp.employee_id,
                "phone": emp.phone or (user.phone if user else ""),
                "title": emp.title or "AC Technician",
                "is_online": emp.is_online,
                "availability": emp.current_availability,
            })

        return Response({"technicians": technicians})
