# work_orders/services/wo_creation_service.py

from django.db import transaction
from django.utils import timezone

# Import models here directly if they are not causing circular imports
# If they do, keep the import inside the function as you did.
# Assuming these models are in work_orders.models.wo_models
from work_orders.models.wo_models import WorkOrder, WorkOrderTask # Example import

def convert_fault_report_to_work_order(fault_report):
    """
    Handles the atomic transition of a Fault Report to a Work Order.
    Creates a WorkOrder and its initial Task based on Fault Report data.
    """
    # Safety check: Don't create another WO if one already exists for this report
    # Using .first() is slightly more efficient than .exists() if you intend to get the object
    existing_work_order = WorkOrder.objects.filter(fault_report=fault_report).first()
    if existing_work_order:
        return existing_work_order

    # Import inside function if models are in the same app and circular imports are an issue
    # from work_orders.models.wo_models import WorkOrder, WorkOrderTask

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
            # Ensure other fields like status are set if they have defaults or require initial values
            # status = WorkOrderStatus.CREATED # or appropriate default
        )

        # 2. Create the first Task (Task #1)
        WorkOrderTask.objects.create(
            work_order=work_order,
            task_requester_department=fault_report.reported_department,
            task_executing_department=fault_report.executing_department,
            directive=fault_report.directive,
            description=fault_report.fault_desc,
            # Use fault_report metadata for the audit trail of the first task
            created_by=fault_report.reviewed_by or fault_report.reported_by,
            # Ensure other task fields have defaults if necessary
        )

        # Optional: Update fault report status if applicable
        # fault_report.status = 'converted_to_wo' # Example status
        # fault_report.save()

        return work_order
