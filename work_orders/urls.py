from django.urls import path
from work_orders.views.fr_views import FaultReportList, fault_report_detail_template,FaultReportExportCSV, FaultReportCreate, FaultsByLocationPartial

app_name = "work_orders"

urlpatterns = [
    path("fault-reports/", FaultReportList.as_view(), name="fault_report_list"),
    path("fault-reports/<int:pk>/detail/", fault_report_detail_template, name="fault_report_detail_template"),
    path("fault-reports/export/csv/", FaultReportExportCSV.as_view(),name="fault_report_export_csv",),
    path("fault-reports/add/", FaultReportCreate.as_view(), name="fault_report_add"),
    path("fault-reports/existing-faults/", FaultsByLocationPartial.as_view(), name="fault_report_existing_faults_partial",),
]
