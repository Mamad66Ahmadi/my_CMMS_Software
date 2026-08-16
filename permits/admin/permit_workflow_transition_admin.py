# permits/admin/permit_workflow_transition_admin.py
from django.contrib import admin

from permits.admin.base_admin import AUDIT_FIELDSET, TimeStampedAdmin
from permits.models.approval_models import PermitApprovalRoleChoices
from permits.models.workflow_models import (
    PermitWorkflowCondition,
    PermitWorkflowTransition,
)


@admin.register(PermitApprovalRoleChoices)
class PermitApprovalRoleChoicesAdmin(TimeStampedAdmin):
    list_display = (
        "code",
        "name",
        "required_qualification",
        "department_scope",
        "unit_scope",
        "is_active",
        "created_at",
        "modified_at",
    )

    list_filter = (
        "department_scope",
        "unit_scope",
        "required_qualification",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "description",
        "required_qualification__code",
        "required_qualification__name",
    )

    list_select_related = (
        "required_qualification",
    )

    fieldsets = (
        (
            "Role Definition",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "required_qualification",
                ),
            },
        ),
        (
            "Responsibility Scope",
            {
                "fields": (
                    "department_scope",
                    "unit_scope",
                ),
                "description": (
                    "Department scope is used for roles such as Work Supervisor. "
                    "Unit scope is used for roles such as Area Authority, "
                    "Area Supervisor, and Area Operator."
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                ),
            },
        ),
        AUDIT_FIELDSET,
    )


class PermitWorkflowConditionInline(admin.TabularInline):
    model = PermitWorkflowCondition
    extra = 1
    fields = (
        "operand",
        "field_path",
        "operator",
        "expected_value",
        "description",
    )


@admin.register(PermitWorkflowTransition)
class PermitWorkflowTransitionAdmin(TimeStampedAdmin):
    inlines = (PermitWorkflowConditionInline,)

    list_display = (
        "workflow",
        "from_step",
        "to_step",
        "decision",
        "role",
        "created_at",
        "modified_at",
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
        "role__code",
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
                ),
            },
        ),
        AUDIT_FIELDSET,
    )
