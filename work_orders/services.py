# work_orders/services.py

from django.db import transaction
from django.utils import timezone

def convert_fault_report_to_work_order(fault_report):
    """
    Handles the atomic transition of a Fault Report to a Work Order.
    """
    # Import inside function to avoid circular imports
    from work_orders.models.wo_models import WorkOrder, WorkOrderTask

    # Safety check: Don't create another WO if one already exists for this report
    if WorkOrder.objects.filter(fault_report=fault_report).exists():
        return WorkOrder.objects.get(fault_report=fault_report)

    with transaction.atomic():
        # 1. Create the Work Order
        work_order = WorkOrder.objects.create(
            fault_report=fault_report,
            location_tag=fault_report.location_tag,
            equipment=fault_report.equipment,
            directive=fault_report.directive,
            fault_desc=fault_report.fault_desc,
            priority=fault_report.priority,
            symptom=fault_report.symptom,
            project_code=fault_report.project_code,
            detection_method=fault_report.detection_method,
            work_type=fault_report.work_type,
            reported_by=fault_report.reported_by,
            reported_department=fault_report.reported_department,
            reported_at=fault_report.reported_at,
        )

        # 2. Create the first Task (Task #1)
        WorkOrderTask.objects.create(
            work_order=work_order,
            task_requester_department=fault_report.reported_department,
            task_executing_department=fault_report.executing_department,
            directive=fault_report.directive,
            description=fault_report.fault_desc,
            # We use fault_report metadata for the audit trail of the first task
            created_by=fault_report.reviewed_by or fault_report.reported_by, 
        )

        return work_order
