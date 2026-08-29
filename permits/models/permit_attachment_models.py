"""Permit attachment model and attachment authorization helpers."""

from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone


MAX_ATTACHMENT_SIZE = 25 * 1024 * 1024


def validate_attachment_size(upload):
    """Reject files larger than the PTW attachment limit (25 MiB)."""

    if upload and upload.size > MAX_ATTACHMENT_SIZE:
        raise ValidationError(
            "Attachment size must not exceed 25 MB "
            f"(received {upload.size / (1024 * 1024):.1f} MB)."
        )


def permit_attachment_upload_to(instance, filename):
    """Keep files grouped by permit number and attachment UUID."""

    suffix = Path(filename).suffix.lower()
    return f"permits/{instance.permit.permit_number}/attachments/{instance.attachment_id}{suffix}"


class PermitAttachment(models.Model):
    """
    A document attached to a permit.

    Attachments remain available for viewing/downloading throughout the
    workflow, including terminal/closed steps.  Mutation authorization is
    deliberately exposed as model methods so admin and future service/view
    layers use the same policy.
    """

    permit = models.ForeignKey(
        "permits.Permit",
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    attachment_id = models.UUIDField(
        default=uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    file = models.FileField(
        upload_to=permit_attachment_upload_to,
        validators=[
            validate_attachment_size,
        ],
        help_text="Maximum size: 25 MB.",
    )
    title = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="permit_attachments_uploaded",
    )
    uploaded_at = models.DateTimeField(default=timezone.now, editable=False)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="permit_attachments_modified",
    )

    class Meta:
        ordering = ["-uploaded_at", "-pk"]
        verbose_name = "Permit Attachment"
        verbose_name_plural = "Permit Attachments"
        indexes = [
            models.Index(fields=["permit", "-uploaded_at"], name="permit_att_permit_date_idx"),
            models.Index(fields=["uploaded_by", "-uploaded_at"], name="permit_att_uploader_date_idx"),
        ]

    def __str__(self):
        return self.title or Path(self.file.name).name or f"Attachment {self.pk}"

    @property
    def filename(self):
        return Path(self.file.name).name

    @property
    def file_size(self):
        try:
            return self.file.size
        except (FileNotFoundError, OSError, ValueError):
            return None

    def clean(self):
        super().clean()
        if self.file:
            validate_attachment_size(self.file)
        if self.title:
            self.title = self.title.strip()

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @classmethod
    def _is_permit_office(cls, actor):
        if not actor or not actor.is_authenticated:
            return False
        from permits.models.approval_models import PermitApprovalRoleAssignment

        return PermitApprovalRoleAssignment.objects.filter(
            user=actor,
            is_active=True,
            role__is_active=True,
        ).filter(
            Q(role__code__iexact="PERMIT_OFFICE")
            | Q(role__code__iexact="Permit Office")
            | Q(role__name__iexact="Permit Office")
        ).exists()

    @classmethod
    def actor_can_manage_all(cls, actor):
        return bool(
            actor
            and actor.is_authenticated
            and (actor.is_superuser or cls._is_permit_office(actor))
        )

    @classmethod
    def actor_can_add_for_permit(cls, actor, permit):
        if cls.actor_can_manage_all(actor):
            return True
        if not actor or not actor.is_authenticated or not permit:
            return False

        # A contributor may add at any workflow step, including closed.  A
        # role is eligible when it is configured on a transition or as the
        # step's editable role, and the normal assignment scope checks pass.
        role_ids = set(
            permit.workflow.transitions.filter(
                role__is_active=True,
            ).values_list("role_id", flat=True)
        )
        role_ids.update(
            permit.workflow.steps.filter(
                editable_role__isnull=False,
                editable_role__is_active=True,
            ).values_list("editable_role_id", flat=True)
        )
        if not role_ids:
            return False

        from permits.models.approval_models import PermitApprovalRoleChoices
        from permits.services.authorization_service import WorkflowAuthorizationService

        for role in PermitApprovalRoleChoices.objects.filter(pk__in=role_ids):
            if WorkflowAuthorizationService.actor_has_role_for_permit(
                actor=actor,
                permit=permit,
                role=role,
            ):
                return True
        return False

    def actor_can_change(self, actor):
        return self.actor_can_manage_all(actor)

    def actor_can_delete(self, actor):
        return bool(
            actor
            and actor.is_authenticated
            and (
                self.actor_can_manage_all(actor)
                or self.uploaded_by_id == actor.pk
            )
        )
