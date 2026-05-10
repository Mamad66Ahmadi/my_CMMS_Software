# equipment/views.py

from django.views.generic import DetailView,TemplateView, CreateView, View
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages



from ..models import LocationTag, EquipmentDocument, Equipment, ObjectType, ObjectCriticality, ObjectCategory, Unit

from equipment.models import LocationTagChangeRequest

from equipment.forms import LocationTagRequestForm

# ----------------------------------------- Location Tag List ------------------------------
class LocationTagList(LoginRequiredMixin, TemplateView):
    template_name = "equipment/location_tag_list.html"
    redirect_field_name = "next"


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filters from GET
        filters = {
            'loc_tag': self.request.GET.get('loc_tag', '').strip(),
            'parent': self.request.GET.get('parent', '').strip(),
            'unit': self.request.GET.get('unit', '').strip(),
            'train': self.request.GET.get('train', '').strip(),
            'criticality': self.request.GET.get('criticality', '').strip(),
            'obj_type': self.request.GET.get('obj_type', '').strip(),
            'obj_category': self.request.GET.get('obj_category', '').strip(), 
            'is_active': self.request.GET.get('is_active', 'true'),

        }

        queryset = LocationTag.objects.all()

        # Filtering logic
        if filters['loc_tag']:
            queryset = queryset.filter(loc_tag__icontains=filters['loc_tag'])

        if filters['parent']:
            queryset = queryset.filter(parent__loc_tag__icontains=filters['parent'])

        if filters['unit']:
            queryset = queryset.filter(unit__unit_code__icontains=filters['unit'])

        if filters['train']:
            queryset = queryset.filter(train__icontains=filters['train'])

        if filters['criticality']:
            queryset = queryset.filter(obj_criticality__obj_crt_level__icontains=filters['criticality'])

        if filters['obj_type']:
            queryset = queryset.filter(obj_type__obj_type__icontains=filters['obj_type'])

        if filters['obj_category']:
            queryset = queryset.filter(obj_category__category_name__icontains=filters['obj_category'])
        if filters['is_active'] == "true":
            queryset = queryset.filter(is_active=True)

        # Sorting
        sort_by = self.request.GET.get('sort', 'loc_tag')
        sort_order = self.request.GET.get('order', 'asc')

        allowed_sort_fields = {
            'loc_tag': 'loc_tag',
            'parent': 'parent__loc_tag',
            'unit': 'unit__unit_code',
            'train': 'train',
            'long_tag': 'long_tag',
            'description': 'description',
            'obj_criticality': 'obj_criticality__obj_crt_level',
            'obj_type': 'obj_type__obj_type',
            'obj_category': 'obj_category__category_name',
            'is_active': 'is_active',
            'note': 'note',
            'mih_level': 'mih_level',
            'created_at': 'created_at',
            'created_by': 'created_by__username',
            'modified_at': 'modified_at',
            'modified_by': 'modified_by__username',

        }

        sort_field = allowed_sort_fields.get(sort_by, 'loc_tag')

        if sort_order == "desc":
            queryset = queryset.order_by(f"-{sort_field}")
        else:
            queryset = queryset.order_by(sort_field)

        # Pagination
        per_page = self.request.GET.get("per_page", "25")

        try:
            per_page = int(per_page)
        except ValueError:
            per_page = 25

        if per_page > 200:
            per_page = 200
        elif per_page <=10:
            per_page = 10

        paginator = Paginator(queryset, per_page)
        page_number = self.request.GET.get("page")
        location_tags = paginator.get_page(page_number)

        context["per_page"] = per_page


        context["location_tags"] = location_tags
        context["paginator"] = paginator
        context["page_obj"] = location_tags
        context["sort_by"] = sort_by
        context["sort_order"] = sort_order
        context["filters"] = filters
        context["total_location_tags"] = queryset.count()

        # Build sort_params WITHOUT sort or order
        param_list = []
        for key, value in filters.items():
            if value:
                param_list.append(f"{key}={value}")

        param_list.append(f"per_page={per_page}")


        context["sort_params"] = "&".join(param_list)

        params = self.request.GET.copy()
        params.pop("page", None)  # remove page so pagination can replace it
        context["query_params"] = params.urlencode()

  
        return context






class LocationTagDetail(LoginRequiredMixin, DetailView):
    model = LocationTag
    template_name = "equipment/location_tag_detail.html"
    context_object_name = "location_tag"

    slug_field = "loc_tag"
    slug_url_kwarg = "loc_tag"

    login_url = "/accounts/login/"
    redirect_field_name = "next"

    queryset = LocationTag.objects.select_related(
        "parent",
        "obj_criticality",
        "obj_type",
        "obj_category",
        "unit",
        "created_by",
        "modified_by",
    ).prefetch_related(
        "children",
        "installed_equipments",
        "installed_equipments__documents",
    )


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        tag = self.object

        context["children"] = tag.children.all()

        equipments = tag.installed_equipments.select_related(
            "created_by", "modified_by"
        ).prefetch_related("documents")

        context["equipments"] = equipments

        context["documents"] = EquipmentDocument.objects.filter(
            equipment__functional_location=tag
        ).select_related("equipment")

        context["history"] = tag.history.all()[:20]

        # 👉 NEW: latest 5 change requests for this tag
        context["change_requests"] = (
            LocationTagChangeRequest.objects
            .filter(location_tag=tag)
            .select_related("requested_by")
            .order_by("-requested_at")[:5]
        )

        # 👉 NEW: check if there's any pending request
        context["has_pending_request"] = (
            LocationTagChangeRequest.objects
            .filter(location_tag=tag, status=LocationTagChangeRequest.Status.PENDING)
            .exists()
        )


        return context
    




@login_required
def locationtag_autocomplete(request):
    q = request.GET.get("q", "")

    tags = LocationTag.objects.filter(
        loc_tag__istartswith=q.upper()).order_by("loc_tag")[:10]
        
    results = [
        {
            "id": tag.id,
            "text": f"{tag.loc_tag}"
        }
        for tag in tags
    ]

    return JsonResponse({"results": results})



class LocationTagUpdateRequestView(LoginRequiredMixin, CreateView):
    model = LocationTagChangeRequest
    form_class =  LocationTagRequestForm
    template_name = "equipment/location_tag_request_update_form.html"

    login_url = "/accounts/login/"
    redirect_field_name = "next"


    def dispatch(self, request, *args, **kwargs):
        self.tag = get_object_or_404(LocationTag, loc_tag=kwargs["loc_tag"])
        return super().dispatch(request, *args, **kwargs)

    def get_initial(self):
        # Pre‑populate the form with current values from the real tag
        tag = self.tag
        return {
            "loc_tag": tag.loc_tag,
            "parent": tag.parent,
            "description": tag.description,
            "long_tag": tag.long_tag,
            "obj_criticality": tag.obj_criticality,
            "obj_type": tag.obj_type,
            "obj_category": tag.obj_category,
            "unit": tag.unit,
            "train": tag.train,
            "note": tag.note,
            "mih_level": tag.mih_level,
        }

    def form_valid(self, form):

        # 1. Check for an existing pending request
        existing = LocationTagChangeRequest.objects.filter(
            location_tag=self.tag,
            status=LocationTagChangeRequest.Status.PENDING
        ).first()

        if existing:
            form.add_error(
                None,
                "There is already a pending change request for this tag. "
                "Please wait for it to be approved before submitting another."
            )
            return self.form_invalid(form)

        # --- FIX: Correct validation for loc_tag ---
        loc_tag = form.cleaned_data["loc_tag"]

        # Allow same value; forbid changing to an existing loc_tag
        if loc_tag != self.tag.loc_tag:
            if LocationTag.objects.filter(loc_tag=loc_tag).exists():
                form.add_error("loc_tag", "Another Location Tag with this code already exists.")
                return self.form_invalid(form)

        # 2. No pending request → create a new one
        req = form.save(commit=False)
        req.action = LocationTagChangeRequest.Action.UPDATE
        req.location_tag = self.tag
        req.requested_by = self.request.user

        # --- FIX: Make the request pending ---
        req.status = LocationTagChangeRequest.Status.PENDING

        # 3. Detect changed fields
        tag = self.tag
        changes = {}

        for field in (
            "loc_tag", "parent", "description", "long_tag",
            "obj_criticality", "obj_type", "obj_category",
            "unit", "train", "note", "mih_level"
        ):
            if field not in form.cleaned_data:
                continue
            old_value = getattr(tag, field, None)
            new_value = form.cleaned_data[field]
            if old_value != new_value:
                changes[field] = {
                    "old": str(old_value),
                    "new": str(new_value),
                }

        req.changes = changes

        # 4. Save the NEW request
        req.save()

        return redirect("equipment:location_tag_detail", loc_tag=self.tag.loc_tag)



class LocationTagCreateRequestView(LoginRequiredMixin, CreateView):
    model = LocationTagChangeRequest
    form_class = LocationTagRequestForm
    template_name = "equipment/location_tag_request_create_form.html"


    def form_valid(self, form):
        # Check if a tag with the same loc_tag already exists
        loc_tag = form.cleaned_data["loc_tag"]
        if LocationTag.objects.filter(loc_tag=loc_tag).exists():
            form.add_error("loc_tag", "A Location Tag with this code already exists.")
            return self.form_invalid(form)

        req = form.save(commit=False)
        req.action = LocationTagChangeRequest.Action.CREATE
        req.requested_by = self.request.user
        req.changes = {}  # no changes for creation
        req.status = LocationTagChangeRequest.Status.PENDING

        req.save()

        # ✅ Build success message with specifications
        messages.success(
            self.request,
            f"Your request for object tag: {req.loc_tag} has been submitted."
        )


        return redirect("equipment:location_tag_create_request")
    
#----------------------------------------------------------------------------------------------------

class LocationTagRemoveRequestView(LoginRequiredMixin, View):

    def get(self, request, loc_tag):
        tag = get_object_or_404(LocationTag, loc_tag=loc_tag)

        # Prevent duplication
        existing = LocationTagChangeRequest.objects.filter(
            location_tag=tag,
            status=LocationTagChangeRequest.Status.PENDING
        ).first()

        if existing:
            messages.error(request,
                           "There is already a pending request for this tag.")
            return redirect("equipment:location_tag_detail", loc_tag=loc_tag)

        # Create a remove request
        LocationTagChangeRequest.objects.create(
            action=LocationTagChangeRequest.Action.REMOVE,
            location_tag=tag,
            requested_by=request.user,
            loc_tag=tag.loc_tag,      # required model field
            parent=tag.parent,
            description=tag.description,
            long_tag=tag.long_tag,
            obj_criticality=tag.obj_criticality,
            obj_type=tag.obj_type,
            obj_category=tag.obj_category,
            unit=tag.unit,
            train=tag.train,
            note=tag.note,
            mih_level=tag.mih_level,
            changes={"action": "remove"},
        )

        messages.success(request,
                         "Remove request submitted successfully.")
        return redirect("equipment:location_tag_detail", loc_tag=loc_tag)



# ----------------------------------------------------------------------------------------------------
class LocationTagRequestReviewView(LoginRequiredMixin, UserPassesTestMixin, View):

    template_name = "equipment/location_tag_request_review.html"

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, pk):
        req = get_object_or_404(
            LocationTagChangeRequest,
            pk=pk,
            status=LocationTagChangeRequest.Status.PENDING
        )


        initial = {
            "loc_tag": req.loc_tag or getattr(req.location_tag, "loc_tag", ""),
            "description": req.description or getattr(req.location_tag, "description", ""),
            "long_tag": req.long_tag or getattr(req.location_tag, "long_tag", ""),
            "obj_criticality": req.obj_criticality or getattr(req.location_tag, "obj_criticality", None),
            "obj_type": req.obj_type or getattr(req.location_tag, "obj_type", None),
            "obj_category": req.obj_category or getattr(req.location_tag, "obj_category", None),
            "unit": req.unit or getattr(req.location_tag, "unit", None),
            "train": req.train or getattr(req.location_tag, "train", None),
            "note": req.note or getattr(req.location_tag, "note", ""),
            "mih_level": req.mih_level or getattr(req.location_tag, "mih_level", ""),
            "parent": req.parent or getattr(req.location_tag, "parent", None),
        }

        form = LocationTagRequestForm(initial=initial)

        return render(request, self.template_name, {"req": req, "form": form})


    def post(self, request, pk):
        req = get_object_or_404(LocationTagChangeRequest, pk=pk)

        action = request.POST.get("decision")



        form = LocationTagRequestForm(request.POST)

        if not form.is_valid():
            messages.error(request, "Invalid form data.")
            return render(request, self.template_name, {"req": req, "form": form})

        # Update the request object with reviewer edits
        for field, value in form.cleaned_data.items():
            setattr(req, field, value)

        req.save()

        # APPROVE
        if action == "approve":
            req.approve_request(reviewer=request.user)
            messages.success(request, "Request approved and applied.")
            return redirect("accounts:dashboard")

        # REJECT
        elif action == "reject":
            req.mark_rejected(reviewer=request.user)
            messages.warning(request, "Request rejected.")
            return redirect("accounts:dashboard")

        return redirect("accounts:dashboard")


class BulkLocationTagActionsView(LoginRequiredMixin,UserPassesTestMixin,View):

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser
    
    def post(self, request):

        ids = request.POST.getlist("selected_requests")
        action = request.POST.get("bulk_action")

        if not ids:
            messages.warning(request, "No requests selected.")
            return redirect("accounts:dashboard")

        qs = LocationTagChangeRequest.objects.filter(id__in=ids)
        count = 0

        for req in qs:
            try:
                if action == "approve":
                    req.approve_request(reviewer=request.user)
                elif action == "reject":
                    req.mark_rejected(reviewer=request.user)
                count += 1
            except Exception as e:
                messages.error(request, f"Error in request {req.id}: {e}")

        if action == "approve":
            messages.success(request, f"{count} request(s) approved.")
        elif action == "reject":
            messages.warning(request, f"{count} request(s) rejected.")

        return redirect("accounts:dashboard")

