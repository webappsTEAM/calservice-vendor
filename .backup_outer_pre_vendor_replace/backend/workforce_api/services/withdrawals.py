"""
Self-service + scheduled withdrawals, and minimum-balance alerts -- SEVO
business plan Section 1 (head-wallet specific features): "Scheduled
withdrawals: providers can set a standing daily/weekly auto-payout to
their bank account timed to their own wage-payment day" and "Minimum
balance alerts: providers can set a floor ... so they never get caught
short on a payday."

This module is the ONLY place that creates a WithdrawalRequest row --
services/payouts.py only knows how to execute one that already exists.
Both the on-demand withdrawal endpoint and the scheduled-withdrawal cron
call request_withdrawal() below, so validation (available balance,
per-tier daily cap) is enforced identically either way. The
WalletAccount model fields these functions read (auto_withdrawal_enabled,
auto_withdrawal_frequency, auto_withdrawal_day_of_week,
minimum_balance_alert_threshold, low_balance_alert_sent_at) already exist
-- see models.py.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

LOW_BALANCE_ALERT_COOLDOWN_HOURS = 24


class WithdrawalValidationError(Exception):
    """Raised for a user-facing validation problem (insufficient balance,
    over the KYC-tier daily cap, no payout destination on file)."""


def _today_withdrawn_total(wallet, as_of_date):
    from workforce_api.models import WithdrawalRequest
    result = WithdrawalRequest.objects.filter(
        wallet=wallet,
        requested_at__date=as_of_date,
        status__in=[
            WithdrawalRequest.Status.PENDING,
            WithdrawalRequest.Status.PROCESSING,
            WithdrawalRequest.Status.SUCCESS,
        ],
    ).aggregate(total=Sum("amount"))
    return result["total"] or Decimal("0")


@transaction.atomic
def request_withdrawal(wallet, amount, *, is_scheduled=False):
    """
    Validates and creates a WithdrawalRequest, then hands it straight to
    services.payouts.execute_withdrawal(). Raises WithdrawalValidationError
    for anything the caller should surface back to the user rather than
    attempt -- an insufficient balance, a request over the wallet's
    KYC-tier daily withdrawal cap, or no payout destination on file yet.
    """
    from workforce_api.models import WithdrawalRequest
    from workforce_api.services import payouts

    amount = Decimal(amount)
    if amount <= 0:
        raise WithdrawalValidationError("Withdrawal amount must be greater than zero.")

    if not wallet.payout_upi_id and not (wallet.payout_bank_account_number_masked and wallet.payout_ifsc):
        raise WithdrawalValidationError("Add a payout bank account or UPI ID before withdrawing.")

    available = Decimal(wallet.current_balance())
    if amount > available:
        raise WithdrawalValidationError(
            f"Withdrawal of {amount} exceeds withdrawable balance of {available}."
        )

    daily_cap = wallet.withdrawal_limit_for_tier()
    if daily_cap is not None:
        already_today = _today_withdrawn_total(wallet, timezone.localtime(timezone.now()).date())
        if already_today + amount > Decimal(daily_cap):
            raise WithdrawalValidationError(
                f"This withdrawal would exceed your {wallet.get_kyc_tier_display()} daily "
                f"limit of {daily_cap} (already withdrawn {already_today} today)."
            )

    withdrawal = WithdrawalRequest.objects.create(
        wallet=wallet, amount=amount, is_scheduled=is_scheduled,
    )
    return payouts.execute_withdrawal(withdrawal)


def _alert_recipients(wallet):
    """Who to notify for a given wallet -- the provider's own admins/
    managers for a head wallet, or the individual worker themselves."""
    from accounts.models import User
    from accounts.permissions import ADMIN_ROLES

    if wallet.account_type == wallet.AccountType.PROVIDER_HEAD:
        if not wallet.company_id:
            return []
        return list(User.objects.filter(company_id=wallet.company_id, role__in=ADMIN_ROLES))
    if wallet.employee_id and getattr(wallet.employee, "user_id", None):
        return [wallet.employee.user]
    return []


def check_minimum_balance_alerts(as_of=None):
    """
    The daily sweep: for every active wallet with a
    minimum_balance_alert_threshold set, fires an in-app notification once
    the withdrawable balance drops below it -- and doesn't re-fire for the
    same dip within LOW_BALANCE_ALERT_COOLDOWN_HOURS, so crossing the
    floor once doesn't spam a notification on every subsequent recompute.
    Returns a count of alerts actually sent.
    """
    from workforce_api.models import WalletAccount
    from workforce_api.views import create_notification

    now = as_of or timezone.now()
    sent = 0
    wallets = WalletAccount.objects.filter(
        is_active=True, minimum_balance_alert_threshold__isnull=False,
    )
    for wallet in wallets.iterator():
        try:
            if wallet.low_balance_alert_sent_at and (
                now - wallet.low_balance_alert_sent_at < timedelta(hours=LOW_BALANCE_ALERT_COOLDOWN_HOURS)
            ):
                continue

            balance = Decimal(wallet.current_balance())
            if balance >= wallet.minimum_balance_alert_threshold:
                continue

            recipients = _alert_recipients(wallet)
            if not recipients:
                continue

            for user in recipients:
                create_notification(
                    recipient=user,
                    title="Wallet balance below your alert threshold",
                    message=(
                        f"Your withdrawable balance is {balance} -- below the "
                        f"{wallet.minimum_balance_alert_threshold} floor you set."
                    ),
                    notification_type="LOW_WALLET_BALANCE",
                    company=wallet.company,
                    related_object_id=str(wallet.id),
                )
            wallet.low_balance_alert_sent_at = now
            wallet.save(update_fields=["low_balance_alert_sent_at", "updated_at"])
            sent += 1
        except Exception:
            logger.exception("check_minimum_balance_alerts: failed for wallet #%s", wallet.id)
    return sent


def _frequency_due_today(wallet, as_of_date):
    if wallet.auto_withdrawal_frequency == "DAILY":
        return True
    if wallet.auto_withdrawal_frequency == "WEEKLY":
        return wallet.auto_withdrawal_day_of_week == as_of_date.weekday()
    return False


def run_scheduled_withdrawals(as_of=None):
    """
    The daily sweep for standing auto-payout rules -- "providers can set a
    standing daily/weekly auto-payout to their bank account timed to
    their own wage-payment day". Withdraws the full withdrawable balance,
    capped by the wallet's KYC-tier daily limit, for every wallet whose
    schedule is due today. A wallet that fails validation (e.g. no payout
    destination on file) is logged and skipped rather than blocking the
    rest of the sweep. Returns a count of withdrawal requests created.
    """
    from workforce_api.models import WalletAccount

    as_of_date = as_of.date() if as_of else timezone.localtime(timezone.now()).date()

    count = 0
    wallets = WalletAccount.objects.filter(is_active=True, auto_withdrawal_enabled=True)
    for wallet in wallets.iterator():
        try:
            if not _frequency_due_today(wallet, as_of_date):
                continue

            balance = Decimal(wallet.current_balance())
            if balance <= 0:
                continue

            daily_cap = wallet.withdrawal_limit_for_tier()
            amount = min(balance, Decimal(daily_cap)) if daily_cap is not None else balance
            if amount <= 0:
                continue

            request_withdrawal(wallet, amount, is_scheduled=True)
            count += 1
        except WithdrawalValidationError as e:
            logger.warning("run_scheduled_withdrawals: skipped wallet #%s -- %s", wallet.id, e)
        except Exception:
            logger.exception("run_scheduled_withdrawals: failed for wallet #%s", wallet.id)
    return count
