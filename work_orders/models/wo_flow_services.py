# # work_orders/models/work_order_flow_services.py

# from django.db import transaction
# from django.core.exceptions import ValidationError

# from work_orders.models.status_models import WorkOrderStatus, TaskStatus
# from work_orders.models.work_order_history import WorkOrderHistory, WorkOrderTaskHistory


# ALLOWED_TASK_TRANSITIONS = {
#     TaskStatus.REQUESTED:   {TaskStatus.PLANNED, TaskStatus.CANCELLED},
#     TaskStatus.PLANNED:     {TaskStatus.RELEASED, TaskStatus.CANCELLED},
#     TaskStatus.RELEASED:    {TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED},
#     TaskStatus.IN_PROGRESS: {TaskStatus.WORK_DONE, TaskStatus.CANCELLED},
#     TaskStatus.WORK_DONE:   {TaskStatus.REPORTED, TaskStatus.CANCELLED},
#     TaskStatus.REPORTED:    {TaskStatus.APPROVED, TaskStatus.CANCELLED},
#     TaskStatus.APPROVED:    {TaskStatus.CLOSED, TaskStatus.CANCELLED},
#     TaskStatus.CLOSED:      set(),
#     TaskStatus.CANCELLED:   set(),
#     TaskStatus.CANCELLED: {TaskStatus.PLANNED}
# }


# def transition_task_status(task, new_status, user, note=""):
#     """
#     Handles task status change, validates workflow, logs history,
#     and updates the parent Work Order aggregate status.
#     """
#     old_status = task.status

#     if old_status == new_status:
#         return

#     allowed_next_statuses = ALLOWED_TASK_TRANSITIONS.get(old_status, set())
#     if new_status not in allowed_next_statuses:
#         raise ValidationError(
#             f"Invalid task transition: {old_status} -> {new_status}. "
#             f"Allowed next statuses are: {', '.join(allowed_next_statuses) or 'none'}."
#         )

#     with transaction.atomic():
#         task.status = new_status
#         task.modified_by = user
#         task.save(update_fields=["status", "modified_by", "modified_at"])

#         WorkOrderTaskHistory.objects.create(
#             task=task,
#             old_status=old_status,
#             new_status=new_status,
#             changed_by=user,
#             note=note
#         )

#         update_work_order_aggregate_status(task.work_order, user)


# def transition_work_order_status(work_order, new_status, user, note=""):
#     """
#     Handles Work Order status change (Manual/Administrative) AND logs the history.
#     """
#     if work_order.status == new_status:
#         return

#     with transaction.atomic():
#         old_status = work_order.status
#         work_order.status = new_status
#         work_order.modified_by = user
#         work_order.save()

#         # Log WO History
#         WorkOrderHistory.objects.create(
#             work_order=work_order,
#             old_status=old_status,
#             new_status=new_status,
#             changed_by=user,
#             transition_note=note
#         )

# def update_work_order_aggregate_status(work_order, user):
#     old_status = work_order.status

#     # Respect terminal states (optional but recommended)
#     if old_status in [WorkOrderStatus.CLOSED, WorkOrderStatus.CANCELLED]:
#         return

#     qs = work_order.tasks.all()
#     if not qs.exists():
#         return

#     statuses = list(qs.values_list("status", flat=True))

#     # Option: ignore cancelled tasks in rollup
#     active_statuses = [s for s in statuses if s != TaskStatus.CANCELLED]
#     if not active_statuses:
#         new_status = WorkOrderStatus.CANCELLED
#     else:
#         # Priority order (top-down)
#         if TaskStatus.IN_PROGRESS in active_statuses:
#             new_status = WorkOrderStatus.IN_EXECUTION
#         elif any(s in [TaskStatus.RELEASED] for s in active_statuses):
#             new_status = WorkOrderStatus.PLANNED  # or IN_EXECUTION/RELEASED if you add WO status
#         elif any(s in [TaskStatus.PLANNED] for s in active_statuses):
#             new_status = WorkOrderStatus.PLANNED
#         elif all(s in [TaskStatus.WORK_DONE, TaskStatus.REPORTED, TaskStatus.APPROVED, TaskStatus.CLOSED] for s in active_statuses):
#             new_status = WorkOrderStatus.WORK_DONE
#         else:
#             new_status = old_status

#     if new_status != old_status:
#         with transaction.atomic():
#             work_order.status = new_status
#             work_order.modified_by = user
#             work_order.save(update_fields=["status", "modified_by", "modified_at"])

#             WorkOrderHistory.objects.create(
#                 work_order=work_order,
#                 old_status=old_status,
#                 new_status=new_status,
#                 changed_by=user,
#                 transition_note="Automatic status update based on task progress.",
#             )
