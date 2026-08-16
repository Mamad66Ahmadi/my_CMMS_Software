# permits/models/permit_closeout_models.py

from django.db import models
from django.utils import timezone
from django.conf import settings
from django.core.exceptions import ValidationError


from permits.models import BaseLookupModel,PermitApprovalRoleChoices,Permit


# =============================================================================
# Permit Close out
# =============================================================================
class PermitCloseoutItem(BaseLookupModel):
    """
    A reusable close-out/sign-off requirement.

    Example:
        code: HOUSEKEEPING
        name: Work area restored and housekeeping completed
        role: Area Authority
    """

    role = models.ForeignKey(
        PermitApprovalRoleChoices,
        on_delete=models.PROTECT,
        related_name="closeout_items",
    )

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Permit Close-out Item"
        verbose_name_plural = "Permit Close-out Items"

    def __str__(self):
        return f"{self.code} - {self.name}"





# =============================================================================
# Permit Closeout Signoff
# =============================================================================
class PermitCloseoutSignoff(models.Model):
    """
    A permit-specific close-out requirement and its actual sign-off data.

    This model is created when the permit enters the close-out workflow step.
    Its signature fields can only be updated while the permit remains there.
    """

    permit = models.ForeignKey(Permit, on_delete=models.CASCADE, related_name="closeout_signoffs",)

    closeout_item = models.ForeignKey(PermitCloseoutItem, on_delete=models.PROTECT, related_name="permit_signoffs",)

    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT, related_name="permit_closeout_signoffs",)

    signed_at = models.DateTimeField(null=True, blank=True,)

    remarks = models.TextField(blank=True,)

    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_permit_closeout_signoffs",)




    class Meta:
        ordering = [
            "closeout_item__display_order",
            "closeout_item__code",
            "pk",
        ]
        verbose_name = "Permit Close-out Sign-off"
        verbose_name_plural = "Permit Close-out Sign-offs"
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "closeout_item"],
                name="unique_permit_closeout_item",
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(signed_by__isnull=True, signed_at__isnull=True)
                    | models.Q(signed_by__isnull=False, signed_at__isnull=False)
                ),
                name="permit_closeout_signer_timestamp_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit} - {self.closeout_item}"

    def clean(self):
        super().clean()

        if not self.permit_id:
            return

        current_step = self.permit.current_step

        # Rename `is_closeout_step` if you adopt another workflow-step field name.
        if not current_step or current_step.state != current_step.State.ACTIVE:
            raise ValidationError(
                {
                    "permit": (
                        "Close-out sign-off data may only be entered while the "
                        "permit is at its designated close-out step."
                    )
                }
            )

        if self.signed_at and not self.signed_by_id:
            raise ValidationError(
                {
                    "signed_by": (
                        "A signer is required when a sign-off timestamp is set."
                    )
                }
            )


    def save(self, *args, **kwargs):
        if self.signed_by_id and not self.signed_at:
            self.signed_at = timezone.now()
        self.full_clean()
        return super().save(*args, **kwargs)
