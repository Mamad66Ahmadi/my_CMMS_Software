# # permits/models/fg_esd_models.py

# """
# Fire & Gas (F&G) / Emergency Shutdown (ESD) models.

# These models record every temporary inhibition,
# override, bypass and restoration of safety systems
# during a Permit-To-Work.

# Author: Mohammad Ahmadi
# """

# from django.db import models
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ValidationError
# from django.utils import timezone

# from equipment.models.equipment_models import (
#     TimeStampedModel,
#     LocationTag,
# )

# from permits.models.permit_models import Permit
# from permits.models.permit_base_models import FireGasSystem


# User = get_user_model()


# # ==========================================================
# # Permit Fire & Gas Record
# # ==========================================================

# class PermitFireGas(TimeStampedModel):
#     """
#     Represents one Fire & Gas system affected
#     during a permit.

#     Example

#         Fire Detector Loop A

#         Deluge Zone 3

#         Fire Alarm Zone 8

#         ESD Loop 2
#     """

#     class Status(models.TextChoices):

#         PLANNED = "PLANNED", "Planned"

#         INHIBITED = "INHIBITED", "Inhibited"

#         BYPASSED = "BYPASSED", "Bypassed"

#         ACTIVE = "ACTIVE", "Active"

#         RESTORED = "RESTORED", "Restored"

#     permit = models.ForeignKey(
#         Permit,
#         on_delete=models.CASCADE,
#         related_name="fire_gas_records",
#     )

#     system = models.ForeignKey(
#         FireGasSystem,
#         on_delete=models.PROTECT,
#         related_name="permit_records",
#     )

#     location_tag = models.ForeignKey(
#         LocationTag,
#         null=True,
#         blank=True,
#         on_delete=models.PROTECT,
#         related_name="fire_gas_records",
#     )

#     system_reference = models.CharField(
#         max_length=100,
#         blank=True,
#         help_text="Detector loop, ESD loop, alarm zone, etc.",
#     )

#     status = models.CharField(
#         max_length=20,
#         choices=Status.choices,
#         default=Status.PLANNED,
#         db_index=True,
#     )

#     reason = models.TextField(
#         blank=True,
#     )

#     approved_by = models.ForeignKey(
#         User,
#         null=True,
#         blank=True,
#         on_delete=models.PROTECT,
#         related_name="approved_fire_gas_records",
#     )

#     inhibited_by = models.ForeignKey(
#         User,
#         null=True,
#         blank=True,
#         on_delete=models.PROTECT,
#         related_name="inhibited_fire_gas_records",
#     )

#     restored_by = models.ForeignKey(
#         User,
#         null=True,
#         blank=True,
#         on_delete=models.PROTECT,
#         related_name="restored_fire_gas_records",
#     )

#     inhibited_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     restored_at = models.DateTimeField(
#         null=True,
#         blank=True,
#     )

#     remarks = models.TextField(
#         blank=True,
#     )

#     class Meta:

#         ordering = [
#             "permit",
#             "system",
#         ]

#         indexes = [

#             models.Index(
#                 fields=[
#                     "permit",
#                     "status",
#                 ]
#             ),

#             models.Index(
#                 fields=[
#                     "system",
#                 ]
#             ),

#         ]

#     def __str__(self):

#         return (
#             f"{self.permit.permit_number}"
#             f" - "
#             f"{self.system.name}"
#         )

#     def clean(self):
#         super().clean()
#         errors = {}
#         if self.status in {self.Status.INHIBITED, self.Status.BYPASSED}:
#             if not self.inhibited_by_id:
#                 errors["inhibited_by"] = "Operator is required for this status."
#             if not self.inhibited_at:
#                 errors["inhibited_at"] = "Action time is required for this status."
#             if not self.approved_by_id:
#                 errors["approved_by"] = "Approval is required for this status."
#         if self.status == self.Status.RESTORED:
#             if not self.restored_by_id:
#                 errors["restored_by"] = "Restored by is required."
#             if not self.restored_at:
#                 errors["restored_at"] = "Restored at is required."
#         if self.inhibited_at and self.restored_at:
#             if self.restored_at < self.inhibited_at:
#                 errors["restored_at"] = "Restoration cannot precede inhibition."
#         if errors:
#             raise ValidationError(errors)

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)

#     @property
#     def is_restored(self):

#         return self.status == self.Status.RESTORED


# # ==========================================================
# # Fire & Gas Action Log
# # ==========================================================

# class FireGasAction(TimeStampedModel):
#     """
#     Complete audit trail of actions performed
#     on one Fire & Gas record.

#     Example

#         Approved

#         Inhibited

#         Tested

#         Restored
#     """

#     class Action(models.TextChoices):

#         APPROVED = "APPROVED", "Approved"

#         INHIBITED = "INHIBITED", "Inhibited"

#         BYPASSED = "BYPASSED", "Bypassed"

#         TESTED = "TESTED", "Tested"

#         RESTORED = "RESTORED", "Restored"

#         CANCELLED = "CANCELLED", "Cancelled"

#     fire_gas = models.ForeignKey(
#         PermitFireGas,
#         on_delete=models.CASCADE,
#         related_name="actions",
#     )

#     action = models.CharField(
#         max_length=20,
#         choices=Action.choices,
#     )

#     performed_by = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         related_name="fire_gas_actions",
#     )

#     action_datetime = models.DateTimeField(
#         default=timezone.now,
#     )

#     comments = models.TextField(
#         blank=True,
#     )

#     class Meta:

#         ordering = [
#             "-action_datetime",
#         ]

#         indexes = [

#             models.Index(
#                 fields=[
#                     "fire_gas",
#                     "action_datetime",
#                 ]
#             )

#         ]

#     def __str__(self):

#         return (
#             f"{self.fire_gas} - "
#             f"{self.get_action_display()}"
#         )

#     def clean(self):
#         super().clean()
#         if self.action_datetime and self.action_datetime > timezone.now():
#             raise ValidationError(
#                 {"action_datetime": "Action time cannot be in the future."}
#             )

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)
