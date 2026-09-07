"""
workforce_api/quote_views.py

HTTP layer for the estimation / quotation workflow.

Context: the models for this feature were deleted by commit 7204699 and restored
in dade298. The service layer (workforce_api/services/quotation_service.py) was
never removed and holds all the business rules. This module is deliberately thin
-- it validates input, enforces tenancy, and delegates. No pricing, state-machine
or conversion logic lives here; that belongs to the service.

Routes (matching frontend/src/api/workforceService.js exactly):

    GET    /api/workforce/quotes/                        list  (tab|status|search|job_id)
    POST   /api/workforce/quotes/                        create
    GET    /api/workforce/quotes/<pk>/                   detail
    PATCH  /api/workforce/quotes/<pk>/                   update draft
    DELETE /api/workforce/quotes/<pk>/                   delete draft
    POST   /api/workforce/quotes/<pk>/items/bulk/        replace items
    POST   /api/workforce/quotes/<pk>/measurements/bulk/ replace measurements
    POST   /api/workforce/quotes/<pk>/inspection/        save inspection
    POST   /api/workforce/quotes/<pk>/send/              send to customer
    POST   /api/workforce/quotes/<pk>/revise/            new revision
"""
import logging
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from workforce_api.models import (
    WorkforceQuote,
    WorkforceQuoteItem,
    WorkforceQuoteMeasurement,
)
from workforce_api.permissions import IsApprovedTechnician
from workforce_api.services import pricing_policy, quotation_service

logger = logging.getLogger(__name__)

# Statuses a quote may still be edited in. Anything sent to a customer is frozen;
# changing it requires a new revision so the customer's copy stays truthful.
EDITABLE_STATUSES = {
    WorkforceQuote.Status.DRAFT,
    WorkforceQuote.Status.CHANGES_REQUESTED,
}

# The tabs the Estimates screen offers, mapped to the statuses behind them.
TAB_FILTERS = {
    "all": None,
    "drafts": [WorkforceQuote.Status.DRAFT],
    "pending": [WorkforceQuote.Status.PENDING_REVIEW],
    "sent": [WorkforceQuote.Status.SENT_TO_CUSTOMER],
    "accepted": [WorkforceQuote.Status.CUSTOMER_ACCEPTED],
    "awaiting_approval": [WorkforceQuote.Status.PENDING_ADMIN_APPROVAL],
    "approved": [WorkforceQuote.Status.ADMIN_APPROVED],
    "rejected": [WorkforceQuote.Status.ADMIN_REJECTED],
    "changes": [WorkforceQuote.Status.CHANGES_REQUESTED],
    "declined": [WorkforceQuote.Status.DECLINED],
    "expired": [WorkforceQuote.Status.EXPIRED],
    "converted": [WorkforceQuote.Status.CONVERTED, WorkforceQuote.Status.CONVERSION_PENDING],
}


# --------------------------------------------------------------------------- #
# tenancy
# --------------------------------------------------------------------------- #
def _employee(request):
    """The Employee behind the request, or None."""
    return getattr(request.user, "employee_profile", None)


def _visible_quotes(request):
    """
    Every quote this caller may see, and nothing more.

    A technician sees quotes they raised. A vendor admin sees everything for
    their company. A platform superuser sees everything. Scoping happens here,
    once, so no individual view can forget it -- getting this wrong on a
    multi-tenant platform means one vendor reading another's commercials.
    """
    qs = WorkforceQuote.objects.select_related("job", "technician", "company", "customer")

    if getattr(request.user, "is_superuser", False):
        return qs

    emp = _employee(request)
    if not emp:
        return qs.none()

    # NB: role is a field on the User model (accounts.User.role), not on
    # Employee, and its choices are lowercase ("admin", "manager", ...).
    role = (getattr(request.user, "role", "") or "").lower()
    if role in ("admin", "manager") and emp.company_id:
        return qs.filter(company_id=emp.company_id)

    # Plain technician: their own work only. company_id is also matched so a
    # reassigned employee cannot reach quotes left behind at a previous vendor.
    scoped = qs.filter(technician_id=emp.id)
    if emp.company_id:
        scoped = scoped.filter(Q(company_id=emp.company_id) | Q(company__isnull=True))
    return scoped


def _get_or_404(request, pk):
    obj = _visible_quotes(request).filter(pk=pk).first()
    if obj is None:
        # Deliberately identical to a genuine 404: a caller must not be able to
        # tell "does not exist" from "belongs to someone else".
        return None, Response({"error": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)
    return obj, None


# --------------------------------------------------------------------------- #
# serialisation
# --------------------------------------------------------------------------- #
def _money(v):
    return float(v) if v is not None else 0.0


def _serialize(q, full=False):
    data = {
        "id": q.id,
        "quote_number": q.quote_number,
        "quote_version": q.quote_version,
        "title": q.title,
        "description": q.description,
        "status": q.status,
        "status_display": q.get_status_display(),
        "service_category": q.service_category,
        "service_name": q.service_name,
        "job_id": q.job_id,
        "work_job_id": q.work_job_id,
        "technician_id": q.technician_id,
        "company_id": q.company_id,
        "customer_id": q.customer_id,
        "customer_name": (q.job.customer_name if q.job_id else "") or "",
        "estimated_labor_cost": _money(q.estimated_labor_cost),
        "estimated_materials_cost": _money(q.estimated_materials_cost),
        "subtotal_amount": _money(q.subtotal_amount),
        "discount_amount": _money(q.discount_amount),
        "tax_amount": _money(q.tax_amount),
        "total_amount": _money(q.total_amount),
        "inspection_fee": _money(q.inspection_fee),
        "inspection_fee_adjusted": _money(q.inspection_fee_adjusted),
        "net_payable": _money(q.net_payable),
        "structural_impact": q.structural_impact,
        "requires_structural_clearance": q.requires_structural_clearance,
        "is_structurally_cleared": q.is_structurally_cleared,
        "customer_decision": q.customer_decision,
        "customer_decline_reason": q.customer_decline_reason,
        "customer_notes": q.customer_notes,
        "valid_until": q.valid_until.isoformat() if q.valid_until else None,
        "sent_at": q.sent_at.isoformat() if q.sent_at else None,
        "customer_decided_at": q.customer_decided_at.isoformat() if q.customer_decided_at else None,
        "created_at": q.created_at.isoformat() if q.created_at else None,
        "updated_at": q.updated_at.isoformat() if q.updated_at else None,
        "is_editable": q.status in EDITABLE_STATUSES,
        "awaiting_admin_approval": q.status == WorkforceQuote.Status.PENDING_ADMIN_APPROVAL,
        "submitted_for_approval_at": q.submitted_for_approval_at.isoformat() if q.submitted_for_approval_at else None,
        "admin_approved_at": q.admin_approved_at.isoformat() if q.admin_approved_at else None,
        "admin_approved_by_id": q.admin_approved_by_id,
        "admin_approval_notes": q.admin_approval_notes,
        "admin_rejection_reason": q.admin_rejection_reason,
    }
    # The decision token is a bearer credential for the customer's accept/decline
    # link. It is never exposed on the technician-facing API.
    if full:
        data["items"] = [
            {
                "id": i.id, "section": i.section, "name": i.name, "description": i.description,
                "item_type": i.item_type, "quantity": _money(i.quantity), "unit": i.unit,
                "unit_price": _money(i.unit_price), "tax_rate": _money(i.tax_rate),
                "discount_amount": _money(i.discount_amount), "total_amount": _money(i.total_amount),
                "material_source": i.material_source, "is_customer_supplied": i.is_customer_supplied,
                "warranty_applicable": i.warranty_applicable,
                "warranty_tier": i.warranty_tier, "notes": i.notes,
                "sort_order": i.sort_order,
            }
            for i in q.items.all().order_by("sort_order", "id")
        ]
        data["measurements"] = [
            {
                "id": m.id, "name": m.name, "measurement_type": m.measurement_type,
                "length": _money(m.length), "width": _money(m.width), "height": _money(m.height),
                "area": _money(m.area), "quantity": _money(m.quantity), "unit": m.unit,
                "notes": m.notes,
            }
            for m in q.measurements.all().order_by("id")
        ]
    return data


def _dec(value, field, default=None):
    """Decimal coercion that reports which field was wrong rather than 500ing."""
    if value in (None, ""):
        if default is None:
            raise ValueError(f"{field} is required.")
        return Decimal(str(default))
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a number (got {value!r}).")


# --------------------------------------------------------------------------- #
# list / create
# --------------------------------------------------------------------------- #
class QuoteListCreateView(APIView):
    permission_classes = [IsApprovedTechnician]

    def get(self, request):
        qs = _visible_quotes(request)

        tab = (request.query_params.get("tab") or "").strip().lower()
        if tab and tab in TAB_FILTERS and TAB_FILTERS[tab]:
            qs = qs.filter(status__in=TAB_FILTERS[tab])

        status_param = (request.query_params.get("status") or "").strip().upper()
        if status_param:
            qs = qs.filter(status=status_param)

        job_id = request.query_params.get("job_id")
        if job_id:
            try:
                qs = qs.filter(job_id=int(job_id))
            except (TypeError, ValueError):
                return Response({"error": "job_id must be an integer."},
                                status=status.HTTP_400_BAD_REQUEST)

        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(quote_number__icontains=search)
                | Q(title__icontains=search)
                | Q(service_name__icontains=search)
                | Q(job__customer_name__icontains=search)
                | Q(job__request_id__icontains=search)
            )

        # A bare JSON array, deliberately. EmployeeEstimatesPage does
        # `setQuotes(data || [])` and then `quotes.filter(...)`, so an envelope
        # such as {"results": [...]} makes the page throw
        # "quotes.filter is not a function". It also derives its own counts from
        # the array, so returning server-side totals would only add four COUNT
        # queries per page load for numbers nobody reads.
        #
        # Capped at 500. If a vendor ever exceeds that this needs pagination, and
        # that means changing the frontend at the same time -- the current shape
        # cannot carry a cursor.
        return Response([_serialize(q) for q in qs[:500]], status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request):
        emp = _employee(request)
        if not emp:
            return Response({"error": "Employee profile not found."}, status=status.HTTP_404_NOT_FOUND)

        job_id = request.data.get("job_id")
        if not job_id:
            return Response({"error": "job_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        from service_requests.models import ServiceRequest
        job = ServiceRequest.objects.filter(pk=job_id).first()
        if not job:
            return Response({"error": "Job not found."}, status=status.HTTP_404_NOT_FOUND)

        # A technician may only quote against a job assigned to them.
        if not getattr(request.user, "is_superuser", False):
            role = (getattr(request.user, "role", "") or "").lower()
            if role not in ("admin", "manager"):
                # Only assigned_employee is used: ServiceRequest.technician_id
                # exists as a database column but is NOT declared on either app's
                # model, so reading it raises AttributeError.
                if job.assigned_employee_id != emp.id:
                    return Response({"error": "This job is not assigned to you."},
                                    status=status.HTTP_403_FORBIDDEN)
            elif emp.company_id and job.company_id and job.company_id != emp.company_id:
                return Response({"error": "This job belongs to another company."},
                                status=status.HTTP_403_FORBIDDEN)

        # The service owns the eligibility rules -- do not duplicate them here.
        # NOTE: can_create_quote returns a TUPLE (bool, detail_dict), not a bool.
        # An earlier version of this view tested `if allowed is False`, which a
        # tuple never satisfies, so the gate silently passed everything through.
        try:
            allowed, detail = quotation_service.can_create_quote(job)
        except Exception as exc:
            logger.exception("[QUOTE_CREATE] can_create_quote failed for job %s", job.id)
            return Response({"error": f"Could not evaluate quote eligibility: {exc}"},
                            status=status.HTTP_400_BAD_REQUEST)
        if not allowed:
            # Pass the service's own reason through verbatim. It distinguishes
            # "not a quotation service" from "pre-service verification incomplete"
            # and names exactly which of the four gates (GPS / OTP / selfie /
            # photos) is outstanding, which is what the technician needs to see.
            detail = detail if isinstance(detail, dict) else {}
            return Response(
                {
                    "error": detail.get("message", "A quotation cannot be created for this job yet."),
                    "code": detail.get("code", "QUOTE_NOT_ALLOWED"),
                    "missing": detail.get("missing", []),
                    "checks": detail.get("checks", {}),
                },
                status=status.HTTP_409_CONFLICT,
            )

        try:
            quote = WorkforceQuote.objects.create(
                job=job,
                technician=emp,
                company_id=job.company_id or emp.company_id,
                customer_id=job.customer_id,
                title=(request.data.get("title") or "Quotation").strip()[:200],
                description=(request.data.get("description") or "").strip(),
                # job.job_type deliberately not used as a fallback: the column
                # exists in the database but is not declared on the model.
                service_category=(request.data.get("service_category") or "").strip()[:150],
                service_name=(request.data.get("service_name") or "").strip()[:200],
                inspection_fee=_dec(request.data.get("inspection_fee"), "inspection_fee", 0),
                status=WorkforceQuote.Status.DRAFT,
            )
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        logger.info("[QUOTE_CREATED] %s for job %s by employee %s",
                    quote.quote_number, job.id, emp.id)
        return Response(_serialize(quote, full=True), status=status.HTTP_201_CREATED)


# --------------------------------------------------------------------------- #
# detail / update / delete
# --------------------------------------------------------------------------- #
class QuoteDetailView(APIView):
    permission_classes = [IsApprovedTechnician]

    def get(self, request, pk):
        quote, err = _get_or_404(request, pk)
        return err or Response(_serialize(quote, full=True), status=status.HTTP_200_OK)

    @transaction.atomic
    def patch(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        if quote.status not in EDITABLE_STATUSES:
            return Response(
                {"error": f"A quotation in state {quote.status} cannot be edited. "
                          f"Create a revision instead."},
                status=status.HTTP_409_CONFLICT,
            )

        text_fields = {"title": 200, "description": None, "service_category": 150,
                       "service_name": 200, "customer_notes": None}
        money_fields = ["estimated_labor_cost", "estimated_materials_cost",
                        "discount_amount", "inspection_fee"]

        try:
            for f, cap in text_fields.items():
                if f in request.data:
                    val = (request.data.get(f) or "").strip()
                    setattr(quote, f, val[:cap] if cap else val)
            for f in money_fields:
                if f in request.data:
                    setattr(quote, f, _dec(request.data.get(f), f, 0))
            if "structural_impact" in request.data:
                val = (request.data.get("structural_impact") or "").strip().upper()
                if val not in WorkforceQuote.StructuralImpact.values:
                    return Response({"error": f"structural_impact must be one of "
                                              f"{list(WorkforceQuote.StructuralImpact.values)}."},
                                    status=status.HTTP_400_BAD_REQUEST)
                quote.structural_impact = val
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        quote.save()
        # Totals are the service's business, not this layer's.
        try:
            quotation_service.recalculate_quote_totals(quote)
            quote.refresh_from_db()
        except Exception:
            logger.exception("[QUOTE_PATCH] recalculate_quote_totals failed for %s", quote.id)

        return Response(_serialize(quote, full=True), status=status.HTTP_200_OK)

    @transaction.atomic
    def delete(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        if quote.status != WorkforceQuote.Status.DRAFT:
            return Response(
                {"error": "Only a DRAFT quotation may be deleted. Anything a customer has "
                          "seen must be cancelled or superseded so the audit trail survives."},
                status=status.HTTP_409_CONFLICT,
            )
        number = quote.quote_number
        quote.delete()
        logger.info("[QUOTE_DELETED] %s by user %s", number, request.user.id)
        return Response(status=status.HTTP_204_NO_CONTENT)


# --------------------------------------------------------------------------- #
# bulk children
# --------------------------------------------------------------------------- #
class QuoteItemsBulkView(APIView):
    """Replaces the whole item set. The builder UI sends the full list each save."""
    permission_classes = [IsApprovedTechnician]

    @transaction.atomic
    def post(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        if quote.status not in EDITABLE_STATUSES:
            return Response({"error": f"Cannot modify items on a {quote.status} quotation."},
                            status=status.HTTP_409_CONFLICT)

        items = request.data.get("items")
        if not isinstance(items, list):
            return Response({"error": "items must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        rows = []
        try:
            for n, raw in enumerate(items):
                if not isinstance(raw, dict):
                    return Response({"error": f"items[{n}] must be an object."},
                                    status=status.HTTP_400_BAD_REQUEST)
                name = (raw.get("name") or "").strip()
                if not name:
                    return Response({"error": f"items[{n}].name is required."},
                                    status=status.HTTP_400_BAD_REQUEST)

                # Customer-supplied material voids the workmanship warranty --
                # expired chemicals or poor sand fail, and the claim lands on
                # SEVO. Rejected unless the category's policy allows it.
                customer_supplied = bool(raw.get("is_customer_supplied", False))
                if customer_supplied and not pricing_policy.allows_customer_supplied_materials(
                    quote.service_category
                ):
                    return Response(
                        {
                            "error": (
                                f"items[{n}] is marked customer-supplied. Customer-supplied "
                                "material is not accepted for this service because it voids "
                                "the workmanship warranty."
                            ),
                            "code": "CUSTOMER_SUPPLIED_NOT_ALLOWED",
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                warranty_tier = str(raw.get("warranty_tier") or "NONE").strip().upper()
                if warranty_tier not in ("NONE", "5_YEAR", "10_YEAR"):
                    return Response(
                        {"error": f"items[{n}].warranty_tier must be NONE, 5_YEAR or 10_YEAR."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                rows.append(WorkforceQuoteItem(
                    quote=quote,
                    section=(raw.get("section") or "").strip()[:100],
                    name=name[:200],
                    description=(raw.get("description") or "").strip(),
                    item_type=(raw.get("item_type") or "LABOR").strip()[:50],
                    quantity=_dec(raw.get("quantity"), f"items[{n}].quantity", 1),
                    unit=(raw.get("unit") or "").strip()[:50],
                    unit_price=_dec(raw.get("unit_price"), f"items[{n}].unit_price", 0),
                    tax_rate=_dec(raw.get("tax_rate"), f"items[{n}].tax_rate", 0),
                    discount_amount=_dec(raw.get("discount_amount"), f"items[{n}].discount_amount", 0),
                    total_amount=_dec(raw.get("total_amount"), f"items[{n}].total_amount", 0),
                    material_source=(raw.get("material_source") or "").strip()[:50],
                    is_customer_supplied=customer_supplied,
                    warranty_applicable=warranty_tier != "NONE",
                    warranty_tier=warranty_tier,
                    notes=(raw.get("notes") or "").strip(),
                    sort_order=int(raw.get("sort_order") or n),
                ))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, OverflowError) as exc:
            return Response({"error": f"Invalid item payload: {exc}"},
                            status=status.HTTP_400_BAD_REQUEST)

        # Atomic swap: nothing is removed unless every replacement validated.
        quote.items.all().delete()
        WorkforceQuoteItem.objects.bulk_create(rows)

        try:
            quotation_service.recalculate_quote_totals(quote)
            quote.refresh_from_db()
        except Exception:
            logger.exception("[QUOTE_ITEMS_BULK] recalculate failed for %s", quote.id)

        return Response(_serialize(quote, full=True), status=status.HTTP_200_OK)


class QuoteMeasurementsBulkView(APIView):
    permission_classes = [IsApprovedTechnician]

    @transaction.atomic
    def post(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        if quote.status not in EDITABLE_STATUSES:
            return Response({"error": f"Cannot modify measurements on a {quote.status} quotation."},
                            status=status.HTTP_409_CONFLICT)

        measurements = request.data.get("measurements")
        if not isinstance(measurements, list):
            return Response({"error": "measurements must be a list."},
                            status=status.HTTP_400_BAD_REQUEST)

        rows = []
        try:
            for n, raw in enumerate(measurements):
                if not isinstance(raw, dict):
                    return Response({"error": f"measurements[{n}] must be an object."},
                                    status=status.HTTP_400_BAD_REQUEST)
                rows.append(WorkforceQuoteMeasurement(
                    quote=quote,
                    name=(raw.get("name") or "").strip()[:200],
                    measurement_type=(raw.get("measurement_type") or "").strip()[:50],
                    length=_dec(raw.get("length"), f"measurements[{n}].length", 0),
                    width=_dec(raw.get("width"), f"measurements[{n}].width", 0),
                    height=_dec(raw.get("height"), f"measurements[{n}].height", 0),
                    area=_dec(raw.get("area"), f"measurements[{n}].area", 0),
                    quantity=_dec(raw.get("quantity"), f"measurements[{n}].quantity", 1),
                    unit=(raw.get("unit") or "").strip()[:50],
                    notes=(raw.get("notes") or "").strip(),
                ))
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        quote.measurements.all().delete()
        WorkforceQuoteMeasurement.objects.bulk_create(rows)
        return Response(_serialize(quote, full=True), status=status.HTTP_200_OK)


class QuoteInspectionView(APIView):
    """
    Stores the trade-specific inspection sheet (painting / mason) attached to a
    quote. The concrete shape differs per trade, so the payload is persisted as
    given onto the matching specialist model when one exists, and otherwise onto
    the quote's description-adjacent fields.
    """
    permission_classes = [IsApprovedTechnician]

    @transaction.atomic
    def post(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        if quote.status not in EDITABLE_STATUSES:
            return Response({"error": f"Cannot modify the inspection on a {quote.status} quotation."},
                            status=status.HTTP_409_CONFLICT)

        payload = request.data if isinstance(request.data, dict) else {}
        trade = (payload.get("trade") or quote.service_category or "").strip().upper()

        try:
            if "PAINT" in trade:
                from workforce_api.models import WorkforcePaintingQuote
                obj, _ = WorkforcePaintingQuote.objects.get_or_create(quote=quote)
            elif "MASON" in trade:
                from workforce_api.models import WorkforceMasonQuote
                obj, _ = WorkforceMasonQuote.objects.get_or_create(quote=quote)
            else:
                obj = None

            if obj is not None:
                editable = {
                    f.name for f in obj._meta.get_fields()
                    if getattr(f, "concrete", False) and f.name not in ("id", "quote")
                }
                for key, value in payload.items():
                    if key in editable:
                        setattr(obj, key, value)
                obj.save()
        except Exception as exc:
            logger.exception("[QUOTE_INSPECTION] failed for quote %s", quote.id)
            return Response({"error": f"Could not save the inspection sheet: {exc}"},
                            status=status.HTTP_400_BAD_REQUEST)

        if "structural_impact" in payload:
            val = (payload.get("structural_impact") or "").strip().upper()
            if val in WorkforceQuote.StructuralImpact.values:
                quote.structural_impact = val
                quote.save(update_fields=["structural_impact", "updated_at"])

        return Response(_serialize(quote, full=True), status=status.HTTP_200_OK)


# --------------------------------------------------------------------------- #
# transitions -- delegated entirely to the service
# --------------------------------------------------------------------------- #
class QuoteSendView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        try:
            valid_days = int(request.data.get("valid_days") or 7)
        except (TypeError, ValueError):
            valid_days = 7
        try:
            quotation_service.send_quote_to_customer(quote.id, actor=request.user, valid_days=valid_days)
        except Exception as exc:
            logger.warning("[QUOTE_SEND] refused for %s: %s", quote.id, exc)
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        quote.refresh_from_db()
        return Response(_serialize(quote, full=True), status=status.HTTP_200_OK)


class QuoteReviseView(APIView):
    permission_classes = [IsApprovedTechnician]

    def post(self, request, pk):
        quote, err = _get_or_404(request, pk)
        if err:
            return err
        notes = (request.data.get("notes") or "").strip()
        try:
            revised = quotation_service.create_revised_quote_version(quote, notes=notes)
        except Exception as exc:
            logger.warning("[QUOTE_REVISE] refused for %s: %s", quote.id, exc)
            return Response({"error": str(exc)}, status=status.HTTP_409_CONFLICT)
        if revised is None:
            return Response({"error": "Could not create a revision of this quotation."},
                            status=status.HTTP_409_CONFLICT)
        return Response(_serialize(revised, full=True), status=status.HTTP_201_CREATED)
