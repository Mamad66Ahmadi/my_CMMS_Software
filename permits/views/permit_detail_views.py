# permits/views/permit_detail_views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView

from equipment.models import LocationTag

from permits.forms import (
    PermitCreateForm,
    PermitFireGasESDSignoffForm,
    PermitShiftSignoffForm,
    PermitUpdateForm,
    PermitWorkShiftForm,
    PermitWorkflowDecisionForm,
)

from permits.models import (
    Permit,
    PermitHazard,
    PermitPrecaution,
    PermitWorkflowTransition,
    PermitApproval,
)

from permits.models.workflow_models import PermitWorkflowStep

from permits.models import (
    Hazard,
    Precaution,
)

from permits.models.permit_fg_esd_models import FireGasESD, PermitFireGasESD

from permits.models.permit_shift_models import (
    PermitShiftSignoff,
    PermitTypeActiveShiftRole,
    PermitWorkShift,
)

from permits.models.permit_closeout_models import (
    PermitCloseoutSignoff,
)

from permits.services.authorization_service import (
    WorkflowAuthorizationService,
)

from permits.services.condition_service import (
    WorkflowConditionEvaluator,
)

from permits.services.workflow_service import (
    PermitWorkflowService,
    WorkflowTransitionError,
)

from permits.services.work_shift_service import (
    PermitWorkShiftService,
)

from permits.services.closeout_service import (
    PermitCloseoutService
)

from permits.services.fire_gas_esd_service import (
    PermitFireGasESDService,
)


def _render_detail_fragment(request, permit_number, template_name, extra_context=None):
    """Build the normal Permit Detail context and render one panel for HTMX."""
    detail_view = PermitDetailView()
    detail_view.request = request
    detail_view.kwargs = {"permit_number": permit_number}
    detail_view.object = detail_view.get_object()
    context = detail_view.get_context_data(object=detail_view.object)
    if extra_context:
        context.update(extra_context)
    return render(request, template_name, context)

# =============================================================================
# Permit Detail View
# =============================================================================

class PermitDetailView(LoginRequiredMixin, DetailView):
    model = Permit
    template_name = "permits/permit_detail.html"
    context_object_name = "permit"
    slug_field = "permit_number"
    slug_url_kwarg = "permit_number"

    def get_queryset(self):

        # ----------------------------------------------------------
        # Work shifts
        # ----------------------------------------------------------

        work_shift_queryset = (
            PermitWorkShift.objects
            .select_related(
                "created_by",
            )
            .prefetch_related(
                Prefetch(
                    "signoffs",
                    queryset=(
                        PermitShiftSignoff.objects
                        .select_related(
                            "role",
                            "signed_by",
                        )
                        .order_by("sequence", "id")
                    ),
                ),
            )
            .order_by("date", "shift")
        )

        # ----------------------------------------------------------
        # Active shift roles
        # ----------------------------------------------------------

        active_shift_role_queryset = (
            PermitTypeActiveShiftRole.objects
            .select_related("role")
            .order_by("sequence", "id")
        )

        # ----------------------------------------------------------
        # Permit close-out signoffs
        # ----------------------------------------------------------

        closeout_signoff_queryset = (
            PermitCloseoutSignoff.objects
            .select_related(
                "closeout_item",
                "closeout_item__role",
                "signed_by",
                "created_by",
            )
            .order_by(
                "closeout_item__display_order",
                "closeout_item__code",
                "pk",
            )
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
                "current_step__editable_role",
                "current_step__editable_role__required_qualification",
            )
            .prefetch_related(

                # ------------------------------------------------------
                # Hazards
                # ------------------------------------------------------

                Prefetch(
                    "hazard_assessments",
                    queryset=(
                        PermitHazard.objects
                        .filter(is_active=True)
                        .select_related("hazard")
                    ),
                    to_attr="active_hazard_assessments",
                ),

                # ------------------------------------------------------
                # Precautions
                # ------------------------------------------------------

                Prefetch(
                    "precaution_requirements",
                    queryset=(
                        PermitPrecaution.objects
                        .filter(is_active=True)
                        .select_related("precaution")
                    ),
                    to_attr="active_precaution_requirements",
                ),

                # ------------------------------------------------------
                # Fire, Gas & ESD Isolations
                # ------------------------------------------------------

                Prefetch(
                    "permit_fire_gas_esd_items",
                    queryset=(
                        PermitFireGasESD.objects
                        .select_related(
                            "fire_gas_esd",
                            "fire_gas_esd__role",
                            "isolated_confirmed_by",
                            "deisolated_confirmed_by",
                        )
                    ),
                    to_attr="prefetched_fire_gas_esd_items",
                ),

                # ------------------------------------------------------
                # Continuations
                # ------------------------------------------------------

                "continuations",

                # ------------------------------------------------------
                # Workflow approvals
                # ------------------------------------------------------

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

                # ------------------------------------------------------
                # Work shifts
                # ------------------------------------------------------

                Prefetch(
                    "work_shifts",
                    queryset=work_shift_queryset,
                    to_attr="prefetched_work_shifts",
                ),

                # ------------------------------------------------------
                # Active work-shift roles
                # ------------------------------------------------------

                Prefetch(
                    "permit_type__active_shift_roles",
                    queryset=active_shift_role_queryset,
                    to_attr="prefetched_active_shift_roles",
                ),

                # ------------------------------------------------------
                # Permit close-out checklist
                # ------------------------------------------------------

                Prefetch(
                    "closeout_signoffs",
                    queryset=closeout_signoff_queryset,
                    to_attr="prefetched_closeout_signoffs",
                ),
            )
        )

    # =========================================================================
    # Workflow Actions
    # =========================================================================

    def get_available_workflow_actions(self, permit):
        """
        Return workflow transitions that the current user is authorized
        to perform.

        This is display-only.
        The POST endpoint validates everything again.
        """

        if not permit.workflow_id or not permit.current_step_id:
            return []

        if permit.current_step.is_terminal:
            return []

        transitions = (
            PermitWorkflowTransition.objects
            .select_related(
                "workflow",
                "from_step",
                "to_step",
                "role",
                "role__required_qualification",
            )
            .prefetch_related("conditions")
            .filter(
                workflow_id=permit.workflow_id,
                from_step_id=permit.current_step_id,
            )
            .order_by(
                "role__name",
                "decision",
                "to_step__step_number",
            )
        )

        available_actions = []

        for transition in transitions:
            try:
                WorkflowAuthorizationService.ensure_actor_can_decide(
                    actor=self.request.user,
                    permit=permit,
                    transition=transition,
                )

                WorkflowConditionEvaluator.ensure_transition_allowed(
                    permit=permit,
                    transition=transition,
                )

            except (PermissionDenied, ValidationError):
                continue

            available_actions.append(
                {
                    "transition": transition,
                    "role": transition.role,
                    "role_code": transition.role.code,
                    "decision": transition.decision,
                    "decision_label": transition.get_decision_display(),
                    "to_step": transition.to_step,
                    "form": PermitWorkflowDecisionForm(
                        initial={
                            "role_code": transition.role.code,
                            "decision": transition.decision,
                        }
                    ),
                }
            )

        return available_actions

    # =========================================================================
    # Context
    # =========================================================================

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permit = self.object

        # ----------------------------------------------------------
        # Hazard / precaution master data
        # ----------------------------------------------------------

        all_hazards = list(
            Hazard.objects.order_by("display_order", "code")
        )

        all_precautions = list(
            Precaution.objects.order_by("display_order", "code")
        )

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
            precaution.permit_assessment = precaution_map.get(
                precaution.id
            )

        context["all_hazards"] = all_hazards
        context["all_precautions"] = all_precautions

        # ----------------------------------------------------------
        # Fire, Gas & ESD isolations
        # ----------------------------------------------------------

        all_fire_gas_esd_items = list(
            FireGasESD.objects
            .select_related("role")
            .order_by("display_order", "code")
        )

        # Only the PermitFireGasESD rows selected for this permit.
        fire_gas_esd_items = list(
            getattr(permit, "prefetched_fire_gas_esd_items", None)
            or PermitFireGasESDService.get_permit_items(permit=permit)
        )

        # Add action permissions to actual PermitFireGasESD rows.
        for item in fire_gas_esd_items:
            item.can_sign_isolation = PermitFireGasESDService.can_sign_isolation(
                item=item,
                actor=self.request.user,
            )

            item.can_sign_deisolation = (
                PermitFireGasESDService.can_sign_deisolation(
                    item=item,
                    actor=self.request.user,
                )
            )


        permit_fg_esd_map = {
            item.fire_gas_esd_id: item
            for item in fire_gas_esd_items
        }

        for master_item in all_fire_gas_esd_items:
            master_item.permit_item = permit_fg_esd_map.get(
                master_item.id
            )

        can_remove_fire_gas_esd_items = (
            PermitFireGasESDService.can_remove_item(
                permit=permit,
                actor=self.request.user,
            )
        )

        # Keep this context key in case another existing template/pane uses it.
        context["fire_gas_esd_items"] = fire_gas_esd_items

        # New key for the pane that must show every master option.
        context["all_fire_gas_esd_items"] = all_fire_gas_esd_items

        context["can_remove_fire_gas_esd_items"] = (
            can_remove_fire_gas_esd_items
        )

        # ----------------------------------------------------------
        # Workflow
        # ----------------------------------------------------------

        context["workflow_actions"] = (
            self.get_available_workflow_actions(permit)
        )

        context["is_currently_valid"] = permit.is_active

        context["can_edit_permit"] = (
            WorkflowAuthorizationService.actor_can_edit_permit(
                actor=self.request.user,
                permit=permit,
            )
        )

        # ----------------------------------------------------------
        # Active workflow state
        # ----------------------------------------------------------

        context["is_active_state"] = (
            permit.current_step is not None
            and permit.current_step.state
            == PermitWorkflowStep.State.ACTIVE
        )

        # ----------------------------------------------------------
        # Active work shifts
        # ----------------------------------------------------------

        work_shifts = getattr(
            permit,
            "prefetched_work_shifts",
            [],
        )

        active_shift_roles = getattr(
            permit.permit_type,
            "prefetched_active_shift_roles",
            [],
        )

        context["work_shifts"] = work_shifts
        context["active_shift_roles"] = active_shift_roles

        context["has_open_work_shift"] = any(
            work_shift.status == PermitWorkShift.Status.OPEN
            for work_shift in work_shifts
        )

        for work_shift in work_shifts:
            signoffs = list(work_shift.signoffs.all())

            work_shift.completed_signoffs_count = sum(
                signoff.signed_by_id is not None
                for signoff in signoffs
            )

            work_shift.is_ready = not any(
                signoff.is_required
                and signoff.signed_by_id is None
                for signoff in signoffs
            )

        # ----------------------------------------------------------
        # Shift management permissions
        # ----------------------------------------------------------
        context["can_view_work_shifts"] = PermitWorkShiftService.can_view_work_shifts(
            actor=self.request.user,
            permit=permit,
        )

        context["can_manage_work_shifts"] = (
            context["is_active_state"]
            and PermitWorkShiftService.can_manage_work_shifts(
                actor=self.request.user,
                permit=permit,
            )
        )

        context["work_shift_form"] = PermitWorkShiftForm(
            permit=permit
        )

        # ----------------------------------------------------------
        # Work-shift signoff permissions
        # ----------------------------------------------------------

        can_sign_role_codes = set()

        if context["is_active_state"]:
            for work_shift in work_shifts:
                for signoff in work_shift.signoffs.all():

                    if (
                        work_shift.status
                        != PermitWorkShift.Status.OPEN
                        or signoff.signed_by_id
                    ):
                        continue

                    if PermitWorkShiftService.can_sign_work_shift(
                        actor=self.request.user,
                        permit=permit,
                        role=signoff.role,
                    ):
                        can_sign_role_codes.add(
                            signoff.role.code
                        )

        context["can_sign_shift_role_codes"] = (
            can_sign_role_codes
        )


        # ----------------------------------------------------------
        # Permit close-out
        # ----------------------------------------------------------

        closeout_signoffs = getattr(
            permit,
            "prefetched_closeout_signoffs",
            [],
        )

        for signoff in closeout_signoffs:
            signoff.is_signed = (
                signoff.signed_by_id is not None
            )

            signoff.is_pending = (
                signoff.signed_by_id is None
            )
        closeout_signoffs = PermitCloseoutService.get_closeout_signoffs_for_permit(permit=permit)

        context["closeout_signoffs"] = closeout_signoffs

        context["can_view_closeout"] = PermitCloseoutService.can_view_closeout_signoffs(
            permit=permit,
            actor=self.request.user,
        )
        
        context["has_closeout_items"] = bool(
            closeout_signoffs
        )

        context["closeout_total_count"] = len(
            closeout_signoffs
        )

        context["closeout_completed_count"] = sum(
            signoff.signed_by_id is not None
            for signoff in closeout_signoffs
        )

        context["closeout_pending_count"] = (
            context["closeout_total_count"]
            - context["closeout_completed_count"]
        )

        context["closeout_is_complete"] = (
            bool(closeout_signoffs)
            and context["closeout_pending_count"] == 0
        )


        # ----------------------------------------------------------
        # Close-out signoff permissions
        # ----------------------------------------------------------

        can_sign_closeout_role_codes = set()

        if context["is_active_state"]:

            for signoff in closeout_signoffs:

                # Already signed
                if signoff.signed_by_id:
                    continue

                role = signoff.closeout_item.role

                # No role configured
                if role is None:
                    continue

                if WorkflowAuthorizationService.actor_has_role_for_permit(
                    actor=self.request.user,
                    permit=permit,
                    role=role,
                ):
                    can_sign_closeout_role_codes.add(
                        role.code
                    )

        context["can_sign_closeout_role_codes"] = (
            can_sign_closeout_role_codes
        )

        return context


@login_required
def permit_autocomplete(request):
    q = request.GET.get("q", "").strip()

    permits = (
        Permit.objects
        .filter(permit_number__icontains=q)
        .order_by("-created_at")[:10]
    )

    results = [
        {
            "id": permit.id,
            "text": permit.permit_number,
        }
        for permit in permits
    ]

    return JsonResponse({"results": results})


class PermitCreateView(LoginRequiredMixin, CreateView):
    model = Permit
    form_class = PermitCreateForm
    template_name = "permits/permit_form.html"

    def get_initial(self):
        initial = super().get_initial()

        location_id = self.request.GET.get("location_tag")
        if location_id:
            initial["location_tag"] = location_id

        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_update"] = False
        context["page_title"] = "Create Permit"

        location_id = (
            self.request.GET.get("location_tag")
            or self.request.POST.get("location_tag")
        )

        if location_id:
            try:
                context["location"] = LocationTag.objects.get(pk=location_id)
            except LocationTag.DoesNotExist:
                context["location"] = None

        return context

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)

        self.object.created_by = self.request.user
        self.object.modified_by = self.request.user

        self.object.save()

        form.save_assessments(user=self.request.user)
        form.save_fire_gas_esd_items(user=self.request.user)

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "permits:permit_detail",
            kwargs={
                "permit_number": self.object.permit_number,
            },
        )

class PermitUpdateView(LoginRequiredMixin, UpdateView):
    model = Permit
    form_class = PermitUpdateForm
    template_name = "permits/permit_form_update.html"
    context_object_name = "permit"
    slug_field = "permit_number"
    slug_url_kwarg = "permit_number"

    def get_queryset(self):
        return (
            Permit.objects.select_related(
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
                "current_step__editable_role",
                "current_step__editable_role__required_qualification",
            )
        )

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()

        try:
            WorkflowAuthorizationService.ensure_actor_can_edit_permit(
                actor=request.user,
                permit=self.object,
            )

        except PermissionDenied as exc:
            messages.error(
                request,
                exc.args[0] if exc.args else "You are not authorized to edit this permit.",
            )
            return redirect(
                "permits:permit_detail",
                permit_number=self.object.permit_number,
            )

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context["is_update"] = True
        context["page_title"] = f"Edit Permit {self.object.permit_number}"

        if self.object.location_tag_id:
            context["location"] = self.object.location_tag
        else:
            context["location"] = None

        return context

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)

        self.object.modified_by = self.request.user
        self.object.save()

        form.save_assessments(user=self.request.user)
        form.save_fire_gas_esd_items(user=self.request.user)

        messages.success(
            self.request,
            "Permit updated successfully.",
        )

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse(
            "permits:permit_detail",
            kwargs={
                "permit_number": self.object.permit_number,
            },
        )



@login_required
def get_permit_data(request):
    permit_id = request.GET.get("continuation_of")

    if not permit_id:
        return JsonResponse(
            {"error": "No permit selected"},
            status=400,
        )

    try:
        permit = (
            Permit.objects
            .select_related(
                "location_tag",
                "department",
                "work_order",
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
                    "permit_fire_gas_esd_items",
                    queryset=(
                        PermitFireGasESD.objects
                        .select_related("fire_gas_esd")
                        .order_by(
                            "fire_gas_esd__display_order",
                            "fire_gas_esd__code",
                            "unit_zone",
                            "pk",
                        )
                    ),
                    to_attr="continuation_fire_gas_esd_items",
                ),
            )
            .get(pk=permit_id)
        )

    except Permit.DoesNotExist:
        return JsonResponse(
            {"error": "Permit not found"},
            status=404,
        )

    active_hazards = [
        assessment.hazard_id
        for assessment in permit.active_hazard_assessments
    ]

    active_precautions = [
        requirement.precaution_id
        for requirement in permit.active_precaution_requirements
    ]

    # Only copy the selected item, Unit/Zone, and remark.
    # Deliberately do NOT copy isolation/de-isolation confirmations/times.
    fire_gas_esd_items = [
        {
            "fire_gas_esd_id": item.fire_gas_esd_id,
            "unit_zone": item.unit_zone or "",
            "remarks": item.remarks or "",
        }
        for item in permit.continuation_fire_gas_esd_items
    ]

    return JsonResponse(
        {
            "scope_of_work": permit.scope_of_work or "",
            "remarks": permit.remarks or "",
            "department": permit.department_id or "",
            "location_tag": permit.location_tag_id or "",
            "location_tag_text": (
                str(permit.location_tag)
                if permit.location_tag
                else ""
            ),
            "work_order": permit.work_order_id or "",
            "work_order_text": (
                str(permit.work_order)
                if permit.work_order
                else ""
            ),

            "electrical_tools": permit.electrical_tools or "",
            "mechanical_tools": permit.mechanical_tools or "",
            "other_tools": permit.other_tools or "",
            "hazardous_materials": permit.hazardous_materials or "",
            "non_explosion_proof_equipment": (
                permit.non_explosion_proof_equipment or ""
            ),
            "vehicle_required": permit.vehicle_required,
            "vehicle_description": permit.vehicle_description or "",

            "mechanical_isolation": permit.mechanical_isolation or "",
            "equipment_depressurized": permit.equipment_depressurized or "",
            "equipment_drained": permit.equipment_drained or "",
            "equipment_purged": permit.equipment_purged or "",
            "process_isolation": permit.process_isolation or "",
            "area_authority_present_required": (
                permit.area_authority_present_required
            ),
            "fire_watch_present_required": (
                permit.fire_watch_present_required
            ),
            "equipment_preparation_notes": (
                permit.equipment_preparation_notes or ""
            ),

            "hazards": active_hazards,
            "precautions": active_precautions,
            "fire_gas_esd_items": fire_gas_esd_items,
        }
    )



class PermitWorkflowTransitionView(LoginRequiredMixin, View):
    """
    Handles workflow decisions for a permit.

    Important:
    - This view never updates Permit.current_step directly.
    - It delegates all workflow movement to PermitWorkflowService.
    """

    def post(self, request, permit_number):
        permit = get_object_or_404(
            Permit.objects.select_related(
                "workflow",
                "current_step",
                "current_step__editable_role",
                "current_step__editable_role__required_qualification",
                "permit_type",
            ),
            permit_number=permit_number,
        )

        form = PermitWorkflowDecisionForm(request.POST)

        if not form.is_valid():
            messages.error(
                request,
                "Invalid workflow action submission.",
            )
            return redirect(
                "permits:permit_detail",
                permit_number=permit.permit_number,
            )

        role_code = form.cleaned_data["role_code"]
        decision = form.cleaned_data["decision"]
        comment = form.cleaned_data.get("comment", "")

        try:
            result = PermitWorkflowService.transition(
                permit_id=permit.pk,
                actor=request.user,
                role_code=role_code,
                decision=decision,
                comment=comment,
            )

        except WorkflowTransitionError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to perform this workflow action.",
            )

        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        else:
            messages.success(
                request,
                (
                    f"Workflow action completed. "
                    f"Permit moved to: {result.permit.current_step.title}"
                ),
            )

        return redirect(
            "permits:permit_detail",
            permit_number=permit.permit_number,
        )


class PermitWorkShiftCreateView(LoginRequiredMixin, View):

    def post(self, request, permit_number):
        permit = get_object_or_404(
            Permit.objects.select_related(
                "permit_type",
                "current_step",
                "department",
                "location_tag",
                "location_tag__unit",
            ),
            permit_number=permit_number,
        )

        form = PermitWorkShiftForm(request.POST, permit=permit)

        if not form.is_valid():
            messages.error(
                request,
                "Invalid work-shift information.",
            )
            if request.headers.get("HX-Request") == "true":
                return _render_detail_fragment(
                    request,
                    permit.permit_number,
                    "permits/permit_detail_partials/work_shifts_panel.html",
                    {"work_shift_form": form},
                )
            return redirect(
                reverse("permits:permit_detail", kwargs={"permit_number": permit.permit_number})
                + "#work-shifts-panel"
            )

        try:
            result = PermitWorkShiftService.create_work_shift(
                permit_id=permit.pk,
                actor=request.user,
                date=form.cleaned_data["date"],
                shift=form.cleaned_data["shift"],
                work_leader=form.cleaned_data["work_leader"],
                worker_count=form.cleaned_data["worker_count"],
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to create work shifts "
                "for this permit.",
            )
            form.add_error(None, "You are not authorized to create work shifts for this permit.")

        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )
            form.add_error(None, exc.messages[0] if hasattr(exc, "messages") else str(exc))

        else:
            messages.success(
                request,
                (
                    f"Work shift {result.work_shift.date} / "
                    f"{result.work_shift.get_shift_display()} was created."
                ),
            )

        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                permit.permit_number,
                "permits/permit_detail_partials/work_shifts_panel.html",
                {"work_shift_form": form},
            )
        return redirect(
            reverse("permits:permit_detail", kwargs={"permit_number": permit.permit_number})
            + "#work-shifts-panel"
        )



class PermitWorkShiftSignoffView(LoginRequiredMixin, View):

    def post(self, request, permit_number, work_shift_id, role_code):

        work_shift = get_object_or_404(
            PermitWorkShift.objects.select_related("permit"),
            pk=work_shift_id,
            permit__permit_number=permit_number,
        )

        form = PermitShiftSignoffForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please confirm the signoff before signing.")
            return redirect(
                reverse("permits:permit_detail", kwargs={"permit_number": permit_number})
                + "#work-shifts-panel"
            )

        try:
            result = PermitWorkShiftService.sign_shift(
                work_shift_id=work_shift_id,
                actor=request.user,
                role_code=role_code,
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to perform this signoff.",
            )

        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        else:
            messages.success(
                request,
                (
                    f"{result.signoff.role.name} signoff completed "
                    f"for {result.signoff.work_shift.get_shift_display()}."
                ),
            )

        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                work_shift.permit.permit_number,
                "permits/permit_detail_partials/work_shifts_panel.html",
            )
        next_url = request.POST.get("next", "").strip()
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(
            reverse(
                "permits:permit_detail",
                kwargs={"permit_number": work_shift.permit.permit_number},
            )
            + "#work-shifts-panel"
        )


class PermitWorkShiftCloseView(LoginRequiredMixin, View):
    """Permit Office endpoint for closing the current open work shift."""

    def post(self, request, permit_number, work_shift_id):
        work_shift = get_object_or_404(
            PermitWorkShift.objects.select_related("permit"),
            pk=work_shift_id,
            permit__permit_number=permit_number,
        )

        try:
            result = PermitWorkShiftService.close_work_shift(
                work_shift_id=work_shift.pk,
                actor=request.user,
            )
        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to close work shifts for this permit.",
            )
        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )
        else:
            messages.success(
                request,
                (
                    f"Work shift {result.work_shift.date} / "
                    f"{result.work_shift.get_shift_display()} was closed."
                ),
            )

        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                work_shift.permit.permit_number,
                "permits/permit_detail_partials/work_shifts_panel.html",
            )
        next_url = request.POST.get("next", "").strip()
        if next_url.startswith("/") and not next_url.startswith("//"):
            return redirect(next_url)
        return redirect(
            reverse(
                "permits:permit_detail",
                kwargs={"permit_number": work_shift.permit.permit_number},
            )
            + "#work-shifts-panel"
        )


class PermitCloseoutSignoffView(LoginRequiredMixin, View):
    """
    Signs one permit close-out requirement.

    The responsible role is determined from the stored
    PermitCloseoutItem associated with the sign-off.

    The browser never supplies the role.
    """

    def post(
        self,
        request,
        permit_number,
        closeout_signoff_id,
    ):
        signoff = get_object_or_404(
            PermitCloseoutSignoff.objects.select_related(
                "permit",
                "closeout_item",
                "closeout_item__role",
            ),
            pk=closeout_signoff_id,
            permit__permit_number=permit_number,
        )

        try:
            result = PermitCloseoutService.sign_closeout(
                signoff_id=signoff.pk,
                actor=request.user,
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to perform this close-out signoff.",
            )

        except ValidationError as exc:
            messages.error(
                request,
                (
                    exc.messages[0]
                    if hasattr(exc, "messages")
                    else str(exc)
                ),
            )

        else:
            messages.success(
                request,
                (
                    f"{result.signoff.closeout_item.name} "
                    f"signoff completed."
                ),
            )

        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                signoff.permit.permit_number,
                "permits/permit_detail_partials/closeout_panel.html",
            )
        return redirect(
            reverse(
                "permits:permit_detail",
                kwargs={
                    "permit_number": signoff.permit.permit_number,
                },
            )
            + "#permit-closeout-panel"
        )


class PermitFireGasESDIsolateView(LoginRequiredMixin, View):
    """
    Records the isolation date/time and signature for one
    PermitFireGasESD row.

    The responsible role is taken from the linked FireGasESD master item,
    never supplied by the browser. Isolation can be signed at any time,
    independently of the permit's workflow/editable state.
    """

    def post(self, request, permit_number, item_id):
        item = get_object_or_404(
            PermitFireGasESD.objects.select_related(
                "permit",
                "fire_gas_esd",
                "fire_gas_esd__role",
            ),
            pk=item_id,
            permit__permit_number=permit_number,
        )

        form = PermitFireGasESDSignoffForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                "Please provide a valid isolation date/time and confirm before signing.",
            )
            return redirect(
                reverse("permits:permit_detail", kwargs={"permit_number": permit_number})
                + "#fire-gas-esd-panel"
            )

        try:
            result = PermitFireGasESDService.sign_isolation(
                item_id=item.pk,
                isolated_time=form.cleaned_data["time"],
                actor=request.user,
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to sign this isolation.",
            )

        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        else:
            messages.success(
                request,
                f"Isolation signed for {result.item.fire_gas_esd}.",
            )

        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                item.permit.permit_number,
                "permits/permit_detail_partials/_fire_gas_esd_panel.html",
            )
        return redirect(
            reverse(
                "permits:permit_detail",
                kwargs={"permit_number": item.permit.permit_number},
            )
            + "#fire-gas-esd-panel"
        )


class PermitFireGasESDDeisolateView(LoginRequiredMixin, View):
    """
    Records the de-isolation date/time and signature for one
    PermitFireGasESD row.

    Same authorization rules as isolation: the responsible role comes
    from the FireGasESD master item and de-isolation can be signed at
    any time.
    """

    def post(self, request, permit_number, item_id):
        item = get_object_or_404(
            PermitFireGasESD.objects.select_related(
                "permit",
                "fire_gas_esd",
                "fire_gas_esd__role",
            ),
            pk=item_id,
            permit__permit_number=permit_number,
        )

        form = PermitFireGasESDSignoffForm(request.POST)
        if not form.is_valid():
            messages.error(
                request,
                "Please provide a valid de-isolation date/time and confirm before signing.",
            )
            return redirect(
                reverse("permits:permit_detail", kwargs={"permit_number": permit_number})
                + "#fire-gas-esd-panel"
            )

        try:
            result = PermitFireGasESDService.sign_deisolation(
                item_id=item.pk,
                deisolated_time=form.cleaned_data["time"],
                actor=request.user,
            )

        except PermissionDenied:
            messages.error(
                request,
                "You are not authorized to sign this de-isolation.",
            )

        except ValidationError as exc:
            messages.error(
                request,
                exc.messages[0] if hasattr(exc, "messages") else str(exc),
            )

        else:
            messages.success(
                request,
                f"De-isolation signed for {result.item.fire_gas_esd}.",
            )

        if request.headers.get("HX-Request") == "true":
            return _render_detail_fragment(
                request,
                item.permit.permit_number,
                "permits/permit_detail_partials/_fire_gas_esd_panel.html",
            )
        return redirect(
            reverse(
                "permits:permit_detail",
                kwargs={"permit_number": item.permit.permit_number},
            )
            + "#fire-gas-esd-panel"
        )


