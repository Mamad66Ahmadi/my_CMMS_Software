"""
Workflow configuration models.

These models define how a Permit moves through its approval lifecycle.

Workflow Template
        ↓
Workflow Steps
        ↓
Workflow Conditions
        ↓
PermitApproval records (runtime)

Author: Mohammad Ahmadi
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

from equipment.models.equipment_models import TimeStampedModel
from permits.models.approval_models import ApprovalRoleChoices
from permits.models.permit_base_models import PermitType




class PermitWorkflowTemplate(TimeStampedModel):
    """
    Workflow definition.

    Examples

    Standard Hot Work

    Critical Hot Work

    Confined Space

    Excavation
    """

    code = models.CharField(
        max_length=30,
    )

    name = models.CharField(
        max_length=150,
    )

    permit_type = models.ForeignKey(
        PermitType,
        on_delete=models.PROTECT,
        related_name="workflow_templates",
    )

    description = models.TextField(
        blank=True,
    )

    version = models.PositiveIntegerField(
        default=1,
    )

    is_active = models.BooleanField(
        default=True,
        db_index=True,
    )

    is_default = models.BooleanField(
        default=False,
    )

    class Meta:

        ordering = [
            "permit_type",
            "name",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "permit_type",
                    "version",
                    "code",
                ],
                name="uq_template_version",
            ),
            models.UniqueConstraint(
                fields=["permit_type"],
                condition=Q(is_default=True, is_active=True),
                name="uq_active_default_workflow",
            ),
            models.CheckConstraint(
                condition=Q(version__gt=0),
                name="workflow_version_positive_ck",
            ),

        ]

    def __str__(self):

        return self.name

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()
        self.name = (self.name or "").strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PermitWorkflowStep(TimeStampedModel):

    workflow = models.ForeignKey(
        PermitWorkflowTemplate,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    sequence = models.PositiveSmallIntegerField()

    role = models.CharField(
        max_length=40,
        choices=ApprovalRoleChoices.choices,
    )

    title = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )

    is_required = models.BooleanField(
        default=True,
    )

    allow_delegate = models.BooleanField(
        default=False,
    )

    allow_parallel = models.BooleanField(
        default=False,
    )

    parallel_group = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    can_reject = models.BooleanField(
        default=True,
    )

    can_return = models.BooleanField(
        default=True,
    )

    can_skip = models.BooleanField(
        default=False,
    )

    requires_comment = models.BooleanField(
        default=False,
    )

    timeout_hours = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    class Meta:

        ordering = [
            "workflow",
            "sequence",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "workflow",
                    "sequence",
                ],
                name="uq_workflow_sequence",
            ),
            models.CheckConstraint(
                condition=Q(sequence__gt=0),
                name="workflow_sequence_positive_ck",
            ),

        ]

    def __str__(self):

        return f"{self.workflow} - Step {self.sequence}"

    def clean(self):
        super().clean()
        if self.allow_parallel and self.parallel_group is None:
            raise ValidationError(
                {"parallel_group": "Parallel steps require a parallel group."}
            )
        if not self.allow_parallel and self.parallel_group is not None:
            raise ValidationError(
                {"parallel_group": "Only parallel steps may have a parallel group."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class PermitWorkflowCondition(TimeStampedModel):
    """
    Optional rule that determines whether a step is required.
    """

    class ConditionType(models.TextChoices):

        HOT_WORK = "HOT_WORK"

        CONFINED_SPACE = "CONFINED_SPACE"

        GAS_TEST_REQUIRED = "GAS_TEST_REQUIRED"

        FIRE_WATCH_REQUIRED = "FIRE_WATCH_REQUIRED"

        VEHICLE_REQUIRED = "VEHICLE_REQUIRED"

        ELECTRICAL_ISOLATION = "ELECTRICAL_ISOLATION"

        WORK_AT_HEIGHT = "WORK_AT_HEIGHT"

        CUSTOM = "CUSTOM"

    workflow_step = models.ForeignKey(
        PermitWorkflowStep,
        on_delete=models.CASCADE,
        related_name="conditions",
    )

    condition_type = models.CharField(
        max_length=40,
        choices=ConditionType.choices,
    )

    expected_value = models.CharField(
        max_length=100,
    )

    description = models.TextField(
        blank=True,
    )

    def __str__(self):

        return (
            f"{self.workflow_step} "
            f"{self.condition_type}"
        )


class PermitWorkflowTransition(TimeStampedModel):

    from_step = models.ForeignKey(
        PermitWorkflowStep,
        on_delete=models.CASCADE,
        related_name="next_steps",
    )

    to_step = models.ForeignKey(
        PermitWorkflowStep,
        on_delete=models.CASCADE,
        related_name="previous_steps",
    )

    on_approve = models.BooleanField(
        default=True,
    )

    on_reject = models.BooleanField(
        default=False,
    )

    on_return = models.BooleanField(
        default=False,
    )

    class Meta:

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "from_step",
                    "to_step",
                    "on_approve",
                    "on_reject",
                    "on_return",
                ],
                name="uq_transition",
            ),
            models.CheckConstraint(
                condition=Q(on_approve=True)
                | Q(on_reject=True)
                | Q(on_return=True),
                name="workflow_transition_outcome_ck",
            ),

        ]

    def __str__(self):

        return (
            f"{self.from_step.sequence}"
            f" → "
            f"{self.to_step.sequence}"
        )

    def clean(self):
        super().clean()
        if self.from_step_id and self.to_step_id:
            if self.from_step_id == self.to_step_id:
                raise ValidationError("A workflow step cannot transition to itself.")
            if self.from_step.workflow_id != self.to_step.workflow_id:
                raise ValidationError(
                    "Workflow transitions must stay within one workflow."
                )
        if not any((self.on_approve, self.on_reject, self.on_return)):
            raise ValidationError("Select at least one transition outcome.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
