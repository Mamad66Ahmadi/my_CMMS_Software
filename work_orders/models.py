from django.db import models
from django.contrib.auth import get_user_model

from django.core.validators import MinValueValidator
from django.utils import timezone

from equipment.models.equipment_models import LocationTag, TimeStampedModel
# ----------------------    Getting user model object    ----------------------------------
User = get_user_model()

# ----------------------    Abstract Base Class    ----------------------------------
class WorkOrderStatus(models.TextChoices):
    FAULT_REPORTED = "FAULT_REPORTED", "Fault Reported"
    FAULT_APPROVED = "FAULT_APPROVED", "Fault Approved"
    PLANNED = "PLANNED", "Planned"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    WORK_DONE = "WORK_DONE", "Work Done"
    CLOSED = "CLOSED", "Closed"
    CANCELLED = "CANCELLED", "Cancelled"


# class WorkType(TimeStampedModel):
#     work_type_code = models.CharField(max_length=20, unique=True, verbose_name="Work Type Code")
#     work_type_desc = models.TextField(max_length=100, null=True, blank=True)
    
    
#     def __str__(self):
#         return self.work_type_code

#     class Meta:
#         verbose_name = "Work Type"
#         ordering = ['work_type_code']


# class Symptoms(TimeStampedModel):
#     symptom_code = models.CharField(max_length=20, unique=True)
#     symptom_desc = models.TextField(max_length=75, null=True, blank=True)
    
    
#     def __str__(self):
#         return self.symptom_code 

#     class Meta:
#         verbose_name = "Symptom"
#         ordering = ['symptom_code']


# class Cause(TimeStampedModel):
#     cause_code = models.CharField(max_length=20, unique=True)    
    
#     def __str__(self):
#         return self.cause_code 

#     class Meta:
#         verbose_name = "Cause"
#         ordering = ['cause_code']

class Priority(TimeStampedModel):
    priority_code = models.CharField(max_length=20, unique=True)
    priority_level = models.IntegerField(default=3, help_text="Numeric importance: 1 (High) to 5 (Low)")

    def __str__(self):
        return self.priority_code 

    class Meta:
        verbose_name = "Priority"
        verbose_name_plural = "Priorities"
        ordering = ['priority_level']

# ----------------------------------------- WORK ORDER -------------------------------------------------
class WorkOrder(models.Model):
    wo_number = models.CharField(max_length=50, unique=True, db_index=True)
    location_tag = models.ForeignKey(LocationTag, on_delete=models.PROTECT, related_name="work_orders")

    # Scoping
#    work_type = models.ForeignKey(WorkType, on_delete=models.PROTECT, related_name="work_orders")
    priority = models.ForeignKey(Priority, on_delete=models.PROTECT, related_name="work_orders")

    # Fault details
    fault_description = models.TextField()
#    symptoms = models.ForeignKey(Symptoms, on_delete=models.PROTECT, related_name="work_orders",)

#    cause = models.ForeignKey(Cause, on_delete=models.PROTECT, related_name="work_orders")
#    cause_description = models.TextField()

    # Workflow Status
    status = models.CharField(
        max_length=20, choices=WorkOrderStatus.choices, default=WorkOrderStatus.FAULT_REPORTED, db_index=True,)

    # Departments
    requester_department = models.ForeignKey(
        "accounts.Department", on_delete=models.PROTECT, related_name="requested_dep_work_orders")
    executing_department = models.ForeignKey(
        "accounts.Department", on_delete=models.PROTECT, related_name="executing_dep_work_orders")
    
    # Work Order audit
    fault_reported_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fault_reported_work_orders",)
    fault_reported_at = models.DateTimeField(auto_now_add=True)

    fault_approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="fault_approved_work_orders",)
    fault_approved_at = models.DateTimeField(null=True, blank=True)

    planner = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="planner_work_orders",)

    remarks = models.TextField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="updated_work_orders")


    class Meta:
        ordering = ["-wo_number"]
        indexes = [
            models.Index(fields=["wo_number", "status"]),
            models.Index(fields=["location_tag"]),
        ]

    def __str__(self):
        return self.wo_number
    

class WorkOrderHistory(models.Model):
    """
    Lightweight audit trail for tracking status transitions and ownership 
    changes without duplicating the entire WorkOrder data.
    """
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="history")
    
    old_status = models.CharField(max_length=20, choices=WorkOrderStatus.choices)
    new_status = models.CharField(max_length=20, choices=WorkOrderStatus.choices)
    
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    changed_at = models.DateTimeField(auto_now_add=True)
    
    transition_note = models.TextField(blank=True, help_text="Reason for status change or cancellation")

    class Meta:
        verbose_name = "Work Order History"
        verbose_name_plural = "Work Order Histories"
        ordering = ['-changed_at']