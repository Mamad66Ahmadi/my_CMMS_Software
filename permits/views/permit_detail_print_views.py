from django.db.models import Prefetch
from django.views.generic import DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

from permits.models import (
    Permit,
    PermitHazard,
    PermitPrecaution,
    PermitApproval,
    PermitWorkShift,
    PermitShiftSignoff,
    PermitTypeActiveShiftRole,
    PermitWorkflowStep,
    PermitCloseoutSignoff,
)
from permits.models.permit_base_models import Hazard, Precaution


class PermitPrintView(LoginRequiredMixin, DetailView):
    model = Permit
    template_name = "permits/permit_detail_print.html"
    context_object_name = "permit"
    slug_field = "permit_number"
    slug_url_kwarg = "permit_number"

    def get_queryset(self):
        work_shift_queryset = (
            PermitWorkShift.objects
            .select_related("created_by")
            .prefetch_related(
                Prefetch(
                    "signoffs",
                    queryset=(
                        PermitShiftSignoff.objects
                        .select_related("role", "signed_by")
                        .order_by("sequence", "id")
                    ),
                ),
            )
            .order_by("date", "shift")
        )

        active_shift_role_queryset = (
            PermitTypeActiveShiftRole.objects
            .select_related("role")
            .order_by("sequence", "id")
        )

        closeout_signoff_queryset = (
            PermitCloseoutSignoff.objects
            .select_related(
                "closeout_item",
                "closeout_item__role",
                "signed_by",
            )
            .order_by("id")
        )

        return (
            Permit.objects
            .select_related(
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
                "continuation_of",
                "permit_type",
                "workflow",
                "current_step",
            )
            .prefetch_related(
                Prefetch(
                    "hazard_assessments",
                    queryset=(
                        PermitHazard.objects
                        .filter(is_active=True)
                        .select_related("hazard")
                    ),
                    to_attr="active_hazard_assessments",
                ),
                Prefetch(
                    "precaution_requirements",
                    queryset=(
                        PermitPrecaution.objects
                        .filter(is_active=True)
                        .select_related("precaution")
                    ),
                    to_attr="active_precaution_requirements",
                ),
                Prefetch(
                    "approvals",
                    queryset=(
                        PermitApproval.objects
                        .select_related(
                            "actor",
                            "role",
                            "from_step",
                            "to_step",
                        )
                    ),
                ),
                Prefetch(
                    "work_shifts",
                    queryset=work_shift_queryset,
                    to_attr="prefetched_work_shifts",
                ),
                Prefetch(
                    "permit_type__active_shift_roles",
                    queryset=active_shift_role_queryset,
                    to_attr="prefetched_active_shift_roles",
                ),
                Prefetch(
                    "closeout_signoffs",
                    queryset=closeout_signoff_queryset,
                    to_attr="prefetched_closeout_signoffs",
                ),
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permit = self.object

        # ----------------------------------------------------------
        # Hazard / precaution master data (with audit info)
        # ----------------------------------------------------------

        all_hazards = list(Hazard.objects.order_by("display_order", "code"))
        all_precautions = list(Precaution.objects.order_by("display_order", "code"))

        hazard_map = {
            item.hazard_id: item
            for item in permit.hazard_assessments.select_related(
                "created_by",
                "modified_by",
                "removed_by",
            )
        }

        precaution_map = {
            item.precaution_id: item
            for item in permit.precaution_requirements.select_related(
                "created_by",
                "modified_by",
                "removed_by",
            )
        }

        for hazard in all_hazards:
            hazard.permit_assessment = hazard_map.get(hazard.id)

        for precaution in all_precautions:
            precaution.permit_assessment = precaution_map.get(precaution.id)

        context["all_hazards"] = all_hazards
        context["all_precautions"] = all_precautions

        # ----------------------------------------------------------
        # Validity / state (display only)
        # ----------------------------------------------------------

        context["is_currently_valid"] = permit.is_active
        context["is_active_state"] = (
            permit.current_step is not None
            and permit.current_step.state == PermitWorkflowStep.State.ACTIVE
        )

        # ----------------------------------------------------------
        # Work shifts
        # ----------------------------------------------------------

        work_shifts = getattr(permit, "prefetched_work_shifts", [])
        active_shift_roles = getattr(
            permit.permit_type,
            "prefetched_active_shift_roles",
            [],
        )

        context["work_shifts"] = work_shifts
        context["active_shift_roles"] = active_shift_roles

        for work_shift in work_shifts:
            signoffs = list(work_shift.signoffs.all())
            work_shift.completed_signoffs_count = sum(
                signoff.signed_by_id is not None for signoff in signoffs
            )
            work_shift.is_ready = not any(
                signoff.is_required and signoff.signed_by_id is None
                for signoff in signoffs
            )

        # ----------------------------------------------------------
        # Close-out signoffs
        # ----------------------------------------------------------

        context["closeout_signoffs"] = getattr(
            permit,
            "prefetched_closeout_signoffs",
            [],
        )

        return context
