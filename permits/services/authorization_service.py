# permits/services/authorization_service.py

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from permits.models.approval_models import PermitApprovalRoleAssignment


class WorkflowAuthorizationService:

    @classmethod
    def ensure_actor_can_decide(cls, *, actor, permit, transition):
        if not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if actor.is_superuser:
            return

        role = transition.role
        today = timezone.localdate()

        # 1. Qualification checks
        cls._ensure_required_qualification(
            actor=actor,
            role=role,
            today=today,
        )

        # 2. Start building assignment queries
        assignments = PermitApprovalRoleAssignment.objects.filter(
            user=actor,
            role=role,
            is_active=True,
        ).filter(
            Q(permit_type__isnull=True)
            | Q(permit_type=permit.permit_type)
        )

        # 3. Department constraint validation
        if role.department_scope == role.ScopeRequirement.REQUIRED:
            if not permit.department_id:
                raise PermissionDenied(
                    "This permit has no originating department."
                )

            assignments = assignments.filter(
                department=permit.department,
            )

        # 4. Unit constraint validation
        if role.unit_scope == role.ScopeRequirement.REQUIRED:
            permit_unit = permit.location_tag.unit if permit.location_tag else None

            if not permit_unit:
                raise PermissionDenied(
                    "The permit equipment location does not resolve to an operational unit."
                )

            assignments = assignments.filter(
                Q(all_units=True)
                | Q(units=permit_unit)
            )

        # 5. Confirm assignment exists
        if not assignments.exists():
            raise PermissionDenied(
                f"You do not hold an active role assignment matching '{role.name}' "
                "for the designated department or unit scope."
            )

    @classmethod
    def _ensure_required_qualification(cls, *, actor, role, today):
        if not role.required_qualification_id:
            return

        qualification_manager = cls._get_actor_qualification_manager(actor)

        if qualification_manager is None:
            raise PermissionDenied(
                "Action blocked: this user has no qualification records configured."
            )

        has_qualification = qualification_manager.filter(
            qualification=role.required_qualification,
            is_active=True,
        ).filter(
            Q(granted_date__isnull=True)
            | Q(granted_date__lte=today)
        ).filter(
            Q(expiry_date__isnull=True)
            | Q(expiry_date__gte=today)
        ).exists()

        if not has_qualification:
            raise PermissionDenied(
                f"Action blocked: A valid '{role.required_qualification.name}' "
                "qualification is required to execute this transition."
            )

    @staticmethod
    def _get_actor_qualification_manager(actor):
        """
        Return the related manager used for user qualification records.

        Expected relation:
            actor.user_qualifications

        If the relation does not exist, return None instead of raising AttributeError.
        """

        qualification_manager = getattr(actor, "user_qualifications", None)

        if qualification_manager is None:
            return None

        if not hasattr(qualification_manager, "filter"):
            return None

        return qualification_manager
