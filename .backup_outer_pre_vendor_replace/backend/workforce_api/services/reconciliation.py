"""
Daily financial reconciliation -- SEVO business plan Section 5 (Reconciliation
cadence): "A daily automated reconciliation job -- extending the
payment-reconciliation audit tooling already built into the platform --
checks gross bookings against recognised commission, net payouts, and the
actual escrow-bank balance, flagging same-day if anything drifts."

Two existing tools already cover adjacent ground and are deliberately left
untouched rather than duplicated:
  - management/commands/audit_jobpayment_reconciliation.py checks
    JobPayment.payment_status against ServiceRequest.payment_status (a
    status-field consistency check, not a financial-amount one).
  - services/cash_reconciliation.py reconciles a technician's physically
    collected cash against what they deposit.

This module is the new piece: it checks financial AMOUNTS across the
wallet ledger (services/commission.py:settle_completed_job is the only
writer of JOB_CREDIT/COMMISSION_DEBIT entries) for a given day.

Honest scoping note on "actual escrow-bank balance": this codebase has no
live feed from SEVO's actual nodal/escrow bank account (RazorpayX Payouts
tracks payout request/webhook status, not an account balance API -- see
services/payouts.py). So this job cannot *compare against* the real bank
balance automatically. What it CAN do, and does, is compute the balance
that SHOULD be sitting in escrow given the ledger -- `expected_escrow_balance`
-- for a human (finance/ops) to tie out against the actual bank statement.
Treat that figure as informational, not a pass/fail check, until a real
bank-statement feed is wired up.
"""
import logging
from decimal import Decimal

from django.db.models import Sum, Q
from django.utils import timezone

logger = logging.getLogger(__name__)

AMOUNT_TOLERANCE = Decimal("0.05")  # per-comparison rounding slack


def _daterange_for(target_date):
    """Returns (start, end) datetimes spanning target_date in the current
    timezone, for filtering created_at/completed_date fields."""
    start = timezone.make_aware(timezone.datetime.combine(target_date, timezone.datetime.min.time()))
    end = start + timezone.timedelta(days=1)
    return start, end


def run_daily_reconciliation(target_date=None, company=None):
    """
    Runs the day's reconciliation and returns a findings dict. Does not
    mutate any data -- purely a read-only audit, same posture as
    audit_jobpayment_reconciliation.py.

    target_date: a date object; defaults to yesterday (the job is meant to
    run overnight over the previous day's completed activity).
    company: optional Company to scope to (a provider's own books);
    omitted for a platform-wide run covering all companies and individual
    workers.
    """
    from workforce_api.models import WalletLedgerEntry, WithdrawalRequest, JobPayment
    from service_requests.models import ServiceRequest

    if target_date is None:
        target_date = (timezone.localtime(timezone.now()) - timezone.timedelta(days=1)).date()
    start, end = _daterange_for(target_date)

    findings = []

    # 1. Settlement completeness: every job completed that day should have
    # produced exactly one JOB_CREDIT entry (services.commission.settle_completed_job
    # logs SETTLEMENT_NO_WALLET / SETTLEMENT_NO_PAYMENT / SETTLEMENT_ZERO_AMOUNT
    # when it can't settle -- those jobs surface here instead of only in logs).
    completed_jobs_qs = ServiceRequest.objects.filter(
        status="completed", updated_at__gte=start, updated_at__lt=end,
    )
    if company is not None:
        completed_jobs_qs = completed_jobs_qs.filter(company_id=company.id)

    settled_job_ids = set(
        WalletLedgerEntry.objects.filter(
            entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT,
            job_id__in=completed_jobs_qs.values_list("id", flat=True),
        ).values_list("job_id", flat=True)
    )
    for job in completed_jobs_qs.select_related(None):
        payment = JobPayment.objects.filter(job=job).first()
        gross = (payment.amount_due or payment.amount_paid) if payment else None
        if job.id not in settled_job_ids and gross and gross > 0:
            findings.append({
                "type": "MISSING_SETTLEMENT",
                "job_id": job.id,
                "detail": f"Job #{job.id} completed with a payable amount of {gross} but has no JOB_CREDIT ledger entry.",
            })

    # 2. Gross bookings vs recognised commission + net worker/provider credit.
    # By construction (settle_completed_job creates both entries together)
    # these should always tie out exactly for jobs settled today -- a
    # mismatch here means a bug in settlement math, not routine drift.
    ledger_qs = WalletLedgerEntry.objects.filter(created_at__gte=start, created_at__lt=end)
    if company is not None:
        ledger_qs = ledger_qs.filter(wallet__company_id=company.id)

    gross_bookings = ledger_qs.filter(
        entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT
    ).aggregate(total=Sum("gross_job_amount"))["total"] or Decimal("0")

    recognised_net = ledger_qs.filter(
        entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT
    ).aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")

    recognised_commission = -(
        ledger_qs.filter(
            entry_type__in=[
                WalletLedgerEntry.EntryType.COMMISSION_DEBIT,
                WalletLedgerEntry.EntryType.COD_COMMISSION_PAYABLE,
            ]
        ).aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")
    )

    gross_minus_expected = gross_bookings - (recognised_net + recognised_commission)
    if abs(gross_minus_expected) > AMOUNT_TOLERANCE:
        findings.append({
            "type": "GROSS_MISMATCH",
            "detail": (
                f"Gross bookings ({gross_bookings}) do not equal recognised net "
                f"({recognised_net}) + recognised commission ({recognised_commission}); "
                f"difference {gross_minus_expected}."
            ),
        })

    # 3. Net payouts that actually left the platform today.
    payouts_qs = WithdrawalRequest.objects.filter(
        status=WithdrawalRequest.Status.SUCCESS, processed_at__gte=start, processed_at__lt=end,
    )
    if company is not None:
        payouts_qs = payouts_qs.filter(wallet__company_id=company.id)
    net_payouts = payouts_qs.aggregate(total=Sum("amount"))["total"] or Decimal("0")

    # 4. Expected escrow balance (informational -- see module docstring).
    # Everything still sitting in the platform's nodal account on behalf of
    # wallet owners: money credited for jobs (HELD or RELEASED, i.e. not
    # CLAWED_BACK) minus money that has actually been paid out.
    escrow_qs = WalletLedgerEntry.objects.exclude(status=WalletLedgerEntry.Status.CLAWED_BACK).filter(
        entry_type__in=[WalletLedgerEntry.EntryType.JOB_CREDIT, WalletLedgerEntry.EntryType.WITHDRAWAL_DEBIT],
    )
    if company is not None:
        escrow_qs = escrow_qs.filter(wallet__company_id=company.id)
    expected_escrow_balance = escrow_qs.aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")

    if findings:
        logger.warning(
            "[RECONCILIATION_DRIFT] %s finding(s) for %s (company=%s): %s",
            len(findings), target_date, company.id if company else "ALL",
            "; ".join(f["type"] for f in findings),
        )
    else:
        logger.info("[RECONCILIATION_CLEAN] %s (company=%s): no findings.", target_date, company.id if company else "ALL")

    return {
        "date": target_date.isoformat(),
        "company_id": company.id if company else None,
        "gross_bookings": gross_bookings,
        "recognised_commission": recognised_commission,
        "recognised_net": recognised_net,
        "net_payouts": net_payouts,
        "expected_escrow_balance": expected_escrow_balance,
        "findings": findings,
        "is_clean": len(findings) == 0,
    }


def run_daily_reconciliation_all_companies(target_date=None):
    """Runs the platform-wide check plus one scoped check per Company (so a
    single provider's books can drift without the platform-wide totals
    hiding it), for the daily cron. Returns {platform: {...}, companies: [...]}."""
    from companies.models import Company

    platform_result = run_daily_reconciliation(target_date=target_date, company=None)
    company_results = [
        run_daily_reconciliation(target_date=target_date, company=c)
        for c in Company.objects.all()
    ]
    return {"platform": platform_result, "companies": company_results}
