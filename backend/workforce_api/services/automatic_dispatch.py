"""
Authoritative Automatic Geo-Based Distance Wave Dispatch Service.

Single source of truth for all automatic job dispatch, candidate ranking,
6-wave sequential proximity evaluation (0-1km, 1-2km, 2-5km, 5-10km, 10-15km, 15-20km),
synchronized 2-minute offer creation with UUID wave IDs, lazy and scheduled wave progression,
and cross-application job reconciliation across Workforce and Marketplace.

Public API (preferred entry points for all callers):
  reconcile_booking_for_dispatch(job)  — single authoritative gate for any booking needing dispatch
  dispatch_pending_jobs(company_id, limit)  — periodic reconciliation sweep
  reconsider_jobs_for_employee(employee)    — GPS / presence re-evaluation trigger
"""
import uuid
import logging
import re
from datetime import timedelta
from typing import List, Dict, Any, Tuple, Optional, Set

from django.db import transaction
from django.db.models import Exists, OuterRef, Prefetch, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.utils.dateparse import parse_datetime

from service_requests.models import ServiceRequest, EmployeeJob
from service_requests.state_machine import apply_transition
from employees.models import Employee
from workforce_api.models import (
    WorkforceJobOffer,
    WorkforceNotification,
    WorkforceEmployeeSkill,
    WorkforceEmployeeCompliance,
    WorkforceEmployeeSchedule,
    WorkforceEventLog,
)
from workforce_api.services.geo_spatial import (
    ADMIN_DISPATCH_RADIUS_KM,
    MAX_DISPATCH_RADIUS_KM,
    MAX_GPS_AGE_SECONDS,
    DISTANCE_TOLERANCE_KM,
    calculate_distance_km,
    calculate_distance_meters,
    get_spatial_bounding_box,
    classify_wave,
    get_distance_band,
    is_within_automatic_radius,
    is_within_radius,
    validate_coordinates,
)
from workforce_api.services.workload import get_employee_active_job, ACTIVE_WORKLOAD_STATUSES

logger = logging.getLogger("workforce.dispatch")

# Backward compatibility alias
haversine_distance = calculate_distance_meters

# Phase 1: Exact 2-minute offer duration
DEFAULT_OFFER_DURATION_MINUTES = 2

# Dispatchable database statuses
DISPATCHABLE_STATUSES = ["draft", "new_request", "received", "confirmed", "unassigned", "assigned", "redispatching"]


def get_booking_discovery_scope(company_id: Optional[int] = None) -> Q:
    """
    Authoritative booking discovery scope helper for Marketplace & Vendor bookings:
    - If company_id is provided (vendor context): discovers company-owned bookings + unassigned Marketplace bookings (company_id=NULL).
    - If company_id is None (marketplace / global sweep context): discovers all dispatchable bookings across all companies + Marketplace bookings.
    """
    if company_id is not None:
        return Q(company_id=company_id) | Q(company_id__isnull=True)
    return Q()

def normalize_service_name(name: str) -> str:
    """
    Normalizes service names by lowercasing, replacing dashes, underscores,
    slashes, unicode hyphens, pluses, and ampersands with standard words.
    """
    if not name:
        return ""
    s = str(name).lower()
    s = s.replace("—", " ").replace("–", " ").replace("-", " ").replace("_", " ")
    s = s.replace("/", " ").replace("\\", " ").replace("+", " and ")
    s = s.replace("&", " and ")
    return " ".join(s.split())



def resolve_service_identifiers(category_raw: Any, issue_title_raw: Any, cart_data: Any) -> List[str]:
    """
    Resolves all potential canonical service names and category identifiers for a booking.
    If category_raw or issue_title_raw is a numeric ID (e.g. '15', '18', '11'), looks up
    CatalogCategory and Service database records to resolve canonical titles/slugs.
    """
    terms = []

    def _add_term(val):
        if val is None:
            return
        val_str = str(val).strip()
        if not val_str:
            return
        if val_str not in terms:
            terms.append(val_str)

        # If numeric string or integer, resolve from database tables
        if val_str.isdigit():
            cat_id = int(val_str)
            try:
                from service_requests.models import CatalogCategory, Service
                cat_obj = CatalogCategory.objects.filter(pk=cat_id).first()
                if cat_obj:
                    if cat_obj.name and cat_obj.name not in terms:
                        terms.append(cat_obj.name)
                    if hasattr(cat_obj, "slug") and cat_obj.slug and cat_obj.slug not in terms:
                        terms.append(cat_obj.slug)
                svc_obj = Service.objects.filter(pk=cat_id).first()
                if svc_obj:
                    if svc_obj.name and svc_obj.name not in terms:
                        terms.append(svc_obj.name)
                    if hasattr(svc_obj, "slug") and svc_obj.slug and svc_obj.slug not in terms:
                        terms.append(svc_obj.slug)
                    if getattr(svc_obj, "category", None) and svc_obj.category.name not in terms:
                        terms.append(svc_obj.category.name)
            except Exception as e:
                logger.debug(f"[SERVICE_ID_RESOLVE_ERR] {e}")

    _add_term(category_raw)
    _add_term(issue_title_raw)

    if isinstance(cart_data, list):
        for item in cart_data:
            if isinstance(item, dict):
                _add_term(item.get("service_name"))
                _add_term(item.get("category"))
                _add_term(item.get("categoryName"))
                _add_term(item.get("title"))
                _add_term(item.get("name"))
                _add_term(item.get("service_id"))
                _add_term(item.get("category_id"))
                item_id = item.get("id")
                if item_id:
                    _add_term(item_id)
                    try:
                        from service_requests.models import Service
                        svc = Service.objects.filter(slug=str(item_id)).first()
                        if svc:
                            _add_term(svc.name)
                            if svc.category:
                                _add_term(svc.category.name)
                    except Exception:
                        pass
    elif isinstance(cart_data, dict):
        _add_term(cart_data.get("service_name"))
        _add_term(cart_data.get("category"))
        _add_term(cart_data.get("categoryName"))
        _add_term(cart_data.get("title"))
        _add_term(cart_data.get("name"))

    return terms


def canonical_service_match(requested_service: str, approved_services: List[str], verified_skills: List[str]) -> Tuple[bool, str, str]:
    """
    Evaluates whether a requested service matches an employee's authorized services or verified skills
    using 100% database-driven relationships:
    ServiceRequest → Service → required Skill/Capability → verified Employee Skill.
    """
    if not requested_service:
        return True, "EMPTY_SERVICE_BYPASS", ""

    req_clean = normalize_service_name(requested_service)
    if not req_clean:
        return False, "EMPTY_SERVICE", ""

    # Direct match against approved services or verified skills (normalized)
    for app_s in approved_services:
        if app_s and normalize_service_name(app_s) == req_clean:
            return True, "EXACT_APPROVED_SERVICE_MATCH", app_s

    for vs in verified_skills:
        if vs and normalize_service_name(vs) == req_clean:
            return True, "EXACT_VERIFIED_SKILL_MATCH", vs

    # Database Service Resolution
    try:
        from service_requests.models import Service, CatalogCategory
        from workforce_api.models import WorkforceSkill, WorkforceServiceSkillRequirement

        svc = None
        if req_clean.isdigit():
            svc = Service.objects.filter(pk=int(req_clean)).select_related("category").first()
        if not svc:
            svc = Service.objects.filter(Q(slug=req_clean) | Q(name__iexact=req_clean)).select_related("category").first()

        if svc:
            # 1. Relational requirements: WorkforceServiceSkillRequirement
            req_skills = list(WorkforceServiceSkillRequirement.objects.filter(service=svc).select_related("skill"))
            if req_skills:
                req_names = {normalize_service_name(r.skill.name) for r in req_skills}
                req_codes = {normalize_service_name(r.skill.code) for r in req_skills if r.skill.code}
                for vs in verified_skills:
                    vs_clean = normalize_service_name(vs)
                    if vs_clean in req_names or vs_clean in req_codes:
                        return True, "DB_SERVICE_SKILL_REQUIREMENT_MATCH", vs

            # 2. Match service name / slug against employee verified skills
            svc_name_norm = normalize_service_name(svc.name)
            svc_slug_norm = normalize_service_name(svc.slug or "")
            for vs in verified_skills:
                vs_clean = normalize_service_name(vs)
                if vs_clean and (vs_clean == svc_name_norm or vs_clean == svc_slug_norm):
                    return True, "DB_SERVICE_SKILL_MATCH", vs

            # 3. Match service name / slug / ID against employee approved services
            for app_s in approved_services:
                app_clean = normalize_service_name(app_s)
                if app_clean and (app_clean == svc_name_norm or app_clean == svc_slug_norm or str(app_s) == str(svc.id)):
                    return True, "DB_SERVICE_APPROVED_MATCH", app_s

            # 4. Service's CatalogCategory
            if svc.category:
                cat_name_norm = normalize_service_name(svc.category.name)
                cat_slug_norm = normalize_service_name(svc.category.slug or "")
                for app_s in approved_services:
                    app_clean = normalize_service_name(app_s)
                    if app_clean and (app_clean == cat_name_norm or app_clean == cat_slug_norm or str(app_s) == str(svc.category_id)):
                        return True, "DB_CATEGORY_APPROVED_MATCH", app_s
                for vs in verified_skills:
                    vs_clean = normalize_service_name(vs)
                    if vs_clean and (vs_clean == cat_name_norm or vs_clean == cat_slug_norm):
                        return True, "DB_CATEGORY_SKILL_MATCH", vs

        # Database Category Resolution
        cat = None
        if req_clean.isdigit():
            cat = CatalogCategory.objects.filter(pk=int(req_clean)).first()
        if not cat:
            cat = CatalogCategory.objects.filter(Q(slug=req_clean) | Q(name__iexact=req_clean)).first()

        if cat:
            cat_name_norm = normalize_service_name(cat.name)
            cat_slug_norm = normalize_service_name(cat.slug or "")
            for app_s in approved_services:
                app_clean = normalize_service_name(app_s)
                if app_clean and (app_clean == cat_name_norm or app_clean == cat_slug_norm or str(app_s) == str(cat.id)):
                    return True, "DB_CATEGORY_MATCH", app_s
            for vs in verified_skills:
                vs_clean = normalize_service_name(vs)
                if vs_clean and (vs_clean == cat_name_norm or vs_clean == cat_slug_norm):
                    return True, "DB_CATEGORY_SKILL_MATCH", vs

        # Database Skill Resolution
        db_skill = WorkforceSkill.objects.filter(Q(name__iexact=req_clean) | Q(code__iexact=req_clean)).first()
        if db_skill:
            sk_name_norm = normalize_service_name(db_skill.name)
            sk_code_norm = normalize_service_name(db_skill.code or "")
            for vs in verified_skills:
                vs_clean = normalize_service_name(vs)
                if vs_clean and (vs_clean == sk_name_norm or vs_clean == sk_code_norm):
                    return True, "DB_SKILL_MATCH", vs

    except Exception as e:
        logger.debug(f"[CANONICAL_DB_MATCH_ERR] {e}")

    return False, "NO_DB_RELATIONSHIP_MATCH", ""



_MANDATORY_DOC_REQS_CACHE: Dict[int, List[Any]] = {}
_MANDATORY_COMP_REQS_CACHE: Dict[int, List[Any]] = {}


def check_candidate_eligibility(emp: Employee, service_name: Optional[str] = None, check_workload: bool = True) -> Tuple[bool, str, Dict[str, bool]]:
    """
    9-Gate Employee Eligibility Engine:
    Authoritative server-side evaluation of 9 mandatory operational gates.
    
    Parameters:
      emp: Employee model instance
      service_name: Optional requested service name
      check_workload: If True (default, for acceptance), Gate 9 fails if the technician has an active job.
                      If False (for offer discovery), Gate 9 passes so that busy technicians can still
                      receive and view upcoming job offers.
    
    Returns (is_eligible, reason_message, gate_results_dict).
    """
    gate_results = {f"G{i}": True for i in range(1, 10)}

    # ── Gate 1: Account Active ────────────────────────────────────────────────
    if not emp or not emp.is_active or not getattr(emp.user, "is_active", True):
        gate_results["G1"] = False
        logger.debug(f"[9GATE_REJECT_GATE1_ACCOUNT_INACTIVE] Employee #{getattr(emp, 'id', None)} account is inactive.")
        return False, "Gate 1: Technician account is inactive.", gate_results

    bank_details = emp.bank_details or {}
    onboarding = bank_details.get("onboarding", {})

    # ── Gate 2: Registration Approved ─────────────────────────────────────────
    reg_status = onboarding.get("status", "not_started")
    if reg_status != "approved":
        gate_results["G2"] = False
        logger.debug(f"[9GATE_REJECT_GATE2_ONBOARDING_UNAPPROVED] Employee #{emp.id} onboarding status is '{reg_status}'.")
        return False, "Gate 2: Technician registration onboarding is not approved.", gate_results

    # ── Gate 3: Required Documents Approved ───────────────────────────────────
    if emp and getattr(emp, "company_id", None):
        if hasattr(emp, "prefetched_mandatory_doc_reqs"):
            mandatory_doc_reqs = emp.prefetched_mandatory_doc_reqs
        else:
            cid = emp.company_id
            if cid not in _MANDATORY_DOC_REQS_CACHE:
                from workforce_api.models import WorkforceRequiredDocument
                _MANDATORY_DOC_REQS_CACHE[cid] = list(WorkforceRequiredDocument.objects.filter(company_id=cid, is_mandatory=True))
            mandatory_doc_reqs = _MANDATORY_DOC_REQS_CACHE[cid]

        if mandatory_doc_reqs:
            if hasattr(emp, "prefetched_employee_documents"):
                emp_docs_map = {d.requirement_id: d for d in emp.prefetched_employee_documents}
            else:
                from workforce_api.models import WorkforceEmployeeDocument
                emp_docs_map = {
                    d.requirement_id: d
                    for d in WorkforceEmployeeDocument.objects.filter(employee=emp, requirement__in=mandatory_doc_reqs)
                }

            today = timezone.now().date()
            for req_doc in mandatory_doc_reqs:
                emp_doc = emp_docs_map.get(req_doc.id)
                if not emp_doc or emp_doc.status != "APPROVED":
                    gate_results["G3"] = False
                    st = emp_doc.status if emp_doc else "MISSING"
                    logger.debug(f"[9GATE_REJECT_GATE3_DOCUMENTS_UNAPPROVED] Employee #{emp.id} mandatory document '{req_doc.title}' is {st}.")
                    return False, f"Gate 3: Technician mandatory document '{req_doc.title}' is {st} (must be APPROVED).", gate_results
                if emp_doc.expiry_date and emp_doc.expiry_date < today:
                    gate_results["G3"] = False
                    logger.debug(f"[9GATE_REJECT_GATE3_DOCUMENTS_EXPIRED] Employee #{emp.id} mandatory document '{req_doc.title}' expired on {emp_doc.expiry_date}.")
                    return False, f"Gate 3: Technician mandatory document '{req_doc.title}' expired on {emp_doc.expiry_date}.", gate_results
        else:
            documents = onboarding.get("documents", {})
            if any(doc.get("status") == "rejected" for doc in documents.values()):
                gate_results["G3"] = False
                logger.debug(f"[9GATE_REJECT_GATE3_DOCUMENTS_REJECTED] Employee #{emp.id} has rejected documents.")
                return False, "Gate 3: Technician has rejected dossier documents.", gate_results
    else:
        documents = onboarding.get("documents", {})
        if any(doc.get("status") in ["rejected", "pending_review", "missing"] for doc in documents.values()):
            gate_results["G3"] = False
            return False, "Gate 3: Technician has unapproved dossier documents.", gate_results

    # ── Gate 4: Mandatory Compliance Valid ────────────────────────────────────
    if emp and getattr(emp, "company_id", None):
        if hasattr(emp, "prefetched_mandatory_comp_reqs"):
            mandatory_comp_reqs = emp.prefetched_mandatory_comp_reqs
        else:
            cid = emp.company_id
            if cid not in _MANDATORY_COMP_REQS_CACHE:
                from workforce_api.models import WorkforceComplianceRequirement
                _MANDATORY_COMP_REQS_CACHE[cid] = list(WorkforceComplianceRequirement.objects.filter(company_id=cid, is_mandatory=True))
            mandatory_comp_reqs = _MANDATORY_COMP_REQS_CACHE[cid]

        if mandatory_comp_reqs:
            today = timezone.now().date()
            if hasattr(emp, "prefetched_compliance_records"):
                emp_comp_records = emp.prefetched_compliance_records
            else:
                emp_comp_records = list(WorkforceEmployeeCompliance.objects.filter(employee=emp, requirement__in=mandatory_comp_reqs))
            emp_comp_map = {c.requirement_id: c for c in emp_comp_records}
            for comp_req in mandatory_comp_reqs:
                c_rec = emp_comp_map.get(comp_req.id)
                if not c_rec or c_rec.status in ["MISSING", "PENDING_REVIEW", "REJECTED", "EXPIRED"]:
                    gate_results["G4"] = False
                    st = c_rec.status if c_rec else "MISSING"
                    logger.debug(f"[9GATE_REJECT_GATE4_COMPLIANCE_INVALID] Employee #{emp.id} mandatory compliance '{comp_req.title}' is {st}.")
                    return False, f"Gate 4: Mandatory compliance '{comp_req.title}' is {st} (must be VALID).", gate_results
                if c_rec.expiry_date and c_rec.expiry_date < today:
                    gate_results["G4"] = False
                    return False, f"Gate 4: Mandatory compliance '{comp_req.title}' expired on {c_rec.expiry_date}.", gate_results
        else:
            if hasattr(emp, "prefetched_compliance_records"):
                invalid_comp = next((c for c in emp.prefetched_compliance_records if c.status in ["EXPIRED", "REJECTED"]), None)
                if invalid_comp:
                    gate_results["G4"] = False
                    return False, "Gate 4: Technician has expired or rejected mandatory compliance document.", gate_results
            elif hasattr(emp, "prefetched_invalid_compliance"):
                if emp.prefetched_invalid_compliance:
                    gate_results["G4"] = False
                    logger.debug(f"[9GATE_REJECT_GATE4_COMPLIANCE_INVALID] Employee #{emp.id} has invalid compliance.")
                    return False, "Gate 4: Technician has expired or rejected mandatory compliance document.", gate_results
            else:
                mandatory_comp = WorkforceEmployeeCompliance.objects.filter(
                    employee=emp,
                    requirement__is_mandatory=True,
                    status__in=["EXPIRED", "REJECTED"],
                ).first()
                if mandatory_comp:
                    gate_results["G4"] = False
                    logger.debug(f"[9GATE_REJECT_GATE4_COMPLIANCE_INVALID] Employee #{emp.id} compliance '{mandatory_comp.requirement.title}' is {mandatory_comp.status}.")
                    return False, f"Gate 4: Technician has expired or rejected mandatory compliance document: '{mandatory_comp.requirement.title}'.", gate_results
    else:
        if hasattr(emp, "prefetched_invalid_compliance"):
            if emp.prefetched_invalid_compliance:
                gate_results["G4"] = False
                return False, "Gate 4: Technician has expired or rejected mandatory compliance document.", gate_results
        else:
            mandatory_comp = WorkforceEmployeeCompliance.objects.filter(
                employee=emp,
                requirement__is_mandatory=True,
                status__in=["EXPIRED", "REJECTED"],
            ).first()
            if mandatory_comp:
                gate_results["G4"] = False
                return False, f"Gate 4: Technician has expired or rejected mandatory compliance document: '{mandatory_comp.requirement.title}'.", gate_results

    # ── Gate 5: Working Schedule ──────────────────────────────────────────────
    if hasattr(emp, "prefetched_today_schedules"):
        sched = emp.prefetched_today_schedules[0] if emp.prefetched_today_schedules else None
    else:
        today_dow = timezone.now().weekday()
        sched = WorkforceEmployeeSchedule.objects.filter(employee=emp, day_of_week=today_dow).first()

    if sched:
        if not sched.is_working_day:
            gate_results["G5"] = False
            logger.debug(f"[9GATE_REJECT_GATE5_SCHEDULE_OFF] Employee #{emp.id} is scheduled off today.")
            return False, "Gate 5: Technician is scheduled off today.", gate_results
        now_time = timezone.now().time()
        if not (sched.start_time <= now_time <= sched.end_time):
            gate_results["G5"] = False
            logger.debug(f"[9GATE_REJECT_GATE5_SCHEDULE_OUTSIDE] Employee #{emp.id} outside hours ({sched.start_time}-{sched.end_time}).")
            return False, f"Gate 5: Technician is outside scheduled working hours ({sched.start_time.strftime('%H:%M')}-{sched.end_time.strftime('%H:%M')}).", gate_results

    # ── Gate 6: Service / Skill Authorization ─────────────────────────────────
    approved_svcs = []
    for s in onboarding.get("services", []):
        if s.get("status") == "approved":
            if s.get("name"):
                approved_svcs.append(s["name"])
            if s.get("category"):
                approved_svcs.append(s["category"])

    if hasattr(emp, "service_roles") and isinstance(emp.service_roles, list):
        for sr in emp.service_roles:
            if sr and str(sr) not in approved_svcs:
                approved_svcs.append(str(sr))

    if hasattr(emp, "prefetched_verified_skills"):
        verified_skills = [es.skill.name for es in emp.prefetched_verified_skills]
    else:
        verified_skills = list(
            WorkforceEmployeeSkill.objects.filter(employee=emp, is_verified=True).values_list("skill__name", flat=True)
        )

    if service_name:
        is_match, method, matched = canonical_service_match(service_name, approved_svcs, verified_skills)
        logger.debug(f"[DISPATCH_SERVICE_MATCH] job_service=\"{service_name}\" employee_services={approved_svcs} verified_skills={verified_skills} match_method={method} result={'PASS' if is_match else 'FAIL'}")
        if not is_match:
            gate_results["G6"] = False
            logger.debug(f"[9GATE_REJECT_GATE6_SKILL_MISMATCH] Employee #{emp.id} not authorized/verified for '{service_name}'.")
            return False, f"Gate 6: Technician is not authorized or verified for requested service '{service_name}'.", gate_results

    # ── Gate 7: Live Presence (Online & Available) ────────────────────────────
    # For offer receipt, technician must be online; current_availability can be 'busy' if they are currently executing another job
    if not emp.is_online:
        gate_results["G7"] = False
        logger.debug(f"[9GATE_REJECT_GATE7_PRESENCE_OFFLINE] Employee #{emp.id} presence is is_online={emp.is_online}.")
        return False, "Gate 7: Technician is currently OFFLINE.", gate_results

    # ── Gate 8: Leave Check ───────────────────────────────────────────────────
    today_str = timezone.now().date().isoformat()
    leaves = bank_details.get("leaves", [])
    for l in leaves:
        if l.get("status") == "approved":
            start_date = l.get("start_date", "")
            end_date = l.get("end_date", "")
            if start_date <= today_str <= end_date:
                gate_results["G8"] = False
                logger.debug(f"[9GATE_REJECT_GATE8_LEAVE_ACTIVE] Employee #{emp.id} on approved leave ({start_date} to {end_date}).")
                return False, f"Gate 8: Technician is on approved leave from {start_date} to {end_date}.", gate_results

    # ── Gate 9: Workload Concurrency (Single-Active-Job Isolation) ──────────────
    # Checked strictly on Accept. Bypassed for offer recipient discovery so busy technicians can see upcoming offers.
    if check_workload:
        if hasattr(emp, "is_busy_job"):
            if emp.is_busy_job:
                gate_results["G9"] = False
                logger.info(f"[DISPATCH_REJECT] employee={emp.id} reason=EMPLOYEE_ALREADY_BUSY (annotated)")
                return False, f"Gate 9: Technician #{emp.id} is busy on an active job.", gate_results
        else:
            active_job = get_employee_active_job(emp)
            if active_job:
                gate_results["G9"] = False
                logger.info(f"[DISPATCH_REJECT] employee={emp.id} reason=EMPLOYEE_ALREADY_BUSY active_job={active_job.id}")
                return False, f"Gate 9: Technician is busy on active Job #{active_job.id} ({active_job.request_id}).", gate_results

    return True, "All Eligibility Gates Passed", gate_results


def get_eligible_candidates(
    job_id_or_obj,
    max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS,
    radius_km: Optional[float] = None,
    exclude_employee_ids: Optional[List[int]] = None,
    candidate_employee_ids: Optional[List[int]] = None,
    check_workload: bool = False,
) -> List[Dict[str, Any]]:
    """
    Finds and ranks all eligible candidate employees for a given ServiceRequest within the configured global radius.
    Uses mathematical bounding-box prefiltering and exact Haversine distance calculation.
    
    If candidate_employee_ids is provided (e.g. from Redis GEO candidate discovery),
    evaluates only those candidate IDs, drastically reducing Supabase/PostgreSQL roundtrips.
    By default check_workload=False so busy employees are eligible to receive and view offers.
    """
    from workforce_api.services.geo_spatial import get_global_dispatch_radius_km
    if radius_km is None:
        radius_km = get_global_dispatch_radius_km()
    if hasattr(job_id_or_obj, "latitude"):
        job_obj = job_id_or_obj
    else:
        job_obj = ServiceRequest.objects.filter(pk=job_id_or_obj).first()
        if not job_obj:
            logger.warning(f"[DISPATCH_JOB_NOT_FOUND] Job #{job_id_or_obj} not found.")
            return []

    if candidate_employee_ids is not None and not candidate_employee_ids:
        logger.debug(f"[DISPATCH_EMPTY_CANDIDATE_LIST] Empty candidate_employee_ids supplied for Job #{job_obj.id}.")
        return []

    is_valid_coords, cust_lat, cust_lon, coord_err = validate_coordinates(job_obj.latitude, job_obj.longitude)
    if not is_valid_coords:
        logger.warning(f"[DISPATCH_GPS_MISSING] Job #{job_obj.id} invalid coordinates: {coord_err}")
        return []

    min_lat, max_lat, min_lon, max_lon = get_spatial_bounding_box(cust_lat, cust_lon, radius_km=radius_km)

    today_dow = timezone.now().weekday()
    busy_subquery = ServiceRequest.objects.filter(
        assigned_employee_id=OuterRef("pk"),
        status__in=ACTIVE_WORKLOAD_STATUSES
    )

    candidates_qs = (
        Employee.objects.filter(
            is_active=True,
            is_online=True,
        )
        .select_related("user", "company")
        .annotate(is_busy_job=Exists(busy_subquery))
    )

    if exclude_employee_ids:
        candidates_qs = candidates_qs.exclude(pk__in=exclude_employee_ids)

    if candidate_employee_ids is not None:
        candidates_qs = candidates_qs.filter(pk__in=candidate_employee_ids)

    candidates_qs = (
        candidates_qs
        .prefetch_related(
            Prefetch(
                "compliance_records",
                queryset=WorkforceEmployeeCompliance.objects.filter(
                    requirement__is_mandatory=True,
                    status__in=["EXPIRED", "REJECTED"],
                ),
                to_attr="prefetched_invalid_compliance",
            ),
            Prefetch(
                "schedules",
                queryset=WorkforceEmployeeSchedule.objects.filter(day_of_week=today_dow),
                to_attr="prefetched_today_schedules",
            ),
            Prefetch(
                "skills",
                queryset=WorkforceEmployeeSkill.objects.filter(is_verified=True).select_related("skill"),
                to_attr="prefetched_verified_skills",
            ),
        )
    )

    if job_obj.company_id:
        candidates_qs = candidates_qs.filter(company_id=job_obj.company_id)
    else:
        candidates_qs = candidates_qs.filter(Q(company__is_active=True) | Q(company__isnull=True))

    now = timezone.now()

    declined_emp_ids = set(
        WorkforceJobOffer.objects.filter(
            job=job_obj,
            status__in=["DECLINED", "REJECTED"],
        ).values_list("employee_id", flat=True)
    )
    # Exclude candidates who currently have an active unexpired offer
    active_offer_emp_ids = set(
        WorkforceJobOffer.objects.filter(
            job=job_obj,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        ).values_list("employee_id", flat=True)
    )
    excluded_emp_ids = declined_emp_ids | active_offer_emp_ids
    if exclude_employee_ids:
        excluded_emp_ids.update(exclude_employee_ids)

    # Resolve all potential service identifiers (category names, numeric IDs, cart items)
    requested_service_terms = resolve_service_identifiers(
        job_obj.service_category,
        job_obj.issue_title,
        job_obj.cart_data,
    )

    ranked_candidates = []
    rejected_reasons = {}

    for emp in candidates_qs:
        if emp.id in excluded_emp_ids:
            logger.debug(f"[DISPATCH_CANDIDATE_SKIPPED] Employee #{emp.id} excluded (declined or active unexpired offer).")
            continue

        # Extract live GPS from User.last_known_location
        last_loc = getattr(emp.user, "last_known_location", None) or {}
        emp_lat = last_loc.get("latitude") if last_loc.get("latitude") is not None else last_loc.get("lat")
        emp_lon = last_loc.get("longitude") if last_loc.get("longitude") is not None else (last_loc.get("lng") or last_loc.get("lon"))

        is_emp_loc_valid, emp_lat_f, emp_lon_f, _ = validate_coordinates(emp_lat, emp_lon)
        if not is_emp_loc_valid:
            rejected_reasons[emp.id] = "GPS missing or invalid"
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=GPS_MISSING")
            continue

        # Bounding box prefilter
        if not (min_lat <= emp_lat_f <= max_lat and min_lon <= emp_lon_f <= max_lon):
            rejected_reasons[emp.id] = "Outside spatial bounding box"
            logger.debug(f"[DISPATCH_BOUNDING_BOX_EXCLUDED] employee={emp.id} outside bbox ({emp_lat_f}, {emp_lon_f})")
            continue

        gps_age_s = 0.0
        updated_at_str = last_loc.get("updated_at") or last_loc.get("captured_at")
        if updated_at_str:
            try:
                loc_dt = parse_datetime(str(updated_at_str))
                if loc_dt:
                    if timezone.is_naive(loc_dt):
                        loc_dt = timezone.make_aware(loc_dt)
                    raw_diff = (now - loc_dt).total_seconds()
                    if raw_diff < 0 and raw_diff >= -300:
                        gps_age_s = 0.0
                    else:
                        gps_age_s = raw_diff
            except Exception:
                gps_age_s = 0.0

        # Exact geodesic distance
        dist_km = calculate_distance_km(cust_lat, cust_lon, emp_lat_f, emp_lon_f)

        # Strict boundary enforcement using configured global radius
        if not is_within_automatic_radius(dist_km, max_radius_km=radius_km):
            rejected_reasons[emp.id] = f"Outside dispatch radius ({dist_km:.2f}km > {radius_km:.1f}km)"
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=RADIUS_EXCEEDED distance_km={dist_km}")
            continue

        # Classify sequential distance wave (1 to 6) using configured global radius
        wave_number = classify_wave(dist_km, max_radius_km=radius_km)
        if wave_number is None:
            rejected_reasons[emp.id] = f"Outside automatic waves ({dist_km:.2f}km)"
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=OUTSIDE_AUTOMATIC_WAVES distance_km={dist_km}")
            continue

        # Check candidate eligibility across all resolved service terms
        is_eligible = False
        elig_reason = "No service terms matched"
        gate_results = {}

        if not requested_service_terms:
            is_eligible, elig_reason, gate_results = check_candidate_eligibility(emp, None, check_workload=check_workload)
        else:
            for term in requested_service_terms:
                term_elig, term_reason, term_gates = check_candidate_eligibility(emp, term, check_workload=check_workload)
                if term_elig:
                    is_eligible = True
                    elig_reason = "All Eligibility Gates Passed"
                    gate_results = term_gates
                    break
                else:
                    elig_reason = term_reason
                    gate_results = term_gates

        if not is_eligible:
            rejected_reasons[emp.id] = elig_reason
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason={elig_reason}")
            continue

        if gps_age_s > max_gps_age_seconds:
            rejected_reasons[emp.id] = f"Stale GPS ({gps_age_s:.0f}s > {max_gps_age_seconds}s)"
            logger.info(f"[DISPATCH_REJECT] job={job_obj.id} employee={emp.id} reason=GPS_STALE gps_age={gps_age_s}s")
            continue

        # Proximity score (closer = higher score, max 100)
        proximity_score = max(0.0, 100.0 - (dist_km * 2.0))

        # Skill proficiency score bonus
        skills = getattr(emp, "prefetched_verified_skills", [])
        max_prof = 0
        for sk in skills:
            sk_name = sk.skill.name.lower()
            matches = False
            for term in requested_service_terms:
                if term and (normalize_service_name(term) in sk_name or sk_name in normalize_service_name(term)):
                    matches = True
                    break
            if matches:
                if sk.proficiency_level == "EXPERT":
                    max_prof = max(max_prof, 30)
                elif sk.proficiency_level == "INTERMEDIATE":
                    max_prof = max(max_prof, 20)
                else:
                    max_prof = max(max_prof, 10)

        # Territory bonus
        city = (emp.bank_details or {}).get("onboarding", {}).get("draft", {}).get("personal", {}).get("city", "")
        territory_bonus = 15.0 if (job_obj.address and city and city.lower() in job_obj.address.lower()) else 0.0

        # Shift clock-in bonus
        bank_details = emp.bank_details or {}
        is_clocked_in = bank_details.get("attendance", {}).get("is_clocked_in", False)
        clock_in_bonus = 10.0 if is_clocked_in else 0.0

        total_score = proximity_score + max_prof + territory_bonus + clock_in_bonus

        logger.info(
            f"[DISPATCH_CANDIDATE_FOUND] Employee #{emp.id} ({emp.user.username}) eligible for Job #{job_obj.id}: "
            f"{dist_km:.2f}km away (Wave {wave_number}), score={total_score:.1f}"
        )

        ranked_candidates.append({
            "employee": emp,
            "distance_km": dist_km,
            "wave_number": wave_number,
            "distance_band": get_distance_band(dist_km),
            "latitude": emp_lat_f,
            "longitude": emp_lon_f,
            "gps_age_seconds": gps_age_s,
            "score": round(total_score, 1),
        })

    # Structured candidate summary logging
    if rejected_reasons:
        rej_str = "; ".join([f"EMP-{e_id}: {r}" for e_id, r in list(rejected_reasons.items())[:5]])
        logger.info(f"[DISPATCH_CANDIDATE_SUMMARY] Job #{job_obj.id} — Eligible: {len(ranked_candidates)}, Rejected ({len(rejected_reasons)}): {rej_str}")

    # Deterministic sort: distance (ascending), score (descending), employee ID (ascending)
    ranked_candidates.sort(key=lambda x: (x["distance_km"], -x["score"], x["employee"].id))
    return ranked_candidates


def sweep_job_expired_offers(job_obj) -> int:
    """
    Lazy reconciliation helper: sweeps and marks EXPIRED any overdue OFFERED offers
    for the given job.
    """
    now = timezone.now()
    return WorkforceJobOffer.objects.filter(
        job=job_obj,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__lte=now,
    ).update(status=WorkforceJobOffer.Status.EXPIRED)


def dispatch_job(
    job_id_or_obj,
    max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS,
    exclude_employee_ids: Optional[List[int]] = None,
    candidate_employee_ids: Optional[List[int]] = None,
) -> Tuple[bool, str]:
    """
    Authoritative sequential distance-wave dispatch engine (Phase 1):
    1. Locks ServiceRequest row with select_for_update inside transaction.atomic()
    2. Sweeps and expires any overdue offers for this job (Lazy Reconciliation)
    3. Checks if an active unexpired wave is currently pending (Idempotency & Same-Wave Stability)
    4. Evaluates eligible candidates in 6 sequential waves (0-1km, 1-2km, 2-5km, 5-10km, 10-15km, 15-20km)
    5. Picks the lowest non-empty wave (empty waves are skipped immediately without delay)
    6. Generates a unique UUID wave_id and synchronized timestamps (offered_at = now, expires_at = now + 2 min)
    7. Atomically creates WorkforceJobOffer for ALL candidates in the wave
    8. Falls back to Admin escalation when all 20 km waves are exhausted
    """
    job_id = job_id_or_obj.pk if hasattr(job_id_or_obj, "pk") else job_id_or_obj

    job_obj = ServiceRequest.objects.filter(pk=job_id).first()
    if not job_obj:
        return False, "Job not found."

    if job_obj.status in ["completed", "cancelled"]:
        return False, f"Job #{job_id} is {job_obj.status} and cannot be dispatched."

    if job_obj.status in ["accepted", "on_the_way", "en_route", "arrived", "in_progress", "proof_submitted", "service_completed", "payment_pending", "cash_pending"] and job_obj.assigned_employee:
        return False, f"Job #{job_id} is already accepted and in progress with Employee #{job_obj.assigned_employee_id}."

    now = timezone.now()

    # Step 1: Lazy reconciliation of expired offers for this job
    sweep_job_expired_offers(job_obj)

    # Step 2: Idempotency check: Is there an active unexpired wave running for this job?
    active_offers = list(
        WorkforceJobOffer.objects.filter(
            job=job_obj,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        )
    )

    if active_offers:
        first_offer = active_offers[0]
        current_wave_num = first_offer.wave_number
        current_wave_id = first_offer.wave_id
        current_expires_at = first_offer.expires_at

        # Check if any newly eligible technicians within this active wave boundary need to be added
        already_offered_ids = set(o.employee_id for o in active_offers)
        declined_or_past_ids = set(
            WorkforceJobOffer.objects.filter(
                job=job_obj,
                status__in=["DECLINED", "REJECTED", "ACCEPTED", "SUPERSEDED_BY_ACCEPTANCE"]
            ).values_list("employee_id", flat=True)
        )
        exclude_joining_ids = list(already_offered_ids | declined_or_past_ids | set(exclude_employee_ids or []))

        candidates = get_eligible_candidates(
            job_obj,
            max_gps_age_seconds=max_gps_age_seconds,
            radius_km=MAX_DISPATCH_RADIUS_KM,
            exclude_employee_ids=exclude_joining_ids,
            check_workload=False,
        )
        new_wave_candidates = [c for c in candidates if c.get("wave_number") == current_wave_num]

        if new_wave_candidates:
            with transaction.atomic():
                locked_job = ServiceRequest.objects.select_for_update().filter(pk=job_id).first()
                if not locked_job or locked_job.status in ["completed", "cancelled"]:
                    return False, f"Job #{job_id} is {locked_job.status if locked_job else 'missing'}."
                if locked_job.assigned_employee and locked_job.status not in ["unassigned", "redispatching"]:
                    return False, f"Job #{job_id} already assigned."

                for cand in new_wave_candidates:
                    emp_cand = cand["employee"]
                    if WorkforceJobOffer.objects.filter(job=locked_job, employee=emp_cand, status=WorkforceJobOffer.Status.OFFERED, expires_at__gt=now).exists():
                        continue
                    if WorkforceJobOffer.objects.filter(job=locked_job, employee=emp_cand, status__in=["DECLINED", "REJECTED"]).exists():
                        continue

                    offer = WorkforceJobOffer.objects.create(
                        job=locked_job,
                        employee=emp_cand,
                        wave_id=current_wave_id,
                        wave_number=current_wave_num,
                        status=WorkforceJobOffer.Status.OFFERED,
                        expires_at=current_expires_at,
                    )
                    WorkforceEventLog.objects.create(
                        user=emp_cand.user,
                        event_type="JOB_OFFERED",
                        payload={
                            "offer_id": offer.id,
                            "job_id": locked_job.id,
                            "wave_id": str(current_wave_id),
                            "wave_number": current_wave_num,
                            "expires_at": current_expires_at.isoformat(),
                            "joined_active_wave": True,
                        }
                    )
                    service_display = locked_job.issue_title or locked_job.service_category or "Service Request"
                    WorkforceNotification.objects.create(
                        recipient=emp_cand.user,
                        title=f"New Job Offer: {service_display}",
                        message=f"Wave {current_wave_num}: Job #{locked_job.id} offered to you ({cand.get('distance_km', 0.0):.1f} km away). Expires shortly.",
                        notification_type="JOB_OFFER",
                        company=locked_job.company,
                        related_object_id=str(offer.id),
                    )

            logger.info(
                f"[DISPATCH_WAVE_JOINED] Added {len(new_wave_candidates)} newly eligible technician(s) "
                f"to active Wave {current_wave_num} for Job #{job_id}."
            )
            return True, f"Added {len(new_wave_candidates)} technician(s) to active Wave {current_wave_num}."

        logger.info(
            f"[DISPATCH_WAVE_ACTIVE] Job #{job_id} already has active Wave {current_wave_num} "
            f"with {len(active_offers)} pending offer(s)."
        )
        return True, f"Active Wave {current_wave_num} already pending ({len(active_offers)} offers)."

    # Step 3: Validate customer booking coordinates
    is_valid_coords, cust_lat, cust_lon, coord_err = validate_coordinates(job_obj.latitude, job_obj.longitude)
    if not is_valid_coords:
        if job_obj.status not in ["unassigned", "redispatching"]:
            job_obj.status = "unassigned"
            job_obj.save(update_fields=["status", "updated_at"])
        logger.info(
            f"[DISPATCH_PENDING_GPS] Job #{job_id} ({job_obj.request_id}) coordinates missing or invalid ({coord_err}). Waiting for valid GPS fix."
        )
        return False, "Customer booking is missing valid GPS coordinates."

    WorkforceEventLog.objects.create(
        event_type="DISPATCH_STARTED",
        payload={"job_id": job_obj.id, "service": job_obj.service_category}
    )

    # Step 4: Find eligible candidate technicians across 0 to 20 km (OUTSIDE TRANSACTION)
    auto_exclude_ids = set(exclude_employee_ids or [])
    past_offer_ids = set(
        WorkforceJobOffer.objects.filter(
            job=job_obj,
            status__in=["DECLINED", "REJECTED", "EXPIRED", "ACCEPTED", "SUPERSEDED_BY_ACCEPTANCE"]
        ).values_list("employee_id", flat=True)
    )
    all_excluded = list(auto_exclude_ids | past_offer_ids)

    candidates = get_eligible_candidates(
        job_obj,
        max_gps_age_seconds=max_gps_age_seconds,
        radius_km=MAX_DISPATCH_RADIUS_KM,
        exclude_employee_ids=all_excluded,
        candidate_employee_ids=candidate_employee_ids,
        check_workload=False,
    )

    WorkforceEventLog.objects.create(
        event_type="CANDIDATES_EVALUATED",
        payload={"job_id": job_obj.id, "eligible_count": len(candidates)}
    )

    # Step 5: Group candidates by sequential distance wave (1 to 6, up to 20 km)
    wave_groups: Dict[int, List[Dict[str, Any]]] = {w: [] for w in range(1, 7)}
    for c in candidates:
        w_num = c.get("wave_number")
        if w_num and 1 <= w_num <= 6:
            wave_groups[w_num].append(c)

    # Step 6: Select lowest non-empty wave (skip empty waves immediately)
    target_wave_number = None
    target_wave_candidates = []
    for w_idx in range(1, 7):
        if wave_groups[w_idx]:
            target_wave_number = w_idx
            target_wave_candidates = wave_groups[w_idx]
            break

    # Step 7: If all 6 waves are exhausted, escalate to Admin fallback
    if not target_wave_number or not target_wave_candidates:
        if job_obj.status != "unassigned" or job_obj.assigned_employee is not None:
            job_obj.status = "unassigned"
            job_obj.assigned_employee = None
            job_obj.save(update_fields=["status", "assigned_employee"])

        WorkforceEventLog.objects.create(
            event_type="DISPATCH_ADMIN_FALLBACK",
            payload={"job_id": job_obj.id, "reason": "ALL_WAVES_EXHAUSTED", "candidates_considered": len(candidates)}
        )

        admin_user = None
        if job_obj.company:
            admin_user = get_user_model().objects.filter(
                Q(role__in=["admin", "manager"]) | Q(is_staff=True),
                company=job_obj.company
            ).first()
        if not admin_user:
            admin_user = get_user_model().objects.filter(is_superuser=True).first()

        if admin_user:
            service_name = job_obj.issue_title or job_obj.service_category or "Service"
            WorkforceNotification.objects.create(
                recipient=admin_user,
                title="Automatic Dispatch: Awaiting Technician",
                message=f"No eligible nearby technician available within 20 km for Job #{job_obj.id} ({service_name}). Job escalated to Admin dispatch.",
                notification_type="DISPATCH_UNASSIGNED",
                company=job_obj.company,
                related_object_id=str(job_obj.id),
            )
        logger.info(f"[DISPATCH_NO_CANDIDATES] Job #{job_obj.id} -> No eligible candidates found in Waves 1-6. Escalated to Admin.")
        return False, "No eligible technicians available for automatic dispatch within 20 km. Job escalated to Admin dispatch."

    # Step 8: Fast Atomic Offer Creation (Transaction held ONLY for offer inserts: < 20 ms)
    wave_uuid = uuid.uuid4()
    wave_created_at = timezone.now()
    wave_expires_at = wave_created_at + timedelta(minutes=DEFAULT_OFFER_DURATION_MINUTES)
    wave_label = f"Wave {target_wave_number}"

    created_offers = []
    with transaction.atomic():
        locked_job = ServiceRequest.objects.select_for_update().filter(pk=job_id).first()
        if not locked_job or locked_job.status in ["completed", "cancelled"]:
            return False, f"Job #{job_id} is {locked_job.status if locked_job else 'missing'}."

        if locked_job.assigned_employee and locked_job.status not in ["unassigned", "redispatching"]:
            return False, f"Job #{job_id} already assigned to Employee #{locked_job.assigned_employee_id}."

        if WorkforceJobOffer.objects.filter(job=locked_job, status=WorkforceJobOffer.Status.OFFERED, expires_at__gt=wave_created_at).exists():
            return True, f"Active wave already pending for Job #{job_id}."

        # Keep ServiceRequest in unassigned status until an employee accepts
        if locked_job.status in ["draft", "new_request", "received", "confirmed"]:
            apply_transition(locked_job, "unassigned")

        for cand in target_wave_candidates:
            cand_emp = cand["employee"]
            cand_dist = cand["distance_km"]
            cand_score = cand["score"]

            offer = WorkforceJobOffer.objects.create(
                job=locked_job,
                employee=cand_emp,
                status=WorkforceJobOffer.Status.OFFERED,
                wave_id=wave_uuid,
                wave_number=target_wave_number,
                rank_score=cand_score,
                offered_at=wave_created_at,
                expires_at=wave_expires_at,
            )
            created_offers.append(offer)

            WorkforceEventLog.objects.create(
                user=cand_emp.user,
                event_type="OFFER_CREATED",
                payload={
                    "job_id": locked_job.id,
                    "offer_id": offer.id,
                    "employee_id": cand_emp.id,
                    "wave_id": str(wave_uuid),
                    "wave_number": target_wave_number,
                    "distance_km": round(cand_dist, 3),
                    "expires_at": wave_expires_at.isoformat(),
                }
            )

            loc_str = f" at {locked_job.address}" if locked_job.address else ""
            req_id_str = f" ({locked_job.request_id})" if locked_job.request_id else f" #{locked_job.id}"
            service_label = locked_job.issue_title or locked_job.service_category or "Service Request"
            expiry_str = wave_expires_at.strftime("%H:%M:%S UTC")

            WorkforceNotification.objects.create(
                recipient=cand_emp.user,
                title="New Job Offer Available!",
                message=f"You have a new job offer for '{service_label}'{req_id_str}{loc_str} ({cand_dist:.1f} km away via {wave_label}). Expiry: {expiry_str}. Open your dashboard to review.",
                notification_type="JOB_OFFER",
                company=locked_job.company,
                related_object_id=str(locked_job.id),
            )

    emp_summary = ", ".join([f"EMP-{c['employee'].id} ({c['distance_km']:.2f}km)" for c in target_wave_candidates])
    logger.info(
        f"[DISPATCH_DECISION] Job #{job_obj.id} dispatched to Wave {target_wave_number} "
        f"(UUID: {wave_uuid}, expires: {wave_expires_at.strftime('%H:%M:%S')}) -> Offers: [{emp_summary}]"
    )
    return True, f"Job #{job_obj.id} dispatched to Wave {target_wave_number} ({len(created_offers)} technicians offered)."


def dispatch_next_candidate(job_id_or_obj, exclude_employee_ids: Optional[List[int]] = None) -> Tuple[bool, str]:
    """
    Triggered when a wave expires or all offers in a wave are declined:
    Advances dispatch through canonical reconciliation, excluding past candidates.
    """
    job_id = job_id_or_obj.pk if hasattr(job_id_or_obj, "pk") else job_id_or_obj
    past_candidates = list(
        WorkforceJobOffer.objects.filter(
            job_id=job_id,
            status__in=["DECLINED", "REJECTED", "EXPIRED", "SUPERSEDED_BY_ACCEPTANCE"]
        ).values_list("employee_id", flat=True)
    )
    if exclude_employee_ids is None:
        exclude_employee_ids = []
    combined_excludes = list(set(exclude_employee_ids) | set(past_candidates))
    logger.info(f"[DISPATCH_FALLBACK] Triggering next wave dispatch for Job #{job_id}, excluding {len(combined_excludes)} past candidates.")
    return reconcile_booking_for_dispatch(job_id, exclude_employee_ids=combined_excludes)


def expire_and_reassign_offers(company_id=None, limit: int = 50) -> int:
    """
    Scans for expired job offers in OFFERED state, marks them EXPIRED,
    and automatically triggers next wave dispatch for jobs whose wave has completed.
    Returns the count of expired offers handled.
    """
    now = timezone.now()
    qs = WorkforceJobOffer.objects.filter(
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__lte=now,
    )
    if company_id:
        qs = qs.filter(job__company_id=company_id)
    expired_offers = list(qs.select_related("job").order_by("-expires_at")[:limit])

    if not expired_offers:
        return 0

    expired_offer_pks = [o.pk for o in expired_offers]
    WorkforceJobOffer.objects.filter(pk__in=expired_offer_pks).update(status=WorkforceJobOffer.Status.EXPIRED)
    count = len(expired_offer_pks)
    affected_job_ids = {o.job_id for o in expired_offers}

    logger.info(f"[DISPATCH_SWEEP_EXPIRED] Marked {count} overdue offers as EXPIRED across {len(affected_job_ids)} jobs.")

    # For each affected job, check if any active offers remain; if not, trigger next wave dispatch via canonical reconciliation
    for j_id in affected_job_ids:
        has_active_peers = WorkforceJobOffer.objects.filter(
            job_id=j_id,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        ).exists()
        if not has_active_peers:
            logger.info(f"[DISPATCH_WAVE_EXPIRED] All offers for Job #{j_id} expired. Advancing to next wave via canonical reconciliation.")
            dispatch_next_candidate(j_id)

    return count


def dispatch_pending_jobs(company_id=None, limit: int = 50) -> Dict[str, Any]:
    """
    Core cross-application reconciliation function:
    1. Sweeps and reassigns expired offers.
    2. Discovers all dispatchable jobs in the database.
    3. Filters out jobs that already have an active exclusive offer.
    4. Evaluates proximity and dispatches pending jobs.
    """
    # 1. Sweep expired offers first
    expired_count = expire_and_reassign_offers(company_id=company_id, limit=limit)

    now = timezone.now()
    active_offered_ids = set(
        WorkforceJobOffer.objects.filter(
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        ).values_list("job_id", flat=True)
    )

    scope_q = get_booking_discovery_scope(company_id)
    qs = ServiceRequest.objects.filter(
        scope_q,
        status__in=DISPATCHABLE_STATUSES,
        assigned_employee__isnull=True,
        latitude__isnull=False,
        longitude__isnull=False,
    ).exclude(id__in=active_offered_ids)

    pending_jobs = list(qs.order_by("-created_at")[:limit])

    results = {
        "expired_offers_swept": expired_count,
        "pending_jobs_found": len(pending_jobs),
        "dispatched_count": 0,
        "unassigned_count": 0,
        "details": [],
    }

    for job in pending_jobs:
        logger.info(f"[DISPATCH_JOB_FOUND] Reconciling pending Job #{job.id} ({job.request_id}, status={job.status}).")
        success, msg = reconcile_booking_for_dispatch(job)
        results["details"].append({"job_id": job.id, "success": success, "message": msg})
        if success:
            results["dispatched_count"] += 1
        else:
            results["unassigned_count"] += 1

    return results


def reconsider_jobs_for_employee(employee_or_id) -> int:
    """
    Triggered when an employee comes online or transmits fresh GPS coordinates.
    Finds all pending dispatchable jobs within the employee's company scope
    — including Marketplace bookings (company_id IS NULL) — and evaluates
    dispatch via reconcile_booking_for_dispatch().

    Marketplace bookings (company_id=NULL) are included because they are
    eligible for any active vendor employee, consistent with get_eligible_candidates().
    The actual eligibility filter (GPS proximity, skill match, 9-gate) inside
    dispatch_job() provides the precise restriction.
    """
    emp_id = employee_or_id.pk if hasattr(employee_or_id, "pk") else employee_or_id
    emp = Employee.objects.filter(pk=emp_id).first()
    if not emp or not emp.is_active or not emp.is_online:
        return 0

    now = timezone.now()
    # If employee already has an active unexpired offer, skip search
    has_active_offer = WorkforceJobOffer.objects.filter(
        employee_id=emp.id,
        status=WorkforceJobOffer.Status.OFFERED,
        expires_at__gt=now,
    ).exists()
    if has_active_offer:
        return 0

    cutoff = now - timedelta(days=2)

    # Exclude jobs where THIS employee already has an active offer or has DECLINED/REJECTED.
    emp_active_offered_ids = set(
        WorkforceJobOffer.objects.filter(
            employee_id=emp.id,
            status=WorkforceJobOffer.Status.OFFERED,
            expires_at__gt=now,
        ).values_list("job_id", flat=True)
    )
    declined_ids = set(
        WorkforceJobOffer.objects.filter(
            employee_id=emp.id,
            status__in=["DECLINED", "REJECTED"],
        ).values_list("job_id", flat=True)
    )
    excluded_job_ids = list(emp_active_offered_ids | declined_ids)

    # Determine employee's domains from approved services and service_roles
    emp_services = []
    bank_details = emp.bank_details or {}
    onboarding = bank_details.get("onboarding", {})
    for s in onboarding.get("services", []):
        if isinstance(s, dict):
            if s.get("name"):
                emp_services.append(str(s["name"]))
            if s.get("category"):
                emp_services.append(str(s["category"]))
    if hasattr(emp, "service_roles") and isinstance(emp.service_roles, list):
        for sr in emp.service_roles:
            if sr:
                emp_services.append(str(sr))

    # Scope: Company-scoped bookings for this employee's company + Marketplace bookings (company_id=NULL)
    scope_q = get_booking_discovery_scope(emp.company_id)

    pending_jobs = list(
        ServiceRequest.objects.filter(
            scope_q,
            status__in=DISPATCHABLE_STATUSES,
            assigned_employee__isnull=True,
            latitude__isnull=False,
            longitude__isnull=False,
            created_at__gte=cutoff,
        ).exclude(id__in=excluded_job_ids).order_by("-id")[:30]
    )

    dispatched_count = 0
    for job in pending_jobs:
        logger.info(f"[DISPATCH_GPS_TRIGGER] Fresh GPS / presence for Employee #{emp.id} triggered evaluation for Job #{job.id}.")
        success, msg = reconcile_booking_for_dispatch(job)
        if success:
            dispatched_count += 1
            # If this employee received an offer from this dispatch, stop immediately
            if WorkforceJobOffer.objects.filter(
                job=job,
                employee=emp,
                status=WorkforceJobOffer.Status.OFFERED,
                expires_at__gt=timezone.now(),
            ).exists():
                break

    return dispatched_count


def reconcile_booking_for_dispatch(
    job_or_id,
    max_gps_age_seconds: int = MAX_GPS_AGE_SECONDS,
    exclude_employee_ids: Optional[List[int]] = None,
    use_redis_geo: bool = True,
) -> Tuple[bool, str]:
    """
    Single authoritative entry point for all dispatch triggers.

    Use this function from every caller:
      - New booking created (ServiceRequest.save via transaction.on_commit)
      - Employee becomes available (presence toggle)
      - Employee GPS becomes eligible (GPS update handler)
      - Periodic reconciliation sweep (dispatch_pending_jobs)
      - Recovery after missed events (SSE stream, management command)
      - Manual retry (admin override)

    Invariant checks performed before calling dispatch_job():
      1. Booking exists and is not already completed/cancelled.
      2. Booking is not already assigned to an employee.
      3. Booking has valid coordinates (lat/lon) required for proximity dispatch.
      4. Booking status is within DISPATCHABLE_STATUSES.
      5. No active unexpired offer already exists (idempotency — dispatch_job checks this).

    If the booking does not yet have valid coordinates:
      - It remains in its dispatchable status.
      - We log DISPATCH_PENDING_GPS.
      - We NEVER fabricate or guess coordinates based on address keywords or city centers.
      - When valid GPS becomes available later, reconciliation will dispatch normally.

    Returns (success: bool, message: str) matching dispatch_job() contract.
    """
    from service_requests.models import suppress_dispatch_hook

    with suppress_dispatch_hook():
        job_id = job_or_id.pk if hasattr(job_or_id, "pk") else job_or_id

        job = ServiceRequest.objects.filter(pk=job_id).first()
        if not job:
            logger.warning(f"[RECONCILE_SKIP] Job #{job_id} not found.")
            return False, f"Job #{job_id} not found."

        if job.status in ["completed", "cancelled"]:
            logger.debug(f"[RECONCILE_SKIP] Job #{job.id} is terminal ({job.status}), skipping dispatch.")
            return False, f"Job #{job.id} is {job.status} and does not require dispatch."

        if job.status not in DISPATCHABLE_STATUSES:
            logger.debug(
                f"[RECONCILE_SKIP] Job #{job.id} status='{job.status}' is not in DISPATCHABLE_STATUSES, skipping."
            )
            return False, f"Job #{job.id} status '{job.status}' is not dispatchable."

        if job.assigned_employee_id and job.status not in ["unassigned", "redispatching"]:
            logger.debug(f"[RECONCILE_SKIP] Job #{job.id} already has assigned employee #{job.assigned_employee_id}.")
            return False, f"Job #{job.id} is already assigned to Employee #{job.assigned_employee_id}."

        is_valid_coords, cust_lat, cust_lon, coord_err = validate_coordinates(job.latitude, job.longitude)
        if not is_valid_coords:
            # If coordinates are missing on the job, try extracting from authenticated customer's last known location
            if job.customer:
                cust_loc = getattr(job.customer, "last_known_location", None) or {}
                c_lat = cust_loc.get("latitude") if cust_loc.get("latitude") is not None else cust_loc.get("lat")
                c_lon = cust_loc.get("longitude") if cust_loc.get("longitude") is not None else (cust_loc.get("lng") or cust_loc.get("lon"))
                is_c_valid, c_lat_f, c_lon_f, _ = validate_coordinates(c_lat, c_lon)
                if is_c_valid:
                    job.latitude = c_lat_f
                    job.longitude = c_lon_f
                    job.save(update_fields=["latitude", "longitude", "updated_at"], skip_dispatch=True)
                    is_valid_coords = True

            if not is_valid_coords:
                logger.info(
                    f"[DISPATCH_PENDING_GPS] Job #{job.id} ({job.request_id}) coordinates missing or invalid ({coord_err}). "
                    f"Booking remains dispatchable ({job.status}) awaiting valid GPS fix."
                )
                return False, "Customer booking is missing valid GPS coordinates."

        candidate_ids = None
        if use_redis_geo and is_valid_coords:
            try:
                from workforce_api.services.redis_dispatch import find_nearby_technician_candidates
                geo_candidates = find_nearby_technician_candidates(
                    latitude=cust_lat,
                    longitude=cust_lon,
                    radius_km=MAX_DISPATCH_RADIUS_KM,
                    max_age_seconds=max_gps_age_seconds,
                )
                if geo_candidates is not None:
                    candidate_ids = geo_candidates
            except Exception as geo_err:
                logger.debug(f"[DISPATCH_REDIS_GEO_ERR] {geo_err}")
                candidate_ids = None

        logger.info(
            f"[RECONCILE_DISPATCH] Evaluating Job #{job.id} ({job.request_id}, "
            f"status={job.status}, company_id={job.company_id}, coords=({job.latitude}, {job.longitude}), "
            f"redis_geo_candidates={len(candidate_ids) if candidate_ids is not None else 'DB_FALLBACK'})."
        )
        return dispatch_job(
            job,
            max_gps_age_seconds=max_gps_age_seconds,
            exclude_employee_ids=exclude_employee_ids,
            candidate_employee_ids=candidate_ids,
        )
