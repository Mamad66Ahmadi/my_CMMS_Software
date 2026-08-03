from django.contrib import admin

from permits.admin.common import AuditAdminMixin
from permits.models import (
    PermitApprovalRoleChoices,
    PermitWorkflow,
    PermitWorkflowCondition,
    PermitWorkflowStep,
    PermitWorkflowTransition,
)


class WorkflowStepInline(admin.TabularInline):
    model = PermitWorkflowStep
    extra = 0
    fields = ("step_number", "title", "is_start", "is_terminal")
    ordering = ("step_number",)
    show_change_link = True


@admin.register(PermitWorkflow)
class PermitWorkflowAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("name", "version", "modified_at")
    search_fields = ("name",)
    ordering = ("name", "-version")
    inlines = (WorkflowStepInline,)


@admin.register(PermitApprovalRoleChoices)
class PermitApprovalRoleChoicesAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("code", "name", "is_active", "modified_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")
    ordering = ("code",)


@admin.register(PermitWorkflowStep)
class PermitWorkflowStepAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "workflow",
        "step_number",
        "title",
        "is_start",
        "is_terminal",
    )
    list_filter = ("is_start", "is_terminal")
    search_fields = ("workflow__name", "title", "description")
    autocomplete_fields = ("workflow",)
    ordering = ("workflow", "step_number")


class WorkflowConditionInline(admin.TabularInline):
    model = PermitWorkflowCondition
    extra = 0
    fields = ("operand", "field_path", "operator", "expected_value")
    show_change_link = True


@admin.register(PermitWorkflowTransition)
class PermitWorkflowTransitionAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("workflow", "from_step", "decision", "role", "to_step")
    list_filter = ("workflow", "decision", "role")
    search_fields = (
        "workflow__name",
        "from_step__title",
        "to_step__title",
        "role__code",
        "role__name",
    )
    autocomplete_fields = ("workflow", "from_step", "to_step", "role")
    inlines = (WorkflowConditionInline,)


@admin.register(PermitWorkflowCondition)
class PermitWorkflowConditionAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "transition",
        "operand",
        "field_path",
        "operator",
        "expected_value",
    )
    list_filter = ("operand", "operator")
    search_fields = ("field_path", "expected_value", "description")
    autocomplete_fields = ("transition",)
