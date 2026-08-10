# permits/views/permit_detail_views.py

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, CreateView, UpdateView

from equipment.models import LocationTag
from permits.forms import PermitCreateForm, PermitWorkflowDecisionForm,PermitUpdateForm
from permits.models import (
    Permit,
    PermitHazard,
    PermitPrecaution,
    PermitWorkflowTransition,
    PermitApproval,
)
from permits.services.authorization_service import WorkflowAuthorizationService
from permits.services.condition_service import WorkflowConditionEvaluator
from permits.services.workflow_service import (
    PermitWorkflowService,
    WorkflowTransitionError,
)
from permits.models.permit_base_models import Hazard, Precaution




# ---------------- Detail View ----------------
class PermitDetailView(LoginRequiredMixin, DetailView):
    model = Permit
    template_name = "permits/permit_detail.html"
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
            .prefetch_related(
                Prefetch(
                    "hazard_assessments",
                    queryset=PermitHazard.objects.filter(
                        is_active=True,
                    ).select_related("hazard"),
                    to_attr="active_hazard_assessments",
                ),
                Prefetch(
                    "precaution_requirements",
                    queryset=PermitPrecaution.objects.filter(
                        is_active=True,
                    ).select_related("precaution"),
                    to_attr="active_precaution_requirements",
                ),
                "continuations",
                # Prefetch approvals sorted by execution time (newest first as per Meta class ordering)
                Prefetch(
                    "approvals",
                    queryset=PermitApproval.objects.select_related("actor", "role", "from_step", "to_step")
                ),
            )
        )
    def get_available_workflow_actions(self, permit):
        """
        Return transitions the current user can perform from the permit's
        current workflow step.

        This is display-only. The POST view still validates again.
        """

        if not permit.workflow_id or not permit.current_step_id:
            return []

        if permit.current_step.is_terminal:
            return []

        transitions = (
            PermitWorkflowTransition.objects.select_related(
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

            except PermissionDenied as exc:
                print(
                    "\n========== WORKFLOW ACTION BLOCKED =========="
                )
                print(f"User: {self.request.user}")
                print(f"User ID: {self.request.user.pk}")
                print(f"Permit: {permit.permit_number}")
                print(f"Permit ID: {permit.pk}")
                print(f"Workflow: {permit.workflow}")
                print(f"Current Step: {permit.current_step}")
                print(f"Transition: {transition}")
                print(f"Role: {transition.role}")
                print(f"Role Code: {transition.role.code}")
                print(f"Decision: {transition.decision}")
                print(f"Reason: {exc}")
                print("===============================================\n")

                continue

            except ValidationError as exc:
                print(
                    "\n========== WORKFLOW CONDITION BLOCKED =========="
                )
                print(f"User: {self.request.user}")
                print(f"Permit: {permit.permit_number}")
                print(f"Transition: {transition}")
                print(f"Role: {transition.role}")
                print(f"Decision: {transition.decision}")
                print(f"Reason: {exc}")
                print("=================================================\n")

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permit = self.object

        # 1. Fetch all master records
        all_hazards = list(Hazard.objects.order_by("display_order", "code"))
        all_precautions = list(Precaution.objects.order_by("display_order", "code"))

        # 2. Build maps of permit-specific records
        hazard_map = {
            item.hazard_id: item
            for item in permit.hazard_assessments.select_related("created_by", "modified_by", "removed_by")
        }
        
        precaution_map = {
            item.precaution_id: item
            for item in permit.precaution_requirements.select_related("created_by", "modified_by", "removed_by")
        }

        # 3. Attach the permit-specific assessment directly to each master instance
        for hazard in all_hazards:
            hazard.permit_assessment = hazard_map.get(hazard.id)

        for precaution in all_precautions:
            precaution.permit_assessment = precaution_map.get(precaution.id)

        # 4. Bind variables to context
        context["all_hazards"] = all_hazards
        context["all_precautions"] = all_precautions

        context["workflow_actions"] = self.get_available_workflow_actions(permit)
        context["is_currently_valid"] = permit.is_active
        context["can_edit_permit"] = WorkflowAuthorizationService.actor_can_edit_permit(
            actor=self.request.user,
            permit=permit,
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
        return JsonResponse({"error": "No permit selected"}, status=400)

    try:
        permit = (
            Permit.objects.select_related("location_tag", "department", "work_order")
            .prefetch_related(
                Prefetch(
                    "hazard_assessments",
                    queryset=PermitHazard.objects.filter(
                        is_active=True,
                    ).select_related("hazard"),
                    to_attr="active_hazard_assessments",
                ),
                Prefetch(
                    "precaution_requirements",
                    queryset=PermitPrecaution.objects.filter(
                        is_active=True,
                    ).select_related("precaution"),
                    to_attr="active_precaution_requirements",
                ),
            )
            .get(pk=permit_id)
        )
    except Permit.DoesNotExist:
        return JsonResponse({"error": "Permit not found"}, status=404)

    active_hazards = [
        assessment.hazard_id
        for assessment in permit.active_hazard_assessments
    ]
    active_precautions = [
        requirement.precaution_id
        for requirement in permit.active_precaution_requirements
    ]

    return JsonResponse({
        "scope_of_work": permit.scope_of_work or "",
        "remarks": permit.remarks or "",
        "department": permit.department_id or "",
        "location_tag": permit.location_tag_id or "",
        "location_tag_text": str(permit.location_tag) if permit.location_tag else "",
        "work_order": permit.work_order_id or "",
        "work_order_text": str(permit.work_order) if permit.work_order else "",

        "electrical_tools": permit.electrical_tools or "",
        "mechanical_tools": permit.mechanical_tools or "",
        "other_tools": permit.other_tools or "",
        "hazardous_materials": permit.hazardous_materials or "",
        "non_explosion_proof_equipment": permit.non_explosion_proof_equipment or "",
        "vehicle_required": permit.vehicle_required,
        "vehicle_description": permit.vehicle_description or "",

        "mechanical_isolation": permit.mechanical_isolation or "",
        "equipment_depressurized": permit.equipment_depressurized or "",
        "equipment_drained": permit.equipment_drained or "",
        "equipment_purged": permit.equipment_purged or "",
        "process_isolation": permit.process_isolation or "",
        "area_authority_present_required": permit.area_authority_present_required,
        "fire_watch_present_required": permit.fire_watch_present_required,
        "equipment_preparation_notes": permit.equipment_preparation_notes or "",

        "hazards": active_hazards,
        "precautions": active_precautions,
    })


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
