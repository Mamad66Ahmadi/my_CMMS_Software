from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
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

    class Meta:
        ordering = ["sort_order", "name", "pk"]
        verbose_name = "Paper Safety Permit Type"
        verbose_name_plural = "Paper Safety Permit Types"

    def __str__(self):
        return self.name


class PaperSafetyPermitWorkflowStep(TimeStampedModel):
    """Safety-permit step mapped to a hardcoded operational status."""

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DEACTIVE = "DEACTIVE", "Deactive"

    name = models.CharField(max_length=100)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DEACTIVE,
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
        return f"{self.step_order}. {self.name} ({self.get_status_display()})"


class PermitPaperSafetyPermit(models.Model):
    """
    A paper safety permit required by a main Permit-to-Work.

    The presence of a row means the paper safety permit is required.  Several
    rows of the same type are allowed.  Its number may remain blank while the
    paper permit is being prepared, but approval requires a number.
    """

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        DEACTIVE = "DEACTIVE", "Deactive"

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
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.DEACTIVE,
        db_index=True,
        editable=False,
    )
    current_step = models.ForeignKey(
        PaperSafetyPermitWorkflowStep,
        null=True,
        blank=True,
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
            models.CheckConstraint(
                condition=(
                    ~Q(status="ACTIVE") | ~Q(safety_permit_number="")
                ),
                name="paper_safety_active_complete_ck",
            ),
        ]
        indexes = [
            models.Index(
                fields=["permit", "status"],
                name="paper_safety_permit_status_idx",
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

    def get_status_display(self):
        return dict(self.Status.choices).get(self.status, self.status)

    @staticmethod
    def status_labels():
        return dict(PermitPaperSafetyPermit.Status.choices)

    def clean(self):
        super().clean()
        self.safety_permit_number = (
            self.safety_permit_number or ""
        ).strip().upper()
        self.review_comment = (self.review_comment or "").strip()

        if self.status == self.Status.ACTIVE and not self.safety_permit_number:
            raise ValidationError(
                {
                    "safety_permit_number": (
                        "A paper safety permit number is required before activation."
                    )
                }
            )

    def save(self, *args, status_actor=None, status_remarks="", **kwargs):
        previous_status = None
        if not self.pk and not self.current_step_id:
            default_step = PaperSafetyPermitWorkflowStep.objects.filter(
                name="Pending",
                is_active=True,
            ).first()
            if default_step:
                self.current_step = default_step
                self.status = default_step.status
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list(
                "status", flat=True
            ).first()

        if previous_status and previous_status != self.status and status_actor is None:
            raise ValidationError(
                "Use change_status() and provide the user who changed the status."
            )

        self.full_clean()
        result = super().save(*args, **kwargs)

        if previous_status and previous_status != self.status:
            self.status_history.create(
                from_status=previous_status,
                to_status=self.status,
                changed_by=status_actor,
                remarks=(status_remarks or "").strip(),
            )
        elif previous_status is None:
            self.status_history.create(
                from_status="",
                to_status=self.status,
                changed_by=status_actor or self.created_by,
                remarks=(status_remarks or "Created paper safety permit.").strip(),
            )
        return result

    def change_status(self, *, status, changed_by, remarks=""):
        if not changed_by or not getattr(changed_by, "is_authenticated", False):
            raise ValidationError("A user is required to change the status.")
        if status == self.status:
            return self
        if status not in self.Status.values:
            raise ValidationError("Invalid paper safety-permit status.")
        self.status = status
        self.modified_by = changed_by
        self.reviewed_by = changed_by
        self.reviewed_at = timezone.now()
        self.review_comment = (remarks or "").strip()
        self.save(status_actor=changed_by, status_remarks=remarks)
        return self

    def change_step(self, *, step, changed_by, remarks=""):
        """Assign a workflow step and copy its active/deactive status."""
        if not isinstance(step, PaperSafetyPermitWorkflowStep):
            raise ValidationError("A valid safety-permit workflow step is required.")
        if not step.is_active:
            raise ValidationError("An inactive safety-permit workflow step cannot be assigned.")

        self.current_step = step
        if step.status == self.status:
            self.modified_by = changed_by
            self.reviewed_by = changed_by
            self.reviewed_at = timezone.now()
            self.review_comment = (remarks or "").strip()
            self.save()
            return self
        return self.change_status(
            status=step.status,
            changed_by=changed_by,
            remarks=remarks,
        )


class PermitPaperSafetyPermitStatusHistory(models.Model):
    """Immutable audit record for every paper safety-permit status change."""

    permit_safety_permit = models.ForeignKey(
        PermitPaperSafetyPermit,
        on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField(max_length=20, blank=True)
    to_status = models.CharField(
        max_length=20,
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
