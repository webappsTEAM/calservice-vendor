"""
Workforce API Services module.
"""
from .automatic_dispatch import (
    dispatch_job,
    dispatch_pending_jobs,
    dispatch_next_candidate,
    get_eligible_candidates,
    expire_and_reassign_offers,
    reconsider_jobs_for_employee,
)
from .workload import (
    ACTIVE_QUEUE_STATUSES,
    ACTIVE_WORKLOAD_STATUSES,
    WORKLOAD_OCCUPIED_STATUSES,
    TERMINAL_WORKLOAD_STATUSES,
    get_employee_active_job,
    is_employee_busy,
    reconcile_employee_availability,
    supersede_other_offers_for_employee,
)
from .cash_reconciliation import (
    compute_outstanding_cash,
    record_cash_settlement,
    list_cash_settlements,
)
from .payouts import (
    is_configured as razorpayx_is_configured,
    ensure_fund_account,
    execute_withdrawal,
    handle_payout_webhook,
    retry_pending_activations,
)
from .commission import (
    settle_completed_job,
    release_due_holds,
    clawback_job,
    net_cod_commission_payable,
    resolve_payee_wallet,
    commission_rate_for,
)

from .wallet_onboarding import (
    provision_provider_wallet,
    provision_individual_wallet,
    resolve_wallet_for_user,
    set_payout_details,
    PayoutDetailsError,
)

from .scorecards import (
    recalculate_employee_scorecard,
    recalculate_all_scorecards,
)

from .reconciliation import (
    run_daily_reconciliation,
    run_daily_reconciliation_all_companies,
)

from .tax_statements import (
    generate_earnings_statement,
    export_ledger_csv,
)

from .social_security import (
    recompute_registration_status,
    recompute_all as recompute_all_social_security,
    mark_registered as mark_social_security_registered,
    SocialSecurityMarkRegisteredError,
    current_financial_year_start,
)

__all__ = [
    "dispatch_job",
    "dispatch_pending_jobs",
    "dispatch_next_candidate",
    "get_eligible_candidates",
    "expire_and_reassign_offers",
    "reconsider_jobs_for_employee",
    "ACTIVE_QUEUE_STATUSES",
    "ACTIVE_WORKLOAD_STATUSES",
    "WORKLOAD_OCCUPIED_STATUSES",
    "TERMINAL_WORKLOAD_STATUSES",
    "get_employee_active_job",
    "is_employee_busy",
    "reconcile_employee_availability",
    "supersede_other_offers_for_employee",
    "compute_outstanding_cash",
    "record_cash_settlement",
    "list_cash_settlements",
    "razorpayx_is_configured",
    "ensure_fund_account",
    "execute_withdrawal",
    "handle_payout_webhook",
    "retry_pending_activations",
    "settle_completed_job",
    "release_due_holds",
    "clawback_job",
    "net_cod_commission_payable",
    "resolve_payee_wallet",
    "commission_rate_for",
    "provision_provider_wallet",
    "provision_individual_wallet",
    "resolve_wallet_for_user",
    "set_payout_details",
    "PayoutDetailsError",
    "recalculate_employee_scorecard",
    "recalculate_all_scorecards",
    "run_daily_reconciliation",
    "run_daily_reconciliation_all_companies",
    "generate_earnings_statement",
    "export_ledger_csv",
    "recompute_registration_status",
    "recompute_all_social_security",
    "mark_social_security_registered",
    "SocialSecurityMarkRegisteredError",
    "current_financial_year_start",
]
