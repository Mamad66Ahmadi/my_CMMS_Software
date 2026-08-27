from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import DetailView, TemplateView
from urllib.parse import urlencode

from permits.models.permit_shift_models import PermitWorkShift, Shift
from accounts.models import Department
from permits.models.workflow_models import PermitWorkflowStep
from permits.services.work_shift_service import PermitWorkShiftService


class WorkShiftListView(LoginRequiredMixin, TemplateView):
    template_name = "permits/work_shift_list.html"
    sort_fields = {
        "date": "date",
        "shift": "shift",
        "permit_number": "permit__permit_number",
        "permit_type": "permit__permit_type__name",
        "department": "permit__department__name",
        "location": "permit__location_tag__loc_tag",
        "unit": "permit__location_tag__unit__unit_code",
        "train": "permit__location_tag__train",
        "work_order": "permit__work_order__wo_number",
        "scope_of_work": "permit__scope_of_work",
        "work_leader": "work_leader",
        "worker_count": "worker_count",
        "status": "status",
        "required_signoffs": "required_signoffs",
        "signed_signoffs": "signed_signoffs",
    }

    def get_queryset(self):
        qs = (
            PermitWorkShift.objects
            .select_related(
                "permit",
                "permit__permit_type",
                "permit__current_step",
                "permit__department",
                "permit__location_tag",
                "permit__location_tag__unit",
                "permit__work_order",
            )
            .prefetch_related(
                "signoffs__role",
                "signoffs__signed_by",
            )
            .annotate(
                required_signoffs=Count(
                    "signoffs",
                    filter=Q(signoffs__is_required=True),
                    distinct=True,
                ),
                signed_signoffs=Count(
                    "signoffs",
                    filter=Q(
                        signoffs__is_required=True,
                        signoffs__signed_by__isnull=False,
                    ),
                    distinct=True,
                ),
            )
        )

        params = self.request.GET
        selected_date = params.get("date", "").strip()
        if selected_date:
            try:
                qs = qs.filter(date=date.fromisoformat(selected_date))
            except ValueError:
                qs = qs.filter(date=timezone.localdate())
        else:
            qs = qs.filter(date=timezone.localdate())

        if params.get("shift", "").strip():
            qs = qs.filter(shift__in=[v for v in params.getlist("shift") if v])
        if params.get("status", "").strip():
            qs = qs.filter(status__in=[v for v in params.getlist("status") if v])
        if params.get("permit_number", "").strip():
            qs = qs.filter(permit__permit_number__icontains=params["permit_number"].strip())
        if params.get("permit_type", "").strip():
            qs = qs.filter(permit__permit_type__name__icontains=params["permit_type"].strip())
        for param, lookup in (
            ("department", "permit__department__name"),
            ("location", "permit__location_tag__loc_tag"),
            ("unit", "permit__location_tag__unit__unit_code"),
            ("train", "permit__location_tag__train"),
        ):
            values = [value.strip() for value in params.get(param, "").split(",") if value.strip()]
            if values:
                query = Q()
                for value in values:
                    query |= Q(**{f"{lookup}__icontains": value})
                qs = qs.filter(query)
        if params.get("work_order", "").strip():
            qs = qs.filter(permit__work_order__wo_number__icontains=params["work_order"].strip())
        if params.get("scope_of_work", "").strip():
            qs = qs.filter(permit__scope_of_work__icontains=params["scope_of_work"].strip())
        if params.get("work_leader", "").strip():
            qs = qs.filter(work_leader__icontains=params["work_leader"].strip())

        sort = self.request.GET.get("sort", "-date").strip()
        descending = sort.startswith("-")
        key = sort.lstrip("-")
        sort_field = self.sort_fields.get(key, "date")
        if descending:
            sort_field = f"-{sort_field}"
        return qs.order_by(sort_field, "shift", "permit__permit_number", "id")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        qs = self.get_queryset()
        selected_date = self.request.GET.get("date", "").strip()
        try:
            selected_date = date.fromisoformat(selected_date) if selected_date else timezone.localdate()
        except ValueError:
            selected_date = timezone.localdate()

        per_page = 25
        page_obj = Paginator(qs, per_page).get_page(self.request.GET.get("page"))
        summary_qs = PermitWorkShift.objects.filter(pk__in=qs.values("pk"))
        summary = summary_qs.aggregate(
            total=Count("id"),
            open=Count("id", filter=Q(status=PermitWorkShift.Status.OPEN)),
            closed=Count("id", filter=Q(status=PermitWorkShift.Status.CLOSED)),
            workers=Sum("worker_count"),
        )
        shift_counts = {
            value: summary_qs.filter(shift=value).count() for value, _ in Shift.choices
        }
        context.update(
            {
                "work_shifts": page_obj,
                "selected_date": selected_date,
                "summary": summary,
                "shift_choices": Shift.choices,
                "status_choices": PermitWorkShift.Status.choices,
                "departments": Department.objects.filter(is_active=True).order_by("name"),
                "filters": self.request.GET,
                "has_filters": any(
                    self.request.GET.get(key, "").strip()
                    for key in (
                        "date",
                        "shift",
                        "status",
                        "permit_number",
                        "permit_type",
                        "department",
                        "location",
                        "work_leader",
                    )
                ),
                "sort_by": self.request.GET.get("sort", "-date").strip() or "-date",
                "previous_date": selected_date - timedelta(days=1),
                "next_date": selected_date + timedelta(days=1),
                "shift_counts": shift_counts,
                "shift_count_rows": [
                    {"value": value, "label": label, "count": shift_counts[value]}
                    for value, label in Shift.choices
                ],
            }
        )
        query = self.request.GET.copy()
        query.pop("page", None)
        context["query_params"] = query.urlencode()
        header_query = self.request.GET.copy()
        header_query.pop("page", None)
        header_query.pop("sort", None)
        context["header_query_params"] = header_query.urlencode()
        context["previous_url"] = f"?{urlencode({**query.dict(), 'date': context['previous_date'].isoformat()})}"
        context["today_url"] = f"?{urlencode({**query.dict(), 'date': timezone.localdate().isoformat()})}"
        context["next_url"] = f"?{urlencode({**query.dict(), 'date': context['next_date'].isoformat()})}"
        return context


class WorkShiftDetailView(LoginRequiredMixin, DetailView):
    model = PermitWorkShift
    context_object_name = "work_shift"
    template_name = "permits/work_shift_detail.html"

    def get_queryset(self):
        return (
            PermitWorkShift.objects
            .select_related(
                "permit",
                "permit__permit_type",
                "permit__department",
                "permit__location_tag",
                "created_by",
                "closed_by",
            )
            .prefetch_related("signoffs__role", "signoffs__signed_by")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        signoffs = list(self.object.signoffs.all())
        permit = self.object.permit
        is_active_state = (
            permit.current_step is not None
            and permit.current_step.state == PermitWorkflowStep.State.ACTIVE
        )
        can_manage = (
            is_active_state
            and PermitWorkShiftService.can_manage_work_shifts(
                actor=self.request.user,
                permit=permit,
            )
        )
        for signoff in signoffs:
            signoff.can_sign = (
                is_active_state
                and self.object.status == PermitWorkShift.Status.OPEN
                and not signoff.signed_by_id
                and PermitWorkShiftService.can_sign_work_shift(
                    actor=self.request.user,
                    permit=permit,
                    role=signoff.role,
                )
            )
        context["signoffs"] = signoffs
        context["required_signoffs"] = [s for s in signoffs if s.is_required]
        context["signed_signoffs"] = [s for s in signoffs if s.is_required and s.signed_by_id]
        context["is_active_state"] = is_active_state
        context["can_manage_work_shifts"] = can_manage
        return context
