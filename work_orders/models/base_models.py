# work_orders/models/base_models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator




from equipment.models.equipment_models import TimeStampedModel
# ----------------------    Getting user model object    ----------------------------------
User = get_user_model()

# ----------------------    Base Class    ----------------------------------
class WorkType(TimeStampedModel):
    work_type_code = models.CharField(max_length=15, unique=True, verbose_name="Work Type Code")
    work_type_desc = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.work_type_code
    
    class Meta:
        verbose_name = "Work Type"
        ordering = ['work_type_code']


class Symptom(TimeStampedModel):
    symptom_code = models.CharField(max_length=20, unique=True)
    symptom_desc = models.CharField(max_length=50, blank=True)
    
    def __str__(self):
        return self.symptom_code 
    
    class Meta:
        verbose_name = "Symptom"
        ordering = ['symptom_code']


class Cause(TimeStampedModel):
    cause_code = models.CharField(max_length=20, unique=True)    
    cause_info = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.cause_code 

    class Meta:
        verbose_name = "Cause"
        ordering = ['cause_code']


class Priority(TimeStampedModel):
    priority_code = models.CharField(max_length=20, unique=True)
    priority_level = models.PositiveSmallIntegerField(
        default=3,validators=[MinValueValidator(1), MaxValueValidator(5)],help_text="Numeric importance: 1 (High) to 5 (Low)")

    def __str__(self):
        return self.priority_code 

    class Meta:
        verbose_name = "Priority"
        verbose_name_plural = "Priorities"
        ordering = ['priority_level']


class AwaitingReason(TimeStampedModel):
    awaiting_code = models.CharField(max_length=20, unique=True)
    awaiting_desc = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return self.awaiting_code 

    class Meta:
        verbose_name = "Awaiting Reason"
        verbose_name_plural = "Awaiting Reasons"
        ordering = ['awaiting_code']


class ProjectCode(TimeStampedModel):
    project_code = models.CharField(max_length=20, unique=True)
    project_code_desc = models.CharField(max_length=100, blank=True)
    def __str__(self):
        return self.project_code 

    class Meta:
        verbose_name = "Project Code"
        verbose_name_plural = "Project Codes"
        ordering = ['project_code']


class PerformedAction(TimeStampedModel):
    action_code = models.CharField(max_length=25, unique=True)
    action_desc = models.CharField(max_length=75, blank=True)
    def __str__(self):
        return self.action_code
    class Meta:
        verbose_name = "Performed Action"
        verbose_name_plural = "Performed Actions"
        ordering = ["action_code"]

class DetectionMethod(TimeStampedModel):
    detection_code = models.CharField(max_length=25, unique=True)
    detection_desc = models.CharField(max_length=75, blank=True, null=True)
    def __str__(self):
        return self.detection_code
    class Meta:
        verbose_name = "Detection Method"
        verbose_name_plural = "Detection Methods"
        ordering = ["detection_code"]