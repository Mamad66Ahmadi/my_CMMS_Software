# daily_reports/urls.py

from django.urls import path
from .views import dr_list_views,dr_create_views

app_name = "daily_reports"

urlpatterns = [
    path("", dr_list_views.DailyReportList.as_view(), name="report_list"),
    path("export/", dr_list_views.DailyReportExportCSV.as_view(), name="report_export_csv"),
    path("create/", dr_create_views.ReportCreateView.as_view(), name="report_create"),
    path("reports/detail-template/", dr_list_views.report_detail_template, name="report_detail_template"),


]
