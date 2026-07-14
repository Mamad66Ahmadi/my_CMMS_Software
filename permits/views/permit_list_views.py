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
    status_param = request.GET.get("status")

    # Default to ACTIVE only when status is not provided at all.
    if status_param is None:
        default_status = PermitStatus.ACTIVE
    else:
        default_status = status_param.strip()

    filters = {
        "q": request.GET.get("q", "").strip(),
        "permit_number": request.GET.get("permit_number", "").strip(),
        "continuation_of": request.GET.get("continuation_of", "").strip(),
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
        "modified_from": request.GET.get("modified_from", "").strip(),
        "modified_to": request.GET.get("modified_to", "").strip(),
        "created_by": request.GET.get("created_by", "").strip(),
        "modified_by": request.GET.get("modified_by", "").strip(),
        "is_excavation": request.GET.get("is_excavation", "").strip(),
        "is_spading": request.GET.get("is_spading", "").strip(),
        "is_confined_space": request.GET.get("is_confined_space", "").strip(),
        "is_equipment_test": request.GET.get("is_equipment_test", "").strip(),
        "is_radiography": request.GET.get("is_radiography", "").strip(),
        "is_diving": request.GET.get("is_diving", "").strip(),
        "is_currently_valid": request.GET.get("is_currently_valid", "").strip(),
    }

    queryset = (
        Permit.objects.select_related(
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
        )
        .prefetch_related("hazard_codes")
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

    def apply_boolean_filter(qs, value, field_name):
        if not value or str(value).strip() == "":
            return qs

        normalized = str(value).strip().lower()
        if normalized in ["1", "true", "yes", "on"]:
            return qs.filter(**{field_name: True})
        if normalized in ["0", "false", "no", "off"]:
            return qs.filter(**{field_name: False})
        return qs

    # Quick Search: comma-separated values, searching both permit and work order numbers.
    # Quick search bypasses the status filter only.
    has_quick_search = bool(filters["q"])
    if has_quick_search:
        q_values = split_csv(filters["q"])
        if q_values:
            quick_query = Q()
            for value in q_values:
                quick_query |= Q(permit_number__icontains=value)
                quick_query |= Q(work_order__wo_number__icontains=value)
            queryset = queryset.filter(quick_query)

    # Text / related-object filters
    queryset = apply_multi_value_filter(queryset, filters["permit_number"], "permit_number")
    queryset = apply_multi_value_filter(queryset, filters["continuation_of"], "continuation_of__permit_number")
    queryset = apply_multi_value_filter(queryset, filters["location_tag"], "location_tag__loc_tag")
    queryset = apply_multi_value_filter(queryset, filters["work_order"], "work_order__wo_number")
    queryset = apply_multi_value_filter(queryset, filters["department"], "department__name")
    queryset = apply_multi_value_filter(queryset, filters["authorized_issuer"], "authorized_issuer__username")
    queryset = apply_multi_value_filter(queryset, filters["permit_holder"], "permit_holder__username")
    queryset = apply_multi_value_filter(queryset, filters["created_by"], "created_by__username")
    queryset = apply_multi_value_filter(queryset, filters["modified_by"], "modified_by__username")
    queryset = apply_multi_value_filter(queryset, filters["description"], "description")
    queryset = apply_multi_value_filter(queryset, filters["comment"], "comment")
    queryset = apply_multi_value_filter(queryset, filters["unit"], "location_tag__unit__unit_code")
    queryset = apply_multi_value_filter(queryset, filters["train"], "location_tag__train")

    # Parent tag filter: match either the direct location tag or its parent.
    if filters["parent_tag"]:
        parent_values = split_csv(filters["parent_tag"])
        parent_query = Q()
        for val in parent_values:
            parent_query |= (
                Q(location_tag__loc_tag__icontains=val) |
                Q(location_tag__parent__loc_tag__icontains=val)
            )
        queryset = queryset.filter(parent_query)

    # Status: skip when quick search is used.
    if not has_quick_search:
        if filters["status"] and filters["status"] != "ALL":
            queryset = queryset.filter(status=filters["status"])

    # Hazard codes
    if filters["hazard_code"]:
        hazard_values = split_csv(filters["hazard_code"])
        hazard_query = Q()
        for val in hazard_values:
            hazard_query |= Q(hazard_codes__code__icontains=val)
            hazard_query |= Q(hazard_codes__name__icontains=val)
            hazard_query |= Q(hazard_codes__description__icontains=val)
        queryset = queryset.filter(hazard_query)

    # Validity date filters
    if filters["valid_from_date"]:
        queryset = queryset.filter(valid_from__date__gte=filters["valid_from_date"])

    if filters["valid_to_date"]:
        queryset = queryset.filter(valid_to__date__lte=filters["valid_to_date"])

    # Audit date filters
    if filters["created_from"]:
        queryset = queryset.filter(created_at__date__gte=filters["created_from"])

    if filters["created_to"]:
        queryset = queryset.filter(created_at__date__lte=filters["created_to"])

    if filters["modified_from"]:
        queryset = queryset.filter(modified_at__date__gte=filters["modified_from"])

    if filters["modified_to"]:
        queryset = queryset.filter(modified_at__date__lte=filters["modified_to"])

    # Boolean model fields
    queryset = apply_boolean_filter(queryset, filters["is_excavation"], "is_excavation")
    queryset = apply_boolean_filter(queryset, filters["is_spading"], "is_spading")
    queryset = apply_boolean_filter(queryset, filters["is_confined_space"], "is_confined_space")
    queryset = apply_boolean_filter(queryset, filters["is_equipment_test"], "is_equipment_test")
    queryset = apply_boolean_filter(queryset, filters["is_radiography"], "is_radiography")
    queryset = apply_boolean_filter(queryset, filters["is_diving"], "is_diving")

    # Computed validity filter
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

        # Determine if any advanced filters are active to keep panel expanded.
        # Determine if any advanced filters are active to keep panel expanded.
        has_advanced_filters = any(filters[k] for k in filters if k not in ["q", "status"])

        query_dict = self.request.GET.copy()
        query_dict.pop("sort", None)
        query_dict.pop("page", None)

        def build_remove_url(key_to_remove):
            params = self.request.GET.copy()
            params.pop(key_to_remove, None)
            params.pop("page", None)
            return f"?{params.urlencode()}" if params.urlencode() else "?"

        status_labels = dict(PermitStatus.choices)
        active_filter_badges = []

        # 1. Text / choice filters
        badge_labels = {
            "permit_number": "Permit No.",
            "continuation_of": "Continuation Of",
            "location_tag": "Location Tag",
            "parent_tag": "Parent Tag",
            "unit": "Unit",
            "train": "Train",
            "work_order": "Work Order",
            "department": "Department",
            "authorized_issuer": "Authorized Issuer",
            "permit_holder": "Permit Holder",
            "description": "Description",
            "comment": "Comment",
            "hazard_code": "Hazard Code",
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
                active_filter_badges.append({
                    "key": key,
                    "label": label,
                    "value": value,
                    "remove_url": build_remove_url(key),
                })

        # 2. Status Badge
        if "status" in self.request.GET and filters.get("status") and filters["status"] != "ALL":
            status_value = filters["status"]
            active_filter_badges.append({
                "key": "status",
                "label": "Status",
                "value": status_labels.get(status_value, status_value),
                "remove_url": build_remove_url("status"),
            })

        # 3. Boolean filters
        bool_labels = {
            "is_excavation": "Excavation",
            "is_spading": "Spading",
            "is_confined_space": "Confined Space",
            "is_equipment_test": "Equipment Test",
            "is_radiography": "Radiography",
            "is_diving": "Diving",
            "is_currently_valid": "Currently Valid",
        }

        for key, label in bool_labels.items():
            value = filters.get(key)
            if value:
                normalized = str(value).strip().lower()
                display_value = "True" if normalized in ["1", "true", "yes", "on"] else "False"
                active_filter_badges.append({
                    "key": key,
                    "label": label,
                    "value": display_value,
                    "remove_url": build_remove_url(key),
                })

        # --- QUICK SEARCH CHECK ---
        # If the user used the 'q' (Quick Search) parameter, we suppress the filter badges.
        # This keeps the UI clean when searching for specific permit numbers.
        if filters.get("q"):
            active_filter_badges = []

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
            "active_filter_badges": active_filter_badges,
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
