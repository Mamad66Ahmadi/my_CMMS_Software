from django.urls import path
from work_orders.views import (FaultReportList, fault_report_detail_template,FaultReportExportCSV, FaultReportCreate, FaultsByLocationPartial,FaultReportReviewView, FaultReportConvertView,
                               WorkOrderTasksEditorView, TaskFormPartialUpdateView)

from work_orders.views import WorkOrderList, WorkOrderExportCSV, work_order_detail_template,WorkOrderSearchView

app_name = "work_orders"

urlpatterns = [
    path("fault-reports/", FaultReportList.as_view(), name="fault_report_list"),
    path("fault-reports/<int:pk>/detail/", fault_report_detail_template, name="fault_report_detail_template"),
    path("fault-reports/export/csv/", FaultReportExportCSV.as_view(),name="fault_report_export_csv",),
    path("fault-reports/add/", FaultReportCreate.as_view(), name="fault_report_add"),
    path("fault-reports/existing-faults/", FaultsByLocationPartial.as_view(), name="fault_report_existing_faults_partial",),
    path("fault-reports/<int:pk>/review/",FaultReportReviewView.as_view(), name="fault_report_review",),
    path("fault-reports/<int:pk>/convert/",FaultReportConvertView.as_view(), name="fault_report_convert",),


    # Work Order List View
    path("search/", WorkOrderSearchView.as_view(), name="wo_search"),
    path("list/", WorkOrderList.as_view(), name="wo_list"),
    path("export/csv/", WorkOrderExportCSV.as_view(), name="wo_export_csv"),
    path("<int:pk>/detail-template/", work_order_detail_template, name="work_order_detail_template"),
    # 1. Main entrypoint: Load tabs and current WO tasks editor layout
    path('work-orders/<int:wo_id>/tasks-editor/', WorkOrderTasksEditorView.as_view(), name='wo_tasks_editor'),
    # 2. Combined AJAX view: GET to fetch form, POST to update it
    path('tasks/<int:task_id>/editor-action/', TaskFormPartialUpdateView.as_view(), name='task_editor_action'),
]
