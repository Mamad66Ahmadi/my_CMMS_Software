# permits/models/permit_base_models.py

from django.core.exceptions import ValidationError
from django.db import models

from equipment.models.equipment_models import TimeStampedModel
from permits.models.workflow_models import PermitWorkflow


# =============================================================================
# Base lookup model
# =============================================================================

class BaseLookupModel(TimeStampedModel):
    """
    Abstract base model for PTW master-data.
    """

    code = models.CharField(
        max_length=30,
        unique=True,
        db_index=True,
    )

    name = models.CharField(
        max_length=150,
    )

    description = models.TextField(
        blank=True,
    )


    display_order = models.PositiveSmallIntegerField(
        default=0,
    )

    class Meta:
        abstract = True
        ordering = ["display_order", "code"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def clean(self):
        super().clean()
        self.code = (self.code or "").strip().upper()
        self.name = (self.name or "").strip()

        if not self.code:
            raise ValidationError({"code": "Code is required."})
        if not self.name:
            raise ValidationError({"name": "Name is required."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)


# =============================================================================
# Permit Types
# =============================================================================

class PermitType(BaseLookupModel):

    active_workflow = models.ForeignKey(PermitWorkflow,null=True, blank=True, on_delete=models.PROTECT, related_name="permit_types",)

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Permit Type"
        verbose_name_plural = "Permit Types"

# =============================================================================
# Hazard
# =============================================================================

class Hazard(BaseLookupModel):
    """
    Hazard identification list.
    """

    class Category(models.TextChoices):
        PROCESS = "PROCESS", "Process"
        SAFETY = "SAFETY", "Safety"
        ENVIRONMENT = "ENV", "Environment"
        HEALTH = "HEALTH", "Occupational Health"
        ELECTRICAL = "ELEC", "Electrical"

    category = models.CharField(
        max_length=20,
        choices=Category.choices,
        default=Category.SAFETY,
    )

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Hazard"
        verbose_name_plural = "Hazards"


# =============================================================================
# Personal Protective Equipment
# =============================================================================

class PPE(BaseLookupModel):
    mandatory_by_default = models.BooleanField(default=False)

    class Meta(BaseLookupModel.Meta):
        verbose_name = "PPE"
        verbose_name_plural = "PPE"






# =============================================================================
# Precautions / Control Measures
# =============================================================================

class Precaution(BaseLookupModel):
    """
    Required control measures.
    """

    requires_verification = models.BooleanField(
        default=True,
    )
    

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Precaution"
        verbose_name_plural = "Precautions"


# =============================================================================
# Fire & Gas Systems
# =============================================================================

class FireGasSystem(BaseLookupModel):
    """
    Systems that may be inhibited or isolated.
    """

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Fire & Gas System"
        verbose_name_plural = "Fire & Gas Systems"


# =============================================================================
# Isolation Types
# =============================================================================

class IsolationType(BaseLookupModel):
    """
    Mechanical
    Process
    Electrical
    Instrument
    LOTO
    Blind
    """

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Isolation Type"
        verbose_name_plural = "Isolation Types"




# =============================================================================
# Shift Types
# =============================================================================

class ShiftType(BaseLookupModel):
    """
    Day
    Night
    """

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Shift"
        verbose_name_plural = "Shifts"


# =============================================================================
# Equipment Status
# =============================================================================

class EquipmentStatus(models.TextChoices):
    """
    Used by Page 2 of the permit.

    N/A
    Required
    Completed
    """

    NOT_APPLICABLE = "NA", "N/A"
    REQUIRED = "REQ", "Required"
    COMPLETED = "DONE", "Completed"




class DurationUnit(models.TextChoices):
    SHIFT = "SHIFT", "Shift(s)"
    DAY = "DAY", "Day(s)"
