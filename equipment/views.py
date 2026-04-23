# equipment/views.py

from django.shortcuts import render
from django.views.generic import ListView,DetailView,TemplateView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger


from django.db.models import F, OrderBy


from .models import LocationTag



class Taglist(LoginRequiredMixin, ListView):
    model = LocationTag
    template_name = 'equipment/tag_list.html'
    context_object_name = 'tags'
    paginate_by = 20
    ordering = ['loc_tag']

    def get_queryset(self):
        queryset = super().get_queryset()
        
        loc_tag = self.request.GET.get('loc_tag', '').strip()
        if loc_tag:
            queryset = queryset.filter(loc_tag__icontains=loc_tag)
        
        parent = self.request.GET.get('parent', '').strip()
        if parent:
            queryset = queryset.filter(parent__loc_tag__icontains=parent)
        
        train = self.request.GET.get('train', '').strip()
        if train:
            queryset = queryset.filter(train__icontains=train)
        
        unit_code = self.request.GET.get('unit_code', '').strip()
        if unit_code:
            queryset = queryset.filter(unit__unit_code__icontains=unit_code)
        
        obj_type = self.request.GET.get('obj_type', '').strip()
        if obj_type:
            queryset = queryset.filter(obj_type__obj_type__icontains=obj_type)
        
        return queryset
    



class TagDetailView(LoginRequiredMixin,DetailView):
    model = LocationTag
    template_name = 'equipment/tag_detail.html'
    
    def get_object(self, queryset=None):
        # Get loc_tag from URL instead of pk
        loc_tag = self.kwargs.get('loc_tag')
        return get_object_or_404(self.model, loc_tag=loc_tag)

from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login



class RegisterView(CreateView):
    form_class = UserCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        return super().form_valid(form)

# function based view function
def tagView(request):
    return render(request, 'website/index.html')




# ----------------------------------------- Location Tag List ------------------------------
class LocationTagList(TemplateView):
    template_name = "equipment/location_tag_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Filters from GET
        filters = {
            'loc_tag': self.request.GET.get('search', '').strip(),
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
        }

        sort_field = allowed_sort_fields.get(sort_by, 'loc_tag')

        if sort_order == "desc":
            queryset = queryset.order_by(f"-{sort_field}")
        else:
            queryset = queryset.order_by(sort_field)

        # Pagination
        paginator = Paginator(queryset, 25)
        page_number = self.request.GET.get("page")
        location_tags = paginator.get_page(page_number)

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

        return context
