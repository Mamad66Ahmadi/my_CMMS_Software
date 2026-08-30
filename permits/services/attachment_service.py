"""Authorization and mutation services for Permit attachments.

Attachments are treated as controlled permit documents: they remain readable
throughout the permit lifecycle. Any authenticated user may add one; edits and
deletions are limited to the uploader, Permit Office, or superusers.
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from permits.models.permit_attachment_models import PermitAttachment


class PermitAttachmentService:
    """Single policy boundary for attachment access and mutations."""

    @staticmethod
    def actor_can_view(*, actor, attachment=None, permit=None):
        """Any authenticated user may view/download permit attachments."""

        return bool(actor and actor.is_authenticated and (attachment or permit))

    @classmethod
    def actor_can_manage_all(cls, *, actor):
        return PermitAttachment.actor_can_manage_all(actor)

    @classmethod
    def actor_can_add(cls, *, actor, permit):
        # Every authenticated user may add an attachment to any existing
        # permit.  The elevated Permit Office/superuser check is relevant to
        # editing and deleting attachments globally, not to uploading.
        return bool(actor and actor.is_authenticated and permit)

    @classmethod
    def actor_can_change(cls, *, actor, attachment):
        return bool(
            attachment
            and actor
            and actor.is_authenticated
            and (
                cls.actor_can_manage_all(actor=actor)
                or attachment.uploaded_by_id == actor.pk
            )
        )

    @classmethod
    def actor_can_delete(cls, *, actor, attachment):
        return bool(
            attachment
            and actor
            and actor.is_authenticated
            and (
                cls.actor_can_manage_all(actor=actor)
                or attachment.uploaded_by_id == actor.pk
            )
        )

    @classmethod
    def ensure_can_add(cls, *, actor, permit):
        if not cls.actor_can_add(actor=actor, permit=permit):
            raise PermissionDenied(
                "You do not hold an active workflow role scoped to this permit."
            )

    @classmethod
    def ensure_can_change(cls, *, actor, attachment):
        if not cls.actor_can_change(actor=actor, attachment=attachment):
            raise PermissionDenied(
                "You may edit only attachments that you uploaded."
            )

    @classmethod
    def ensure_can_delete(cls, *, actor, attachment):
        if not cls.actor_can_delete(actor=actor, attachment=attachment):
            raise PermissionDenied(
                "You may delete only attachments that you uploaded, unless you are "
                "Permit Office or a superuser."
            )

    @classmethod
    @transaction.atomic
    def add(cls, *, actor, permit, file, title="", description=""):
        cls.ensure_can_add(actor=actor, permit=permit)
        attachment = PermitAttachment(
            permit=permit,
            file=file,
            title=title,
            description=description,
            uploaded_by=actor,
            modified_by=actor,
        )
        attachment.save()
        return attachment

    @classmethod
    @transaction.atomic
    def change(cls, *, actor, attachment, **values):
        cls.ensure_can_change(actor=actor, attachment=attachment)
        for field in ("file", "title", "description"):
            if field in values:
                setattr(attachment, field, values[field])
        attachment.modified_by = actor
        attachment.save()
        return attachment

    @classmethod
    @transaction.atomic
    def remove(cls, *, actor, attachment):
        cls.ensure_can_delete(actor=actor, attachment=attachment)
        attachment.delete()
