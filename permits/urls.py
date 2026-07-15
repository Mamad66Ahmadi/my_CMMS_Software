# permits/urls.py
from django.urls import path
from permits.views import PermitList,PermitExportCSV, PermitDetailView, PermitCreateView, permit_autocomplete, get_permit_data

app_name = "permits"

urlpatterns = [
    path("list/", PermitList.as_view(), name="permit_list"),
    path("export/csv/", PermitExportCSV.as_view(), name="permit_export_csv"),
    path("create/", PermitCreateView.as_view(), name="permit_create"),
    path("autocomplete/permits/", permit_autocomplete, name="permit_autocomplete"),
    path('get-permit-data/', get_permit_data, name='get_permit_data'),

    path("<str:permit_number>/", PermitDetailView.as_view(), name="permit_detail"),

]
