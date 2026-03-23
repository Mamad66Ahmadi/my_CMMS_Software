from django.urls import path, include
from . import views

app_name = "equipment"

urlpatterns = [
    path('tag/', views.Taglist.as_view(), name="tag_list"),
    path('tag/<str:loc_tag>/', views.TagDetailView.as_view(), name="tag_detail"),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('api/v1/', include('equipment.api.v1.urls')),
    path('fvb/', views.tagView, name='function-based-view'),
]