from django.contrib import admin

from permits.models.permit_models import (
    PermitWorkflow,
    PermitWorkflowStep,
)


class PermitWorkflowStepInline(admin.TabularInline):
    """
    Manage steps on the Permit Workflow edit page.

    This is an inline only; it does NOT register PermitWorkflowStep again.
    """

    model = PermitWorkflowStep
    extra = 1
    fields = (
        "step_number",
        "title",
        "description",
        "is_start",
        "is_terminal",
        "is_active",
    )
    ordering = ("step_number",)
    show_change_link = True


@admin.register(PermitWorkflow)
class PermitWorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "version",
        "is_active",
        "created_at",
        "modified_at",
    )

    list_filter = (
        "is_active",
        "created_at",
        "modified_at",
    )

    search_fields = (
        "name",
    )

    ordering = (
        "name",
        "-version",
    )

    readonly_fields = (
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

    fieldsets = (
        (
            "Workflow Definition",
            {
                "fields": (
                    "name",
                    "version",
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

    inlines = (
        PermitWorkflowStepInline,
    )



