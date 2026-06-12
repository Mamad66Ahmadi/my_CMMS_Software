# # work_orders/models/wo_status_models.py

from django.db import models

# ----------------------------------------- Status ----------------------------------------------------
class WorkOrderStatus(models.TextChoices):

    # Administrative Phase
    CREATED = "CREATED", "Created"                  # Created from fault report
    PLANNED = "PLANNED", "Planned"                  # at least one task is planned
    
    # Execution Phase (Aggregate Statuses)
    IN_EXECUTION = "IN_EXECUTION", "In Execution"   # At least one task started
    WORK_DONE = "WORK_DONE", "Work Done"            # all non-cancelled tasks are in {WORK_DONE, REPORTED, APPROVED}

    # Closeout Phase
    CLOSED = "CLOSED", "Closed"                    # all non-cancelled tasks are APPROVED
    CANCELLED = "CANCELLED", "Cancelled"           # cancelled by planner or staff

class TaskStatus(models.TextChoices):
    """Execution state of individual craft activities"""
    CREATED = "CREATED", "Created"              # task created, waiting for executing dept review/input
    ESTIMATED = "ESTIMATED", "Estimated"        # executing dept gave planning/resource suggestions
    PLANNED = "PLANNED", "Planned"              # planner finalized planning
    RELEASED = "RELEASED", "Released"           # authorized for execution
    
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"        # field execution finished & execution result formally reported
    APPROVED = "APPROVED", "Approved"           # report/closeout approved
    CANCELLED = "CANCELLED", "Cancelled"