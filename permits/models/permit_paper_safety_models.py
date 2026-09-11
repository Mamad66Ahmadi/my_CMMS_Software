from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from equipment.models.equipment_models import TimeStampedModel


paper_permit_identifier_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9._-]*$",
    message="Use uppercase letters, numbers, periods, underscores, or hyphens only.",
)


class PaperSafetyPermitType(TimeStampedModel):
    """Configurable paper safety-permit type shown to permit creators."""

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)
    validity_shifts = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Active shifts",
        help_text="Number of work shifts this safety permit remains active after approval.",
    )

    class Meta:
        ordering = ["sort_order", "name", "pk"]
        verbose_name = "Paper Safety Permit Type"
        verbose_name_plural = "Paper Safety Permit Types"

    def __str__(self):
        return self.name


class PaperSafetyPermitWorkflowStep(TimeStampedModel):
    """Configurable workflow state for a paper safety permit."""

    name = models.CharField(max_length=100)
    blocks_main_permit = models.BooleanField(
        default=True,
        help_text=(
            "Whether a safety permit at this step prevents the main permit "
            "from proceeding."
        ),
    )
    step_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["step_order", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["name"], name="uq_paper_safety_workflow_step_name"
            )
        ]
        verbose_name = "Paper Safety Permit Workflow Step"
        verbose_name_plural = "Paper Safety Permit Workflow Steps"

    def __str__(self):
        return f"{self.step_order}. {self.name}"


class PermitPaperSafetyPermit(models.Model):
    """
    A paper safety permit required by a main Permit-to-Work.

    The presence of a row means the paper safety permit is required.  Several
    rows of the same type are allowed.  Its number may remain blank while the
    paper permit is being prepared, but approval requires a number.
    """

    permit = models.ForeignKey(
        "permits.Permit",
        on_delete=models.CASCADE,
        related_name="paper_safety_permits",
    )
    safety_type = models.ForeignKey(
        PaperSafetyPermitType,
        on_delete=models.PROTECT,
        related_name="paper_safety_permits",
        db_index=True,
    )
    safety_permit_number = models.CharField(
        max_length=30,
        blank=True,
        validators=[paper_permit_identifier_validator],
        help_text="May be left blank until the paper safety permit is issued.",
    )
    current_step = models.ForeignKey(
        PaperSafetyPermitWorkflowStep,
        editable=False,
        on_delete=models.PROTECT,
        related_name="paper_safety_permits",
    )
    review_comment = models.TextField(blank=True, editable=False)
    reviewed_at = models.DateTimeField(null=True, blank=True, editable=False)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="reviewed_paper_safety_permits",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_paper_safety_permits",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modified_paper_safety_permits",
    )

    class Meta:
        ordering = ["permit", "safety_type", "pk"]
        verbose_name = "Paper Safety Permit"
        verbose_name_plural = "Paper Safety Permits"
        constraints = [
            models.UniqueConstraint(
                fields=["safety_type", "safety_permit_number"],
                condition=~Q(safety_permit_number=""),
                name="uq_paper_safety_type_number",
            ),
        ]
        indexes = [
            models.Index(
                fields=["permit", "current_step"],
                name="paper_safety_permit_step_idx",
            ),
            models.Index(
                fields=["permit", "safety_type"],
                name="paper_safety_permit_type_idx",
            ),
        ]

    def __str__(self):
        number = self.safety_permit_number or "number pending"
        return f"{self.safety_type} - {number}"

    def get_safety_type_display(self):
        return str(self.safety_type)

    @property
    def status(self):
        """The displayed and operational state is the current workflow step name."""
        if self._shift_limit_reached:
            return "Expired"
        return self.current_step.name

    def get_status_display(self):
        return self.status

    @property
    def blocks_main_permit(self):
        return self.current_step.blocks_main_permit

    @property
    def _shift_limit_reached(self):
        if not self.current_step_id or self.current_step.name != "Activated":
            return False
        limit = self.safety_type.validity_shifts if self.safety_type_id else None
        if not limit or not self.permit_id:
            return False
        activated_at = (
            self.status_history.filter(to_status="Activated")
            .order_by("changed_at")
            .values_list("changed_at", flat=True)
            .first()
        )
        if not activated_at:
            return False
        return self.permit.work_shifts.filter(created_at__gte=activated_at).count() >= limit

    def expire_if_needed(self):
        """Move an activated permit to the configured Expired step when its shift limit is reached."""
        if not self._shift_limit_reached:
            return False
        expired_step = PaperSafetyPermitWorkflowStep.objects.filter(
            name="Expired", is_active=True
        ).first()
        if not expired_step:
            return False
        previous_name = self.current_step.name
        now = timezone.now()
        self.current_step = expired_step
        self.reviewed_at = now
        self.review_comment = "Automatically expired after the configured number of work shifts."
        super().save(update_fields=["current_step", "reviewed_at", "review_comment"])
        self.status_history.create(
            from_status=previous_name,
            to_status=expired_step.name,
            changed_by=None,
            changed_at=now,
            remarks=self.review_comment,
        )
        return True

    def clean(self):
        super().clean()
        self.safety_permit_number = (
            self.safety_permit_number or ""
        ).strip().upper()
        self.review_comment = (self.review_comment or "").strip()

        if (
            self.current_step_id
            and self.current_step.name == "Activated"
            and not self.safety_permit_number
        ):
            raise ValidationError(
                {
                    "safety_permit_number": (
                        "A paper safety permit number is required before activation."
                    )
                }
            )

    def save(self, *args, step_actor=None, step_remarks="", **kwargs):
        previous_step = None
        if not self.pk and not self.current_step_id:
            default_step = PaperSafetyPermitWorkflowStep.objects.filter(
                name="Pending",
                is_active=True,
            ).first()
            if not default_step:
                raise ValidationError(
                    'The active safety-permit step "Pending" is not configured.'
                )
            self.current_step = default_step
        if self.pk:
            previous_step = (
                type(self).objects.select_related("current_step").get(pk=self.pk).current_step
            )

        if previous_step and previous_step.pk != self.current_step_id and step_actor is None:
            raise ValidationError(
                "Use change_step() and provide the user who changed the step."
            )

        self.full_clean()
        result = super().save(*args, **kwargs)

        if previous_step and previous_step.pk != self.current_step_id:
            self.status_history.create(
                from_status=previous_step.name,
                to_status=self.current_step.name,
                changed_by=step_actor,
                remarks=(step_remarks or "").strip(),
            )
        elif previous_step is None:
            self.status_history.create(
                from_status="",
                to_status=self.current_step.name,
                changed_by=step_actor or self.created_by,
                remarks=(step_remarks or "").strip(),
            )
        return result

    def change_step(self, *, step, changed_by, remarks=""):
        """Assign an enabled workflow step and record the transition."""
        if not isinstance(step, PaperSafetyPermitWorkflowStep):
            raise ValidationError("A valid safety-permit workflow step is required.")
        if not changed_by or not getattr(changed_by, "is_authenticated", False):
            raise ValidationError("A user is required to change the workflow step.")
        if not step.is_active:
            raise ValidationError("An inactive safety-permit workflow step cannot be assigned.")

        if self.current_step_id == step.pk:
            return self
        self.current_step = step
        self.modified_by = changed_by
        self.reviewed_by = changed_by
        self.reviewed_at = timezone.now()
        self.review_comment = (remarks or "").strip()
        self.save(step_actor=changed_by, step_remarks=remarks)
        return self


class PermitPaperSafetyPermitStatusHistory(models.Model):
    """Immutable audit record for every paper safety-permit step change."""

    permit_safety_permit = models.ForeignKey(
        PermitPaperSafetyPermit,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=100, blank=True)
    to_status = models.CharField(
        max_length=100,
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="paper_safety_permit_status_changes",
    )
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at", "-pk"]
        verbose_name = "Paper Safety Permit Status History"
        verbose_name_plural = "Paper Safety Permit Status History"
        indexes = [
            models.Index(
                fields=["permit_safety_permit", "-changed_at"],
                name="paper_safety_status_hist_idx",
            )
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Status history records are immutable.")
        self.remarks = (self.remarks or "").strip()
        return super().save(*args, **kwargs)
