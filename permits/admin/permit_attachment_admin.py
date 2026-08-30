from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html

from permits.admin.base_admin import TimeStampedAdmin
from permits.models import PermitAttachment
from permits.services.attachment_service import PermitAttachmentService


@admin.register(PermitAttachment)
class PermitAttachmentAdmin(admin.ModelAdmin):
    list_display = (
        "filename_link",
        "permit",
        "title",
        "uploaded_by",
        "uploaded_at",
        "file_size_display",
    )
    list_filter = ("uploaded_at",)
    search_fields = (
        "permit__permit_number",
        "title",
        "description",
        "uploaded_by__username",
        "file",
    )
    autocomplete_fields = ("permit", "uploaded_by", "modified_by")
    readonly_fields = ("attachment_id", "uploaded_by", "uploaded_at", "modified_at", "modified_by", "file_size_display")
    fields = (
        "permit",
        "file",
        "title",
        "description",
        "attachment_id",
        "uploaded_by",
        "uploaded_at",
        "modified_at",
        "modified_by",
        "file_size_display",
    )

    @admin.display(description="File")
    def filename_link(self, obj):
        if not obj.file:
            return "—"
        return format_html('<a href="{}" target="_blank">{}</a>', obj.file.url, obj.filename)

    @admin.display(description="Size")
    def file_size_display(self, obj):
        size = obj.file_size
        return f"{size / (1024 * 1024):.2f} MB" if size is not None else "Unavailable"

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_authenticated)

    def has_add_permission(self, request):
        return bool(request.user.is_authenticated)

    def has_change_permission(self, request, obj=None):
        return bool(
            request.user.is_authenticated
            and (obj is None or PermitAttachmentService.actor_can_change(
                actor=request.user, attachment=obj
            ))
        )

    def has_delete_permission(self, request, obj=None):
        return bool(
            request.user.is_authenticated
            and (obj is None or PermitAttachmentService.actor_can_delete(
                actor=request.user, attachment=obj
            ))
        )

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Attachment deletion is intentionally object-level because
        # contributors may delete only their own files.
        actions.pop("delete_selected", None)
        return actions

    def save_model(self, request, obj, form, change):
        if not change:
            PermitAttachmentService.ensure_can_add(
                actor=request.user, permit=obj.permit
            )
            obj.uploaded_by = request.user
        elif not PermitAttachmentService.actor_can_change(
            actor=request.user, attachment=obj
        ):
            raise PermissionDenied(
                "You may edit only attachments that you uploaded."
            )
        obj.modified_by = request.user
        obj.full_clean()
        super().save_model(request, obj, form, change)


class PermitAttachmentInline(admin.TabularInline):
    model = PermitAttachment
    extra = 0
    show_change_link = True
    verbose_name = "Permit Attachment"
    verbose_name_plural = "Permit Attachments"
    classes = ("collapse",)
    fields = (
        "file",
        "title",
        "description",
        "uploaded_by",
        "uploaded_at",
        "file_size_display",
    )
    readonly_fields = ("uploaded_by", "uploaded_at", "file_size_display")
    autocomplete_fields = ("uploaded_by",)

    @admin.display(description="Size")
    def file_size_display(self, obj):
        size = obj.file_size
        return f"{size / (1024 * 1024):.2f} MB" if size is not None else "Unavailable"

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_authenticated)

    def has_add_permission(self, request, obj=None):
        return bool(
            request.user.is_authenticated
            and obj is not None
            and PermitAttachmentService.actor_can_add(actor=request.user, permit=obj)
        )

    def has_change_permission(self, request, obj=None):
        return bool(
            request.user.is_authenticated
            and PermitAttachmentService.actor_can_manage_all(actor=request.user)
        )

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if PermitAttachmentService.actor_can_manage_all(actor=request.user):
            return True
        # For an inline, ``obj`` is the parent Permit rather than an
        # individual PermitAttachment.  The formset save hook still checks
        # each selected attachment with ``actor_can_delete``.
        if obj is None:
            return True
        return obj.attachments.filter(uploaded_by=request.user).exists()
