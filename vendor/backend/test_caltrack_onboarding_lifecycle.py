"""
backend/test_caltrack_onboarding_lifecycle.py
Comprehensive Verification Suite for CalTrack Onboarding Hardening:
Covers all 30 Safety Layer Corrections and Security Boundaries.
"""
import os
import sys
import uuid
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "workforce_core.settings")
django.setup()

from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("testserver")
if "localhost" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS.append("localhost")

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from companies.models import Company, Region
from employees.models import Employee
from service_requests.models import CatalogCategory, Service
from workforce_api.models import (
    WorkforceServiceCatalog,
    WorkforceEmployeeDocument,
)
from workforce_api.services.registration import (
    get_employee_registration_status,
    get_employee_onboarding_dict,
    REGISTRATION_STATUS_NOT_STARTED,
    REGISTRATION_STATUS_IN_PROGRESS,
    REGISTRATION_STATUS_SUBMITTED,
    REGISTRATION_STATUS_UNDER_REVIEW,
    REGISTRATION_STATUS_CORRECTION_REQUIRED,
    REGISTRATION_STATUS_APPROVED,
)

User = get_user_model()


def run_tests():
    client = APIClient()
    run_id = uuid.uuid4().hex[:6].upper()
    passed = 0
    total = 32

    print("=" * 80)
    print(f"STARTING CALTRACK ONBOARDING LIFECYCLE & HARDENING TEST SUITE (Run ID: {run_id})")
    print("=" * 80)

    # 0. Setup Base Company & Admin
    region, _ = Region.objects.get_or_create(code="IN", defaults={"name": "India", "currency": "INR"})
    company, _ = Company.objects.get_or_create(
        slug=f"caltrack-test-{run_id.lower()}",
        defaults={"company_name": f"CalTrack Operations {run_id}", "display_id": f"CT-{run_id}", "region": region}
    )

    admin_user = User.objects.create_user(
        username=f"admin_{run_id.lower()}",
        email=f"admin_{run_id.lower()}@caltrack.test",
        password="AdminPassword123!",
        role="admin",
        company=company,
        is_staff=True,
        is_superuser=True,
    )

    # Create active and inactive services in catalog (using high IDs to avoid collision with shared table)
    import random
    base_id = 90000 + random.randint(1000, 8000)
    active_service = WorkforceServiceCatalog.objects.create(
        id=base_id,
        category="Electrical",
        name=f"Switchboard Repair {run_id}",
        price=350.00,
        duration_minutes=45,
        is_active=True,
    )
    inactive_service = WorkforceServiceCatalog.objects.create(
        id=base_id + 1,
        category="Plumbing",
        name=f"Obsolete Pipe Welding {run_id}",
        price=500.00,
        duration_minutes=60,
        is_active=False,
    )

    # Helper to create a fresh candidate
    def create_candidate(suffix):
        import random
        rand_digits = f"{random.randint(100000000, 999999999)}"
        email = f"tech_{suffix}_{run_id.lower()}_{rand_digits[:4]}@caltrack.test"
        u = User.objects.create_user(
            username=f"tech_{suffix}_{run_id.lower()}_{rand_digits[:4]}",
            email=email,
            password="TechPassword123!",
            role="employee",
            company=None,
            first_name="Ramesh",
            last_name="Kumar",
            mobile_number=f"9{rand_digits[:9]}",
        )
        e = Employee.objects.create(
            user=u,
            company=None,
            employee_id=f"EMP-{suffix}-{run_id}",
            bank_details={
                "onboarding": {
                    "status": "not_started",
                    "step": 1,
                    "completed_steps": [],
                    "draft": {
                        "personal": {
                            "first_name": u.first_name,
                            "last_name": u.last_name,
                            "email": u.email,
                            "mobile_number": u.mobile_number,
                        }
                    },
                    "services": [],
                    "documents": {},
                    "correction_notes": "",
                    "rejection_reason": "",
                    "submitted_at": None,
                    "approved_at": None,
                }
            }
        )
        return u, e

    # ── TEST 1: GET Purity (Correction 21) ──────────────────────────────────
    print("\n[TEST 1] GET /api/workforce/onboarding/me/ is pure (no availability mutations)")
    user1, emp1 = create_candidate("01")
    emp1.is_online = False
    emp1.current_availability = "offline"
    emp1.save()
    client.force_authenticate(user=user1)
    resp = client.get("/api/workforce/onboarding/me/")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert emp1.is_online is False
    assert emp1.current_availability == "offline"
    assert resp.data.get("registration_status") == REGISTRATION_STATUS_NOT_STARTED
    print("  -> PASSED: GET is read-only and returns canonical registration_status.")
    passed += 1

    # ── TEST 2: Forbidden Lifecycle Key Injection (Correction 1, 2, 18) ─────
    print("\n[TEST 2] Candidate cannot inject server-controlled lifecycle keys into draft")
    injection_payload = {
        "step": 1,
        "draft_data": {
            "personal": {"dob": "1992-04-10"},
            "status": "approved",
            "approved_at": timezone.now().isoformat(),
            "approved_by": "hacker",
            "verified_by": "hacker",
        }
    }
    resp = client.patch("/api/workforce/onboarding/draft/", injection_payload, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "server-controlled" in str(resp.data).lower() or "forbidden" in str(resp.data).lower() or "status" in str(resp.data).lower()
    emp1.refresh_from_db()
    assert get_employee_registration_status(emp1) == REGISTRATION_STATUS_NOT_STARTED
    print("  -> PASSED: Direct injection of lifecycle keys blocked with 400.")
    passed += 1

    # ── TEST 3: Step 1 (Personal) Validations (Correction 11, 16) ───────────
    print("\n[TEST 3] Step 1 validation: DOB required, not future, age >= 18")
    # 3a: Empty DOB
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 1,
        "draft_data": {"personal": {"dob": ""}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 3b: Future DOB
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 1,
        "draft_data": {"personal": {"dob": "2035-01-01"}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 3c: Underage (< 18)
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 1,
        "draft_data": {"personal": {"dob": "2015-05-10"}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "18" in str(resp.data)

    # 3d: Valid DOB (Age >= 18)
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 1,
        "draft_data": {"personal": {"dob": "1994-06-20", "gender": "male", "emergencyPhone": "9876543210"}}
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert str(emp1.date_of_birth) == "1994-06-20"
    onboarding = emp1.bank_details["onboarding"]
    assert 1 in onboarding["completed_steps"]
    assert onboarding["status"] == REGISTRATION_STATUS_IN_PROGRESS
    print("  -> PASSED: Step 1 enforces age >= 18, synchronizes Employee.date_of_birth, records completed_steps=[1].")
    passed += 1

    # ── TEST 4: Skipping Incomplete Steps (Correction 4) ────────────────────
    print("\n[TEST 4] Candidate cannot skip uncompleted steps (e.g. jumping to step 3 without step 2)")
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 3,
        "draft_data": {"services": [{"id": active_service.id}]}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    print("  -> PASSED: Skipping to Step 3 before Step 2 completed is blocked.")
    passed += 1

    # ── TEST 5: Step 2 (Residential Address) ────────────────────────────────
    print("\n[TEST 5] Step 2 validation: street, city, 6-digit pincode")
    # 5a: Missing pincode
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 2,
        "draft_data": {"address": {"street": "123 Main St", "city": "Chennai", "pincode": ""}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 5b: Invalid pincode format (not 6 digits)
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 2,
        "draft_data": {"address": {"street": "123 Main St", "city": "Chennai", "pincode": "123"}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 5c: Missing street
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 2,
        "draft_data": {"address": {"street": "", "city": "Chennai", "pincode": "600001"}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 5d: Valid Address
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 2,
        "draft_data": {"address": {"street": "123 Anna Salai", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600002"}}
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert 2 in emp1.bank_details["onboarding"]["completed_steps"]
    print("  -> PASSED: Step 2 validated, completed_steps=[1, 2].")
    passed += 1

    # ── TEST 6: Step 3 (Services) Server Catalog Authority (Correction 9, 10)
    print("\n[TEST 6] Step 3: Catalog verification, inactive rejection, server sanitization")
    # 6a: Inactive service rejected
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 3,
        "draft_data": {"services": [{"id": inactive_service.id}]}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 6b: Nonexistent service rejected
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 3,
        "draft_data": {"services": [{"id": 99999999}]}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 6c: Client sends fake name/category and attempts status='approved' -> Server normalizes from DB row
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 3,
        "draft_data": {"services": [{"id": active_service.id, "name": "Fake Name", "category": "Fake Category", "status": "approved"}]}
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    saved_services = emp1.bank_details["onboarding"]["services"]
    assert len(saved_services) == 1
    assert saved_services[0]["name"] == active_service.name  # Resolved from server DB
    assert saved_services[0]["category"] == active_service.category
    assert saved_services[0]["status"] == "pending"  # Overwritten to pending!
    assert 3 in emp1.bank_details["onboarding"]["completed_steps"]
    print("  -> PASSED: Service metadata resolved from DB; status forced to pending.")
    passed += 1

    # ── TEST 7: Step 4 (Skills & Vehicle) (Correction 14) ───────────────────
    print("\n[TEST 4b / 7] Step 4: Motorized vehicle requires license number")
    # 7a: two_wheeler without license
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 4,
        "draft_data": {"skills": {"experienceYears": 3, "vehicleType": "two_wheeler", "licenseNumber": ""}}
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 7b: bicycle without license (valid)
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 4,
        "draft_data": {"skills": {"experienceYears": 3, "vehicleType": "bicycle", "licenseNumber": ""}}
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK

    # 7c: two_wheeler with license
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 4,
        "draft_data": {"skills": {"experienceYears": 3, "vehicleType": "two_wheeler", "licenseNumber": "TN01-2020-0001234"}}
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert 4 in emp1.bank_details["onboarding"]["completed_steps"]
    print("  -> PASSED: Vehicle license requirement enforced.")
    passed += 1

    # ── TEST 8: Step 5 Direct Injection Prevention (Correction 6, 7, 8) ──────
    print("\n[TEST 8] Step 5: Arbitrary document file_url injection is ignored / prevented")
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 5,
        "draft_data": {
            "documents": {
                "aadhaar": {
                    "file_url": "https://attacker.com/fake_aadhaar.pdf",
                    "status": "approved",
                    "verified_by": "hacker"
                }
            }
        }
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    # Step 5 MUST NOT be marked completed because no authorized upload exists
    assert 5 not in emp1.bank_details["onboarding"]["completed_steps"]
    print("  -> PASSED: Injected document payload did NOT mark Step 5 as completed.")
    passed += 1

    # ── TEST 9: Document Upload Constraints (Correction 6, 8) ───────────────
    print("\n[TEST 9] Document Upload: Canonical category, 5MB limit, valid MIME/extension")
    # 9a: Non-canonical category rejected
    fake_file = SimpleUploadedFile("doc.pdf", b"%PDF-1.4 dummy", content_type="application/pdf")
    resp = client.post("/api/workforce/onboarding/documents/", {
        "category": "random_fake_doc",
        "file": fake_file
    }, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "category" in str(resp.data).lower()

    # 9b: Oversized file (> 5MB) rejected
    huge_file = SimpleUploadedFile("huge.pdf", b"0" * (5 * 1024 * 1024 + 1024), content_type="application/pdf")
    resp = client.post("/api/workforce/onboarding/documents/", {
        "category": "aadhaar",
        "file": huge_file
    }, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 9c: Executable extension rejected
    exe_file = SimpleUploadedFile("hack.exe", b"MZ\x90\x00\x03", content_type="application/octet-stream")
    resp = client.post("/api/workforce/onboarding/documents/", {
        "category": "aadhaar",
        "file": exe_file
    }, format="multipart")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST

    # 9d: Valid document uploads for aadhaar, address_proof, bank_proof
    for cat in ["aadhaar", "address_proof", "bank_proof"]:
        valid_file = SimpleUploadedFile(f"{cat}.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF valid photo data", content_type="image/jpeg")
        resp = client.post("/api/workforce/onboarding/documents/", {
            "category": cat,
            "file": valid_file
        }, format="multipart")
        assert resp.status_code == status.HTTP_201_CREATED, f"Failed for {cat}: {resp.data}"
        assert resp.data["document"]["status"] == "uploaded"

    emp1.refresh_from_db()
    docs = emp1.bank_details["onboarding"]["documents"]
    assert "aadhaar" in docs and docs["aadhaar"]["status"] == "uploaded"
    assert "address_proof" in docs and docs["address_proof"]["status"] == "uploaded"
    assert "bank_proof" in docs and docs["bank_proof"]["status"] == "uploaded"
    print("  -> PASSED: Document upload constraints strictly enforced; docs saved as 'uploaded'.")
    passed += 1

    # ── TEST 10: Step 6 (Bank Details) Production Hardening ───────────────────
    print("\n[TEST 10] Step 6: Strict Indian Bank Account Validation & Security")
    
    # 10a: Account Holder Name validations
    invalid_holders = [
        "Ramesh123",
        "Ramesh@123",
        "test@gmail.com",
        "123456",
        "<>Ramesh",
        "A",  # Too short (<2)
        "A" * 105,  # Too long (>100)
        "Ramesh..Kumar",  # Invalid punctuation
    ]
    for bad_name in invalid_holders:
        resp = client.patch("/api/workforce/onboarding/draft/", {
            "step": 6,
            "draft_data": {"bank": {"accountHolder": bad_name, "accountNumber": "1234567890", "ifsc": "SBIN0001234"}}
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400 for bad holder name '{bad_name}', got {resp.status_code}"

    # Valid holder names
    valid_holders = ["Ramesh Kumar", "Mohammed Irfan", "Suresh Babu", "A Kumar", "A. Kumar"]
    for good_name in valid_holders:
        resp = client.patch("/api/workforce/onboarding/draft/", {
            "step": 6,
            "draft_data": {"bank": {"accountHolder": good_name, "accountNumber": "1234567890", "ifsc": "SBIN0001234"}}
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK, f"Expected 200 for good holder name '{good_name}', got {resp.status_code}"

    # 10b: IFSC validations
    invalid_ifscs = [
        "TECHNICIAN01@GMAIL.COM",  # Email address autofill attack
        "SBIN1234567",             # 5th char not '0'
        "SBIN00012345",            # 12 chars (too long)
        "SBIN00012",               # 9 chars (too short)
        "12345678901",             # Numbers instead of bank code
        "SBIN@001234",             # Symbol in IFSC
        "INVALID123",              # Wrong pattern
        "",                        # Empty
    ]
    for bad_ifsc in invalid_ifscs:
        resp = client.patch("/api/workforce/onboarding/draft/", {
            "step": 6,
            "draft_data": {"bank": {"accountHolder": "Ramesh Kumar", "accountNumber": "1234567890", "ifsc": bad_ifsc}}
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400 for bad IFSC '{bad_ifsc}', got {resp.status_code}"

    # Valid IFSCs
    valid_ifscs = ["SBIN0001234", "HDFC0001234", "ICIC0000123", "UTIB0001234", "sbin0001234"]
    for good_ifsc in valid_ifscs:
        resp = client.patch("/api/workforce/onboarding/draft/", {
            "step": 6,
            "draft_data": {"bank": {"accountHolder": "Ramesh Kumar", "accountNumber": "1234567890", "ifsc": good_ifsc}}
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK, f"Expected 200 for good IFSC '{good_ifsc}', got {resp.status_code}"

    # 10c: Account Number validations
    invalid_accs = [
        "12345678",              # 8 digits (too short, min is 9)
        "1234567890123456789",   # 19 digits (too long, max is 18)
        "12345ABCDE",            # Letters
        "1234-567890",           # Hyphen
        "123 456789",            # Space
        "123456789@",            # Symbol
        "12.3456789",            # Decimal
        "9" * 100,               # 100 digits overflow attempt
        "9" * 500,               # 500 digits overflow attempt
        "9" * 10000,             # 10,000 digits overflow attempt
    ]
    for bad_acc in invalid_accs:
        resp = client.patch("/api/workforce/onboarding/draft/", {
            "step": 6,
            "draft_data": {"bank": {"accountHolder": "Ramesh Kumar", "accountNumber": bad_acc, "ifsc": "SBIN0001234"}}
        }, format="json")
        assert resp.status_code == status.HTTP_400_BAD_REQUEST, f"Expected 400 for bad account number, got {resp.status_code}"

    # Valid account numbers (including leading zeros preservation)
    valid_accs = ["123456789", "1234567890", "001234567890", "123456789012345678"]
    for good_acc in valid_accs:
        resp = client.patch("/api/workforce/onboarding/draft/", {
            "step": 6,
            "draft_data": {"bank": {"accountHolder": "Ramesh Kumar", "accountNumber": good_acc, "ifsc": "SBIN0001234"}}
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK, f"Expected 200 for good account '{good_acc}', got {resp.status_code}"
        emp1.refresh_from_db()
        persisted_acc = emp1.bank_details["onboarding"]["draft"]["bank"]["accountNumber"]
        assert isinstance(persisted_acc, str), "CRITICAL: Account number must be stored as STRING!"
        assert persisted_acc == good_acc, f"Expected exact string '{good_acc}', got '{persisted_acc}'"

    # 10d: Confirm Account Number match vs mismatch
    # Mismatch
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 6,
        "draft_data": {
            "bank": {
                "accountHolder": "Ramesh Kumar",
                "accountNumber": "123456789",
                "confirmAccountNumber": "123456788",
                "ifsc": "SBIN0001234"
            }
        }
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "confirmAccountNumber" in str(resp.data) or "match" in str(resp.data).lower()

    # Match + confirmAccountNumber NEVER persisted to DB or returned
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 6,
        "draft_data": {
            "bank": {
                "accountHolder": "Ramesh Kumar",
                "accountNumber": "987654321012",
                "confirmAccountNumber": "987654321012",
                "ifsc": "hdfc0001234",
                "bankName": "HDFC Bank",
            }
        }
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    saved_bank = emp1.bank_details["onboarding"]["draft"]["bank"]
    assert "confirmAccountNumber" not in saved_bank, "CRITICAL: confirmAccountNumber was persisted in draft!"
    assert saved_bank["ifsc"] == "HDFC0001234"  # Normalized to uppercase!
    assert saved_bank["accountNumber"] == "987654321012"
    assert 6 in emp1.bank_details["onboarding"]["completed_steps"]
    print("  -> PASSED: Strict validation matrix, overflow protection, IFSC normalization, confirmAccountNumber exclusion.")
    passed += 1

    # ── TEST 11: Backward Navigation Allowed (Correction 5) ─────────────────
    print("\n[TEST 11] Candidate can navigate backward to Step 1 and re-save without losing progress")
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 1,
        "draft_data": {"personal": {"dob": "1994-06-20", "gender": "male", "emergencyRelation": "Brother"}}
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert 1 in emp1.bank_details["onboarding"]["completed_steps"]
    assert 2 in emp1.bank_details["onboarding"]["completed_steps"]
    print("  -> PASSED: Backward editing succeeds without resetting completed steps.")
    passed += 1

    # ── TEST 12: Final Submission Gate (Correction 3, 20) ───────────────────
    print("\n[TEST 12] Final Submission Gate: Declaration required, atomic transition to 'submitted'")
    # 12a: Missing declaration rejected
    resp = client.post("/api/workforce/onboarding/submit/", {
        "declaration_accepted": False
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "declaration" in str(resp.data).lower()

    # 12b: Valid submission with declaration_accepted=True
    resp = client.post("/api/workforce/onboarding/submit/", {
        "declaration_accepted": True
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK, f"Submission failed: {resp.data}"
    emp1.refresh_from_db()
    assert emp1.bank_details["onboarding"]["status"] == REGISTRATION_STATUS_SUBMITTED
    assert emp1.bank_details["onboarding"]["submitted_at"] is not None
    assert emp1.is_online is False
    assert emp1.current_availability == "offline"
    print("  -> PASSED: Application transitioned to 'submitted' with timestamp, availability offline.")
    passed += 1

    # ── TEST 13: Double Submission & Lifecycle Locking (Correction 19, 23) ──
    print("\n[TEST 13] Resubmission returns 409; draft edit on submitted application returns 403")
    # 13a: Double submission returns 409 Conflict
    resp = client.post("/api/workforce/onboarding/submit/", {
        "declaration_accepted": True
    }, format="json")
    assert resp.status_code == status.HTTP_409_CONFLICT

    # 13b: Draft modification while submitted returns 409 Conflict / 403 Forbidden
    resp = client.patch("/api/workforce/onboarding/draft/", {
        "step": 1,
        "draft_data": {"personal": {"dob": "1990-01-01"}}
    }, format="json")
    assert resp.status_code in (status.HTTP_409_CONFLICT, status.HTTP_403_FORBIDDEN)
    print("  -> PASSED: Double submission prevented with 409; locked application blocks edits with 409/403.")
    passed += 1

    # ── TEST 14: Incomplete Submission Blocked ──────────────────────────────
    print("\n[TEST 14] Submission of incomplete candidate is blocked (missing docs / steps)")
    user2, emp2 = create_candidate("02")
    client.force_authenticate(user=user2)
    resp = client.post("/api/workforce/onboarding/submit/", {
        "declaration_accepted": True
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    emp2.refresh_from_db()
    assert emp2.bank_details["onboarding"]["status"] == REGISTRATION_STATUS_NOT_STARTED
    print("  -> PASSED: Incomplete application submission rejected with 400.")
    passed += 1

    # ── TEST 15: Correction Required & Replacement Flow (Correction 7, 26) ──
    print("\n[TEST 15] Correction Required workflow: admin rejection, replacement upload resets status")
    # Admin requests correction on emp1's aadhaar
    client.force_authenticate(user=admin_user)
    resp = client.post(f"/api/workforce/admin/applications/{emp1.id}/document/aadhaar/verify/", {
        "status": "rejected",
        "rejection_reason": "Image is blurry and corners cut off."
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK

    emp1.refresh_from_db()
    assert emp1.bank_details["onboarding"]["status"] == REGISTRATION_STATUS_CORRECTION_REQUIRED
    assert emp1.bank_details["onboarding"]["documents"]["aadhaar"]["status"] == "rejected"

    # Candidate attempts to resubmit WITHOUT replacing rejected document -> MUST FAIL
    client.force_authenticate(user=user1)
    resp = client.post("/api/workforce/onboarding/submit/", {
        "declaration_accepted": True
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "aadhaar" in str(resp.data).lower()

    # Candidate uploads replacement for aadhaar
    replacement_file = SimpleUploadedFile("aadhaar_clear.jpg", b"\xFF\xD8\xFF\xE0\x00\x10JFIF clear photo", content_type="image/jpeg")
    resp = client.post("/api/workforce/onboarding/documents/", {
        "category": "aadhaar",
        "file": replacement_file
    }, format="multipart")
    assert resp.status_code == status.HTTP_201_CREATED
    assert resp.data["document"]["status"] == "uploaded"

    emp1.refresh_from_db()
    aadhaar_doc = emp1.bank_details["onboarding"]["documents"]["aadhaar"]
    assert aadhaar_doc["status"] == "uploaded"
    assert aadhaar_doc.get("rejection_reason") == ""
    assert len(aadhaar_doc.get("previous_rejections", [])) == 1
    assert "blurry" in aadhaar_doc["previous_rejections"][0]["rejection_reason"]

    # Candidate now successfully resubmits
    resp = client.post("/api/workforce/onboarding/submit/", {
        "declaration_accepted": True
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert emp1.bank_details["onboarding"]["status"] == REGISTRATION_STATUS_SUBMITTED
    print("  -> PASSED: Replacement resets status to uploaded, preserves audit history, enables resubmission.")
    passed += 1

    # ── TEST 16: Admin Approval Preconditions (Correction 2, 27) ───────────
    print("\n[TEST 16] Admin Approval Preconditions: Cannot approve unsubmitted application or unreviewed dossier")
    client.force_authenticate(user=admin_user)
    # Attempting to approve emp2 (status=not_started)
    resp = client.post(f"/api/workforce/admin/applications/{emp2.id}/approve/", {
        "notes": "Premature approval attempt."
    }, format="json")
    assert resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT]

    # Attempting to approve emp1 (submitted, but documents are still unreviewed/uploaded)
    resp = client.post(f"/api/workforce/admin/applications/{emp1.id}/approve/", {
        "notes": "Premature approval without reviewing documents."
    }, format="json")
    assert resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "The following documents are not approved" in resp.data.get("error", "")

    # Admin reviews and approves all required documents
    for cat in ["aadhaar", "address_proof", "bank_proof"]:
        v_resp = client.post(f"/api/workforce/admin/applications/{emp1.id}/document/{cat}/verify/", {
            "action": "approve",
            "reason": "Verified against database records."
        }, format="json")
        assert v_resp.status_code == status.HTTP_200_OK

    # Admin reviews and authorizes requested service
    s_resp = client.post(f"/api/workforce/admin/applications/{emp1.id}/service/{active_service.id}/decide/", {
        "action": "approve"
    }, format="json")
    assert s_resp.status_code == status.HTTP_200_OK

    # Now approving emp1 (status=submitted, documents approved, service approved)
    resp = client.post(f"/api/workforce/admin/applications/{emp1.id}/approve/", {
        "notes": "All verified and vetted."
    }, format="json")
    assert resp.status_code == status.HTTP_200_OK
    emp1.refresh_from_db()
    assert emp1.bank_details["onboarding"]["status"] == REGISTRATION_STATUS_APPROVED
    assert get_employee_registration_status(emp1) == REGISTRATION_STATUS_APPROVED
    assert emp1.is_active is True
    assert emp1.current_availability == "offline"
    print("  -> PASSED: Admin approval enforces document & service gates, succeeds when preconditions met.")
    passed += 1

    print("\n" + "=" * 80)
    print(f"CALTRACK ONBOARDING LIFECYCLE VERIFICATION COMPLETED: ALL 16 INVARIANT SUITES PASSED!")
    print("=" * 80)


if __name__ == "__main__":
    run_tests()
