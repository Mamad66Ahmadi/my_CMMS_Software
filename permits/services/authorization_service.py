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
        action_label="perform this action",
    ):
        if not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if actor.is_superuser:
            return

        if role is None:
            raise PermissionDenied(
                f"No workflow role is configured to {action_label}."
            )

        today = timezone.localdate()

        # ---------------------------------------------------------
        # 1. Qualification
        # ---------------------------------------------------------
        cls._ensure_required_qualification(
            actor=actor,
            role=role,
            today=today,
            action_label=action_label,
        )

        # ---------------------------------------------------------
        # 2. Find role assignments
        # ---------------------------------------------------------
        assignments = PermitApprovalRoleAssignment.objects.filter(
            user=actor,
            role=role,
            is_active=True,
        )

        # DEBUG
        print("\n========== WORKFLOW AUTHORIZATION DEBUG ==========")
        print(f"USER: {actor}")
        print(f"ROLE: {role}")
        print(f"ROLE CODE: {role.code}")
        print(f"PERMIT: {permit.permit_number}")
        print(f"PERMIT TYPE: {permit.permit_type}")
        print(f"PERMIT TYPE ID: {permit.permit_type_id}")
        print(f"PERMIT DEPARTMENT: {permit.department}")
        print(f"PERMIT DEPARTMENT ID: {permit.department_id}")

        print("ALL ROLE ASSIGNMENTS:")
        for assignment in PermitApprovalRoleAssignment.objects.filter(
            user=actor,
            role=role,
        ).prefetch_related("units"):
            print(
                "  Assignment:",
                assignment.pk,
                "| active =", getattr(assignment, "is_active", None),
                "| permit_type =", assignment.permit_type,
                "| permit_type_id =", assignment.permit_type_id,
                "| department =", assignment.department,
                "| department_id =", assignment.department_id,
                "| all_units =", assignment.all_units,
                "| units =", list(assignment.units.all()),
            )

        # ---------------------------------------------------------
        # 3. Permit type scope
        # ---------------------------------------------------------
        assignments = assignments.filter(
            Q(permit_type__isnull=True)
            | Q(permit_type=permit.permit_type)
        )

        print(
            "AFTER PERMIT TYPE FILTER:",
            list(assignments.values(
                "id",
                "permit_type_id",
                "department_id",
                "all_units",
            ))
        )

        # ---------------------------------------------------------
        # 4. Department scope
        # ---------------------------------------------------------
        if role.department_scope == role.ScopeRequirement.REQUIRED:

            print("DEPARTMENT SCOPE: REQUIRED")

            if not permit.department_id:
                raise PermissionDenied(
                    "This permit has no originating department."
                )

            assignments = assignments.filter(
                department=permit.department,
            )

            print(
                "AFTER DEPARTMENT FILTER:",
                list(assignments.values(
                    "id",
                    "permit_type_id",
                    "department_id",
                    "all_units",
                ))
            )

        else:
            print("DEPARTMENT SCOPE: NOT REQUIRED")

        # ---------------------------------------------------------
        # 5. Unit scope
        # ---------------------------------------------------------
        if role.unit_scope == role.ScopeRequirement.REQUIRED:

            print("UNIT SCOPE: REQUIRED")

            permit_unit = (
                permit.location_tag.unit
                if permit.location_tag
                else None
            )

            print("PERMIT UNIT:", permit_unit)
            print("PERMIT UNIT ID:", getattr(permit_unit, "pk", None))

            if not permit_unit:
                raise PermissionDenied(
                    "The permit equipment location does not resolve "
                    "to an operational unit."
                )

            assignments = assignments.filter(
                Q(all_units=True)
                | Q(units=permit_unit)
            )

            print(
                "AFTER UNIT FILTER:",
                list(assignments.values(
                    "id",
                    "permit_type_id",
                    "department_id",
                    "all_units",
                ))
            )

        else:
            print("UNIT SCOPE: NOT REQUIRED")

        # ---------------------------------------------------------
        # 6. Final result
        # ---------------------------------------------------------
        print("FINAL MATCHING ASSIGNMENTS:", assignments.exists())
        print("===================================================\n")

        if not assignments.exists():
            raise PermissionDenied(
                f"You do not hold an active role assignment matching "
                f"'{role.name}' to {action_label} for the designated "
                f"permit type, department, or unit scope."
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
            actor.qualifications
        """

        qualification_manager = getattr(actor, "qualifications", None)

        if qualification_manager is None:
            return None

        if not hasattr(qualification_manager, "filter"):
            return None

        return qualification_manager



