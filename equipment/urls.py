from django.urls import path
from django.views.generic import TemplateView
from . import views

app_name = "equipment"

urlpatterns = [
    path('tag-details/', TemplateView.as_view(template_name="website/index.html")),
    path('tag/', views.Taglist.as_view(), name="tag-list"),

    path('fvb/', views.tagView, name='function-based-view')
]