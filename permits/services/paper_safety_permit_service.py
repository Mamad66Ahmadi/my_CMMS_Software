from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from permits.models.approval_models import PermitApprovalRoleChoices
from permits.models.permit_paper_safety_models import (
    PermitPaperSafetyPermit,
    PaperSafetyPermitWorkflowStep,
)
from permits.services.authorization_service import WorkflowAuthorizationService


class PaperSafetyPermitReviewService:
    """Permit Office review actions for paper safety permits."""

    @classmethod
    @transaction.atomic
    def approve(
        cls,
        *,
        paper_safety_permit_id,
        actor,
        safety_permit_number=None,
        comment="",
    ):
        record = cls._get_locked_record(paper_safety_permit_id)
        cls._ensure_review_allowed(record=record, actor=actor)

        if safety_permit_number is not None:
            record.safety_permit_number = safety_permit_number

        record.change_step(
            step=cls._get_step("Activated"),
            changed_by=actor,
            remarks=comment,
        )
        return record

    @classmethod
    @transaction.atomic
    def reject(cls, *, paper_safety_permit_id, actor, comment):
        record = cls._get_locked_record(paper_safety_permit_id)
        cls._ensure_review_allowed(record=record, actor=actor)

        comment = (comment or "").strip()
        if not comment:
            raise ValidationError(
                {"review_comment": "A rejection comment is required."}
            )

        record.change_step(
            step=cls._get_step("Cancelled"),
            changed_by=actor,
            remarks=comment,
        )
        return record

    @staticmethod
    def _get_locked_record(paper_safety_permit_id):
        return (
            PermitPaperSafetyPermit.objects.select_for_update()
            .select_related(
                "permit",
                "permit__permit_type",
                "permit__department",
                "permit__location_tag",
                "permit__location_tag__unit",
                "current_step",
            )
            .get(pk=paper_safety_permit_id)
        )

    @staticmethod
    def _get_step(name):
        try:
            return PaperSafetyPermitWorkflowStep.objects.get(
                name=name,
                is_active=True,
            )
        except PaperSafetyPermitWorkflowStep.DoesNotExist as exc:
            raise ValidationError(
                f'The active safety-permit step "{name}" is not configured.'
            ) from exc

    @classmethod
    def _ensure_review_allowed(cls, *, record, actor):
        if record.permit.activated_at:
            raise ValidationError(
                "Paper safety-permit review cannot change after the main permit is activated."
            )

        if not actor or not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if actor.is_superuser:
            return

        roles = PermitApprovalRoleChoices.objects.filter(is_active=True).filter(
            Q(code__iexact="PERMIT_OFFICE")
            | Q(code__iexact="Permit Office")
            | Q(name__iexact="Permit Office")
        )

        for role in roles:
            if WorkflowAuthorizationService.actor_has_role_for_permit(
                actor=actor,
                permit=record.permit,
                role=role,
            ):
                return

        raise PermissionDenied(
            "Only an authorized Permit Office user may review a paper safety permit."
        )

    @classmethod
    def actor_can_review(cls, *, record, actor):
        try:
            cls._ensure_review_allowed(record=record, actor=actor)
        except (PermissionDenied, ValidationError):
            return False
        return True

    @classmethod
    @transaction.atomic
    def assign_step(cls, *, paper_safety_permit_id, actor, step_id, remarks=""):
        record = cls._get_locked_record(paper_safety_permit_id)
        cls._ensure_review_allowed(record=record, actor=actor)
        step = PaperSafetyPermitWorkflowStep.objects.get(pk=step_id, is_active=True)
        return record.change_step(step=step, changed_by=actor, remarks=remarks)
