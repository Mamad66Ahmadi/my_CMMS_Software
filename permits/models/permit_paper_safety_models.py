from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


paper_permit_identifier_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9._-]*$",
    message="Use uppercase letters, numbers, periods, underscores, or hyphens only.",
)


class PermitPaperSafetyPermit(models.Model):
    """
    A paper safety permit required by a main Permit-to-Work.

    The presence of a row means the paper safety permit is required.  Several
    rows of the same type are allowed.  Its number may remain blank while the
    paper permit is being prepared, but approval requires a number.
    """

    class SafetyType(models.TextChoices):
        ISOLATION = "ISOLATION", "Isolation"
        CONFINED_SPACE = "CONFINED_SPACE", "Confined Space"
        DIVING = "DIVING", "Diving"
        EXCAVATION = "EXCAVATION", "Excavation"
        EQUIPMENT_TEST = "EQUIPMENT_TEST", "Equipment Test"
        RADIOGRAPHY = "RADIOGRAPHY", "Radiography"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ACTIVE = "ACTIVE", "Active"
        CANCELLED = "CANCELLED", "Cancelled"
        TERMINATED = "TERMINATED", "Terminated"

    permit = models.ForeignKey(
        "permits.Permit",
        on_delete=models.CASCADE,
        related_name="paper_safety_permits",
    )
    safety_type = models.CharField(
        max_length=30,
        choices=SafetyType.choices,
        db_index=True,
    )
    safety_permit_number = models.CharField(
        max_length=30,
        blank=True,
        validators=[paper_permit_identifier_validator],
        help_text="May be left blank until the paper safety permit is issued.",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        editable=False,
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
        return f"{self.get_safety_type_display()} - {number}"

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
        if self.status == self.Status.TERMINATED:
            raise ValidationError("A terminated paper safety permit cannot change status.")

        self.status = status
        self.modified_by = changed_by
        self.reviewed_by = changed_by
        self.reviewed_at = timezone.now()
        self.review_comment = (remarks or "").strip()
        self.save(status_actor=changed_by, status_remarks=remarks)
        return self


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
        choices=PermitPaperSafetyPermit.Status.choices,
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
