# permits/views/permit_detail_views.py 

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, CreateView
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch

from permits.forms import PermitCreateForm
from permits.models import Permit, Hazard, Precaution
from equipment.models import LocationTag


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
                # Prefetch only active hazards and precautions to avoid N+1 queries in templates
                Prefetch(
                    "hazards",
                    queryset=Hazard.objects.filter(
                        permit_assessments__is_active=True
                    ).distinct(),
                    to_attr="active_hazards",
                ),
                Prefetch(
                    "precautions",
                    queryset=Precaution.objects.filter(
                        permit_requirements__is_active=True
                    ).distinct(),
                    to_attr="active_precautions",
                ),
                "continuations",  # Reverse FK: permits continued from this one
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        permit = self.object

        # Retrieve the workflow activity status via the standard current step evaluation
        context["is_currently_valid"] = permit.is_active
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
        location_id = self.request.GET.get("location_tag") or self.request.POST.get("location_tag")

        if location_id:
            try:
                context["location"] = LocationTag.objects.get(pk=location_id)
            except LocationTag.DoesNotExist:
                pass

        return context

    def form_valid(self, form):
        obj = form.save(commit=False)
        # Note: Under the new engine, dynamic workflows replace legacy static status.
        # This falls back gracefully if your CreateView/Form isn't fully migrated.
        obj.created_by = self.request.user
        obj.modified_by = self.request.user
        obj.save()
        form.save_m2m()
        self.object = obj
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("permits:permit_detail", kwargs={"permit_number": self.object.permit_number})
    

# ------------------------ Filling the form based on permit number ---------------
@login_required
def get_permit_data(request):
    permit_id = request.GET.get("continuation_of")

    if not permit_id:
        return JsonResponse({"error": "No permit selected"}, status=400)

    try:
        # Optimized with prefetch for active items to populate target forms safely
        permit = (
            Permit.objects.select_related("location_tag", "department", "work_order")
            .prefetch_related(
                Prefetch(
                    "hazards",
                    queryset=Hazard.objects.filter(
                        permit_assessments__is_active=True
                    ).distinct(),
                    to_attr="active_hazards",
                ),
                Prefetch(
                    "precautions",
                    queryset=Precaution.objects.filter(
                        permit_requirements__is_active=True
                    ).distinct(),
                    to_attr="active_precautions",
                ),
            )
            .get(pk=permit_id)
        )
    except Permit.DoesNotExist:
        return JsonResponse({"error": "Permit not found"}, status=404)

    # Return hazard and precaution lists to populate checkboxes/select2 elements in the form
    active_hazards = [h.id for h in getattr(permit, "active_hazards", [])]
    active_precautions = [p.id for p in getattr(permit, "active_precautions", [])]

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
