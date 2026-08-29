"""Authorization and mutation services for Permit attachments.

Attachments are treated as controlled permit documents: they remain readable
throughout the permit lifecycle, while mutation rights are derived from the
permit-office policy and the roles configured on the permit's workflow.
"""

from django.core.exceptions import PermissionDenied
from django.db import transaction

from permits.models.approval_models import PermitApprovalRoleChoices
from permits.models.permit_attachment_models import PermitAttachment
from permits.services.authorization_service import WorkflowAuthorizationService


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
        if cls.actor_can_manage_all(actor=actor):
            return True
        return cls._actor_has_workflow_role(actor=actor, permit=permit)

    @classmethod
    def actor_can_change(cls, *, actor, attachment):
        return bool(
            attachment
            and cls.actor_can_manage_all(actor=actor)
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
                "Only Superusers and Permit Office may edit attachments."
            )

    @classmethod
    def ensure_can_delete(cls, *, actor, attachment):
        if not cls.actor_can_delete(actor=actor, attachment=attachment):
            raise PermissionDenied(
                "You may delete only attachments that you uploaded."
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

    @classmethod
    def _actor_has_workflow_role(cls, *, actor, permit):
        if not actor or not actor.is_authenticated or not permit or not permit.workflow_id:
            return False

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
        roles = PermitApprovalRoleChoices.objects.filter(
            pk__in=role_ids,
            is_active=True,
        )
        return any(
            WorkflowAuthorizationService.actor_has_role_for_permit(
                actor=actor,
                permit=permit,
                role=role,
            )
            for role in roles
        )
