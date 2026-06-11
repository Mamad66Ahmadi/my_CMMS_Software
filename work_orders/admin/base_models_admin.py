# work_orders/admin/base_models_admin.py

from django.contrib import admin

from work_orders.models.base_models import (
    WorkType,
    Symptom,
    Cause,
    Priority,
    AwaitingReason,
    ProjectCode,
    PerformedAction,
    DetectionMethod,
)


class TimeStampedAdminMixin(admin.ModelAdmin):
    """
    Reusable admin settings for models inheriting from your TimeStampedModel:
    - created_at / created_by
    - modified_at / modified_by
    - is_active
    """
    readonly_fields = ("created_at", "created_by", "modified_at", "modified_by")
    list_filter = ("is_active", "created_at", "modified_at")
    list_per_page = 50
    def save_model(self, request, obj, form, change):
        """
        Populate created_by on creation and modified_by on every save.
        """
        if not change:  # On creation
            obj.created_by = request.user
        
        # Always update modified_by on any save
        obj.modified_by = request.user
        
        super().save_model(request, obj, form, change)

@admin.register(WorkType)
class WorkTypeAdmin(TimeStampedAdminMixin):
    list_display = ("work_type_code", "work_type_desc", "is_active", "created_at", "modified_at")
    list_display_links = ("work_type_code",)
    search_fields = ("work_type_code", "work_type_desc")
    ordering = ("work_type_code",)
    fields = (
        "work_type_code",
        "work_type_desc",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )


@admin.register(Symptom)
class SymptomAdmin(TimeStampedAdminMixin):
    list_display = ("symptom_code", "symptom_desc", "is_active", "created_at", "modified_at")
    list_display_links = ("symptom_code",)
    search_fields = ("symptom_code", "symptom_desc")
    ordering = ("symptom_code",)
    fields = (
        "symptom_code",
        "symptom_desc",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )


@admin.register(Cause)
class CauseAdmin(TimeStampedAdminMixin):
    list_display = ("cause_code", "cause_info", "is_active", "created_at", "modified_at")
    list_display_links = ("cause_code",)
    search_fields = ("cause_code", "cause_info")
    ordering = ("cause_code",)
    fields = (
        "cause_code",
        "cause_info",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )


@admin.register(Priority)
class PriorityAdmin(TimeStampedAdminMixin):
    list_display = ("priority_level", "priority_code", "is_active", "created_at", "modified_at")
    list_display_links = ("priority_code",)
    search_fields = ("priority_code",)
    list_filter = ("priority_level",) + TimeStampedAdminMixin.list_filter
    ordering = ("priority_level", "priority_code")
    fields = (
        "priority_code",
        "priority_level",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )


@admin.register(AwaitingReason)
class AwaitingReasonAdmin(TimeStampedAdminMixin):
    list_display = ("awaiting_code", "awaiting_desc", "is_active", "created_at", "modified_at")
    list_display_links = ("awaiting_code",)
    search_fields = ("awaiting_code", "awaiting_desc")
    ordering = ("awaiting_code",)
    fields = (
        "awaiting_code",
        "awaiting_desc",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )


@admin.register(ProjectCode)
class ProjectCodeAdmin(TimeStampedAdminMixin):
    list_display = ("project_code", "project_code_desc", "is_active", "created_at", "modified_at")
    list_display_links = ("project_code",)
    search_fields = ("project_code", "project_code_desc")
    ordering = ("project_code",)
    fields = (
        "project_code",
        "project_code_desc",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )


@admin.register(PerformedAction)
class PerformedActionAdmin(TimeStampedAdminMixin):
    list_display = ("action_code", "action_desc", "is_active", "created_at", "modified_at")
    list_display_links = ("action_code",)
    search_fields = ("action_code", "action_desc")
    ordering = ("action_code",)
    fields = (
        "action_code",
        "action_desc",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

@admin.register(DetectionMethod)
class DetectionMethodAdmin(TimeStampedAdminMixin):
    list_display = ("detection_code", "detection_desc", "is_active", "created_at", "modified_at")
    list_display_links = ("detection_code",)
    search_fields = ("detection_code", "detection_desc")
    ordering = ("detection_code",)
    fields = (
        "detection_code",
        "detection_desc",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )