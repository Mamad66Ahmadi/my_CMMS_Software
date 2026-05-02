# equipment/views/equipment_views.py
from django.core.paginator import Paginator
from django.views.generic import TemplateView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect,render
from django.urls import reverse_lazy, reverse
from django.forms import inlineformset_factory 
from django.db import transaction
from django.http import HttpResponse


from equipment.models.equipment_models import Equipment
from equipment.models.request_equipment_models import EquipmentChangeRequest, EquipmentDocumentChangeRequest

from equipment.forms.equioment_change_form import EquipmentChangeRequestForm, EquipmentDocumentChangeRequestForm, EquipmentDocumentChangeRequestFormSet



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

EquipmentDocumentChangeRequestFormSet = inlineformset_factory(
    EquipmentChangeRequest,
    EquipmentDocumentChangeRequest,
    form=EquipmentDocumentChangeRequestForm,
    extra=1,
    can_delete=True,
)


class EquipmentUpdateRequestView(LoginRequiredMixin, CreateView):
    model = EquipmentChangeRequest
    form_class = EquipmentChangeRequestForm
    template_name = "equipment/equipment_request_update_form.html"

    login_url = "/accounts/login/"
    redirect_field_name = "next"

    def dispatch(self, request, *args, **kwargs):
        # Get the equipment instance here
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

    # Override get_context_data to add the formset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if "doc_formset" not in context:
            context["doc_formset"] = EquipmentDocumentChangeRequestFormSet()

        context["equipment"] = self.equipment
        return context

    # Override form_valid to handle saving the formset

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()

        doc_formset = EquipmentDocumentChangeRequestFormSet(
            request.POST,
            request.FILES,
            instance=self.object,
        )

        if form.is_valid() and doc_formset.is_valid():
            return self.forms_valid(form, doc_formset)
        else:
            return self.forms_invalid(form, doc_formset)


    @transaction.atomic
    def forms_valid(self, form, doc_formset):
        # 1. Fetch the existing pending request (created by HTMX) or create a new one
        # We don't block here anymore; we just "take over" the existing draft
        self.object, created = EquipmentChangeRequest.objects.get_or_create(
            equipment=self.equipment,
            status=EquipmentChangeRequest.Status.PENDING,
            defaults={
                "requested_by": self.request.user,
                "action": EquipmentChangeRequest.Action.UPDATE
            }
        )

        # 2. Update the fields from the form into this instance
        # We use the form to update self.object
        updated_instance = form.save(commit=False)
        
        # Copy fields from form to our object
        self.object.functional_location = updated_instance.functional_location
        self.object.serial_number = updated_instance.serial_number
        self.object.manufacturer = updated_instance.manufacturer
        self.object.model = updated_instance.model
        self.object.note = updated_instance.note

        # 3. Detect changes (your existing logic)
        eq = self.equipment
        changes = {}
        change_fields = ["functional_location", "serial_number", "manufacturer", "model", "note"]

        for field in change_fields:
            old = getattr(eq, field, None)
            new = form.cleaned_data.get(field)
            if old != new:
                changes[field] = {"old": str(old), "new": str(new)}

        self.object.changes = changes
        self.object.save()

        # 4. Handle any REMAINING documents in the formset 
        # (Those the user didn't click "Upload Now" for)
        doc_formset.instance = self.object
        doc_formset.save()

        return redirect(self.get_success_url())

    def forms_invalid(self, form, doc_formset):
        return self.render_to_response(
            self.get_context_data(
                form=form,
                doc_formset=doc_formset,
            )
        )


    def get_success_url(self):
        return reverse_lazy("equipment:equipment_detail", kwargs={"pk": self.equipment.pk})






def upload_request_document(request, equipment_id):
    if request.method != "POST":
        return HttpResponse(status=405)


    equipment = get_object_or_404(Equipment, pk=equipment_id)

    uploaded_file = None
    file_key = None

    # Find the file input and its exact field name
    for key, value in request.FILES.items():
        if key.endswith("-file"):
            uploaded_file = value
            file_key = key
            break

    if not uploaded_file or not file_key:
        return HttpResponse("Missing file", status=400)

    # Extract the form index from something like:
    # equipmentdocumentchangerequest_set-0-file
    # -> equipmentdocumentchangerequest_set-0
    prefix_without_field = file_key.rsplit("-file", 1)[0]

    file_name = request.POST.get(f"{prefix_without_field}-file_name", "").strip()
    description = request.POST.get(f"{prefix_without_field}-description", "").strip()

    if not file_name:
        file_name = uploaded_file.name

    # If your model requires a parent change request, you must attach it here.
    # Example if you already have a pending change request:
    change_request, created = EquipmentChangeRequest.objects.get_or_create(
        equipment=equipment,
        status=EquipmentChangeRequest.Status.PENDING,
        defaults={"requested_by": request.user}
    )

    doc = EquipmentDocumentChangeRequest.objects.create(
        change_request=change_request,
        file=uploaded_file,
        file_name=file_name,
        description=description,
    )


    return render(request, "equipment/document_row.html", {"doc": doc})



def cancel_pending_request(request, equipment_id):

    if request.method != "DELETE":
        return HttpResponse(status=405)

    pending = EquipmentChangeRequest.objects.filter(
        equipment_id=equipment_id,
        requested_by=request.user,
        status=EquipmentChangeRequest.Status.PENDING
    ).first()

    if pending:
        if not pending.changes:   # only delete draft requests
            EquipmentDocumentChangeRequest.objects.filter(
                change_request=pending
            ).delete()

            pending.delete()

    return HttpResponse(
        f'<script>window.location="{reverse("equipment:equipment_detail", args=[equipment_id])}"</script>'
    )
