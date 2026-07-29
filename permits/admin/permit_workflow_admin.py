from django.contrib import admin

from permits.admin.common import AuditAdminMixin
from permits.models import (
    PermitWorkflowCondition,
    PermitWorkflowStep,
    PermitWorkflowTemplate,
    PermitWorkflowTransition,
)


class WorkflowStepInline(admin.TabularInline):
    model = PermitWorkflowStep
    extra = 0
    fields = (
        "sequence",
        "title",
        "role",
        "is_required",
        "allow_parallel",
        "parallel_group",
        "timeout_hours",
    )
    ordering = ("sequence",)
    show_change_link = True


@admin.register(PermitWorkflowTemplate)
class PermitWorkflowTemplateAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "permit_type",
        "version",
        "is_default",
        "is_active",
        "modified_at",
    )
    list_filter = ("permit_type", "is_default", "is_active")
    search_fields = ("code", "name", "description", "permit_type__name")
    autocomplete_fields = ("permit_type",)
    ordering = ("permit_type", "name", "-version")
    inlines = (WorkflowStepInline,)


class WorkflowConditionInline(admin.TabularInline):
    model = PermitWorkflowCondition
    extra = 0
    fields = ("condition_type", "expected_value", "description")
    show_change_link = True


@admin.register(PermitWorkflowStep)
class PermitWorkflowStepAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "workflow",
        "sequence",
        "title",
        "role",
        "is_required",
        "allow_parallel",
        "parallel_group",
        "timeout_hours",
    )
    list_filter = (
        "role",
        "is_required",
        "allow_delegate",
        "allow_parallel",
        "can_reject",
        "can_return",
        "can_skip",
    )
    search_fields = (
        "workflow__code",
        "workflow__name",
        "title",
        "description",
    )
    autocomplete_fields = ("workflow",)
    ordering = ("workflow", "sequence")
    inlines = (WorkflowConditionInline,)


@admin.register(PermitWorkflowCondition)
class PermitWorkflowConditionAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "workflow_step",
        "condition_type",
        "expected_value",
        "modified_at",
    )
    list_filter = ("condition_type",)
    search_fields = (
        "workflow_step__workflow__code",
        "workflow_step__title",
        "expected_value",
        "description",
    )
    autocomplete_fields = ("workflow_step",)


@admin.register(PermitWorkflowTransition)
class PermitWorkflowTransitionAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "from_step",
        "to_step",
        "on_approve",
        "on_reject",
        "on_return",
    )
    list_filter = ("on_approve", "on_reject", "on_return")
    search_fields = (
        "from_step__workflow__code",
        "from_step__title",
        "to_step__title",
    )
    autocomplete_fields = ("from_step", "to_step")
