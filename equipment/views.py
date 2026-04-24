# equipment/views.py

from django.shortcuts import render
from django.views.generic import ListView,DetailView,TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger



from .models import LocationTag, EquipmentDocument, Equipment







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

            'created_at': 'created_at',
            'created_by': 'created_by__username',
            'modified_at': 'modified_at',
            'modified_by': 'modified_by__username',
            'note': 'note',
            'mih_level': 'mih_level',
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
        context["sort_by"] = sort_by
        context["sort_order"] = sort_order
        context["filters"] = filters
        context["total_location_tags"] = queryset.count()

        # Build sort_params WITHOUT sort or order
        param_list = []
        for key, value in filters.items():
            if value:
                param_list.append(f"{key}={value}")

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

        # children location tags
        context["children"] = tag.children.all()

        # equipment installed at this location
        equipments = tag.installed_equipments.select_related(
            "created_by", "modified_by"
        ).prefetch_related("documents")

        context["equipments"] = equipments

        # all documents for this location (via equipment)
        context["documents"] = EquipmentDocument.objects.filter(
            equipment__functional_location=tag
        ).select_related("equipment")

        # history (django-simple-history)
        context["history"] = tag.history.all()[:20]


        return context
