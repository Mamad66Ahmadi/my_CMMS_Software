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
    report_number = models.CharField(max_length=30, unique=True, db_index=True, blank=True)
    
    # Location/Equipment
    location_tag = models.ForeignKey(LocationTag, on_delete=models.PROTECT, related_name="fault_reports", null=True, blank=True)
    equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="fault_reports", null=True, blank=True)

    directive = models.CharField(max_length=255)
    fault_desc = models.TextField()

    priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports")
    symptom = models.ForeignKey(Symptom, on_delete=models.SET_NULL, null=True, blank=True, related_name="fault_reports")

    # Workflow Metadata
    reported_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="fault_reports_reported")
    reported_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="fault_reports_dep")
    reported_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, choices=FaultReportStatus.choices, default=FaultReportStatus.SUBMITTED, db_index=True)
    is_breakdown = models.BooleanField(default=False)

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

    def reject(self, user, comment: str = ""):
        """
        Handles context-aware rejection:
        1. If SUBMITTED: Supervisor rejects (fills reviewed_by/at)
        2. If APPROVED: Planner rejects (fills planner/at)
        """
        now = timezone.now()
        if self.status == FaultReportStatus.SUBMITTED:
            # Stage 1: Supervisor Rejection
            self.reviewed_by = user
            self.reviewed_at = now
            self.review_comment = f"Rejected by Supervisor: {comment}"
        
        elif self.status == FaultReportStatus.APPROVED:
            # Stage 2: Planner Rejection
            self.planner = user
            self.planner_reviewed_at = now
            # Append planner comment to existing supervisor comment
            planner_note = f"\n[Planner Rejection @ {now.strftime('%Y-%m-%d %H:%M')}]: {comment}"
            self.review_comment = (self.review_comment or "") + planner_note
        
        else:
            raise ValidationError(f"Cannot reject from status: {self.status}")

        self.status = FaultReportStatus.REJECTED
        self.save()

    class Meta:
        ordering = ["-reported_at"]
