# permits/services/authorization_service.py

from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils import timezone

from permits.models.approval_models import PermitApprovalRoleAssignment


class WorkflowAuthorizationService:
    """
    Authorization service for permit workflow operations.

    Responsibilities:
    - Check whether an actor can perform a workflow transition.
    - Check whether an actor can edit a permit at the current workflow step.
    - Reuse the same role assignment, permit type, department, unit,
      and qualification logic for both decisions and editing.
    """

    @classmethod
    def ensure_actor_can_decide(cls, *, actor, permit, transition):
        """
        Ensure actor can perform the given workflow transition.

        The required role comes from transition.role.
        """

        cls.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=transition.role,
            action_label="execute this transition",
        )

    @classmethod
    def ensure_actor_can_edit_permit(cls, *, actor, permit):
        """
        Ensure actor can edit the permit at its current workflow step.

        Editing is controlled by:
        - permit.current_step.is_editable_step
        - permit.current_step.editable_role

        The editable_role is then checked using the same assignment/scope/
        qualification rules as workflow transitions.
        """

        if not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if actor.is_superuser:
            return

        if not permit.current_step_id:
            raise PermissionDenied(
                "This permit does not have a current workflow step."
            )

        current_step = permit.current_step

        if current_step.is_terminal:
            raise PermissionDenied(
                "This permit is at a terminal workflow step and cannot be edited."
            )

        if not current_step.is_editable_step:
            raise PermissionDenied(
                "This permit cannot be edited at the current workflow step."
            )

        if not current_step.editable_role_id:
            raise PermissionDenied(
                "This workflow step is editable but has no editable role configured."
            )

        cls.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=current_step.editable_role,
            action_label="edit this permit",
        )

    @classmethod
    def actor_can_edit_permit(cls, *, actor, permit) -> bool:
        """
        Boolean helper for views/templates.

        Use this when you only need to show/hide an Edit button.
        Do not use this as the final protection for saving edits.
        The UpdateView/Form save path should call ensure_actor_can_edit_permit().
        """

        try:
            cls.ensure_actor_can_edit_permit(
                actor=actor,
                permit=permit,
            )
        except PermissionDenied:
            return False

        return True

    @classmethod
    def actor_can_decide(cls, *, actor, permit, transition) -> bool:
        """
        Boolean helper for display-only checks.

        Your detail view may use this if you want a clean boolean method.
        The workflow POST service must still call ensure_actor_can_decide().
        """

        try:
            cls.ensure_actor_can_decide(
                actor=actor,
                permit=permit,
                transition=transition,
            )
        except PermissionDenied:
            return False

        return True

    @classmethod
    def ensure_actor_has_role_for_permit(
        cls,
        *,
        actor,
        permit,
        role,
        action_label: str = "perform this action",
    ):
        """
        Reusable role authorization check.

        This method checks:
        - authentication
        - superuser bypass
        - required qualification
        - active PermitApprovalRoleAssignment
        - permit type scope
        - department scope
        - unit scope

        Used by:
        - ensure_actor_can_decide()
        - ensure_actor_can_edit_permit()
        """

        if not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if actor.is_superuser:
            return

        if role is None:
            raise PermissionDenied(
                f"No workflow role is configured to {action_label}."
            )

        today = timezone.localdate()

        # 1. Qualification check
        cls._ensure_required_qualification(
            actor=actor,
            role=role,
            today=today,
            action_label=action_label,
        )

        # 2. Start building assignment query
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
                f"to {action_label} for the designated permit type, department, or unit scope."
            )

    @classmethod
    def actor_has_role_for_permit(cls, *, actor, permit, role) -> bool:
        """
        Boolean wrapper around ensure_actor_has_role_for_permit().
        """

        try:
            cls.ensure_actor_has_role_for_permit(
                actor=actor,
                permit=permit,
                role=role,
            )
        except PermissionDenied:
            return False

        return True

    @classmethod
    def _ensure_required_qualification(
        cls,
        *,
        actor,
        role,
        today,
        action_label: str = "perform this action",
    ):
        if not role.required_qualification_id:
            return

        qualification_manager = cls._get_actor_qualification_manager(actor)

        if qualification_manager is None:
            raise PermissionDenied(
                f"Action blocked: this user has no qualification records configured "
                f"to {action_label}."
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
                f"qualification is required to {action_label}."
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
