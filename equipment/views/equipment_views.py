# equipment/views/equipment_views.py
from django.core.paginator import Paginator
from django.views.generic import TemplateView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404


from equipment.models.equipment_models import Equipment



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

        # Example: any child objects or reverse lookups could be added here if needed
        # context["maintenance_logs"] = equipment.maintenancelog_set.all()

        # History or recent changes (if using simple_history or audit model)
        if hasattr(equipment, "history"):
            context["history"] = equipment.history.all()[:20]

        return context
