"""Application-level quotas for permit and attachment creation."""

from django.core.exceptions import ValidationError
from django.utils import timezone

from permits.models.permit_attachment_models import PermitAttachment
from permits.models.permit_models import Permit
from permits.models.workflow_models import PermitWorkflowStep

MAX_ATTACHMENTS_PER_PERMIT = 50
MAX_UPLOADS_PER_USER_PER_DAY = 100
MAX_UPLOAD_BYTES_PER_USER_PER_DAY = 500 * 1024 * 1024
MAX_PERMITS_CREATED_PER_USER_PER_DAY = 30
MAX_DRAFT_PERMITS_PER_USER = 50


class PermitQuotaService:
    @staticmethod
    def _today():
        return timezone.localdate()

    @classmethod
    def ensure_can_add_attachment(cls, *, actor, permit, upload):
        if not actor or not actor.is_authenticated:
            raise ValidationError("Authentication is required.")
        if permit.attachments.count() >= MAX_ATTACHMENTS_PER_PERMIT:
            raise ValidationError(
                f"This permit has reached the maximum allowed limit of {MAX_ATTACHMENTS_PER_PERMIT} attachments."
            )
        today_uploads = PermitAttachment.objects.filter(
            uploaded_by=actor, uploaded_at__date=cls._today()
        )
        if today_uploads.count() >= MAX_UPLOADS_PER_USER_PER_DAY:
            raise ValidationError(
                f"Daily file upload limit reached. A maximum of {MAX_UPLOADS_PER_USER_PER_DAY} files may be uploaded per day."
            )
        incoming_size = getattr(upload, "size", 0) or 0
        uploaded_bytes = sum(
            (attachment.file_size or 0) for attachment in today_uploads.only("file")
        )
        if uploaded_bytes + incoming_size > MAX_UPLOAD_BYTES_PER_USER_PER_DAY:
            raise ValidationError("Daily upload storage limit reached (500 MB).")

    @classmethod
    def ensure_can_create_permit(cls, *, actor):
        if not actor or not actor.is_authenticated:
            raise ValidationError("Authentication is required.")
        if Permit.objects.filter(
            created_by=actor, created_at__date=cls._today()
        ).count() >= MAX_PERMITS_CREATED_PER_USER_PER_DAY:
            raise ValidationError(
                f"Daily permit creation limit reached ({MAX_PERMITS_CREATED_PER_USER_PER_DAY} permits)."
            )
        if Permit.objects.filter(
            created_by=actor,
            current_step__state=PermitWorkflowStep.State.DRAFT,
        ).count() >= MAX_DRAFT_PERMITS_PER_USER:
            raise ValidationError(
                f"The maximum number of draft permits allowed per user is {MAX_DRAFT_PERMITS_PER_USER}. To continue, please complete the activation process or cancel your pending drafts."
            )
