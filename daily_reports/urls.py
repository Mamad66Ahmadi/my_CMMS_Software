# daily_reports/urls.py

from django.urls import path
from .views import DailyReportList, DailyReportExportCSV

app_name = "daily_reports"

urlpatterns = [
    path("", DailyReportList.as_view(), name="report_list"),
    path("export/", DailyReportExportCSV.as_view(), name="report_export_csv"),
]
