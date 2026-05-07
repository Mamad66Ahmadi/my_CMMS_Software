# equipment/views/equipment_views.py

from django.core.paginator import Paginator
from django.views.generic import TemplateView, DetailView, CreateView, FormView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy, reverse
from django.db import transaction
from django.http import HttpResponse, HttpResponseBadRequest
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages

from equipment.models.equipment_models import Equipment
from equipment.models.request_equipment_models import (
    EquipmentChangeRequest,
    EquipmentDocumentChangeRequest,
)

from equipment.forms.equioment_change_form import EquipmentChangeRequestForm


# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def update_document_changes(change_request):
    changes = change_request.changes or {}
    docs_qs = change_request.document_requests.all()

    if docs_qs.exists():
        docs_list = [
            {
                "id": d.pk,
                "file_name": d.file_name,
                "description": d.description,
            }
            for d in docs_qs
        ]

        count = docs_qs.count()

        changes["documents"] = {
            "old": f"{count-1} documents" if count > 1 else "0 documents",
            "new": f"{count} documents",
            "details": docs_list,
        }
    else:
        changes.pop("documents", None)

    change_request.changes = changes
    change_request.save(update_fields=["changes"])


def delete_request_files(change_request):
    docs = change_request.document_requests.all()

    for doc in docs:
        if doc.file:
            doc.file.delete(save=False)

    docs.delete()


# ---------------------------------------------------------------------
# Equipment List
# ---------------------------------------------------------------------

class EquipmentList(LoginRequiredMixin, TemplateView):
    template_name = "equipment/equipment_list.html"
    redirect_field_name = "next"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

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

        if filters["functional_location"]:
            queryset = queryset.filter(
                functional_location__loc_tag__icontains=filters["functional_location"]
            )

        if filters["serial_number"]:
            queryset = queryset.filter(serial_number__icontains=filters["serial_number"])

        if filters["manufacturer"]:
            queryset = queryset.filter(manufacturer__icontains=filters["manufacturer"])

        if filters["model"]:
            queryset = queryset.filter(model__icontains=filters["model"])

        if filters["note"]:
            queryset = queryset.filter(note__icontains=filters["note"])

        if filters["is_active"] == "true":
            queryset = queryset.filter(is_active=True)

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

        context["per_page"] = per_page
        context["page_obj"] = equipments
        context["equipments"] = equipments
        context["paginator"] = paginator
        context["sort_by"] = sort_by
        context["sort_order"] = sort_order
        context["filters"] = filters
        context["total_equipments"] = paginator.count

        param_list = [f"{k}={v}" for k, v in filters.items() if v]
        param_list.append(f"per_page={per_page}")
        context["sort_params"] = "&".join(param_list)

        params = self.request.GET.copy()
        params.pop("page", None)
        context["query_params"] = params.urlencode()

        return context


# ---------------------------------------------------------------------
# Equipment Detail
# ---------------------------------------------------------------------

class EquipmentDetail(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = "equipment/equipment_detail.html"
    context_object_name = "equipment"
    pk_url_kwarg = "pk"

    queryset = Equipment.objects.select_related(
        "functional_location",
        "created_by",
        "modified_by",
    ).prefetch_related("documents")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        equipment = self.object

        context["functional_location"] = equipment.functional_location
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


# ---------------------------------------------------------------------
# Equipment Update Request
# ---------------------------------------------------------------------

class EquipmentUpdateRequestView(LoginRequiredMixin, CreateView):
    model = EquipmentChangeRequest
    form_class = EquipmentChangeRequestForm
    template_name = "equipment/equipment_request_update_form.html"

    def dispatch(self, request, *args, **kwargs):

        self.equipment = get_object_or_404(Equipment, pk=kwargs["pk"])

        self.draft_request, _ = EquipmentChangeRequest.objects.get_or_create(
            equipment=self.equipment,
            status=EquipmentChangeRequest.Status.DRAFT,
            requested_by=request.user,
            action=EquipmentChangeRequest.Action.UPDATE,
        )

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
        context["equipment"] = self.equipment
        context["pending_request"] = self.draft_request
        return context

    @transaction.atomic
    def form_valid(self, form):

        self.object = self.draft_request
        updated_instance = form.save(commit=False)

        for field in ["functional_location", "serial_number", "manufacturer", "model", "note"]:
            setattr(self.object, field, getattr(updated_instance, field))

        changes = self.object.changes or {}
        eq = self.equipment

        for field in ["functional_location", "serial_number", "manufacturer", "model", "note"]:
            old = getattr(eq, field, None)
            new = getattr(self.object, field)

            if old != new:
                changes[field] = {"old": str(old), "new": str(new)}
            else:
                changes.pop(field, None)

        self.object.changes = changes
        self.object.status = EquipmentChangeRequest.Status.PENDING
        self.object.save()

        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse_lazy(
            "equipment:equipment_detail",
            kwargs={"pk": self.equipment.pk},
        )


# ---------------------------------------------------------------------
# Update Request Documents
# ---------------------------------------------------------------------

@login_required
def upload_request_document(request, equipment_id):

    if request.method != "POST":
        return HttpResponse(status=405)

    equipment = get_object_or_404(Equipment, pk=equipment_id)

    change_request, _ = EquipmentChangeRequest.objects.get_or_create(
        equipment=equipment,
        status=EquipmentChangeRequest.Status.DRAFT,
        requested_by=request.user,
        action=EquipmentChangeRequest.Action.UPDATE,
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

    update_document_changes(change_request)

    return render(request, "equipment/document_row.html", {"doc": doc})


@login_required
def delete_request_document(request, pk):

    if request.method != "DELETE":
        return HttpResponse(status=405)

    doc = get_object_or_404(
        EquipmentDocumentChangeRequest,
        pk=pk,
        change_request__requested_by=request.user,
        change_request__status=EquipmentChangeRequest.Status.DRAFT,
    )

    change_request = doc.change_request

    if doc.file:
        doc.file.delete(save=False)

    doc.delete()

    update_document_changes(change_request)

    return HttpResponse("")


@login_required
@require_POST
def cancel_update_request(request, request_id):

    change_request = get_object_or_404(
        EquipmentChangeRequest,
        pk=request_id,
        requested_by=request.user,
        status=EquipmentChangeRequest.Status.DRAFT,
        action=EquipmentChangeRequest.Action.UPDATE,
    )

    equipment_id = change_request.equipment_id

    delete_request_files(change_request)
    change_request.delete()

    response = HttpResponse()
    response["HX-Redirect"] = reverse("equipment:equipment_detail", args=[equipment_id])

    return response


# ---------------------------------------------------------------------
# Equipment Create Request
# ---------------------------------------------------------------------

class EquipmentCreateRequestView(LoginRequiredMixin, FormView):

    form_class = EquipmentChangeRequestForm
    template_name = "equipment/equipment_request_create_form.html"
    success_url = reverse_lazy("equipment:equipment_list")

    def get_context_data(self, **kwargs):

        context = super().get_context_data(**kwargs)

        pending_request, _ = EquipmentChangeRequest.objects.get_or_create(
            equipment=None,
            status=EquipmentChangeRequest.Status.DRAFT,
            requested_by=self.request.user,
            action=EquipmentChangeRequest.Action.CREATE,
        )

        context["pending_request"] = pending_request
        return context

    @transaction.atomic
    def form_valid(self, form):

        pending_request = EquipmentChangeRequest.objects.get(
            equipment=None,
            status=EquipmentChangeRequest.Status.DRAFT,
            requested_by=self.request.user,
            action=EquipmentChangeRequest.Action.CREATE,
        )

        pending_request.functional_location = form.cleaned_data["functional_location"]
        pending_request.serial_number = form.cleaned_data["serial_number"]
        pending_request.manufacturer = form.cleaned_data["manufacturer"]
        pending_request.model = form.cleaned_data["model"]
        pending_request.note = form.cleaned_data["note"]

        pending_request.status = EquipmentChangeRequest.Status.PENDING

        changes = {}

        for field in ["functional_location", "serial_number", "manufacturer", "model", "note"]:
            val = getattr(pending_request, field)

            if val:
                changes[field] = {"old": None, "new": str(val)}

        pending_request.changes = changes
        pending_request.save()

        return redirect(self.success_url)


# ---------------------------------------------------------------------
# Create Request Documents
# ---------------------------------------------------------------------

@login_required
def upload_create_request_document(request, request_id):

    if request.method != "POST":
        return HttpResponse(status=405)

    change_request = get_object_or_404(
        EquipmentChangeRequest,
        pk=request_id,
        requested_by=request.user,
        status=EquipmentChangeRequest.Status.DRAFT,
        action=EquipmentChangeRequest.Action.CREATE,
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

    update_document_changes(change_request)

    return render(request, "equipment/document_row.html", {"doc": doc})


@login_required
@require_POST
def cancel_create_request(request, request_id):

    change_request = get_object_or_404(
        EquipmentChangeRequest,
        pk=request_id,
        requested_by=request.user,
        status=EquipmentChangeRequest.Status.DRAFT,
        action=EquipmentChangeRequest.Action.CREATE,
    )

    delete_request_files(change_request)
    change_request.delete()

    return redirect("equipment:equipment_list")


@login_required
@require_POST
def abandon_create_request(request, request_id):

    change_request = get_object_or_404(
        EquipmentChangeRequest,
        pk=request_id,
        requested_by=request.user,
        status=EquipmentChangeRequest.Status.DRAFT,
        action=EquipmentChangeRequest.Action.CREATE,
    )

    delete_request_files(change_request)
    change_request.delete()

    return HttpResponse(status=204)


# -------------------- Review ------------------------------------------
class EquipmentRequestReviewView(LoginRequiredMixin, UserPassesTestMixin, View):

    template_name = "equipment/equipment_request_review.html"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk):

        req = get_object_or_404(
            EquipmentChangeRequest,
            pk=pk,
            status=EquipmentChangeRequest.Status.PENDING
        )
 
        # You only have ONE form for equipment
        FormClass = EquipmentChangeRequestForm

        eq = req.equipment  # Might be None for CREATE requests

        def merged(field, default=""):
            if hasattr(req, field) and getattr(req, field):
                return getattr(req, field)
            if eq and hasattr(eq, field) and getattr(eq, field):
                return getattr(eq, field)
            return default

        initial = {
            "functional_location": merged("functional_location", None),
            "serial_number": merged("serial_number", ""),
            "manufacturer": merged("manufacturer", ""),
            "model": merged("model", ""),
            "note": merged("note", ""),
        }

        form = FormClass(initial=initial)

        return render(request, self.template_name, {"req": req, "form": form})


    def post(self, request, pk):

        req = get_object_or_404(EquipmentChangeRequest, pk=pk)
        action = request.POST.get("decision")

        form = EquipmentChangeRequestForm(request.POST, request.FILES)

        if not form.is_valid():
            messages.error(request, "Invalid form data.")
            return render(request, self.template_name, {"req": req, "form": form})

        # --- Update request object with reviewer edits ---
        for field, value in form.cleaned_data.items():
            setattr(req, field, value)

        req.save()

        # --- APPROVE or REJECT ---
        if action == "approve":
            req.approve_request(reviewer=request.user)
            messages.success(request, "Equipment request approved.")
            return redirect("accounts:dashboard")

        elif action == "reject":
            req.mark_rejected(reviewer=request.user)
            messages.warning(request, "Equipment request rejected.")
            return redirect("accounts:dashboard")

        return redirect("accounts:dashboard")
