"""
Commission engine -- SEVO business plan Section 3 (Payment & Commission
Structure) and half of Section 4 (dispute hold-and-clawback).

settle_completed_job() is called once, from service_requests/state_machine.py
apply_transition(), the instant a job's status flips to "completed" -- the
single authoritative place a job becomes billable, so commission can never
be computed twice or skipped depending on which view triggered completion.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

DISPUTE_HOLD_HOURS = int(getattr(settings, "SEVO_DISPUTE_HOLD_HOURS", 48))
PROMO_PERIOD_DAYS = int(getattr(settings, "SEVO_PROMO_PERIOD_DAYS", 90))

PROVIDER_STANDARD_RATE = Decimal(str(getattr(settings, "SEVO_PROVIDER_COMMISSION_RATE", "0.10")))
PROVIDER_PROMO_RATE = Decimal(str(getattr(settings, "SEVO_PROVIDER_PROMO_RATE", "0.00")))
INDIVIDUAL_STANDARD_RATE = Decimal(str(getattr(settings, "SEVO_INDIVIDUAL_COMMISSION_RATE", "0.18")))
INDIVIDUAL_PROMO_RATE = Decimal(str(getattr(settings, "SEVO_INDIVIDUAL_PROMO_RATE", "0.08")))


def resolve_payee_wallet(service_request):
    """
    Which wallet gets credited for this job. An individually-onboarded
    worker's own wallet takes priority if they have one; otherwise the
    job's assigned employee is on a provider's team and the provider's
    head wallet is credited instead. Returns (None, None) if the job has
    no assigned employee or neither wallet exists yet (e.g. onboarding
    incomplete) -- callers must handle that as "cannot settle yet", not
    silently drop the money.
    """
    from workforce_api.models import WalletAccount

    emp = service_request.assigned_employee
    if not emp:
        return None, None

    try:
        return emp.individual_wallet, "INDIVIDUAL_WORKER"
    except WalletAccount.DoesNotExist:
        pass

    if emp.company_id:
        try:
            return emp.company.head_wallet, "PROVIDER_HEAD"
        except WalletAccount.DoesNotExist:
            pass

    return None, None


def is_in_promo_period(wallet) -> bool:
    if not wallet or not wallet.created_at:
        return False
    return (timezone.now() - wallet.created_at).days < PROMO_PERIOD_DAYS


def commission_rate_for(wallet, channel: str) -> Decimal:
    promo = is_in_promo_period(wallet)
    if channel == "PROVIDER_HEAD":
        return PROVIDER_PROMO_RATE if promo else PROVIDER_STANDARD_RATE
    return INDIVIDUAL_PROMO_RATE if promo else INDIVIDUAL_STANDARD_RATE


@transaction.atomic
def settle_completed_job(service_request):
    """
    Idempotent: safe to call more than once for the same job (e.g. a retry
    after a transient error) -- if a JOB_CREDIT ledger entry already exists
    for this job, does nothing and returns it unchanged.

    Computes gross from the job's JobPayment record, resolves which wallet
    is the payee (Section 1), applies the differentiated commission rate
    (Section 3), and creates:
      - one JOB_CREDIT entry (net amount, HELD until the dispute window
        closes -- Section 4)
      - one COMMISSION_DEBIT entry recorded for auditability (Section 6:
        per-job attribution) -- or, for a still-uncollected cash job, a
        COD_COMMISSION_PAYABLE entry instead, netted against a future
        digital payout rather than deducted from cash SEVO never touched.

    Returns the JOB_CREDIT WalletLedgerEntry, or None if settlement isn't
    possible yet (no assigned employee, no wallet on file, or no payment
    record) -- these are logged loudly rather than silently swallowed,
    since a job that can't be settled is a job whose worker doesn't get
    paid.
    """
    from workforce_api.models import WalletLedgerEntry, JobPayment

    existing = WalletLedgerEntry.objects.filter(
        job=service_request, entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT
    ).first()
    if existing:
        return existing

    wallet, channel = resolve_payee_wallet(service_request)
    if not wallet:
        logger.error(
            f"[SETTLEMENT_NO_WALLET] Job #{service_request.id} completed but has no "
            f"resolvable payee wallet (assigned_employee={service_request.assigned_employee_id}). "
            "This job's earnings cannot be credited until the technician/provider has "
            "completed wallet onboarding."
        )
        return None

    payment = JobPayment.objects.filter(job=service_request).first()
    if not payment:
        logger.error(f"[SETTLEMENT_NO_PAYMENT] Job #{service_request.id} completed but has no JobPayment record.")
        return None

    gross = payment.amount_due or payment.amount_paid or Decimal("0")
    if gross <= 0:
        logger.warning(f"[SETTLEMENT_ZERO_AMOUNT] Job #{service_request.id} has gross amount {gross} -- skipping settlement.")
        return None

    rate = commission_rate_for(wallet, channel)
    commission = (gross * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net = gross - commission

    hold_release_at = timezone.now() + timezone.timedelta(hours=DISPUTE_HOLD_HOURS)
    worker_performed = service_request.assigned_employee
    promo = is_in_promo_period(wallet)

    credit_entry = WalletLedgerEntry.objects.create(
        wallet=wallet,
        job=service_request,
        worker_performed=worker_performed,
        entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT,
        signed_amount=net,
        gross_job_amount=gross,
        commission_rate_applied=rate,
        status=WalletLedgerEntry.Status.HELD,
        hold_release_at=hold_release_at,
        notes=f"Job #{service_request.id} ({channel}, {'promo' if promo else 'standard'} rate {rate})",
    )

    is_cash_job = payment.payment_method == JobPayment.PaymentMethod.CASH_ON_SERVICE
    commission_entry_type = (
        WalletLedgerEntry.EntryType.COD_COMMISSION_PAYABLE if is_cash_job
        else WalletLedgerEntry.EntryType.COMMISSION_DEBIT
    )
    WalletLedgerEntry.objects.create(
        wallet=wallet,
        job=service_request,
        worker_performed=worker_performed,
        entry_type=commission_entry_type,
        signed_amount=-commission,
        gross_job_amount=gross,
        commission_rate_applied=rate,
        # A cash job's commission isn't collectable yet (SEVO never touched
        # the cash) -- it's recorded HELD and gets netted against this
        # wallet's next digital payout rather than debited from a balance
        # that doesn't reflect real money yet. See net_cod_commission_payable().
        status=WalletLedgerEntry.Status.HELD if is_cash_job else WalletLedgerEntry.Status.RELEASED,
        notes=f"Commission for Job #{service_request.id}" + (" (cash job, payable)" if is_cash_job else ""),
    )

    logger.info(
        f"[SETTLEMENT_OK] Job #{service_request.id}: gross={gross} commission={commission} "
        f"net={net} -> wallet #{wallet.id} ({channel}), held until {hold_release_at.isoformat()}"
    )
    return credit_entry


def release_due_holds() -> int:
    """
    Run periodically (cron/beat): flips every HELD JOB_CREDIT entry whose
    hold_release_at has passed to RELEASED, making it withdrawable. This
    is the other half of the dispute-hold window from Section 4 --
    entries are created HELD and only become spendable once nobody's
    disputed them in time. COD_COMMISSION_PAYABLE entries are handled
    separately by net_cod_commission_payable() (they don't release into
    the balance, they get subtracted from the next digital payout).
    """
    from workforce_api.models import WalletLedgerEntry

    due = WalletLedgerEntry.objects.filter(
        status=WalletLedgerEntry.Status.HELD,
        entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT,
        hold_release_at__isnull=False,
        hold_release_at__lte=timezone.now(),
    )
    count = due.update(status=WalletLedgerEntry.Status.RELEASED)
    return count


def clawback_job(service_request, reason: str):
    """
    Section 4 dispute resolution: a validated post-completion complaint
    triggers a job-level clawback against THIS job's own held/released
    payout, never a blanket freeze on the wallet. If the JOB_CREDIT entry
    is still HELD, simply marks it CLAWED_BACK (nothing ever left the
    ledger's release path). If it already RELEASED, creates an offsetting
    CLAWBACK_DEBIT entry instead -- the original entry is never mutated
    after release, preserving the immutable-ledger guarantee.
    """
    from workforce_api.models import WalletLedgerEntry

    credit_entry = WalletLedgerEntry.objects.filter(
        job=service_request, entry_type=WalletLedgerEntry.EntryType.JOB_CREDIT
    ).first()
    if not credit_entry:
        logger.warning(f"[CLAWBACK_NO_ENTRY] No JOB_CREDIT entry found for Job #{service_request.id} to claw back.")
        return None

    with transaction.atomic():
        if credit_entry.status == WalletLedgerEntry.Status.HELD:
            credit_entry.status = WalletLedgerEntry.Status.CLAWED_BACK
            credit_entry.notes = (credit_entry.notes + f" | CLAWED BACK: {reason}")[:255]
            credit_entry.save(update_fields=["status", "notes"])
            return credit_entry
        if credit_entry.status == WalletLedgerEntry.Status.RELEASED:
            return WalletLedgerEntry.objects.create(
                wallet=credit_entry.wallet,
                job=service_request,
                worker_performed=credit_entry.worker_performed,
                entry_type=WalletLedgerEntry.EntryType.CLAWBACK_DEBIT,
                signed_amount=-credit_entry.signed_amount,
                status=WalletLedgerEntry.Status.RELEASED,
                notes=f"Clawback of Job #{service_request.id}: {reason}"[:255],
            )
        logger.info(f"[CLAWBACK_ALREADY_CLAWED_BACK] Job #{service_request.id} already clawed back.")
        return credit_entry


def net_cod_commission_payable(wallet) -> "Decimal":
    """
    Sums this wallet's outstanding COD_COMMISSION_PAYABLE entries (cash
    jobs' commission that SEVO hasn't collected yet, since it never
    touched the cash) and, if positive, nets it against the wallet's next
    RELEASED digital-job credit by creating an offsetting debit -- exactly
    the "commission payable ledger entry ... automatically netted against
    that provider's or worker's next digital payout" behaviour from
    Section 3. Called after settle_completed_job() creates a JOB_CREDIT
    for an ONLINE-paid job.
    """
    from django.db.models import Sum
    from workforce_api.models import WalletLedgerEntry

    outstanding = wallet.ledger_entries.filter(
        entry_type=WalletLedgerEntry.EntryType.COD_COMMISSION_PAYABLE,
        status=WalletLedgerEntry.Status.HELD,
    )
    total_payable = outstanding.aggregate(total=Sum("signed_amount"))["total"] or Decimal("0")
    if total_payable >= 0:
        return Decimal("0")  # nothing outstanding (signed_amount is negative)

    amount_to_net = -total_payable
    with transaction.atomic():
        WalletLedgerEntry.objects.create(
            wallet=wallet,
            entry_type=WalletLedgerEntry.EntryType.COMMISSION_DEBIT,
            signed_amount=-amount_to_net,
            status=WalletLedgerEntry.Status.RELEASED,
            notes="Netting outstanding cash-job commission against digital payout.",
        )
        outstanding.update(status=WalletLedgerEntry.Status.RELEASED)
    return amount_to_net
