"""
workforce_api/services/vendor_network.py

Core domain services for Technician-Vendor Network:
1. VendorDiscoveryEngine (extensible AND/OR attribute matching over candidate technicians)
2. VendorInvitationService (invitation lifecycle, signup backfill, accept/reject state machines)
3. VendorRelationshipService (status transitions, scope management, security isolation)
"""

import logging
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.models import User
from companies.models import Company
from employees.models import Employee
from workforce_api.models import (
    CriteriaTerm,
    VendorCriteria,
    VendorInvitation,
    VendorTechnicianRelationship,
    VendorRelievingRequest,
    WalletAccount,
    WorkforceEmployeeSkill,
    WorkforceNotification,
    WorkforceScorecard,
    WorkforceSkill,
)

logger = logging.getLogger(__name__)


class VendorDiscoveryEngine:
    """
    Evaluates criteria sets across the technician base and returns ranked matches.
    Criteria terms are grouped by group_id:
    - Terms sharing the same group_id are OR'd together.
    - Groups themselves are AND'd together.
    """

    @classmethod
    def evaluate_candidates(
        cls,
        vendor: Company,
        terms: list[dict] = None,
        criteria: VendorCriteria = None,
        limit: int = 50,
        search_query: str = None,
    ) -> list[dict]:
        """
        Evaluate candidate technicians against criteria terms or a saved VendorCriteria.
        Returns a list of technician summary dictionaries with match score and relationship status.
        """
        parsed_terms = []
        if criteria:
            for term in criteria.terms.all():
                parsed_terms.append({
                    "attribute_type": term.attribute_type,
                    "operator": term.operator,
                    "value": term.value,
                    "group_id": term.group_id,
                })
        elif terms:
            parsed_terms = terms

        # Fetch active candidate employees
        employees_qs = Employee.objects.select_related("user", "company").all()
        if search_query:
            employees_qs = employees_qs.filter(
                Q(user__first_name__icontains=search_query)
                | Q(user__last_name__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(phone__icontains=search_query)
                | Q(title__icontains=search_query)
            )

        # Pre-fetch skills, scorecards, relationships, and invitations for efficiency
        employee_ids = list(employees_qs.values_list("id", flat=True))
        if not employee_ids:
            return []

        skills_by_emp = {}
        for es in WorkforceEmployeeSkill.objects.filter(employee_id__in=employee_ids).select_related("skill"):
            skills_by_emp.setdefault(es.employee_id, []).append({
                "name": es.skill.name,
                "category": es.skill.category,
                "proficiency": es.proficiency_level,
                "is_verified": es.is_verified,
            })

        scorecard_by_emp = {
            sc.employee_id: sc
            for sc in WorkforceScorecard.objects.filter(employee_id__in=employee_ids)
        }

        # Existing relationships with this vendor
        # Existing relationships with THIS vendor
        relationships_by_emp = {
            rel.technician_id: rel
            for rel in VendorTechnicianRelationship.objects.filter(vendor=vendor, technician_id__in=employee_ids)
        }

        # Active relationships with ANY vendor (to enforce exclusivity / identify assigned workers)
        all_active_rels_by_emp = {
            rel.technician_id: rel
            for rel in VendorTechnicianRelationship.objects.filter(
                technician_id__in=employee_ids,
                status=VendorTechnicianRelationship.Status.ACTIVE,
            ).select_related("vendor")
        }

        # Existing pending invitations from this vendor
        pending_invitations_by_emp = {
            inv.technician_id: inv
            for inv in VendorInvitation.objects.filter(
                vendor=vendor,
                technician_id__in=employee_ids,
                status=VendorInvitation.Status.PENDING,
            )
        }

        # Group terms by group_id
        term_groups = {}
        for t in parsed_terms:
            gid = t.get("group_id", 1)
            term_groups.setdefault(gid, []).append(t)

        results = []
        for emp in employees_qs:
            emp_skills = skills_by_emp.get(emp.id, [])
            emp_skill_names = {s["name"].lower() for s in emp_skills}
            # Also support legacy service_roles JSON field
            if isinstance(emp.service_roles, list):
                emp_skill_names.update(str(r).lower() for r in emp.service_roles)

            scorecard = scorecard_by_emp.get(emp.id)
            avg_rating = float(scorecard.average_rating) if scorecard else 0.0
            rating_count = scorecard.rating_count if scorecard else 0
            tier = scorecard.tier if scorecard else "UNRATED"

            # Evaluate AND/OR expression groups
            matches_all_groups = True
            matched_term_count = 0
            total_terms = max(1, len(parsed_terms))

            for gid, g_terms in term_groups.items():
                group_matched = False
                for term in g_terms:
                    attr = term.get("attribute_type")
                    op = term.get("operator", "EQUALS")
                    val = term.get("value")

                    term_match = cls._evaluate_single_term(
                        attr=attr,
                        op=op,
                        val=val,
                        emp=emp,
                        emp_skill_names=emp_skill_names,
                        avg_rating=avg_rating,
                    )
                    if term_match:
                        group_matched = True
                        matched_term_count += 1
                
                if not group_matched and g_terms:
                    matches_all_groups = False
                    break

            if parsed_terms and not matches_all_groups:
                continue

            # Determine connection status with this vendor vs other vendors
            existing_rel = relationships_by_emp.get(emp.id)
            active_other_rel = all_active_rels_by_emp.get(emp.id)
            pending_inv = pending_invitations_by_emp.get(emp.id)

            assigned_vendor_name = None
            if existing_rel and existing_rel.status == VendorTechnicianRelationship.Status.ACTIVE:
                network_status = "ACTIVE"
                rel_id = existing_rel.id
            elif existing_rel and existing_rel.status == VendorTechnicianRelationship.Status.SUSPENDED:
                network_status = "SUSPENDED"
                rel_id = existing_rel.id
            elif active_other_rel and active_other_rel.vendor_id != vendor.id:
                network_status = "ASSIGNED_OTHER_VENDOR"
                rel_id = None
                assigned_vendor_name = getattr(active_other_rel.vendor, "company_name", getattr(active_other_rel.vendor, "name", "Another Vendor"))
            elif pending_inv:
                network_status = "INVITATION_PENDING"
                rel_id = None
            elif existing_rel and existing_rel.status == VendorTechnicianRelationship.Status.TERMINATED:
                network_status = "RELIEVED"
                rel_id = existing_rel.id
            else:
                network_status = "NOT_CONNECTED"
                rel_id = None

            # Calculate match percentage (100% if no criteria specified, or ratio of matched groups)
            match_score = int(round((matched_term_count / total_terms) * 100)) if parsed_terms else 100

            full_name = f"{emp.user.first_name} {emp.user.last_name}".strip() or emp.user.username
            results.append({
                "technician_id": emp.id,
                "user_id": emp.user_id,
                "name": full_name,
                "email": emp.user.email,
                "phone": emp.phone or "",
                "title": emp.title or "Field Technician",
                "state": emp.state or "",
                "country": emp.country or "",
                "skills": [s["name"] for s in emp_skills] or (emp.service_roles if isinstance(emp.service_roles, list) else []),
                "average_rating": avg_rating,
                "rating_count": rating_count,
                "scorecard_tier": tier,
                "hourly_rate": float(emp.hourly_rate or 0),
                "is_online": emp.is_online,
                "current_availability": emp.current_availability,
                "network_status": network_status,
                "assigned_vendor_name": assigned_vendor_name,
                "relationship_id": rel_id,
                "match_score": match_score,
            })

        # Sort results: highest match score first, then rating, then name
        results.sort(key=lambda x: (-x["match_score"], -x["average_rating"], x["name"]))
        return results[:limit]

    @classmethod
    def _evaluate_single_term(cls, attr: str, op: str, val, emp: Employee, emp_skill_names: set, avg_rating: float) -> bool:
        if attr == CriteriaTerm.AttributeType.SKILL:
            target_skills = [s.lower() for s in (val if isinstance(val, list) else [str(val)])]
            if op in ("IN", "EQUALS"):
                return any(ts in emp_skill_names for ts in target_skills)
            elif op == "CONTAINS":
                return any(any(ts in s for s in emp_skill_names) for ts in target_skills)

        elif attr == CriteriaTerm.AttributeType.LOCATION:
            loc_str = str(val).lower()
            emp_loc = f"{emp.state or ''} {emp.country or ''} {emp.title or ''}".lower()
            if op in ("EQUALS", "IN", "CONTAINS"):
                return loc_str in emp_loc or any(p.lower() in emp_loc for p in (val if isinstance(val, list) else [str(val)]))

        elif attr == CriteriaTerm.AttributeType.MIN_RATING:
            try:
                min_r = float(val)
                return avg_rating >= min_r
            except (ValueError, TypeError):
                return True

        elif attr == CriteriaTerm.AttributeType.EXPERIENCE_YEARS:
            try:
                # Approximate experience from hire_date if present
                if emp.hire_date:
                    years = (timezone.now().date() - emp.hire_date).days / 365.25
                else:
                    years = 1.0
                target_years = float(val)
                if op == "GTE":
                    return years >= target_years
                elif op == "LTE":
                    return years <= target_years
                return True
            except (ValueError, TypeError):
                return True

        elif attr == CriteriaTerm.AttributeType.AVAILABILITY:
            target_avail = str(val).lower()
            return emp.current_availability.lower() == target_avail

        return True


class VendorInvitationService:
    """
    Manages invitation generation, idempotency, backfill on signup, and accept/reject decisions.
    """

    @classmethod
    def create_invitation(
        cls,
        vendor: Company,
        invited_email: str,
        technician: Employee = None,
        channel: str = VendorInvitation.Channel.DIRECT_EMAIL,
        message: str = "",
        criteria: VendorCriteria = None,
        expiry_days: int = 14,
        actor: User = None,
    ) -> VendorInvitation:
        """
        Creates or updates a pending invitation from vendor to an email / technician.
        """
        clean_email = invited_email.strip().lower()
        if not clean_email:
            raise ValidationError("A valid invited email address is required.")

        # Resolve technician by email if not supplied
        if not technician:
            user_match = User.objects.filter(email__iexact=clean_email).first()
            if user_match and hasattr(user_match, "employee_profile"):
                technician = user_match.employee_profile

        # Check if already an active member
        if technician:
            existing_rel = VendorTechnicianRelationship.objects.filter(
                vendor=vendor,
                technician=technician,
            ).first()
            if existing_rel and existing_rel.status == VendorTechnicianRelationship.Status.ACTIVE:
                raise ValidationError(f"{technician.user.get_full_name() or clean_email} is already an ACTIVE member of your network.")

        expires_at = timezone.now() + timedelta(days=expiry_days)

        # Check for existing PENDING invitation from this vendor
        existing_inv = VendorInvitation.objects.filter(
            vendor=vendor,
            invited_email__iexact=clean_email,
            status=VendorInvitation.Status.PENDING,
        ).first()

        if existing_inv:
            # Refresh / update existing pending invitation
            existing_inv.message = message or existing_inv.message
            existing_inv.matched_criteria = criteria or existing_inv.matched_criteria
            existing_inv.expires_at = expires_at
            if technician and not existing_inv.technician:
                existing_inv.technician = technician
            existing_inv.save()
            return existing_inv

        # Create fresh invitation with secure token
        token = secrets.token_urlsafe(32)
        invitation = VendorInvitation.objects.create(
            vendor=vendor,
            technician=technician,
            invited_email=clean_email,
            status=VendorInvitation.Status.PENDING,
            channel=channel,
            matched_criteria=criteria,
            message=message,
            token=token,
            expires_at=expires_at,
        )

        # Notify technician in-app if registered
        if technician and technician.user:
            try:
                vendor_title = getattr(vendor, "company_name", "A Vendor")
                WorkforceNotification.objects.create(
                    recipient=technician.user,
                    company=vendor,
                    title="New Vendor Network Invitation",
                    message=f"{vendor_title} has invited you to join their technician network.",
                    notification_type="VENDOR_INVITATION",
                    related_object_id=str(invitation.id),
                )
            except Exception as e:
                logger.warning(f"Failed to create in-app notification: {e}")

        return invitation

    @classmethod
    def backfill_invitations_for_employee(cls, employee: Employee) -> int:
        """
        Sweeps unassigned pending invitations matching the employee's email
        and links them to this employee record upon signup.
        """
        if not employee or not employee.user or not employee.user.email:
            return 0

        email = employee.user.email.strip().lower()
        pending_invs = VendorInvitation.objects.filter(
            invited_email__iexact=email,
            technician__isnull=True,
            status=VendorInvitation.Status.PENDING,
        )
        updated_count = pending_invs.update(technician=employee)
        logger.info(f"Backfilled {updated_count} vendor invitations for technician #{employee.id} ({email})")
        return updated_count

    @classmethod
    def respond_to_invitation(
        cls,
        invitation_id: int,
        employee: Employee,
        decision: str,
        actor: User = None,
    ) -> tuple[VendorInvitation, VendorTechnicianRelationship | None]:
        """
        Technician accepts or rejects an invitation atomically with row locking.
        """
        decision_upper = decision.strip().upper()
        if decision_upper not in ("ACCEPT", "REJECT"):
            raise ValidationError("Decision must be either 'ACCEPT' or 'REJECT'.")

        with transaction.atomic():
            # Query without outer joins on nullable relations to avoid FOR UPDATE postgresql restriction
            invitation = (
                VendorInvitation.objects.select_for_update()
                .filter(id=invitation_id)
                .first()
            )
            if not invitation:
                raise ValidationError("Invitation not found.")

            # Validate ownership
            is_owner = (
                invitation.technician_id == employee.id
                or invitation.invited_email.strip().lower() == employee.user.email.strip().lower()
            )
            if not is_owner:
                raise ValidationError("You do not have permission to respond to this invitation.")

            # Attach technician if not yet linked
            if not invitation.technician:
                invitation.technician = employee

            if invitation.status != VendorInvitation.Status.PENDING:
                raise ValidationError(f"This invitation is already {invitation.status} and cannot be modified.")

            # Check expiration
            if invitation.expires_at and invitation.expires_at < timezone.now():
                invitation.status = VendorInvitation.Status.EXPIRED
                invitation.save(update_fields=["status", "updated_at"])
                raise ValidationError("This invitation has expired.")

            now = timezone.now()
            relationship = None

            if decision_upper == "ACCEPT":
                # Single Active Vendor Exclusivity Check:
                # A technician assigned/active inside a vendor cannot accept an offer from another vendor.
                # To accept, they must first relieve from their current active vendor.
                current_active_rel = (
                    VendorTechnicianRelationship.objects.filter(
                        technician=employee,
                        status=VendorTechnicianRelationship.Status.ACTIVE,
                    )
                    .exclude(vendor=invitation.vendor)
                    .select_related("vendor")
                    .first()
                )
                if current_active_rel:
                    active_vendor_name = getattr(
                        current_active_rel.vendor,
                        "company_name",
                        getattr(current_active_rel.vendor, "name", "your current vendor"),
                    )
                    raise ValidationError(
                        f"You are currently assigned to {active_vendor_name}. "
                        f"You cannot accept an offer from another vendor while actively assigned. "
                        f"Please relieve/leave {active_vendor_name} first before joining a new vendor."
                    )

                invitation.status = VendorInvitation.Status.ACCEPTED
                invitation.responded_at = now
                invitation.save(update_fields=["status", "responded_at", "technician", "updated_at"])

                # Create or reactivate relationship
                rel, created = VendorTechnicianRelationship.objects.get_or_create(
                    vendor=invitation.vendor,
                    technician=employee,
                    defaults={
                        "status": VendorTechnicianRelationship.Status.ACTIVE,
                        "source_invitation": invitation,
                        "engagement_type": VendorTechnicianRelationship.EngagementType.PER_JOB,
                        "payment_model": VendorTechnicianRelationship.PaymentModel.DIRECT_TO_TECHNICIAN,
                        "created_by": actor or employee.user,
                        "started_at": now,
                    },
                )
                if not created:
                    rel.status = VendorTechnicianRelationship.Status.ACTIVE
                    rel.source_invitation = invitation
                    rel.ended_at = None
                    rel.save(update_fields=["status", "source_invitation", "ended_at", "updated_at"])

                relationship = rel

            elif decision_upper == "REJECT":
                invitation.status = VendorInvitation.Status.REJECTED
                invitation.responded_at = now
                invitation.save(update_fields=["status", "responded_at", "technician", "updated_at"])

            return invitation, relationship

    @classmethod
    def cancel_invitation(cls, invitation_id: int, vendor: Company, actor: User = None) -> VendorInvitation:
        """
        Vendor withdraws a pending invitation.
        """
        with transaction.atomic():
            invitation = (
                VendorInvitation.objects.select_for_update()
                .filter(id=invitation_id, vendor=vendor)
                .first()
            )
            if not invitation:
                raise ValidationError("Invitation not found or does not belong to your vendor company.")

            if invitation.status != VendorInvitation.Status.PENDING:
                raise ValidationError(f"Cannot cancel invitation with status {invitation.status}.")

            invitation.status = VendorInvitation.Status.CANCELLED
            invitation.responded_at = timezone.now()
            invitation.save(update_fields=["status", "responded_at", "updated_at"])
            return invitation


class VendorRelationshipService:
    """
    Manages ongoing vendor-technician relationship lifecycle (Suspend, Reactivate, Terminate).
    """

    @classmethod
    def update_status(
        cls,
        relationship_id: int,
        vendor: Company,
        action: str,
        actor: User = None,
    ) -> VendorTechnicianRelationship:
        """
        Vendor updates relationship status (SUSPEND, REACTIVATE, TERMINATE).
        """
        action_upper = action.strip().upper()
        with transaction.atomic():
            rel = (
                VendorTechnicianRelationship.objects.select_for_update()
                .filter(id=relationship_id, vendor=vendor)
                .first()
            )
            if not rel:
                raise ValidationError("Technician relationship not found for your company.")

            now = timezone.now()
            if action_upper == "SUSPEND":
                rel.status = VendorTechnicianRelationship.Status.SUSPENDED
            elif action_upper in ("REACTIVATE", "RESUME", "ACTIVATE"):
                rel.status = VendorTechnicianRelationship.Status.ACTIVE
                rel.ended_at = None
            elif action_upper in ("TERMINATE", "END"):
                rel.status = VendorTechnicianRelationship.Status.TERMINATED
                rel.ended_at = now
            else:
                raise ValidationError(f"Unsupported action '{action}'. Valid actions are SUSPEND, REACTIVATE, TERMINATE.")

            rel.save()
            return rel

    @classmethod
    def leave_vendor(
        cls,
        relationship_id: int,
        employee: Employee,
        actor: User = None,
    ) -> VendorTechnicianRelationship:
        """
        Technician leaves/resigns a vendor relationship from their side.
        """
        with transaction.atomic():
            rel = (
                VendorTechnicianRelationship.objects.select_for_update()
                .filter(id=relationship_id, technician=employee)
                .first()
            )
            if not rel:
                raise ValidationError("Vendor relationship not found for your technician profile.")

            rel.status = VendorTechnicianRelationship.Status.RESIGNED
            rel.ended_at = timezone.now()
            rel.save(update_fields=["status", "ended_at", "updated_at"])

            if employee.company_id == rel.vendor_id:
                employee.company = None
                employee.save(update_fields=["company", "updated_at"])

            # Provision Solo Wallet
            WalletAccount.objects.get_or_create(
                employee=employee,
                account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
            )

            return rel

    @classmethod
    def tie_technician_to_vendor(
        cls,
        employee_id: int,
        vendor_id: int,
        actor: User = None,
        engagement_type: str = VendorTechnicianRelationship.EngagementType.PER_JOB,
        payment_model: str = VendorTechnicianRelationship.PaymentModel.DIRECT_TO_TECHNICIAN,
        notes: str = "",
    ) -> VendorTechnicianRelationship:
        """
        SEVO Platform Admin directly ties/assigns a technician to a vendor company.
        If the technician is currently active with another vendor, terminates the old relationship first.
        """
        with transaction.atomic():
            employee = Employee.objects.select_for_update().filter(id=employee_id).first()
            if not employee:
                raise ValidationError("Employee profile not found.")

            vendor = Company.objects.filter(id=vendor_id).first()
            if not vendor:
                raise ValidationError("Vendor company not found.")

            now = timezone.now()

            # Terminate any existing active relationship with other vendors
            existing_active_rels = VendorTechnicianRelationship.objects.select_for_update().filter(
                technician=employee,
                status=VendorTechnicianRelationship.Status.ACTIVE,
            )
            for old_rel in existing_active_rels:
                if old_rel.vendor_id != vendor.id:
                    old_rel.status = VendorTechnicianRelationship.Status.TERMINATED
                    old_rel.ended_at = now
                    old_rel.save(update_fields=["status", "ended_at", "updated_at"])

            # Create or update relationship with target vendor
            rel, created = VendorTechnicianRelationship.objects.get_or_create(
                vendor=vendor,
                technician=employee,
                defaults={
                    "status": VendorTechnicianRelationship.Status.ACTIVE,
                    "engagement_type": engagement_type,
                    "payment_model": payment_model,
                    "created_by": actor or employee.user,
                    "started_at": now,
                },
            )
            if not created:
                rel.status = VendorTechnicianRelationship.Status.ACTIVE
                rel.ended_at = None
                rel.engagement_type = engagement_type
                rel.payment_model = payment_model
                rel.save()

            return rel

    @classmethod
    def untie_technician(
        cls,
        employee_id: int,
        actor: User = None,
    ) -> list:
        """
        SEVO Platform Admin unties a technician from all vendors, making them a free Solo Worker.
        """
        with transaction.atomic():
            employee = Employee.objects.select_for_update().filter(id=employee_id).first()
            if not employee:
                raise ValidationError("Employee profile not found.")

            now = timezone.now()
            active_rels = list(
                VendorTechnicianRelationship.objects.select_for_update().filter(
                    technician=employee,
                    status=VendorTechnicianRelationship.Status.ACTIVE,
                )
            )
            for rel in active_rels:
                rel.status = VendorTechnicianRelationship.Status.TERMINATED
                rel.ended_at = now
                rel.save(update_fields=["status", "ended_at", "updated_at"])

            if employee.company_id:
                employee.company = None
                employee.save(update_fields=["company", "updated_at"])

            # Provision Solo Wallet
            WalletAccount.objects.get_or_create(
                employee=employee,
                account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
            )

            return active_rels


class VendorRelievingService:
    """
    Formal Multi-Party Resignation & Relieving Lifecycle Service:
    1. submit_resignation (Technician)
    2. vendor_approve_relieving (Vendor Admin verifies job settlements/dues)
    3. sevo_approve_relieving (SEVO Superadmin verifies platform settlements & compliance)
    4. complete_legal_signoff (Bi-lateral signoff -> Finalize RESIGNED status, convert to Solo Worker, provision Solo Wallet)
    """

    @classmethod
    def submit_resignation(
        cls,
        employee: Employee,
        reason_category: str = VendorRelievingRequest.ReasonCategory.TRANSITION_TO_SOLO,
        notes: str = "",
        desired_date = None,
        actor: User = None,
    ) -> VendorRelievingRequest:
        with transaction.atomic():
            rel = (
                VendorTechnicianRelationship.objects.select_for_update()
                .filter(
                    technician=employee,
                    status__in=[
                        VendorTechnicianRelationship.Status.ACTIVE,
                        VendorTechnicianRelationship.Status.RESIGNATION_REQUESTED,
                    ],
                )
                .select_related("vendor")
                .first()
            )
            if not rel:
                raise ValidationError("You do not have an active vendor assignment to resign from.")

            # Update relationship status to indicate resignation is in progress
            rel.status = VendorTechnicianRelationship.Status.RESIGNATION_REQUESTED
            rel.save(update_fields=["status", "updated_at"])

            # Create or update existing pending relieving request
            existing = (
                VendorRelievingRequest.objects.select_for_update()
                .filter(
                    relationship=rel,
                    status__in=[
                        VendorRelievingRequest.Status.REQUESTED,
                        VendorRelievingRequest.Status.VENDOR_APPROVED,
                        VendorRelievingRequest.Status.SEVO_APPROVED,
                    ],
                )
                .first()
            )
            if existing:
                existing.reason_category = reason_category
                existing.resignation_notes = notes
                if desired_date:
                    existing.desired_relieving_date = desired_date
                existing.worker_signoff_ack = True
                existing.worker_signed_at = timezone.now()
                existing.save()
                return existing

            now = timezone.now()
            req = VendorRelievingRequest.objects.create(
                relationship=rel,
                technician=employee,
                vendor=rel.vendor,
                status=VendorRelievingRequest.Status.REQUESTED,
                reason_category=reason_category,
                resignation_notes=notes,
                desired_relieving_date=desired_date or now.date(),
                worker_signoff_ack=True,
                worker_signed_at=now,
            )

            # Notification to vendor admin
            try:
                vendor_admin_users = User.objects.filter(company=rel.vendor, role__in=["admin", "manager"])
                for vuser in vendor_admin_users:
                    WorkforceNotification.objects.create(
                        recipient=vuser,
                        title=f"Resignation Request: {employee.user.get_full_name() or employee.user.username}",
                        message=f"{employee.user.get_full_name()} has submitted a formal resignation request. Reason: {req.get_reason_category_display()}.",
                        notification_type="RELIEVING_REQUESTED",
                        data={"request_id": req.id, "technician_id": employee.id},
                    )
            except Exception:
                pass

            return req

    @classmethod
    def vendor_approve_relieving(
        cls,
        request_id: int,
        vendor: Company,
        settlement_notes: str = "",
        actor: User = None,
    ) -> VendorRelievingRequest:
        with transaction.atomic():
            req = (
                VendorRelievingRequest.objects.select_for_update()
                .filter(id=request_id, vendor=vendor)
                .select_related("relationship", "technician", "vendor")
                .first()
            )
            if not req:
                raise ValidationError("Relieving request not found for your company.")

            if req.status not in (VendorRelievingRequest.Status.REQUESTED, VendorRelievingRequest.Status.VENDOR_APPROVED):
                raise ValidationError(f"Cannot approve request with current status: {req.status}")

            now = timezone.now()
            req.status = VendorRelievingRequest.Status.VENDOR_APPROVED
            req.vendor_approved_by = actor
            req.vendor_approved_at = now
            req.vendor_settlement_notes = settlement_notes
            req.vendor_signoff_ack = True
            req.vendor_signed_at = now
            req.save()

            return req

    @classmethod
    def sevo_approve_relieving(
        cls,
        request_id: int,
        audit_notes: str = "",
        actor: User = None,
    ) -> VendorRelievingRequest:
        """
        SEVO Platform Superadmin verifies general job settlement and compliance check,
        then issues official platform relieving approval.
        """
        with transaction.atomic():
            req = (
                VendorRelievingRequest.objects.select_for_update()
                .filter(id=request_id)
                .select_related("relationship", "technician", "vendor")
                .first()
            )
            if not req:
                raise ValidationError("Relieving request not found.")

            now = timezone.now()
            req.status = VendorRelievingRequest.Status.SEVO_APPROVED
            req.sevo_approved_by = actor
            req.sevo_approved_at = now
            req.sevo_audit_notes = audit_notes
            req.save()

            # Check if both worker & vendor have acknowledged -> finalize completion
            if req.worker_signoff_ack and req.vendor_signoff_ack:
                cls.finalize_relieving(req)

            return req

    @classmethod
    def complete_legal_signoff(
        cls,
        request_id: int,
        actor: User,
        persona: str,
    ) -> VendorRelievingRequest:
        with transaction.atomic():
            req = (
                VendorRelievingRequest.objects.select_for_update()
                .filter(id=request_id)
                .select_related("relationship", "technician", "vendor")
                .first()
            )
            if not req:
                raise ValidationError("Relieving request not found.")

            now = timezone.now()
            if persona == "technician":
                if req.technician.user_id != actor.id:
                    raise ValidationError("Only the assigned technician can sign off.")
                req.worker_signoff_ack = True
                req.worker_signed_at = now
            elif persona == "vendor":
                req.vendor_signoff_ack = True
                req.vendor_signed_at = now

            req.save()

            if req.worker_signoff_ack and req.vendor_signoff_ack and req.sevo_approved_at:
                cls.finalize_relieving(req)

            return req

    @classmethod
    def finalize_relieving(cls, req: VendorRelievingRequest):
        """
        Final transition:
        - Relationship status becomes RESIGNED (NOT Terminated)
        - Ended timestamp recorded
        - Worker is unlinked from vendor (company = None) -> becomes SOLO WORKER
        - Automatically provisions worker's INDIVIDUAL_WORKER wallet
        """
        now = timezone.now()
        req.status = VendorRelievingRequest.Status.COMPLETED
        req.save()

        rel = req.relationship
        rel.status = VendorTechnicianRelationship.Status.RESIGNED
        rel.ended_at = now
        rel.save(update_fields=["status", "ended_at", "updated_at"])

        # Detach worker's company assignment
        emp = req.technician
        if emp.company_id == req.vendor_id:
            emp.company = None
            emp.save(update_fields=["company", "updated_at"])

        # Automatically provision Solo Worker Wallet
        WalletAccount.objects.get_or_create(
            employee=emp,
            account_type=WalletAccount.AccountType.INDIVIDUAL_WORKER,
        )


