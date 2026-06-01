from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.views.generic import TemplateView
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from work_orders.models.fault_report_models import FaultReport,FaultReportStatus 


def get_filtered_fault_reports(request):
    filters = {
        "report_number": request.GET.get("report_number", "").strip(),
        "status": request.GET.get("status", "").strip(),
        "location_tag": request.GET.get("location_tag", "").strip(),
        "equipment": request.GET.get("equipment", "").strip(),
        "priority": request.GET.get("priority", "").strip(),
        "symptom": request.GET.get("symptom", "").strip(),
        "reported_by": request.GET.get("reported_by", "").strip(),
        "reported_department": request.GET.get("reported_department", "").strip(),
        "planner": request.GET.get("planner", "").strip(),
        "reviewed_by": request.GET.get("reviewed_by", "").strip(),
        "directive": request.GET.get("directive", "").strip(),
        "is_breakdown": request.GET.get("is_breakdown", "").strip(),
        "date_from": request.GET.get("date_from", "").strip(),
        "date_to": request.GET.get("date_to", "").strip(),
    }

    queryset = FaultReport.objects.select_related(
        "location_tag",
        "equipment",
        "priority",
        "symptom",
        "reported_by",
        "reported_department",
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

    queryset = apply_multi_value_filter(queryset, filters["report_number"], "report_number")
    queryset = apply_multi_value_filter(queryset, filters["location_tag"], "location_tag__loc_tag")
    queryset = apply_multi_value_filter(queryset, filters["equipment"], "equipment__serial_number")
    queryset = apply_multi_value_filter(queryset, filters["reported_by"], "reported_by__username")
    queryset = apply_multi_value_filter(queryset, filters["reported_department"], "reported_department__name")
    queryset = apply_multi_value_filter(queryset, filters["reviewed_by"], "reviewed_by__username")
    queryset = apply_multi_value_filter(queryset, filters["planner"], "planner__username")
    queryset = apply_multi_value_filter(queryset, filters["directive"], "directive")

    # Status filter:
    # Default = only SUBMITTED and APPROVED
    # If user explicitly chooses a status, respect it
    if filters["status"]:
        queryset = queryset.filter(status=filters["status"])
    else:
        queryset = queryset.filter(
            status__in=[
                FaultReportStatus.SUBMITTED,
                FaultReportStatus.APPROVED,
            ]
        )

    if filters["priority"]:
        queryset = queryset.filter(priority_id=filters["priority"])

    if filters["symptom"]:
        queryset = queryset.filter(symptom_id=filters["symptom"])

    if filters["is_breakdown"] in ["true", "false"]:
        queryset = queryset.filter(is_breakdown=(filters["is_breakdown"] == "true"))

    # Date filter:
    # Default = only last 30 days
    # If user provides date_from/date_to, use those instead
    if filters["date_from"]:
        queryset = queryset.filter(reported_at__date__gte=filters["date_from"])
    if filters["date_to"]:
        queryset = queryset.filter(reported_at__date__lte=filters["date_to"])

    if not filters["date_from"] and not filters["date_to"]:
        queryset = queryset.filter(
            reported_at__gte=timezone.now() - timedelta(days=30)
        )

    return queryset, filters


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
            "symptom": "symptom__name",
            "reported_by": "reported_by__username",
            "reported_department": "reported_department__name",
            "reported_at": "reported_at",
            "reviewed_by": "reviewed_by__username",
            "reviewed_at": "reviewed_at",
            "planner": "planner__username",
            "planner_reviewed_at": "planner_reviewed_at",
            "directive": "directive",
            "is_breakdown": "is_breakdown",
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
