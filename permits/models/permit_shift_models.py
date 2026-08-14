# permits/models/permit_shift_models.py

from django.db import models
from django.conf import settings
from django.db.models import Q


from permits.models.approval_models import PermitApprovalRoleChoices
from permits.models.permit_base_models import PermitType
from equipment.models.equipment_models import TimeStampedModel


class Shift(models.TextChoices):
    SHIFT_1 = "SHIFT_1", "Shift 1"
    SHIFT_2 = "SHIFT_2", "Shift 2"


class PermitWorkShift(models.Model):

    class Status(models.TextChoices):
        OPEN = "open", "Open"
        CLOSED = "closed", "Closed"

    permit = models.ForeignKey("permits.Permit", on_delete=models.CASCADE,  related_name="work_shifts",)

    date = models.DateField()

    shift = models.CharField(max_length=20, choices=Shift.choices,)

    work_leader = models.CharField(max_length=45, blank=True, null=True,)
    worker_count = models.PositiveIntegerField(null=True, blank=True, verbose_name="Number of workers", help_text="Number of workers planned to work during this shift.", )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    closed_at = models.DateTimeField(blank=True, null=True)

    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        blank=True,
        null=True,
        on_delete=models.PROTECT,
        related_name="closed_permit_work_shifts",
    )

    created_at = models.DateTimeField(auto_now_add=True,)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_permit_work_shifts",)

    class Meta:
        ordering = ["date", "shift"]

        constraints = [
            models.UniqueConstraint(
                fields=["permit", "date", "shift"],
                name="uq_permit_work_shift",
            ),
            models.UniqueConstraint(
                fields=["permit"],
                condition=Q(status="open"),
                name="uq_one_open_work_shift_per_permit",
            ),
        ]

    def __str__(self):
        return (
            f"{self.permit.permit_number} - "
            f"{self.date} - "
            f"{self.get_shift_display()}"
        )





class PermitShiftSignoff(models.Model):

    work_shift = models.ForeignKey(PermitWorkShift, on_delete=models.CASCADE, related_name="signoffs",)

    role = models.ForeignKey(PermitApprovalRoleChoices, on_delete=models.PROTECT, related_name="shift_signoffs",)

    # Keep the requirement as it was when the shift was released.  Editing a
    # permit type later must not change the signatures required for a shift
    # that already exists.
    sequence = models.PositiveSmallIntegerField(default=1)

    is_required = models.BooleanField(default=True)

    signed_by = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.PROTECT, related_name="permit_shift_signoffs",)

    signed_at = models.DateTimeField(null=True,blank=True,)


    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["work_shift", "role"],
                name="uq_work_shift_role_signoff",
            ),
            models.CheckConstraint(
                condition=(
                    Q(signed_by__isnull=True, signed_at__isnull=True)
                    | Q(signed_by__isnull=False, signed_at__isnull=False)
                ),
                name="shift_signoff_user_time_consistent",
            ),
        ]

    def __str__(self):
        return (
            f"{self.work_shift} - "
            f"{self.role.name} - "
            f"{self.signed_by}"
        )


class PermitTypeActiveShiftRole(TimeStampedModel):

    permit_type = models.ForeignKey(PermitType, on_delete=models.CASCADE, related_name="active_shift_roles",)

    role = models.ForeignKey(PermitApprovalRoleChoices, on_delete=models.PROTECT, related_name="permit_type_active_shift_roles",)

    sequence = models.PositiveSmallIntegerField( default=1,)

    is_required = models.BooleanField( default=True,)

    class Meta:
        ordering = ["sequence", "id"]

        constraints = [
            models.UniqueConstraint(
                fields=["permit_type", "role"],
                name="uq_permit_type_active_shift_role",
            ),
        ]

    def __str__(self):
        return (
            f"{self.permit_type} - "
            f"{self.role} - "
            f"{self.sequence}"
        )

