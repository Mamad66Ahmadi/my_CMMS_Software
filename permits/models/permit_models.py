from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from permits.models import permit_base_models, PermitStatus
from equipment.models.equipment_models import LocationTag
from work_orders.models.wo_models import WorkOrder


User = get_user_model()


class Permit(models.Model):
    permit_number = models.CharField(max_length=50,unique=True,null=False,blank=False,db_index=True,verbose_name="Permit Number",)

    continuation_of = models.ForeignKey("self",on_delete=models.SET_NULL,null=True,blank=True,related_name="continuations",)

    hazard_codes = models.ManyToManyField(permit_base_models.HazardCode,related_name="permits",blank=True,)

    location_tag = models.ForeignKey(LocationTag,on_delete=models.PROTECT,related_name="permits",null=True,blank=True,)

    description = models.TextField()

    work_order = models.ForeignKey(WorkOrder,on_delete=models.SET_NULL,null=True,blank=True,related_name="permits",)

    department = models.ForeignKey("accounts.Department",on_delete=models.PROTECT, related_name="permits",)

    authorized_issuer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="issued_permits",)

    permit_holder = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="held_permits",)

    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    is_excavation = models.BooleanField(default=False)
    requires_loto = models.BooleanField(default=False)
    is_confined_space = models.BooleanField(default=False)
    is_equipment_test = models.BooleanField(default=False)
    is_radiography = models.BooleanField(default=False)
    is_diving = models.BooleanField(default=False)

    status = models.CharField(max_length=50,choices=PermitStatus.choices, default=PermitStatus.DRAFT, db_index=True,)
    comment = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name="created_permits",)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL,null=True,blank=True,related_name="modified_permits",)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["valid_from"]),
            models.Index(fields=["valid_to"]),
        ]

    def __str__(self):
        return self.permit_number

    def clean(self):
        if self.permit_number:
            self.permit_number = self.permit_number.strip()

        if not self.permit_number:
            raise ValidationError({"permit_number": "Permit number is required."})

        if not self.location_tag and not self.work_order:
            raise ValidationError("Either location tag or work order must be provided.")

        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "Valid-to must be after valid-from."})

    def save(self, *args, **kwargs):
        if self.work_order and not self.location_tag:
            self.location_tag = self.work_order.location_tag

        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_currently_valid(self):
        now = timezone.now()
        return (
            self.status == PermitStatus.ACTIVE
            and self.valid_from <= now <= self.valid_to
        )

    @property
    def special_conditions_summary(self):
        flags = {
            "Excavation": self.is_excavation,
            "Requires LOTO": self.requires_loto,
            "Confined Space": self.is_confined_space,
            "Equipment Test": self.is_equipment_test,
            "Radiography": self.is_radiography,
            "Diving": self.is_diving,
        }
        active = [name for name, value in flags.items() if value]
        return ", ".join(active) if active else "None"
