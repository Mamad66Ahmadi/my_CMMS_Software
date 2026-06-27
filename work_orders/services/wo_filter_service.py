# work_orders/services/wo_filter_service.py

from datetime import datetime, time
from django.utils.dateparse import parse_date
from django.db.models import Q

from work_orders.models.wo_models import WorkOrder
from work_orders.models.wo_status_models import WorkOrderStatus
from work_orders.models import Priority, Symptom, ProjectCode, DetectionMethod, WorkType, Cause

from .wo_filter_config import FIELD_CONFIGS, ACTIVE_FILTER_OPERATOR_LABELS

# Define field maps here to avoid repetition in get_filtered_work_orders
NUMERIC_FIELDS = {
    "wo_number": "wo_number_numeric",
    "train": "location_tag__train",
}

DATE_FIELDS = {
    "reported_at": "reported_at",
}

DROPDOWN_FIELDS = {
    "status": "status",
    "priority": "priority_id",
    "symptom": "symptom_id",
    "project_code": "project_code_id",
    "detection_method": "detection_method_id",
    "work_type": "work_type_id",
    "cause": "cause_id",
}

TEXT_FIELDS = {
    "fault_report": "fault_report__report_number",
    "location_tag": "location_tag__loc_tag",
    "equipment": "equipment__serial_number",
    "directive": "directive",
    "fault_desc": "fault_desc",
    "reported_by": "reported_by__username",
    "reported_department": "reported_department__name",
    "parent_tag": "location_tag__parent__loc_tag",
}

def get_object_label(model, pk):
    """Helper to get a human-readable label for a model instance given its PK."""
    if pk in (None, ""):
        return ""
    try:
        # Use get_object_or_404 pattern for clarity, though it might raise exception
        # A safer approach for view context would be a try-except block
        instance = model.objects.get(pk=pk)
        return str(instance)
    except (model.DoesNotExist, ValueError, TypeError):
        return str(pk) # Fallback to returning the raw PK if not found or invalid


def apply_text_condition(queryset, field_name, operator, value):
    """Applies text-based filtering conditions to a queryset."""
    if not operator or value is None:
        return queryset

    value = str(value).strip()
    if not value:
        return queryset

    # Using Q objects for complex lookups and to handle 'not' conditions cleanly
    q_object = Q()
    if operator == "eq":
        q_object = Q(**{field_name: value})
    elif operator == "neq":
        q_object = ~Q(**{field_name: value})
    elif operator == "contains":
        q_object = Q(**{f"{field_name}__icontains": value})
    elif operator == "ncontains":
        q_object = ~Q(**{f"{field_name}__icontains": value})
    elif operator == "startswith":
        q_object = Q(**{f"{field_name}__istartswith": value})
    elif operator == "endswith":
        q_object = Q(**{f"{field_name}__iendswith": value})

    if q_object:
        return queryset.filter(q_object)
    return queryset


def apply_numeric_condition(queryset, field_name, operator, value, strict=False):
    """Applies numeric filtering conditions to a queryset."""
    if not operator or value in (None, ""):
        return queryset

    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return queryset.none() if strict else queryset

    q_object = Q()
    if operator == "eq":
        q_object = Q(**{field_name: numeric_value})
    elif operator == "neq":
        q_object = ~Q(**{field_name: numeric_value})
    elif operator == "gt":
        q_object = Q(**{f"{field_name}__gt": numeric_value})
    elif operator == "gte":
        q_object = Q(**{f"{field_name}__gte": numeric_value})
    elif operator == "lt":
        q_object = Q(**{f"{field_name}__lt": numeric_value})
    elif operator == "lte":
        q_object = Q(**{f"{field_name}__lte": numeric_value})

    if q_object:
        return queryset.filter(q_object)
    return queryset


def apply_date_condition(queryset, field_name, operator, value):
    """Applies date filtering conditions to a queryset."""
    if not operator or not value:
        return queryset

    parsed = parse_date(value)
    if not parsed:
        return queryset # Invalid date format

    start_dt = datetime.combine(parsed, time.min)
    end_dt = datetime.combine(parsed, time.max)

    q_object = Q()
    if operator == "eq":
        q_object = Q(**{f"{field_name}__gte": start_dt, f"{field_name}__lte": end_dt})
    elif operator == "neq":
        q_object = ~Q(**{f"{field_name}__gte": start_dt, f"{field_name}__lte": end_dt})
    elif operator == "gt":
        q_object = Q(**{f"{field_name}__gt": end_dt})
    elif operator == "gte":
        q_object = Q(**{f"{field_name}__gte": start_dt})
    elif operator == "lt":
        q_object = Q(**{f"{field_name}__lt": start_dt})
    elif operator == "lte":
        q_object = Q(**{f"{field_name}__lte": end_dt})

    if q_object:
        return queryset.filter(q_object)
    return queryset


def parse_wo_number(value):
    """Parses a WO number string, removing 'WO-' prefix and converting to integer."""
    if value in (None, ""):
        return None
    value = str(value).strip().upper()
    if value.startswith("WO-"):
        value = value[3:]
    try:
        return int(value)
    except ValueError:
        return None # Not a valid integer after prefix removal


def apply_exact_condition(queryset, field_name, operator, value):
    """Applies exact match (dropdown) filtering conditions to a queryset."""
    if not operator or value in (None, ""):
        return queryset

    value = str(value).strip()
    if not value:
        return queryset

    q_object = Q()
    if operator == "eq":
        q_object = Q(**{field_name: value})
    elif operator == "neq":
        q_object = ~Q(**{field_name: value})

    if q_object:
        return queryset.filter(q_object)
    return queryset


def normalize_operator(op: str, value: str, default: str = "eq") -> str:
    """
    If a value exists but operator is empty, return default operator.
    Otherwise return operator as-is.
    """
    if value and not op:
        return default
    return op


def build_active_filters(filters):
    """
    Builds a list of dictionaries representing active filters for display.
    Each dictionary contains field label, operator label, and display value.
    """
    field_labels = {field["name"]: field["label"] for field in FIELD_CONFIGS}

    # Fields that use labels from the database (dropdowns)
    dropdown_fields = {
        "status", "priority", "symptom", "project_code", "detection_method",
        "work_type", "cause",
    }

    active_filters = []

    for field_name, field_label in field_labels.items():
        for idx in ("1", "2"): # Handle val1 and val2
            op_key = f"{field_name}_op{idx}"
            val_key = f"{field_name}_val{idx}"
            op = filters.get(op_key, "").strip()
            val = filters.get(val_key, "").strip()

            if not val: # Skip if no value is provided for this filter part
                continue

            display_value = val
            # If it's a dropdown field, try to get its human-readable label
            if field_name in dropdown_fields:
                # Use the _label suffix from the filters dict (which is populated in get_filtered_work_orders)
                label_key = f"{field_name}_val{idx}_label"
                display_value = filters.get(label_key, val) # Fallback to raw value if label not found

            active_filters.append({
                "field_name": field_name,
                "field_label": field_label,
                "operator": op,
                "operator_label": ACTIVE_FILTER_OPERATOR_LABELS.get(op, op), # Get readable operator text
                "value": val,
                "display_value": display_value,
            })

    return active_filters


def get_filtered_work_orders(request):
    """
    Retrieves and filters WorkOrders based on request parameters.
    Returns the filtered queryset and a dictionary of filters (including human-readable labels).
    """
    filters_data = request.GET.copy() # Use a different name to avoid shadowing

    queryset = WorkOrder.objects.select_related(
        "fault_report", "location_tag", "location_tag__parent", "location_tag__unit",
        "equipment", "priority", "symptom", "cause", "project_code",
        "detection_method", "work_type", "reported_by", "reported_department",
        "modified_by", "parent_work_order",
    ).all()

    # --- Default status behavior ---
    status_op1 = filters_data.get("status_op1", "").strip()
    status_val1 = filters_data.get("status_val1", "").strip()
    status_op2 = filters_data.get("status_op2", "").strip()
    status_val2 = filters_data.get("status_val2", "").strip()

    # If no status filters are explicitly provided, apply a default set of active statuses
    ACTIVE_STATUSES = [
        WorkOrderStatus.CREATED,
        WorkOrderStatus.PLANNED,
        WorkOrderStatus.IN_EXECUTION,
        WorkOrderStatus.WORK_DONE,
    ]

    status_val1 = filters_data.get("status_val1")
    status_val2 = filters_data.get("status_val2")

    # If user selected ALL → do not filter
    if status_val1 == "ALL" or status_val2 == "ALL":
        pass

    # If user selected specific statuses
    elif status_val1 or status_val2:
        if status_val1:
            queryset = queryset.filter(status=status_val1)
        if status_val2:
            queryset = queryset.filter(status=status_val2)

    # Default behaviour
    else:
        queryset = queryset.filter(status__in=ACTIVE_STATUSES)

    # --- Apply filters based on field types ---
    # Numeric fields
    for param_name, model_field in NUMERIC_FIELDS.items():
        op1 = filters_data.get(f"{param_name}_op1", "").strip()
        val1 = filters_data.get(f"{param_name}_val1", "").strip()
        op2 = filters_data.get(f"{param_name}_op2", "").strip()
        val2 = filters_data.get(f"{param_name}_val2", "").strip()

        op1 = normalize_operator(op1, val1)
        op2 = normalize_operator(op2, val2)

        if param_name == "wo_number":

            parsed_val1 = parse_wo_number(val1)
            parsed_val2 = parse_wo_number(val2)

            # 🚨 If user typed something but parsing failed → return no results
            if val1 and parsed_val1 is None:
                return WorkOrder.objects.none(), filters_data

            if val2 and parsed_val2 is None:
                return WorkOrder.objects.none(), filters_data

            queryset = apply_numeric_condition(
                queryset, model_field, op1, parsed_val1
            )
            queryset = apply_numeric_condition(
                queryset, model_field, op2, parsed_val2
            )
        else:
            queryset = apply_numeric_condition(queryset, model_field, op1, val1)
            queryset = apply_numeric_condition(queryset, model_field, op2, val2)


    # Date fields
    for param_name, model_field in DATE_FIELDS.items():
        op1 = filters_data.get(f"{param_name}_op1", "").strip()
        val1 = filters_data.get(f"{param_name}_val1", "").strip()
        op2 = filters_data.get(f"{param_name}_op2", "").strip()
        val2 = filters_data.get(f"{param_name}_val2", "").strip()

        op1 = normalize_operator(op1, val1)
        op2 = normalize_operator(op2, val2)

        queryset = apply_date_condition(queryset, model_field, op1, val1)
        queryset = apply_date_condition(queryset, model_field, op2, val2)

    # Dropdown / exact categorical fields
    for param_name, model_field in DROPDOWN_FIELDS.items():
        op1 = filters_data.get(f"{param_name}_op1", "").strip()
        val1 = filters_data.get(f"{param_name}_val1", "").strip()
        op2 = filters_data.get(f"{param_name}_op2", "").strip()
        val2 = filters_data.get(f"{param_name}_val2", "").strip()

        op1 = normalize_operator(op1, val1)
        op2 = normalize_operator(op2, val2)

        queryset = apply_exact_condition(queryset, model_field, op1, val1)
        queryset = apply_exact_condition(queryset, model_field, op2, val2)

    # Text fields
    for param_name, model_field in TEXT_FIELDS.items():
        op1 = filters_data.get(f"{param_name}_op1", "").strip()
        val1 = filters_data.get(f"{param_name}_val1", "").strip()
        op2 = filters_data.get(f"{param_name}_op2", "").strip()
        val2 = filters_data.get(f"{param_name}_val2", "").strip()

        op1 = normalize_operator(op1, val1)
        op2 = normalize_operator(op2, val2)

        queryset = apply_text_condition(queryset, model_field, op1, val1)
        queryset = apply_text_condition(queryset, model_field, op2, val2)

    # --- Human-readable labels for dropdown filters ---
    # These labels are needed for the active filters display
    filters_data["priority_val1_label"] = get_object_label(Priority, filters_data.get("priority_val1"))
    filters_data["priority_val2_label"] = get_object_label(Priority, filters_data.get("priority_val2"))

    filters_data["symptom_val1_label"] = get_object_label(Symptom, filters_data.get("symptom_val1"))
    filters_data["symptom_val2_label"] = get_object_label(Symptom, filters_data.get("symptom_val2"))

    filters_data["project_code_val1_label"] = get_object_label(ProjectCode, filters_data.get("project_code_val1"))
    filters_data["project_code_val2_label"] = get_object_label(ProjectCode, filters_data.get("project_code_val2"))

    filters_data["detection_method_val1_label"] = get_object_label(DetectionMethod, filters_data.get("detection_method_val1"))
    filters_data["detection_method_val2_label"] = get_object_label(DetectionMethod, filters_data.get("detection_method_val2"))

    filters_data["work_type_val1_label"] = get_object_label(WorkType, filters_data.get("work_type_val1"))
    filters_data["work_type_val2_label"] = get_object_label(WorkType, filters_data.get("work_type_val2"))

    filters_data["cause_val1_label"] = get_object_label(Cause, filters_data.get("cause_val1"))
    filters_data["cause_val2_label"] = get_object_label(Cause, filters_data.get("cause_val2"))

    # Human-readable status label
    status_choices = dict(WorkOrderStatus.choices)
    filters_data["status_val1_label"] = status_choices.get(filters_data.get("status_val1"), filters_data.get("status_val1", ""))
    filters_data["status_val2_label"] = status_choices.get(filters_data.get("status_val2"), filters_data.get("status_val2", ""))

    # --- Build active filters for display ---
    filters_data["active_filters"] = build_active_filters(filters_data)

    return queryset.distinct(), filters_data # Return distinct queryset and filters dict


def apply_fault_report_condition(queryset, field_name, operator, value):
    if not operator or value in (None, ""):
        return queryset

    value = str(value).strip().upper()
    if value.startswith("FR-"):
        value = value[3:]

    if not value.isdigit():
        return queryset.none()

    formatted_value = f"FR-{value}"

    if operator == "eq":
        return queryset.filter(**{field_name: formatted_value})
    elif operator == "neq":
        return queryset.exclude(**{field_name: formatted_value})
    elif operator == "startswith":
        return queryset.filter(**{f"{field_name}__istartswith": formatted_value})
    elif operator == "endswith":
        return queryset.filter(**{f"{field_name}__iendswith": formatted_value})
    elif operator == "contains":
        return queryset.filter(**{f"{field_name}__icontains": formatted_value})
    elif operator == "ncontains":
        return queryset.exclude(**{f"{field_name}__icontains": formatted_value})

    return queryset