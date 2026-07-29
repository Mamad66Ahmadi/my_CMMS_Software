# permits/models/history_models.py

"""
Audit history models for Permit-To-Work.

Every significant action performed on a permit is recorded
to provide a complete audit trail.

History records are append-only and should never be edited
or deleted during normal system operation.

Author: Mohammad Ahmadi
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from equipment.models.equipment_models import TimeStampedModel
from permits.models.permit_models import Permit


User = get_user_model()


# ==========================================================
# Permit History
# ==========================================================

class PermitHistory(TimeStampedModel):
    """
    Immutable audit log for Permit-To-Work.
    """

    class EventType(models.TextChoices):

        CREATED = "CREATED", "Permit Created"

        UPDATED = "UPDATED", "Permit Updated"

        SUBMITTED = "SUBMITTED", "Submitted"

        APPROVED = "APPROVED", "Approved"

        REJECTED = "REJECTED", "Rejected"

        RETURNED = "RETURNED", "Returned"

        ISSUED = "ISSUED", "Issued"

        ACTIVATED = "ACTIVATED", "Activated"

        SUSPENDED = "SUSPENDED", "Suspended"

        RESUMED = "RESUMED", "Resumed"

        GAS_TEST = "GAS_TEST", "Gas Test"

        GAS_TEST_FAILED = "GAS_TEST_FAILED", "Gas Test Failed"

        GAS_TEST_PASSED = "GAS_TEST_PASSED", "Gas Test Passed"

        ISOLATION_APPLIED = (
            "ISOLATION_APPLIED",
            "Isolation Applied",
        )

        ISOLATION_REMOVED = (
            "ISOLATION_REMOVED",
            "Isolation Removed",
        )

        FIRE_GAS_INHIBITED = (
            "FIRE_GAS_INHIBITED",
            "Fire & Gas Inhibited",
        )

        FIRE_GAS_RESTORED = (
            "FIRE_GAS_RESTORED",
            "Fire & Gas Restored",
        )

        SHIFT_HANDOVER = (
            "SHIFT_HANDOVER",
            "Shift Handover",
        )

        EXTENDED = "EXTENDED", "Permit Extended"

        ATTACHMENT_UPLOADED = (
            "ATTACHMENT_UPLOADED",
            "Attachment Uploaded",
        )

        ATTACHMENT_REMOVED = (
            "ATTACHMENT_REMOVED",
            "Attachment Removed",
        )

        COMPLETED = "COMPLETED", "Work Completed"

        CLOSED = "CLOSED", "Permit Closed"

        CANCELLED = "CANCELLED", "Cancelled"

    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="history",
    )

    event_type = models.CharField(
        max_length=40,
        choices=EventType.choices,
        db_index=True,
    )

    event_datetime = models.DateTimeField(
        default=timezone.now,
        db_index=True,
    )

    performed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="permit_history_events",
    )

    title = models.CharField(
        max_length=200,
    )

    description = models.TextField(
        blank=True,
    )

    old_value = models.TextField(
        blank=True,
    )

    new_value = models.TextField(
        blank=True,
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
    )

    user_agent = models.TextField(
        blank=True,
    )

    class Meta:

        ordering = [
            "-event_datetime",
        ]

        indexes = [

            models.Index(
                fields=[
                    "permit",
                    "event_datetime",
                ]
            ),

            models.Index(
                fields=[
                    "event_type",
                ]
            ),

        ]

    def __str__(self):

        return (
            f"{self.permit.permit_number}"
            f" - "
            f"{self.get_event_type_display()}"
        )

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Permit history entries are append-only.")
        return super().save(*args, **kwargs)


# ==========================================================
# Permit Comment
# ==========================================================

class PermitComment(TimeStampedModel):
    """
    Operational discussion related to a permit.

    Unlike PermitHistory, comments are conversations
    between operations, maintenance and HSE.
    """

    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="permit_comments",
    )

    comment = models.TextField()

    is_internal = models.BooleanField(
        default=False,
        help_text="Visible only to internal users.",
    )

    parent_comment = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
    )

    class Meta:

        ordering = [
            "created_at",
        ]

    def __str__(self):

        return (
            f"{self.author} - "
            f"{self.created_at:%Y-%m-%d %H:%M}"
        )

    def clean(self):
        super().clean()
        if self.parent_comment_id:
            if self.pk and self.parent_comment_id == self.pk:
                raise ValidationError(
                    {"parent_comment": "A comment cannot reply to itself."}
                )
            if self.parent_comment.permit_id != self.permit_id:
                raise ValidationError(
                    {"parent_comment": "Parent comment must belong to this permit."}
                )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
