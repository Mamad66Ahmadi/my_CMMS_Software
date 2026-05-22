from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from equipment.models.equipment_models import LocationTag

User = get_user_model()


class DailyReportStatus(models.TextChoices):
    COMPLETED = "completed", "Completed"
    ONGOING = "ongoing", "Ongoing"
    WAITING = "waiting", "Waiting"


class DailyReport(models.Model):

    # ---- Date ----
    date = models.DateField(default=timezone.now, db_index=True)

    # ---- Location ----
    location_tag = models.ForeignKey(
        LocationTag,
        on_delete=models.PROTECT,
        related_name="daily_reports"
    )

    father_tag = models.ForeignKey(
        LocationTag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_reports"
    )

    # ---- Work Order ----
    wo_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="WO Number",
        db_index=True
    )

    # ---- Work Details ----
    actual_start = models.DateField(null=True, blank=True)

    description = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=DailyReportStatus.choices,
        default=DailyReportStatus.ONGOING,
        db_index=True
    )

    # ---- Workers (free text) ----
    employees = models.TextField(
        blank=True,
        help_text="Names of workers separated by comma."
    )

    # ---- Department (copied from user at creation) ----
    department = models.ForeignKey(
        "accounts.Department",
        on_delete=models.PROTECT,
        related_name="daily_reports"
    )

    # ---- Audit ----
    created_at = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_created"
    )

    modified_at = models.DateTimeField(null=True, blank=True)

    modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reports_modified"
    )

    # ---------------------- Save Logic ----------------------
    def save(self, *args, **kwargs):

        # Auto-set father tag from location
        if self.location_tag:
            self.father_tag = self.location_tag.parent

        if self.location_tag:
            self.father_tag = self.location_tag.parent

        # Only set default if it's absolutely blank
        if not self.department and self.created_by and hasattr(self.created_by, 'department'):
            self.department = self.created_by.department
            
        if not self.actual_start:
            self.actual_start = self.date
            
        if self.pk:  # means object already exists
            self.modified_at = timezone.localtime()

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.date} | {self.location_tag} | {self.created_by}"

    class Meta:
        ordering = ["-date"]
        verbose_name = "Daily Report"
        verbose_name_plural = "Daily Reports"
        indexes = [
            # 1. Critical for Running Counts (Year/Month)
            # This index covers both subquery requirements:
            # - location_tag + year + date
            # - location_tag + year + month + date
            models.Index(fields=["location_tag", "date"], name="idx_loc_date"),
            
            # 2. Helps performance on department filtering
            models.Index(fields=["department", "date"], name="idx_dept_date"),
        ]
