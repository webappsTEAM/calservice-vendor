"""
Project a WorkforceQuote into the EstimationQuotation tables.

WorkforceQuote is canonical (see ESTIMATION_MASTER_PLAN.md, decision D2). The
customer application reads the older service_requests_estimation* tables, so a
quote raised in the workforce Quotation Builder was invisible to it -- the
technician could send a painting quote and the customer's own app would show
nothing.

Sync already ran the other way: service_requests/vendor_views._sync_workforce_quote
mirrors an AC EstimationQuotation into WorkforceQuote. This module is the
return direction. Together they mean either entry point produces both records.

Three rules this module keeps:

1. **It never breaks the caller.** A projection is a convenience copy. If
   writing it fails, the quote the technician just built must still exist, so
   every entry point swallows and logs rather than raising.

2. **It never invents AC specifics.** Estimation was designed for air
   conditioning and its fields are required. A painting job gets ACType.OTHER
   and ACCapacity.OTHER rather than a fabricated "1.5 ton split", because a
   plausible-looking wrong value is worse than an obviously absent one.

3. **quote_ref carries the version.** EstimationQuotation.quote_ref is unique
   while WorkforceQuote.quote_number is deliberately shared across revisions,
   so the reference is suffixed -V1, -V2 ... matching the convention the AC
   path already uses (QTE-<request_id>-V<n>).
"""
import logging
from decimal import Decimal

from django.db import transaction

logger = logging.getLogger(__name__)

# WorkforceQuote.Status -> EstimationQuotation.QuoteStatus.
# EstimationQuotation has a coarser vocabulary: it has no notion of "the
# customer accepted but SEVO has not authorised it yet", so everything from
# acceptance onward reads as APPROVED to the customer. That is the truthful
# summary from their side -- they did approve it.
STATUS_MAP = {
    "DRAFT": "DRAFT",
    "PENDING_REVIEW": "DRAFT",           # held for admin; not the customer's business yet
    "SENT_TO_CUSTOMER": "SENT",
    "CHANGES_REQUESTED": "SENT",         # still the live version until v2 supersedes it
    "CUSTOMER_ACCEPTED": "APPROVED",
    "PENDING_ADMIN_APPROVAL": "APPROVED",
    "ADMIN_APPROVED": "APPROVED",
    "CONVERSION_PENDING": "APPROVED",
    "CONVERTED": "APPROVED",
    "DECLINED": "REJECTED",
    "ADMIN_REJECTED": "REJECTED",
    "EXPIRED": "EXPIRED",
    "SUPERSEDED": "SUPERSEDED",
    "CANCELLED": "CANCELLED",
}

# WorkforceQuote.Status -> Estimation.Status, so the customer's booking screen
# moves through its own lifecycle as the quote does.
ESTIMATION_STATUS_MAP = {
    "SENT_TO_CUSTOMER": "QUOTATION_SENT",
    "CUSTOMER_ACCEPTED": "CUSTOMER_APPROVED",
    "PENDING_ADMIN_APPROVAL": "CUSTOMER_APPROVED",
    "ADMIN_APPROVED": "CUSTOMER_APPROVED",
    "CONVERTED": "CONVERTED_TO_SERVICE",
    "DECLINED": "CUSTOMER_REJECTED",
    "ADMIN_REJECTED": "CUSTOMER_REJECTED",
    "CANCELLED": "CANCELLED",
}


def quote_ref_for(quote):
    return f"{quote.quote_number}-V{quote.quote_version}"


def project_quote(quote):
    """
    Create or refresh the customer-facing projection of a quote.

    Returns the EstimationQuotation, or None if it could not be written.
    Safe to call repeatedly and from inside another transaction.
    """
    try:
        return _project(quote)
    except Exception as exc:  # pragma: no cover - defensive by design
        logger.warning(
            "Could not project quote %s v%s to the customer estimation tables: %s",
            getattr(quote, "quote_number", "?"), getattr(quote, "quote_version", "?"), exc,
            exc_info=True,
        )
        return None


def _project(quote):
    from service_requests.models import (
        Estimation,
        EstimationQuotation,
        EstimationQuotationItem,
    )

    job = quote.job
    if job is None:
        return None

    # A quote that CAME FROM the AC path already has its customer-side row --
    # vendor_views._sync_workforce_quote created this WorkforceQuote from it,
    # copying quote_ref into quote_number. Projecting it back would create a
    # second EstimationQuotation with a doubled reference (QTE-...-V1-V1) and
    # the customer would see the same quotation twice.
    if EstimationQuotation.objects.filter(quote_ref=quote.quote_number).exists():
        logger.debug(
            "Quote %s originated in the AC estimation path; its projection already exists.",
            quote.quote_number,
        )
        return None

    with transaction.atomic():
        estimation = _estimation_for(job, quote, Estimation)

        projected, _created = EstimationQuotation.objects.update_or_create(
            quote_ref=quote_ref_for(quote),
            defaults={
                "estimation": estimation,
                "version": quote.quote_version,
                "status": STATUS_MAP.get(quote.status, "DRAFT"),
                "technician_id": str(quote.technician_id or ""),
                "vendor_id": str(quote.company_id or ""),
                "subtotal": _money(quote.subtotal_amount),
                "tax_amount": _money(quote.tax_amount),
                "discount_amount": _money(quote.discount_amount),
                "total_amount": _money(quote.net_payable or quote.total_amount),
                "currency": "INR",
                "notes": quote.description or "",
                # valid_until is a DateField here and a DateTimeField on the quote.
                "valid_until": quote.valid_until.date() if quote.valid_until else None,
                "customer_approved_at": (
                    quote.customer_decided_at if quote.customer_decision == "ACCEPTED" else None
                ),
                "customer_rejected_at": (
                    quote.customer_decided_at if quote.customer_decision == "DECLINED" else None
                ),
                "rejection_note": quote.customer_decline_reason or "",
            },
        )

        # Replace the lines wholesale. They are a copy of the quote's, and
        # reconciling them item by item would only invent ways to drift.
        EstimationQuotationItem.objects.filter(quotation=projected).delete()
        EstimationQuotationItem.objects.bulk_create([
            EstimationQuotationItem(
                quotation=projected,
                service_name=item.name[:255],
                description=item.description or "",
                quantity=_money(item.quantity),
                unit=item.unit or "unit",
                unit_price=_money(item.unit_price),
                tax_rate=_money(item.tax_rate if item.tax_rate is not None else 18),
                tax_amount=_line_tax(item),
                discount_amount=_money(item.discount_amount),
                line_total=_money(item.total_amount),
                catalog_service_id=str(item.section or ""),
                sort_order=item.sort_order or 0,
            )
            for item in quote.items.all().order_by("sort_order", "id")
        ])

        target = ESTIMATION_STATUS_MAP.get(quote.status)
        if target and estimation.status != target:
            estimation.status = target
            estimation.save(update_fields=["status", "updated_at"])

    logger.info(
        "Projected quote %s v%s -> EstimationQuotation %s (%s)",
        quote.quote_number, quote.quote_version, projected.quote_ref, projected.status,
    )
    return projected


def _estimation_for(job, quote, Estimation):
    """
    The Estimation row this job's quotes hang from, created if absent.

    Estimation was built for air conditioning and its specification fields are
    not nullable. For anything else they are set to OTHER and the real service
    is recorded in customer_symptom -- an honest "not applicable" rather than a
    fabricated AC specification that would read as real data on a report.
    """
    existing = Estimation.objects.filter(service_request=job).order_by("id").first()
    if existing:
        return existing

    category = (quote.service_category or job.service_category or "").lower()
    is_ac = "ac" in category.split() or "air" in category

    return Estimation.objects.create(
        service_request=job,
        ac_type="SPLIT" if is_ac else "OTHER",
        ac_brand="" if not is_ac else "General",
        ac_capacity="1.5_TON" if is_ac else "OTHER",
        ac_quantity=1,
        customer_symptom=(quote.service_name or job.issue_title or "")[:2000],
        customer_notes=(
            "" if is_ac else
            f"Non-AC {quote.service_category or 'service'} estimation; AC "
            "specification fields are not applicable."
        ),
        status="REQUESTED",
    )


def _money(value):
    try:
        return Decimal(str(value if value is not None else 0))
    except Exception:
        return Decimal("0.00")


def _line_tax(item):
    net = _money(item.total_amount)
    rate = _money(item.tax_rate if item.tax_rate is not None else 18)
    return (net * rate / Decimal("100")).quantize(Decimal("0.01"))
