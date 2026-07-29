# permits/models/isolation_models.py

"""
Isolation models for Permit To Work (PTW).

A Permit may require multiple isolation groups.
Each isolation group may contain multiple isolation points.
Each isolation point may have multiple verification records.

Author: Mohammad Ahmadi
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from equipment.models.equipment_models import TimeStampedModel
from permits.models.permit_models import Permit
from permits.models.permit_base_models import IsolationType
from equipment.models.equipment_models import LocationTag

User = get_user_model()


# ==========================================================
# Isolation Group
# ==========================================================

class PermitIsolation(TimeStampedModel):
    """
    Represents one isolation plan for a permit.

    Examples:
        Mechanical Isolation
        Electrical Isolation
        Process Isolation
    """

    class IsolationStatus(models.TextChoices):

        PLANNED = "PLANNED", "Planned"

        IN_PROGRESS = "IN_PROGRESS", "In Progress"

        COMPLETED = "COMPLETED", "Completed"

        VERIFIED = "VERIFIED", "Verified"

        REMOVED = "REMOVED", "Removed"

    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="isolations",
    )

    isolation_type = models.ForeignKey(
        IsolationType,
        on_delete=models.PROTECT,
        related_name="permit_isolations",
    )

    status = models.CharField(
        max_length=20,
        choices=IsolationStatus.choices,
        default=IsolationStatus.PLANNED,
        db_index=True,
    )

    description = models.TextField(
        blank=True,
    )

    requires_loto = models.BooleanField(
        default=False,
    )

    blind_list_required = models.BooleanField(
        default=False,
    )

    planned_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="planned_isolations",
    )

    applied_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="applied_isolations",
    )

    verified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="verified_isolations",
    )

    removed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="removed_isolations",
    )

    applied_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    verified_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    removed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:

        ordering = [
            "permit",
            "isolation_type",
        ]

        indexes = [

            models.Index(
                fields=[
                    "permit",
                    "status",
                ]
            ),

        ]

    def __str__(self):

        return (
            f"{self.permit.permit_number}"
            f" - "
            f"{self.isolation_type.name}"
        )

    def clean(self):
        super().clean()
        errors = {}
        if self.status in {
            self.IsolationStatus.COMPLETED,
            self.IsolationStatus.VERIFIED,
            self.IsolationStatus.REMOVED,
        }:
            if not self.applied_by_id:
                errors["applied_by"] = "Applied by is required for this status."
            if not self.applied_at:
                errors["applied_at"] = "Applied at is required for this status."
        if self.status in {
            self.IsolationStatus.VERIFIED,
            self.IsolationStatus.REMOVED,
        }:
            if not self.verified_by_id:
                errors["verified_by"] = "Verified by is required for this status."
            if not self.verified_at:
                errors["verified_at"] = "Verified at is required for this status."
        if self.status == self.IsolationStatus.REMOVED:
            if not self.removed_by_id:
                errors["removed_by"] = "Removed by is required after restoration."
            if not self.removed_at:
                errors["removed_at"] = "Removed at is required after restoration."
        if self.applied_at and self.verified_at and self.verified_at < self.applied_at:
            errors["verified_at"] = "Verification cannot precede application."
        if self.verified_at and self.removed_at and self.removed_at < self.verified_at:
            errors["removed_at"] = "Removal cannot precede verification."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# ==========================================================
# Isolation Point
# ==========================================================

class IsolationPoint(TimeStampedModel):
    """
    Individual isolation point.

    Examples:

    Valve HV-101

    MCC Feeder M-101

    Breaker BR-14

    Blind BL-203
    """

    class PointStatus(models.TextChoices):

        PENDING = "PENDING", "Pending"

        ISOLATED = "ISOLATED", "Isolated"

        VERIFIED = "VERIFIED", "Verified"

        RESTORED = "RESTORED", "Restored"

    isolation = models.ForeignKey(
        PermitIsolation,
        on_delete=models.CASCADE,
        related_name="points",
    )

    equipment_tag = models.ForeignKey(
        LocationTag,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="isolation_points",
    )

    point_number = models.CharField(
        max_length=50,
        blank=True,
    )

    description = models.CharField(
        max_length=250,
    )

    lock_number = models.CharField(
        max_length=50,
        blank=True,
    )

    tag_number = models.CharField(
        max_length=50,
        blank=True,
    )

    blind_number = models.CharField(
        max_length=50,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=PointStatus.choices,
        default=PointStatus.PENDING,
    )

    isolated_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="isolated_points",
    )

    restored_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="restored_points",
    )

    isolated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    restored_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:

        ordering = [
            "point_number",
            "id",
        ]

        indexes = [

            models.Index(
                fields=[
                    "status",
                ]
            ),

        ]
        constraints = [
            models.UniqueConstraint(
                fields=["isolation", "point_number"],
                condition=~models.Q(point_number=""),
                name="uq_isolation_point_number",
            ),
        ]

    def __str__(self):

        return self.description

    def clean(self):
        super().clean()
        if not self.equipment_tag_id and not self.point_number.strip():
            raise ValidationError(
                "Either equipment tag or point number is required."
            )
        errors = {}
        if self.status in {self.PointStatus.ISOLATED, self.PointStatus.VERIFIED}:
            if not self.isolated_by_id:
                errors["isolated_by"] = "Isolated by is required for this status."
            if not self.isolated_at:
                errors["isolated_at"] = "Isolated at is required for this status."
        if self.status == self.PointStatus.RESTORED:
            if not self.restored_by_id:
                errors["restored_by"] = "Restored by is required after restoration."
            if not self.restored_at:
                errors["restored_at"] = "Restored at is required after restoration."
        if self.isolated_at and self.restored_at and self.restored_at < self.isolated_at:
            errors["restored_at"] = "Restoration cannot precede isolation."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# ==========================================================
# Isolation Verification
# ==========================================================

class IsolationVerification(TimeStampedModel):
    """
    Every verification of an isolation point.

    Multiple verifications may exist during the permit lifecycle.
    """

    point = models.ForeignKey(
        IsolationPoint,
        on_delete=models.CASCADE,
        related_name="verifications",
    )

    verified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="isolation_verifications",
    )

    verified_at = models.DateTimeField(
        default=timezone.now,
    )

    passed = models.BooleanField(
        default=True,
    )

    comments = models.TextField(
        blank=True,
    )

    class Meta:

        ordering = [
            "-verified_at",
        ]

    def __str__(self):

        return (
            f"{self.point.description}"
            f" ({self.verified_at:%Y-%m-%d %H:%M})"
        )

    def clean(self):
        super().clean()
        if self.verified_at and self.verified_at > timezone.now():
            raise ValidationError(
                {"verified_at": "Verification time cannot be in the future."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
