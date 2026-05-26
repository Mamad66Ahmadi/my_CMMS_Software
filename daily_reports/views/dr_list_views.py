# daily_reports/views/dr_list_views.py

import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView
from datetime import timedelta
from django.utils import timezone
from django.shortcuts import render
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.db.models import Q


from daily_reports.services import annotate_running_counts
from daily_reports.models import DailyReport



def get_filtered_reports(request):
    filters = {
        "date_from": request.GET.get("date_from", "").strip(),
        "date_to": request.GET.get("date_to", "").strip(),
        "wo_number": request.GET.get("wo_number", "").strip(),
        "location_tag": request.GET.get("location_tag", "").strip(),
        "parent_tag": request.GET.get("parent_tag", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "department": request.GET.get("department", "").strip(),
        "unit": request.GET.get("unit", "").strip(),
        "train": request.GET.get("train", "").strip(),
        "description": request.GET.get("description", "").strip(),
    }

    queryset = DailyReport.objects.select_related(
        "location_tag",
        "location_tag__parent",
        "father_tag",
        "department",
        "created_by",
        "modified_by",
    ).all()

    # --- Date Filtering ---
    if not filters["date_from"] and not filters["date_to"]:
        today = timezone.now().date()
        fourteen_days_ago = today - timedelta(days=14)
        queryset = queryset.filter(date__gte=fourteen_days_ago)
    else:
        if filters["date_from"]:
            queryset = queryset.filter(date__gte=filters["date_from"])
        if filters["date_to"]:
            queryset = queryset.filter(date__lte=filters["date_to"])

    # --- Multi-Value Filtering (Comma Separated) Helper ---
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

    # Apply existing filters
    queryset = apply_multi_value_filter(queryset, filters["wo_number"], "wo_number")
    queryset = apply_multi_value_filter(queryset, filters["location_tag"], "location_tag__loc_tag")
    queryset = apply_multi_value_filter(queryset, filters["department"], "department__name")

    queryset = apply_multi_value_filter(queryset, filters["unit"], "location_tag__unit__unit_code")
    queryset = apply_multi_value_filter(queryset, filters["train"], "location_tag__train")
    queryset = apply_multi_value_filter(queryset, filters["description"], "description")
    
    # Parent Tag (Checking both father_tag and the direct parent loc_tag)
    if filters["parent_tag"]:
        p_values = [x.strip() for x in filters["parent_tag"].split(",") if x.strip()]
        p_query = Q()
        for val in p_values:
            p_query |= (
                Q(location_tag__loc_tag__icontains=val) |            # Exact/Matches current location
                Q(location_tag__parent__loc_tag__icontains=val) |     # Matches parent of current location
                Q(father_tag__loc_tag__icontains=val)                 # Matches report's father tag
            )
        queryset = queryset.filter(p_query)
    # --- Single Value Filtering ---
    if filters["status"]:
        queryset = queryset.filter(status=filters["status"])

    return queryset, filters


class DailyReportList(LoginRequiredMixin, TemplateView):
    template_name = "daily_reports/report_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset, filters = get_filtered_reports(self.request)
        queryset = annotate_running_counts(queryset)

        sort_by = self.request.GET.get("sort", "-date")

        allowed_sort = {
            "date": "date",
            "day": "date",
            "location_tag": "location_tag__loc_tag",
            "father_tag": "father_tag__loc_tag",
            "year_count": "year_count",
            "month_count": "month_count",
            "wo_number": "wo_number",
            "status": "status",
            "description": "description",
            "employees": "employees",
            "department": "department__name",
            "actual_start": "actual_start",
            "created_by": "created_by__username",
            "created_at": "created_at",
            "modified_by": "modified_by__username",
            "modified_at": "modified_at",
            "parent_month_count": "parent_month_count",

        }

        sort_field = allowed_sort.get(sort_by.lstrip("-"), "date")
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
            "reports": page_obj,
            "filters": filters,
            "sort_by": sort_by,
            "per_page": per_page,
            "query_params": query_dict.urlencode(),
        })
        return context


class DailyReportExportCSV(LoginRequiredMixin, View):
    def get(self, request):
        queryset, filters = get_filtered_reports(request)
        queryset = annotate_running_counts(queryset).order_by("-date", "-id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="daily_reports.csv"'

        # ✅ important for Excel Persian support
        response.write("\ufeff")

        writer = csv.writer(response)

        writer.writerow([
            "Date",
            "Day",
            "Location Tag",
            "Month Count",
            "Year Count",
            "Status",
            "WO Number",
            "Description",
            "Actual Start",
            "Department",
            "Parent Tag",
            "Parent 30d Count",
            "Employees",
            "Created By",
            "Created At",
            "Modified By",
            "Modified At",
        ])

        for r in queryset:
            writer.writerow([
                r.date.strftime("%Y-%m-%d") if r.date else "",
                r.date.strftime("%a") if r.date else "",
                r.location_tag.loc_tag if r.location_tag else "",
                r.month_count,
                r.year_count,
                r.get_status_display() if r.status else "",
                r.wo_number or "",
                r.description or "",
                r.actual_start.strftime("%Y-%m-%d") if r.actual_start else "",
                r.department.name if r.department else "",
                r.location_tag.equipment_parent.loc_tag if r.location_tag and r.location_tag.equipment_parent else "",
                r.parent_month_count,
                r.employees or "",
                r.created_by.username if r.created_by else "",
                r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                r.modified_by.username if r.modified_by else "",
                r.modified_at.strftime("%Y-%m-%d %H:%M") if r.modified_at else "",
            ])

        return response




@login_required
def report_detail_template(request, pk):
    report = get_object_or_404(
        DailyReport.objects.select_related(
            "location_tag",
            "location_tag__parent",
            "location_tag__unit",
            "department",
            "created_by",
            "modified_by",
        ),
        pk=pk
    )

    is_same_dept = (request.user.department is not None and 
                    request.user.department == report.department)
    
    is_within_time_limit = (timezone.now() - report.created_at) <= timedelta(days=7)
    
    can_edit = request.user.is_staff or (is_same_dept and is_within_time_limit)
    can_add = request.user.is_staff or is_same_dept

    return render(request, "daily_reports/dr_list/_report_detail_content.html", {
        "report": report,
        "can_add": can_add,
        "can_edit": can_edit,
    })  
