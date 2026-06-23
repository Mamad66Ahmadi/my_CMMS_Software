# # work_orders/models/wo_costs_models.py

# from django.db import models

# from django.contrib.auth import get_user_model

# from work_orders.models.base_models import *
# from work_orders.models.wo_status_models import *
# from work_orders.models import *

# User = get_user_model()


# class TaskLabor(models.Model):

#     task = models.ForeignKey(
#         WorkOrderTask,
#         on_delete=models.CASCADE,
#         related_name="labor"
#     )

#     technician = models.ForeignKey(
#         User,
#         on_delete=models.PROTECT,
#         related_name="labor_bookings"
#     )

#     craft = models.ForeignKey(
#         "accounts.Department",
#         on_delete=models.PROTECT
#     )

#     estimated_hours = models.DecimalField(max_digits=5, decimal_places=2)
#     actual_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

#     started_at = models.DateTimeField(null=True, blank=True)
#     finished_at = models.DateTimeField(null=True, blank=True)

#     remarks = models.TextField(blank=True, null=True)

#     class Meta:
#         ordering = ["task"]


# class TaskSparePart(models.Model):

#     task = models.ForeignKey(
#         WorkOrderTask,
#         on_delete=models.CASCADE,
#         related_name="spare_parts"
#     )

#     spare_part = models.ForeignKey(
#         "inventory.SparePart",
#         on_delete=models.PROTECT
#     )

#     estimated_quantity = models.DecimalField(max_digits=10, decimal_places=2)

#     reserved_quantity = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         null=True,
#         blank=True
#     )

#     used_quantity = models.DecimalField(
#         max_digits=10,
#         decimal_places=2,
#         null=True,
#         blank=True
#     )

#     issued_from_store = models.ForeignKey(
#         "inventory.Store",
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True
#     )

#     remarks = models.TextField(null=True, blank=True)


# class TaskTool(models.Model):

#     task = models.ForeignKey(
#         WorkOrderTask,
#         on_delete=models.CASCADE,
#         related_name="tools"
#     )

#     tool = models.ForeignKey(
#         "tools.Tool",
#         on_delete=models.PROTECT
#     )

#     estimated_quantity = models.PositiveIntegerField(default=1)

#     reserved_quantity = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     used_quantity = models.PositiveIntegerField(
#         null=True,
#         blank=True
#     )

#     issued_at = models.DateTimeField(null=True, blank=True)
#     returned_at = models.DateTimeField(null=True, blank=True)

#     remarks = models.TextField(null=True, blank=True)
