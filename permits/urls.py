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
    PermitWorkflowTransitionView,
    PermitUpdateView,
    PermitPrintView,
    WorkShiftListView,
    WorkShiftDetailView,
    
)

from permits.views.permit_attachment_views import (
    PermitAttachmentCreateView,
    PermitAttachmentDeleteView,
    PermitAttachmentUpdateView,
    PermitAttachmentDownloadView,
)


from permits.views.permit_detail_views import (
    PermitWorkShiftCloseView,
    PermitWorkShiftCreateView,
    PermitWorkShiftSignoffView,
    PermitCloseoutSignoffView,
    PermitFireGasESDIsolateView,
    PermitFireGasESDDeisolateView,
)



app_name = "permits"


urlpatterns = [
    # -------------------------------------------------------------------------
    # Permit list / filters / export
    # -------------------------------------------------------------------------
    path("list/", PermitList.as_view(), name="permit_list",),
    path("work-shifts/", WorkShiftListView.as_view(), name="work_shift_list"),
    path("work-shifts/<int:pk>/", WorkShiftDetailView.as_view(), name="work_shift_detail"),
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
    path("<str:permit_number>/workflow/action/", PermitWorkflowTransitionView.as_view(), name="permit_workflow_action",),
    path("<str:permit_number>/edit/", PermitUpdateView.as_view(), name="permit_update",),
    path("<slug:permit_number>/work-shifts/<int:work_shift_id>/signoff/<str:role_code>/", PermitWorkShiftSignoffView.as_view(), name="permit_shift_signoff",),
    path("<slug:permit_number>/work-shifts/<int:work_shift_id>/close/", PermitWorkShiftCloseView.as_view(), name="permit_work_shift_close",),
    path("<slug:permit_number>/work-shifts/create/", PermitWorkShiftCreateView.as_view(), name="permit_work_shift_create",),
    path("<str:permit_number>/print/", PermitPrintView.as_view(), name="permit_print"),
    path(
        "<str:permit_number>/attachments/upload/",
        PermitAttachmentCreateView.as_view(),
        name="permit_attachment_upload",
    ),
    path(
        "<str:permit_number>/attachments/<uuid:attachment_id>/download/",
        PermitAttachmentDownloadView.as_view(),
        name="permit_attachment_download",
    ),
    path(
        "<str:permit_number>/attachments/<uuid:attachment_id>/edit/",
        PermitAttachmentUpdateView.as_view(),
        name="permit_attachment_update",
    ),
    path(
        "<str:permit_number>/attachments/<uuid:attachment_id>/delete/",
        PermitAttachmentDeleteView.as_view(),
        name="permit_attachment_delete",
    ),
    path("<str:permit_number>/closeout/<int:closeout_signoff_id>/sign/", PermitCloseoutSignoffView.as_view(), name="permit_closeout_signoff",),
    path("<str:permit_number>/fire-gas-esd/<int:item_id>/isolate/", PermitFireGasESDIsolateView.as_view(), name="permit_fire_gas_esd_isolate",),
    path("<str:permit_number>/fire-gas-esd/<int:item_id>/deisolate/", PermitFireGasESDDeisolateView.as_view(), name="permit_fire_gas_esd_deisolate",),
    path("<str:permit_number>/", PermitDetailView.as_view(), name="permit_detail"),
]
