from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.utils import timezone
from django.views.generic import DetailView, TemplateView

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
        per_page = 25
        shift_1_work_shifts = Paginator(
            qs.filter(shift=Shift.SHIFT_1),
            per_page,
        ).get_page(self.request.GET.get("shift_1_page"))
        shift_2_work_shifts = Paginator(
            qs.filter(shift=Shift.SHIFT_2),
            per_page,
        ).get_page(self.request.GET.get("shift_2_page"))

        active_tab = self.request.GET.get("tab", "").strip()
        if active_tab not in {"shift-1", "shift-2"}:
            selected_shifts = [value for value in self.request.GET.getlist("shift") if value]
            if self.request.GET.get("shift_2_page") or selected_shifts == [Shift.SHIFT_2]:
                active_tab = "shift-2"
            else:
                active_tab = "shift-1"

        context.update(
            {
                "shift_1_work_shifts": shift_1_work_shifts,
                "shift_2_work_shifts": shift_2_work_shifts,
                "active_work_shift_tab": active_tab,
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
            }
        )
        query = self.request.GET.copy()
        query.pop("page", None)
        query.pop("shift_1_page", None)
        query.pop("shift_2_page", None)
        for tab_name, context_prefix in (("shift-1", "shift_1"), ("shift-2", "shift_2")):
            pagination_query = self.request.GET.copy()
            pagination_query.pop(f"{context_prefix}_page", None)
            pagination_query.pop("page", None)
            pagination_query["tab"] = tab_name
            context[f"{context_prefix}_query_params"] = pagination_query.urlencode()

            header_query = self.request.GET.copy()
            header_query.pop("shift_1_page", None)
            header_query.pop("shift_2_page", None)
            header_query.pop("page", None)
            header_query.pop("sort", None)
            header_query["tab"] = tab_name
            context[f"{context_prefix}_header_query_params"] = header_query.urlencode()

        context["shift_tabs"] = [
            {
                "name": "shift-1",
                "panel_id": "work-shift-panel-1",
                "tab_id": "work-shift-tab-1",
                "label": "Shift 1",
                "icon": "bi-sun",
                "window": "07:00–19:00",
                "pagination_label": "Shift 1 pagination",
                "count": shift_counts[Shift.SHIFT_1],
                "page_obj": shift_1_work_shifts,
                "page_param": "shift_1_page",
                "query_params": context["shift_1_query_params"],
                "header_query_params": context["shift_1_header_query_params"],
            },
            {
                "name": "shift-2",
                "panel_id": "work-shift-panel-2",
                "tab_id": "work-shift-tab-2",
                "label": "Shift 2",
                "icon": "bi-moon-stars",
                "window": "19:00–07:00 the following day",
                "pagination_label": "Shift 2 pagination",
                "count": shift_counts[Shift.SHIFT_2],
                "page_obj": shift_2_work_shifts,
                "page_param": "shift_2_page",
                "query_params": context["shift_2_query_params"],
                "header_query_params": context["shift_2_header_query_params"],
            },
        ]

        def date_url(target_date):
            date_query = query.copy()
            date_query["date"] = target_date.isoformat()
            encoded_query = date_query.urlencode()
            return f"?{encoded_query}" if encoded_query else "?"

        context["previous_url"] = date_url(context["previous_date"])
        context["today_url"] = date_url(timezone.localdate())
        context["next_url"] = date_url(context["next_date"])
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
