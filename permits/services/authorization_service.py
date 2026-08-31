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

        if cls._actor_can_submit_initial_permit(
            actor=actor,
            permit=permit,
            transition=transition,
        ):
            return

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

        if (
            current_step.is_start
            and permit.created_by_id == actor.pk
        ):
            return

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
    def _actor_can_submit_initial_permit(
        cls,
        *,
        actor,
        permit,
        transition,
    ) -> bool:
        """
        The permit creator may submit their own permit from the start step.

        The workflow must still explicitly configure the transition with the
        Permit-Creator role. This bypass applies only to the original creator
        and only while the transition exits the workflow start step.
        """
        if not actor.is_authenticated or actor.is_superuser:
            return False

        if permit.created_by_id != actor.pk:
            return False

        if not transition.from_step.is_start:
            return False

        role = transition.role
        if role is None:
            return False

        role_code = (role.code or "").strip().upper().replace("_", "-")
        role_name = (role.name or "").strip().casefold()

        return (
            role_code == "PERMIT-CREATOR"
            or role_name == "permit creator"
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
            raise PermissionDenied(f"No workflow role is configured to {action_label}.")

        today = timezone.localdate()

        # --- Qualification ---
        print(f"\n[AUTH] user={actor} role={role.code!r} action={action_label!r}")
        print(f"  [1] qualification required: {role.required_qualification_id}")
        try:
            cls._ensure_required_qualification(actor=actor, role=role, today=today, action_label=action_label)
            print(f"  [1] qualification: PASS")
        except PermissionDenied as e:
            print(f"  [1] qualification: FAIL — {e}")
            raise

        # --- Base assignments ---
        assignments = PermitApprovalRoleAssignment.objects.filter(user=actor, role=role, is_active=True)
        base_count = assignments.count()
        print(f"  [2] active assignments for role: {base_count}")
        if base_count == 0:
            all_for_role = PermitApprovalRoleAssignment.objects.filter(user=actor, role=role)
            print(f"      (inactive assignments exist: {all_for_role.count()})")

        # --- Permit type filter ---
        assignments = assignments.filter(Q(permit_type__isnull=True) | Q(permit_type=permit.permit_type))
        print(f"  [3] after permit_type filter (permit_type={permit.permit_type_id}): {assignments.count()}")

        # --- Department scope ---
        print(f"  [4] dept_scope={role.department_scope} | permit.department_id={permit.department_id}")
        if role.department_scope == role.ScopeRequirement.REQUIRED:
            if not permit.department_id:
                print(f"  [4] dept: FAIL — permit has no department")
                raise PermissionDenied("This permit has no originating department.")
            assignments = assignments.filter(department=permit.department)
            print(f"  [4] after dept filter: {assignments.count()}")

        # --- Unit scope ---
        permit_unit = permit.location_tag.unit if permit.location_tag else None
        print(f"  [5] unit_scope={role.unit_scope} | permit_unit={permit_unit}")
        if role.unit_scope == role.ScopeRequirement.REQUIRED:
            if not permit_unit:
                print(f"  [5] unit: FAIL — no unit resolved from location_tag")
                raise PermissionDenied("The permit equipment location does not resolve to an operational unit.")
            assignments = assignments.filter(Q(all_units=True) | Q(units=permit_unit))
            print(f"  [5] after unit filter: {assignments.count()}")

        # --- Final ---
        result = assignments.exists()
        print(f"  [6] FINAL match={result}")
        if not result:
            # Show what assignments exist to diagnose mismatch
            for a in PermitApprovalRoleAssignment.objects.filter(user=actor, role=role):
                print(f"      assignment pk={a.pk} active={a.is_active} permit_type_id={a.permit_type_id} dept_id={a.department_id} all_units={a.all_units} units={list(a.units.values_list('pk', flat=True))}")
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



