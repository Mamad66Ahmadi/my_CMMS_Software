# daily_reports/urls.py

from django.urls import path
from .views import dr_list_views,dr_create_views

app_name = "daily_reports"

urlpatterns = [
    path("", dr_list_views.DailyReportList.as_view(), name="report_list"),
    path("export/", dr_list_views.DailyReportExportCSV.as_view(), name="report_export_csv"),
    path("create/", dr_create_views.ReportCreateView.as_view(), name="report_create"),
    path("reports/detail-template/", dr_list_views.report_detail_template, name="report_detail_template"),
    path('test-autocomplete/', dr_create_views.DailyReportPortalView.as_view(), name='report_portal'),
    path('create/', dr_create_views.ReportCreateView.as_view(), name='report_create'),
    path('recent-reports/', dr_create_views.RecentReportsPartialView.as_view(), name='recent_reports'),
    path('details/<int:pk>/', dr_create_views.ReportDetailJsonView.as_view(), name='report_details'),
        


]
