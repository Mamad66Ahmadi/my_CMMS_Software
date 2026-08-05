from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from permits.models.approval_models import PermitApproval
from permits.models.workflow_models import Decision, PermitWorkflowTransition
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

    Never update Permit.current_step directly in views, serializers,
    admin actions, or unrelated model methods.
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

        cls._validate_decision(decision)

        permit = (
            Permit.objects.select_for_update()
            .select_related(
                "workflow",
                "current_step",
                "permit_type",
                "department",
                "location_tag",
                "location_tag__unit",
            )
            .get(pk=permit_id)
        )

        if not permit.workflow_id:
            raise WorkflowTransitionError(
                "This permit does not have an assigned workflow."
            )

        if not permit.current_step_id:
            raise WorkflowTransitionError(
                "This permit does not have a current workflow step."
            )

        if permit.current_step.is_terminal:
            raise WorkflowTransitionError(
                "This permit is already at a terminal workflow step."
            )

        transition = (
            PermitWorkflowTransition.objects.select_related(
                "workflow",
                "from_step",
                "to_step",
                "role",
                "role__required_qualification",
            )
            .prefetch_related("conditions")
            .filter(
                workflow_id=permit.workflow_id,
                from_step_id=permit.current_step_id,
                decision=decision,
                role__code=role_code,
            )
            .first()
        )

        if transition is None:
            raise WorkflowTransitionError(
                "No configured workflow transition matches this decision, "
                "current step, and approval role."
            )

        role = transition.role

        WorkflowAuthorizationService.ensure_actor_can_decide(
            actor=actor,
            permit=permit,
            transition=transition,
        )

        WorkflowConditionEvaluator.ensure_transition_allowed(
            permit=permit,
            transition=transition,
        )

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

        now = timezone.now()

        update_data = {
            "current_step_id": transition.to_step_id,
        }

        if transition.to_step.is_terminal:
            update_data["closed_at"] = now

        if transition.decision == Decision.CANCEL:
            update_data["suspended_at"] = now

        Permit.objects.filter(pk=permit.pk).update(**update_data)

        permit.current_step = transition.to_step
        permit.current_step_id = transition.to_step_id

        for field_name, value in update_data.items():
            setattr(permit, field_name, value)

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
