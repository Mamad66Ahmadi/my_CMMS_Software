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
        if not self.location_tag and not self.equipment:
            raise ValidationError("Provide at least one of location_tag or equipment.")

        if self.equipment and self.location_tag:
            eq_loc = self.equipment.functional_location
            if eq_loc and eq_loc != self.location_tag:
                raise ValidationError({
                    "equipment": "Selected equipment does not belong to selected location tag."
                })

        # Approved / Rejected / Converted must have supervisor review
        if self.status in (FaultReportStatus.APPROVED, FaultReportStatus.REJECTED, FaultReportStatus.CONVERTED):
            if not self.reviewed_by or not self.reviewed_at:
                raise ValidationError("Approved/Rejected/Converted reports must have reviewed_by and reviewed_at.")

        # Converted must have planner action
        if self.status == FaultReportStatus.CONVERTED:
            if not self.planner:
                raise ValidationError("Converted reports must have a planner.")
            if not self.planner_reviewed_at:
                raise ValidationError("Converted reports must have planner_reviewed_at.")

    def save(self, *args, **kwargs):
        if self.equipment and not self.location_tag:
            self.location_tag = self.equipment.functional_location
        if not self.report_number:
            self.report_number = self.generate_report_number()
        super().save(*args, **kwargs)

    def approve(self, user, comment: str = ""):
        if self.status != FaultReportStatus.SUBMITTED:
            raise ValidationError("Only submitted fault reports can be approved.")
        self.status = FaultReportStatus.APPROVED
        self.reviewed_by = user
        self.reviewed_at = timezone.now()
        self.review_comment = comment
        self.full_clean()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])

    def reject(self, user, comment: str = ""):
        """
        Allows:
        - supervisor rejection from SUBMITTED
        - planner rejection from APPROVED
        """
        if self.status == FaultReportStatus.SUBMITTED:
            # supervisor rejection
            self.status = FaultReportStatus.REJECTED
            self.reviewed_by = user
            self.reviewed_at = timezone.now()
            self.review_comment = comment
            self.full_clean()
            self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_comment"])

        elif self.status == FaultReportStatus.APPROVED:
            # planner rejection
            self.status = FaultReportStatus.REJECTED
            self.planner = user
            self.planner_reviewed_at = timezone.now()
            # optional: append comment so both are preserved in one field
            if comment:
                if self.review_comment:
                    self.review_comment = f"{self.review_comment}\nPlanner rejection: {comment}"
                else:
                    self.review_comment = f"Planner rejection: {comment}"
            self.full_clean()
            self.save(update_fields=["status", "planner", "planner_reviewed_at", "review_comment"])

        else:
            raise ValidationError("This fault report cannot be rejected in its current status.")

    def mark_converted(self, user):
        if self.status != FaultReportStatus.APPROVED:
            raise ValidationError("Only approved fault reports can be converted.")
        self.status = FaultReportStatus.CONVERTED
        self.planner = user
        self.planner_reviewed_at = timezone.now()
        self.full_clean()
        self.save(update_fields=["status", "planner", "planner_reviewed_at"])

    class Meta:
        ordering = ["-reported_at"]