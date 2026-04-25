# equipment/urls.py

from django.urls import path, include
from . import views

app_name = "equipment"

urlpatterns = [

    path('tag/', views.LocationTagList.as_view(), name = "location_tag_list"),
    path("tag/<path:loc_tag>/", views.LocationTagDetail.as_view(),name="location_tag_detail",),
    path("tag-modification/<path:loc_tag>/", views.LocationTagUpdateRequestView.as_view(),name="location_tag_update_request",),
    path("locationtag-autocomplete/",views.locationtag_autocomplete,name="locationtag_autocomplete"),
]