# permits/admin/permit_base_admin.py

from django.contrib import admin

from permits.models.permit_base_models import HazardCode


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
        if not change:
            obj.created_by = request.user

        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(HazardCode)
class HazardCodeAdmin(TimeStampedAdminMixin):
    list_display = ("code", "name", "description", "is_active", "created_at", "modified_at")
    list_display_links = ("code",)
    search_fields = ("code", "name", "description")
    ordering = ("code",)
    fields = (
        "code",
        "name",
        "description",
        "is_active",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )
