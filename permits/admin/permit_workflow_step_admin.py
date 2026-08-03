from django.contrib import admin

from permits.models.permit_models import PermitWorkflowStep


@admin.register(PermitWorkflowStep)
class PermitWorkflowStepAdmin(admin.ModelAdmin):
    list_display = (
        "workflow",
        "step_number",
        "title",
        "is_start",
        "is_terminal",
        "is_active",
        "created_at",
    )

    list_filter = (
        "workflow",
        "is_start",
        "is_terminal",
        "is_active",
    )

    search_fields = (
        "workflow__name",
        "title",
        "description",
    )

    ordering = (
        "workflow",
        "step_number",
    )

    autocomplete_fields = (
        "workflow",
    )

    readonly_fields = (
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

    fieldsets = (
        (
            "Step Definition",
            {
                "fields": (
                    "workflow",
                    "step_number",
                    "title",
                    "description",
                )
            },
        ),
        (
            "Workflow Behavior",
            {
                "fields": (
                    "is_start",
                    "is_terminal",
                    "is_active",
                )
            },
        ),
        (
            "Audit Information",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "created_by",
                    "modified_at",
                    "modified_by",
                ),
            },
        ),
    )
