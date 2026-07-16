# permits/views/qualification_views.py

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, ListView

from accounts.models import Qualification, UserQualification
from permits.forms import AddPISQualificationForm

# ------------------ Filters -------------------------------
def get_filtered_pis_qualifications(request):
    filters = {
        "q": request.GET.get("q", "").strip(),
        "department": request.GET.get("department", "").strip(),
        "granted_date_from": request.GET.get("granted_date_from", "").strip(),
        "granted_date_to": request.GET.get("granted_date_to", "").strip(),
        "expiry_date_from": request.GET.get("expiry_date_from", "").strip(),
        "expiry_date_to": request.GET.get("expiry_date_to", "").strip(),
        "granted_by": request.GET.get("granted_by", "").strip(),
        "is_active": request.GET.get("is_active", "true").strip(),
    }

    sort_by = request.GET.get("sort", "").strip() or "user__personnel_number"

    allowed_sort_fields = {
        "user__personnel_number": "user__personnel_number",
        "user__first_name": "user__first_name",
        "user__department__name": "user__department__name",
        "user__is_active": "user__is_active",
        "qualification__code": "qualification__code",
        "granted_date": "granted_date",
        "expiry_date": "expiry_date",
        "granted_by__personnel_number": "granted_by__personnel_number",
        "note": "note",
    }

    queryset = UserQualification.objects.filter(
        qualification__is_active=True,
        qualification__code__iexact="PIS",
    ).select_related(
        "user",
        "user__department",
        "qualification",
        "granted_by",
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
        if value == "":
            return qs

        normalized = str(value).strip().lower()
        if normalized in ["1", "true", "yes", "on"]:
            return qs.filter(**{field_name: True})
        if normalized in ["0", "false", "no", "off"]:
            return qs.filter(**{field_name: False})
        return qs

    # Quick search should return all matching users, regardless of active/inactive status.
    if filters["q"]:
        q_values = split_csv(filters["q"])
        if q_values:
            quick_query = Q()
            for value in q_values:
                quick_query |= Q(user__personnel_number__icontains=value)
            queryset = queryset.filter(quick_query)
    else:
        queryset = apply_boolean_filter(queryset, filters["is_active"], "user__is_active")

    queryset = apply_multi_value_filter(queryset, filters["department"], "user__department__name")
    queryset = apply_multi_value_filter(queryset, filters["granted_by"], "granted_by__personnel_number")

    if filters["granted_date_from"]:
        queryset = queryset.filter(granted_date__gte=filters["granted_date_from"])

    if filters["granted_date_to"]:
        queryset = queryset.filter(granted_date__lte=filters["granted_date_to"])

    if filters["expiry_date_from"]:
        queryset = queryset.filter(expiry_date__gte=filters["expiry_date_from"])

    if filters["expiry_date_to"]:
        queryset = queryset.filter(expiry_date__lte=filters["expiry_date_to"])

    descending = sort_by.startswith("-")
    sort_key = sort_by[1:] if descending else sort_by
    sort_field = allowed_sort_fields.get(sort_key, "user__personnel_number")
    final_sort = f"-{sort_field}" if descending else sort_field

    queryset = queryset.order_by(final_sort, "user__username")

    return queryset.distinct(), filters, sort_by



# ------------------------------ PIS List -------------------------------
class PISQualificationListView(LoginRequiredMixin, ListView):
    model = UserQualification
    template_name = "permits/pis_qualification_list.html"
    context_object_name = "pis_qualifications"
    paginate_by = 25

    def get_queryset(self):
        queryset, self.filters, self.sort_by = get_filtered_pis_qualifications(self.request)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        filters = getattr(self, "filters", {})
        context["filters"] = filters
        context["sort_by"] = getattr(self, "sort_by", "user__personnel_number")

        advanced_keys = [
            "department",
            "granted_date_from",
            "granted_date_to",
            "expiry_date_from",
            "expiry_date_to",
            "granted_by",
        ]

        has_text_or_date_filters = any(filters.get(k) for k in advanced_keys if filters.get(k))
        has_non_default_status = filters.get("is_active") not in ["true", None]
        context["has_advanced_filters"] = has_text_or_date_filters or has_non_default_status

        querydict = self.request.GET.copy()
        querydict.pop("page", None)
        querydict.pop("sort", None)
        context["query_params"] = querydict.urlencode()

        user = self.request.user

        is_permit_office = (
            user.department
            and user.department.name
            and user.department.name.strip().lower() == "permit office"
        )

        is_supervisor = (
            getattr(user, "role", "")
            and str(user.role).strip().lower() == "supervisor"
        )

        context["can_add_pis"] = (
            user.is_active
            and (
                user.is_staff
                or (is_permit_office and is_supervisor)
            )
        )

        return context

# ------------------- Add PIS Qualification ---------------------------
class AddPISQualificationView(LoginRequiredMixin, CreateView):
    model = UserQualification
    form_class = AddPISQualificationForm
    template_name = "permits/pis_qualification_form.html"

    def dispatch(self, request, *args, **kwargs):
        user = request.user

        is_permit_office = (
            getattr(user, "department", None)
            and user.department.name
            and user.department.name.strip().lower() == "permit office"
        )

        is_supervisor = str(getattr(user, "role", "")).strip().lower() == "supervisor"

        can_grant_pis = (
            user.is_active
            and (
                user.is_staff
                or (is_permit_office and is_supervisor)
            )
        )

        if not can_grant_pis:
            messages.error(request, "You do not have permission to grant PIS qualifications.")
            raise PermissionDenied(
                "Only active staff or active Permit Office supervisors can grant PIS qualifications."
            )

        return super().dispatch(request, *args, **kwargs)


    def form_valid(self, form):
        form.instance.qualification = get_object_or_404(
            Qualification,
            code__iexact="PIS",
            is_active=True,
        )
        # Sets the granting authority to the logged-in user who passed the dispatch check
        form.instance.granted_by = self.request.user

        response = super().form_valid(form)

        user_name = form.instance.user.get_full_name() or form.instance.user.username

        if self.request.POST.get("save_and_add_another"):
            messages.success(
                self.request,
                f"PIS qualification successfully added for {user_name}. You can add another.",
            )
        else:
            messages.success(
                self.request,
                f"PIS qualification successfully added for {user_name}.",
            )

        return response

    def get_success_url(self):
        if self.request.POST.get("save_and_add_another"):
            next_url = self.request.GET.get("next")
            url = self.request.path
            if next_url:
                return f"{url}?next={next_url}"
            return url

        next_url = self.request.GET.get("next")
        if next_url:
            return next_url
        return reverse("permits:pis_holders")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["back_url"] = self.request.GET.get("next") or reverse("permits:pis_holders")
        return context
