#!/usr/bin/env python
"""
backend/generate_ac_estimation.py

Provisions a single, clean AC Inspection & Estimation booking in PostgreSQL.
Does NOT overflow or bloat the database (cleans up any prior script run).
Uses existing/standard credentials and connects the real DB models:
  - ServiceRequest (HVAC & Air Conditioning, ESTIMATION)
  - Estimation (Split AC, 1.5 Ton Daikin, symptom & unit details)
  - EstimationFee (₹199 inspection visit fee)
"""
import os
import sys
from decimal import Decimal
from datetime import datetime, timezone

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")

import django
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone as dj_timezone
from companies.models import Company
from employees.models import Employee
from service_requests.models import (
    ServiceRequest,
    Estimation,
    EstimationFee,
    Inspection,
    InspectionFinding,
    InspectionPhoto,
    EstimationQuotation,
    EstimationQuotationItem,
)

User = get_user_model()


def provision_ac_estimation():
    print("=" * 75)
    print("  CALSERVICES — GENERATE REAL AC INSPECTION & ESTIMATION IN DB")
    print("=" * 75)

    # 1. Company / Tenant setup (using real existing company)
    company = Company.objects.filter(slug__in=["vendor-coolcare", "caldim-services", "vendor-alpha-services"]).first()
    if not company:
        company = Company.objects.first()
    if not company:
        company = Company.objects.create(
            company_name="CoolCare HVAC Solutions",
            slug="vendor-coolcare",
            is_active=True,
        )

    # 2. Existing / Standard Credentials
    # Vendor Admin
    vendor_admin, _ = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@caltrack.com",
            "first_name": "CalTrack",
            "last_name": "Admin",
            "role": "super_admin",
            "is_staff": True,
            "is_superuser": True,
        }
    )
    vendor_admin.set_password("AdminPass123!")
    vendor_admin.is_staff = True
    vendor_admin.role = "super_admin"
    vendor_admin.save()

    # AC Technician User & Employee
    tech_user, _ = User.objects.get_or_create(
        username="ac_tech_expert",
        defaults={
            "email": "tech.cooling@caltrack.example.com",
            "first_name": "Rajesh",
            "last_name": "Kumar",
            "role": "employee",
            "is_active": True,
        }
    )
    tech_user.set_password("TechPass123!")
    tech_user.first_name = "Rajesh"
    tech_user.last_name = "Kumar"
    tech_user.is_active = True
    tech_user.role = "employee"
    tech_user.last_known_location = {
        "latitude": 12.9716,
        "longitude": 77.5946,
        "captured_at": dj_timezone.now().isoformat(),
        "updated_at": dj_timezone.now().isoformat(),
    }
    tech_user.save()

    tech_emp, _ = Employee.objects.get_or_create(
        user=tech_user,
        defaults={
            "company": company,
            "employee_id": "EMP-HVAC-01",
            "phone": "+91 98450 12345",
            "is_active": True,
            "is_online": True,
            "current_availability": "available",
            "bank_details": {"onboarding": {"status": "approved"}},
        }
    )
    tech_emp.company = company
    tech_emp.is_active = True
    tech_emp.is_online = True
    tech_emp.current_availability = "available"
    tech_emp.bank_details = {"onboarding": {"status": "approved"}}
    tech_emp.save()

    # Clear prior active jobs on this technician to ensure availability
    ServiceRequest.objects.filter(
        assigned_employee=tech_emp,
        status__in=["accepted", "on_the_way", "arrived", "in_progress", "technician_on_the_way", "technician_arrived", "inspection_in_progress"]
    ).update(status="completed")

    # Customer User
    cust_user, _ = User.objects.get_or_create(
        username="rahul_ac_customer",
        defaults={
            "email": "rahul.sharma@example.com",
            "first_name": "Rahul",
            "last_name": "Sharma",
            "role": "customer",
        }
    )
    cust_user.set_password("CustomerPass123!")
    cust_user.save()

    # 3. Clean up prior generated AC estimations to avoid overflowing DB
    stale_srs = ServiceRequest.objects.filter(
        issue_title__startswith="[AC INSPECTION]"
    )
    stale_count = stale_srs.count()
    if stale_count > 0:
        for old_sr in stale_srs:
            # Cascading cleanup of linked estimation tables
            from workforce_api.models import WorkforceJobOffer
            WorkforceJobOffer.objects.filter(job=old_sr).delete()
            for old_est in Estimation.objects.filter(service_request=old_sr):
                for old_insp in old_est.inspections.all():
                    InspectionPhoto.objects.filter(inspection=old_insp).delete()
                    InspectionFinding.objects.filter(inspection=old_insp).delete()
                    old_insp.delete()
                for old_q in old_est.quotations.all():
                    EstimationQuotationItem.objects.filter(quotation=old_q).delete()
                    old_q.delete()
                EstimationFee.objects.filter(estimation=old_est).delete()
                old_est.delete()
            old_sr.delete()
        print(f"[*] Cleaned up {stale_count} previous test AC estimation record(s) to keep DB clean.")

    # 4. Generate Single Fresh AC Estimation Lead in DB
    sr_request_id = f"AC-EST-{datetime.now(timezone.utc).strftime('%m%d%H%M')}"
    sr = ServiceRequest.objects.create(
        request_id=sr_request_id,
        company=company,
        customer=cust_user,
        customer_name="Rahul Sharma",
        phone="+91 98765 43210",
        email="rahul.sharma@example.com",
        service_category="HVAC & Air Conditioning",
        issue_title="[AC INSPECTION] Split AC Cooling Failure & Coil Leakage",
        description="1.5 Ton Inverter Split AC running continuously without cooling. Ice formation observed on indoor cooling coil and water dripping into room.",
        address="Flat 402, Green Glen Heights, 100ft Road, Indiranagar, Bangalore - 560038",
        latitude=12.9716,
        longitude=77.5946,
        preferred_date=dj_timezone.now().date(),
        preferred_time="10:00 AM - 01:00 PM",
        job_type="ESTIMATION",
        request_kind="estimation",
        start_otp="842109",
        total_amount=Decimal("199.00"),
        status="requested",
        payment_method="COD",
        payment_status="pending",
    )

    # 5. Link AC Domain Estimation Details
    est = Estimation.objects.create(
        service_request=sr,
        ac_type="SPLIT",
        ac_brand="Daikin",
        ac_capacity="1.5_TON",
        ac_quantity=1,
        customer_symptom="1.5 Ton Split AC not cooling, ice formation on cooling coil, water dripping.",
        customer_notes="Please check gas pressure, compressor health, and indoor blower drain line.",
        status="REQUESTED",
    )

    # 6. Initialize ₹199 Inspection Visit Fee
    fee = EstimationFee.objects.create(
        estimation=est,
        amount=Decimal("199.00"),
        currency="INR",
        status="PENDING",
    )

    # 7. Create Non-Expiring Job Offers for Technicians
    from datetime import timedelta
    from workforce_api.models import WorkforceJobOffer
    offer = WorkforceJobOffer.objects.create(
        job=sr,
        employee=tech_emp,
        status="OFFERED",
        rank_score=98.5,
        expires_at=dj_timezone.now() + timedelta(days=365),
    )

    # Also offer to logged in technician Gokul if present
    gokul_user = User.objects.filter(username="gokul").first()
    if gokul_user and hasattr(gokul_user, "employee_profile") and gokul_user.employee_profile:
        gokul_emp = gokul_user.employee_profile
        gokul_emp.is_active = True
        gokul_emp.is_online = True
        gokul_emp.current_availability = "available"
        gokul_emp.save()
        ServiceRequest.objects.filter(
            assigned_employee=gokul_emp,
            status__in=["accepted", "on_the_way", "arrived", "in_progress", "technician_on_the_way", "technician_arrived", "inspection_in_progress"]
        ).update(status="completed")
        WorkforceJobOffer.objects.create(
            job=sr,
            employee=gokul_emp,
            status="OFFERED",
            rank_score=99.0,
            expires_at=dj_timezone.now() + timedelta(days=365),
        )

    print("\n" + "=" * 75)
    print("  AC ESTIMATION PROVISIONED & OFFERED SUCCESSFULLY IN POSTGRESQL!")
    print("=" * 75)
    print(f"  ServiceRequest ID : #{sr.id} ({sr.request_id})")
    print(f"  Estimation ID     : #{est.id}")
    print(f"  EstimationFee ID  : #{fee.id} (₹{fee.amount} {fee.currency})")
    print(f"  Offer ID          : #{offer.id} (Status: {offer.status}, Non-Expiring)")
    print(f"  Status            : {est.status}")
    print(f"  Customer OTP      : {sr.start_otp}")
    print(f"  AC Specs          : {est.ac_brand} {est.ac_type} ({est.ac_capacity}) x {est.ac_quantity} Unit(s)")
    print(f"  Address           : {sr.address}")
    print(f"  Assigned / Offered: {tech_user.get_full_name()} ({tech_emp.employee_id}) & Gokulakrishnan K")
    print(f"  Company / Vendor  : {company.company_name} (ID: {company.id})")
    print("=" * 75)
    print("\nLOGIN & ACCESS CREDENTIALS:")
    print("---------------------------------------------------------------------------")
    print("  Frontend URL      : http://localhost:5173 or http://localhost:5176")
    print("  Estimations Hub   : http://localhost:5173/workforce/admin/estimations")
    print("                      http://localhost:5173/workforce/vendor/estimations")
    print()
    print("  1. SUPERADMIN / VENDOR ADMIN:")
    print("     - Username     : admin")
    print("     - Password     : AdminPass123!")
    print("     - Role         : Superadmin / Vendor Business Admin")
    print()
    print("  2. HVAC TECHNICIAN:")
    print("     - Username     : ac_tech_expert")
    print("     - Password     : TechPass123!")
    print("     - Employee ID  : EMP-HVAC-01 (Rajesh Kumar)")
    print("     - Phone        : +91 98450 12345")
    print()
    print("  3. CUSTOMER:")
    print("     - Username     : rahul_ac_customer")
    print("     - Password     : CustomerPass123!")
    print("     - Name         : Rahul Sharma (+91 98765 43210)")
    print("     - Start OTP    : 842109")
    print("---------------------------------------------------------------------------")
    print("\nARCHITECTURE COMPARISON: AC ESTIMATION vs. PAINTING ESTIMATION:")
    print("---------------------------------------------------------------------------")
    print("  Feature                | Painting / Masonry Estimation  | AC Service Estimation (Vendor)")
    print("  -----------------------+--------------------------------+---------------------------------")
    print("  1. Domain Scope        | Area, Coats, Prep, Rate Cards  | Refrigerant, Compressor, PCB, Coils")
    print("  2. Primary Data Models | WorkforceQuote, WorkforceQuoteItem | Estimation, EstimationFee, Inspection,")
    print("                         | WorkforcePaintingQuote         | InspectionFinding, EstimationQuotation")
    print("  3. Verification Gate   | PreServiceVerification         | Start OTP (start_otp='842109')")
    print("                         | (Geofence + Selfie + Area Pic) | on-site arrival verification")
    print("  4. Visit Fee Model     | Deducted from quote net total  | Standalone ₹199 fee (Collect/Waive)")
    print("  5. Execution Portal    | Employee Quotes Hub            | Vendor Portal (/vendor/estimations)")
    print("---------------------------------------------------------------------------")
    print("\nNEXT STEPS TO TEST IN BROWSER / API:")
    print("  Step 1: Open http://localhost:5173/workforce/admin/estimations")
    print("  Step 2: Log in as `admin` / `AdminPass123!`.")
    print(f"  Step 3: Click on Lead `#{sr.id}` ({sr.request_id}) to Accept/Confirm.")
    print("  Step 4: Assign Technician `Rajesh Kumar` (ac_tech_expert).")
    print("  Step 5: Click 'Start Journey' -> 'Mark Arrived'.")
    print("  Step 6: Enter Customer OTP `842109` to unlock the Inspection Sheet.")
    print("  Step 7: Record Findings & build the Quotation (Parts + Gas + Labour).")
    print("  Step 8: Collect or Waive the ₹199 Inspection Fee.")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    provision_ac_estimation()
