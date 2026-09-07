"""
workforce_api/invoice_views.py

HTTP layer for the second half of the estimation workflow: the customer's
decision, the SEVO admin's approval, and the invoice that follows.

    GET    /api/workforce/quotes/decision/<token>/     customer views the quote
    POST   /api/workforce/quotes/decision/<token>/     customer accepts/declines
    GET    /api/workforce/quotes/pending-approval/     SEVO admin queue
    POST   /api/workforce/quotes/<pk>/admin-review/    SEVO admin decides
    GET    /api/workforce/invoices/                    list (scoped)
    GET    /api/workforce/invoices/<pk>/               detail
    POST   /api/workforce/invoices/<pk>/payments/      record a customer payment
    POST   /api/workforce/invoices/<pk>/cancel/        void an unpaid invoice

Like quote_views, this module is thin: it authenticates, scopes, validates and
delegates. Every state change lives in services/quotation_service.py or
services/invoice_service.py.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny, BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import is_admin_role
from workforce_api.models import WorkforceInvoice, WorkforceQuote
from workforce_api.services import invoice_service, quotation_service
from workforce_api.quote_views import _serialize as _serialize_quote

logger = logging.getLogger(__name__)


class IsSevoAdmin(BasePermission):
    """
    The SEVO back office, not a vendor's own admin.

    Approving a quote authorises work and issues an invoice on SEVO's behalf,
    so it must not be reachable by a vendor administering their own company --
    that would let a provider approve their own commercials. Platform
    superusers, and staff users holding an admin role, qualify.
    """
    message = "Only SEVO platform administrators can approve quotations."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if getattr(user, "is_superuser", False):
            return True
        return bool(getattr(user, "is_staff", False) and is_admin_role(user))


# --------------------------------------------------------------------------- #
# serialisation
# --------------------------------------------------------------------------- #
def _money(v):
    return float(v) if v is not None else 0.0


def _serialize_invoice(inv, full=False):
    data = {
        "id": inv.id,
        "invoice_number": inv.invoice_number,
        "status": inv.status,
        "status_display": inv.get_status_display(),
        "quote_id": inv.quote_id,
        "quote_number": inv.quote.quote_number if inv.quote_id else None,
        "job_id": inv.job_id,
        "customer_id": inv.customer_id,
        "company_id": inv.company_id,
        "technician_id": inv.technician_id,
        "bill_to_name": inv.bill_to_name,
        "bill_to_phone": inv.bill_to_phone,
        "bill_to_email": inv.bill_to_email,
        "bill_to_address": inv.bill_to_address,
        "service_category": inv.service_category,
        "service_name": inv.service_name,
        "subtotal_amount": _money(inv.subtotal_amount),
        "discount_amount": _money(inv.discount_amount),
        "tax_amount": _money(inv.tax_amount),
        "inspection_fee_adjusted": _money(inv.inspection_fee_adjusted),
        "total_amount": _money(inv.total_amount),
        "amount_paid": _money(inv.amount_paid),
        "balance_due": _money(inv.balance_due),
        "currency": inv.currency,
        "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
        "due_at": inv.due_at.isoformat() if inv.due_at else None,
        "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
        "notes": inv.notes,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }
    if full:
        data["items"] = [
            {
                "id": i.id, "section": i.section, "name": i.name,
                "description": i.description, "item_type": i.item_type,
                "quantity": _money(i.quantity), "unit": i.unit,
                "unit_price": _money(i.unit_price), "tax_rate": _money(i.tax_rate),
                "discount_amount": _money(i.discount_amount),
                "line_total": _money(i.line_total), "sort_order": i.sort_order,
            }
            for i in inv.items.all()
        ]
        data["payments"] = [
            {
                "id": p.id, "amount": _money(p.amount), "method": p.method,
                "status": p.status, "reference": p.reference, "gateway": p.gateway,
                "paid_at": p.paid_at.isoformat() if p.paid_at else None,
                "ledger_entry_id": p.ledger_entry_id,
            }
            for p in inv.payments.all()
        ]
    return data


def _dec(value, field):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError(f"{field} must be a number (got {value!r}).")


# --------------------------------------------------------------------------- #
# customer decision (token-authenticated, no login)
# --------------------------------------------------------------------------- #
class QuoteCustomerDecisionView(APIView):
    """
    The customer's copy of a quotation, reached by the decision token minted
    when the technician sent it. The token IS the credential -- there is no
    session here, because the customer may open the link on a device that has
    never signed in.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def _load(self, token):
        # Tokens are secrets.token_urlsafe(32). Anything materially shorter is
        # a probe, not a real link; reject before touching the database.
        if not token or len(token) < 20:
            return None
        return (
            WorkforceQuote.objects
            .select_related("job", "technician", "company", "customer")
            .filter(decision_token=token)
            .first()
        )

    def get(self, request, token):
        quote = self._load(token)
        if quote is None:
            return Response({"error": "This quotation link is not valid."},
                            status=status.HTTP_404_NOT_FOUND)

        data = _serialize_quote(quote, full=True)
        expired = bool(quote.valid_until and quote.valid_until < timezone.now())
        data["is_expired"] = expired
        data["can_decide"] = (
            not expired
            and quote.status == WorkforceQuote.Status.SENT_TO_CUSTOMER
        )
        invoice = quote.invoices.exclude(status=WorkforceInvoice.Status.CANCELLED).first()
        data["invoice"] = _serialize_invoice(invoice, full=True) if invoice else None
        return Response(data)

    def post(self, request, token):
        quote = self._load(token)
        if quote is None:
            return Response({"error": "This quotation link is not valid."},
                            status=status.HTTP_404_NOT_FOUND)

        action = str(request.data.get("action") or request.data.get("decision") or "").upper().strip()
        aliases = {
            "APPROVE": "ACCEPT", "ACCEPTED": "ACCEPT", "ACCEPT": "ACCEPT",
            "REJECT": "DECLINE", "DECLINED": "DECLINE", "DECLINE": "DECLINE",
            "CHANGES": "REQUEST_CHANGES", "REQUEST_CHANGES": "REQUEST_CHANGES",
        }
        action = aliases.get(action)
        if not action:
            return Response(
                {"error": "action must be one of ACCEPT, DECLINE, REQUEST_CHANGES."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quote, follow_on = quotation_service.record_customer_decision(
                quote.id,
                action,
                notes=request.data.get("notes", "") or "",
                reason=request.data.get("reason", "") or "",
                token=token,
            )
        except ValidationError as exc:
            return Response({"error": "; ".join(exc.messages)},
                            status=status.HTTP_400_BAD_REQUEST)

        payload = {
            "success": True,
            "action": action,
            "quote": _serialize_quote(quote, full=True),
        }
        if action == "ACCEPT":
            if quotation_service.requires_admin_approval():
                payload["message"] = (
                    "Thank you. Your approval is recorded and the quotation is with "
                    "the SEVO team for final confirmation. You will be notified once "
                    "the work is scheduled."
                )
                payload["awaiting_admin_approval"] = True
            else:
                payload["message"] = "Quotation accepted. Your work booking has been created."
                payload["work_job_id"] = getattr(follow_on, "id", None)
        elif action == "DECLINE":
            payload["message"] = "Quotation declined."
        else:
            payload["message"] = "Change request recorded. A revised quotation will follow."
            payload["revised_quote_id"] = getattr(follow_on, "id", None)
        return Response(payload)


# --------------------------------------------------------------------------- #
# SEVO admin approval
# --------------------------------------------------------------------------- #
class QuotePendingApprovalView(APIView):
    permission_classes = [IsSevoAdmin]

    def get(self, request):
        quotes = quotation_service.quotes_awaiting_admin_approval()
        company_id = request.query_params.get("company_id")
        if company_id:
            quotes = quotes.filter(company_id=company_id)
        return Response([_serialize_quote(q) for q in quotes[:200]])


class QuoteAdminReviewView(APIView):
    permission_classes = [IsSevoAdmin]

    def post(self, request, pk):
        quote = WorkforceQuote.objects.filter(pk=pk).first()
        if quote is None:
            return Response({"error": "Quotation not found."}, status=status.HTTP_404_NOT_FOUND)

        raw = str(request.data.get("action") or request.data.get("decision") or "").upper().strip()
        if raw in ("APPROVE", "APPROVED", "ACCEPT"):
            approve = True
        elif raw in ("REJECT", "REJECTED", "DECLINE"):
            approve = False
        else:
            return Response({"error": "action must be APPROVE or REJECT."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            quote, work_job, invoice = quotation_service.admin_review_quote(
                quote.id,
                request.user,
                approve=approve,
                notes=request.data.get("notes", "") or "",
                reason=request.data.get("reason", "") or "",
            )
        except ValidationError as exc:
            return Response({"error": "; ".join(exc.messages)},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "approved": approve,
            "quote": _serialize_quote(quote, full=True),
            "work_job_id": getattr(work_job, "id", None),
            "invoice": _serialize_invoice(invoice, full=True) if invoice else None,
        })


# --------------------------------------------------------------------------- #
# invoices
# --------------------------------------------------------------------------- #
def _visible_invoices(request):
    """
    Same tenancy contract as quote_views._visible_quotes, plus the customer:
    the person being billed can always see their own invoice.
    """
    qs = WorkforceInvoice.objects.select_related("quote", "job", "company", "technician")
    user = request.user

    if getattr(user, "is_superuser", False):
        return qs

    conditions = Q(customer_id=user.id)

    emp = getattr(user, "employee_profile", None)
    if emp:
        role = (getattr(user, "role", "") or "").lower()
        if role in ("admin", "manager") and emp.company_id:
            conditions |= Q(company_id=emp.company_id)
        else:
            conditions |= Q(technician_id=emp.id)
    return qs.filter(conditions)


class InvoiceListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = _visible_invoices(request)
        st = request.query_params.get("status")
        if st:
            qs = qs.filter(status=st.upper())
        job_id = request.query_params.get("job_id")
        if job_id:
            qs = qs.filter(job_id=job_id)
        quote_id = request.query_params.get("quote_id")
        if quote_id:
            qs = qs.filter(quote_id=quote_id)
        search = (request.query_params.get("search") or "").strip()
        if search:
            qs = qs.filter(
                Q(invoice_number__icontains=search)
                | Q(bill_to_name__icontains=search)
                | Q(bill_to_phone__icontains=search)
            )
        # Bare array: the Estimates/Invoices screens call .filter() on the
        # response directly, so an envelope here becomes a TypeError there.
        return Response([_serialize_invoice(i) for i in qs[:200]])


class InvoiceDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        inv = _visible_invoices(request).filter(pk=pk).first()
        if inv is None:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(_serialize_invoice(inv, full=True))


class InvoicePaymentView(APIView):
    """
    Record a customer payment. This is the step that eventually puts money in
    the provider's wallet: it updates the job's JobPayment row, which is what
    services/commission.settle_completed_job reads when the job completes.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        inv = _visible_invoices(request).filter(pk=pk).first()
        if inv is None:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            amount = _dec(request.data.get("amount", inv.balance_due), "amount")
        except ValueError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            inv, payment, created = invoice_service.record_invoice_payment(
                inv,
                amount,
                method=request.data.get("method", "ONLINE"),
                reference=request.data.get("reference", "") or "",
                gateway=request.data.get("gateway", "") or "",
                actor=request.user,
                notes=request.data.get("notes", "") or "",
            )
        except ValidationError as exc:
            return Response({"error": "; ".join(exc.messages)},
                            status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "success": True,
                "duplicate": not created,
                "payment_id": payment.id,
                "wallet_ledger_entry_id": payment.ledger_entry_id,
                "invoice": _serialize_invoice(inv, full=True),
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class InvoiceCancelView(APIView):
    permission_classes = [IsSevoAdmin]

    def post(self, request, pk):
        inv = WorkforceInvoice.objects.filter(pk=pk).first()
        if inv is None:
            return Response({"error": "Invoice not found."}, status=status.HTTP_404_NOT_FOUND)
        try:
            inv = invoice_service.cancel_invoice(
                inv, actor=request.user, reason=request.data.get("reason", "") or ""
            )
        except ValidationError as exc:
            return Response({"error": "; ".join(exc.messages)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True, "invoice": _serialize_invoice(inv, full=True)})
