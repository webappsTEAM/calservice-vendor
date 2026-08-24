#!/usr/bin/env python
"""
backend/setup_manual_e2e_scenario.py

Provisions a complete, real database scenario for manual browser E2E testing:
  1. Creates or updates a designated test technician account with known credentials.
  2. Creates a realistic quotation-based Estimation ServiceRequest assigned to the technician.
  3. Pre-initializes PreServiceVerification with a known customer OTP ('123456').
  4. Outputs exact step-by-step instructions with URLs, credentials, and walkthrough flow.
"""
import os
import sys
import uuid
from decimal import Decimal
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone as dj_timezone
from service_requests.models import ServiceRequest, RequestKind, Service, QUOTATION_SERVICE_IDS
from employees.models import Employee
from companies.models import Company
from workforce_api.models import PreServiceVerification, WorkforceQuote

User = get_user_model()

def setup_manual_scenario():
    print("=" * 70)
    print("CALTRACK WORKFORCE — MANUAL E2E TEST SCENARIO SETUP")
    print("=" * 70)

    # 1. Company
    company = Company.objects.first()
    if not company:
        company = Company.objects.create(
            company_name="CalTrack Premier Home Services",
            slug="caltrack-premier",
            is_active=True,
        )

    # 2. Customer User
    customer_user, _ = User.objects.get_or_create(
        username="vikram_malhotra",
        defaults={
            "email": "vikram.malhotra@example.com",
            "first_name": "Vikram",
            "last_name": "Malhotra",
        }
    )
    customer_user.set_password("Password123!")
    customer_user.save()

    # 3. Technician User & Employee Profile
    tech_user, created_user = User.objects.get_or_create(
        username="painter_pro",
        defaults={
            "email": "painter.pro@caltrack.example.com",
            "first_name": "Suresh",
            "last_name": "Painter",
            "is_active": True,
        }
    )
    tech_user.set_password("Password123!")
    tech_user.first_name = "Suresh"
    tech_user.last_name = "Painter"
    tech_user.is_active = True
    tech_user.save()

    employee, created_emp = Employee.objects.get_or_create(
        user=tech_user,
        defaults={
            "company": company,
            "employee_id": "TECH-PAINT-01",
            "phone": "+91 98765 43210",
            "is_active": True,
            "is_online": True,
            "current_availability": "online",
            "bank_details": {"onboarding": {"status": "approved"}},
        }
    )
    employee.is_active = True
    employee.is_online = True
    employee.current_availability = "online"
    employee.bank_details = {"onboarding": {"status": "approved"}}
    employee.save()

    # 4. Clean up any previous stale manual test jobs for this technician
    ServiceRequest.objects.filter(
        assigned_employee=employee,
        issue_title__icontains="[MANUAL E2E TEST]"
    ).delete()

    # 5. Create Real Estimation Booking
    unique_suffix = datetime.now(timezone.utc).strftime("%H%M%S")
    est_job = ServiceRequest.objects.create(
        customer=customer_user,
        company=company,
        customer_name="Mr. Vikram Malhotra",
        phone="+91 98765 43210",
        email=customer_user.email,
        service_category="Painting",
        issue_title=f"[MANUAL E2E TEST] Interior Painting & Waterproofing ({unique_suffix})",
        description="Customer requested on-site inspection for 3BHK interior walls, crack filling, and balcony waterproofing.",
        address="Flat 402, Sunshine Heights, 12th Main Road, Indiranagar, Bangalore - 560038",
        latitude=12.9716,
        longitude=77.5946,
        preferred_date=dj_timezone.now().date(),
        preferred_time="10:00 AM",
        request_kind=RequestKind.ESTIMATION,
        status="accepted",  # Accepted and ready for technician arrival on site
        assigned_employee=employee,
        start_otp="123456",
        total_amount=Decimal("299.00"),  # Inspection fee
        payment_method="COD",
        payment_status="PENDING",
    )

    # 6. Initialize PreServiceVerification
    psv, _ = PreServiceVerification.objects.get_or_create(
        job=est_job,
        defaults={
            "employee": employee,
            "geofence_passed": True,  # Pre-geofenced for seamless testing
            "otp_code": "123456",
            "otp_verified": False,
            "presence_photo": "",
            "work_area_photo": "",
            "is_complete": False,
        }
    )
    psv.geofence_passed = True
    psv.otp_code = "123456"
    psv.otp_verified = False
    psv.save()

    print("\n" + "=" * 70)
    print("MANUAL TEST SCENARIO PROVISIONED SUCCESSFULLY!")
    print("=" * 70)
    print(f"1. LOGIN CREDENTIALS:")
    print(f"   - Frontend URL : http://localhost:5176 (or http://127.0.0.1:5176)")
    print(f"   - Username     : painter_pro")
    print(f"   - Password     : Password123!")
    print(f"   - Role         : Approved Technician (Suresh Painter)")
    print()
    print(f"2. ESTIMATION JOB DETAILS:")
    print(f"   - Job ID       : SR-{est_job.id}")
    print(f"   - Title        : {est_job.issue_title}")
    print(f"   - Request Kind : ESTIMATION")
    print(f"   - Customer     : Mr. Vikram Malhotra (+91 98765 43210)")
    print(f"   - Customer OTP : 123456")
    print(f"   - Address      : {est_job.address}")
    print()
    print("=" * 70)
    print("STEP-BY-STEP MANUAL BROWSER TEST GUIDE:")
    print("=" * 70)
    print("STEP 1: Log In")
    print("  - Open http://localhost:5176/ in your browser.")
    print("  - Log in using `painter_pro` / `Password123!`.")
    print()
    print("STEP 2: View Active Estimation Job on Dashboard")
    print("  - On Home / Active Jobs, find the job card for `[MANUAL E2E TEST] Interior Painting`.")
    print("  - Notice the purple 'ESTIMATION REQUIRED' badge.")
    print("  - Click on the job card to open the Job Details view.")
    print()
    print("STEP 3: Arrive & Pre-Service Verification")
    print("  - Click 'Arrive on Site'.")
    print("  - In the Verification Card, enter Customer OTP: `123456` and click Verify.")
    print("  - Upload / Capture your Technician Presence Selfie.")
    print("  - Upload / Capture a Site Work Area Photo.")
    print("  - Notice the 'Quotation Unlocked' alert appears.")
    print()
    print("STEP 4: Create Quotation via Builder Modal")
    print("  - Click the 'Create Quotation' button.")
    print("  - Step 1 (Scope): Fill Property Type (e.g. 3BHK), Paint Grade (Asian Paints Royale), Surface Condition.")
    print("  - Step 2 (Measurements): Add Living Room (450 sqft) and Master Bedroom (320 sqft).")
    print("  - Step 3 (Line Items): Select rate cards (e.g. Luxury Emulsion @ INR 600, Labour @ INR 15,000, Prep @ INR 8,000).")
    print("  - Step 4 (Review & Send): Check the live breakdown (Subtotal INR 35,000, 18% GST INR 6,300, INR 299 inspection fee deduction = Net INR 41,001).")
    print("  - Click 'Send Quotation to Customer'.")
    print()
    print("STEP 5: Verify on Estimates Hub")
    print("  - In the sidebar, click 'Estimates' (or navigate to `/workforce/employee/estimates`).")
    print("  - Under the 'Sent' tab, verify your newly created quotation appears with status 'Sent to Customer'!")
    print("=" * 70)

if __name__ == "__main__":
    setup_manual_scenario()
