from django.contrib import admin
from django.utils.html import format_html

from work_orders.models.fault_report_models import FaultReport


@admin.register(FaultReport)
class FaultReportAdmin(admin.ModelAdmin):
    list_display = (
        "report_number",
        "status_badge",
        "location_tag",
        "equipment",
        "priority",
        "reported_by",
        "reported_department",
        "executing_department",
        "reported_at",
        "reviewed_by",
        "planner",
    )

    list_filter = (
        "status",
        "priority",
        "symptom",
        "reported_department",
        "executing_department",
        "reported_at",
        "reviewed_at",
        "planner_reviewed_at",
    )

    search_fields = (
        "report_number",
        "directive",
        "fault_desc",
        "location_tag__loc_tag",
        "equipment__serial_number",
        "reported_by__username",
        "reported_by__first_name",
        "reported_by__last_name",
        "reviewed_by__username",
        "reviewed_by__first_name",
        "reviewed_by__last_name",
        "planner__username",
        "planner__first_name",
        "planner__last_name",
        "review_comment",
        "executing_department__name",
    )

    autocomplete_fields = (
        "location_tag",
        "equipment",
        "priority",
        "symptom",
        "reported_by",
        "reported_department",
        "executing_department",
        "reviewed_by",
        "planner",
    )

    readonly_fields = (
        "report_number",
        "reported_at",
        "reviewed_at",
        "planner_reviewed_at",
    )

    list_select_related = (
        "location_tag",
        "equipment",
        "priority",
        "symptom",
        "reported_by",
        "reported_department",
        "executing_department", 
        "reviewed_by",
        "planner",
    )

    date_hierarchy = "reported_at"
    ordering = ("-reported_at",)

    fieldsets = (
        ("Basic Information", {
            "fields": (
                "report_number",
                "status",
                "directive",
                "fault_desc",
            )
        }),
        ("Equipment / Location", {
            "fields": (
                "location_tag",
                "equipment",
            )
        }),
        ("Classification", {
            "fields": (
                "priority",
                "symptom",
                 "executing_department",
            )
        }),
        ("Reporter Information", {
            "fields": (
                "reported_by",
                "reported_department",
                "reported_at",
            )
        }),
        ("Supervisor Review", {
            "fields": (
                "reviewed_by",
                "reviewed_at",
                "review_comment",
            )
        }),
        ("Planner Action", {
            "fields": (
                "planner",
                "planner_reviewed_at",
            )
        }),
    )

    def status_badge(self, obj):
        colors = {
            "SUBMITTED": "#f0ad4e",   # orange
            "APPROVED": "#5bc0de",    # blue
            "REJECTED": "#d9534f",    # red
            "CONVERTED": "#5cb85c",   # green
        }
        color = colors.get(obj.status, "#777")
        return format_html(
            '<span style="color: white; background-color: {}; padding: 3px 8px; border-radius: 8px;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_badge.short_description = "Status"
