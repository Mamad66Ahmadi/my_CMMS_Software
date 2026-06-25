
# # work_orders/models/wo_history_model.py

# from django.db import models

# from work_orders.models import WorkOrder, WorkOrderStatus, WorkOrderTask, TaskStatus
# from django.contrib.auth import get_user_model
# User = get_user_model()

# # -------------------------------------------- History ------------------------------------------------------

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
