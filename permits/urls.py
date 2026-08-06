# permits/urls.py

from django.urls import path

from permits.views import (
    PermitList,
    PermitExportCSV,
    PermitFilterFavoriteSaveView,
    PermitFilterFavoriteDeleteView,
    permit_autocomplete,
    get_permit_data,
    PISQualificationListView,
    AddPISQualificationView,
    PermitCreateView,
    PermitDetailView,
)


app_name = "permits"


urlpatterns = [
    # -------------------------------------------------------------------------
    # Permit list / filters / export
    # -------------------------------------------------------------------------
    path("list/", PermitList.as_view(), name="permit_list",),
    path("list/export/csv/", PermitExportCSV.as_view(), name="permit_export_csv",),
    # -------------------------------------------------------------------------
    # Saved filter favorites
    # -------------------------------------------------------------------------
    path("list/favorites/save/", PermitFilterFavoriteSaveView.as_view(), name="permit_filter_favorite_save",),
    path("list/favorites/<int:pk>/delete/", PermitFilterFavoriteDeleteView.as_view(), name="permit_filter_favorite_delete",),
    # -------------------------------------------------------------------------
    # Permit AJAX / autocomplete helpers
    # -------------------------------------------------------------------------
    path("autocomplete/permits/", permit_autocomplete, name="permit_autocomplete",),
    path("get-permit-data/", get_permit_data, name="get_permit_data",),
    # -------------------------------------------------------------------------
    # PIS qualifications
    # -------------------------------------------------------------------------
    path("pis-holders/", PISQualificationListView.as_view(), name="pis_holders",),
    path("pis-holders/add/", AddPISQualificationView.as_view(), name="add_pis",),
    # -------------------------------------------------------------------------
    # Permit Detail / Create
    # -------------------------------------------------------------------------
    path("create/", PermitCreateView.as_view(), name="permit_create"),
    path("<str:permit_number>/", PermitDetailView.as_view(), name="permit_detail"),
]
