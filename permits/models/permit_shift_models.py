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

    permit = models.ForeignKey("permits.Permit", on_delete=models.CASCADE,  related_name="work_shifts",)

    date = models.DateField()

    shift = models.CharField(max_length=20, choices=Shift.choices,)

    work_leader = models.CharField(max_length=45, blank=True, null=True,)

    created_at = models.DateTimeField(auto_now_add=True,)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="created_permit_work_shifts",)

    class Meta:
        ordering = ["date", "shift"]

        constraints = [
            models.UniqueConstraint(
                fields=["permit", "date", "shift"],
                name="uq_permit_work_shift",
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
                f"{self.permit_type} - "
                f"{self.role} - "
                f"{self.sequence}"
            )



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



