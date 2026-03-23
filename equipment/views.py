from django.shortcuts import render
from django.views.generic import ListView,DetailView
from django.shortcuts import get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin

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