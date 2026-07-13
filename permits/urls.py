# permits/urls.py
from django.urls import path
from permits.views.permit_list_views import PermitList,PermitExportCSV

app_name = "permits"

urlpatterns = [
    path("list/", PermitList.as_view(), name="permit_list"),
    path("export/csv/", PermitExportCSV.as_view(), name="permit_export_csv"),
]
