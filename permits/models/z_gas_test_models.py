# # permits/models/gas_test_models.py

# """
# Gas testing models for Permit To Work (PTW).

# One permit may contain multiple gas tests.
# Each gas test may contain multiple gas readings.

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
# # Gas Type (Master Data)
# # ==========================================================

# class GasType(TimeStampedModel):
#     """
#     Configurable gas types.

#     Examples
#     --------
#     O2
#     LEL
#     H2S
#     CO
#     NH3
#     VOC
#     """

#     code = models.CharField(
#         max_length=20,
#         unique=True,
#     )

#     name = models.CharField(
#         max_length=100,
#     )

#     unit = models.CharField(
#         max_length=20,
#     )

#     minimum_limit = models.DecimalField(
#         max_digits=8,
#         decimal_places=2,
#         null=True,
#         blank=True,
#     )

#     maximum_limit = models.DecimalField(
#         max_digits=8,
#         decimal_places=2,
#         null=True,
#         blank=True,
#     )

#     display_order = models.PositiveSmallIntegerField(
#         default=0,
#     )

#     is_active = models.BooleanField(
#         default=True,
#     )

#     class Meta:

#         ordering = [
#             "display_order",
#             "code",
#         ]

#     def __str__(self):

#         return self.code

#     def clean(self):
#         super().clean()
#         self.code = (self.code or "").strip().upper()
#         self.name = (self.name or "").strip()
#         self.unit = (self.unit or "").strip()

#         if (
#             self.minimum_limit is not None
#             and self.maximum_limit is not None
#             and self.maximum_limit <= self.minimum_limit
#         ):
#             raise ValidationError(
#                 {"maximum_limit": "Maximum limit must exceed minimum limit."}
#             )

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)


# # ==========================================================
# # Gas Test
# # ==========================================================

# class PermitGasTest(TimeStampedModel):
#     """
#     One gas test event.

#     One permit
#         ↓
#     Many gas tests
#     """

#     class TestType(models.TextChoices):

#         INITIAL = "INITIAL", "Initial"

#         PERIODIC = "PERIODIC", "Periodic"

#         CONTINUOUS = "CONTINUOUS", "Continuous"

#         RE_TEST = "RE_TEST", "Re-Test"

#         FINAL = "FINAL", "Final"

#     permit = models.ForeignKey(
#         Permit,
#         on_delete=models.CASCADE,
#         related_name="gas_tests",
#     )

#     test_type = models.CharField(
#         max_length=20,
#         choices=TestType.choices,
#         default=TestType.INITIAL,
#     )

#     test_datetime = models.DateTimeField()

#     gas_tester = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         related_name="performed_gas_tests",
#     )

#     gas_detector_serial = models.CharField(
#         max_length=50,
#         blank=True,
#     )

#     gas_detector_model = models.CharField(
#         max_length=100,
#         blank=True,
#     )

#     calibration_due_date = models.DateField(
#         null=True,
#         blank=True,
#     )

#     location_description = models.CharField(
#         max_length=200,
#         blank=True,
#     )

#     acceptable = models.BooleanField(
#         default=True,
#     )

#     remarks = models.TextField(
#         blank=True,
#     )

#     class Meta:

#         ordering = [
#             "-test_datetime",
#         ]

#         indexes = [

#             models.Index(
#                 fields=[
#                     "permit",
#                     "test_datetime",
#                 ]
#             )

#         ]

#     def __str__(self):

#         return (
#             f"{self.permit.permit_number}"
#             f" - "
#             f"{self.test_datetime}"
#         )

#     def clean(self):
#         super().clean()
#         if (
#             self.calibration_due_date
#             and self.test_datetime
#             and self.calibration_due_date < self.test_datetime.date()
#         ):
#             raise ValidationError(
#                 {
#                     "calibration_due_date":
#                         "The gas detector calibration was expired at test time."
#                 }
#             )
#         if self.test_datetime and self.test_datetime > timezone.now():
#             raise ValidationError(
#                 {"test_datetime": "Gas test time cannot be in the future."}
#             )

#     def save(self, *args, **kwargs):
#         self.full_clean()
#         return super().save(*args, **kwargs)

#     @property
#     def failed(self):

#         return not self.acceptable


# # ==========================================================
# # Gas Reading
# # ==========================================================

# class PermitGasReading(models.Model):
#     """
#     Individual gas reading.
#     """

#     gas_test = models.ForeignKey(
#         PermitGasTest,
#         on_delete=models.CASCADE,
#         related_name="readings",
#     )

#     gas_type = models.ForeignKey(
#         GasType,
#         on_delete=models.PROTECT,
#         related_name="readings",
#     )

#     measured_value = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#     )

#     is_safe = models.BooleanField(
#         default=True,
#     )

#     remarks = models.CharField(
#         max_length=200,
#         blank=True,
#     )

#     class Meta:

#         ordering = [
#             "gas_type__display_order",
#         ]

#         constraints = [

#             models.UniqueConstraint(
#                 fields=[
#                     "gas_test",
#                     "gas_type",
#                 ],
#                 name="uq_gastest_gastype",
#             )

#         ]

#     def clean(self):
#         super().clean()
#         if not self.gas_type_id or self.measured_value is None:
#             return
#         self.is_safe = True
#         if (
#             self.gas_type.minimum_limit is not None
#             and self.measured_value < self.gas_type.minimum_limit
#         ):
#             self.is_safe = False

#         if (
#             self.gas_type.maximum_limit is not None
#             and self.measured_value > self.gas_type.maximum_limit
#         ):
#             self.is_safe = False

#     def save(self, *args, **kwargs):

#         self.full_clean()

#         result = super().save(*args, **kwargs)
#         acceptable = not self.gas_test.readings.filter(is_safe=False).exists()
#         if self.gas_test.acceptable != acceptable:
#             type(self.gas_test).objects.filter(pk=self.gas_test_id).update(
#                 acceptable=acceptable
#             )
#             self.gas_test.acceptable = acceptable
#         return result

#     def __str__(self):

#         return (
#             f"{self.gas_type.code}"
#             f": "
#             f"{self.measured_value}"
#         )
