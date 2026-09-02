"""
Wallet onboarding/provisioning helpers -- SEVO business plan Section 2
(dual onboarding flow) and half of Section 1 (KYC tiers).

Kept separate from commission.py (which only ever runs at job-completion
time) so the signup/onboarding request path never has to import the
settlement engine, and vice versa.

Nothing here talks to RazorpayX directly -- fund-account creation with
RazorpayX only happens lazily, the first time a withdrawal is actually
attempted (see services/payouts.py:ensure_fund_account). Onboarding only
ever touches the local WalletAccount row.
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def provision_provider_wallet(company):
    """
    Idempotent: get_or_create a PROVIDER_HEAD wallet for a provider
    business's Company row. Called once, right after a new provider
    business signs up (ProviderSignupView) -- every job a provider's team
    completes settles into this single wallet regardless of which of the
    provider's own workers actually did the job (see
    commission.py:resolve_payee_wallet and WalletLedgerEntry.worker_performed
    for the per-job attribution trail that keeps that fact visible).
    """
    from workforce_api.models import WalletAccount

    wallet, _created = WalletAccount.objects.get_or_create(
        company=company,
        account_type=WalletAccount.AccountType.PROVIDER_HEAD,
    )
    return wallet


def provision_individual_wallet(employee):
    """
    Idempotent: get_or_create an INDIVIDUAL_WORKER wallet for a worker who
    signed up without a provider company_id/company_slug -- the "Individual
    Worker Model" from Section 2. This wallet, not any company's head
    wallet, is what resolve_payee_wallet() finds first for this employee's
    completed jobs.

    Deliberately non-fatal to call from a signup transaction: wallet
    provisioning failing should never block someone from creating an
    account. Callers should wrap this in try/except and log rather than
    let it roll back the whole signup (see WorkforceSignupView).
    """
    from workforce_api.models import WalletAccount

    wallet, _created = WalletAccount.objects.get_or_create(
        employee=employee,
        account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
    )
    return wallet


def resolve_wallet_for_user(user):
    """
    Which wallet (if any) the currently-authenticated user is entitled to
    see/manage, and what kind of owner they are. Used by
    WalletPayoutDetailsView and any wallet-dashboard endpoints.

    Rules:
      - Solo Worker (independent technician): individual_worker wallet.
      - Tied Worker (dedicated to a vendor): None, None (money flows directly to company wallet).
      - Provider / Vendor Admin: provider_admin (company head wallet).
      - Platform Superadmin: None, None or company head wallet if tenant scoped.
    """
    from workforce_api.models import WalletAccount, VendorTechnicianRelationship

    emp = getattr(user, "employee_profile", None)
    if emp is not None:
        # Check if worker is tied to a vendor
        has_active_rel = VendorTechnicianRelationship.objects.filter(
            technician=emp,
            status=VendorTechnicianRelationship.Status.ACTIVE,
        ).exists()
        if has_active_rel or emp.company_id:
            # Tied workers do not have a separate wallet; job revenue flows to their vendor
            return None, None

        # Solo worker
        try:
            return emp.individual_wallet, "individual_worker"
        except WalletAccount.DoesNotExist:
            wallet, _ = WalletAccount.objects.get_or_create(
                employee=emp,
                account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
            )
            return wallet, "individual_worker"

    company = getattr(user, "company", None)
    if company is not None and getattr(user, "role", "") in ("admin", "manager"):
        try:
            return company.head_wallet, "provider_admin"
        except WalletAccount.DoesNotExist:
            wallet, _ = WalletAccount.objects.get_or_create(
                company=company,
                account_type=WalletAccount.AccountType.PROVIDER_HEAD,
            )
            return wallet, "provider_admin"

    return None, None


class PayoutDetailsError(Exception):
    """Raised for a user-facing validation problem (bad IFSC shape, no
    destination given at all, etc) -- callers should surface str(e) as a
    400, not a 500."""


@transaction.atomic
def set_payout_details(wallet, *, bank_account_name="", bank_account_number="", ifsc="", upi_id=""):
    """
    Updates a wallet's payout destination (Section 1: "workers/providers add
    their bank account or UPI ID during onboarding"). Requires either a full
    bank account (name + number + IFSC) or a UPI ID -- partial bank details
    are rejected rather than silently stored, since ensure_fund_account()
    (services/payouts.py) would otherwise fail opaquely at withdrawal time
    instead of at onboarding time when the user can still fix it.

    On first successful save, bumps kyc_tier from TIER_0 (provisional) to
    TIER_1 (verified enough to receive payouts up to the Tier 1 withdrawal
    limit -- see WalletAccount.withdrawal_limit_for_tier()). TIER_2 (fully
    KYC'd, uncapped) is an admin-side upgrade, not something onboarding
    itself grants -- see workforce_api admin actions.
    """
    from workforce_api.models import WalletAccount

    upi_id = (upi_id or "").strip()
    bank_account_name = (bank_account_name or "").strip()
    bank_account_number = (bank_account_number or "").strip()
    ifsc = (ifsc or "").strip().upper()

    has_upi = bool(upi_id)
    has_bank = bool(bank_account_name and bank_account_number and ifsc)

    if not has_upi and not has_bank:
        raise PayoutDetailsError(
            "Provide either a UPI ID, or all of account holder name, "
            "account number, and IFSC code."
        )
    if ifsc and (len(ifsc) != 11 or not ifsc[:4].isalpha() or not ifsc[4:].isalnum()):
        raise PayoutDetailsError("IFSC code looks invalid -- expected an 11-character code, e.g. HDFC0001234.")

    wallet.payout_upi_id = upi_id
    wallet.payout_bank_account_name = bank_account_name
    wallet.payout_bank_account_number_masked = bank_account_number
    wallet.payout_ifsc = ifsc

    # A changed payout destination invalidates any previously-registered
    # RazorpayX fund account -- ensure_fund_account() will lazily recreate
    # one against the new details next time a withdrawal is attempted.
    wallet.razorpayx_contact_id = ""
    wallet.razorpayx_fund_account_id = ""

    update_fields = [
        "payout_upi_id", "payout_bank_account_name",
        "payout_bank_account_number_masked", "payout_ifsc",
        "razorpayx_contact_id", "razorpayx_fund_account_id", "updated_at",
    ]
    if wallet.kyc_tier == WalletAccount.KYCTier.TIER_0_PROVISIONAL:
        wallet.kyc_tier = WalletAccount.KYCTier.TIER_1_VERIFIED
        wallet.kyc_tier_updated_at = timezone.now()
        update_fields += ["kyc_tier", "kyc_tier_updated_at"]

    wallet.save(update_fields=update_fields)
    return wallet
