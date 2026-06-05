import csv
from django.http import HttpResponse

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.views import View
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render


from work_orders.models.fault_report_models import FaultReport,FaultReportStatus


# ---------------------------------------------- Filter ------------------------------------------
def get_filtered_fault_reports(request):
    filters = {
        "report_number": request.GET.get("report_number", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "location_tag": request.GET.get("location_tag", "").strip(),
        "equipment": request.GET.get("equipment", "").strip(),
        "directive": request.GET.get("directive", "").strip(),
        "priority": request.GET.get("priority", "").strip(),
        "symptom": request.GET.get("symptom", "").strip(),
        "reported_by": request.GET.get("reported_by", "").strip(),
        "reported_department": request.GET.get("reported_department", "").strip(),
        "executing_department": request.GET.get("executing_department", "").strip(),
        "planner": request.GET.get("planner", "").strip(),
        "date_from": request.GET.get("date_from", "").strip(),
        "date_to": request.GET.get("date_to", "").strip(),
        "parent_tag": request.GET.get("parent_tag", "").strip(),
        "unit": request.GET.get("unit", "").strip(),
        "train": request.GET.get("train", "").strip(),
    }

    queryset = FaultReport.objects.select_related(
        "location_tag",
        "location_tag__parent",
        "location_tag__unit",
        "equipment",
        "priority",
        "symptom",
        "reported_by",
        "reported_department",
        "executing_department",
        "reviewed_by",
        "planner",
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

    # Standard filters
    queryset = apply_multi_value_filter(queryset, filters["report_number"], "report_number")
    queryset = apply_multi_value_filter(queryset, filters["location_tag"], "location_tag__loc_tag")
    queryset = apply_multi_value_filter(queryset, filters["equipment"], "equipment__serial_number")
    queryset = apply_multi_value_filter(queryset, filters["reported_by"], "reported_by__username")
    queryset = apply_multi_value_filter(queryset, filters["reported_department"], "reported_department__name")
    queryset = apply_multi_value_filter(queryset, filters["planner"], "planner__username")
    queryset = apply_multi_value_filter(queryset, filters["executing_department"], "executing_department__name")
    # Unit / Train
    queryset = apply_multi_value_filter(queryset, filters["unit"], "location_tag__unit__unit_code")
    queryset = apply_multi_value_filter(queryset, filters["train"], "location_tag__train")

    # Directive OR Fault Description search
    if filters["directive"]:
        values = [x.strip() for x in filters["directive"].split(",") if x.strip()]
        q = Q()
        for val in values:
            q |= Q(directive__icontains=val) | Q(fault_desc__icontains=val)
        queryset = queryset.filter(q)
        
    # Parent Tag logic similar to DailyReport
    if filters["parent_tag"]:
        p_values = [x.strip() for x in filters["parent_tag"].split(",") if x.strip()]
        p_query = Q()
        for val in p_values:
            p_query |= (
                Q(location_tag__loc_tag__icontains=val) |
                Q(location_tag__parent__loc_tag__icontains=val)
            )
        queryset = queryset.filter(p_query)

    # Status logic
    if filters["status"] == "ALL":
        pass
    elif filters["status"]:
        queryset = queryset.filter(status=filters["status"])
    else:
        queryset = queryset.filter(
            status__in=[
                FaultReportStatus.SUBMITTED,
                FaultReportStatus.APPROVED,
            ]
        )

    # FK filters
    if filters["priority"]:
        queryset = queryset.filter(priority_id=filters["priority"])

    if filters["symptom"]:
        queryset = queryset.filter(symptom_id=filters["symptom"])

    # Date filters
    if filters["date_from"]:
        queryset = queryset.filter(reported_at__date__gte=filters["date_from"])

    if filters["date_to"]:
        queryset = queryset.filter(reported_at__date__lte=filters["date_to"])

    return queryset, filters



# ---------------------------------------------------------- List View -----------------------------------------
class FaultReportList(LoginRequiredMixin, TemplateView):
    template_name = "work_orders/fault_reports/fault_report_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset, filters = get_filtered_fault_reports(self.request)

        sort_by = self.request.GET.get("sort", "-reported_at")

        allowed_sort = {
            "report_number": "report_number",
            "status": "status",
            "location_tag": "location_tag__loc_tag",
            "equipment": "equipment__serial_number",
            "priority": "priority__priority_level",
            "symptom": "symptom__symptom_code",
            "reported_by": "reported_by__username",
            "reported_department": "reported_department__name",
            "executing_department": "executing_department__name",
            "reported_at": "reported_at",
            "reviewed_by": "reviewed_by__username",
            "reviewed_at": "reviewed_at",
            "planner": "planner__username",
            "planner_reviewed_at": "planner_reviewed_at",
            "directive": "directive",
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
            "fault_reports": page_obj,
            "filters": filters,
            "sort_by": sort_by,
            "per_page": per_page,
            "query_params": query_dict.urlencode(),
        })

        return context

# ------------------------------- Modal Datail View ------------------------------------
@login_required
def fault_report_detail_template(request, pk):
    fr = get_object_or_404(
        FaultReport.objects.select_related(
            "location_tag",
            "equipment",
            "priority",
            "symptom",
            "reported_by",
            "reported_department",
            "executing_department",
            "reviewed_by",
            "planner",
        ),
        pk=pk,
    )

    return render(
        request,
        "work_orders/fault_reports/_fault_report_detail_content.html",
        {
            "fr": fr,
        },
    )

# -------------------------------------- Export CSV -------------------------------------------
class FaultReportExportCSV(LoginRequiredMixin, View):
    def get(self, request):
        queryset, filters = get_filtered_fault_reports(request)

        sort_by = request.GET.get("sort", "-reported_at")

        allowed_sort = {
            "report_number": "report_number",
            "status": "status",
            "location_tag": "location_tag__loc_tag",
            "equipment": "equipment__serial_number",
            "priority": "priority__priority_level",
            "symptom": "symptom__symptom_code",
            "reported_by": "reported_by__username",
            "reported_department": "reported_department__name",
            "executing_department": "executing_department__name",
            "reported_at": "reported_at",
            "reviewed_by": "reviewed_by__username",
            "reviewed_at": "reviewed_at",
            "planner": "planner__username",
            "planner_reviewed_at": "planner_reviewed_at",
            "directive": "directive",
        }

        sort_field = allowed_sort.get(sort_by.lstrip("-"), "reported_at")
        if sort_by.startswith("-"):
            sort_field = f"-{sort_field}"

        queryset = queryset.order_by(sort_field, "-id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="fault_reports.csv"'

        # Important for Excel UTF-8 / Persian / Arabic support
        response.write("\ufeff")

        writer = csv.writer(response)

        writer.writerow([
            "Report Number",
            "Status",
            "Location Tag",
            "Parent Tag",
            "Unit",
            "Train",
            "Equipment Serial",
            "Priority",
            "Symptom",
            "Reported By",
            "Reported Department",
            "Executing Department",
            "Reported At",
            "Reviewed By",
            "Reviewed At",
            "Planner",
            "Planner Reviewed At",
            "Directive",
            "Fault Desc"
            "Breakdown",
        ])

        for fr in queryset:
            writer.writerow([
                fr.report_number or "",
                fr.get_status_display() if fr.status else "",
                fr.location_tag.loc_tag if fr.location_tag else "",
                fr.location_tag.parent.loc_tag if fr.location_tag and fr.location_tag.parent else "",
                fr.location_tag.unit.unit_code if fr.location_tag and fr.location_tag.unit else "",
                fr.location_tag.train if fr.location_tag and fr.location_tag.train is not None else "",
                fr.equipment.serial_number if fr.equipment else "",
                fr.priority.priority_level if fr.priority else "",
                fr.symptom.symptom_code if fr.symptom else "",
                fr.reported_by.username if fr.reported_by else "",
                fr.reported_department.name if fr.reported_department else "",
                fr.executing_department.name if fr.executing_department else "",
                fr.reported_at.strftime("%Y-%m-%d %H:%M") if fr.reported_at else "",
                fr.reviewed_by.username if fr.reviewed_by else "",
                fr.reviewed_at.strftime("%Y-%m-%d %H:%M") if fr.reviewed_at else "",
                fr.planner.username if fr.planner else "",
                fr.planner_reviewed_at.strftime("%Y-%m-%d %H:%M") if fr.planner_reviewed_at else "",
                fr.directive or "",
                fr.fault_desc or "",
            ])

        return response



