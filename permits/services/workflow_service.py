# permits/services/workflow_service.py
from dataclasses import dataclass
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from permits.models.approval_models import (
    PermitApproval,
    PermitApprovalRoleChoices,
)
from permits.models.workflow_models import (
    Decision,
    PermitWorkflowTransition,
)
from permits.services.authorization_service import WorkflowAuthorizationService
from permits.services.condition_service import WorkflowConditionEvaluator


class WorkflowTransitionError(ValidationError):
    """Raised when a permit workflow transition is not permitted."""


@dataclass(frozen=True)
class TransitionResult:
    permit: object
    approval: PermitApproval
    transition: PermitWorkflowTransition


class PermitWorkflowService:
    """
    The single application-level write path for Permit workflow decisions.
    """

    @classmethod
    @transaction.atomic
    def transition(
        cls,
        *,
        permit_id: int,
        actor,
        role_code: str,
        decision: str,
        comment: str = "",
    ) -> TransitionResult:
        from permits.models.permit_models import Permit

        # Lock the permit record to prevent race conditions in concurrent requests
        permit = (
            Permit.objects.select_for_update()
            .select_related(
                "workflow",
                "current_step",
                "location_tag__unit",  # Prefetch to support unit scope checks
                "department",
            )
            .get(pk=permit_id)
        )

        cls._validate_decision(decision)

        if not permit.workflow_id:
            raise WorkflowTransitionError(
                "This permit does not have an assigned workflow."
            )

        if not permit.current_step_id:
            raise WorkflowTransitionError(
                "This permit does not have a current workflow step."
            )

        try:
            role = PermitApprovalRoleChoices.objects.get(code=role_code)
        except PermitApprovalRoleChoices.DoesNotExist:
            raise WorkflowTransitionError(
                f"Approval role with code '{role_code}' does not exist."
            )

        # Retrieve transition matching context
        transition = (
            PermitWorkflowTransition.objects.select_related(
                "workflow",
                "from_step",
                "to_step",
                "role",
            )
            .filter(
                workflow_id=permit.workflow_id,
                from_step_id=permit.current_step_id,
                decision=decision,
                role_id=role.pk,
            )
            .first()
        )

        if transition is None:
            raise WorkflowTransitionError(
                "No configured workflow transition matches this decision, "
                "current step, and approval role."
            )

        # Validate authorization rules
        WorkflowAuthorizationService.ensure_actor_can_decide(
            actor=actor,
            permit=permit,
            transition=transition,  # Fix: removed redundant 'role=role' keyword argument
        )

        # Validate workflow field-level conditions
        WorkflowConditionEvaluator.ensure_transition_allowed(
            permit=permit,
            transition=transition,
        )

        # Build immutable approval record
        approval = PermitApproval.objects.create(
            permit=permit,
            actor=actor,
            role=role,
            from_step=transition.from_step,
            to_step=transition.to_step,
            decision=transition.decision,
            comment=(comment or "").strip(),
            transition=transition,
        )

        # Update permit state
        permit.current_step = transition.to_step

        # Auto-populate timestamp audits depending on transition goals
        now = timezone.now()
        
        # Keep track of updated fields for optimal SQL performance
        updated_fields = ["current_step"]

        if transition.to_step.is_terminal:
            permit.closed_at = now
            updated_fields.append("closed_at")

        if transition.decision == Decision.CANCEL:
            permit.suspended_at = now
            updated_fields.append("suspended_at")

        permit.save(update_fields=updated_fields)

        return TransitionResult(
            permit=permit,
            approval=approval,
            transition=transition,
        )

    @staticmethod
    def _validate_decision(decision: str) -> None:
        valid_decisions = {choice for choice, _label in Decision.choices}
        if decision not in valid_decisions:
            raise WorkflowTransitionError(
                {"decision": "The supplied decision is not valid."}
            )
