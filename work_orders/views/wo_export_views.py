# work_orders/views/wo_export_views.py

import csv
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.views import View
from django.db.models import Count

# Import services and configs
from work_orders.services.wo_filter_service import get_filtered_work_orders
from work_orders.services.wo_sorting import WORK_ORDER_EXPORT_SORT_FIELDS, get_sort_field

class WorkOrderExportCSV(LoginRequiredMixin, View):
    def get(self, request):
        # Apply filtering
        queryset, filters = get_filtered_work_orders(request)
        queryset = queryset.annotate(task_count=Count("tasks")) # Add task count for export

        # Apply sorting using the sorting service
        sort_by_param = request.GET.get("sort", "-reported_at")
        sort_field = get_sort_field(sort_by_param, WORK_ORDER_EXPORT_SORT_FIELDS)
        queryset = queryset.order_by(sort_field, "-id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="work_orders.csv"'
        response.write("\ufeff") # UTF-8 BOM for Excel compatibility

        writer = csv.writer(response)

        # CSV Header Row
        writer.writerow([
            "WO Number", "Tasks Count", "Status", "Fault Report", "Location Tag",
            "Parent Tag", "Unit", "Train", "Equipment Serial", "Priority", "Symptom",
            "Project Code", "Detection Method", "Work Type", "Reported By",
            "Reported Department", "Reported At", "Modified By", "Modified At",
            "Directive", "Fault Desc", "Task Summary",
        ])

        # CSV Data Rows
        for wo in queryset:
            writer.writerow([
                wo.wo_number or "",
                wo.task_count or 0,
                wo.get_status_display() if wo.status else "",
                wo.fault_report.report_number if wo.fault_report else "",
                wo.location_tag.loc_tag if wo.location_tag else "",
                wo.location_tag.parent.loc_tag if wo.location_tag and wo.location_tag.parent else "",
                wo.location_tag.unit.unit_code if wo.location_tag and wo.location_tag.unit else "",
                wo.location_tag.train if wo.location_tag and wo.location_tag.train is not None else "",
                wo.equipment.serial_number if wo.equipment else "",
                wo.priority.priority_level if wo.priority else "",
                wo.symptom.symptom_code if wo.symptom else "",
                wo.project_code.project_code if wo.project_code else "",
                wo.detection_method.detection_code if wo.detection_method else "",
                wo.work_type.work_type_code if wo.work_type else "",
                wo.reported_by.username if wo.reported_by else "",
                wo.reported_department.name if wo.reported_department else "",
                wo.reported_at.strftime("%Y-%m-%d %H:%M") if wo.reported_at else "",
                wo.modified_by.username if wo.modified_by else "",
                wo.modified_at.strftime("%Y-%m-%d %H:%M") if wo.modified_at else "",
                wo.directive or "",
                wo.fault_desc or "",
                wo.task_status_summary or "",
            ])

        return response
