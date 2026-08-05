from django.contrib import admin

from permits.models.approval_models import PermitApproval


@admin.register(PermitApproval)
class PermitApprovalAdmin(admin.ModelAdmin):
    """
    Immutable approval audit records.

    Approvals are created by the workflow service and cannot be manually
    created, edited, or deleted from Django admin.
    """

    list_display = (
        "permit",
        "actor",
        "role",
        "decision",
        "from_step",
        "to_step",
        "created_at",
    )

    list_filter = (
        "decision",
        "role",
        "created_at",
    )

    search_fields = (
        "permit__permit_number",
        "actor__username",
        "actor__first_name",
        "actor__last_name",
        "role__code",
        "role__name",
        "comment",
    )

    list_select_related = (
        "permit",
        "actor",
        "role",
        "from_step",
        "to_step",
        "transition",
    )

    readonly_fields = (
        "permit",
        "actor",
        "role",
        "decision",
        "from_step",
        "to_step",
        "comment",
        "transition",
        "created_at",
    )

    fields = readonly_fields

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
