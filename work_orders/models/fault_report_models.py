# work_orders/models/fault_report_models.py

from django.db import models, transaction
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

from equipment.models.equipment_models import LocationTag, Equipment
from work_orders.models.base_models import Priority, Symptom,ProjectCode,DetectionMethod,WorkType
from work_orders.models.sequences import DocumentSequence

User = get_user_model()

class FaultReportStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted"
    APPROVED  = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CONVERTED = "CONVERTED", "Converted to Work Order"

class FaultReport(models.Model):
    report_number = models.CharField(max_length=30, unique=True, db_index=True, blank=True)
    
    # Location/Equipment
    location_tag = models.ForeignKey(LocationTag, on_delete=models.PROTECT, related_name="fault_reports", null=True, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="fault_reports", null=True, blank=True)

    directive = models.CharField(max_length=255)
    fault_desc = models.TextField()

    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports")
    symptom = models.ForeignKey(Symptom, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports")
    project_code = models.ForeignKey(ProjectCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports")
    parent_work_order_number = models.CharField(max_length=30,null=True, blank=True, help_text="Optional parent work order reference number.",)
    detection_method = models.ForeignKey(DetectionMethod, on_delete=models.SET_NULL, null=True,blank=True,related_name="fault_reports",)
    work_type = models.ForeignKey(WorkType, on_delete=models.SET_NULL, null=True,blank=True, related_name="fault_reports",)

    executing_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="fault_executing_dep")
    # Workflow Metadata
    reported_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fault_reports_reported")
    reported_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="fault_reports_dep")
    reported_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=FaultReportStatus.choices, default=FaultReportStatus.SUBMITTED, db_index=True)

    # Supervisor Stage
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports_reviewed")
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Planner Stage
    planner = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="fault_reports_planner")
    planner_reviewed_at = models.DateTimeField(null=True, blank=True)

    review_comment = models.TextField(blank=True, null=True)

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
        if not self.location_tag and not self.equipment:
            raise ValidationError("Provide at least one of location_tag or equipment.")

        if self.equipment and self.location_tag:
            eq_loc = self.equipment.functional_location
            if eq_loc and eq_loc != self.location_tag:
                raise ValidationError({"equipment": "Selected equipment does not belong to selected location tag."})

    def save(self, *args, **kwargs):
        # Auto-fill location from equipment if missing
        if self.equipment and not self.location_tag:
            self.location_tag = self.equipment.functional_location
        
        # Generate sequence number for new reports
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
        if comment:
            self.review_comment = f"Supervisor: {comment}"
        
        self.save()

    def mark_converted(self, user):
        """Handled by Planner: APPROVED -> CONVERTED"""
        if self.status != FaultReportStatus.APPROVED:
            raise ValidationError("Only approved fault reports can be converted.")
            
        self.status = FaultReportStatus.CONVERTED
        self.planner = user
        self.planner_reviewed_at = timezone.now()
        
        self.save()

    def reject(self, user, comment=""):
        if self.status not in [FaultReportStatus.SUBMITTED, FaultReportStatus.APPROVED]:
            raise ValidationError(f"Cannot reject from status: {self.status}")

        now = timezone.now()

        self.status = FaultReportStatus.REJECTED
        self.reviewed_by = user
        self.reviewed_at = now

        if comment:
            self.review_comment = comment

        self.save()

    def resubmit(self, user):
        """Rejected -> Submitted"""
        if self.status != FaultReportStatus.REJECTED:
            raise ValidationError("Only rejected reports can be resubmitted.")

        self.status = FaultReportStatus.SUBMITTED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.save()

    class Meta:
        ordering = ["-reported_at"]
