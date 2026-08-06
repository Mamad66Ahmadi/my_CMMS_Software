# permits/views/permit_list_views.py

from urllib.parse import urlencode
import csv
import re

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Q, Min, Case, When, Value, IntegerField
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.db import transaction
from django.http import HttpResponseBadRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.text import slugify

from accounts.models import Department, UserFilterFavorite
from permits.models.permit_base_models import Hazard as HazardCode, PermitType
from permits.models.permit_models import Permit
from permits.models.workflow_models import PermitWorkflowStep
from permits.services.user_filter_favorite import (
    FAVORITE_APP_KEY,
    FAVORITE_VIEW_KEY,
    FILTER_KEYS,
    PER_PAGE_CHOICES,
    DEFAULT_SORT,
    DEFAULT_PER_PAGE,
)



# =============================================================================
# Filter state helpers
# =============================================================================

def get_request_filters(request):
    """
    Filters for the new workflow-based Permit model.

    Note:
    - Old `status` is replaced by `current_step`.
    - Old `description` is replaced by `scope_of_work`.
    - Old `comment` is replaced by `remarks`.
    - Old `hazard_codes` is replaced by `hazards` through PermitHazard.
    """

    current_step_param = request.GET.get("current_step")

    return {
        "q": request.GET.get("q", "").strip(),

        # Identification
        "permit_number": request.GET.get("permit_number", "").strip(),
        "continuation_of": request.GET.get("continuation_of", "").strip(),
        "permit_type": request.GET.get("permit_type", "").strip(),

        # Workflow
        "current_step": current_step_param.strip() if current_step_param else "",
        "workflow": request.GET.get("workflow", "").strip(),
        "is_terminal": request.GET.get("is_terminal", "").strip(),

        # Location / WO
        "location_tag": request.GET.get("location_tag", "").strip(),
        "parent_tag": request.GET.get("parent_tag", "").strip(),
        "unit": request.GET.get("unit", "").strip(),
        "train": request.GET.get("train", "").strip(),
        "work_order": request.GET.get("work_order", "").strip(),

        # Department / personnel
        "department": request.GET.get("department", "").strip(),
        "work_supervisor": request.GET.get("work_supervisor", "").strip(),
        "designated_area_authority": request.GET.get("designated_area_authority", "").strip(),
        "designated_area_supervisor": request.GET.get("designated_area_supervisor", "").strip(),

        # Work details
        "scope_of_work": request.GET.get("scope_of_work", "").strip(),
        "remarks": request.GET.get("remarks", "").strip(),
        "hazard_code": request.GET.get("hazard_code", "").strip(),
        "precaution_code": request.GET.get("precaution_code", "").strip(),

        # Tools / materials
        "electrical_tools": request.GET.get("electrical_tools", "").strip(),
        "mechanical_tools": request.GET.get("mechanical_tools", "").strip(),
        "hazardous_materials": request.GET.get("hazardous_materials", "").strip(),
        "vehicle_required": request.GET.get("vehicle_required", "").strip(),

        # Equipment preparation
        "mechanical_isolation": request.GET.get("mechanical_isolation", "").strip(),
        "equipment_depressurized": request.GET.get("equipment_depressurized", "").strip(),
        "equipment_drained": request.GET.get("equipment_drained", "").strip(),
        "equipment_purged": request.GET.get("equipment_purged", "").strip(),
        "process_isolation": request.GET.get("process_isolation", "").strip(),
        "area_authority_present_required": request.GET.get("area_authority_present_required", "").strip(),
        "fire_watch_present_required": request.GET.get("fire_watch_present_required", "").strip(),

        # Validity
        "valid_from_date": request.GET.get("valid_from_date", "").strip(),
        "valid_to_date": request.GET.get("valid_to_date", "").strip(),
        "is_currently_valid": request.GET.get("is_currently_valid", "").strip(),
        "has_expired": request.GET.get("has_expired", "").strip(),

        # Step audit timestamps
        "activated": request.GET.get("activated", "").strip(),
        "suspended": request.GET.get("suspended", "").strip(),
        "completed": request.GET.get("completed", "").strip(),
        "closed": request.GET.get("closed", "").strip(),

        # Audit
        "created_from": request.GET.get("created_from", "").strip(),
        "created_to": request.GET.get("created_to", "").strip(),
        "modified_from": request.GET.get("modified_from", "").strip(),
        "modified_to": request.GET.get("modified_to", "").strip(),
        "created_by": request.GET.get("created_by", "").strip(),
        "modified_by": request.GET.get("modified_by", "").strip(),
    }


def get_post_filters(request):
    """
    Same as get_request_filters(), but for POST if you still use
    saved filter forms or favorite creation forms.
    """

    current_step_param = request.POST.get("current_step")

    return {
        "q": request.POST.get("q", "").strip(),

        "permit_number": request.POST.get("permit_number", "").strip(),
        "continuation_of": request.POST.get("continuation_of", "").strip(),
        "permit_type": request.POST.get("permit_type", "").strip(),

        "current_step": current_step_param.strip() if current_step_param else "",
        "workflow": request.POST.get("workflow", "").strip(),
        "is_terminal": request.POST.get("is_terminal", "").strip(),

        "location_tag": request.POST.get("location_tag", "").strip(),
        "parent_tag": request.POST.get("parent_tag", "").strip(),
        "unit": request.POST.get("unit", "").strip(),
        "train": request.POST.get("train", "").strip(),
        "work_order": request.POST.get("work_order", "").strip(),

        "department": request.POST.get("department", "").strip(),
        "work_supervisor": request.POST.get("work_supervisor", "").strip(),
        "designated_area_authority": request.POST.get("designated_area_authority", "").strip(),
        "designated_area_supervisor": request.POST.get("designated_area_supervisor", "").strip(),

        "scope_of_work": request.POST.get("scope_of_work", "").strip(),
        "remarks": request.POST.get("remarks", "").strip(),
        "hazard_code": request.POST.get("hazard_code", "").strip(),
        "precaution_code": request.POST.get("precaution_code", "").strip(),

        "electrical_tools": request.POST.get("electrical_tools", "").strip(),
        "mechanical_tools": request.POST.get("mechanical_tools", "").strip(),
        "hazardous_materials": request.POST.get("hazardous_materials", "").strip(),
        "vehicle_required": request.POST.get("vehicle_required", "").strip(),

        "mechanical_isolation": request.POST.get("mechanical_isolation", "").strip(),
        "equipment_depressurized": request.POST.get("equipment_depressurized", "").strip(),
        "equipment_drained": request.POST.get("equipment_drained", "").strip(),
        "equipment_purged": request.POST.get("equipment_purged", "").strip(),
        "process_isolation": request.POST.get("process_isolation", "").strip(),
        "area_authority_present_required": request.POST.get("area_authority_present_required", "").strip(),
        "fire_watch_present_required": request.POST.get("fire_watch_present_required", "").strip(),

        "valid_from_date": request.POST.get("valid_from_date", "").strip(),
        "valid_to_date": request.POST.get("valid_to_date", "").strip(),
        "is_currently_valid": request.POST.get("is_currently_valid", "").strip(),
        "has_expired": request.POST.get("has_expired", "").strip(),

        "activated": request.POST.get("activated", "").strip(),
        "suspended": request.POST.get("suspended", "").strip(),
        "completed": request.POST.get("completed", "").strip(),
        "closed": request.POST.get("closed", "").strip(),

        "created_from": request.POST.get("created_from", "").strip(),
        "created_to": request.POST.get("created_to", "").strip(),
        "modified_from": request.POST.get("modified_from", "").strip(),
        "modified_to": request.POST.get("modified_to", "").strip(),
        "created_by": request.POST.get("created_by", "").strip(),
        "modified_by": request.POST.get("modified_by", "").strip(),
    }


def compact_filters(filters):
    return {
        key: value
        for key, value in filters.items()
        if value not in ["", None]
    }


def normalize_per_page(value):
    try:
        per_page = int(value)
    except (TypeError, ValueError):
        return DEFAULT_PER_PAGE

    if per_page not in PER_PAGE_CHOICES:
        return DEFAULT_PER_PAGE

    return per_page


def get_allowed_sort():
    return {
        "permit_number": "permit_number",
        "continuation_of": "continuation_of__permit_number",
        "permit_type": "permit_type__name",

        "workflow": "workflow__name",
        "current_step": "current_step__step_number",
        "current_step_title": "current_step__title",
        "is_terminal": "current_step__is_terminal",

        "location_tag": "location_tag__loc_tag",
        "unit": "location_tag__unit__unit_code",
        "train": "location_tag__train",
        "work_order": "work_order__wo_number",

        "scope_of_work": "scope_of_work",
        "department": "department__name",

        "work_supervisor": "work_supervisor__username",
        "designated_area_authority": "designated_area_authority__username",
        "designated_area_supervisor": "designated_area_supervisor__username",

        "hazard_code": "first_hazard_code",
        "precaution_code": "first_precaution_code",

        "vehicle_required": "vehicle_required",
        "area_authority_present_required": "area_authority_present_required",
        "fire_watch_present_required": "fire_watch_present_required",

        "mechanical_isolation": "mechanical_isolation",
        "equipment_depressurized": "equipment_depressurized",
        "equipment_drained": "equipment_drained",
        "equipment_purged": "equipment_purged",
        "process_isolation": "process_isolation",

        "valid_from": "valid_from",
        "valid_to": "valid_to",

        "activated_at": "activated_at",
        "suspended_at": "suspended_at",
        "completed_at": "completed_at",
        "closed_at": "closed_at",

        "created_at": "created_at",
        "created_by": "created_by__username",
        "modified_at": "modified_at",
        "modified_by": "modified_by__username",
    }


def normalize_sort(sort_by):
    sort_by = (sort_by or DEFAULT_SORT).strip()
    sort_key = sort_by.lstrip("-")

    if sort_key not in get_allowed_sort():
        return DEFAULT_SORT

    return f"-{sort_key}" if sort_by.startswith("-") else sort_key


def get_user_favorites(user):
    return UserFilterFavorite.objects.filter(
        user=user,
        app_key=FAVORITE_APP_KEY,
        view_key=FAVORITE_VIEW_KEY,
    ).order_by("name")


def get_favorite_by_id(user, favorite_id):
    if not favorite_id:
        return None

    return UserFilterFavorite.objects.filter(
        pk=favorite_id,
        user=user,
        app_key=FAVORITE_APP_KEY,
        view_key=FAVORITE_VIEW_KEY,
    ).first()


def get_default_favorite(user):
    return UserFilterFavorite.objects.filter(
        user=user,
        app_key=FAVORITE_APP_KEY,
        view_key=FAVORITE_VIEW_KEY,
        is_default=True,
    ).first()


def has_manual_filters(request):
    for key in FILTER_KEYS:
        if request.GET.get(key, "").strip():
            return True

    if request.GET.get("sort", "").strip():
        return True

    if request.GET.get("per_page", "").strip():
        return True

    return False


def build_query_string(filters, sort_by=None, per_page=None, favorite_id=None):
    params = {}

    for key in FILTER_KEYS:
        value = filters.get(key, "")
        if value not in ["", None]:
            params[key] = value

    if sort_by:
        params["sort"] = sort_by

    if per_page:
        params["per_page"] = per_page

    if favorite_id:
        params["favorite"] = favorite_id

    return urlencode(params)


def get_effective_state(request):
    manual_filters = get_request_filters(request)
    manual_sort = normalize_sort(request.GET.get("sort", DEFAULT_SORT))
    manual_per_page = normalize_per_page(request.GET.get("per_page", DEFAULT_PER_PAGE))
    favorite_id = request.GET.get("favorite")

    selected_favorite = get_favorite_by_id(request.user, favorite_id)

    if has_manual_filters(request):
        return {
            "filters": manual_filters,
            "sort_by": manual_sort,
            "per_page": manual_per_page,
            "selected_favorite": selected_favorite,
            "using_favorite": False,
        }

    if selected_favorite:
        favorite_filters = dict(selected_favorite.filters or {})

        return {
            "filters": favorite_filters,
            "sort_by": normalize_sort(selected_favorite.sort_by or DEFAULT_SORT),
            "per_page": normalize_per_page(selected_favorite.per_page or DEFAULT_PER_PAGE),
            "selected_favorite": selected_favorite,
            "using_favorite": True,
        }

    default_favorite = get_default_favorite(request.user)

    if default_favorite:
        favorite_filters = dict(default_favorite.filters or {})

        return {
            "filters": favorite_filters,
            "sort_by": normalize_sort(default_favorite.sort_by or DEFAULT_SORT),
            "per_page": normalize_per_page(default_favorite.per_page or DEFAULT_PER_PAGE),
            "selected_favorite": default_favorite,
            "using_favorite": True,
        }

    return {
        "filters": manual_filters,
        "sort_by": manual_sort,
        "per_page": manual_per_page,
        "selected_favorite": None,
        "using_favorite": False,
    }


# =============================================================================
# Query filtering
# =============================================================================

def get_filtered_permits(filters):
    queryset = (
        Permit.objects.select_related(
            "continuation_of",
            "permit_type",
            "workflow",
            "current_step",
            "location_tag",
            "location_tag__parent",
            "location_tag__unit",
            "work_order",
            "department",
            "work_supervisor",
            "designated_area_authority",
            "designated_area_supervisor",
            "created_by",
            "modified_by",
        )
        .prefetch_related(
            "hazards",
            "precautions",
        )
        .all()
    )

    def split_csv(value):
        return [item.strip() for item in value.split(",") if item.strip()]

    def apply_multi_value_filter(qs, filter_str, field_lookup):
        if not filter_str:
            return qs

        values = split_csv(filter_str)
        if not values:
            return qs

        query = Q()
        for val in values:
            query |= Q(**{f"{field_lookup}__icontains": val})

        return qs.filter(query)

    def apply_choice_filter(qs, value, field_name):
        if not value:
            return qs

        values = split_csv(value)
        if not values:
            return qs

        return qs.filter(**{f"{field_name}__in": values})

    def apply_boolean_filter(qs, value, field_name):
        if not value or str(value).strip() == "":
            return qs

        normalized = str(value).strip().lower()

        if normalized in ["1", "true", "yes", "on"]:
            return qs.filter(**{field_name: True})

        if normalized in ["0", "false", "no", "off"]:
            return qs.filter(**{field_name: False})

        return qs

    def apply_null_datetime_filter(qs, value, field_name):
        """
        For filters like activated, closed, completed:
        true  => field is not null
        false => field is null
        """
        if not value or str(value).strip() == "":
            return qs

        normalized = str(value).strip().lower()

        if normalized in ["1", "true", "yes", "on"]:
            return qs.filter(**{f"{field_name}__isnull": False})

        if normalized in ["0", "false", "no", "off"]:
            return qs.filter(**{f"{field_name}__isnull": True})

        return qs

    has_quick_search = bool(filters.get("q"))

    if has_quick_search:
        q_values = split_csv(filters["q"])

        if q_values:
            quick_query = Q()

            for value in q_values:
                quick_query |= Q(permit_number__icontains=value)
                quick_query |= Q(work_order__wo_number__icontains=value)
                quick_query |= Q(location_tag__loc_tag__icontains=value)
                quick_query |= Q(scope_of_work__icontains=value)
                quick_query |= Q(remarks__icontains=value)
                quick_query |= Q(permit_type__code__icontains=value)
                quick_query |= Q(permit_type__name__icontains=value)
                quick_query |= Q(current_step__title__icontains=value)
                quick_query |= Q(department__name__icontains=value)

            queryset = queryset.filter(quick_query)

    # Identification
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("permit_number", ""),
        "permit_number",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("continuation_of", ""),
        "continuation_of__permit_number",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("permit_type", ""),
        "permit_type__name",
    )

    # Workflow
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("workflow", ""),
        "workflow__name",
    )

    queryset = apply_multi_value_filter(
        queryset,
        filters.get("current_step", ""),
        "current_step__title",
    )

    queryset = apply_boolean_filter(
        queryset,
        filters.get("is_terminal", ""),
        "current_step__is_terminal",
    )

    # Location / WO
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("location_tag", ""),
        "location_tag__loc_tag",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("work_order", ""),
        "work_order__wo_number",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("unit", ""),
        "location_tag__unit__unit_code",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("train", ""),
        "location_tag__train",
    )

    if filters.get("parent_tag"):
        parent_values = split_csv(filters["parent_tag"])
        parent_query = Q()

        for val in parent_values:
            parent_query |= (
                Q(location_tag__loc_tag__icontains=val)
                | Q(location_tag__parent__loc_tag__icontains=val)
            )

        queryset = queryset.filter(parent_query)

    # Department / people
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("department", ""),
        "department__name",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("work_supervisor", ""),
        "work_supervisor__username",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("designated_area_authority", ""),
        "designated_area_authority__username",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("designated_area_supervisor", ""),
        "designated_area_supervisor__username",
    )

    # Work details
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("scope_of_work", ""),
        "scope_of_work",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("remarks", ""),
        "remarks",
    )

    # Hazards through PermitHazard
    if filters.get("hazard_code"):
        hazard_values = split_csv(filters["hazard_code"])
        hazard_query = Q()

        for val in hazard_values:
            hazard_query |= Q(hazards__code__icontains=val)
            hazard_query |= Q(hazards__name__icontains=val)
            hazard_query |= Q(hazards__description__icontains=val)

        # Only active through-records
        queryset = queryset.filter(
            hazard_assessments__is_active=True,
        ).filter(hazard_query)

    # Precautions through PermitPrecaution
    if filters.get("precaution_code"):
        precaution_values = split_csv(filters["precaution_code"])
        precaution_query = Q()

        for val in precaution_values:
            precaution_query |= Q(precautions__code__icontains=val)
            precaution_query |= Q(precautions__name__icontains=val)
            precaution_query |= Q(precautions__description__icontains=val)

        queryset = queryset.filter(
            precaution_requirements__is_active=True,
        ).filter(precaution_query)

    # Tools / materials
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("electrical_tools", ""),
        "electrical_tools",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("mechanical_tools", ""),
        "mechanical_tools",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("hazardous_materials", ""),
        "hazardous_materials",
    )
    queryset = apply_boolean_filter(
        queryset,
        filters.get("vehicle_required", ""),
        "vehicle_required",
    )

    # Equipment preparation choices
    queryset = apply_choice_filter(
        queryset,
        filters.get("mechanical_isolation", ""),
        "mechanical_isolation",
    )
    queryset = apply_choice_filter(
        queryset,
        filters.get("equipment_depressurized", ""),
        "equipment_depressurized",
    )
    queryset = apply_choice_filter(
        queryset,
        filters.get("equipment_drained", ""),
        "equipment_drained",
    )
    queryset = apply_choice_filter(
        queryset,
        filters.get("equipment_purged", ""),
        "equipment_purged",
    )
    queryset = apply_choice_filter(
        queryset,
        filters.get("process_isolation", ""),
        "process_isolation",
    )

    queryset = apply_boolean_filter(
        queryset,
        filters.get("area_authority_present_required", ""),
        "area_authority_present_required",
    )
    queryset = apply_boolean_filter(
        queryset,
        filters.get("fire_watch_present_required", ""),
        "fire_watch_present_required",
    )

    # Date filters
    if filters.get("valid_from_date"):
        queryset = queryset.filter(valid_from__date__gte=filters["valid_from_date"])

    if filters.get("valid_to_date"):
        queryset = queryset.filter(valid_to__date__lte=filters["valid_to_date"])

    if filters.get("created_from"):
        queryset = queryset.filter(created_at__date__gte=filters["created_from"])

    if filters.get("created_to"):
        queryset = queryset.filter(created_at__date__lte=filters["created_to"])

    if filters.get("modified_from"):
        queryset = queryset.filter(modified_at__date__gte=filters["modified_from"])

    if filters.get("modified_to"):
        queryset = queryset.filter(modified_at__date__lte=filters["modified_to"])

    # Runtime validity
    if filters.get("is_currently_valid") and not has_quick_search:
        now = timezone.now()
        normalized = str(filters["is_currently_valid"]).strip().lower()

        currently_valid_query = Q(
            valid_from__lte=now,
            valid_to__gte=now,
            activated_at__isnull=False,
            closed_at__isnull=True,
            current_step__is_terminal=False,
        )

        if normalized in ["1", "true", "yes", "on"]:
            queryset = queryset.filter(currently_valid_query)
        elif normalized in ["0", "false", "no", "off"]:
            queryset = queryset.exclude(currently_valid_query)

    if filters.get("has_expired"):
        now = timezone.now()
        normalized = str(filters["has_expired"]).strip().lower()

        if normalized in ["1", "true", "yes", "on"]:
            queryset = queryset.filter(valid_to__lt=now)
        elif normalized in ["0", "false", "no", "off"]:
            queryset = queryset.filter(valid_to__gte=now)

    # Step timestamp state
    queryset = apply_null_datetime_filter(
        queryset,
        filters.get("activated", ""),
        "activated_at",
    )
    queryset = apply_null_datetime_filter(
        queryset,
        filters.get("suspended", ""),
        "suspended_at",
    )
    queryset = apply_null_datetime_filter(
        queryset,
        filters.get("completed", ""),
        "completed_at",
    )
    queryset = apply_null_datetime_filter(
        queryset,
        filters.get("closed", ""),
        "closed_at",
    )

    # Audit user filters
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("created_by", ""),
        "created_by__username",
    )
    queryset = apply_multi_value_filter(
        queryset,
        filters.get("modified_by", ""),
        "modified_by__username",
    )

    return queryset.distinct(), filters


# =============================================================================
# List view
# =============================================================================

class PermitList(LoginRequiredMixin, TemplateView):
    template_name = "permits/permit_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        state = get_effective_state(self.request)
        filters = state["filters"]
        sort_by = state["sort_by"]
        per_page = state["per_page"]
        selected_favorite = state["selected_favorite"]

        queryset, filters = get_filtered_permits(filters)

        queryset = queryset.annotate(
            first_hazard_code=Min("hazards__code"),
            first_precaution_code=Min("precautions__code"),
            workflow_state_sort=Case(
                When(current_step__is_start=True, then=Value(1)),
                When(activated_at__isnull=False, closed_at__isnull=True, then=Value(2)),
                When(suspended_at__isnull=False, closed_at__isnull=True, then=Value(3)),
                When(completed_at__isnull=False, closed_at__isnull=True, then=Value(4)),
                When(current_step__is_terminal=True, then=Value(5)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )

        allowed_sort = get_allowed_sort()

        # Add annotation-based sort keys
        allowed_sort.update(
            {
                "workflow_state": "workflow_state_sort",
            }
        )

        sort_key = sort_by.lstrip("-")
        sort_field = allowed_sort.get(sort_key, "created_at")

        if sort_by.startswith("-"):
            queryset = queryset.order_by(f"-{sort_field}", "-id")
        else:
            queryset = queryset.order_by(sort_field, "-id")

        paginator = Paginator(queryset.distinct(), per_page)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        has_advanced_filters = any(
            filters.get(k)
            for k in filters
            if k not in ["q"]
        )

        def build_remove_url(key_to_remove):
            remaining_filters = dict(filters)
            remaining_filters[key_to_remove] = ""

            query_string = build_query_string(
                remaining_filters,
                sort_by=sort_by,
                per_page=per_page,
                favorite_id=selected_favorite.pk if selected_favorite else None,
            )

            return f"?{query_string}" if query_string else "?"

        active_filter_badges = []

        badge_labels = {
            "permit_number": "Permit No.",
            "continuation_of": "Continuation Of",
            "permit_type": "Permit Type",
            "workflow": "Workflow",
            "current_step": "Current Step",
            "location_tag": "Location Tag",
            "parent_tag": "Parent Tag",
            "unit": "Unit",
            "train": "Train",
            "work_order": "Work Order",
            "department": "Department",
            "work_supervisor": "Work Supervisor",
            "designated_area_authority": "Area Authority",
            "designated_area_supervisor": "Area Supervisor",
            "scope_of_work": "Scope of Work",
            "remarks": "Remarks",
            "hazard_code": "Hazard",
            "precaution_code": "Precaution",
            "electrical_tools": "Electrical Tools",
            "mechanical_tools": "Mechanical Tools",
            "hazardous_materials": "Hazardous Materials",
            "mechanical_isolation": "Mechanical Isolation",
            "equipment_depressurized": "Depressurized",
            "equipment_drained": "Drained",
            "equipment_purged": "Purged",
            "process_isolation": "Process Isolation",
            "valid_from_date": "Valid From",
            "valid_to_date": "Valid To",
            "created_from": "Created From",
            "created_to": "Created To",
            "modified_from": "Modified From",
            "modified_to": "Modified To",
            "created_by": "Created By",
            "modified_by": "Modified By",
        }

        for key, label in badge_labels.items():
            value = filters.get(key)

            if value:
                active_filter_badges.append(
                    {
                        "key": key,
                        "label": label,
                        "value": value,
                        "remove_url": build_remove_url(key),
                    }
                )

        bool_labels = {
            "is_terminal": "Terminal Step",
            "vehicle_required": "Vehicle Required",
            "area_authority_present_required": "Area Authority Present Required",
            "fire_watch_present_required": "Fire Watch Required",
            "is_currently_valid": "Currently Valid",
            "has_expired": "Expired",
            "activated": "Activated",
            "suspended": "Suspended",
            "completed": "Completed",
            "closed": "Closed",
        }

        for key, label in bool_labels.items():
            value = filters.get(key)

            if value:
                normalized = str(value).strip().lower()
                display_value = "True" if normalized in ["1", "true", "yes", "on"] else "False"

                active_filter_badges.append(
                    {
                        "key": key,
                        "label": label,
                        "value": display_value,
                        "remove_url": build_remove_url(key),
                    }
                )

        if filters.get("q"):
            active_filter_badges = []

        query_params = build_query_string(
            filters,
            sort_by=sort_by,
            per_page=per_page,
            favorite_id=selected_favorite.pk if selected_favorite else None,
        )

        header_query_params = build_query_string(
            filters,
            per_page=per_page,
            favorite_id=selected_favorite.pk if selected_favorite else None,
        )

        context.update(
            {
                "permits": page_obj,
                "filters": filters,
                "sort_by": sort_by,
                "per_page": per_page,
                "query_params": query_params,
                "header_query_params": header_query_params,

                # Filter dropdown data
                "permit_types": PermitType.objects.filter(is_active=True).order_by("name"),
                "workflow_steps": PermitWorkflowStep.objects.select_related("workflow").order_by(
                    "workflow__name",
                    "workflow__version",
                    "step_number",
                ),
                "hazard_codes": HazardCode.objects.filter(is_active=True).order_by("code"),
                "departments": Department.objects.filter(is_active=True).order_by("name"),

                "has_advanced_filters": has_advanced_filters,
                "active_filter_badges": active_filter_badges,

                "filter_favorites": get_user_favorites(self.request.user),
                "selected_favorite": selected_favorite,
                "using_favorite": state["using_favorite"],
            }
        )

        return context

# =============================================================================
# Filters
# =============================================================================

class PermitFilterFavoriteSaveView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        name = request.POST.get("name", "").strip()
        favorite_id = request.POST.get("favorite_id", "").strip()
        is_default = request.POST.get("is_default") in ["1", "true", "on", "yes"]

        if not name:
            return HttpResponseBadRequest("Favorite name is required.")

        filters = compact_filters(get_post_filters(request))
        sort_by = normalize_sort(request.POST.get("sort", DEFAULT_SORT))
        per_page = normalize_per_page(request.POST.get("per_page", DEFAULT_PER_PAGE))

        with transaction.atomic():
            if is_default:
                UserFilterFavorite.objects.filter(
                    user=request.user,
                    app_key=FAVORITE_APP_KEY,
                    view_key=FAVORITE_VIEW_KEY,
                    is_default=True,
                ).update(is_default=False)

            if favorite_id:
                favorite = get_object_or_404(
                    UserFilterFavorite,
                    pk=favorite_id,
                    user=request.user,
                    app_key=FAVORITE_APP_KEY,
                    view_key=FAVORITE_VIEW_KEY,
                )
                favorite.name = name
                favorite.filters = filters
                favorite.sort_by = sort_by
                favorite.per_page = per_page
                favorite.is_default = is_default
            else:
                favorite = UserFilterFavorite(
                    user=request.user,
                    app_key=FAVORITE_APP_KEY,
                    view_key=FAVORITE_VIEW_KEY,
                    name=name,
                    filters=filters,
                    sort_by=sort_by,
                    per_page=per_page,
                    is_default=is_default,
                )

            try:
                favorite.full_clean()
                favorite.save()
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))

                redirect_url = redirect("permits:permit_list").url
                if favorite_id:
                    redirect_url = f"{redirect_url}?favorite={favorite_id}"

                return redirect(redirect_url)

        messages.success(request, "Favorite filter saved.")
        return redirect(f"{redirect('permits:permit_list').url}?favorite={favorite.pk}")


class PermitFilterFavoriteDeleteView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        favorite = get_object_or_404(
            UserFilterFavorite,
            pk=pk,
            user=request.user,
            app_key=FAVORITE_APP_KEY,
            view_key=FAVORITE_VIEW_KEY,
        )
        favorite.delete()
        messages.success(request, "Favorite filter deleted.")
        return redirect("permits:permit_list")


# ------------------------ CSV Export ------------------------------------------
class PermitExportCSV(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        state = get_effective_state(request)
        filters = state["filters"]

        queryset, filters = get_filtered_permits(filters)
        
        # Optimize query by executing a specific ordering without complex annotations
        queryset = queryset.order_by("-created_at", "-id")

        filter_parts = []
        for key, value in request.GET.items():
            if key in ["page", "sort", "csrfmiddlewaretoken"]:
                continue
            if value:
                clean_key = re.sub(r'[^a-zA-Z0-9_-]', '', key)
                clean_value = slugify(value)
                if clean_key and clean_value:
                    filter_parts.append(f"{clean_key}-{clean_value}")

        if filter_parts:
            filename_suffix = "_".join(filter_parts)
            if len(filename_suffix) > 100:
                filename_suffix = filename_suffix[:100] + "-truncated"
            filename = f"permits_{filename_suffix}.csv"
        else:
            # Handle default name based on the current step/active state
            if filters.get("current_step") and not request.GET.get("q"):
                filename = f"permits_step-{slugify(filters['current_step'])}.csv"
            else:
                filename = "permits_all.csv"

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        # Ensure Excel parses Persian / UTF-8 characters correctly
        response.write("\ufeff")
        writer = csv.writer(response)

        # Header fields reflecting the new schema
        writer.writerow([
            "ID", "Permit Number", "Continuation Of ID", "Continuation Of Permit Number",
            "Permit Type", "Workflow", "Current Step", "Is Terminal",
            "Location Tag ID", "Location Tag", "Unit", "Train", "Work Order ID", "Work Order Number", 
            "Scope of Work", "Remarks", "Hazards List", "Precautions List",
            "Duration Value", "Duration Unit", "Estimated Personnel",
            "Electrical Tools", "Mechanical Tools", "Other Tools", "Hazardous Materials", 
            "Non-Explosion Proof Equipment", "Vehicle Required", "Vehicle Description",
            "Mechanical Isolation", "Equipment Depressurized", "Equipment Drained", "Equipment Purged", "Process Isolation",
            "AA Present Required", "Fire Watch Required", "Equipment Preparation Notes",
            "Work Supervisor Username", "Department", 
            "Designated Area Authority", "Designated Area Supervisor",
            "Valid From", "Valid To", "Is Active (Current Step Context)",
            "Activated At", "Suspended At", "Completed At", "Closed At",
            "Created At", "Created By Username", "Modified At", "Modified By Username"
        ])

        for permit in queryset:
            hazards_list = ", ".join(
                permit.hazards.filter(
                    permit_assessments__permit=permit,
                    permit_assessments__is_active=True,
                ).values_list("code", flat=True).distinct()
            )

            precautions_list = ", ".join(
                permit.precautions.filter(
                    permit_requirements__permit=permit,
                    permit_requirements__is_active=True,
                ).values_list("code", flat=True).distinct()
            )

            writer.writerow([
                permit.pk,
                permit.permit_number or "",
                permit.continuation_of_id or "",
                permit.continuation_of.permit_number if permit.continuation_of else "",
                permit.permit_type.name if permit.permit_type else "",
                permit.workflow.name if permit.workflow else "",
                permit.current_step.title if permit.current_step else "",
                permit.current_step.is_terminal if permit.current_step else False,
                permit.location_tag_id or "",
                permit.location_tag.loc_tag if permit.location_tag else "",
                permit.location_tag.unit.unit_code if (permit.location_tag and permit.location_tag.unit) else "",
                permit.location_tag.train if permit.location_tag else "",
                permit.work_order_id or "",
                permit.work_order.wo_number if permit.work_order else "",
                permit.scope_of_work or "",
                permit.remarks or "",
                hazards_list,
                precautions_list,
                permit.duration_value or "",
                permit.get_duration_unit_display() if permit.duration_unit else "",
                permit.estimated_personnel or "",
                permit.electrical_tools or "",
                permit.mechanical_tools or "",
                permit.other_tools or "",
                permit.hazardous_materials or "",
                permit.non_explosion_proof_equipment or "",
                permit.vehicle_required,
                permit.vehicle_description or "",
                permit.get_mechanical_isolation_display() if permit.mechanical_isolation else "",
                permit.get_equipment_depressurized_display() if permit.equipment_depressurized else "",
                permit.get_equipment_drained_display() if permit.equipment_drained else "",
                permit.get_equipment_purged_display() if permit.equipment_purged else "",
                permit.get_process_isolation_display() if permit.process_isolation else "",
                permit.area_authority_present_required,
                permit.fire_watch_present_required,
                permit.equipment_preparation_notes or "",
                permit.work_supervisor.username if permit.work_supervisor else "",
                permit.department.name if permit.department else "",
                permit.designated_area_authority.username if permit.designated_area_authority else "",
                permit.designated_area_supervisor.username if permit.designated_area_supervisor else "",
                permit.valid_from.strftime("%Y-%m-%d %H:%M:%S") if permit.valid_from else "",
                permit.valid_to.strftime("%Y-%m-%d %H:%M:%S") if permit.valid_to else "",
                permit.is_active,
                permit.activated_at.strftime("%Y-%m-%d %H:%M:%S") if permit.activated_at else "",
                permit.suspended_at.strftime("%Y-%m-%d %H:%M:%S") if permit.suspended_at else "",
                permit.completed_at.strftime("%Y-%m-%d %H:%M:%S") if permit.completed_at else "",
                permit.closed_at.strftime("%Y-%m-%d %H:%M:%S") if permit.closed_at else "",
                permit.created_at.strftime("%Y-%m-%d %H:%M:%S") if permit.created_at else "",
                permit.created_by.username if permit.created_by else "",
                permit.modified_at.strftime("%Y-%m-%d %H:%M:%S") if permit.modified_at else "",
                permit.modified_by.username if permit.modified_by else "",
            ])


        return response
