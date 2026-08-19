# permits/models/permit_fg_esd_models.py

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from permits.models import BaseLookupModel

User = settings.AUTH_USER_MODEL


# =============================================================================
# Fire, Gas & ESD Master Data
# =============================================================================
class FireGasESD(BaseLookupModel):

    role = models.ForeignKey(
        "PermitApprovalRoleChoices",
        on_delete=models.PROTECT,
        related_name="fire_gas_isolations",
        help_text="The role authorized to perform and confirm this type of isolation.",
    )

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Fire, Gas & ESD"
        verbose_name_plural = "Fire, Gas & ESDs"


# =============================================================================
# Permit Fire, Gas & ESD Isolation / De-isolation
# =============================================================================
class PermitFireGasESD(models.Model):
    permit = models.ForeignKey(
        "Permit",
        on_delete=models.CASCADE,
        related_name="permit_fire_gas_esd_items",
    )
    fire_gas_esd = models.ForeignKey(
        "FireGasESD",
        on_delete=models.PROTECT,
        related_name="permit_links",
    )

    unit_zone = models.CharField(
        max_length=100,
        help_text="Unit, area, or zone where this Fire/Gas/ESD isolation applies.",
    )

    remarks = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Isolation
    # ------------------------------------------------------------------
    isolated_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The actual time the isolation was performed.",
    )
    isolated_confirmed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="confirmed_fg_esd_isolations",
    )
    isolated_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The time the isolation confirmation was recorded.",
    )

    # ------------------------------------------------------------------
    # De-isolation
    # ------------------------------------------------------------------
    deisolated_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The actual time the de-isolation was performed.",
    )
    deisolated_confirmed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="confirmed_fg_esd_deisolations",
    )
    deisolated_confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="The time the de-isolation confirmation was recorded.",
    )

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="created_permit_fire_gas_esd_items",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modified_permit_fire_gas_esd_items",
    )

    class Meta:
        verbose_name = "Permit Fire, Gas & ESD Item"
        verbose_name_plural = "Permit Fire, Gas & ESD Items"
        ordering = ["permit", "fire_gas_esd", "unit_zone", "pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "fire_gas_esd", "unit_zone"],
                name="permit_fg_esd_unique_per_zone",
            ),
            models.CheckConstraint(
                condition=Q(isolated_confirmed_at__isnull=True)
                | Q(isolated_time__isnull=False),
                name="permit_fg_esd_isolated_confirm_requires_time_ck",
            ),
            models.CheckConstraint(
                condition=Q(deisolated_confirmed_at__isnull=True)
                | Q(deisolated_time__isnull=False),
                name="permit_fg_esd_deisolated_confirm_requires_time_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit} - {self.fire_gas_esd} - {self.unit_zone}"

    def clean(self):
        super().clean()

        self.unit_zone = (self.unit_zone or "").strip()

        if not self.unit_zone:
            raise ValidationError({"unit_zone": "Unit/Zone is required."})

        if self.isolated_confirmed_by and not self.isolated_confirmed_at:
            raise ValidationError(
                {
                    "isolated_confirmed_at": (
                        "Isolation confirmation time is required when a confirmer is selected."
                    )
                }
            )

        if self.isolated_confirmed_at and not self.isolated_confirmed_by:
            raise ValidationError(
                {
                    "isolated_confirmed_by": (
                        "Isolation confirmer is required when confirmation time is entered."
                    )
                }
            )

        if self.deisolated_confirmed_by and not self.deisolated_confirmed_at:
            raise ValidationError(
                {
                    "deisolated_confirmed_at": (
                        "De-isolation confirmation time is required when a confirmer is selected."
                    )
                }
            )

        if self.deisolated_confirmed_at and not self.deisolated_confirmed_by:
            raise ValidationError(
                {
                    "deisolated_confirmed_by": (
                        "De-isolation confirmer is required when confirmation time is entered."
                    )
                }
            )

        if self.deisolated_time and not self.isolated_time:
            raise ValidationError(
                {
                    "deisolated_time": (
                        "De-isolation cannot be recorded before isolation."
                    )
                }
            )

        if self.isolated_time and self.deisolated_time:
            if self.deisolated_time < self.isolated_time:
                raise ValidationError(
                    {
                        "deisolated_time": (
                            "De-isolation time must be after isolation time."
                        )
                    }
                )

        if self.isolated_confirmed_at and self.isolated_time:
            if self.isolated_confirmed_at < self.isolated_time:
                raise ValidationError(
                    {
                        "isolated_confirmed_at": (
                            "Isolation confirmation time cannot be earlier than isolation time."
                        )
                    }
                )

        if self.deisolated_confirmed_at and self.deisolated_time:
            if self.deisolated_confirmed_at < self.deisolated_time:
                raise ValidationError(
                    {
                        "deisolated_confirmed_at": (
                            "De-isolation confirmation time cannot be earlier than de-isolation time."
                        )
                    }
                )

        if self.deisolated_confirmed_at and not self.deisolated_time:
            raise ValidationError(
                {
                    "deisolated_time": (
                        "De-isolation time is required before de-isolation can be confirmed."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_isolated(self):
        return self.isolated_time is not None and self.isolated_confirmed_at is not None

    @property
    def is_deisolated(self):
        return self.deisolated_time is not None and self.deisolated_confirmed_at is not None
