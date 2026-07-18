# permits/urls.py
from django.urls import path
from permits.views import (PermitList,PermitExportCSV, PermitDetailView, PermitCreateView,
                           permit_autocomplete, get_permit_data, PISQualificationListView,
                           AddPISQualificationView, PermitFilterFavoriteDeleteView, PermitFilterFavoriteSaveView)

app_name = "permits"

urlpatterns = [
    path("list/", PermitList.as_view(), name="permit_list"),
    path("permits/favorites/save/", PermitFilterFavoriteSaveView.as_view(), name="permit_filter_favorite_save"),
    path("permits/favorites/<int:pk>/delete/", PermitFilterFavoriteDeleteView.as_view(), name="permit_filter_favorite_delete"),
    path("export/csv/", PermitExportCSV.as_view(), name="permit_export_csv"),
    path("create/", PermitCreateView.as_view(), name="permit_create"),
    path("autocomplete/permits/", permit_autocomplete, name="permit_autocomplete"),
    path('get-permit-data/', get_permit_data, name='get_permit_data'),

    path("pis-holders/",PISQualificationListView.as_view(), name="pis_holders",),
    path("pis-holders/add/", AddPISQualificationView.as_view(), name="add_pis"),


    path("<str:permit_number>/", PermitDetailView.as_view(), name="permit_detail"),

]
