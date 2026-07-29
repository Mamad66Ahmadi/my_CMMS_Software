# permits/attachment_models.py

"""
Attachment models for Permit-To-Work.

Stores all supporting documents related to a permit,
including JSA, risk assessments, drawings, certificates,
photographs and other supporting files.

Author: Mohammad Ahmadi
"""

import os

from django.db import models
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from equipment.models.equipment_models import TimeStampedModel
from permits.models.permit_models import Permit

User = get_user_model()


# ==========================================================
# Upload Path
# ==========================================================

def permit_attachment_path(instance, filename):
    attachment = getattr(instance, "attachment", instance)
    extension = os.path.splitext(filename)[1].lower()
    document_reference = (
        attachment.document_number
        or f"document-{attachment.pk or 'new'}"
    )
    revision = getattr(instance, "revision", attachment.revision)

    return (
        f"permits/"
        f"{attachment.permit.permit_number}/"
        f"{attachment.document_type.lower()}/"
        f"{document_reference}_rev-{revision}"
        f"{extension}"
    )


# ==========================================================
# Permit Attachment
# ==========================================================

class PermitAttachment(TimeStampedModel):
    """
    Main attachment record.

    One permit may contain many documents.
    """

    class DocumentType(models.TextChoices):

        JSA = "JSA", "Job Safety Analysis"

        RISK_ASSESSMENT = (
            "RISK_ASSESSMENT",
            "Risk Assessment",
        )

        METHOD_STATEMENT = (
            "METHOD_STATEMENT",
            "Method Statement",
        )

        DRAWING = "DRAWING", "Drawing"

        P_AND_ID = "P_AND_ID", "P&ID"

        ISOMETRIC = "ISOMETRIC", "Isometric"

        LIFTING_PLAN = "LIFTING_PLAN", "Lifting Plan"

        ISOLATION_PLAN = (
            "ISOLATION_PLAN",
            "Isolation Plan",
        )

        GAS_TEST = "GAS_TEST", "Gas Test"

        PHOTO = "PHOTO", "Photograph"

        CERTIFICATE = (
            "CERTIFICATE",
            "Certificate",
        )

        SDS = (
            "SDS",
            "Safety Data Sheet",
        )

        OTHER = "OTHER", "Other"

    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        db_index=True,
    )

    document_number = models.CharField(
        max_length=100,
        blank=True,
    )

    title = models.CharField(
        max_length=250,
    )

    description = models.TextField(
        blank=True,
    )

    file = models.FileField(
        upload_to=permit_attachment_path,
    )

    original_filename = models.CharField(
        max_length=255,
    )

    file_size = models.PositiveBigIntegerField(
        default=0,
    )

    mime_type = models.CharField(
        max_length=100,
        blank=True,
    )

    revision = models.PositiveIntegerField(
        default=1,
    )

    is_latest_revision = models.BooleanField(
        default=True,
        db_index=True,
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="uploaded_permit_documents",
    )

    approved_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="approved_permit_documents",
    )

    approved_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    is_mandatory = models.BooleanField(
        default=False,
    )

    remarks = models.TextField(
        blank=True,
    )

    class Meta:

        ordering = [
            "-created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "permit",
                    "document_type",
                ]
            ),

            models.Index(
                fields=[
                    "document_number",
                ]
            ),

        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(revision__gt=0),
                name="permit_attachment_revision_ck",
            ),
        ]

    def __str__(self):

        return (
            f"{self.permit.permit_number}"
            f" - "
            f"{self.title}"
        )

    def clean(self):
        super().clean()
        self.title = (self.title or "").strip()
        self.document_number = (self.document_number or "").strip().upper()
        self.original_filename = (self.original_filename or "").strip()

        if self.approved_by_id and not self.approved_at:
            raise ValidationError(
                {"approved_at": "Approval time is required when approved by is set."}
            )
        if self.approved_at and not self.approved_by_id:
            raise ValidationError(
                {"approved_by": "Approver is required when approval time is set."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# ==========================================================
# Attachment Version
# ==========================================================

class AttachmentVersion(TimeStampedModel):
    """
    Stores historical revisions of a document.
    """

    attachment = models.ForeignKey(
        PermitAttachment,
        on_delete=models.CASCADE,
        related_name="versions",
    )

    revision = models.PositiveIntegerField()

    file = models.FileField(
        upload_to=permit_attachment_path,
    )

    change_description = models.TextField(
        blank=True,
    )

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="attachment_versions",
    )

    class Meta:

        ordering = [
            "-revision",
        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "attachment",
                    "revision",
                ],
                name="uq_attachment_revision",
            ),
            models.CheckConstraint(
                condition=Q(revision__gt=0),
                name="attachment_version_revision_ck",
            ),

        ]

    def __str__(self):

        return (
            f"{self.attachment.title}"
            f" Rev.{self.revision}"
        )
