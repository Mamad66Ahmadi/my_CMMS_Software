"""
Master / lookup models for the Permit To Work (PTW) system.

These tables contain relatively static data managed by HSE
administrators. Most of them are referenced by the transactional
Permit models.

Author: Mohammad Ahmadi
"""

# permits/models/permit_base_models.py

from django.core.exceptions import ValidationError
from django.db import models

from equipment.models.equipment_models import TimeStampedModel


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

    is_active = models.BooleanField(
        default=True,
        db_index=True,
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
    """
    Cold Work
    Hot Work
    Hot Work (Open Flame)

    Future:
        Confined Space
        Excavation
        Electrical
        Radiography
        Diving
    """

    requires_gas_test = models.BooleanField(default=False)

    requires_fire_watch = models.BooleanField(default=False)

    requires_isolation = models.BooleanField(default=False)

    requires_risk_assessment = models.BooleanField(default=True)

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


# Backward-compatible import used by the current permit admin and list views.
HazardCode = Hazard


# =============================================================================
# PPE
# =============================================================================

class PPE(BaseLookupModel):
    """
    Personal Protective Equipment
    """

    mandatory_by_default = models.BooleanField(
        default=False,
    )

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
# Approval Roles
# =============================================================================

class ApprovalRole(BaseLookupModel):
    """
    Roles participating in the PTW workflow.
    """

    class Meta(BaseLookupModel.Meta):
        verbose_name = "Approval Role"
        verbose_name_plural = "Approval Roles"


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


# =============================================================================
# Permit Status
# =============================================================================

class PermitStatus(models.TextChoices):

    DRAFT = "DRAFT", "Draft"

    SUBMITTED = "SUBMITTED", "Submitted"

    UNDER_REVIEW = "UNDER_REVIEW", "Under Review"

    APPROVED = "APPROVED", "Approved"

    READY_FOR_ISSUE = "READY", "Ready for Issue"

    ISSUED = "ISSUED", "Issued"

    ACTIVE = "ACTIVE", "Active"

    SUSPENDED = "SUSPENDED", "Suspended"

    EXTENDED = "EXTENDED", "Extended"

    COMPLETED = "COMPLETED", "Completed"

    CLOSED = "CLOSED", "Closed"

    CANCELLED = "CANCELLED", "Cancelled"

    EXPIRED = "EXPIRED", "Expired"


class DurationUnit(models.TextChoices):
    SHIFT = "SHIFT", "Shift(s)"
    DAY = "DAY", "Day(s)"