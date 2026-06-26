import csv
from datetime import datetime, time

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import TemplateView

from work_orders.models.wo_models import WorkOrder
from work_orders.models.wo_status_models import WorkOrderStatus
from work_orders.models import Priority, Symptom, ProjectCode, DetectionMethod, WorkType, Cause



# -------------------------------------------------------
# Operator helpers
# -------------------------------------------------------
TEXT_OPERATORS = {
    "eq": "=",
    "neq": "<>",
    "contains": "contains",
    "ncontains": "not contains",
    "startswith": "starts with",
    "endswith": "ends with",
}

NUMERIC_OPERATORS = {
    "eq": "=",
    "neq": "<>",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}

DROPDOWN_OPERATORS = {
    "eq": "=",
    "neq": "<>",
}


def apply_text_condition(queryset, field_name, operator, value):
    if not operator or value is None:
        return queryset

    value = str(value).strip()
    if value == "":
        return queryset

    if operator == "eq":
        return queryset.filter(**{field_name: value})
    elif operator == "neq":
        return queryset.exclude(**{field_name: value})
    elif operator == "contains":
        return queryset.filter(**{f"{field_name}__icontains": value})
    elif operator == "ncontains":
        return queryset.exclude(**{f"{field_name}__icontains": value})
    elif operator == "startswith":
        return queryset.filter(**{f"{field_name}__istartswith": value})
    elif operator == "endswith":
        return queryset.filter(**{f"{field_name}__iendswith": value})

    return queryset


def apply_numeric_condition(queryset, field_name, operator, value):
    if not operator or value in (None, ""):
        return queryset

    try:
        numeric_value = int(value)
    except (TypeError, ValueError):
        return queryset

    if operator == "eq":
        return queryset.filter(**{field_name: numeric_value})
    elif operator == "neq":
        return queryset.exclude(**{field_name: numeric_value})
    elif operator == "gt":
        return queryset.filter(**{f"{field_name}__gt": numeric_value})
    elif operator == "gte":
        return queryset.filter(**{f"{field_name}__gte": numeric_value})
    elif operator == "lt":
        return queryset.filter(**{f"{field_name}__lt": numeric_value})
    elif operator == "lte":
        return queryset.filter(**{f"{field_name}__lte": numeric_value})

    return queryset


def apply_date_condition(queryset, field_name, operator, value):
    if not operator or not value:
        return queryset

    parsed = parse_date(value)
    if not parsed:
        return queryset

    start_dt = datetime.combine(parsed, time.min)
    end_dt = datetime.combine(parsed, time.max)

    if operator == "eq":
        return queryset.filter(**{
            f"{field_name}__gte": start_dt,
            f"{field_name}__lte": end_dt,
        })
    elif operator == "neq":
        return queryset.exclude(**{
            f"{field_name}__gte": start_dt,
            f"{field_name}__lte": end_dt,
        })
    elif operator == "gt":
        return queryset.filter(**{f"{field_name}__gt": end_dt})
    elif operator == "gte":
        return queryset.filter(**{f"{field_name}__gte": start_dt})
    elif operator == "lt":
        return queryset.filter(**{f"{field_name}__lt": start_dt})
    elif operator == "lte":
        return queryset.filter(**{f"{field_name}__lte": end_dt})

    return queryset


def parse_wo_number(value):
    if value in (None, ""):
        return None

    value = str(value).strip().upper()

    if value.startswith("WO-"):
        value = value[3:]

    try:
        return int(value)
    except ValueError:
        return None

def apply_exact_condition(queryset, field_name, operator, value):
    if not operator or value in (None, ""):
        return queryset

    value = str(value).strip()
    if value == "":
        return queryset

    if operator == "eq":
        return queryset.filter(**{field_name: value})
    elif operator == "neq":
        return queryset.exclude(**{field_name: value})

    return queryset


# -------------------------------------------------------
# Filter helper
# -------------------------------------------------------
def get_filtered_work_orders(request):
    filters = request.GET.copy()

    queryset = WorkOrder.objects.select_related(
        "fault_report",
        "location_tag",
        "location_tag__parent",
        "location_tag__unit",
        "equipment",
        "priority",
        "symptom",
        "cause",
        "project_code",
        "detection_method",
        "work_type",
        "reported_by",
        "reported_department",
        "modified_by",
        "parent_work_order",
    ).all()

    # ---------------------------------------------------
    # Default status behavior
    # If user does not explicitly search status, show active-like statuses
    # ---------------------------------------------------
    status_op1 = filters.get("status_op1", "").strip()
    status_val1 = filters.get("status_val1", "").strip()
    status_op2 = filters.get("status_op2", "").strip()
    status_val2 = filters.get("status_val2", "").strip()

    if not any([status_op1, status_val1, status_op2, status_val2]):
        queryset = queryset.filter(
            status__in=[
                WorkOrderStatus.CREATED,
                WorkOrderStatus.PLANNED,
                WorkOrderStatus.IN_EXECUTION,
                WorkOrderStatus.WORK_DONE,
                WorkOrderStatus.CLOSED,
            ]
        )

    # ---------------------------------------------------
    # Numeric fields
    # ---------------------------------------------------
    numeric_fields = {
        "wo_number": "wo_number_numeric",
        "train": "location_tag__train",
    }

    for param_name, model_field in numeric_fields.items():
        op1 = filters.get(f"{param_name}_op1", "").strip()
        val1 = filters.get(f"{param_name}_val1", "").strip()
        op2 = filters.get(f"{param_name}_op2", "").strip()
        val2 = filters.get(f"{param_name}_val2", "").strip()

        if param_name == "wo_number":
            val1 = parse_wo_number(val1) if val1 else None
            val2 = parse_wo_number(val2) if val2 else None

        queryset = apply_numeric_condition(queryset, model_field, op1, val1)
        queryset = apply_numeric_condition(queryset, model_field, op2, val2)

    # ---------------------------------------------------
    # Date fields
    # ---------------------------------------------------
    date_fields = {
        "reported_at": "reported_at",
    }

    for param_name, model_field in date_fields.items():
        op1 = filters.get(f"{param_name}_op1", "").strip()
        val1 = filters.get(f"{param_name}_val1", "").strip()
        op2 = filters.get(f"{param_name}_op2", "").strip()
        val2 = filters.get(f"{param_name}_val2", "").strip()

        queryset = apply_date_condition(queryset, model_field, op1, val1)
        queryset = apply_date_condition(queryset, model_field, op2, val2)

    # ---------------------------------------------------
    # Dropdown / exact categorical fields
    # Only eq / neq should be shown in UI
    # ---------------------------------------------------
    dropdown_fields = {
        "status": "status",
        "priority": "priority_id",
        "symptom": "symptom_id",
        "project_code": "project_code_id",
        "detection_method": "detection_method_id",
        "work_type": "work_type_id",
        "cause": "cause_id",
    }

    for param_name, model_field in dropdown_fields.items():
        op1 = filters.get(f"{param_name}_op1", "").strip()
        val1 = filters.get(f"{param_name}_val1", "").strip()
        op2 = filters.get(f"{param_name}_op2", "").strip()
        val2 = filters.get(f"{param_name}_val2", "").strip()

        queryset = apply_exact_condition(queryset, model_field, op1, val1)
        queryset = apply_exact_condition(queryset, model_field, op2, val2)

    # ---------------------------------------------------
    # Text fields
    # ---------------------------------------------------
    text_fields = {
        "fault_report": "fault_report__report_number",
        "location_tag": "location_tag__loc_tag",
        "equipment": "equipment__serial_number",
        "directive": "directive",
        "fault_desc": "fault_desc",
        "reported_by": "reported_by__username",
        "reported_department": "reported_department__name",
        "parent_tag": "location_tag__parent__loc_tag",
    }

    for param_name, model_field in text_fields.items():
        op1 = filters.get(f"{param_name}_op1", "").strip()
        val1 = filters.get(f"{param_name}_val1", "").strip()
        op2 = filters.get(f"{param_name}_op2", "").strip()
        val2 = filters.get(f"{param_name}_val2", "").strip()

        queryset = apply_text_condition(queryset, model_field, op1, val1)
        queryset = apply_text_condition(queryset, model_field, op2, val2)

    # ---------------------------------------------------
    # Human-readable labels for dropdown filters
    # ---------------------------------------------------
    filters["priority_val1_label"] = get_object_label(Priority, filters.get("priority_val1"))
    filters["priority_val2_label"] = get_object_label(Priority, filters.get("priority_val2"))

    filters["symptom_val1_label"] = get_object_label(Symptom, filters.get("symptom_val1"))
    filters["symptom_val2_label"] = get_object_label(Symptom, filters.get("symptom_val2"))

    filters["project_code_val1_label"] = get_object_label(ProjectCode, filters.get("project_code_val1"))
    filters["project_code_val2_label"] = get_object_label(ProjectCode, filters.get("project_code_val2"))

    filters["detection_method_val1_label"] = get_object_label(DetectionMethod, filters.get("detection_method_val1"))
    filters["detection_method_val2_label"] = get_object_label(DetectionMethod, filters.get("detection_method_val2"))

    filters["work_type_val1_label"] = get_object_label(WorkType, filters.get("work_type_val1"))
    filters["work_type_val2_label"] = get_object_label(WorkType, filters.get("work_type_val2"))

    filters["cause_val1_label"] = get_object_label(Cause, filters.get("cause_val1"))
    filters["cause_val2_label"] = get_object_label(Cause, filters.get("cause_val2"))

    # Optional: human-readable status label too
    status_choices = dict(WorkOrderStatus.choices)
    filters["status_val1_label"] = status_choices.get(filters.get("status_val1"), filters.get("status_val1", ""))
    filters["status_val2_label"] = status_choices.get(filters.get("status_val2"), filters.get("status_val2", ""))

    return queryset.distinct(), filters

# -------------------------------------------------------
# Search / Filter Page View
# -------------------------------------------------------

FIELD_CONFIGS = [
    {'name': 'wo_number',          'label': 'WO Number',        'icon': 'hash',                'input_type': 'text',   'placeholder': 'WO-2600010',    'operators': 'numeric'},
    {'name': 'reported_at',        'label': 'Reported At',      'icon': 'calendar',            'input_type': 'date',   'placeholder': '',              'operators': 'numeric'},
    {'name': 'status',             'label': 'Status',           'icon': 'circle-dot',          'input_type': 'select', 'placeholder': 'Default active', 'operators': 'dropdown'},
    {'name': 'priority',           'label': 'Priority',         'icon': 'flag',                'input_type': 'select', 'placeholder': 'All',           'operators': 'dropdown'},
    {'name': 'symptom',            'label': 'Symptom',          'icon': 'stethoscope',         'input_type': 'select', 'placeholder': 'All',           'operators': 'dropdown'},
    {'name': 'cause',              'label': 'Cause',            'icon': 'circle-x',            'input_type': 'select', 'placeholder': 'All',           'operators': 'dropdown'},
    {'name': 'project_code',       'label': 'Project Code',     'icon': 'folder-code',         'input_type': 'select', 'placeholder': 'All',           'operators': 'dropdown'},
    {'name': 'detection_method',   'label': 'Detection Method', 'icon': 'radar',               'input_type': 'select', 'placeholder': 'All',           'operators': 'dropdown'},
    {'name': 'work_type',          'label': 'Work Type',        'icon': 'tool',                'input_type': 'select', 'placeholder': 'All',           'operators': 'dropdown'},
    {'name': 'fault_report',       'label': 'Fault Report',     'icon': 'file-alert',          'input_type': 'text',   'placeholder': 'FR-26...',      'operators': 'text'},
    {'name': 'location_tag',       'label': 'Location Tag',     'icon': 'map-pin',             'input_type': 'text',   'placeholder': '103-KM-101...', 'operators': 'text'},
    {'name': 'parent_tag',         'label': 'Parent Tag',       'icon': 'sitemap',             'input_type': 'text',   'placeholder': '103-K-101...',  'operators': 'text'},
    {'name': 'equipment',          'label': 'Equipment Serial', 'icon': 'cpu',                 'input_type': 'text',   'placeholder': 'Serial...',     'operators': 'text'},
    {'name': 'reported_by',        'label': 'Reported By',      'icon': 'user',                'input_type': 'text',   'placeholder': 'Username',      'operators': 'text'},
    {'name': 'reported_department','label': 'Reporting Dept.',  'icon': 'building',            'input_type': 'text',   'placeholder': 'CBM, FIX...',   'operators': 'text'},
    {'name': 'directive',          'label': 'Directive',        'icon': 'bolt',                'input_type': 'text',   'placeholder': 'Leak, vibration...', 'operators': 'text'},
    {'name': 'fault_desc',         'label': 'Fault Description','icon': 'notes',               'input_type': 'text',   'placeholder': 'Description...','operators': 'text'},
    {'name': 'train',              'label': 'Train',            'icon': 'train',               'input_type': 'number', 'placeholder': '1',             'operators': 'numeric'},
]


class WorkOrderSearchView(LoginRequiredMixin, TemplateView):
    template_name = "work_orders/work_orders_head/wo_search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        # Build structured_filters for nested lookup in template tag
        structured_filters = {
            field['name']: {
                'op1':  request.GET.get(f"{field['name']}_op1",  ""),
                'val1': request.GET.get(f"{field['name']}_val1", ""),
                'op2':  request.GET.get(f"{field['name']}_op2",  ""),
                'val2': request.GET.get(f"{field['name']}_val2", ""),
            }
            for field in FIELD_CONFIGS
        }

        # Fetch querysets once
        priorities        = Priority.objects.all().order_by("priority_level")
        symptoms          = Symptom.objects.all().order_by("symptom_code")
        project_codes     = ProjectCode.objects.all().order_by("project_code")
        detection_methods = DetectionMethod.objects.all().order_by("detection_code")
        work_types        = WorkType.objects.all().order_by("work_type_code")
        causes            = Cause.objects.all().order_by("cause_code")

        choices_map = {
            'status':           list(WorkOrderStatus.choices),
            'priority':         [(str(p.pk), str(p)) for p in priorities],
            'symptom':          [(str(s.pk), str(s)) for s in symptoms],
            'cause':            [(str(c.pk), str(c)) for c in causes],
            'project_code':     [(str(pc.pk), str(pc)) for pc in project_codes],
            'detection_method': [(str(dm.pk), str(dm)) for dm in detection_methods],
            'work_type':        [(str(wt.pk), str(wt)) for wt in work_types],
        }

        operators_map = {
            'numeric':  NUMERIC_OPERATORS,
            'dropdown': DROPDOWN_OPERATORS,
            'text':     TEXT_OPERATORS,
        }

        context.update({
            'field_configs':      FIELD_CONFIGS,
            'structured_filters': structured_filters,
            'choices_map':        choices_map,
            'operators_map':      operators_map,
            'per_page':           request.GET.get('per_page', '25'),
        })
        return context


# -------------------------------------------------------
# List View
# -------------------------------------------------------
class WorkOrderList(LoginRequiredMixin, TemplateView):
    template_name = "work_orders/work_orders_head/wo_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset, filters = get_filtered_work_orders(self.request)

        sort_by = self.request.GET.get("sort", "-reported_at")

        allowed_sort = {
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

        sort_field = allowed_sort.get(sort_by.lstrip("-"), "reported_at")
        if sort_by.startswith("-"):
            sort_field = f"-{sort_field}"

        queryset = queryset.order_by(sort_field, "-id")

        try:
            per_page = int(self.request.GET.get("per_page", 25))
        except ValueError:
            per_page = 25

        if per_page not in [10, 25, 50, 100]:
            per_page = 25

        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        query_dict = self.request.GET.copy()
        query_dict.pop("sort", None)
        query_dict.pop("page", None)

        context.update({
            "work_orders": page_obj,
            "filters": filters,
            "sort_by": sort_by,
            "per_page": per_page,
            "query_params": query_dict.urlencode(),
        })

        return context

# -------------------------------------------------------
# Modal Detail View
# -------------------------------------------------------
@login_required
def work_order_detail_template(request, pk):
    wo = get_object_or_404(
        WorkOrder.objects.select_related(
            "fault_report",
            "location_tag",
            "location_tag__parent",
            "location_tag__unit",
            "equipment",
            "priority",
            "symptom",
            "project_code",
            "detection_method",
            "work_type",
            "reported_by",
            "reported_department",
            "modified_by",
            "parent_work_order",
        ).prefetch_related("tasks"),
        pk=pk,
    )

    return render(
        request,
        "work_orders/work_orders_head/_wo_detail_content.html",
        {
            "wo": wo,
        },
    )


# -------------------------------------------------------
# CSV Export
# -------------------------------------------------------
# -------------------------------------------------------
# CSV Export
# -------------------------------------------------------
class WorkOrderExportCSV(LoginRequiredMixin, View):
    def get(self, request):
        queryset, filters = get_filtered_work_orders(request)
        queryset = queryset.annotate(task_count=Count("tasks"))

        sort_by = request.GET.get("sort", "-reported_at")

        allowed_sort = {
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

        sort_field = allowed_sort.get(sort_by.lstrip("-"), "reported_at")
        if sort_by.startswith("-"):
            sort_field = f"-{sort_field}"

        queryset = queryset.order_by(sort_field, "-id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="work_orders.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)

        writer.writerow([
            "WO Number",
            "Tasks Count",
            "Status",
            "Fault Report",
            "Location Tag",
            "Parent Tag",
            "Unit",
            "Train",
            "Equipment Serial",
            "Priority",
            "Symptom",
            "Project Code",
            "Detection Method",
            "Work Type",
            "Reported By",
            "Reported Department",
            "Reported At",
            "Modified By",
            "Modified At",
            "Directive",
            "Fault Desc",
            "Task Summary",
        ])

        for wo in queryset:
            writer.writerow([
                wo.wo_number or "",
                wo.task_count or 0,
                wo.get_status_display() if wo.status else "",
                wo.fault_report.report_number if wo.fault_report else "",
                wo.location_tag.loc_tag if wo.location_tag else "",
                wo.location_tag.parent.loc_tag if wo.location_tag and wo.location_tag.parent else "",
                wo.location_tag.unit.unit_code if wo.location_tag and wo.location_tag.unit else "",
                wo.location_tag.train if wo.location_tag and wo.location_tag.train is not None else "",
                wo.equipment.serial_number if wo.equipment else "",
                wo.priority.priority_level if wo.priority else "",
                wo.symptom.symptom_code if wo.symptom else "",
                wo.project_code.project_code if wo.project_code else "",
                wo.detection_method.detection_code if wo.detection_method else "",
                wo.work_type.work_type_code if wo.work_type else "",
                wo.reported_by.username if wo.reported_by else "",
                wo.reported_department.name if wo.reported_department else "",
                wo.reported_at.strftime("%Y-%m-%d %H:%M") if wo.reported_at else "",
                wo.modified_by.username if wo.modified_by else "",
                wo.modified_at.strftime("%Y-%m-%d %H:%M") if wo.modified_at else "",
                wo.directive or "",
                wo.fault_desc or "",
                wo.task_status_summary or "",
            ])

        return response


def get_object_label(model, pk):
    if pk in (None, ""):
        return ""

    try:
        return str(model.objects.get(pk=pk))
    except (model.DoesNotExist, ValueError, TypeError):
        return str(pk)