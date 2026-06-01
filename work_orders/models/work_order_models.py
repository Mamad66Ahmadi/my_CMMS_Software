
# # work_orders/models/work_order_models.py

# from django.db import models
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ValidationError

# from work_orders.models.base_models import *
# from work_orders.models.status_models import *
# from equipment.models.equipment_models import LocationTag

# # ----------------------    Getting user model object    ----------------------------------
# User = get_user_model()


# # --- The Header: WorkOrder ---

# class WorkOrder(models.Model):
#     wo_number = models.CharField(max_length=50, unique=True, db_index=True)
    
#     # Scope & Location (Static for all tasks)
#     location_tag = models.ForeignKey(LocationTag, on_delete=models.PROTECT, related_name="work_orders")
#     work_type = models.ForeignKey(WorkType, on_delete=models.PROTECT, related_name="work_orders")
#     priority = models.ForeignKey(Priority, on_delete=models.PROTECT, related_name="work_orders")
#     project_code = models.ForeignKey(ProjectCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_orders")
    
#     # Fault Details
#     initial_directive = models.CharField(max_length=150, null=True, blank=True)
#     fault_description = models.TextField(null=True, blank=True)
#     symptom = models.ForeignKey(Symptom, on_delete=models.PROTECT,null=True, blank=True, related_name="work_orders")

#     # Status & Workflow
#     status = models.CharField(
#         max_length=30, 
#         choices=WorkOrderStatus.choices, 
#         default=WorkOrderStatus.REQUESTED, 
#         db_index=True
#     )
    
#     # Ownership
#     fault_requester_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT,related_name="requested_dep_work_orders")
#     requester = models.ForeignKey(User, on_delete=models.PROTECT, related_name="requested_work_orders")
#     reg_date = models.DateTimeField(auto_now_add=True)
#     # to who
#     requested_executing_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="executing_dep_work_orders")
    
#     # Administrative Approval
#     fault_approved_by = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_work_orders")
#     fault_approved_at = models.DateTimeField(null=True, blank=True)
    
#     # Audit
#     modified_at = models.DateTimeField(auto_now=True)
#     modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modified_work_orders")

#     class Meta:
#         ordering = ["-wo_number"]

#     def __str__(self):
#         return self.wo_number

#     def clean(self):
#         if self.status == WorkOrderStatus.SUPERVISOR_APPROVED:
#             if not self.fault_approved_by:
#                 raise ValidationError({"fault_approved_by": "Supervisor approval user is required."})
#             if not self.fault_approved_at:
#                 raise ValidationError({"fault_approved_at": "Supervisor approval time is required."})

#     @property
#     def task_status_summary(self):
#         tasks = self.tasks.all()
#         total = tasks.count()

#         if total == 0:
#             return "No tasks created"

#         status_order = [
#             TaskStatus.REQUESTED,
#             TaskStatus.PLANNED,
#             TaskStatus.RELEASED,
#             TaskStatus.IN_PROGRESS,
#             TaskStatus.WORK_DONE,
#             TaskStatus.REPORTED,
#             TaskStatus.APPROVED,
#             TaskStatus.CLOSED,
#             TaskStatus.CANCELLED,
#         ]

#         counts = {
#             row["status"]: row["count"]
#             for row in tasks.values("status").annotate(count=models.Count("id"))
#         }

#         label_map = dict(TaskStatus.choices)
#         parts = []

#         for status in status_order:
#             count = counts.get(status, 0)
#             if count:
#                 parts.append(f"{count} {label_map[status].lower()}")

#         return f"From {total} tasks: " + ", ".join(parts)
# # --- The Detail: WorkOrderTask ---

# class WorkOrderTask(models.Model):
#     work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="tasks")
#     task_number = models.PositiveIntegerField(default=1)
    
#     # Task Scope
#     task_requester_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="requested_tasks")
#     task_executing_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="executing_tasks")
#     directive = models.CharField(max_length=150,)
#     description = models.TextField(blank=True, null=True)

    
#     # Execution Status
#     status = models.CharField(
#         max_length=30, 
#         choices=TaskStatus.choices, 
#         default=TaskStatus.REQUESTED, 
#         db_index=True
#     )
    
#     # Execution Reporting (Moved here from Header)
#     cause = models.ForeignKey(Cause, on_delete=models.PROTECT, null=True, blank=True, related_name="tasks")
#     cause_description = models.TextField(null=True, blank=True)
#     performed_action = models.ForeignKey(PerformedAction, on_delete=models.SET_NULL, null=True, blank=True, related_name="tasks")
#     work_done_description = models.TextField(null=True, blank=True)
#     permit = models.CharField(max_length=20, null=True, blank=True)

#     # Planning & Resource
#     planner = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="planned_tasks")
#     planned_start = models.DateField(null=True, blank=True)
#     planned_finish = models.DateField(null=True, blank=True)
    
#     # Delays
#     awaiting_reason = models.ForeignKey(AwaitingReason, on_delete=models.SET_NULL, null=True, blank=True)
#     waiting_history = models.TextField(null=True, blank=True) 
#     remarks = models.TextField(null=True, blank=True)

#     # Timestamps
#     actual_start = models.DateTimeField(null=True, blank=True)
#     actual_finish = models.DateTimeField(null=True, blank=True)

#     # Audit
#     work_master = models.ForeignKey(User, on_delete=models.PROTECT, related_name="mastered_tasks", null=True, blank=True)
#     work_leader = models.ForeignKey(User, on_delete=models.PROTECT, related_name="led_tasks", null=True, blank=True)

#     created_at = models.DateTimeField(auto_now_add=True)
#     created_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="created_tasks")

#     modified_at = models.DateTimeField(auto_now=True)
#     modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="modified_tasks")
#     modified_itam = models.TextField(null=True, blank=True)

#     class Meta:
#         ordering = ["work_order", "task_number"]
#         constraints = [
#             models.UniqueConstraint(fields=['work_order', 'task_number'], name='unique_task_per_wo')
#         ]

#     def __str__(self):
#         return f"{self.work_order.wo_number}-{self.task_number}"
    
#     def clean(self):
#         if self.planned_start and self.planned_finish:
#             if self.planned_finish < self.planned_start:
#                 raise ValidationError({
#                     "planned_finish": "Planned finish cannot be before planned start."
#                 })
#         if self.actual_start and self.actual_finish:
#             if self.actual_finish < self.actual_start:
#                 raise ValidationError({
#                     "actual_finish": "Actual finish cannot be before actual start."
#                 })
