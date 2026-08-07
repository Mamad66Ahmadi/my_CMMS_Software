# permits/views/permit_detail_views.py 

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.views.generic import DetailView, CreateView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Prefetch

from permits.forms import PermitCreateForm
from permits.models import Permit, PermitHazard, PermitPrecaution
from equipment.models import LocationTag
from permits.models import PermitWorkflowTransition
from permits.services.authorization_service import WorkflowAuthorizationService
from permits.services.condition_service import WorkflowConditionEvaluator
from permits.forms import PermitWorkflowDecisionForm

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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permit = self.object

        permit.active_hazards = [
            assessment.hazard
            for assessment in permit.active_hazard_assessments
        ]

        permit.active_precautions = [
            requirement.precaution
            for requirement in permit.active_precaution_requirements
        ]

        context["is_currently_valid"] = permit.is_active

        context["workflow_actions"] = self.get_available_workflow_actions(permit)

        return context

# ----------------------- Auto complete ------------------
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


# ----------------- Create --------------------------------
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

        # Audit fields
        self.object.created_by = self.request.user
        self.object.modified_by = self.request.user

        # Workflow fields such as workflow/current_step/status are not set here.
        # They should be initialized by your workflow service/model signal/model save logic.
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

# ------------------------ Filling the form based on permit number ---------------
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
        
        # Tools & Vehicle
        "electrical_tools": permit.electrical_tools or "",
        "mechanical_tools": permit.mechanical_tools or "",
        "other_tools": permit.other_tools or "",
        "hazardous_materials": permit.hazardous_materials or "",
        "non_explosion_proof_equipment": permit.non_explosion_proof_equipment or "",
        "vehicle_required": permit.vehicle_required,
        "vehicle_description": permit.vehicle_description or "",

        # Isolation details
        "mechanical_isolation": permit.mechanical_isolation or "",
        "equipment_depressurized": permit.equipment_depressurized or "",
        "equipment_drained": permit.equipment_drained or "",
        "equipment_purged": permit.equipment_purged or "",
        "process_isolation": permit.process_isolation or "",
        "area_authority_present_required": permit.area_authority_present_required,
        "fire_watch_present_required": permit.fire_watch_present_required,
        "equipment_preparation_notes": permit.equipment_preparation_notes or "",

        # M2Ms
        "hazards": active_hazards,
        "precautions": active_precautions,
    })
