# daily_reports/views.py

import csv

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView
from datetime import timedelta
from django.utils import timezone

from .services import annotate_running_counts
from .models import DailyReport


def get_filtered_reports(request):
    filters = {
        "date_from": request.GET.get("date_from", "").strip(),
        "date_to": request.GET.get("date_to", "").strip(),
        "wo_number": request.GET.get("wo_number", "").strip(),
        "location_tag": request.GET.get("location_tag", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "department": request.GET.get("department", "").strip(),
    }

    queryset = DailyReport.objects.select_related(
        "location_tag",
        "location_tag__parent",
        "father_tag",
        "department",
        "created_by",
        "modified_by",
    ).all()

    # ✅ If no date filters → default to last 14 days
    if not filters["date_from"] and not filters["date_to"]:
        today = timezone.now().date()
        fourteen_days_ago = today - timedelta(days=14)
        queryset = queryset.filter(date__gte=fourteen_days_ago)
    else:
        if filters["date_from"]:
            queryset = queryset.filter(date__gte=filters["date_from"])

        if filters["date_to"]:
            queryset = queryset.filter(date__lte=filters["date_to"])

    if filters["wo_number"]:
        queryset = queryset.filter(wo_number__icontains=filters["wo_number"])

    if filters["location_tag"]:
        queryset = queryset.filter(location_tag__loc_tag__icontains=filters["location_tag"])

    if filters["status"]:
        queryset = queryset.filter(status=filters["status"])

    if filters["department"]:
        queryset = queryset.filter(department__name__icontains=filters["department"])

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
