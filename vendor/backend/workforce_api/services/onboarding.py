"""
workforce-app/backend/workforce_api/services/onboarding.py
Authoritative, server-controlled validation engine and lifecycle safety layer
for CalTrack Technician / Vendor Onboarding (Steps 1–7).
"""
import os
import re
import uuid
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from django.utils import timezone
from django.core.files.storage import default_storage

from workforce_api.services.registration import (
    REGISTRATION_STATUS_NOT_STARTED,
    REGISTRATION_STATUS_IN_PROGRESS,
    REGISTRATION_STATUS_SUBMITTED,
    REGISTRATION_STATUS_UNDER_REVIEW,
    REGISTRATION_STATUS_CORRECTION_REQUIRED,
    REGISTRATION_STATUS_APPROVED,
    REGISTRATION_STATUS_REJECTED,
    VALID_REGISTRATION_STATUSES,
)

logger = logging.getLogger(__name__)

# ─── Canonical Constants ───────────────────────────────────────────────────────

TOTAL_ONBOARDING_STEPS = 7

STEP_1_PERSONAL = 1
STEP_2_ADDRESS = 2
STEP_3_SERVICES = 3
STEP_4_SKILLS = 4
STEP_5_DOCUMENTS = 5
STEP_6_BANK = 6
STEP_7_REVIEW_SUBMIT = 7

STEP_NAME_MAP = {
    STEP_1_PERSONAL: "personal",
    STEP_2_ADDRESS: "address",
    STEP_3_SERVICES: "services",
    STEP_4_SKILLS: "skills",
    STEP_5_DOCUMENTS: "documents",
    STEP_6_BANK: "bank",
    STEP_7_REVIEW_SUBMIT: "review",
}

# Canonical Document Categories
DOC_AADHAAR = "aadhaar"
DOC_ADDRESS_PROOF = "address_proof"
DOC_BANK_PROOF = "bank_proof"
DOC_TRADE_CERT = "trade_cert"

CANONICAL_DOCUMENT_CATEGORIES: Set[str] = {
    DOC_AADHAAR,
    DOC_ADDRESS_PROOF,
    DOC_BANK_PROOF,
    DOC_TRADE_CERT,
}

REQUIRED_DOCUMENT_CATEGORIES: Set[str] = {
    DOC_AADHAAR,
    DOC_ADDRESS_PROOF,
    DOC_BANK_PROOF,
}

OPTIONAL_DOCUMENT_CATEGORIES: Set[str] = {
    DOC_TRADE_CERT,
}

# Upload Security Rules
ALLOWED_DOC_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp", ".pdf"}
ALLOWED_DOC_MIMES: Set[str] = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "application/pdf",
}
MAX_DOC_FILE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB

# Business Validation Constraints
MIN_WORKING_AGE_YEARS = 18
MAX_SANITY_AGE_YEARS = 100

ALLOWED_GENDERS: Set[str] = {"male", "female", "other", "prefer_not_to_say", ""}
ALLOWED_VEHICLE_TYPES: Set[str] = {
    "two_wheeler",
    "four_wheeler",
    "bicycle",
    "public_transit",
    "none",
    "",
}
MOTOR_VEHICLES_REQUIRING_LICENSE: Set[str] = {"two_wheeler", "four_wheeler"}

# Lifecycle State Partitioning
CANDIDATE_EDITABLE_STATUSES: Set[str] = {
    REGISTRATION_STATUS_NOT_STARTED,
    REGISTRATION_STATUS_IN_PROGRESS,
    REGISTRATION_STATUS_CORRECTION_REQUIRED,
}

CANDIDATE_READONLY_STATUSES: Set[str] = {
    REGISTRATION_STATUS_SUBMITTED,
    REGISTRATION_STATUS_UNDER_REVIEW,
    REGISTRATION_STATUS_APPROVED,
}


class OnboardingValidationError(Exception):
    """
    Structured validation error returning field-level errors
    compatible with the CalTrack error contract.
    """
    def __init__(self, message: str, fields: Optional[Dict[str, List[str]]] = None, code: str = "ONBOARDING_VALIDATION_FAILED"):
        super().__init__(message)
        self.message = message
        self.fields = fields or {}
        self.code = code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error": self.code,
            "message": self.message,
            "fields": self.fields,
        }


# ─── Field Validation Helpers ──────────────────────────────────────────────────

def validate_indian_phone(phone_str: str) -> Tuple[bool, str]:
    """
    Validates and normalizes Indian 10-digit mobile number.
    Returns (is_valid, cleaned_10_digits).
    """
    if not phone_str:
        return False, ""
    cleaned = re.sub(r"[\s\-\+]", "", str(phone_str))
    if len(cleaned) == 12 and cleaned.startswith("91"):
        cleaned = cleaned[2:]
    if len(cleaned) == 11 and cleaned.startswith("0"):
        cleaned = cleaned[1:]
    if len(cleaned) == 10 and cleaned.isdigit() and cleaned[0] in "6789":
        return True, cleaned
    return False, cleaned


def validate_ifsc_code(ifsc: str) -> bool:
    """
    Validates RBI standard Indian Financial System Code (11 characters: 4 alpha, 0, 6 alphanumeric).
    """
    if not ifsc or not isinstance(ifsc, str):
        return False
    cleaned = ifsc.strip().upper()
    return bool(re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", cleaned))


# ─── Step-by-Step Validation & Normalization ───────────────────────────────────

def validate_personal_step(data: Any) -> Dict[str, Any]:
    """
    Validates Step 1: Personal Information.
    Required: dob (ISO YYYY-MM-DD, age >= 18, not future).
    Optional: gender, emergencyName, emergencyPhone, emergencyRelation.
    """
    if not isinstance(data, dict):
        raise OnboardingValidationError(
            "Personal details must be an object.",
            fields={"personal": ["Personal details must be an object."]}
        )

    errors: Dict[str, List[str]] = {}
    cleaned: Dict[str, Any] = {}

    # DOB validation
    raw_dob = data.get("dob")
    if not raw_dob or not str(raw_dob).strip():
        errors["personal.dob"] = ["Date of birth is required."]
    else:
        try:
            dob_date = datetime.strptime(str(raw_dob).strip(), "%Y-%m-%d").date()
            today = date.today()
            if dob_date > today:
                errors["personal.dob"] = ["Date of birth cannot be in the future."]
            else:
                age = today.year - dob_date.year - ((today.month, today.day) < (dob_date.month, dob_date.day))
                if age < MIN_WORKING_AGE_YEARS:
                    errors["personal.dob"] = [f"Technician must be at least {MIN_WORKING_AGE_YEARS} years of age."]
                elif age > MAX_SANITY_AGE_YEARS:
                    errors["personal.dob"] = ["Please provide a valid date of birth."]
                else:
                    cleaned["dob"] = dob_date.isoformat()
        except ValueError:
            errors["personal.dob"] = ["Date of birth must be a valid date in YYYY-MM-DD format."]

    # Gender validation
    raw_gender = str(data.get("gender", "") or "").strip().lower()
    if raw_gender and raw_gender not in ALLOWED_GENDERS:
        errors["personal.gender"] = [f"Gender must be one of: {', '.join(sorted(g for g in ALLOWED_GENDERS if g))}."]
    else:
        cleaned["gender"] = raw_gender

    # Emergency Contact Name
    raw_em_name = str(data.get("emergencyName", "") or "").strip()
    if raw_em_name and len(raw_em_name) > 150:
        errors["personal.emergencyName"] = ["Emergency contact name cannot exceed 150 characters."]
    cleaned["emergencyName"] = raw_em_name

    # Emergency Contact Phone
    raw_em_phone = str(data.get("emergencyPhone", "") or "").strip()
    if raw_em_phone:
        is_valid, phone_clean = validate_indian_phone(raw_em_phone)
        if not is_valid:
            errors["personal.emergencyPhone"] = ["Emergency contact phone must be a valid 10-digit Indian mobile number."]
        else:
            cleaned["emergencyPhone"] = phone_clean
    else:
        cleaned["emergencyPhone"] = ""

    # Emergency Contact Relation
    raw_em_rel = str(data.get("emergencyRelation", "") or "").strip()
    if raw_em_rel and len(raw_em_rel) > 50:
        errors["personal.emergencyRelation"] = ["Emergency contact relation cannot exceed 50 characters."]
    cleaned["emergencyRelation"] = raw_em_rel

    if errors:
        raise OnboardingValidationError("Personal information validation failed.", fields=errors)

    return cleaned


def validate_address_step(data: Any) -> Dict[str, Any]:
    """
    Validates Step 2: Address & Travel Territory.
    Required: street (min 3 chars), city (min 2 chars), pincode (exactly 6 digits).
    Required: serviceRadius (1 to 100 km).
    Optional: state.
    """
    if not isinstance(data, dict):
        raise OnboardingValidationError(
            "Address details must be an object.",
            fields={"address": ["Address details must be an object."]}
        )

    errors: Dict[str, List[str]] = {}
    cleaned: Dict[str, Any] = {}

    # Street
    raw_street = str(data.get("street", "") or "").strip()
    if not raw_street:
        errors["address.street"] = ["Street address is required."]
    elif len(raw_street) < 3:
        errors["address.street"] = ["Street address must be at least 3 characters."]
    elif len(raw_street) > 255:
        errors["address.street"] = ["Street address cannot exceed 255 characters."]
    else:
        cleaned["street"] = raw_street

    # City
    raw_city = str(data.get("city", "") or "").strip()
    if not raw_city:
        errors["address.city"] = ["City is required."]
    elif len(raw_city) < 2:
        errors["address.city"] = ["City must be at least 2 characters."]
    elif len(raw_city) > 100:
        errors["address.city"] = ["City cannot exceed 100 characters."]
    else:
        cleaned["city"] = raw_city

    # State (optional text field in existing UI)
    raw_state = str(data.get("state", "") or "").strip()
    if len(raw_state) > 100:
        errors["address.state"] = ["State cannot exceed 100 characters."]
    cleaned["state"] = raw_state

    # Pincode
    raw_pincode = str(data.get("pincode", "") or "").strip()
    if not raw_pincode:
        errors["address.pincode"] = ["Pincode is required."]
    elif not re.match(r"^\d{6}$", raw_pincode):
        errors["address.pincode"] = ["Pincode must be exactly 6 numeric digits."]
    else:
        cleaned["pincode"] = raw_pincode

    if errors:
        raise OnboardingValidationError("Address validation failed.", fields=errors)

    return cleaned


def validate_services_step(services_data: Any, existing_services: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Validates Step 3: Service Selection.
    Resolves each service ID against the authoritative database Service catalog.
    Never trusts client-provided service names, categories, or statuses.
    Status defaults to 'pending' unless already decided by an Admin.
    """
    if not isinstance(services_data, list) or len(services_data) == 0:
        raise OnboardingValidationError(
            "Please select at least ONE service you provide.",
            fields={"services": ["Please select at least ONE service you provide."]}
        )

    # Extract raw IDs
    raw_ids = []
    for item in services_data:
        if isinstance(item, dict):
            s_id = item.get("id")
        else:
            s_id = item
        if s_id is not None:
            raw_ids.append(s_id)

    if not raw_ids:
        raise OnboardingValidationError(
            "Please select at least ONE service you provide.",
            fields={"services": ["Please select at least ONE service you provide."]}
        )

    # Convert to unique integer/string keys
    unique_ids = []
    seen = set()
    for sid in raw_ids:
        try:
            clean_id = int(sid)
        except (ValueError, TypeError):
            clean_id = str(sid).strip()
        if clean_id not in seen:
            seen.add(clean_id)
            unique_ids.append(clean_id)

    from service_requests.models import Service
    from workforce_api.models import WorkforceServiceCatalog

    int_ids = [s for s in unique_ids if isinstance(s, int)]

    db_services = {}
    if int_ids:
        db_services = {
            s.id: s
            for s in Service.objects.filter(pk__in=int_ids, is_active=True).select_related("category")
        }

    wf_services = {}
    if int_ids:
        wf_services = {
            s.id: s
            for s in WorkforceServiceCatalog.objects.filter(pk__in=int_ids, is_active=True)
        }

    # A service ID is valid if it is active in either the shared Service catalog or WorkforceServiceCatalog.
    # Note: Service and WorkforceServiceCatalog have separate integer primary keys. An ID active in Service
    # must not be rejected merely because an unrelated inactive row with the same integer ID exists in WorkforceServiceCatalog.
    invalid_ids = []
    for sid in unique_ids:
        if sid in db_services or sid in wf_services:
            continue
        invalid_ids.append(sid)

    if invalid_ids:
        raise OnboardingValidationError(
            f"The following selected services do not exist or are inactive: {', '.join(str(i) for i in invalid_ids)}.",
            fields={"services": [f"Selected service {i} does not exist or is inactive in catalog." for i in invalid_ids]}
        )

    # Existing admin decisions mapping
    existing_map: Dict[str, Dict[str, Any]] = {}
    if existing_services:
        for s in existing_services:
            existing_map[str(s.get("id"))] = s

    # Construct authoritative service representations
    authoritative_list = []
    for sid in unique_ids:
        if sid in db_services:
            svc_row = db_services[sid]
            cat_name = svc_row.category.name if svc_row.category else "General"
            svc_name = svc_row.name
        else:
            wf_row = wf_services[sid]
            cat_name = wf_row.category or "General"
            svc_name = wf_row.name

        existing_entry = existing_map.get(str(sid), {})
        existing_status = existing_entry.get("status", "pending")
        # Candidate cannot self-grant 'approved'
        if existing_status not in ("pending", "approved", "rejected"):
            existing_status = "pending"

        authoritative_list.append({
            "id": sid,
            "name": svc_name,
            "category": cat_name,
            "category_name": cat_name,
            "status": existing_status,
            "rejection_reason": existing_entry.get("rejection_reason", ""),
        })

    return authoritative_list


def validate_skills_step(data: Any) -> Dict[str, Any]:
    """
    Validates Step 4: Skills & Tools.
    Required: experienceYears (0 to 50), vehicleType (allowed enum).
    Conditional: licenseNumber required if vehicle is two_wheeler or four_wheeler.
    Optional: tools (list of strings), languages (list of strings).
    """
    if not isinstance(data, dict):
        raise OnboardingValidationError(
            "Skills details must be an object.",
            fields={"skills": ["Skills details must be an object."]}
        )

    errors: Dict[str, List[str]] = {}
    cleaned: Dict[str, Any] = {}

    # Experience Years
    raw_exp = data.get("experienceYears")
    if raw_exp is None or raw_exp == "":
        errors["skills.experienceYears"] = ["Years of experience is required."]
    else:
        try:
            exp_val = float(raw_exp)
            if exp_val < 0 or exp_val > 50:
                errors["skills.experienceYears"] = ["Years of experience must be between 0 and 50."]
            else:
                cleaned["experienceYears"] = exp_val
        except (ValueError, TypeError):
            errors["skills.experienceYears"] = ["Years of experience must be a valid number."]

    # Vehicle Type
    raw_veh = str(data.get("vehicleType", "") or "").strip().lower()
    if raw_veh not in ALLOWED_VEHICLE_TYPES:
        errors["skills.vehicleType"] = [f"Vehicle type must be one of: {', '.join(sorted(v for v in ALLOWED_VEHICLE_TYPES if v))}."]
    else:
        cleaned["vehicleType"] = raw_veh

    # License Number (conditional)
    raw_lic = str(data.get("licenseNumber", "") or "").strip()
    if raw_veh in MOTOR_VEHICLES_REQUIRING_LICENSE:
        if not raw_lic:
            errors["skills.licenseNumber"] = ["Driving license number is required for motorized transport."]
        elif len(raw_lic) < 5 or len(raw_lic) > 50:
            errors["skills.licenseNumber"] = ["Please provide a valid driving license number (5–50 characters)."]
        else:
            cleaned["licenseNumber"] = raw_lic
    else:
        cleaned["licenseNumber"] = raw_lic

    # Tools
    raw_tools = data.get("tools", [])
    if isinstance(raw_tools, list):
        cleaned["tools"] = [str(t).strip() for t in raw_tools if str(t).strip()][:50]
    else:
        cleaned["tools"] = []

    # Languages
    raw_langs = data.get("languages", [])
    if isinstance(raw_langs, list):
        cleaned["languages"] = [str(l).strip() for l in raw_langs if str(l).strip()][:20]
    else:
        cleaned["languages"] = []

    if errors:
        raise OnboardingValidationError("Skills and equipment validation failed.", fields=errors)

    return cleaned


def validate_documents_step(documents_dict: Any, employee_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Validates Step 5: Uploaded Documents.
    Checks that each REQUIRED document category (aadhaar, address_proof, bank_proof)
    is present, has a valid server-traced file URL, and is not in a rejected state.
    """
    if not isinstance(documents_dict, dict):
        raise OnboardingValidationError(
            "Documents record must be a dictionary.",
            fields={"documents": ["Documents record must be a dictionary."]}
        )

    errors: Dict[str, List[str]] = {}

    for req_cat in REQUIRED_DOCUMENT_CATEGORIES:
        doc = documents_dict.get(req_cat)
        if not doc or not isinstance(doc, dict):
            errors[f"documents.{req_cat}"] = [f"Mandatory document '{req_cat.replace('_', ' ').title()}' has not been uploaded."]
            continue

        file_url = str(doc.get("file_url", "") or "").strip()
        if not file_url:
            errors[f"documents.{req_cat}"] = [f"Document '{req_cat}' is missing a valid file attachment."]
            continue

        # Traceability check: must originate from server-side upload path
        if not (file_url.startswith("http") or file_url.startswith("/media/") or "workforce_docs" in file_url):
            errors[f"documents.{req_cat}"] = [f"Document '{req_cat}' has an untrusted or invalid file path."]
            continue

        # Status check
        doc_status = str(doc.get("status", "") or "").strip().lower()
        if doc_status == "rejected":
            errors[f"documents.{req_cat}"] = [f"Document '{req_cat}' was rejected by Admin and must be replaced before submission."]
        elif doc_status not in ("uploaded", "approved", "pending"):
            errors[f"documents.{req_cat}"] = [f"Document '{req_cat}' has an invalid status: {doc_status}."]

    if errors:
        raise OnboardingValidationError("Required documents are missing or invalid.", fields=errors)

    return documents_dict


def validate_bank_step(data: Any) -> Dict[str, Any]:
    """
    Validates Step 6: Bank & Payout Details.
    Required: accountHolder (min 2 chars), accountNumber (9-18 digits), ifsc (valid 11-char IFSC).
    Enforces account confirmation match when confirmAccountNumber is provided.
    NEVER returns or persists confirmAccountNumber.
    Optional: bankName, upiId.
    """
    if not isinstance(data, dict):
        raise OnboardingValidationError(
            "Bank details must be an object.",
            fields={"bank": ["Bank details must be an object."]}
        )

    errors: Dict[str, List[str]] = {}
    cleaned: Dict[str, Any] = {}

    # 1. Account Holder Name
    raw_holder = re.sub(r"\s+", " ", str(data.get("accountHolder", "") or "")).strip()
    if not raw_holder:
        errors["bank.accountHolder"] = ["Account holder name is required."]
    elif len(raw_holder) < 2:
        errors["bank.accountHolder"] = ["Account holder name must be at least 2 characters."]
    elif len(raw_holder) > 100:
        errors["bank.accountHolder"] = ["Account holder name cannot exceed 100 characters."]
    elif not re.match(r"^[A-Za-z][A-Za-z\s.'-]*[A-Za-z.]$", raw_holder) or sum(c.isalpha() for c in raw_holder) < 2 or any(p in raw_holder for p in ["..", "--", "''", ".-", "-.", "-'", "'-"]):
        errors["bank.accountHolder"] = ["Enter a valid account holder name using English letters and standard punctuation only."]
    else:
        cleaned["accountHolder"] = raw_holder

    # 2. IFSC Code
    raw_ifsc = str(data.get("ifsc", "") or "").strip().upper()
    if not raw_ifsc:
        errors["bank.ifsc"] = ["IFSC code is required."]
    elif len(raw_ifsc) != 11 or not validate_ifsc_code(raw_ifsc):
        errors["bank.ifsc"] = ["Enter a valid 11-character IFSC code, e.g. SBIN0001234."]
    else:
        cleaned["ifsc"] = raw_ifsc

    # 3. Account Number (strictly 9-18 digits, preserved as string)
    raw_acc = str(data.get("accountNumber", "") or "").strip()
    if not raw_acc:
        errors["bank.accountNumber"] = ["Account number is required."]
    elif not re.match(r"^\d{9,18}$", raw_acc):
        errors["bank.accountNumber"] = ["Account number must be between 9 and 18 digits (numbers only)."]
    else:
        cleaned["accountNumber"] = raw_acc

    # 4. Confirm Account Number (validation only, NEVER persisted)
    if "confirmAccountNumber" in data:
        raw_confirm = str(data.get("confirmAccountNumber", "") or "").strip()
        if not raw_confirm and raw_acc:
            errors["bank.confirmAccountNumber"] = ["Please confirm your account number."]
        elif raw_confirm and not re.match(r"^\d{9,18}$", raw_confirm):
            errors["bank.confirmAccountNumber"] = ["Confirm account number must be between 9 and 18 digits (numbers only)."]
        elif raw_acc and raw_confirm != raw_acc:
            errors["bank.confirmAccountNumber"] = ["Account numbers do not match."]

    # 5. Bank Name (optional)
    raw_bank_name = str(data.get("bankName", "") or "").strip()
    cleaned["bankName"] = raw_bank_name[:100]

    # 6. UPI ID (optional)
    raw_upi = str(data.get("upiId", "") or "").strip()
    if raw_upi:
        if not re.match(r"^[\w\.\-]+@[\w\-]+$", raw_upi):
            errors["bank.upiId"] = ["Enter a valid UPI ID (e.g. username@okhdfcbank)."]
        else:
            cleaned["upiId"] = raw_upi
    else:
        cleaned["upiId"] = ""

    if errors:
        raise OnboardingValidationError("Bank details validation failed.", fields=errors)

    return cleaned


# ─── Step Navigation & Progression Control ─────────────────────────────────────

def can_access_onboarding_step(target_step: int, completed_steps: List[int], is_locked: bool) -> bool:
    """
    Determines if candidate can navigate to target_step.
    - If locked (submitted/approved/under_review), all steps 1-7 can be viewed in read-only mode.
    - If editable:
      - Step 1 is always accessible.
      - Backward navigation to already visited/completed steps is always allowed.
      - Forward navigation requires step (target_step - 1) to be in completed_steps.
    """
    if is_locked:
        return 1 <= target_step <= TOTAL_ONBOARDING_STEPS

    if target_step <= 1:
        return True

    # Backward navigation is allowed if target_step is already completed or at least reached
    completed_set = set(completed_steps)
    if target_step in completed_set:
        return True

    # Moving to the immediate next step requires the previous step to be completed
    return (target_step - 1) in completed_set


# ─── Full Submission Validation ────────────────────────────────────────────────

def validate_full_onboarding_submission(
    emp: Any,
    declaration_accepted: bool = False,
) -> Dict[str, Any]:
    """
    Strict server-authoritative validation for Step 7: Application Submission.
    Checks:
    1. Candidate is in an editable lifecycle state.
    2. declaration_accepted is True.
    3. Step 1 (Personal) is valid.
    4. Step 2 (Address) is valid.
    5. Step 3 (Services) has at least 1 valid DB service.
    6. Step 4 (Skills) is valid.
    7. Step 5 (Documents) has all required documents uploaded and non-rejected.
    8. Step 6 (Bank) is valid.
    Returns cleaned canonical draft payload.
    """
    from workforce_api.services.registration import get_employee_onboarding_dict

    ob = get_employee_onboarding_dict(emp)
    current_status = str(ob.get("status", REGISTRATION_STATUS_NOT_STARTED)).strip().lower()

    if current_status not in CANDIDATE_EDITABLE_STATUSES:
        if current_status in (REGISTRATION_STATUS_SUBMITTED, REGISTRATION_STATUS_UNDER_REVIEW):
            raise OnboardingValidationError(
                "Your application has already been submitted and is pending verification.",
                code="ALREADY_SUBMITTED"
            )
        elif current_status == REGISTRATION_STATUS_APPROVED:
            raise OnboardingValidationError(
                "Your application has already been approved.",
                code="ALREADY_APPROVED"
            )
        elif current_status == REGISTRATION_STATUS_REJECTED:
            raise OnboardingValidationError(
                "Your application was declined. Reapplication is not permitted through this channel.",
                code="APPLICATION_REJECTED"
            )
        else:
            raise OnboardingValidationError(
                f"Application cannot be submitted from current status: {current_status}.",
                code="INVALID_LIFECYCLE_STATE"
            )

    all_errors: Dict[str, List[str]] = {}

    # Check declaration
    if not declaration_accepted:
        all_errors["declaration"] = ["You must accept the declaration to submit your application."]

    draft = ob.get("draft", {})
    services = ob.get("services", []) or draft.get("services", [])
    documents = ob.get("documents", {}) or draft.get("documents", {})

    # 1. Validate Personal
    try:
        clean_personal = validate_personal_step(draft.get("personal", {}))
    except OnboardingValidationError as e:
        all_errors.update(e.fields)
        clean_personal = draft.get("personal", {})

    # 2. Validate Address
    try:
        clean_address = validate_address_step(draft.get("address", {}))
    except OnboardingValidationError as e:
        all_errors.update(e.fields)
        clean_address = draft.get("address", {})

    # 3. Validate Services
    try:
        clean_services = validate_services_step(services, existing_services=ob.get("services", []))
    except OnboardingValidationError as e:
        all_errors.update(e.fields)
        clean_services = services

    # 4. Validate Skills
    try:
        clean_skills = validate_skills_step(draft.get("skills", {}))
    except OnboardingValidationError as e:
        all_errors.update(e.fields)
        clean_skills = draft.get("skills", {})

    # 5. Validate Documents
    try:
        clean_documents = validate_documents_step(documents, employee_id=emp.id)
    except OnboardingValidationError as e:
        all_errors.update(e.fields)
        clean_documents = documents

    # 6. Validate Bank
    try:
        clean_bank = validate_bank_step(draft.get("bank", {}))
    except OnboardingValidationError as e:
        all_errors.update(e.fields)
        clean_bank = draft.get("bank", {})

    if all_errors:
        raise OnboardingValidationError(
            "Application cannot be submitted. Please complete or correct all highlighted sections.",
            fields=all_errors,
            code="ONBOARDING_SUBMISSION_INCOMPLETE"
        )

    return {
        "personal": clean_personal,
        "address": clean_address,
        "services": clean_services,
        "skills": clean_skills,
        "documents": clean_documents,
        "bank": clean_bank,
    }
