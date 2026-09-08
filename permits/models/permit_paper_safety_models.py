from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q


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
        PENDING = "PENDING", "Pending Permit Office Review"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

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
                    ~Q(status="APPROVED")
                    | (
                        ~Q(safety_permit_number="")
                        & Q(reviewed_at__isnull=False)
                        & Q(reviewed_by__isnull=False)
                    )
                ),
                name="paper_safety_approved_complete_ck",
            ),
            models.CheckConstraint(
                condition=(
                    (
                        Q(status="PENDING")
                        & Q(reviewed_at__isnull=True)
                        & Q(reviewed_by__isnull=True)
                    )
                    | (
                        ~Q(status="PENDING")
                        & Q(reviewed_at__isnull=False)
                        & Q(reviewed_by__isnull=False)
                    )
                ),
                name="paper_safety_reviewed_complete_ck",
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

        if self.status == self.Status.APPROVED and not self.safety_permit_number:
            raise ValidationError(
                {
                    "safety_permit_number": (
                        "A paper safety permit number is required before approval."
                    )
                }
            )

        if self.status == self.Status.PENDING:
            if self.reviewed_by_id or self.reviewed_at:
                raise ValidationError(
                    {
                        "status": (
                            "A pending paper safety permit cannot contain review details."
                        )
                    }
                )
        elif not self.reviewed_by_id or not self.reviewed_at:
            raise ValidationError(
                {
                    "status": (
                        "Approved or rejected paper safety permits require the "
                        "Permit Office reviewer and review time."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
