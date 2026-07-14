# permits/views/permit_list_views.py

import csv
import re

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Min, Case, When, Value, IntegerField
from django.http import HttpResponse
from django.views import View
from django.views.generic import TemplateView
from django.utils import timezone
from django.utils.text import slugify

from permits.models.permit_models import Permit
from permits.models import PermitStatus
from permits.models.permit_base_models import HazardCode
from accounts.models import Department


# ---------------------------------------------- Filter ------------------------------------------
def get_filtered_permits(request):
    # Detect if the status query parameter is explicitly provided in the request
    status_param = request.GET.get("status")
    
    # If no status parameter is provided, default to ACTIVE
    if status_param is None:
        default_status = PermitStatus.ACTIVE
    else:
        default_status = status_param.strip()

    filters = {
        "q": request.GET.get("q", "").strip(),  # Unified Quick Search
        "permit_number": request.GET.get("permit_number", "").strip(),
        "status": default_status,
        "location_tag": request.GET.get("location_tag", "").strip(),
        "parent_tag": request.GET.get("parent_tag", "").strip(),
        "unit": request.GET.get("unit", "").strip(),
        "train": request.GET.get("train", "").strip(),
        "work_order": request.GET.get("work_order", "").strip(),
        "department": request.GET.get("department", "").strip(),
        "authorized_issuer": request.GET.get("authorized_issuer", "").strip(),
        "permit_holder": request.GET.get("permit_holder", "").strip(),
        "description": request.GET.get("description", "").strip(),
        "comment": request.GET.get("comment", "").strip(),
        "hazard_code": request.GET.get("hazard_code", "").strip(),
        "valid_from_date": request.GET.get("valid_from_date", "").strip(),
        "valid_to_date": request.GET.get("valid_to_date", "").strip(),
        "created_from": request.GET.get("created_from", "").strip(),
        "created_to": request.GET.get("created_to", "").strip(),
        "is_excavation": request.GET.get("is_excavation", "").strip(),
        "is_spading": request.GET.get("is_spading", "").strip(),
        "is_confined_space": request.GET.get("is_confined_space", "").strip(),
        "is_equipment_test": request.GET.get("is_equipment_test", "").strip(),
        "is_radiography": request.GET.get("is_radiography", "").strip(),
        "is_diving": request.GET.get("is_diving", "").strip(),
        "is_currently_valid": request.GET.get("is_currently_valid", "").strip(),
    }

    queryset = Permit.objects.select_related(
        "continuation_of",
        "location_tag",
        "location_tag__parent",
        "location_tag__unit",
        "work_order",
        "department",
        "authorized_issuer",
        "permit_holder",
        "created_by",
        "modified_by",
    ).prefetch_related(
        "hazard_codes",
    ).all()

    # Apply Quick Search: searches only permit numbers or work order numbers
    # If q is present, we ignore the status constraint.
    has_quick_search = bool(filters["q"])
    if has_quick_search:
        q_values = [x.strip() for x in filters["q"].split(",") if x.strip()]
        if q_values:
            quick_query = Q()
            for value in q_values:
                quick_query |= Q(permit_number__icontains=value)
                quick_query |= Q(work_order__wo_number__icontains=value)
            queryset = queryset.filter(quick_query)

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

    def apply_boolean_filter(qs, value, field_name):
        if not value or str(value).strip() == "":
            return qs

        normalized = str(value).strip().lower()
        if normalized in ["1", "true", "yes", "on"]:
            return qs.filter(**{field_name: True})
        if normalized in ["0", "false", "no", "off"]:
            return qs.filter(**{field_name: False})
        return qs

    # Standard text filters (Advanced)
    queryset = apply_multi_value_filter(queryset, filters["permit_number"], "permit_number")
    queryset = apply_multi_value_filter(queryset, filters["location_tag"], "location_tag__loc_tag")
    queryset = apply_multi_value_filter(queryset, filters["work_order"], "work_order__wo_number")
    queryset = apply_multi_value_filter(queryset, filters["authorized_issuer"], "authorized_issuer__username")
    queryset = apply_multi_value_filter(queryset, filters["permit_holder"], "permit_holder__username")
    queryset = apply_multi_value_filter(queryset, filters["description"], "description")
    queryset = apply_multi_value_filter(queryset, filters["comment"], "comment")
    queryset = apply_multi_value_filter(queryset, filters["unit"], "location_tag__unit__unit_code")
    queryset = apply_multi_value_filter(queryset, filters["train"], "location_tag__train")
    queryset = apply_multi_value_filter(queryset, filters["department"], "department__name")

    # Parent tag logic
    if filters["parent_tag"]:
        p_values = [x.strip() for x in filters["parent_tag"].split(",") if x.strip()]
        p_query = Q()
        for val in p_values:
            p_query |= (
                Q(location_tag__loc_tag__icontains=val) |
                Q(location_tag__parent__loc_tag__icontains=val)
            )
        queryset = queryset.filter(p_query)

    # Status: Skip status filtering if we are doing a Quick Search (q), 
    # otherwise apply selected or default status.
    if not has_quick_search:
        if filters["status"] == "ALL":
            pass
        elif filters["status"]:
            queryset = queryset.filter(status=filters["status"])

    # Hazard code filter
    if filters["hazard_code"]:
        values = [x.strip() for x in filters["hazard_code"].split(",") if x.strip()]
        q = Q()
        for val in values:
            q |= Q(hazard_codes__code__icontains=val)
            q |= Q(hazard_codes__name__icontains=val)
            q |= Q(hazard_codes__description__icontains=val)
        queryset = queryset.filter(q)

    # Date filters
    if filters["valid_from_date"]:
        queryset = queryset.filter(valid_from__date__gte=filters["valid_from_date"])

    if filters["valid_to_date"]:
        queryset = queryset.filter(valid_to__date__lte=filters["valid_to_date"])

    if filters["created_from"]:
        queryset = queryset.filter(created_at__date__gte=filters["created_from"])

    if filters["created_to"]:
        queryset = queryset.filter(created_at__date__lte=filters["created_to"])

    # Boolean special conditions
    queryset = apply_boolean_filter(queryset, filters["is_excavation"], "is_excavation")
    queryset = apply_boolean_filter(queryset, filters["is_spading"], "is_spading")
    queryset = apply_boolean_filter(queryset, filters["is_confined_space"], "is_confined_space")
    queryset = apply_boolean_filter(queryset, filters["is_equipment_test"], "is_equipment_test")
    queryset = apply_boolean_filter(queryset, filters["is_radiography"], "is_radiography")
    queryset = apply_boolean_filter(queryset, filters["is_diving"], "is_diving")

    # Currently valid filter (only apply if not overridden by Quick Search status bypass)
    if filters["is_currently_valid"] and not has_quick_search:
        now = timezone.now()
        normalized = str(filters["is_currently_valid"]).strip().lower()

        if normalized in ["1", "true", "yes", "on"]:
            queryset = queryset.filter(
                status=PermitStatus.ACTIVE,
                valid_from__lte=now,
                valid_to__gte=now,
            )
        elif normalized in ["0", "false", "no", "off"]:
            queryset = queryset.exclude(
                status=PermitStatus.ACTIVE,
                valid_from__lte=now,
                valid_to__gte=now,
            )

    return queryset.distinct(), filters


# ---------------------------------------------------------- List View -----------------------------------------
class PermitList(LoginRequiredMixin, TemplateView):
    template_name = "permits/permit_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        queryset, filters = get_filtered_permits(self.request)

        queryset = queryset.annotate(
            first_hazard_code=Min("hazard_codes__code"),
            special_conditions_sort=Case(
                When(is_excavation=True, then=Value(1)),
                When(is_spading=True, then=Value(2)),
                When(is_confined_space=True, then=Value(3)),
                When(is_equipment_test=True, then=Value(4)),
                When(is_radiography=True, then=Value(5)),
                When(is_diving=True, then=Value(6)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        )

        sort_by = self.request.GET.get("sort", "-created_at")

        allowed_sort = {
            "permit_number": "permit_number",
            "continuation_of": "continuation_of__permit_number",
            "location_tag": "location_tag__loc_tag",
            "status": "status",
            "hazard_code": "first_hazard_code",
            "work_order": "work_order__wo_number",
            "description": "description",
            "department": "department__name",
            "unit": "location_tag__unit__unit_code",
            "valid_from": "valid_from",
            "valid_to": "valid_to",
            "special_conditions": "special_conditions_sort",
            "is_excavation": "is_excavation",
            "is_spading": "is_spading",
            "is_confined_space": "is_confined_space",
            "is_equipment_test": "is_equipment_test",
            "is_radiography": "is_radiography",
            "is_diving": "is_diving",
            "authorized_issuer": "authorized_issuer__username",
            "permit_holder": "permit_holder__username",
            "created_at": "created_at",
            "created_by": "created_by__username",
            "modified_at": "modified_at",
            "modified_by": "modified_by__username",
        }

        sort_key = sort_by.lstrip("-")
        sort_field = allowed_sort.get(sort_key, "created_at")

        if sort_by.startswith("-"):
            queryset = queryset.order_by(f"-{sort_field}", "-id")
        else:
            queryset = queryset.order_by(sort_field, "-id")

        try:
            per_page = int(self.request.GET.get("per_page", 25))
        except ValueError:
            per_page = 25

        if per_page not in [10, 25, 50, 100]:
            per_page = 25

        paginator = Paginator(queryset.distinct(), per_page)
        page_obj = paginator.get_page(self.request.GET.get("page"))

        # Determine if any advanced filters are active to keep panel expanded
        # Excluding both 'q' and 'status' so status defaulting to ACTIVE doesn't force expand the panel.
        has_advanced_filters = any(
            filters[k] for k in filters if k not in ["q", "status"]
        )

        query_dict = self.request.GET.copy()
        query_dict.pop("sort", None)
        query_dict.pop("page", None)

        context.update({
            "permits": page_obj,
            "filters": filters,
            "sort_by": sort_by,
            "per_page": per_page,
            "query_params": query_dict.urlencode(),
            "status_choices": PermitStatus.choices,
            "hazard_codes": HazardCode.objects.filter(is_active=True).order_by("code"),
            "departments": Department.objects.filter(is_active=True).order_by("name"),
            "has_advanced_filters": has_advanced_filters,
        })

        return context


# ------------------------ CSV Export ------------------------------------------
class PermitExportCSV(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        queryset, filters = get_filtered_permits(request)
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
            # Mirror the default filename logic if status is defaulted to ACTIVE
            if filters.get("status") == PermitStatus.ACTIVE and not request.GET.get("q"):
                filename = "permits_status-active.csv"
            else:
                filename = "permits_all.csv"

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        response.write("\ufeff")
        writer = csv.writer(response)

        writer.writerow([
            "ID", "Permit Number", "Continuation Of ID", "Continuation Of Permit Number",
            "Hazard Codes", "Location Tag ID", "Location Tag", "Description",
            "Work Order ID", "Work Order Number", "Department ID", "Department",
            "Authorized Issuer ID", "Authorized Issuer Username", "Permit Holder ID",
            "Permit Holder Username", "Valid From", "Valid To", "Is Excavation",
            "Is Spading", "Is Confined Space", "Is Equipment Test", "Is Radiography",
            "Is Diving", "Status", "Status Display", "Comment", "Created At",
            "Created By ID", "Created By Username", "Modified At", "Modified By ID",
            "Modified By Username", "Is Currently Valid", "Special Conditions Summary"
        ])

        for permit in queryset:
            hazard_codes = ", ".join(
                permit.hazard_codes.all().values_list("code", flat=True)
            )

            writer.writerow([
                permit.pk,
                permit.permit_number or "",
                permit.continuation_of.pk if permit.continuation_of else "",
                permit.continuation_of.permit_number if permit.continuation_of else "",
                hazard_codes,
                permit.location_tag.pk if permit.location_tag else "",
                permit.location_tag.loc_tag if permit.location_tag else "",
                permit.description or "",
                permit.work_order.pk if permit.work_order else "",
                permit.work_order.wo_number if permit.work_order else "",
                permit.department.pk if permit.department else "",
                permit.department.name if permit.department else "",
                permit.authorized_issuer.pk if permit.authorized_issuer else "",
                permit.authorized_issuer.username if permit.authorized_issuer else "",
                permit.permit_holder.pk if permit.permit_holder else "",
                permit.permit_holder.username if permit.permit_holder else "",
                permit.valid_from.strftime("%Y-%m-%d %H:%M:%S") if permit.valid_from else "",
                permit.valid_to.strftime("%Y-%m-%d %H:%M:%S") if permit.valid_to else "",
                permit.is_excavation,
                permit.is_spading,
                permit.is_confined_space,
                permit.is_equipment_test,
                permit.is_radiography,
                permit.is_diving,
                permit.status or "",
                permit.get_status_display() if permit.status else "",
                permit.comment or "",
                permit.created_at.strftime("%Y-%m-%d %H:%M:%S") if permit.created_at else "",
                permit.created_by.pk if permit.created_by else "",
                permit.created_by.username if permit.created_by else "",
                permit.modified_at.strftime("%Y-%m-%d %H:%M:%S") if permit.modified_at else "",
                permit.modified_by.pk if permit.modified_by else "",
                permit.modified_by.username if permit.modified_by else "",
                permit.is_currently_valid,
                permit.special_conditions_summary,
            ])

        return response
