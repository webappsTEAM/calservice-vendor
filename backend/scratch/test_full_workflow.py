import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'workforce_core.settings')
django.setup()

import uuid
from decimal import Decimal
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from accounts.models import User
from employees.models import Employee
from service_requests.models import ServiceRequest, Estimation, EstimationFee, EstimationQuotation, EstimationQuotationItem
from workforce_api.models import WorkforceQuote, WorkforceQuoteItem
from workforce_api.views import WorkforceJobListView, WorkforceQuoteListView
from service_requests.vendor_views import (
    VendorEstimationAssignTechnicianView,
    VendorEstimationQuotationView,
    VendorEstimationQuotationSendView,
    VendorEstimationCustomerDecideView,
    VendorEstimationInvoiceView,
)

factory = APIRequestFactory()

def run_tests():
    print("==================================================")
    print("TESTING ESTIMATION IN JOBS, QUOTES, CONVERSION, AND INVOICING")
    print("==================================================")

    # 1. Setup Admin & Technician
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create(username=f"admin_test_{uuid.uuid4().hex[:6]}", role="admin", is_staff=True, is_superuser=True)

    tech_emp = Employee.objects.filter(is_active=True).first()
    assert tech_emp is not None, "Need at least one active employee"
    b_det = tech_emp.bank_details or {}
    if not isinstance(b_det, dict):
        b_det = {}
    b_det["onboarding"] = {"status": "approved"}
    tech_emp.bank_details = b_det
    tech_emp.save(update_fields=["bank_details"])
    tech_user = tech_emp.user
    print(f"Admin: {admin_user.username}, Tech: {tech_user.username} (Emp ID: {tech_emp.id})")

    # 2. Create Lead
    req_id = f"AC{uuid.uuid4().hex[:5].upper()}"
    sr = ServiceRequest.objects.create(
        request_id=req_id,
        customer_name="Ramesh Kumar",
        phone="+919888877777",
        address="104, Green Glen Layout, Bellandur, Bengaluru",
        service_category="Air Conditioner",
        issue_title="AC Not Cooling - Low Gas & Strange Noise",
        job_type="ESTIMATION",
        status="requested",
        total_amount=Decimal("199.00"),
        preferred_date=timezone.now().date(),
    )
    est = Estimation.objects.create(
        service_request=sr,
        ac_type="SPLIT",
        ac_brand="Daikin",
        ac_capacity="1.5_TON",
        ac_quantity=1,
        customer_symptom=sr.issue_title,
        status="REQUESTED",
    )
    fee = EstimationFee.objects.create(
        estimation=est,
        amount=Decimal("199.00"),
        currency="INR",
        status="PENDING",
    )
    print(f"[OK] Lead created: SR #{sr.id} ({sr.request_id})")

    # 3. Assign Technician
    assign_view = VendorEstimationAssignTechnicianView.as_view()
    assign_req = factory.post(f"/api/vendor/estimations/{sr.id}/assign-technician/", {
        "technician_id": tech_emp.id,
        "technician_name": tech_user.get_full_name() or tech_user.username,
        "technician_phone": tech_emp.phone or "+919876543210",
    }, format="json")
    force_authenticate(assign_req, user=admin_user)
    assign_res = assign_view(assign_req, pk=sr.id)
    assert assign_res.status_code == 200, f"Assign failed: {assign_res.data}"
    sr.refresh_from_db()
    assert sr.assigned_employee_id == tech_emp.id, "assigned_employee not set on SR"
    print(f"[OK] Technician assigned. SR status: {sr.status}, assigned_emp: {sr.assigned_employee_id}")

    # 4. Verify Visibility in Admin Jobs
    admin_jobs_view = WorkforceJobListView.as_view()
    admin_req = factory.get("/api/workforce/jobs/?scope=admin")
    force_authenticate(admin_req, user=admin_user)
    admin_res = admin_jobs_view(admin_req)
    assert admin_res.status_code == 200
    admin_job_ids = [j["id"] for j in admin_res.data]
    assert sr.id in admin_job_ids, f"SR #{sr.id} not found in admin jobs list: {admin_job_ids[:10]}"
    print(f"[OK] SR #{sr.id} is VISIBLE in Admin Jobs page.")

    # 5. Verify Visibility in Technician Queue
    tech_req = factory.get("/api/workforce/jobs/?status=active")
    force_authenticate(tech_req, user=tech_user)
    tech_res = admin_jobs_view(tech_req)
    assert tech_res.status_code == 200
    tech_job_ids = [j["id"] for j in tech_res.data]
    assert sr.id in tech_job_ids, f"SR #{sr.id} not found in technician jobs list: {tech_job_ids}"
    print(f"[OK] SR #{sr.id} is VISIBLE in Technician Active Jobs queue.")

    # 6. Build and Send Quotation
    quote_view = VendorEstimationQuotationView.as_view()
    quote_req = factory.post(f"/api/vendor/estimations/{sr.id}/quotation/", {
        "notes": "Full diagnostic and gas replenishment recommended.",
        "valid_until": "2026-09-30",
        "items": [
            {
                "item_type": "GAS",
                "service_name": "R32 Refrigerant Gas Top-Up",
                "description": "Full charging with vacuuming",
                "quantity": 1,
                "unit": "unit",
                "unit_price": 2200,
                "tax_rate": 18,
                "discount_amount": 200,
            },
            {
                "item_type": "LABOR",
                "service_name": "Deep Chemical Coil Jet Cleaning",
                "description": "Indoor & outdoor pressure wash",
                "quantity": 1,
                "unit": "unit",
                "unit_price": 799,
                "tax_rate": 18,
                "discount_amount": 0,
            }
        ]
    }, format="json")
    force_authenticate(quote_req, user=admin_user)
    quote_res = quote_view(quote_req, pk=sr.id)
    assert quote_res.status_code == 201, f"Quotation build failed: {quote_res.data}"
    est_quote = EstimationQuotation.objects.filter(estimation=est).first()
    assert est_quote is not None
    print(f"[OK] Quotation created: #{est_quote.quote_ref}, total: Rs.{est_quote.total_amount}")

    # Send Quotation
    send_view = VendorEstimationQuotationSendView.as_view()
    send_req = factory.post(f"/api/vendor/estimations/{sr.id}/quotation/{est_quote.id}/send/")
    force_authenticate(send_req, user=admin_user)
    send_res = send_view(send_req, pk=sr.id, quote_id=est_quote.id)
    assert send_res.status_code == 200

    # 7. Verify Synchronized WorkforceQuote in Estimates Page
    quotes_list_view = WorkforceQuoteListView.as_view()
    quotes_req = factory.get("/api/workforce/quotes/")
    force_authenticate(quotes_req, user=admin_user)
    quotes_res = quotes_list_view(quotes_req)
    assert quotes_res.status_code == 200
    matched_quote = next((q for q in quotes_res.data if q.get("quote_number") == est_quote.quote_ref), None)
    assert matched_quote is not None, f"Quotation {est_quote.quote_ref} not found in Estimates API!"
    assert float(matched_quote["total_amount"]) == float(est_quote.total_amount)
    print(f"[OK] Quotation #{est_quote.quote_ref} successfully visible on Estimates page API.")

    # 8. Test Customer Acceptance & Conversion to Service Job (Same-Day)
    decide_view = VendorEstimationCustomerDecideView.as_view()
    today_str = timezone.now().date().strftime("%Y-%m-%d")
    decide_req = factory.post(f"/api/vendor/estimations/{sr.id}/customer-decide/", {
        "decision": "APPROVE",
        "scheduled_date": today_str,
        "scheduled_time": "02:00 PM - 05:00 PM",
    }, format="json")
    force_authenticate(decide_req, user=admin_user)
    decide_res = decide_view(decide_req, pk=sr.id)
    assert decide_res.status_code == 200, f"Customer decide failed: {decide_res.data}"

    sr.refresh_from_db()
    est.refresh_from_db()
    fee.refresh_from_db()

    # Check Conversion
    assert sr.job_type == "SERVICE", f"Expected job_type 'SERVICE', got '{sr.job_type}'"
    assert est.status == "CONVERTED_TO_JOB", f"Expected est.status 'CONVERTED_TO_JOB', got '{est.status}'"
    assert sr.status == "assigned", f"Expected SR status 'assigned', got '{sr.status}'"
    assert sr.assigned_employee_id == tech_emp.id, "Expected same technician to be assigned for same-day"
    assert float(sr.total_amount) == float(est_quote.total_amount), f"Expected total_amount {est_quote.total_amount}, got {sr.total_amount}"
    assert fee.status == "WAIVED", f"Expected estimation fee to be WAIVED, got {fee.status}"
    print(f"[OK] ADD-ON 1 & 2 PASSED: Quotation converted to SERVICE job, same technician {sr.technician_name} assigned, fee waived.")

    # 9. Test Invoicing Endpoint for Converted Job
    inv_view = VendorEstimationInvoiceView.as_view()
    inv_req = factory.get(f"/api/vendor/estimations/{sr.id}/invoice/")
    inv_res = inv_view(inv_req, pk=sr.id)
    assert inv_res.status_code == 200
    inv_data = inv_res.data["invoice"]
    assert len(inv_data["line_items"]) == 2
    assert float(inv_data["total_amount"]) == float(est_quote.total_amount)
    print(f"[OK] Invoice endpoint works for converted job: #{inv_data['invoice_number']}")

    # 10. Test Scenario B: Customer Cancellation & Fee Collection Invoicing
    sr2 = ServiceRequest.objects.create(
        request_id=f"AC{uuid.uuid4().hex[:5].upper()}",
        customer_name="Priya Sharma",
        phone="+919777766666",
        address="Flat 202, Palm Meadows, Whitefield, Bengaluru",
        service_category="Air Conditioner",
        issue_title="AC Water Leakage Inside Room",
        job_type="ESTIMATION",
        status="technician_arrived",
        total_amount=Decimal("199.00"),
        preferred_date=timezone.now().date(),
    )
    est2 = Estimation.objects.create(
        service_request=sr2,
        ac_type="SPLIT",
        ac_brand="LG",
        customer_symptom=sr2.issue_title,
        status="INSPECTION_COMPLETED",
    )
    fee2 = EstimationFee.objects.create(
        estimation=est2,
        amount=Decimal("199.00"),
        currency="INR",
        status="PENDING",
    )
    quote2 = EstimationQuotation.objects.create(
        estimation=est2,
        version=1,
        quote_ref=f"QTE-{sr2.request_id}-V1",
        status="SENT",
        total_amount=Decimal("1850.00"),
        subtotal=Decimal("1850.00"),
    )

    cancel_req = factory.post(f"/api/vendor/estimations/{sr2.id}/customer-decide/", {
        "decision": "REJECT",
        "rejection_reason": "PRICE_TOO_HIGH",
        "rejection_note": "Found local technician cheaper.",
        "payment_method": "ONLINE",
        "payment_reference": "PAY_RZP_TEST_99812",
    }, format="json")
    force_authenticate(cancel_req, user=admin_user)
    cancel_res = decide_view(cancel_req, pk=sr2.id)
    assert cancel_res.status_code == 200

    sr2.refresh_from_db()
    fee2.refresh_from_db()
    assert sr2.status == "cancelled"
    assert fee2.status == "COLLECTED"
    assert sr2.invoice_id is not None
    assert sr2.payment_status == "collected"
    assert float(sr2.total_amount) == 199.00
    print(f"[OK] ADD-ON 3 PASSED: Cancellation collected Rs.199 fee and generated DB invoice: {sr2.invoice_id}")

    # Check Invoice endpoint for cancelled estimation
    inv2_req = factory.get(f"/api/vendor/estimations/{sr2.id}/invoice/")
    inv2_res = inv_view(inv2_req, pk=sr2.id)
    assert inv2_res.status_code == 200
    assert inv2_res.data["invoice"]["invoice_number"] == sr2.invoice_id
    assert inv2_res.data["invoice"]["status"] == "PAID"
    assert float(inv2_res.data["invoice"]["total_amount"]) == 199.00
    print(f"[OK] Authoritative DB invoice ready for customer download: {inv2_res.data['invoice']['invoice_number']}")

    # Check HTML format
    inv2_html_req = factory.get(f"/api/vendor/estimations/{sr2.id}/invoice/?format=html")
    inv2_html_res = inv_view(inv2_html_req, pk=sr2.id)
    if hasattr(inv2_html_res, "render"):
        inv2_html_res.render()
    print(f"HTML status code: {inv2_html_res.status_code}, data: {getattr(inv2_html_res, 'data', None)}")
    assert inv2_html_res.status_code == 200
    assert b"CalServices" in inv2_html_res.content
    print("[OK] Printable HTML invoice generated successfully.")

    # Cleanup
    sr.delete()
    sr2.delete()
    print("\n==================================================")
    print("ALL 10 VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
