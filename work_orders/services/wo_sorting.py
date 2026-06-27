# work_orders/services/wo_sorting.py

# Define allowed sort fields for WorkOrderList and WorkOrderExportCSV
# Maps user-facing sort parameters to model field lookups.
WORK_ORDER_LIST_SORT_FIELDS = {
    "wo_number": "wo_number_numeric",
    "status": "status",
    "location_tag": "location_tag__loc_tag",
    "equipment": "equipment__serial_number",
    "priority": "priority__priority_level",
    "symptom": "symptom__symptom_code",
    "project_code": "project_code__project_code",
    "detection_method": "detection_method__detection_code",
    "work_type": "work_type__work_type_code",
    "reported_by": "reported_by__username",
    "reported_department": "reported_department__name",
    "reported_at": "reported_at",
    "modified_by": "modified_by__username",
    "modified_at": "modified_at",
    "directive": "directive",
    "fault_report": "fault_report__report_number",
}

WORK_ORDER_EXPORT_SORT_FIELDS = {
    "wo_number": "wo_number_numeric",
    "task_count": "task_count",
    "status": "status",
    "parent_work_order": "parent_work_order__wo_number_numeric",
    "location_tag": "location_tag__loc_tag",
    "directive": "directive",
    "priority": "priority__priority_level",
    "fault_desc": "fault_desc",
    "work_type": "work_type__work_type_code",
    "symptom": "symptom__symptom_code",
    "cause": "cause__cause_code",
    "project_code": "project_code__project_code",
    "detection_method": "detection_method__detection_code",
    "reported_by": "reported_by__username",
    "reported_department": "reported_department__name",
    "reported_at": "reported_at",
}

def get_sort_field(sort_param: str, allowed_sort_map: dict) -> str:
    """
    Determines the database sort field based on the request's sort parameter.
    Handles ascending/descending order and falls back to a default.
    """
    sort_field = allowed_sort_map.get(sort_param.lstrip("-"), "reported_at") # Default to reported_at
    if sort_param.startswith("-"):
        return f"-{sort_field}"
    return sort_field
