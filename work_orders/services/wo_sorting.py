# work_orders/services/wo_sorting.py


WORK_ORDER_LIST_SORT_FIELDS = {
    "wo_number": "wo_number_numeric",
    "task_count": "task_count",
    "status": "status",
    "parent_work_order": "parent_work_order__wo_number_numeric",
    "location_tag": "location_tag__loc_tag",
    "equipment": "equipment__serial_number",
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
    "modified_by": "modified_by__username",
    "modified_at": "modified_at",
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


def get_sort_field(sort_param: str, allowed_sort_map: dict, default: str = "wo_number") -> str:
    """
    Determines the database sort field based on the request's sort parameter.
    Handles ascending/descending order.

    Example:
        sort=wo_number   -> wo_number_numeric
        sort=-wo_number  -> -wo_number_numeric
    """

    if not sort_param:
        sort_param = default

    is_desc = sort_param.startswith("-")
    clean_sort = sort_param.lstrip("-")

    sort_field = allowed_sort_map.get(
        clean_sort,
        allowed_sort_map[default],
    )

    if is_desc:
        return f"-{sort_field}"

    return sort_field
