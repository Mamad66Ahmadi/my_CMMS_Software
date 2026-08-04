# permits/admin/permit_workflow_transition_admin.py
from django.contrib import admin

from permits.admin.base_admin import AUDIT_FIELDSET, TimeStampedAdmin
from permits.models.approval_models import PermitApprovalRoleChoices
from permits.models.workflow_models import PermitWorkflowTransition


@admin.register(PermitApprovalRoleChoices)
class PermitApprovalRoleChoicesAdmin(TimeStampedAdmin):
    """
    Lookup Admin for Role Choices. Inherits from BaseLookupAdmin
    which provides standardized search_fields, list_display, and Audit info.
    """
    search_fields = (
        "code",
        "name",
    )

    list_display = (
        "code",
        "name",
        "description",
    )


@admin.register(PermitWorkflowTransition)
class PermitWorkflowTransitionAdmin(TimeStampedAdmin):
    list_display = (
        "workflow",
        "from_step",
        "to_step",
        "decision",
        "role",
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
        "role",
    )

    list_select_related = (
        "workflow",
        "from_step",
        "to_step",
        "role",
    )

    fieldsets = (
        (
            "Transition Definition",
            {
                "fields": (
                    "workflow",
                    "from_step",
                    "to_step",
                    "decision",
                    "role",
                )
            },
        ),
        AUDIT_FIELDSET,
    )
