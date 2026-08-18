# permits/models/permit_hazard_precaution_models.py

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from permits.models.permit_base_models import BaseLookupModel

User = settings.AUTH_USER_MODEL

# =============================================================================
# Hazard
# =============================================================================

class Hazard(BaseLookupModel):
    """
    Hazard identification list.
    """

    class Category(models.TextChoices):
        PROCESS = "PROCESS", "Process"
        SAFETY = "SAFETY", "Safety"
        ENVIRONMENT = "ENV", "Environment"
        HEALTH = "HEALTH", "Occupational Health"
        ELECTRICAL = "ELEC", "Electrical"

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SAFETY,
    )

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Hazard"
        verbose_name_plural = "Hazards"

# =============================================================================
# Precautions / Control Measures
# =============================================================================

class Precaution(BaseLookupModel):
    """
    Required control measures.
    """

    requires_verification = models.BooleanField(
        default=True,
    )
    

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Precaution"
        verbose_name_plural = "Precautions"


# =============================================================================
# PermitHazard
# =============================================================================
class PermitHazard(models.Model):
    permit = models.ForeignKey(
        "Permit",
        on_delete=models.CASCADE,
        related_name="hazard_assessments",
    )
    hazard = models.ForeignKey(
        Hazard,
        on_delete=models.PROTECT,
        related_name="permit_assessments",
    )
    remarks = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_modified",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_removed",
    )


    class Meta:
        ordering = ["hazard__display_order", "hazard__code"]
        indexes = [
            models.Index(
                fields=["permit", "is_active"],
                name="permit_hazard_active_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "hazard"],
                condition=Q(is_active=True),
                name="permit_hazard_unique_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, removed_by__isnull=True, removed_at__isnull=True)
                    | Q(
                        is_active=False,
                        removed_by__isnull=False,
                        removed_at__isnull=False,
                    )
                ),
                name="permit_hazard_removed_fields_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit_id}: {self.hazard}"

    def clean(self):
        super().clean()
        if self.is_active:
            if self.removed_by or self.removed_at:
                raise ValidationError(
                    {
                        "__all__": (
                            "Active hazard records cannot have removal metadata."
                        )
                    }
                )
        elif not self.removed_by or not self.removed_at:
            raise ValidationError(
                {
                    "__all__": (
                        "Inactive hazard records must include "
                        "removed_by and removed_at."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def deactivate(self, *, user):
        if not self.is_active:
            return

        self.is_active = False
        self.removed_by = user
        self.removed_at = timezone.now()
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )


    def reactivate(self, *, user):
        if self.is_active:
            return

        self.is_active = True
        self.removed_by = None
        self.removed_at = None
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )



# =============================================================================
# PermitPrecaution
# =============================================================================
class PermitPrecaution(models.Model):
    permit = models.ForeignKey(
        "Permit",
        on_delete=models.CASCADE,
        related_name="precaution_requirements",
    )
    precaution = models.ForeignKey(
        Precaution,
        on_delete=models.PROTECT,
        related_name="permit_requirements",
    )

    remarks = models.CharField(max_length=50, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_modified",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_removed",
    )

    class Meta:
        ordering = ["precaution__display_order", "precaution__code"]
        indexes = [
            models.Index(
                fields=["permit", "is_active"],
                name="permit_precaution_active_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "precaution"],
                condition=Q(is_active=True),
                name="permit_precaution_unique_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, removed_by__isnull=True, removed_at__isnull=True)
                    | Q(
                        is_active=False,
                        removed_by__isnull=False,
                        removed_at__isnull=False,
                    )
                ),
                name="permit_precaution_removed_fields_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit_id}: {self.precaution}"

    def clean(self):
        super().clean()
        if self.is_active:
            if self.removed_by is not None or self.removed_at is not None:
                raise ValidationError(
                    {
                        "__all__": (
                            "Active precaution records cannot have "
                            "removal metadata."
                        )
                    }
                )
        elif self.removed_by is None or self.removed_at is None:
            raise ValidationError(
                {
                    "__all__": (
                        "Inactive precaution records must include "
                        "removed_by and removed_at."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


    def deactivate(self, *, user):
        if not self.is_active:
            return

        self.is_active = False
        self.removed_by = user
        self.removed_at = timezone.now()
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )


    def reactivate(self, *, user):
        if self.is_active:
            return

        self.is_active = True
        self.removed_by = None
        self.removed_at = None
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )
