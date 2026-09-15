"""
workforce_api/services/cash_reconciliation.py

GT-C-02: cash-on-service collected by a technician was never reconciled --
JobPayment tracked the collection itself (CASH_PENDING -> PAID via OTP
confirmation) but nothing tracked whether that cash actually made it back to
the office. This module is the settlement half: compute what a technician
should be holding, and record what they actually handed in.
"""
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from workforce_api.models import JobPayment, CashSettlement


def compute_outstanding_cash(employee):
    """Sum of amount_received for every unreconciled, successfully collected
    cash payment for this employee. This is what the employee should
    currently be holding."""
    qs = JobPayment.objects.filter(
        employee=employee,
        payment_method=JobPayment.PaymentMethod.CASH_ON_SERVICE,
        payment_status=JobPayment.PaymentStatus.PAID,
        reconciled=False,
    )
    total = Decimal("0.00")
    for p in qs:
        total += (p.amount_received if p.amount_received is not None else p.amount_paid) or Decimal("0.00")
    return total, qs


def record_cash_settlement(employee, company, deposited_amount, recorded_by, notes=""):
    """
    Records a settlement: computes expected_amount from every currently
    outstanding cash payment for this employee, compares to what was
    actually deposited, and marks every matched JobPayment reconciled --
    all inside one transaction so a settlement can never mark only some of
    the outstanding payments as reconciled.
    """
    deposited_amount = Decimal(str(deposited_amount))
    if deposited_amount < 0:
        raise ValueError("Deposited amount cannot be negative.")

    with transaction.atomic():
        expected_amount, outstanding_qs = compute_outstanding_cash(employee)
        outstanding_ids = list(outstanding_qs.values_list("id", flat=True))
        discrepancy = deposited_amount - expected_amount

        settlement = CashSettlement.objects.create(
            employee=employee,
            company=company,
            expected_amount=expected_amount,
            deposited_amount=deposited_amount,
            discrepancy=discrepancy,
            notes=notes,
            recorded_by=recorded_by,
        )

        JobPayment.objects.filter(id__in=outstanding_ids).update(
            reconciled=True, reconciled_in=settlement, updated_at=timezone.now()
        )

    return settlement


def list_cash_settlements(employee=None, company=None, limit=100):
    qs = CashSettlement.objects.select_related("employee", "company", "recorded_by")
    if employee:
        qs = qs.filter(employee=employee)
    if company:
        qs = qs.filter(company=company)
    return qs[:limit]
