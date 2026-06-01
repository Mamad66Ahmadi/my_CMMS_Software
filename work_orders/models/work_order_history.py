
# # work_orders/models/work_order_history.py

# from django.db import models

# from work_orders.models import WorkOrder, WorkOrderStatus, WorkOrderTask, TaskStatus
# from django.contrib.auth import get_user_model
# User = get_user_model()

# # -------------------------------------------- History ------------------------------------------------------
# class WorkOrderHistory(models.Model):
#     """
#     Lightweight audit trail for tracking work order status transitions
#     without duplicating the entire WorkOrder row.
#     """
#     work_order = models.ForeignKey(
#         WorkOrder,
#         on_delete=models.CASCADE,
#         related_name="workorder_history"
#     )

#     old_status = models.CharField(
#         max_length=20,
#         choices=WorkOrderStatus.choices
#     )
#     new_status = models.CharField(
#         max_length=20,
#         choices=WorkOrderStatus.choices
#     )

#     changed_by = models.ForeignKey(
#         User,
#         on_delete=models.SET_NULL,
#         null=True,
#         blank=True,
#         related_name="work_order_history_entries"
#     )
#     changed_at = models.DateTimeField(auto_now_add=True)

#     transition_note = models.TextField(
#         blank=True,
#         help_text="Reason for status change, cancellation, approval, etc."
#     )

#     class Meta:
#         verbose_name = "Work Order History"
#         verbose_name_plural = "Work Order Histories"
#         ordering = ["-changed_at"]

#     def __str__(self):
#         return f"{self.work_order.wo_number}: {self.old_status} -> {self.new_status}"

# class WorkOrderTaskHistory(models.Model):

#     task = models.ForeignKey(WorkOrderTask, on_delete=models.CASCADE, related_name="task_history")


#     old_status = models.CharField(max_length=20, choices=TaskStatus.choices, null=True, blank=True)
#     new_status = models.CharField(max_length=20, choices=TaskStatus.choices, null=True, blank=True)

#     changed_by = models.ForeignKey(User,on_delete=models.SET_NULL,null=True, blank=True,related_name="work_order_task_history_entries")
#     changed_at = models.DateTimeField(auto_now_add=True)

#     note = models.TextField(blank=True)

#     class Meta:
#         ordering = ["-changed_at"]

#     def __str__(self):
#         return f"{self.task.work_order.wo_number}-{self.task.task_number}: {self.old_status} -> {self.new_status}"
