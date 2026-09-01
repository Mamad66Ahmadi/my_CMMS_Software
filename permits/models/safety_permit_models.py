
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from accounts.models import Department
from equipment.models.equipment_models import LocationTag
from work_orders.models.wo_models import WorkOrder


class SafetyPermit(models.Model):
    """
    Common parent record for all safety permits.

    The concrete child models below intentionally contain no fields yet. They
    will hold the subtype-specific data once each safety-permit procedure is
    defined.
    """

    class SafetyType(models.TextChoices):
        ISOLATION = "ISOLATION", "Isolation"
        CONFINED_SPACE = "CONFINED_SPACE", "Confined Space"
        DIVING = "DIVING", "Diving"
        EXCAVATION = "EXCAVATION", "Excavation"
        EQUIPMENT_TEST = "EQUIPMENT_TEST", "Equipment Test"
        RADIOGRAPHY = "RADIOGRAPHY", "Radiography"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        ALLOWED = "ALLOWED", "Allowed"
        ACTIVE = "ACTIVE", "Active"
        SUSPENDED = "SUSPENDED", "Suspended"
        COMPLETED = "COMPLETED", "Completed"
        CLOSED = "CLOSED", "Closed"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    permit_number = models.CharField(max_length=30, unique=True, db_index=True)
    safety_type = models.CharField(max_length=30, choices=SafetyType.choices, db_index=True)

    work_order = models.ForeignKey(
        WorkOrder,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="safety_permits",
    )
    location_tag = models.ForeignKey(
        LocationTag,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="safety_permits",
    )
    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="safety_permits",
    )
    scope_of_work = models.TextField(blank=True)

    # Workflows will be configured after the safety-permit procedures are
    # defined, so both references are intentionally nullable for now.
    workflow = models.ForeignKey(
        "permits.PermitWorkflow",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="safety_permits",
    )


    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_safety_permits",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modified_safety_permits",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Safety Permit"
        verbose_name_plural = "Safety Permits"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True)
                | Q(valid_to__isnull=True)
                | Q(valid_to__gt=models.F("valid_from")),
                name="safety_permit_valid_window_ck",
            ),
        ]
        indexes = [
            models.Index(fields=["safety_type", "status"], name="safety_type_status_idx"),
            models.Index(fields=["location_tag", "status"], name="safety_loc_status_idx"),
            models.Index(fields=["work_order", "status"], name="safety_wo_status_idx"),
        ]

    def __str__(self):
        return self.permit_number

    def clean(self):
        super().clean()

        self.permit_number = (self.permit_number or "").strip().upper()
        if not self.permit_number:
            raise ValidationError({"permit_number": "Safety permit number is required."})


        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "Valid To must be after Valid From."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


class IsolationPermit(SafetyPermit):
    class Meta:
        verbose_name = "Isolation Safety Permit"
        verbose_name_plural = "Isolation Safety Permits"


class ConfinedSpacePermit(SafetyPermit):
    class Meta:
        verbose_name = "Confined Space Safety Permit"
        verbose_name_plural = "Confined Space Safety Permits"


class DivingPermit(SafetyPermit):
    class Meta:
        verbose_name = "Diving Safety Permit"
        verbose_name_plural = "Diving Safety Permits"


class ExcavationPermit(SafetyPermit):
    class Meta:
        verbose_name = "Excavation Safety Permit"
        verbose_name_plural = "Excavation Safety Permits"


class EquipmentTestPermit(SafetyPermit):
    class Meta:
        verbose_name = "Equipment Test Safety Permit"
        verbose_name_plural = "Equipment Test Safety Permits"


class RadiographyPermit(SafetyPermit):
    class Meta:
        verbose_name = "Radiography Safety Permit"
        verbose_name_plural = "Radiography Safety Permits"


class PermitSafetyRequirement(models.Model):
    """
    Formal dependency between a main Permit and a SafetyPermit.
    """

    class RequiredStatus(models.TextChoices):
        ALLOWED = SafetyPermit.Status.ALLOWED, "Allowed"
        ACTIVE = SafetyPermit.Status.ACTIVE, "Active"

    permit = models.ForeignKey(
        "permits.Permit",
        on_delete=models.CASCADE,
        related_name="safety_requirements",
    )
    safety_permit = models.ForeignKey(
        SafetyPermit,
        on_delete=models.PROTECT,
        related_name="main_permit_requirements",
    )
    required_status = models.CharField(
        max_length=20,
        choices=RequiredStatus.choices,
        default=RequiredStatus.ALLOWED,
    )
    is_mandatory = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_permit_safety_requirements",
    )

    class Meta:
        ordering = ["permit", "safety_permit", "pk"]
        verbose_name = "Permit Safety Requirement"
        verbose_name_plural = "Permit Safety Requirements"
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "safety_permit"],
                name="uq_permit_safety_requirement",
            ),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True)
                | Q(valid_to__isnull=True)
                | Q(valid_to__gt=models.F("valid_from")),
                name="permit_safety_req_valid_window_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit} requires {self.safety_permit}"

    def clean(self):
        super().clean()
        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValidationError({"valid_to": "Valid To must be after Valid From."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
