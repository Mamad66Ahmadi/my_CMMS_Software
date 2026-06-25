import csv

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Count


from work_orders.models.wo_models import WorkOrder
from work_orders.models.wo_status_models import WorkOrderStatus
from work_orders.models import Priority, Symptom, ProjectCode, DetectionMethod, WorkType


# -------------------------------------------------------
# Filter helper
# -------------------------------------------------------
def get_filtered_work_orders(request):
    filters = {
        "wo_number": request.GET.get("wo_number", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "location_tag": request.GET.get("location_tag", "").strip(),
        "equipment": request.GET.get("equipment", "").strip(),
        "directive": request.GET.get("directive", "").strip(),
        "fault_desc": request.GET.get("fault_desc", "").strip(),
        "priority": request.GET.get("priority", "").strip(),
        "symptom": request.GET.get("symptom", "").strip(),
        "project_code": request.GET.get("project_code", "").strip(),
        "detection_method": request.GET.get("detection_method", "").strip(),
        "work_type": request.GET.get("work_type", "").strip(),
        "reported_by": request.GET.get("reported_by", "").strip(),
        "reported_department": request.GET.get("reported_department", "").strip(),
        "date_from": request.GET.get("date_from", "").strip(),
        "date_to": request.GET.get("date_to", "").strip(),
        "parent_tag": request.GET.get("parent_tag", "").strip(),
        "unit": request.GET.get("unit", "").strip(),
        "train": request.GET.get("train", "").strip(),
        "fault_report": request.GET.get("fault_report", "").strip(),
    }

    queryset = WorkOrder.objects.select_related(
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
    ).all()

    def apply_multi_value_filter(qs, filter_str, field_lookup):
        if not filter_str:
            return qs

        values = [x.strip() for x in filter_str.split(",") if x.strip()]
        if not values:
            return qs

        query = Q()
        for val in values:
            query |= Q(**{f"{field_lookup}__icontains": val})
        return qs.filter(query)

    # Text filters
    queryset = apply_multi_value_filter(queryset, filters["wo_number"], "wo_number")
    queryset = apply_multi_value_filter(queryset, filters["location_tag"], "location_tag__loc_tag")
    queryset = apply_multi_value_filter(queryset, filters["equipment"], "equipment__serial_number")
    queryset = apply_multi_value_filter(queryset, filters["reported_by"], "reported_by__username")
    queryset = apply_multi_value_filter(queryset, filters["reported_department"], "reported_department__name")
    queryset = apply_multi_value_filter(queryset, filters["fault_report"], "fault_report__report_number")

    # Directive / description search
    if filters["directive"] or filters["fault_desc"]:
        q = Q()
        if filters["directive"]:
            for val in [x.strip() for x in filters["directive"].split(",") if x.strip()]:
                q |= Q(directive__icontains=val)
        if filters["fault_desc"]:
            for val in [x.strip() for x in filters["fault_desc"].split(",") if x.strip()]:
                q |= Q(fault_desc__icontains=val)
        queryset = queryset.filter(q)

    # Parent tag / unit / train
    if filters["parent_tag"]:
        p_query = Q()
        for val in [x.strip() for x in filters["parent_tag"].split(",") if x.strip()]:
            p_query |= (
                Q(location_tag__loc_tag__icontains=val) |
                Q(location_tag__parent__loc_tag__icontains=val)
            )
        queryset = queryset.filter(p_query)

    queryset = apply_multi_value_filter(queryset, filters["unit"], "location_tag__unit__unit_code")
    queryset = apply_multi_value_filter(queryset, filters["train"], "location_tag__train")

    # Status
    if filters["status"] == "ALL":
        pass
    elif filters["status"]:
        queryset = queryset.filter(status=filters["status"])
    else:
        queryset = queryset.filter(
            status__in=[
                WorkOrderStatus.CREATED,
                WorkOrderStatus.PLANNED,
                WorkOrderStatus.IN_EXECUTION,
                WorkOrderStatus.WORK_DONE,
                WorkOrderStatus.CLOSED,
            ]
        )

    # FK filters
    if filters["priority"]:
        queryset = queryset.filter(priority_id=filters["priority"])

    if filters["symptom"]:
        queryset = queryset.filter(symptom_id=filters["symptom"])

    if filters["project_code"]:
        queryset = queryset.filter(project_code_id=filters["project_code"])

    if filters["detection_method"]:
        queryset = queryset.filter(detection_method_id=filters["detection_method"])

    if filters["work_type"]:
        queryset = queryset.filter(work_type_id=filters["work_type"])

    # Date filters
    if filters["date_from"]:
        queryset = queryset.filter(reported_at__date__gte=filters["date_from"])

    if filters["date_to"]:
        queryset = queryset.filter(reported_at__date__lte=filters["date_to"])

    return queryset, filters


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
            "wo_number": "wo_number",
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
            "priorities": Priority.objects.all().order_by("priority_level"),
            "symptoms": Symptom.objects.all().order_by("symptom_code"),
            "project_codes": ProjectCode.objects.all().order_by("project_code"),
            "detection_methods": DetectionMethod.objects.all().order_by("detection_code"),
            "work_types": WorkType.objects.all().order_by("work_type_code"),
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
class WorkOrderExportCSV(LoginRequiredMixin, View):
    def get(self, request):
        queryset, filters = get_filtered_work_orders(request)

        sort_by = request.GET.get("sort", "-reported_at")
        queryset = queryset.annotate(task_count=Count("tasks"))

        allowed_sort = {
            "wo_number": "wo_number",
            "task_count": "task_count",
            "status": "status",
            "parent_work_order": "parent_work_order__wo_number",
            "location_tag": "location_tag__loc_tag",
            "directive": "directive",
            "priority": "priority__priority_level",
            "fault_desc": "fault_desc",
            "work_type": "work_type__work_type_code",
            "symptom": "symptom__symptom_code",
            "cause": "cause",
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
