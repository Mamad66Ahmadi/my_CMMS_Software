from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils import timezone
from work_orders.models.fault_report_models import FaultReport, FaultReportStatus

@admin.register(FaultReport)
class FaultReportAdmin(admin.ModelAdmin):
    # 1. List Display
    list_display = (
        "report_number",
        "status_badge",
        "location_tag",
        "equipment",
        "priority",
        "executing_department",
        "reported_by",
        "reported_at",
    )

    # 2. Filtering and Search
    list_filter = ("status", "priority", "reported_department", "executing_department", "reported_at")
    search_fields = (
        "report_number", "directive", "fault_desc", 
        "location_tag__loc_tag", "equipment__serial_number"
    )
    autocomplete_fields = (
        "location_tag", "equipment", "priority", "symptom", 
        "project_code", "detection_method", "work_type", 
        "reported_by", "reported_department", "executing_department", 
        "reviewed_by", "planner"
    )

    # 3. Read-only Logic
    def get_readonly_fields(self, request, obj=None):
        # Base readonly fields for everyone
        readonly = ["report_number", "reported_at", "reviewed_at", "planner_reviewed_at"]
        
        if obj:
            # If CONVERTED, lock everything
            if obj.status == FaultReportStatus.CONVERTED:
                return [f.name for f in self.model._meta.fields]
            
            # If APPROVED, hide some reporter fields to keep data integrity
            if obj.status == FaultReportStatus.APPROVED:
                readonly += ["reported_by", "reported_department", "directive", "equipment"]
        
        return readonly

    # 4. Status Badge Helper
    def status_badge(self, obj):
        colors = {
            "SUBMITTED": "#f0ad4e",   # Orange
            "APPROVED": "#17a2b8",    # Teal/Blue
            "REJECTED": "#dc3545",    # Red
            "CONVERTED": "#28a745",   # Green
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: white; background-color: {}; padding: 4px 10px; '
            'border-radius: 12px; font-weight: bold; font-size: 0.85em;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = "Status"

    # 5. Admin Actions (Workflow Shortcuts)
    actions = ['batch_approve', 'batch_reject', 'batch_convert']

    def batch_approve(self, request, queryset):
        count = 0
        for report in queryset.filter(status=FaultReportStatus.SUBMITTED):
            report.approve(user=request.user)
            count += 1
        self.message_user(request, f"{count} reports approved successfully.")
    batch_approve.short_description = "Mark selected as Approved"

    def batch_reject(self, request, queryset):
        count = 0
        for report in queryset.filter(status__in=[FaultReportStatus.SUBMITTED, FaultReportStatus.APPROVED]):
            report.reject(user=request.user, comment="Rejected via bulk action.")
            count += 1
        self.message_user(request, f"{count} reports rejected.")
    batch_reject.short_description = "Mark selected as Rejected"

    def batch_convert(self, request, queryset):
        count = 0
        for report in queryset.filter(status=FaultReportStatus.APPROVED):
            try:
                report.mark_converted(user=request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f"Error converting {report.report_number}: {str(e)}", level=messages.ERROR)
        self.message_user(request, f"{count} reports converted to Work Orders.")
    batch_convert.short_description = "Convert selected to Work Orders"

    # 6. Fieldsets
    fieldsets = (
        ("General Information", {
            "fields": ("report_number", "status", "directive", "fault_desc")
        }),
        ("Technical Details", {
            "fields": (("equipment", "location_tag"), "parent_work_order_number")
        }),
        ("Classification", {
            "fields": (
                ("priority", "symptom"), 
                ("work_type", "detection_method"),
                ("project_code", "executing_department")
            )
        }),
        ("Audit Trail", {
            "fields": (
                ("reported_by", "reported_department", "reported_at"),
                ("reviewed_by", "reviewed_at"),
                ("planner", "planner_reviewed_at"),
                "review_comment"
            )
        }),
    )

    # Optimization
    list_select_related = (
        "location_tag", "equipment", "priority", "reported_by", 
        "reported_department", "executing_department"
    )
