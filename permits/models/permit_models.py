# permits/models/permit_models.py

"""
Permit Header Model

This model represents the main Permit-To-Work document.

Child models:
    - PermitGasTest
    - PermitApproval
    - PermitIsolation
    - PermitFireGas
    - PermitShiftLog
    - PermitAttachment
    - PermitHistory
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.utils import timezone


from accounts.models import Department

from equipment.models.equipment_models import LocationTag

from work_orders.models.wo_models import WorkOrder
from permits.models.workflow_models import PermitWorkflowStep
from permits.models.permit_base_models import (
    PermitType,
    Hazard,
    Precaution,
    EquipmentStatus,
    PermitStatus,
    DurationUnit
)

User = get_user_model()

permit_identifier_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9._-]*$",
    message=(
        "Use uppercase letters, numbers, periods, underscores, or hyphens only."
    ),
)


class Permit(models.Model):

    # ------------------------------------------------------------------
    # Identification
    # ------------------------------------------------------------------

    permit_number = models.CharField(max_length=30, unique=True, db_index=True, validators=[permit_identifier_validator],)

    continuation_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="continuations",)

    current_step = models.ForeignKey(PermitWorkflowStep, null=True, blank=True, on_delete=models.PROTECT, related_name="permits_at_step",)

    # ------------------------------------------------------------------
    # Permit Type
    # ------------------------------------------------------------------

    permit_type = models.ForeignKey(PermitType, on_delete=models.PROTECT, related_name="permits",)

    work_order = models.ForeignKey(WorkOrder, null=True, blank=True, on_delete=models.SET_NULL, related_name="permits",)

    location_tag = models.ForeignKey(LocationTag, null=True, blank=True, on_delete=models.PROTECT, related_name="permits",)

    # ------------------------------------------------------------------
    # Work Details
    # ------------------------------------------------------------------

    scope_of_work = models.TextField()

    duration_value = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Enter the number of units.")
    
    duration_unit = models.CharField(max_length=10, choices=DurationUnit.choices, default=DurationUnit.SHIFT, help_text="Select the duration unit.")

    estimated_personnel = models.PositiveSmallIntegerField(null=True,blank=True,)

    # ------------------------------------------------------------------
    # Equipment / Materials
    # ------------------------------------------------------------------

    electrical_tools = models.TextField(blank=True)

    mechanical_tools = models.TextField(blank=True)

    other_tools = models.TextField(blank=True)

    hazardous_materials = models.TextField(blank=True)

    non_explosion_proof_equipment = models.TextField(blank=True)

    vehicle_required = models.BooleanField(default=False)

    vehicle_description = models.CharField(max_length=150, blank=True,)

    # ------------------------------------------------------------------
    # Hazard Assessment
    # ------------------------------------------------------------------

    hazards = models.ManyToManyField(Hazard, through="PermitHazard", blank=True, related_name="permits",)

    previous_incidents = models.TextField(blank=True)

    precautions = models.ManyToManyField(Precaution, through="PermitPrecaution", blank=True, related_name="permits",)

    area_authority_comments = models.TextField(blank=True)

    additional_precautions = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Equipment Preparation
    # ------------------------------------------------------------------

    mechanical_isolation = models.CharField(
        max_length=10,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.REQUIRED,
    )

    equipment_depressurized = models.CharField(
        max_length=10,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.REQUIRED,
    )

    equipment_drained = models.CharField(
        max_length=10,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.REQUIRED,
    )

    equipment_purged = models.CharField(
        max_length=10,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.REQUIRED,
    )

    process_isolation = models.CharField(
        max_length=10,
        choices=EquipmentStatus.choices,
        default=EquipmentStatus.REQUIRED,
    )

    area_authority_present = models.BooleanField(default=False)

    fire_watch_required = models.BooleanField(default=False)

    fire_watch_present = models.BooleanField(default=False)

    equipment_preparation_notes = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Related Permits
    # ------------------------------------------------------------------

    related_permits = models.ManyToManyField(
        "self",
        symmetrical=False,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Personnel
    # ------------------------------------------------------------------

    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="requested_permits",
    )

    permit_holder = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="held_permits",
    )

    work_supervisor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="supervised_permits",
    )

    area_authority = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="area_authority_permits",
    )

    contractor_supervisor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="contractor_supervised_permits",
    )

    department = models.ForeignKey(
        Department,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="permits",
    )

    # ------------------------------------------------------------------
    # Validity
    # ------------------------------------------------------------------

    valid_from = models.DateTimeField()

    valid_to = models.DateTimeField()

    issued_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    activated_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    suspended_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    closed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    # ------------------------------------------------------------------
    # Remarks
    # ------------------------------------------------------------------

    remarks = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_permits",
    )

    modified_at = models.DateTimeField(
        auto_now=True,
    )

    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modified_permits",
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Permit to Work"
        verbose_name_plural = "Permits to Work"
        indexes = [
            models.Index(fields=["status", "valid_to"], name="permit_status_exp_idx"),
            models.Index(fields=["location_tag", "status"], name="permit_loc_status_idx"),
            models.Index(fields=["department", "status"], name="permit_dept_status_idx"),
            models.Index(fields=["work_order", "status"], name="permit_wo_status_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__gt=models.F("valid_from")),
                name="permit_valid_window_ck",
            ),

        ]

    def __str__(self):

        return self.permit_number

    def clean(self):
        super().clean()
        self.permit_number = (self.permit_number or "").strip().upper()

        if not self.permit_number:
            raise ValidationError({"permit_number": "Permit number is required."})

        if not self.location_tag and not self.work_order:
            raise ValidationError(
                "Either Work Order or Location Tag is required."
            )

        if (
            self.valid_from
            and self.valid_to
            and self.valid_to <= self.valid_from
        ):
            raise ValidationError(
                {
                    "valid_to":
                        "Valid To must be after Valid From."
                }
            )

        if self.continuation_of_id:
            if self.pk and self.continuation_of_id == self.pk:
                raise ValidationError(
                    {"continuation_of": "A permit cannot continue itself."}
                )
            if (
                self.continuation_of
                and self.continuation_of.permit_type_id != self.permit_type_id
            ):
                raise ValidationError(
                    {
                        "continuation_of":
                            "A continuation must use the same permit type."
                    }
                )

        if self.vehicle_required and not self.vehicle_description.strip():
            raise ValidationError(
                {
                    "vehicle_description":
                        "Describe the vehicle when a vehicle is required."
                }
            )

        if self.fire_watch_present and not self.fire_watch_required:
            raise ValidationError(
                {
                    "fire_watch_present":
                        "Fire watch cannot be present unless it is required."
                }
            )

        timestamp_rules = {
            "issued_at": {
                PermitStatus.ISSUED,
                PermitStatus.ACTIVE,
                PermitStatus.SUSPENDED,
                PermitStatus.EXTENDED,
                PermitStatus.COMPLETED,
                PermitStatus.CLOSED,
            },
            "activated_at": {
                PermitStatus.ACTIVE,
                PermitStatus.SUSPENDED,
                PermitStatus.EXTENDED,
                PermitStatus.COMPLETED,
                PermitStatus.CLOSED,
            },
            "completed_at": {PermitStatus.COMPLETED, PermitStatus.CLOSED},
            "closed_at": {PermitStatus.CLOSED},
        }
        errors = {}
        for field_name, statuses in timestamp_rules.items():
            if self.status in statuses and getattr(self, field_name) is None:
                errors[field_name] = (
                    f"{field_name.replace('_', ' ').title()} is required "
                    f"when status is {self.get_status_display()}."
                )
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):

        if self.work_order and not self.location_tag:
            self.location_tag = self.work_order.location_tag

        if not self.department and self.requested_by_id:
            self.department = self.requested_by.department

        now = timezone.now()
        timestamp_by_status = {
            PermitStatus.ISSUED: "issued_at",
            PermitStatus.ACTIVE: "activated_at",
            PermitStatus.SUSPENDED: "suspended_at",
            PermitStatus.COMPLETED: "completed_at",
            PermitStatus.CLOSED: "closed_at",
        }
        timestamp_field = timestamp_by_status.get(self.status)
        if timestamp_field and getattr(self, timestamp_field) is None:
            setattr(self, timestamp_field, now)

        self.full_clean()

        return super().save(*args, **kwargs)

    @property
    def is_active(self):

        now = timezone.now()

        return (
            self.status == PermitStatus.ACTIVE
            and self.valid_from <= now <= self.valid_to
        )

    @property
    def has_expired(self):

        return timezone.now() > self.valid_to

    @property
    def duration(self):

        if self.valid_from and self.valid_to:
            return self.valid_to - self.valid_from

        return None


# =============================================================================
# PermitHazard
# =============================================================================
class PermitHazard(models.Model):
    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="hazard_assessments",
    )
    hazard = models.ForeignKey(
        Hazard,
        on_delete=models.PROTECT,
        related_name="permit_assessments",
    )
    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_modified",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_removed",
    )

    class Meta:
        ordering = ["hazard__display_order", "hazard__code"]
        indexes = [
            models.Index(fields=["permit", "is_active"], name="permit_hazard_permit_active_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "hazard"],
                condition=Q(is_active=True),
                name="permit_hazard_unique_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, removed_by__isnull=True, removed_at__isnull=True)
                    | Q(
                        is_active=False,
                        removed_by__isnull=False,
                        removed_at__isnull=False,
                    )
                ),
                name="permit_hazard_removed_fields_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit_id}: {self.hazard}"

    def clean(self):
        super().clean()
        if self.is_active:
            if self.removed_by or self.removed_at:
                raise ValidationError(
                    {
                        "__all__": (
                            "Active hazard records cannot have removal metadata."
                        )
                    }
                )
        elif not self.removed_by or not self.removed_at:
            raise ValidationError(
                {
                    "__all__": (
                        "Inactive hazard records must include "
                        "removed_by and removed_at."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def deactivate(self, *, user):
        if not self.is_active:
            return

        self.is_active = False
        self.removed_by = user
        self.removed_at = timezone.now()

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )


    def reactivate(self, *, user):
        if self.is_active:
            return

        self.is_active = True
        self.removed_by = None
        self.removed_at = None
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )
# =============================================================================
# PermitPrecaution
# =============================================================================
class PermitPrecaution(models.Model):
    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="precaution_requirements",
    )
    precaution = models.ForeignKey(
        Precaution,
        on_delete=models.PROTECT,
        related_name="permit_requirements",
    )

    remarks = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_created",
    )
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="%(app_label)s_%(class)s_modified",
    )

    is_active = models.BooleanField(default=True, db_index=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_removed",
    )

    class Meta:
        ordering = ["precaution__display_order", "precaution__code"]
        indexes = [
            models.Index(
                fields=["permit", "is_active"],
                name="permit_precaution_permit_active_idx",
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["permit", "precaution"],
                condition=Q(is_active=True),
                name="permit_precaution_unique_active",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_active=True, removed_by__isnull=True, removed_at__isnull=True)
                    | Q(
                        is_active=False,
                        removed_by__isnull=False,
                        removed_at__isnull=False,
                    )
                ),
                name="permit_precaution_removed_fields_ck",
            ),
        ]

    def __str__(self):
        return f"{self.permit_id}: {self.precaution}"

    def clean(self):
        super().clean()
        if self.is_active:
            if self.removed_by is not None or self.removed_at is not None:
                raise ValidationError(
                    {
                        "__all__": (
                            "Active precaution records cannot have "
                            "removal metadata."
                        )
                    }
                )
        elif self.removed_by is None or self.removed_at is None:
            raise ValidationError(
                {
                    "__all__": (
                        "Inactive precaution records must include "
                        "removed_by and removed_at."
                    )
                }
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


    def deactivate(self, *, user):
        if not self.is_active:
            return

        self.is_active = False
        self.removed_by = user
        self.removed_at = timezone.now()
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )


    def reactivate(self, *, user):
        if self.is_active:
            return

        self.is_active = True
        self.removed_by = None
        self.removed_at = None
        self.modified_by = user

        self.save(
            update_fields=[
                "is_active",
                "removed_by",
                "removed_at",
                "modified_by",
                "modified_at",
            ]
        )