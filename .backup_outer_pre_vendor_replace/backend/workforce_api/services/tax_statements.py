"""
Earnings statements -- SEVO business plan Section 6 (Tax documentation):
"Auto-generated monthly and annual earnings statements for both providers
(business income) and individual workers (professional/other income)."
and Section 1: "Transaction history for salary reconciliation: every
ledger credit is tagged with the job ID, customer, amount, commission
deducted and (optionally) the worker who performed it -- exportable as a
CSV/PDF wage register."

Scope note on TDS: the business plan itself flags TDS withholding as
needing "sign-off from a chartered accountant before go-live rather than
a general assumption in this plan" -- this module deliberately does NOT
compute or withhold tax. It produces the gross/commission/net figures a
CA or the wallet owner's own accountant needs to do that work themselves;
inventing a withholding calculation here would be exactly the kind of
unverified assumption the plan warns against.
"""
import csv
import io
from decimal import Decimal

from django.db.models import Sum, Count
from django.utils import timezone


def _period_bounds(year, month=None):
    """Returns (start, end, label) for a calendar month (if month given) or
    a full calendar year (Apr-Mar Indian FY is NOT assumed here -- this is
    a calendar-year statement; a CA/finance team can re-slice by FY from
    the underlying ledger export if needed)."""
    if month:
        start = timezone.datetime(year, month, 1)
        end = timezone.datetime(year + 1, 1, 1) if month == 12 else timezone.datetime(year, month + 1, 1)
        label = start.strftime("%B %Y")
    else:
        start = timezone.datetime(year, 1, 1)
        end = timezone.datetime(year + 1, 1, 1)
        label = str(year)
    start = timezone.make_aware(start)
    end = timezone.make_aware(end)
    return start, end, label


def generate_earnings_statement(wallet, year, month=None):
    """
    Aggregates one wallet's ledger for a calendar month or year into a
    statement dict: gross job value, commission deducted, net credited,
    clawbacks/refund adjustments, promo credits, and jobs count. This is
    the "business income" statement for a PROVIDER_HEAD wallet and the
    "professional/other income" statement for an INDIVIDUAL_WORKER wallet
    -- the plan's distinction is about how the recipient reports it to
    the tax authority, not a different computation here.
    """
    from workforce_api.models import WalletLedgerEntry

    start, end, label = _period_bounds(year, month)
    qs = WalletLedgerEntry.objects.filter(wallet=wallet, created_at__gte=start, created_at__lt=end)

    gross = qs.filter(entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT).aggregate(
        total=Sum("gross_job_amount"), count=Count("id"),
    )
    net_credited = qs.filter(entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT).aggregate(
        total=Sum("signed_amount")
    )["total"] or Decimal("0")
    commission = -(
        qs.filter(entry_type__in=[
            WalletLedgerEntry.EntryType.COMMISSION_DEBIT,
            WalletLedgerEntry.EntryType.COD_COMMISSION_PAYABLE,
        ]).aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")
    )
    clawbacks = -(
        qs.filter(entry_type=WalletLedgerEntry.EntryType.CLAWBACK_DEBIT)
        .aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")
    )
    refund_adjustments = -(
        qs.filter(entry_type=WalletLedgerEntry.EntryType.REFUND_ADJUSTMENT)
        .aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")
    )
    promo_credits = qs.filter(entry_type=WalletLedgerEntry.EntryType.PROMO_CREDIT).aggregate(
        total=Sum("signed_amount")
    )["total"] or Decimal("0")

    owner_name = wallet.company.company_name if wallet.company_id else (
        wallet.employee.user.get_full_name() if wallet.employee_id and wallet.employee.user_id else ""
    )
    income_category = "Business income" if wallet.company_id else "Professional/other income"

    return {
        "wallet_id": wallet.id,
        "owner_name": owner_name,
        "income_category": income_category,
        "period_label": label,
        "period_start": start.date().isoformat(),
        "period_end": (end - timezone.timedelta(days=1)).date().isoformat(),
        "jobs_count": gross["count"] or 0,
        "gross_job_value": gross["total"] or Decimal("0"),
        "commission_deducted": commission,
        "clawbacks": clawbacks,
        "refund_adjustments": refund_adjustments,
        "promo_credits": promo_credits,
        "net_credited": net_credited,
    }


def export_ledger_csv(wallet, start_date=None, end_date=None):
    """
    Builds the "wage register" CSV the business plan describes: every
    ledger row for this wallet, tagged with job ID, amount, commission,
    and (when known) the worker who performed it -- so a provider can
    reconcile it against their own payroll, and either wallet owner can
    hand it to their accountant. Returns CSV text (str), not a file --
    callers wrap it in an HttpResponse with the right content-type.
    """
    from workforce_api.models import WalletLedgerEntry

    qs = WalletLedgerEntry.objects.filter(wallet=wallet).select_related(
        "job", "worker_performed", "worker_performed__user",
    ).order_by("created_at")
    if start_date:
        qs = qs.filter(created_at__gte=start_date)
    if end_date:
        qs = qs.filter(created_at__lt=end_date)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "date", "entry_type", "job_id", "worker_performed", "gross_job_amount",
        "commission_rate_applied", "amount", "status", "notes",
    ])
    for entry in qs.iterator():
        worker_name = ""
        if entry.worker_performed_id and entry.worker_performed.user_id:
            worker_name = entry.worker_performed.user.get_full_name()
        writer.writerow([
            timezone.localtime(entry.created_at).strftime("%Y-%m-%d %H:%M"),
            entry.entry_type,
            entry.job_id or "",
            worker_name,
            entry.gross_job_amount if entry.gross_job_amount is not None else "",
            entry.commission_rate_applied if entry.commission_rate_applied is not None else "",
            entry.signed_amount,
            entry.status,
            entry.notes,
        ])
    return buf.getvalue()
