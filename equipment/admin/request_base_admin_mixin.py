from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.utils.html import format_html

# --------------------- Base Admin Mixin -----------------------------
class BaseChangeRequestAdmin(admin.ModelAdmin):
    """
    Shared admin behavior for all ChangeRequest models.
    """

    readonly_fields = (
        "status",
        "requested_by",
        "requested_at",
        "reviewed_by",
        "reviewed_at",
    )

    list_filter = ("status", "action", "requested_at")
    search_fields = ("id",)
    ordering = ("-requested_at",)

    actions = ["approve_requests", "reject_requests"]

    # ✅ Auto-assign requester
    def save_model(self, request, obj, form, change):
        if not change:
            obj.requested_by = request.user
        super().save_model(request, obj, form, change)

    # ✅ Approve Action
    @admin.action(description="✅ Approve selected requests")
    def approve_requests(self, request, queryset):
        approved_count = 0

        for obj in queryset:
            try:
                obj.approve_request(reviewer=request.user)
                approved_count += 1
            except ValidationError as e:
                self.message_user(
                    request,
                    f"Request #{obj.pk} skipped: {e}",
                    level=messages.WARNING,
                )

        self.message_user(
            request,
            f"{approved_count} request(s) approved successfully.",
            level=messages.SUCCESS,
        )

    # ✅ Reject Action
    @admin.action(description="❌ Reject selected requests")
    def reject_requests(self, request, queryset):
        rejected_count = 0

        for obj in queryset:
            try:
                obj.mark_rejected(reviewer=request.user)
                rejected_count += 1
            except ValidationError as e:
                self.message_user(
                    request,
                    f"Request #{obj.pk} skipped: {e}",
                    level=messages.WARNING,
                )

        self.message_user(
            request,
            f"{rejected_count} request(s) rejected.",
            level=messages.SUCCESS,
        )

    # Optional: colored status badge
    def colored_status(self, obj):
        colors = {
            "pending": "#f0ad4e",
            "approved": "#5cb85c",
            "approved_with_change": "#5bc0de",
            "rejected": "#d9534f",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="color:white;background:{};padding:3px 8px;border-radius:8px;">{}</span>',
            color,
            obj.get_status_display(),
        )

    colored_status.short_description = "Status"
