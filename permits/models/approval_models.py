from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError

from equipment.models.equipment_models import TimeStampedModel
from permits.models.workflow_models import Decision


class PermitApprovalRoleChoices(TimeStampedModel):
    """
    Dynamic roles configured by admin (e.g. Area Authority, Safety Officer, Performing Authority).
    """
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Permit Approval Role"
        verbose_name_plural = "Permit Approval Roles"

    def __str__(self):
        return self.name


class PermitApproval(TimeStampedModel):
    """
    An immutable audit record of a decision made on a Permit.
    Once created, this cannot be updated or replaced.
    """
    permit = models.ForeignKey(
        "permits.Permit", 
        on_delete=models.CASCADE, 
        related_name="approvals"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.PROTECT, 
        related_name="permit_approvals"
    )
    role = models.ForeignKey(
        PermitApprovalRoleChoices, 
        on_delete=models.PROTECT, 
        related_name="approvals"
    )
    from_step = models.ForeignKey(
        "permits.PermitWorkflowStep", 
        on_delete=models.PROTECT, 
        related_name="+"
    )
    to_step = models.ForeignKey(
        "permits.PermitWorkflowStep", 
        on_delete=models.PROTECT, 
        related_name="+"
    )
    decision = models.CharField(
        max_length=20, 
        choices=Decision.choices
    )
    comment = models.TextField(blank=True)
    
    transition = models.ForeignKey(
        "permits.PermitWorkflowTransition", 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name="approvals"
    )

    class Meta:
        verbose_name = "Permit Approval"
        verbose_name_plural = "Permit Approvals"
        ordering = ["-created_at"]
        indexes = [
            # High efficiency lookups for permit history timelines and user audit trails
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
                raise ValidationError("Approval steps must belong to the exact same workflow version.")

        # Transition Traceability & Match Validation
        if self.transition_id:
            t = self.transition
            if self.from_step_id and self.from_step_id != t.from_step_id:
                raise ValidationError({"from_step": "from_step does not match the configured transition step."})
            
            if self.to_step_id and self.to_step_id != t.to_step_id:
                raise ValidationError({"to_step": "to_step does not match the configured transition target."})
            
            if self.role_id and self.role_id != t.role_id:
                raise ValidationError({"role": "role does not match the role specified by the transition."})
            
            if self.decision and self.decision != t.decision:
                raise ValidationError({"decision": "decision does not match the decision type of this transition."})

    def save(self, *args, **kwargs):
        # Enforce structural audit immutability on update
        if self.pk:
            raise ValidationError("PermitApproval audit records are immutable and cannot be updated.")
            
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Permit {self.permit.permit_number} - {self.decision} by {self.actor} as {self.role.code}"
