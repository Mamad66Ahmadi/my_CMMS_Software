# daily_reports/views.py

import csv
from datetime import date

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView

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
        today = date.today()

        # Annotate counts for the same location_tag
        queryset = queryset.annotate(
            year_count=Count(
                "location_tag__daily_reports",
                filter=Q(location_tag__daily_reports__date__year=today.year),
                distinct=True,
            ),
            month_count=Count(
                "location_tag__daily_reports",
                filter=Q(
                    location_tag__daily_reports__date__year=today.year,
                    location_tag__daily_reports__date__month=today.month,
                ),
                distinct=True,
            ),
        )

        # Sorting
        sort_by = self.request.GET.get("sort", "-date")
        allowed_sort = {
            "date": "date",
            "day": "date",  # same underlying field as date
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
        }

        sort_field = allowed_sort.get(sort_by.lstrip("-"), "date")
        if sort_by.startswith("-"):
            sort_field = f"-{sort_field}"

        queryset = queryset.order_by(sort_field, "-id")

        # Pagination
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
        today = date.today()

        queryset = queryset.annotate(
            year_count=Count(
                "location_tag__daily_reports",
                filter=Q(location_tag__daily_reports__date__year=today.year),
                distinct=True,
            ),
            month_count=Count(
                "location_tag__daily_reports",
                filter=Q(
                    location_tag__daily_reports__date__year=today.year,
                    location_tag__daily_reports__date__month=today.month,
                ),
                distinct=True,
            ),
        ).order_by("-date", "-id")

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="daily_reports.csv"'

        writer = csv.writer(response)
        writer.writerow([
            "Date",
            "Day",
            "Location Tag",
            "Father Tag",
            "Year Count",
            "Month Count",
            "WO Number",
            "Status",
            "Description",
            "Employees",
            "Department",
            "Actual Start",
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
                r.father_tag.loc_tag if r.father_tag else "",
                r.year_count,
                r.month_count,
                r.wo_number or "",
                r.get_status_display() if r.status else "",
                r.description or "",
                r.employees or "",
                r.department.name if r.department else "",
                r.actual_start.strftime("%Y-%m-%d") if r.actual_start else "",
                r.created_by.username if r.created_by else "",
                r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
                r.modified_by.username if r.modified_by else "",
                r.modified_at.strftime("%Y-%m-%d %H:%M") if r.modified_at else "",
            ])

        return response
