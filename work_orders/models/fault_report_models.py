# work_orders/models/fault_report_models.py
from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from equipment.models.equipment_models import LocationTag, Equipment
from work_orders.models.base_models import Priority, Symptom
from work_orders.models.sequences import DocumentSequence


User = get_user_model()



class FaultReportStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED  = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CONVERTED = "CONVERTED", "Converted to Work Order"



class FaultReport(models.Model):
    # Identity
    report_number = models.CharField(max_length=30, unique=True, db_index=True, blank=True)

    # Where / what
    location_tag = models.ForeignKey(
        LocationTag,on_delete=models.PROTECT,related_name="fault_reports",null=True, blank=True,)

    equipment = models.ForeignKey(
        Equipment,on_delete=models.PROTECT,related_name="fault_reports",null=True, blank=True,)

    # What happened
    directive = models.CharField(max_length=255)
    fault_desc = models.TextField()

    # Classification (optional but useful)
    priority = models.ForeignKey(
        Priority, on_delete=models.SET_NULL,null=True, blank=True, related_name="fault_reports")

    symptom = models.ForeignKey(
        Symptom, on_delete=models.SET_NULL,null=True, blank=True, related_name="fault_reports")


    # Reporter
    reported_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fault_reports_reported",)
    reported_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="fault_reports_dep")
    reported_at = models.DateTimeField(auto_now_add=True)

    # Flags (typical for refinery ops)
    is_breakdown = models.BooleanField(default=False)

    # Workflow
    status = models.CharField(
        max_length=20,choices=FaultReportStatus.choices,default=FaultReportStatus.SUBMITTED,db_index=True,)

    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports_reviewed"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Conversion fields
    planner = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="fault_reports_planner"
    )
    planner_reviewed_at = models.DateTimeField(null=True, blank=True)


    review_comment = models.TextField(blank=True, null=True)

    # Later when WorkOrder exists:
    # work_order = models.OneToOneField(
    #     "work_orders.WorkOrder",
    #     on_delete=models.SET_NULL,
    #     null=True, blank=True,
    #     related_name="source_fault_report",
    # )

    @classmethod
    def generate_report_number(cls):
        year2 = timezone.now().strftime("%y")
        with transaction.atomic():
            sequence, _ = DocumentSequence.objects.select_for_update().get_or_create(
                code="FR",
                year=timezone.now().year,
                defaults={"last_number": 0},
            )
            sequence.last_number += 1
            sequence.save(update_fields=["last_number"])
            return f"FR-{year2}{sequence.last_number:05d}"
        
    def clean(self):
        """Validation logic to ensure workflow integrity."""
        if not self.location_tag and not self.equipment:
            raise ValidationError("Provide at least one of location_tag or equipment.")

        if self.equipment and self.location_tag:
            eq_loc = self.equipment.functional_location
            if eq_loc and eq_loc != self.location_tag:
                raise ValidationError({
                    "equipment": "Selected equipment does not belong to selected location tag."
                })

        # APPROVED must have supervisor review info
        if self.status == FaultReportStatus.APPROVED:
            if not self.reviewed_by or not self.reviewed_at:
                raise ValidationError("Approved reports must have supervisor 'reviewed_by' and 'reviewed_at'.")

        # CONVERTED must have both supervisor and planner info
        if self.status == FaultReportStatus.CONVERTED:
            if not self.reviewed_by or not self.reviewed_at:
                raise ValidationError("Converted reports must have supervisor review data.")
            if not self.planner or not self.planner_reviewed_at:
                raise ValidationError("Converted reports must have planner review data.")

        # REJECTED must have at least one person responsible
        if self.status == FaultReportStatus.REJECTED:
            # If no planner info, supervisor info MUST exist
            if not self.planner_reviewed_at and not self.reviewed_at:
                 raise ValidationError("Rejected reports must have review data (Supervisor or Planner).")

    def save(self, *args, **kwargs):
        if self.equipment and not self.location_tag:
            self.location_tag = self.equipment.functional_location
        if not self.report_number:
            self.report_number = self.generate_report_number()
        super().save(*args, **kwargs)

    def approve(self, user, comment: str = ""):
        """Handled by Supervisor: SUBMITTED -> APPROVED"""
        if self.status != FaultReportStatus.SUBMITTED:
            raise ValidationError(f"Cannot approve from status: {self.status}")
        
        self.status = FaultReportStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        
        self.full_clean()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])

    def reject(self, user, comment: str = ""):
        """
        Handles dual-stage rejection:
        1. Supervisor rejects from SUBMITTED.
        2. Planner rejects from APPROVED.
        """
        if self.status == FaultReportStatus.SUBMITTED:
            # Supervisor rejection
            self.status = FaultReportStatus.REJECTED
            self.reviewed_by = user
            self.reviewed_at = timezone.now()
            self.review_comment = comment

        elif self.status == FaultReportStatus.APPROVED:
            # Planner rejection
            self.status = FaultReportStatus.REJECTED
            self.planner = user
            self.planner_reviewed_at = timezone.now()
            
            # Combine planner comment with existing supervisor comment
            if comment:
                header = f"--- Planner Rejection ({timezone.now().strftime('%Y-%m-%d %H:%M')}) ---"
                if self.review_comment:
                    self.review_comment = f"{self.review_comment}\n\n{header}\n{comment}"
                else:
                    self.review_comment = f"{header}\n{comment}"
        else:
            raise ValidationError(f"This report cannot be rejected from its current status ({self.status}).")

        self.full_clean()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "planner", "planner_reviewed_at", "review_comment"])

    def mark_converted(self, user):
        """Handled by Planner: APPROVED -> CONVERTED"""
        if self.status != FaultReportStatus.APPROVED:
            raise ValidationError("Only approved fault reports can be converted to Work Orders.")
            
        self.status = FaultReportStatus.CONVERTED
        self.planner = user
        self.planner_reviewed_at = timezone.now()
        
        self.full_clean()
        self.save(update_fields=["status", "planner", "planner_reviewed_at"])

    class Meta:
        ordering = ["-reported_at"]