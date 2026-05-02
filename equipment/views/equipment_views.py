# equipment/views/equipment_views.py
from django.core.paginator import Paginator
from django.views.generic import TemplateView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect,render
from django.urls import reverse_lazy, reverse
from django.forms import inlineformset_factory 
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required


from equipment.models.equipment_models import Equipment
from equipment.models.request_equipment_models import EquipmentChangeRequest, EquipmentDocumentChangeRequest

from equipment.forms.equioment_change_form import EquipmentChangeRequestForm



class EquipmentList(LoginRequiredMixin, TemplateView):
    template_name = "equipment/equipment_list.html"
    redirect_field_name = "next"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # ---------------- Filters ----------------
        filters = {
            "functional_location": self.request.GET.get("functional_location", "").strip(),
            "serial_number": self.request.GET.get("serial_number", "").strip(),
            "manufacturer": self.request.GET.get("manufacturer", "").strip(),
            "model": self.request.GET.get("model", "").strip(),
            "note": self.request.GET.get("note", "").strip(),
            "is_active": self.request.GET.get("is_active", "true"),
        }

        queryset = Equipment.objects.select_related(
            "functional_location",
            "functional_location__unit",
            "created_by",
            "modified_by",
        )

        # ---------------- Filtering ----------------
        if filters["functional_location"]:
            queryset = queryset.filter(
                functional_location__loc_tag__icontains=filters["functional_location"]
            )

        if filters["serial_number"]:
            queryset = queryset.filter(
                serial_number__icontains=filters["serial_number"]
            )

        if filters["manufacturer"]:
            queryset = queryset.filter(
                manufacturer__icontains=filters["manufacturer"]
            )

        if filters["model"]:
            queryset = queryset.filter(model__icontains=filters["model"])

        if filters["note"]:
            queryset = queryset.filter(note__icontains=filters["note"])

        if filters["is_active"] == "true":
            queryset = queryset.filter(is_active=True)

        # ---------------- Sorting ----------------
        sort_by = self.request.GET.get("sort", "functional_location")
        sort_order = self.request.GET.get("order", "asc")

        allowed_sort_fields = {
            "id": "id",
            "functional_location": "functional_location__loc_tag",
            "serial_number": "serial_number",
            "manufacturer": "manufacturer",
            "model": "model",
            "note": "note",
            "is_active": "is_active",
            "created_at": "created_at",
            "created_by": "created_by__username",
            "modified_at": "modified_at",
            "modified_by": "modified_by__username",
        }

        sort_field = allowed_sort_fields.get(sort_by, "functional_location__loc_tag")

        if sort_order == "desc":
            queryset = queryset.order_by(f"-{sort_field}")
        else:
            queryset = queryset.order_by(sort_field)

        # ---------------- Pagination ----------------
        per_page = self.request.GET.get("per_page", "25")

        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 25

        if per_page > 200:
            per_page = 200
        elif per_page < 10:
            per_page = 10

        paginator = Paginator(queryset, per_page)
        page_number = self.request.GET.get("page")
        equipments = paginator.get_page(page_number)

        # ---------------- Context ----------------
        context["per_page"] = per_page
        context["page_obj"] = equipments
        context["equipments"] = equipments
        context["paginator"] = paginator
        context["sort_by"] = sort_by
        context["sort_order"] = sort_order
        context["filters"] = filters
        context["total_equipments"] = queryset.count()

        # Build sorting params without sort/order for column headers
        param_list = [f"{k}={v}" for k, v in filters.items() if v]
        param_list.append(f"per_page={per_page}")
        context["sort_params"] = "&".join(param_list)

        # Build safe query string without 'page' param
        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_params"] = params.urlencode()

        return context


# ----------------------------------------- Equipment Detail ------------------------------


class EquipmentDetail(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = "equipment/equipment_detail.html"
    context_object_name = "equipment"

    pk_url_kwarg = "pk"  # assuming URL pattern like path("<int:pk>/", ...)
    login_url = "/accounts/login/"
    redirect_field_name = "next"

    queryset = Equipment.objects.select_related(
        "functional_location",
        "created_by",
        "modified_by",
    ).prefetch_related(
        "documents",
    )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipment = self.object

        # Functional location of this equipment (for linking)
        context["functional_location"] = equipment.functional_location

        # Related documents
        context["documents"] = equipment.documents.all()

        context["change_requests"] = (
            EquipmentChangeRequest.objects
            .filter(equipment=equipment)
            .order_by("-requested_at")[:5]
        )

        context["has_pending_request"] = EquipmentChangeRequest.objects.filter(
            equipment=equipment,
            status=EquipmentChangeRequest.Status.PENDING,
        ).exists()

        return context



#-------------------------------- Modification ------------------------------
class EquipmentUpdateRequestView(LoginRequiredMixin, CreateView):
    model = EquipmentChangeRequest
    form_class = EquipmentChangeRequestForm
    template_name = "equipment/equipment_request_update_form.html"
    login_url = "/accounts/login/"
    redirect_field_name = "next"

    def dispatch(self, request, *args, **kwargs):
        self.equipment = get_object_or_404(Equipment, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        eq = self.equipment
        return {
            "functional_location": eq.functional_location,
            "serial_number": eq.serial_number,
            "manufacturer": eq.manufacturer,
            "model": eq.model,
            "note": eq.note,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['equipment'] = self.equipment
        context['pending_request'] = EquipmentChangeRequest.objects.filter(
            equipment=self.equipment,
            status=EquipmentChangeRequest.Status.PENDING,
            requested_by=self.request.user
        ).first()
        return context

    @transaction.atomic
    def form_valid(self, form):
        self.object, _ = EquipmentChangeRequest.objects.get_or_create(
            equipment=self.equipment,
            status=EquipmentChangeRequest.Status.PENDING,
            defaults={
                "requested_by": self.request.user,
                "action": EquipmentChangeRequest.Action.UPDATE
            }
        )

        updated_instance = form.save(commit=False)
        for field in ["functional_location", "serial_number", "manufacturer", "model", "note"]:
            setattr(self.object, field, getattr(updated_instance, field))

        # Detect changes, as you already do
        eq = self.equipment
        changes = {}
        for field in ["functional_location", "serial_number", "manufacturer", "model", "note"]:
            old = getattr(eq, field, None)
            new = getattr(self.object, field)
            if old != new:
                changes[field] = {"old": str(old), "new": str(new)}
        self.object.changes = changes
        self.object.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy("equipment:equipment_detail", kwargs={"pk": self.equipment.pk})



@login_required
def upload_request_document(request, equipment_id):
    if request.method != "POST":
        return HttpResponse(status=405)
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    change_request, _ = EquipmentChangeRequest.objects.get_or_create(
        equipment=equipment,
        status=EquipmentChangeRequest.Status.PENDING,
        defaults={"requested_by": request.user}
    )
    file = request.FILES.get("file")
    if not file:
        return HttpResponseBadRequest("Missing file")
    file_name = request.POST.get("file_name") or file.name
    description = request.POST.get("description")
    doc = EquipmentDocumentChangeRequest.objects.create(
        change_request=change_request,
        file=file,
        file_name=file_name,
        description=description,
    )
    return render(request, "equipment/document_row.html", {"doc": doc})

@login_required
def delete_request_document(request, pk):
    if request.method != "DELETE":
        return HttpResponse(status=405)
    doc = get_object_or_404(
        EquipmentDocumentChangeRequest,
        pk=pk,
        change_request__requested_by=request.user,
        change_request__status=EquipmentChangeRequest.Status.PENDING,
    )
    doc.delete()
    return HttpResponse("")
