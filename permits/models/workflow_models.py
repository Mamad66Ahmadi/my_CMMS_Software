# permits/models/workflow_models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q

from equipment.models.equipment_models import TimeStampedModel


class PermitWorkflow(TimeStampedModel):
    """
    A workflow definition (versioned). A PermitType can point to the active workflow.
    """
    name = models.CharField(max_length=150)
    version = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Permit Workflow"
        verbose_name_plural = "Permit Workflows"
        constraints = [
            models.UniqueConstraint(

                fields=["name", "version"],
                name="uq_workflow_name_version",
            ),
            models.CheckConstraint(
                condition=Q(version__gt=0),
                name="workflow_version_positive_ck",
            ),
        ]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        if not self.name:
            raise ValidationError({"name": "Workflow name is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

class PermitWorkflowStep(TimeStampedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        UNDER_REVIEW = "under_review", "Under Review"
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"

    workflow = models.ForeignKey(
        PermitWorkflow,
        on_delete=models.CASCADE,
        related_name="steps",
    )

    state = models.CharField(
        max_length=30,
        null=True,
        blank=True,
        choices=State.choices,
        help_text="Stable machine-readable identifier for this workflow step.",
    )

    step_number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    is_start = models.BooleanField(default=False)
    is_terminal = models.BooleanField(default=False)

    is_editable_step = models.BooleanField(default=False)
    editable_role = models.ForeignKey(
        "permits.PermitApprovalRoleChoices",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="editable_workflow_steps",
    )

    class Meta:
        verbose_name = "Permit Workflow Step"
        verbose_name_plural = "Permit Workflow Steps"
        ordering = ["workflow", "step_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "step_number"],
                name="uq_workflow_step_number",
            ),
            models.CheckConstraint(
                condition=Q(step_number__gt=0),
                name="workflow_step_number_positive_ck",
            ),
            models.UniqueConstraint(
                fields=["workflow"],
                condition=Q(is_start=True),
                name="uq_workflow_start_step",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workflow", "state"],
                name="workflow_step_state_idx",
            ),
        ]
        
    def clean(self):
        super().clean()

        if self.is_start and self.is_terminal:
            raise ValidationError(
                "A step cannot be both start and terminal."
            )

        if self.is_terminal and self.is_editable_step:
            raise ValidationError(
                {
                    "is_editable_step": (
                        "A terminal step cannot be editable."
                    )
                }
            )

        if self.is_editable_step and not self.editable_role_id:
            raise ValidationError(
                {
                    "editable_role": (
                        "Select the single role allowed to edit permits "
                        "at this step."
                    )
                }
            )

        if not self.is_editable_step and self.editable_role_id:
            raise ValidationError(
                {
                    "editable_role": (
                        "Editable role should only be set when this step "
                        "is editable."
                    )
                }
            )

        if self.is_start and self.workflow_id:
            exists_query = PermitWorkflowStep.objects.filter(
                workflow_id=self.workflow_id,
                is_start=True,
            )

            if self.pk:
                exists_query = exists_query.exclude(pk=self.pk)

            if exists_query.exists():
                raise ValidationError(
                    {
                        "is_start": (
                            "This workflow already has a start step configured."
                        )
                    }
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.workflow.name} (v{self.workflow.version}) - "
            f"Step {self.step_number} ({self.title})"
        )



class Decision(models.TextChoices):
    APPROVE = "APPROVE", "Approve"
    RETURN = "RETURN", "Return"
    CANCEL = "CANCEL", "Cancel"


class PermitWorkflowTransition(TimeStampedModel):
    workflow = models.ForeignKey(
        PermitWorkflow, 
        on_delete=models.CASCADE, 
        related_name="transitions"
    )
    from_step = models.ForeignKey(
        PermitWorkflowStep, 
        on_delete=models.CASCADE, 
        related_name="outgoing_transitions"
    )
    to_step = models.ForeignKey(
        PermitWorkflowStep, 
        on_delete=models.CASCADE, 
        related_name="incoming_transitions"
    )
    decision = models.CharField(max_length=20, choices=Decision.choices)
    
    # Lazy reference string to avoid circular dependency
    role = models.ForeignKey(
        "permits.PermitApprovalRoleChoices", 
        on_delete=models.PROTECT, 
        related_name="transitions"
    )

    class Meta:
        verbose_name = "Permit Workflow Transition"
        verbose_name_plural = "Permit Workflow Transitions"
        constraints = [
            models.UniqueConstraint(
                fields=["workflow", "from_step", "to_step", "decision", "role"],
                name="uq_transition_edge",
            ),
        ]

    def clean(self):
        super().clean()

        # Derive workflow from steps if it isn't set yet
        if self.from_step_id and not self.workflow_id:
            self.workflow = self.from_step.workflow

        if self.from_step_id and self.to_step_id:
            if self.from_step_id == self.to_step_id:
                raise ValidationError("A workflow step cannot transition to itself.")

            if self.from_step.workflow_id != self.to_step.workflow_id:
                raise ValidationError("Steps must belong to the same workflow.")

            if self.workflow_id and self.workflow_id != self.from_step.workflow_id:
                raise ValidationError("Transition workflow must match steps workflow.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.workflow}] Step {self.from_step.step_number} --{self.decision} ({self.role.name})--> Step {self.to_step.step_number}"


class PermitWorkflowCondition(TimeStampedModel):
    """
    A condition that must evaluate True for a transition to be allowed.
    """

    class Operand(models.TextChoices):
        PERMIT = "PERMIT", "Permit"
        PERMIT_TYPE = "PERMIT_TYPE", "Permit Type"

    class Operator(models.TextChoices):
        EQ = "EQ", "Equals"
        NE = "NE", "Not equals"
        GT = "GT", "Greater than"
        GTE = "GTE", "Greater than or equal"
        LT = "LT", "Less than"
        LTE = "LTE", "Less than or equal"
        IN = "IN", "In (comma-separated)"
        CONTAINS = "CONTAINS", "Contains (substring)"
        IS_TRUE = "IS_TRUE", "Is True"
        IS_FALSE = "IS_FALSE", "Is False"
        IS_NULL = "IS_NULL", "Is Null"
        NOT_NULL = "NOT_NULL", "Not Null"

    transition = models.ForeignKey(
        PermitWorkflowTransition,
        on_delete=models.CASCADE,
        related_name="conditions",
    )
    operand = models.CharField(
        max_length=20, 
        choices=Operand.choices, 
        default=Operand.PERMIT
    )
    field_path = models.CharField(max_length=100)
    operator = models.CharField(
        max_length=20, 
        choices=Operator.choices, 
        default=Operator.EQ
    )
    expected_value = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Permit Workflow Condition"
        verbose_name_plural = "Permit Workflow Conditions"
        constraints = [
            models.UniqueConstraint(
                fields=["transition", "operand", "field_path", "operator", "expected_value"],
                name="uq_transition_condition",
            ),
            # Supports single field names or nested dotted paths (e.g., permit_type.code)
            models.CheckConstraint(
                condition=Q(field_path__regex=r"^[a-zA-Z_][a-zA-Z0-9_]*(\.[a-zA-Z_][a-zA-Z0-9_]*)*$"),
                name="workflow_condition_field_path_valid_ck",
            ),
        ]

    def __str__(self):
        return f"{self.transition}: {self.operand}.{self.field_path} {self.operator} {self.expected_value}"

    def clean(self):
        super().clean()

        # 1. Operand Allowed-Fields Validation
        # Keeps permit workflows robust against configuration errors.
        allowed_fields = {
            self.Operand.PERMIT: {
                "vehicle_required",
                "duration_value",
                "duration_unit",
                "estimated_personnel",
            },
            self.Operand.PERMIT_TYPE: {
                "code",
                "name",
            },
        }

        current_allowed = allowed_fields.get(self.operand, set())
        if self.field_path not in current_allowed:
            raise ValidationError(
                {"field_path": f"'{self.field_path}' is not a valid field for the operand '{self.operand}'."}
            )

        # 2. Operator & Value Compatibility check
        no_value_ops = {
            self.Operator.IS_TRUE,
            self.Operator.IS_FALSE,
            self.Operator.IS_NULL,
            self.Operator.NOT_NULL,
        }
        if self.operator in no_value_ops and self.expected_value:
            raise ValidationError({"expected_value": "This operator must not specify an expected value."})

        needs_value_ops = {
            self.Operator.EQ,
            self.Operator.NE,
            self.Operator.GT,
            self.Operator.GTE,
            self.Operator.LT,
            self.Operator.LTE,
            self.Operator.IN,
            self.Operator.CONTAINS,
        }
        if self.operator in needs_value_ops and not self.expected_value:
            raise ValidationError({"expected_value": "This operator requires a non-empty expected value."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
