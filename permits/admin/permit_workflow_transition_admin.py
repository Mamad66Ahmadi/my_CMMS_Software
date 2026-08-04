from django.contrib import admin

from permits.models.workflow_models import PermitWorkflowTransition


@admin.register(PermitWorkflowTransition)
class PermitWorkflowTransitionAdmin(admin.ModelAdmin):
    list_display = (
        "workflow",
        "from_step",
        "decision",
        "role",
        "to_step",
        "created_at",
    )

    list_filter = (
        "workflow",
        "decision",
        "role",
    )

    search_fields = (
        "workflow__name",
        "from_step__title",
        "to_step__title",
        "role__name",
    )

    autocomplete_fields = (
        "workflow",
        "from_step",
        "to_step",
    )

    list_select_related = (
        "workflow",
        "from_step",
        "to_step",
        "role",
    )

    readonly_fields = (
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

    fieldsets = (
        (
            "Transition Definition",
            {
                "fields": (
                    "workflow",
                    "from_step",
                    "decision",
                    "role",
                    "to_step",
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
