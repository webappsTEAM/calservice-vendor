"""
Invoicing for the estimation workflow.

Where this sits in the chain:

    customer books a quotation service
      -> technician inspects on site (4 pre-service gates)
      -> technician builds a quote            (services/quotation_service.py)
      -> quote sent to customer
      -> CUSTOMER approves
      -> SEVO ADMIN approves                  (quotation_service.admin_review_quote)
      -> work booking created + INVOICE issued        (this module)
      -> customer pays the invoice                    (this module)
      -> job completed -> provider wallet credited    (services/commission.py)

Two rules this module exists to enforce:

1. An issued invoice is frozen. Totals and line items are COPIED from the
   quote, never read back through it, so revising a quote afterwards cannot
   change the value of a document the customer has already been given.

2. Recording a payment is idempotent on `reference`. Gateway callbacks are
   at-least-once; replaying one must not credit the customer twice, and the
   database unique constraint on (invoice, reference) is the backstop if the
   application check ever races.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from workforce_api.models import (
    JobPayment,
    WorkforceInvoice,
    WorkforceInvoiceItem,
    WorkforceInvoicePayment,
    WorkforceQuote,
)

logger = logging.getLogger(__name__)

ZERO = Decimal("0.00")
CENT = Decimal("0.01")


def _money(value):
    try:
        return Decimal(str(value if value is not None else 0)).quantize(CENT)
    except (InvalidOperation, TypeError, ValueError):
        return ZERO


def _payment_method_for_job(job):
    """Map the booking's payment method onto JobPayment's narrower vocabulary."""
    raw = str(getattr(job, "payment_method", "") or "").upper()
    if raw in ("COD", "CASH", "CASH_ON_SERVICE", "CASH_ON_DELIVERY"):
        return JobPayment.PaymentMethod.CASH_ON_SERVICE
    return JobPayment.PaymentMethod.ONLINE


# ---------------------------------------------------------------------------
# Issuing
# ---------------------------------------------------------------------------

@transaction.atomic
def generate_invoice_for_quote(quote, work_job=None, actor=None, due_days=7):
    """
    Issue the invoice for an approved quote.

    Idempotent: if a live (non-cancelled) invoice already exists for this
    quote it is returned unchanged. Admin approval can be retried, and a
    retry must not produce a second invoice for the same work.
    """
    if isinstance(quote, int):
        quote = WorkforceQuote.objects.get(id=quote)

    existing = (
        WorkforceInvoice.objects.filter(quote=quote)
        .exclude(status=WorkforceInvoice.Status.CANCELLED)
        .first()
    )
    if existing:
        return existing

    job = work_job or quote.work_job or quote.job
    if job is None:
        raise ValidationError("Cannot issue an invoice: the quote has no job attached.")

    source = quote.job or job
    now = timezone.now()

    invoice = WorkforceInvoice(
        quote=quote,
        job=job,
        customer=quote.customer or getattr(source, "customer", None),
        company=quote.company or getattr(source, "company", None),
        technician=quote.technician or getattr(source, "assigned_employee", None),
        bill_to_name=getattr(source, "customer_name", "") or "",
        bill_to_phone=getattr(source, "phone", "") or "",
        bill_to_email=getattr(source, "email", "") or "",
        bill_to_address=getattr(source, "address", "") or "",
        service_category=quote.service_category or getattr(source, "service_category", "") or "",
        service_name=quote.service_name or quote.title or "",
        subtotal_amount=_money(quote.subtotal_amount),
        discount_amount=_money(quote.discount_amount),
        tax_amount=_money(quote.tax_amount),
        inspection_fee_adjusted=_money(quote.inspection_fee_adjusted),
        total_amount=_money(quote.net_payable or quote.total_amount),
        amount_paid=ZERO,
        status=WorkforceInvoice.Status.ISSUED,
        issued_at=now,
        due_at=now + timezone.timedelta(days=due_days),
        notes=f"Issued against quotation {quote.quote_number} (v{quote.quote_version}).",
        metadata={
            "quote_number": quote.quote_number,
            "quote_version": quote.quote_version,
            "issued_by": getattr(actor, "id", None),
            "inspection_job_id": getattr(quote.job, "id", None),
        },
    )
    invoice.balance_due = invoice.total_amount
    invoice.save()

    for item in quote.items.all():
        WorkforceInvoiceItem.objects.create(
            invoice=invoice,
            section=item.section,
            name=item.name,
            description=item.description,
            item_type=item.item_type,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate if item.tax_rate is not None else Decimal("18.00"),
            discount_amount=item.discount_amount,
            line_total=item.total_amount,
            sort_order=item.sort_order,
        )

    # The settlement engine (services/commission.settle_completed_job) refuses
    # to credit a wallet for a job with no JobPayment row, and quote-converted
    # work bookings were never given one -- which is why converted jobs could
    # complete without the provider ever being paid. Create it here, at the
    # moment the amount becomes billable.
    _ensure_job_payment(invoice)

    logger.info(
        "[INVOICE_ISSUED] %s for quote %s v%s job #%s amount=%s",
        invoice.invoice_number, quote.quote_number, quote.quote_version,
        job.id, invoice.total_amount,
    )
    return invoice


def _ensure_job_payment(invoice):
    job = invoice.job
    payment, created = JobPayment.objects.get_or_create(
        job=job,
        defaults={
            "employee": invoice.technician,
            "company": invoice.company,
            "payment_method": _payment_method_for_job(job),
            "payment_status": JobPayment.PaymentStatus.PENDING,
            "amount_due": invoice.total_amount,
            "amount_paid": ZERO,
        },
    )
    if not created:
        fields = []
        if _money(payment.amount_due) != invoice.total_amount:
            payment.amount_due = invoice.total_amount
            fields.append("amount_due")
        if payment.employee_id is None and invoice.technician_id:
            payment.employee = invoice.technician
            fields.append("employee")
        if payment.company_id is None and invoice.company_id:
            payment.company = invoice.company
            fields.append("company")
        if fields:
            fields.append("updated_at")
            payment.save(update_fields=fields)
    return payment


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

@transaction.atomic
def record_invoice_payment(
    invoice, amount, method="ONLINE", reference="", gateway="",
    actor=None, paid_at=None, notes="",
):
    """
    Record a customer payment against an invoice.

    Returns (invoice, payment, created). `created` is False when this is a
    replay of a reference already recorded -- the caller should treat that as
    success, not as a duplicate charge.
    """
    if isinstance(invoice, int):
        invoice = WorkforceInvoice.objects.get(id=invoice)
    invoice = WorkforceInvoice.objects.select_for_update().get(id=invoice.id)

    if invoice.status == WorkforceInvoice.Status.CANCELLED:
        raise ValidationError(f"Invoice {invoice.invoice_number} is cancelled and cannot take payment.")

    reference = (reference or "").strip()
    if reference:
        replay = invoice.payments.filter(reference=reference).first()
        if replay:
            logger.info(
                "[INVOICE_PAYMENT_REPLAY] %s reference=%s ignored",
                invoice.invoice_number, reference,
            )
            return invoice, replay, False

    amount = _money(amount)
    if amount <= ZERO:
        raise ValidationError("Payment amount must be greater than zero.")
    if amount > _money(invoice.balance_due) + CENT:
        raise ValidationError(
            f"Payment of {amount} exceeds the outstanding balance "
            f"{invoice.balance_due} on invoice {invoice.invoice_number}."
        )

    now = paid_at or timezone.now()
    payment = WorkforceInvoicePayment.objects.create(
        invoice=invoice,
        amount=amount,
        method=str(method or "ONLINE").upper(),
        status=WorkforceInvoicePayment.Status.SUCCESS,
        reference=reference,
        gateway=gateway or "",
        paid_at=now,
        recorded_by=actor if getattr(actor, "is_authenticated", False) else None,
        notes=notes or "",
    )

    invoice.amount_paid = _money(invoice.amount_paid) + amount
    invoice.balance_due = max(ZERO, _money(invoice.total_amount) - invoice.amount_paid)
    if invoice.balance_due <= ZERO:
        invoice.status = WorkforceInvoice.Status.PAID
        invoice.paid_at = now
    else:
        invoice.status = WorkforceInvoice.Status.PARTIALLY_PAID
    invoice.save(update_fields=["amount_paid", "balance_due", "status", "paid_at", "updated_at"])

    _sync_job_payment(invoice, payment)

    entry = _settle_if_job_complete(invoice)
    if entry is not None:
        payment.ledger_entry = entry
        payment.save(update_fields=["ledger_entry"])

    logger.info(
        "[INVOICE_PAYMENT] %s +%s via %s (ref=%s) -> paid=%s balance=%s status=%s",
        invoice.invoice_number, amount, payment.method, reference or "-",
        invoice.amount_paid, invoice.balance_due, invoice.status,
    )
    return invoice, payment, True


def _sync_job_payment(invoice, payment):
    """Mirror the invoice's collection state onto JobPayment, which is what
    the settlement engine and the cash-reconciliation reports read."""
    job_payment = _ensure_job_payment(invoice)
    job_payment.amount_paid = _money(invoice.amount_paid)

    if invoice.status == WorkforceInvoice.Status.PAID:
        job_payment.payment_status = JobPayment.PaymentStatus.PAID
    elif payment.method == WorkforceInvoicePayment.Method.CASH:
        job_payment.payment_status = JobPayment.PaymentStatus.CASH_PENDING
    else:
        job_payment.payment_status = JobPayment.PaymentStatus.AUTHORIZED

    if payment.method == WorkforceInvoicePayment.Method.CASH:
        job_payment.payment_method = JobPayment.PaymentMethod.CASH_ON_SERVICE
        job_payment.cash_collected_at = payment.paid_at
        if invoice.technician_id:
            job_payment.cash_collected_by = invoice.technician
    else:
        job_payment.payment_method = JobPayment.PaymentMethod.ONLINE
        if payment.reference:
            job_payment.gateway_transaction_id = payment.reference

    job_payment.save()
    return job_payment


def _settle_if_job_complete(invoice):
    """
    Normally the wallet is credited when the job completes -- the state
    machine calls settle_completed_job() on the transition. But payment can
    arrive AFTER completion (a customer paying an outstanding invoice), and
    settlement would have failed at completion time with no payment on file.
    So retry it here. settle_completed_job is idempotent, so calling it a
    second time for an already-settled job returns the existing entry.
    """
    from workforce_api.services.commission import settle_completed_job, SettlementError

    job = invoice.job
    if str(getattr(job, "status", "")).lower() != "completed":
        return None
    try:
        return settle_completed_job(job)
    except SettlementError as exc:
        logger.warning(
            "[INVOICE_PAYMENT_SETTLEMENT_DEFERRED] %s: %s", invoice.invoice_number, exc
        )
        return None


@transaction.atomic
def cancel_invoice(invoice, actor=None, reason=""):
    if isinstance(invoice, int):
        invoice = WorkforceInvoice.objects.get(id=invoice)
    invoice = WorkforceInvoice.objects.select_for_update().get(id=invoice.id)

    if invoice.status == WorkforceInvoice.Status.CANCELLED:
        return invoice
    if _money(invoice.amount_paid) > ZERO:
        raise ValidationError(
            f"Invoice {invoice.invoice_number} has {invoice.amount_paid} paid against it "
            "and cannot be cancelled. Raise a refund instead."
        )

    invoice.status = WorkforceInvoice.Status.CANCELLED
    invoice.cancelled_at = timezone.now()
    invoice.cancellation_reason = reason or ""
    invoice.save(update_fields=["status", "cancelled_at", "cancellation_reason", "updated_at"])
    logger.info("[INVOICE_CANCELLED] %s by %s: %s", invoice.invoice_number, actor, reason)
    return invoice
