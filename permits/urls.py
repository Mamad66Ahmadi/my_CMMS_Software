# permits/urls.py
from django.urls import path
from permits.views import PermitList,PermitExportCSV, PermitDetailView

app_name = "permits"

urlpatterns = [
    path("list/", PermitList.as_view(), name="permit_list"),
    path("export/csv/", PermitExportCSV.as_view(), name="permit_export_csv"),
    path("<str:permit_number>/", PermitDetailView.as_view(), name="permit_detail"),
]
