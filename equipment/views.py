from django.shortcuts import render
from django.views.generic import ListView
from .models import LocationTag



# Create your views here.
class Taglist(ListView):
    model = LocationTag
    template_name = 'equipment/tag_list.html'  # Point to your specific template
    context_object_name = 'tags'  # This allows you to use {% for tag in tags %} in the template
    paginate_by = 50  # Optional: Adds pagination (20 items per page)
    ordering = ['loc_tag']


# function based view function
def tagView(request):
    return render(request, 'website/index.html')