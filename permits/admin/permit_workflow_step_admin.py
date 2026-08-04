# permits/admin/permit_workflow_step_admin.py
from django.contrib import admin

from permits.admin.base_admin import AUDIT_FIELDSET, TimeStampedAdmin
from permits.models.workflow_models import PermitWorkflowStep


@admin.register(PermitWorkflowStep)
class PermitWorkflowStepAdmin(TimeStampedAdmin):
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
        AUDIT_FIELDSET,
    )
