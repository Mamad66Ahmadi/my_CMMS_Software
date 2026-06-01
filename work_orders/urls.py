from django.urls import path
from .views import FaultReportList, fault_report_detail_template

app_name = "work_orders"

urlpatterns = [
    path("fault-reports/", FaultReportList.as_view(), name="fault_report_list"),
    path("fault-reports/<int:pk>/detail/", fault_report_detail_template, name="fault_report_detail_template"),
]
