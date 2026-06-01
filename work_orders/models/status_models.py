# # # work_orders/models/status_models.py

# from django.db import models

# # ----------------------------------------- Status ----------------------------------------------------
# class WorkOrderStatus(models.TextChoices):

#     # Administrative Phase
#     REQUESTED = "REQUESTED", "Requested"           # User reported
#     SUPERVISOR_APPROVED = "SUPERVISOR_APPROVED", "Supervisor Approved"   # Supervisor approved
#     PLANNED = "PLANNED", "Planned"                 # Planner finished, 1st task created
    
#     # Execution Phase (Aggregate Statuses)
#     IN_EXECUTION = "IN_EXECUTION", "In Execution"   # At least one task started
#     WORK_DONE = "WORK_DONE", "Work Done"           # All tasks finished execution
    
#     # Closeout Phase
#     CLOSED = "CLOSED", "Closed"                    # Final administrative closure
#     CANCELLED = "CANCELLED", "Cancelled"           # Rejected by supervisor or planner

# class TaskStatus(models.TextChoices):
#     """Execution state of individual craft activities"""
#     REQUESTED = "REQUESTED", "Requested"
#     PLANNED = "PLANNED", "Planned"
#     RELEASED = "RELEASED", "Released"
    
#     IN_PROGRESS = "IN_PROGRESS", "In Progress"
#     WORK_DONE = "WORK_DONE", "Work Done"
#     REPORTED = "REPORTED", "Reported"
#     APPROVED = "APPROVED", "Approved"
#     CLOSED = "CLOSED", "Closed"
#     CANCELLED = "CANCELLED", "Cancelled"