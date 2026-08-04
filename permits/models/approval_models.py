# permits/models/approval_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from equipment.models.equipment_models import TimeStampedModel
from permits.models.workflow_models import Decision


class PermitApprovalRoleChoices(TimeStampedModel):
    """
    Dynamic roles configured by admin
    (e.g. Area Authority, Safety Officer, Performing Authority).
    """
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Permit Approval Role"
        verbose_name_plural = "Permit Approval Roles"

    def __str__(self):
        return self.name


class PermitApproval(models.Model):
    """
    Immutable audit record of a workflow decision on a Permit.

    This intentionally does not inherit from TimeStampedModel:
    - actor already captures the decision-maker;
    - records are immutable, so modified_at / modified_by are unnecessary;
    - simple-history records would be redundant for an append-only audit event.
    """

    created_at = models.DateTimeField(
        default=timezone.now,
        editable=False,
        db_index=True,
    )

    permit = models.ForeignKey(
        "permits.Permit",
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="permit_approvals",
    )

    role = models.ForeignKey(
        PermitApprovalRoleChoices,
        on_delete=models.PROTECT,
        related_name="approvals",
    )

    from_step = models.ForeignKey(
        "permits.PermitWorkflowStep",
        on_delete=models.PROTECT,
        related_name="+",
    )

    to_step = models.ForeignKey(
        "permits.PermitWorkflowStep",
        on_delete=models.PROTECT,
        related_name="+",
    )

    decision = models.CharField(
        max_length=20,
        choices=Decision.choices,
    )

    comment = models.TextField(blank=True)

    transition = models.ForeignKey(
        "permits.PermitWorkflowTransition",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approvals",
    )

    class Meta:
        verbose_name = "Permit Approval"
        verbose_name_plural = "Permit Approvals"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["permit", "-created_at"]),
            models.Index(fields=["actor", "-created_at"]),
        ]

    def clean(self):
        super().clean()

        if self.from_step_id and self.permit_id:
            if self.from_step.workflow_id != self.permit.workflow_id:
                raise ValidationError(
                    {
                        "from_step": (
                            "The approval step must belong to the permit workflow."
                        )
                    }
                )

        if self.from_step_id and self.to_step_id:
            if self.from_step.workflow_id != self.to_step.workflow_id:
                raise ValidationError(
                    "Approval steps must belong to the exact same workflow version."
                )

        if self.transition_id:
            transition = self.transition

            if self.from_step_id and self.from_step_id != transition.from_step_id:
                raise ValidationError(
                    {
                        "from_step": (
                            "from_step does not match the configured transition step."
                        )
                    }
                )

            if self.to_step_id and self.to_step_id != transition.to_step_id:
                raise ValidationError(
                    {
                        "to_step": (
                            "to_step does not match the configured transition target."
                        )
                    }
                )

            if self.role_id and self.role_id != transition.role_id:
                raise ValidationError(
                    {
                        "role": (
                            "role does not match the role specified by the transition."
                        )
                    }
                )

            if self.decision and self.decision != transition.decision:
                raise ValidationError(
                    {
                        "decision": (
                            "decision does not match the decision type "
                            "of this transition."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError(
                "PermitApproval audit records are immutable and cannot be updated."
            )

        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"Permit {self.permit.permit_number} - "
            f"{self.decision} by {self.actor} as {self.role.code}"
        )
