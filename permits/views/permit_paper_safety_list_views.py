from urllib.parse import urlencode

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.generic import TemplateView

from accounts.models import User
from equipment.models.equipment_models import LocationTag
from permits.models import (
    PaperSafetyPermitType,
    PaperSafetyPermitWorkflowStep,
    PermitPaperSafetyPermit,
)


SAFETY_SORTS = {
    "safety_permit_number": "safety_permit_number",
    "safety_type": "safety_type__name",
    "current_step": "current_step__step_order",
    "location_tag": "location_tag__loc_tag",
    "permit_number": "permits__permit_number",
    "created_at": "created_at",
    "modified_at": "modified_at",
    "reviewed_at": "reviewed_at",
}
PER_PAGE_CHOICES = (10, 25, 50, 100)


def _filters(request):
    keys = (
        "q", "safety_permit_number", "safety_type", "current_step",
        "location_tag", "permit_number", "created_by", "modified_by",
        "reviewed_by", "created_from", "created_to", "reviewed_from", "reviewed_to",
    )
    return {key: request.GET.get(key, "").strip() for key in keys}


def _query_string(filters, sort_by, per_page):
    values = {key: value for key, value in filters.items() if value}
    if sort_by != "-created_at":
        values["sort"] = sort_by
    if per_page != 25:
        values["per_page"] = per_page
    return urlencode(values)


class PaperSafetyPermitList(LoginRequiredMixin, TemplateView):
    template_name = "permits/paper_safety_permit_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request
        filters = _filters(request)
        sort_by = request.GET.get("sort", "-created_at").strip()
        sort_key = sort_by.lstrip("-")
        if sort_key not in SAFETY_SORTS:
            sort_by = "-created_at"
        try:
            per_page = int(request.GET.get("per_page", 25))
        except (TypeError, ValueError):
            per_page = 25
        if per_page not in PER_PAGE_CHOICES:
            per_page = 25

        queryset = PermitPaperSafetyPermit.objects.select_related(
            "safety_type", "current_step", "location_tag", "created_by", "modified_by", "reviewed_by", "permit"
        ).prefetch_related("permits").all()
        if filters["q"]:
            query = Q()
            for value in filters["q"].split(","):
                value = value.strip()
                if value:
                    query |= Q(safety_permit_number__icontains=value)
                    query |= Q(safety_type__name__icontains=value)
                    query |= Q(safety_type__code__icontains=value)
                    query |= Q(current_step__name__icontains=value)
                    query |= Q(location_tag__loc_tag__icontains=value)
                    query |= Q(permit__permit_number__icontains=value)
                    query |= Q(permits__permit_number__icontains=value)
                    query |= Q(review_comment__icontains=value)
            queryset = queryset.filter(query)

        lookups = {
            "safety_permit_number": "safety_permit_number__icontains",
            "safety_type": "safety_type__name__icontains",
            "current_step": "current_step__name__icontains",
            "location_tag": "location_tag__loc_tag__icontains",
            "permit_number": "permits__permit_number__icontains",
            "created_by": "created_by__username__icontains",
            "modified_by": "modified_by__username__icontains",
            "reviewed_by": "reviewed_by__username__icontains",
        }
        for key, lookup in lookups.items():
            if filters[key]:
                queryset = queryset.filter(**{lookup: filters[key]})
        for key, lookup in (("created_from", "created_at__date__gte"), ("created_to", "created_at__date__lte"),
                            ("reviewed_from", "reviewed_at__date__gte"), ("reviewed_to", "reviewed_at__date__lte")):
            if filters[key]:
                queryset = queryset.filter(**{lookup: filters[key]})

        sort_field = SAFETY_SORTS[sort_by.lstrip("-")]
        queryset = queryset.order_by(("-" if sort_by.startswith("-") else "") + sort_field, "-pk").distinct()
        page_obj = Paginator(queryset, per_page).get_page(request.GET.get("page"))
        query_params = _query_string(filters, sort_by, per_page)
        context.update({
            "safety_permits": page_obj,
            "filters": filters,
            "sort_by": sort_by,
            "per_page": per_page,
            "query_params": query_params,
            "header_query_params": _query_string(filters, "-created_at", per_page),
            "safety_permit_types": PaperSafetyPermitType.objects.filter(is_active=True).order_by("sort_order", "name"),
            "safety_workflow_steps": PaperSafetyPermitWorkflowStep.objects.filter(is_active=True).order_by("step_order", "pk"),
            "locations": LocationTag.objects.order_by("loc_tag"),
            "users": User.objects.filter(is_active=True).order_by("username"),
            "has_advanced_filters": any(filters[key] for key in filters if key != "q"),
        })
        return context
