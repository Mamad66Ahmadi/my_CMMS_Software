
# # work_orders/models/work_order_models.py

# from django.db import models
# from django.contrib.auth import get_user_model
# from django.core.exceptions import ValidationError
# from django.db import transaction
# from django.utils import timezone

# from work_orders.models.base_models import *
# from work_orders.models.wo_status_models import *
# from equipment.models.equipment_models import LocationTag,Equipment
# from work_orders.models.sequences import DocumentSequence


# # ----------------------    Getting user model object    ----------------------------------
# User = get_user_model()


# # --- The Header: WorkOrder ---

# class WorkOrder(models.Model):
#     wo_number = models.CharField(max_length=50, unique=True, db_index=True)
#     fault_report = models.ForeignKey("FaultReport", on_delete=models.SET_NULL, null=True, blank=True, related_name="work_orders")

#     # Location/Equipment
#     location_tag = models.ForeignKey(LocationTag, on_delete=models.PROTECT, related_name="work_orders", null=True, blank=True)
#     equipment = models.ForeignKey(Equipment, on_delete=models.PROTECT, related_name="work_orders", null=True, blank=True)

#     directive = models.CharField(max_length=255)
#     fault_desc = models.TextField()

#     priority = models.ForeignKey(Priority, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_orders")
#     symptom = models.ForeignKey(Symptom, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_orders")
#     cause = models.ForeignKey(Cause, on_delete=models.PROTECT, null=True, blank=True, related_name="work_orders")
#     cause_description = models.TextField(null=True, blank=True)

#     project_code = models.ForeignKey(ProjectCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="work_orders")
#     parent_work_order = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="child_work_orders")
#     detection_method = models.ForeignKey(DetectionMethod, on_delete=models.SET_NULL, null=True,blank=True,related_name="work_orders",)
#     work_type = models.ForeignKey(WorkType, on_delete=models.SET_NULL, null=True,blank=True, related_name="work_orders",)

#     # Workflow Metadata
#     reported_by = models.ForeignKey(User, on_delete=models.SET_NULL, null = True, related_name="work_orders_reported")
#     reported_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="work_orders_rep_dep")
#     reported_at = models.DateTimeField(auto_now_add=True)

#     modified_by = models.ForeignKey(User,on_delete=models.SET_NULL, null=True, related_name="work_orders_modifier")
#     modified_at = models.DateTimeField(auto_now=True)


#     # Status & Workflow
#     status = models.CharField(max_length=20, choices=WorkOrderStatus.choices, default=WorkOrderStatus.CREATED, db_index=True)


#     @classmethod
#     def generate_wo_number(cls):
#         """Generate a WO number in the format WO-YY##### (example: WO-2600001)."""

#         year2 = timezone.now().strftime("%y")
#         year4 = timezone.now().year

#         with transaction.atomic():
#             sequence, _ = DocumentSequence.objects.select_for_update().get_or_create(
#                 code="WO",        
#                 year=year4,
#                 defaults={"last_number": 0},
#             )

#             sequence.last_number += 1
#             sequence.save(update_fields=["last_number"])

#             return f"WO-{year2}{sequence.last_number:05d}"

#     def save(self, *args, **kwargs):
#         if not self.wo_number:
#             self.wo_number = self.generate_wo_number()

#         # Auto derive location from equipment
#         if self.equipment and not self.location_tag:
#             self.location_tag = self.equipment.functional_location

#         super().save(*args, **kwargs)

#     class Meta:
#         ordering = ["-reported_at"]
#         indexes = [
#             models.Index(fields=["status"]),
#             models.Index(fields=["reported_at"]),
#         ]

#     def __str__(self):
#         return self.wo_number

#     def clean(self):

#         if not self.location_tag and not self.equipment:
#             raise ValidationError(
#                 "Either location_tag or equipment must be provided."
#             )


#     @property
#     def task_status_summary(self):

#         tasks = self.tasks.all()
#         total = tasks.count()

#         if total == 0:
#             return "No tasks created"

#         status_order = [
#             TaskStatus.CREATED,
#             TaskStatus.ESTIMATED,
#             TaskStatus.PLANNED,
#             TaskStatus.RELEASED,
#             TaskStatus.IN_PROGRESS,
#             TaskStatus.COMPLETED,
#             TaskStatus.APPROVED,
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
    
#     def update_status_from_tasks(self):

#         tasks = self.tasks.exclude(status=TaskStatus.CANCELLED)

#         if not tasks.exists():
#             self.status = WorkOrderStatus.CREATED
#             self.save(update_fields=["status"])
#             return

#         statuses = set(tasks.values_list("status", flat=True))

#         if all(s == TaskStatus.APPROVED for s in statuses):
#             self.status = WorkOrderStatus.CLOSED

#         elif all(s in [TaskStatus.COMPLETED, TaskStatus.APPROVED] for s in statuses):
#             self.status = WorkOrderStatus.WORK_DONE

#         elif TaskStatus.IN_PROGRESS in statuses:
#             self.status = WorkOrderStatus.IN_EXECUTION

#         elif TaskStatus.PLANNED in statuses or TaskStatus.RELEASED in statuses:
#             self.status = WorkOrderStatus.PLANNED

#         else:
#             self.status = WorkOrderStatus.CREATED

#         self.save(update_fields=["status"])

# # --- The Detail: WorkOrderTask ---

# class WorkOrderTask(models.Model):
#     work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="tasks")
#     task_number = models.PositiveIntegerField(blank=True)
    
#     # Task Scope
#     task_requester_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="requested_tasks")
#     task_executing_department = models.ForeignKey("accounts.Department", on_delete=models.PROTECT, related_name="executing_tasks")
#     directive = models.CharField(max_length=150,)
#     description = models.TextField(blank=True, null=True)

    
#     # Execution Status
#     status = models.CharField(max_length=30, choices=TaskStatus.choices, default=TaskStatus.CREATED, db_index=True)
    
#     # Execution Reporting (Moved here from Header)
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
            

#     def save(self, *args, **kwargs):

#         if not self.pk and not self.task_number:
#             last_task = (
#                 WorkOrderTask.objects
#                 .filter(work_order=self.work_order)
#                 .order_by("-task_number")
#                 .first()
#             )

#             self.task_number = 1 if not last_task else last_task.task_number + 1

#         super().save(*args, **kwargs)

#         # Update parent WO status
#         self.work_order.update_status_from_tasks()