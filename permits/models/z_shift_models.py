# # permits/models/shift_models.py

# """
# Shift handover and permit extension models.

# These models record the operational lifecycle of a Permit-To-Work
# during multi-shift operations.

# Author: Mohammad Ahmadi
# """

# from django.db import models
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ValidationError
# from django.utils import timezone

# from equipment.models.equipment_models import TimeStampedModel
# from permits.models.permit_models import Permit

# User = get_user_model()


# # ==========================================================
# # Shift Handover
# # ==========================================================

# class PermitShiftLog(TimeStampedModel):
#     """
#     Records each shift handover for a permit.

#     Example

#     Day Shift
#         ↓
#     Night Shift
#         ↓
#     Day Shift
#     """

#     class Shift(models.TextChoices):

#         DAY = "DAY", "Day Shift"

#         NIGHT = "NIGHT", "Night Shift"

#         MORNING = "MORNING", "Morning Shift"

#         EVENING = "EVENING", "Evening Shift"

#         OTHER = "OTHER", "Other"

#     permit = models.ForeignKey(
#         Permit,
#         on_delete=models.CASCADE,
#         related_name="shift_logs",
#     )

#     from_shift = models.CharField(
#         max_length=20,
#         choices=Shift.choices,
#     )

#     to_shift = models.CharField(
#         max_length=20,
#         choices=Shift.choices,
#     )

#     handed_over_by = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         related_name="permit_handovers_given",
#     )

#     received_by = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         related_name="permit_handovers_received",
#     )

#     handover_datetime = models.DateTimeField(
#         default=timezone.now,
#     )

#     work_status = models.CharField(
#         max_length=200,
#         blank=True,
#         help_text="Current progress of work.",
#     )

#     outstanding_work = models.TextField(
#         blank=True,
#     )

#     hazards_remaining = models.TextField(
#         blank=True,
#     )

#     equipment_status = models.TextField(
#         blank=True,
#     )

#     gas_test_required = models.BooleanField(
#         default=False,
#     )

#     gas_test_reference = models.ForeignKey(
#         "permits.PermitGasTest",
#         null=True,
#         blank=True,
#         on_delete=models.SET_NULL,
#         related_name="shift_handovers",
#     )

#     remarks = models.TextField(
#         blank=True,
#     )

#     class Meta:

#         ordering = [
#             "-handover_datetime",
#         ]

#         indexes = [

#             models.Index(
#                 fields=[
#                     "permit",
#                     "handover_datetime",
#                 ]
#             ),

#         ]

#     def __str__(self):

#         return (
#             f"{self.permit.permit_number}"
#             f" - "
#             f"{self.get_from_shift_display()}"
#             f" → "
#             f"{self.get_to_shift_display()}"
#         )

#     def clean(self):
#         super().clean()
#         if self.from_shift == self.to_shift:
#             raise ValidationError(
#                 {"to_shift": "Handover must be to a different shift."}
#             )
#         if self.handed_over_by_id == self.received_by_id:
#             raise ValidationError(
#                 {"received_by": "Handover must be received by another person."}
#             )
#         if self.gas_test_required and not self.gas_test_reference_id:
#             raise ValidationError(
#                 {"gas_test_reference": "A required gas test must be referenced."}
#             )
#         if (
#             self.gas_test_reference_id
#             and self.gas_test_reference.permit_id != self.permit_id
#         ):
#             raise ValidationError(
#                 {"gas_test_reference": "Gas test must belong to this permit."}
#             )

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)


# # ==========================================================
# # Permit Extension
# # ==========================================================

# class PermitExtension(TimeStampedModel):
#     """
#     Records every extension of a permit validity.

#     A permit may be extended multiple times.
#     """

#     class ExtensionStatus(models.TextChoices):

#         PENDING = "PENDING", "Pending"

#         APPROVED = "APPROVED", "Approved"

#         REJECTED = "REJECTED", "Rejected"

#         CANCELLED = "CANCELLED", "Cancelled"

#     permit = models.ForeignKey(
#         Permit,
#         on_delete=models.CASCADE,
#         related_name="extensions",
#     )

#     requested_by = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         related_name="requested_extensions",
#     )

#     approved_by = models.ForeignKey(
#         User,
#         null=True,
#         blank=True,
#         on_delete=models.PROTECT,
#         related_name="approved_extensions",
#     )

#     requested_at = models.DateTimeField(
#         default=timezone.now,
#     )

#     previous_valid_to = models.DateTimeField()

#     requested_valid_to = models.DateTimeField()

#     approved_valid_to = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     status = models.CharField(
#         max_length=20,
#         choices=ExtensionStatus.choices,
#         default=ExtensionStatus.PENDING,
#     )

#     reason = models.TextField()

#     approval_comments = models.TextField(
#         blank=True,
#     )

#     requires_new_gas_test = models.BooleanField(
#         default=False,
#     )

#     requires_new_approval = models.BooleanField(
#         default=False,
#     )

#     class Meta:

#         ordering = [
#             "-requested_at",
#         ]

#         indexes = [

#             models.Index(
#                 fields=[
#                     "permit",
#                     "status",
#                 ]
#             ),

#         ]

#     def __str__(self):

#         return (
#             f"{self.permit.permit_number}"
#             f" Extension"
#         )

#     def clean(self):
#         super().clean()
#         if self.requested_valid_to <= self.previous_valid_to:
#             raise ValidationError(
#                 {
#                     "requested_valid_to":
#                         "Requested validity must extend the current validity."
#                 }
#             )
#         if self.status == self.ExtensionStatus.APPROVED:
#             errors = {}
#             if not self.approved_by_id:
#                 errors["approved_by"] = "Approved extensions require an approver."
#             if not self.approved_valid_to:
#                 errors["approved_valid_to"] = (
#                     "Approved extensions require an approved validity."
#                 )
#             elif self.approved_valid_to <= self.previous_valid_to:
#                 errors["approved_valid_to"] = (
#                     "Approved validity must extend the previous validity."
#                 )
#             if errors:
#                 raise ValidationError(errors)
#         elif self.approved_by_id or self.approved_valid_to:
#             raise ValidationError(
#                 "Approval details are only valid for approved extensions."
#             )

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)

#     @property
#     def extension_hours(self):

#         if self.approved_valid_to:

#             delta = (
#                 self.approved_valid_to
#                 - self.previous_valid_to
#             )

#             return round(delta.total_seconds() / 3600, 2)

#         return None
