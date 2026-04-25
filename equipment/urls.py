# equipment/urls.py

from django.urls import path, include
from . import views

app_name = "equipment"

urlpatterns = [

    path('tag/', views.LocationTagList.as_view(), name = "location_tag_list"),
    path("tag/<path:loc_tag>/", views.LocationTagDetail.as_view(),name="location_tag_detail",),
]