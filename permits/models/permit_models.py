# permits/models/permit_models.py

from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.utils import timezone

from accounts.models import Department
from equipment.models.equipment_models import LocationTag
from work_orders.models.wo_models import WorkOrder

from permits.models.workflow_models import PermitWorkflow, PermitWorkflowStep
from permits.models import (
    PermitType,
    EquipmentStatus,
    DurationUnit,
)
from permits.models.permit_hazard_precaution_models import Hazard,Precaution

User = settings.AUTH_USER_MODEL

permit_identifier_validator = RegexValidator(
    regex=r"^[A-Z0-9][A-Z0-9._-]*$",
    message="Use uppercase letters, numbers, periods, underscores, or hyphens only.",
)


class Permit(models.Model):

    # ------------------------------------------------------------------
    # Identification & Workflow Configuration
    # ------------------------------------------------------------------
    permit_number = models.CharField(max_length=30, unique=True, db_index=True, validators=[permit_identifier_validator])
    
    continuation_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="continuations")

    permit_type = models.ForeignKey(PermitType, on_delete=models.PROTECT, related_name="permits")

    workflow = models.ForeignKey(
        PermitWorkflow,
        on_delete=models.PROTECT,
        related_name="permits",
        help_text="The workflow is obtained from permit_type.",
    )

    current_step = models.ForeignKey(PermitWorkflowStep, null=True, blank=True, on_delete=models.PROTECT, related_name="permits_at_step")

    # ------------------------------------------------------------------
    # Location & WorkOrder
    # ------------------------------------------------------------------
    
    work_order = models.ForeignKey(WorkOrder, null=True, blank=True, on_delete=models.SET_NULL, related_name="permits")
    
    location_tag = models.ForeignKey(LocationTag, null=True, blank=True, on_delete=models.PROTECT, related_name="permits")

    # ------------------------------------------------------------------
    # Work Details
    # ------------------------------------------------------------------
    scope_of_work = models.TextField()
    
    duration_value = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Enter the number of units.")
    
    duration_unit = models.CharField(max_length=10, choices=DurationUnit.choices, default=DurationUnit.SHIFT, help_text="Select the duration unit.")
    
    estimated_personnel = models.PositiveSmallIntegerField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Tools / Materials
    # ------------------------------------------------------------------
    electrical_tools = models.TextField(blank=True)
    mechanical_tools = models.TextField(blank=True)
    other_tools = models.TextField(blank=True)
    hazardous_materials = models.TextField(blank=True)
    non_explosion_proof_equipment = models.TextField(blank=True)
    vehicle_required = models.BooleanField(default=False)
    vehicle_description = models.CharField(max_length=150, blank=True)

    # ------------------------------------------------------------------
    # Hazard Assessment
    # ------------------------------------------------------------------
    hazards = models.ManyToManyField(Hazard, through="PermitHazard", blank=True, related_name="permits")
    
    previous_incidents = models.TextField(blank=True)
    
    precautions = models.ManyToManyField(Precaution, through="PermitPrecaution", blank=True, related_name="permits")
    
    area_authority_comments = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Equipment Preparation
    # ------------------------------------------------------------------
    mechanical_isolation = models.CharField(max_length=10, choices=EquipmentStatus.choices, default=EquipmentStatus.REQUIRED,)

    equipment_depressurized = models.CharField(max_length=10, choices=EquipmentStatus.choices, default=EquipmentStatus.REQUIRED,)

    equipment_drained = models.CharField(max_length=10, choices=EquipmentStatus.choices, default=EquipmentStatus.REQUIRED,)

    equipment_purged = models.CharField(max_length=10, choices=EquipmentStatus.choices, default=EquipmentStatus.REQUIRED,)

    process_isolation = models.CharField(max_length=10, choices=EquipmentStatus.choices, default=EquipmentStatus.REQUIRED,)

    area_authority_present_required = models.BooleanField(default=False)

    fire_watch_present_required = models.BooleanField(default=False)

    equipment_preparation_notes = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Fire, Gas & ESD Isolations
    # ------------------------------------------------------------------
    fire_gas_esd_items = models.ManyToManyField(
        "FireGasESD",
        through="PermitFireGasESD",
        blank=True,
        related_name="permits",
    )


    # ------------------------------------------------------------------
    # Related Permits
    # ------------------------------------------------------------------
    related_permits = models.ManyToManyField("self", symmetrical=True, blank=True,)

    required_safety_permits = models.ManyToManyField(
        "SafetyPermit",
        through="PermitSafetyRequirement",
        blank=True,
        related_name="required_by_permits",
    )

    # ------------------------------------------------------------------
    # Personnel (Operational Assignments)
    # ------------------------------------------------------------------
    work_supervisor = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="supervised_permits",)

    department = models.ForeignKey(Department, null=True, blank=True, on_delete=models.PROTECT, related_name="permits",)

    designated_area_authority = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="designated_area_authority_permits",)

    designated_area_supervisor = models.ForeignKey(User, null=True, blank=True, on_delete=models.PROTECT, related_name="contractor_supervised_permits",)


    # ------------------------------------------------------------------
    # Validity Timestamps
    # ------------------------------------------------------------------
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)

    # Step Audit Timestamps
    issued_by_supervisor_at = models.DateTimeField(null=True, blank=True)
    issued_by_area_authority_at = models.DateTimeField(null=True, blank=True)
    issued_by_area_supervisor_at = models.DateTimeField(null=True, blank=True)
    issued_by_permit_office_at = models.DateTimeField(null=True, blank=True)
    issued_by_check_point_at = models.DateTimeField(null=True, blank=True)
    issued_by_area_operator_at = models.DateTimeField(null=True, blank=True)
    
    activated_at = models.DateTimeField(null=True, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    # ------------------------------------------------------------------
    # Remarks
    # ------------------------------------------------------------------
    remarks = models.TextField(blank=True)

    # ------------------------------------------------------------------
    # Audit Metadata
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_permits",)
    modified_at = models.DateTimeField(auto_now=True)
    modified_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="modified_permits",)

    # ------------------------------------------------------------------
    # Permit Close-out (between job completion and closed)
    # ------------------------------------------------------------------
    closeout_items = models.ManyToManyField(
        "PermitCloseoutItem",
        through="PermitCloseoutSignoff",
        blank=True,
        related_name="permits",
    )



    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "Permit to Work"
        verbose_name_plural = "Permits to Work"
        indexes = [
            models.Index(fields=["current_step", "valid_to"], name="permit_step_exp_idx"),
            models.Index(fields=["location_tag", "current_step"], name="permit_loc_step_idx"),
            models.Index(fields=["department", "current_step"], name="permit_dept_step_idx"),
            models.Index(fields=["work_order", "current_step"], name="permit_wo_step_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_to__gt=models.F("valid_from")),
                name="permit_valid_window_ck",
            ),
            models.CheckConstraint(
                condition=Q(duration_value__isnull=True) | Q(duration_value__gt=0),
                name="permit_duration_value_positive_ck",
            ),
            models.CheckConstraint(
                condition=Q(estimated_personnel__isnull=True)
                | Q(estimated_personnel__gt=0),
                name="permit_estimated_personnel_positive_ck",
            ),
        ]

    def __str__(self):
        return self.permit_number

    def clean(self):
        super().clean()

        self.permit_number = (self.permit_number or "").strip().upper()

        if not self.permit_number:
            raise ValidationError(
                {
                    "permit_number": "Permit number is required."
                }
            )

        if self.permit_type_id and not self.workflow_id:
            self.workflow = self.permit_type.active_workflow

        if self.permit_type_id and not self.workflow_id:
            raise ValidationError(
                {
                    "permit_type": (
                        "Selected permit type does not have an active workflow "
                        "version."
                    )
                }
            )

        if (
            self.permit_type_id
            and self.workflow_id
            and self.permit_type.active_workflow_id != self.workflow_id
        ):
            raise ValidationError(
                {
                    "workflow": (
                        "Workflow must match the permit type's active workflow."
                    )
                }
            )

        if self.current_step_id:
            if self.current_step.workflow_id != self.workflow_id:
                raise ValidationError(
                    {
                        "current_step": (
                            "The step does not belong to the workflow assigned to this permit."
                        )
                    }
                )

        if not self.location_tag_id and not self.work_order_id:
            raise ValidationError(
                "Either Work Order or Location Tag is required."
            )

        if self.valid_from and self.valid_to and self.valid_to <= self.valid_from:
            raise ValidationError(
                {
                    "valid_to": "Valid To must be after Valid From."
                }
            )

        if self.continuation_of_id:
            if self.pk and self.continuation_of_id == self.pk:
                raise ValidationError(
                    {
                        "continuation_of": "A permit cannot continue itself."
                    }
                )

            continuation_number = (
                self.continuation_of.permit_number or ""
            ).strip().upper()

            if continuation_number == self.permit_number:
                raise ValidationError(
                    {
                        "continuation_of": (
                            "A permit cannot be a continuation of a permit with the same "
                            "permit number."
                        )
                    }
                )

            if self.continuation_of.permit_type_id != self.permit_type_id:
                raise ValidationError(
                    {
                        "continuation_of": "A continuation must use the same permit type."
                    }
                )

            previous_step = self.continuation_of.current_step
            eligible_states = {
                PermitWorkflowStep.State.ACTIVE,
                PermitWorkflowStep.State.CLOSED,
            }
            if (
                previous_step is None
                or previous_step.state not in eligible_states
            ):
                raise ValidationError(
                    {
                        "continuation_of": (
                            "Only a permit in Active or Closed status can be continued."
                        )
                    }
                )

        if self.vehicle_required and not self.vehicle_description.strip():
            raise ValidationError(
                {
                    "vehicle_description": (
                        "Describe the vehicle when a vehicle is required."
                    )
                }
            )

    def save(self, *args, **kwargs):
        if self.work_order_id and not self.location_tag_id:
            self.location_tag = self.work_order.location_tag

        if not self.current_step_id and self.permit_type_id:
            if not self.workflow_id:
                self.workflow = self.permit_type.active_workflow

            if self.workflow_id:
                start_step = self.workflow.steps.filter(is_start=True).first()
                if not start_step:
                    raise ValidationError(
                        {
                            "workflow": (
                                "The selected workflow does not have a start step."
                            )
                        }
                    )
                self.current_step = start_step

        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_active(self):
        """
        Calculates if the permit is live/active based on dates and terminal/start step contexts.
        (Adjust this criteria depending on whether you want an explicit step checked)
        """
        if self.valid_from is None or self.valid_to is None:
            return False

        now = timezone.now()
        is_in_date_range = self.valid_from <= now <= self.valid_to
        
        # Safe logical fallback check: Active only if it has started, has been activated, and is not terminal
        has_activated = self.activated_at is not None and self.closed_at is None
        is_step_not_terminal = (
            self.current_step_id is not None and not self.current_step.is_terminal
        )

        return is_in_date_range and has_activated and is_step_not_terminal

    @property
    def has_expired(self):
        return timezone.now() > self.valid_to

    @property
    def duration(self):
        if self.valid_from and self.valid_to:
            return self.valid_to - self.valid_from
        return None

