# equipment/urls.py

from django.urls import path, include
from .views import location_tag_views, equipment_views

app_name = "equipment"

urlpatterns = [

    path('tag/', location_tag_views.LocationTagList.as_view(), name = "location_tag_list"),
    path("tag/<path:loc_tag>/", location_tag_views.LocationTagDetail.as_view(),name="location_tag_detail",),
    path("tag-modification/<path:loc_tag>/", location_tag_views.LocationTagUpdateRequestView.as_view(),name="location_tag_update_request",),
    path("locationtag-autocomplete/",location_tag_views.locationtag_autocomplete,name="locationtag_autocomplete"),
    path("tag-creation/",location_tag_views.LocationTagCreateRequestView.as_view(),name="location_tag_create_request",),
    path("tag-remove/<path:loc_tag>", location_tag_views.LocationTagRemoveRequestView.as_view(), name="location_tag_request_remove",),
    path("request-confirmation/<int:pk>/", location_tag_views.LocationTagRequestReviewView.as_view(), name="location_tag_request_review",),
    path("requests/location-tags/bulk/",location_tag_views.BulkLocationTagActionsView.as_view(),name="bulk_location_tag_actions",),

    path("equipment/", equipment_views.EquipmentList.as_view(), name="equipment_list"),
    path("equipment/<int:pk>/", equipment_views.EquipmentDetail.as_view(), name="equipment_detail"),
    path("equipment-modification/<int:pk>/", equipment_views.EquipmentUpdateRequestView.as_view(), name="equipment_update_request"),
    path("equipment/<int:equipment_id>/upload-document/",equipment_views.upload_request_document,name="upload_request_document",),
    path("equipment/document/<int:pk>/delete/",equipment_views.delete_request_document,name="delete_request_document",),
    path("request/update/<int:request_id>/cancel/",equipment_views.cancel_update_request,name="cancel_update_request",),
    path("equipment/request/create/",equipment_views.EquipmentCreateRequestView.as_view(),name="equipment_request_create",),
    path("equipment/request/<int:request_id>/upload-document/",equipment_views.upload_create_request_document,name="upload_create_request_document",),
    path("equipment/request/<int:request_id>/cancel/",equipment_views.cancel_create_request,name="cancel_create_request",),
    path("equipment/create/abandon/<int:request_id>/",equipment_views.abandon_create_request,name="abandon_create_request",),
    path("equipment-request/<int:pk>/review/",equipment_views.EquipmentRequestReviewView.as_view(),name="equipment_request_review",),
]
