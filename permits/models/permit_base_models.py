# permits/models/permit_base_models.py


from django.db import models
from django.contrib.auth import get_user_model



from equipment.models.equipment_models import TimeStampedModel


User = get_user_model()


# ----------------------------------------------------------------------------
#   Lookup / master-data models
# ----------------------------------------------------------------------------

class HazardCode(TimeStampedModel):
    """Master list of hazard classifications a permit can be tagged with
    (e.g. Hot Work, Working at Height, Electrical Isolation)."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"



# ----------------------------------------------------------------------------
#   Status choices
# ----------------------------------------------------------------------------

class PermitStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING_DEPT_APPROVAL = "pending_dept_approval", "Dept. Approval"
    PENDING_SAFETY_REVIEW = "pending_safety_review", "Safety Review"
    PENDING_PERMIT_OFFICE = "pending_permit_office", "Permit Office Review"
    ISOLATION_REQUIRED = "isolation_required", "Isolation Planning"
    ISOLATIONS_IN_PROGRESS = "isolations_in_progress", "Isolations In Progress"
    READY_FOR_ISSUE = "ready_for_issue", "Ready For Issue"
    VALIDATED = "validated", "Validated"
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"
    EXPIRED = "expired", "Expired"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"



