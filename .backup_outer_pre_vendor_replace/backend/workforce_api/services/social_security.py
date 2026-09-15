"""
Social Security Code, 2020 registration tracking -- SEVO business plan
Section 8 (Labour classification): for the individual-worker channel,
SEVO is the "aggregator" under the 2026 Central Rules and must register
on the government portal (Shram Suvidha), and workers become eligible
for benefits once they cross 90 days worked with SEVO in a financial
year (April 1 - March 31 in India).

Scope note: this module counts days worked and flags eligibility -- it
does NOT talk to the Shram Suvidha portal (no public API exists for
individual platforms to integrate against at the time this was built).
The SocialSecurityRegistration model's own docstring already frames this
correctly: "an accurate, exportable worklist for whoever does that
submission, not an automated integration with a government system SEVO
doesn't have API access to." Registration itself is a manual, admin-side
action (see WorkforceAdminSocialSecurityMarkRegisteredView) once someone
has actually completed the portal submission.

Only individual workers are in scope -- for the provider channel, SEVO's
contractual relationship is with the provider business, not their
workers, which is the basis (per Section 8) for SEVO staying outside the
aggregator definition for those workers. "Individual worker" here is
detected the same way the rest of the wallet system detects it: an
Employee with an INDIVIDUAL_WORKER WalletAccount (see
services/wallet_onboarding.py).
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

ELIGIBILITY_THRESHOLD_DAYS = 90


def current_financial_year_start(as_of=None):
    """Indian financial year runs April 1 - March 31. Returns the date
    April 1 of the FY containing `as_of` (defaults to today)."""
    as_of = as_of or timezone.localtime(timezone.now()).date()
    year = as_of.year if as_of.month >= 4 else as_of.year - 1
    return as_of.replace(year=year, month=4, day=1)


def _is_individual_worker(employee):
    from workforce_api.models import WalletAccount
    return WalletAccount.objects.filter(
        employee=employee, account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
    ).exists()


@transaction.atomic
def recompute_registration_status(employee, as_of=None):
    """
    Idempotent: recounts this employee's distinct days-worked in the
    current financial year from completed jobs, and updates their
    SocialSecurityRegistration row's day count and status accordingly.
    Returns the row, or None if this employee isn't an individual worker
    (out of scope -- see module docstring) or isn't an assignable worker
    at all.

    Never downgrades an already-REGISTERED row's status -- registration,
    once actually completed on the government portal, doesn't get undone
    by a day-count recompute.
    """
    from workforce_api.models import SocialSecurityRegistration
    from service_requests.models import ServiceRequest

    if not _is_individual_worker(employee):
        return None

    fy_start = current_financial_year_start(as_of)
    as_of = as_of or timezone.localtime(timezone.now()).date()

    days_worked = ServiceRequest.objects.filter(
        assigned_employee=employee,
        status="completed",
        updated_at__date__gte=fy_start,
        updated_at__date__lte=as_of,
    ).dates("updated_at", "day").count()

    registration, _created = SocialSecurityRegistration.objects.get_or_create(
        employee=employee,
        defaults={"financial_year_start": fy_start},
    )

    # A new financial year has started since this row was last touched --
    # the day count resets (eligibility is per-FY), but a REGISTERED
    # status is a durable fact about the worker's registration, not
    # something a new FY undoes.
    if registration.financial_year_start != fy_start:
        registration.financial_year_start = fy_start
        days_worked = ServiceRequest.objects.filter(
            assigned_employee=employee, status="completed",
            updated_at__date__gte=fy_start, updated_at__date__lte=as_of,
        ).dates("updated_at", "day").count()

    registration.days_worked_current_fy = days_worked

    if registration.status != SocialSecurityRegistration.RegistrationStatus.REGISTERED:
        if days_worked >= ELIGIBILITY_THRESHOLD_DAYS:
            if registration.status != SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION:
                logger.info(
                    "[SOCIAL_SECURITY_ELIGIBLE] Employee #%s crossed %s days worked in FY starting %s -- "
                    "now eligible, registration pending.",
                    employee.id, ELIGIBILITY_THRESHOLD_DAYS, fy_start,
                )
            registration.status = SocialSecurityRegistration.RegistrationStatus.ELIGIBLE_PENDING_REGISTRATION
        else:
            registration.status = SocialSecurityRegistration.RegistrationStatus.NOT_YET_ELIGIBLE

    registration.save(update_fields=["financial_year_start", "days_worked_current_fy", "status", "updated_at"])
    return registration


def recompute_all(as_of=None):
    """Bulk recompute across every individual-worker employee -- the daily
    cron's entry point. Returns a count of rows touched."""
    from employees.models import Employee
    from workforce_api.models import WalletAccount

    individual_worker_employee_ids = WalletAccount.objects.filter(
        account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
    ).values_list("employee_id", flat=True)

    count = 0
    for employee in Employee.objects.filter(id__in=individual_worker_employee_ids).iterator():
        try:
            if recompute_registration_status(employee, as_of=as_of) is not None:
                count += 1
        except Exception:
            logger.exception("recompute_all (social security): failed for employee #%s", employee.id)
    return count


class SocialSecurityMarkRegisteredError(Exception):
    """Raised for a user-facing validation problem when marking a worker
    registered (e.g. missing portal reference)."""


def mark_registered(registration, *, registered_by, portal_reference_id):
    """
    Records that an admin has actually completed the Shram Suvidha portal
    submission for this worker. Manual and deliberately so -- see module
    docstring on why this isn't automated.
    """
    from workforce_api.models import SocialSecurityRegistration

    portal_reference_id = (portal_reference_id or "").strip()
    if not portal_reference_id:
        raise SocialSecurityMarkRegisteredError("A portal reference ID is required to mark a worker as registered.")

    registration.status = SocialSecurityRegistration.RegistrationStatus.REGISTERED
    registration.registered_at = timezone.now()
    registration.registered_by = (registered_by or "").strip()
    registration.portal_reference_id = portal_reference_id
    registration.save(update_fields=["status", "registered_at", "registered_by", "portal_reference_id", "updated_at"])
    return registration
