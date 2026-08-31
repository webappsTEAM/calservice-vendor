"""
RazorpayX Payouts adapter -- SEVO business plan Section 1.

This module is the ONLY place that talks to RazorpayX. Everything else in
the wallet system (ledger entries, balance computation, withdrawal
requests) works entirely without it. That split is deliberate: RazorpayX
requires its own current account and its own API keys (a separate product
from plain Razorpay Payments used for customer checkout), and getting that
account activated is a business step outside this codebase's control. So
every function here checks `is_configured()` first and degrades to
WithdrawalRequest.Status.AWAITING_RAZORPAYX_ACTIVATION instead of raising --
a withdrawal request is never lost, it just queues until the real
credentials exist.

Nothing in this module ever logs or returns a raw secret.
"""
import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """True once a real RazorpayX current account is wired up. Until then,
    every function below is a documented no-op rather than a crash."""
    return bool(
        getattr(settings, "RAZORPAYX_KEY_ID", "")
        and getattr(settings, "RAZORPAYX_KEY_SECRET", "")
        and getattr(settings, "RAZORPAYX_ACCOUNT_NUMBER", "")
    )


def _client():
    """Lazily import + construct the razorpay SDK client. Imported lazily
    (not at module load) so this file imports cleanly even in an
    environment where the `razorpay` package isn't installed yet -- only
    actually calling a payout function requires it."""
    import razorpay  # same package already used for customer-side Razorpay Payments
    return razorpay.Client(auth=(settings.RAZORPAYX_KEY_ID, settings.RAZORPAYX_KEY_SECRET))


def ensure_fund_account(wallet) -> str:
    """
    Registers the wallet owner as a RazorpayX Contact + Fund Account if not
    already done, and returns the fund_account_id. Idempotent: if the
    wallet already has razorpayx_fund_account_id set, returns it unchanged
    without calling the API again.

    Raises RuntimeError if RazorpayX isn't configured, or if the wallet has
    no bank/UPI destination on file yet -- callers should catch this and
    surface "add your payout details" rather than a raw exception.
    """
    if wallet.razorpayx_fund_account_id:
        return wallet.razorpayx_fund_account_id

    if not is_configured():
        raise RuntimeError(
            "RazorpayX is not configured on this environment yet "
            "(RAZORPAYX_KEY_ID / RAZORPAYX_KEY_SECRET / RAZORPAYX_ACCOUNT_NUMBER)."
        )

    if not wallet.payout_upi_id and not (wallet.payout_bank_account_number_masked and wallet.payout_ifsc):
        raise RuntimeError(
            f"Wallet #{wallet.id} has no payout bank account or UPI ID on file -- "
            "cannot create a RazorpayX fund account without one."
        )

    owner_name = wallet.payout_bank_account_name or (
        wallet.company.company_name if wallet.company_id
        else getattr(wallet.employee, "full_name", None) or f"Employee #{wallet.employee_id}"
    )
    owner_phone = getattr(wallet.employee, "phone_number", None) if wallet.employee_id else None

    client = _client()
    contact = client.contact.create({
        "name": owner_name,
        "contact": owner_phone or "",
        "type": "vendor" if wallet.account_type == wallet.AccountType.PROVIDER_HEAD else "employee",
        "reference_id": f"wallet_{wallet.id}",
    })

    if wallet.payout_upi_id:
        fund_account = client.fund_account.create({
            "contact_id": contact["id"],
            "account_type": "vpa",
            "vpa": {"address": wallet.payout_upi_id},
        })
    else:
        fund_account = client.fund_account.create({
            "contact_id": contact["id"],
            "account_type": "bank_account",
            "bank_account": {
                "name": owner_name,
                # NOTE: payout_bank_account_number_masked is expected to hold
                # the full account number for this call despite the field
                # name -- the "masked" display value shown in-app is derived
                # from it at read time, never stored separately. See
                # onboarding serializer (Task #33/#34) for where this is set.
                "account_number": wallet.payout_bank_account_number_masked,
                "ifsc": wallet.payout_ifsc,
            },
        })

    wallet.razorpayx_contact_id = contact["id"]
    wallet.razorpayx_fund_account_id = fund_account["id"]
    wallet.save(update_fields=["razorpayx_contact_id", "razorpayx_fund_account_id", "updated_at"])
    return fund_account["id"]


@transaction.atomic
def execute_withdrawal(withdrawal) -> "object":
    """
    Attempts to actually move money for a WithdrawalRequest. Called
    immediately after a WithdrawalRequest is created (on-demand or via the
    scheduled-withdrawal cron, Task #40).

    Behaviour when RazorpayX isn't configured yet: marks the request
    AWAITING_RAZORPAYX_ACTIVATION and returns -- the ledger debit for the
    withdrawal is NOT created in that case (money hasn't actually left),
    so the wallet's available balance is untouched and the request can be
    retried once credentials exist (see retry_pending_activations below).
    """
    from workforce_api.models import WalletLedgerEntry, WithdrawalRequest

    if not is_configured():
        withdrawal.status = WithdrawalRequest.Status.AWAITING_RAZORPAYX_ACTIVATION
        withdrawal.save(update_fields=["status"])
        logger.info(
            f"[PAYOUT_PENDING_ACTIVATION] Withdrawal #{withdrawal.id} for wallet "
            f"#{withdrawal.wallet_id} queued -- RazorpayX not configured on this environment."
        )
        return withdrawal

    wallet = withdrawal.wallet
    try:
        fund_account_id = ensure_fund_account(wallet)
    except RuntimeError as e:
        withdrawal.status = WithdrawalRequest.Status.FAILED
        withdrawal.failure_reason = str(e)
        withdrawal.save(update_fields=["status", "failure_reason"])
        return withdrawal

    client = _client()
    try:
        payout = client.payout.create({
            "account_number": settings.RAZORPAYX_ACCOUNT_NUMBER,
            "fund_account_id": fund_account_id,
            "amount": int(withdrawal.amount * 100),  # RazorpayX amounts are in paise
            "currency": "INR",
            "mode": "UPI" if wallet.payout_upi_id else "IMPS",
            "purpose": "payout",
            "queue_if_low_balance": True,
            "reference_id": f"withdrawal_{withdrawal.id}",
            "narration": f"SEVO wallet withdrawal #{withdrawal.id}",
        })
    except Exception as e:
        withdrawal.status = WithdrawalRequest.Status.FAILED
        withdrawal.failure_reason = str(e)[:255]
        withdrawal.save(update_fields=["status", "failure_reason"])
        logger.error(f"[PAYOUT_FAILED] Withdrawal #{withdrawal.id}: {e}")
        return withdrawal

    withdrawal.status = WithdrawalRequest.Status.PROCESSING
    withdrawal.razorpayx_payout_id = payout.get("id", "")
    withdrawal.save(update_fields=["status", "razorpayx_payout_id"])

    # Debit the wallet ledger now that RazorpayX has actually accepted the
    # payout -- this is what makes the money disappear from the withdrawable
    # balance. Final SUCCESS/FAILED reconciliation happens via webhook
    # (handle_payout_webhook below); a payout RazorpayX later reports as
    # FAILED gets its ledger entry reversed there, not here.
    entry = WalletLedgerEntry.objects.create(
        wallet=wallet,
        entry_type=WalletLedgerEntry.EntryType.WITHDRAWAL_DEBIT,
        signed_amount=-withdrawal.amount,
        status=WalletLedgerEntry.Status.RELEASED,
        notes=f"Withdrawal #{withdrawal.id} (RazorpayX payout {payout.get('id', '')})",
    )
    withdrawal.debit_ledger_entry = entry
    withdrawal.save(update_fields=["debit_ledger_entry"])
    return withdrawal


def handle_payout_webhook(payload: dict, signature: str) -> bool:
    """
    Processes a RazorpayX payout webhook (payout.processed / payout.failed /
    payout.reversed). Verifies the signature before touching anything.
    Returns True if handled, False if the signature was invalid or the
    referenced withdrawal wasn't found (caller should still 200 the
    webhook either way, per RazorpayX's own retry-suppression guidance --
    just log and move on).
    """
    from workforce_api.models import WalletLedgerEntry, WithdrawalRequest

    if not getattr(settings, "RAZORPAYX_WEBHOOK_SECRET", ""):
        logger.warning("[PAYOUT_WEBHOOK] RAZORPAYX_WEBHOOK_SECRET not set -- rejecting webhook.")
        return False

    import razorpay
    try:
        razorpay.Utility.verify_webhook_signature(
            payload if isinstance(payload, str) else __import__("json").dumps(payload),
            signature,
            settings.RAZORPAYX_WEBHOOK_SECRET,
        )
    except Exception as e:
        logger.warning(f"[PAYOUT_WEBHOOK] Signature verification failed: {e}")
        return False

    event = payload.get("event", "")
    payout_entity = (payload.get("payload", {}) or {}).get("payout", {}).get("entity", {})
    reference_id = payout_entity.get("reference_id", "")
    if not reference_id.startswith("withdrawal_"):
        return False
    withdrawal_id = reference_id.replace("withdrawal_", "")

    try:
        withdrawal = WithdrawalRequest.objects.select_related("wallet").get(id=withdrawal_id)
    except (WithdrawalRequest.DoesNotExist, ValueError):
        logger.warning(f"[PAYOUT_WEBHOOK] No WithdrawalRequest for reference_id={reference_id}")
        return False

    with transaction.atomic():
        if event == "payout.processed":
            withdrawal.status = WithdrawalRequest.Status.SUCCESS
            withdrawal.razorpayx_utr = payout_entity.get("utr", "")
            withdrawal.processed_at = timezone.now()
            withdrawal.save(update_fields=["status", "razorpayx_utr", "processed_at"])
        elif event in ("payout.failed", "payout.reversed"):
            withdrawal.status = WithdrawalRequest.Status.FAILED
            withdrawal.failure_reason = f"RazorpayX {event}"
            withdrawal.processed_at = timezone.now()
            withdrawal.save(update_fields=["status", "failure_reason", "processed_at"])
            # Reverse the WITHDRAWAL_DEBIT ledger entry -- the money never
            # actually left, so the wallet's balance must reflect that.
            if withdrawal.debit_ledger_entry_id:
                WalletLedgerEntry.objects.create(
                    wallet=withdrawal.wallet,
                    entry_type=WalletLedgerEntry.EntryType.REFUND_ADJUSTMENT,
                    signed_amount=withdrawal.amount,
                    status=WalletLedgerEntry.Status.RELEASED,
                    notes=f"Reversal: withdrawal #{withdrawal.id} {event}",
                )
    return True


def retry_pending_activations() -> int:
    """
    Run periodically (or once, right after RazorpayX credentials are added
    to the environment) to sweep every WithdrawalRequest stuck in
    AWAITING_RAZORPAYX_ACTIVATION and actually attempt them now that
    credentials exist. Returns the count retried.
    """
    from workforce_api.models import WithdrawalRequest

    if not is_configured():
        return 0
    pending = WithdrawalRequest.objects.filter(status=WithdrawalRequest.Status.AWAITING_RAZORPAYX_ACTIVATION)
    count = 0
    for withdrawal in pending:
        execute_withdrawal(withdrawal)
        count += 1
    return count
