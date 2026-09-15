"""
python manage.py audit_jobpayment_reconciliation [--limit N] [--json]

HS-C-03/HS-C-06: this app's JobPayment model (workforce_api/models.py)
calls itself "the authoritative payment state machine" and gates job
completion on it (see ServiceRequest's completion-readiness check in
service_requests/models.py), but its payment_status vocabulary
(PENDING/AUTHORIZED/PAID/CASH_PENDING/FAILED/REFUNDED/CANCELLED) is
completely separate from ServiceRequest.payment_status (the field the
Customer app's UI actually reads) -- and no code path in this app was
found that keeps the two in sync as a matter of course; some views write
both fields together at the moment of a transition (e.g. marking
CASH_PENDING also sets job.payment_status = "cash_pending"), but there is
no ongoing reconciliation, so any row that was updated by one path and
not the other, or by direct DB access, or from before the two fields
existed together, can drift.

This command is READ-ONLY -- it does not correct anything, only reports
where the two disagree with the expected-correspondence table below, so
a human can decide the right fix per case. See
audit_payment_reconciliation.py in the Customer app for the other half
of this reconciliation (ServiceRequest.payment_status vs
RefundRequest.status, which this app cannot see -- RefundRequest lives
only in the Customer app's database models).
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Read-only audit of JobPayment.payment_status vs ServiceRequest.payment_status divergence (HS-C-03/HS-C-06)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=200, help="Stop after reporting this many findings (still counts the true total).")
        parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of a human report.")

    def handle(self, *args, **options):
        from workforce_api.models import JobPayment

        limit = options["limit"]
        as_json = options["json"]

        # Expected ServiceRequest.payment_status values for each JobPayment
        # state -- "the authoritative model says X, so the shared field
        # should say one of these". Anything outside this set is a finding.
        EXPECTED = {
            JobPayment.PaymentStatus.PENDING: {"pending"},
            JobPayment.PaymentStatus.AUTHORIZED: {"pending", "processing"},
            JobPayment.PaymentStatus.PAID: {"paid", "collected"},
            JobPayment.PaymentStatus.CASH_PENDING: {"cash_pending"},
            JobPayment.PaymentStatus.FAILED: {"failed"},
            JobPayment.PaymentStatus.REFUNDED: {"refunded", "partially_refunded"},
            JobPayment.PaymentStatus.CANCELLED: {"cancelled"},
        }

        findings = []
        qs = JobPayment.objects.select_related("job").only(
            "id", "payment_status", "amount_due", "amount_paid",
            "job__id", "job__request_id", "job__payment_status",
        )
        for pmt in qs.iterator():
            job = pmt.job
            if job is None:
                continue
            expected = EXPECTED.get(pmt.payment_status, set())
            if (job.payment_status or "").lower() not in expected:
                findings.append({
                    "job_id": job.id,
                    "request_id": job.request_id,
                    "jobpayment_status": pmt.payment_status,
                    "servicerequest_payment_status": job.payment_status,
                    "expected_one_of": sorted(expected),
                })

        if as_json:
            import json
            self.stdout.write(json.dumps({"total": len(findings), "sample": findings[:limit]}, indent=2, default=str))
            return

        self.stdout.write(self.style.MIGRATE_HEADING("HS-C-03/HS-C-06 JobPayment reconciliation audit (read-only)"))
        self.stdout.write("")
        self.stdout.write(f"JobPayment.payment_status disagrees with ServiceRequest.payment_status: {len(findings)}")
        for f in findings[:limit]:
            self.stdout.write(
                f"     job {f['request_id']} (id={f['job_id']}) "
                f"JobPayment={f['jobpayment_status']!r} ServiceRequest={f['servicerequest_payment_status']!r} "
                f"expected one of {f['expected_one_of']}"
            )
        self.stdout.write("")
        if not findings:
            self.stdout.write(self.style.SUCCESS("No divergences found."))
        else:
            self.stdout.write(self.style.WARNING(f"{len(findings)} divergence(s) found -- this command made no changes. Review each case before deciding how to correct it."))
