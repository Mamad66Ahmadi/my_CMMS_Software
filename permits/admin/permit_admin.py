from django.contrib import admin
from django.utils import timezone

from permits.models.permit_models import Permit


class AuditAdminMixin(admin.ModelAdmin):
    """
    Reusable admin settings for models with:
    - created_at / created_by
    - modified_at / modified_by
    """
    readonly_fields = ("created_at", "created_by", "modified_at", "modified_by")
    list_per_page = 50

    def save_model(self, request, obj, form, change):
        # set created_by on create
        if not change and not getattr(obj, "created_by_id", None):
            obj.created_by = request.user

        # always update modified_by
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Permit)
class PermitAdmin(AuditAdminMixin):
    date_hierarchy = "created_at"

    list_display = (
        "permit_number",
        "status",
        "department",
        "location_tag",
        "work_order",
        "authorized_issuer",
        "permit_holder",
        "valid_from",
        "valid_to",
        "is_currently_valid_display",
        "created_at",
    )
    list_display_links = ("permit_number",)

    search_fields = (
        "permit_number",
        "description",
        "comment",
        "department__name",
        "location_tag__tag_code",
        "work_order__wo_number",
        "authorized_issuer__username",
        "authorized_issuer__first_name",
        "authorized_issuer__last_name",
        "permit_holder__username",
        "permit_holder__first_name",
        "permit_holder__last_name",
        "hazard_codes__code",
        "hazard_codes__name",
    )

    list_filter = (
        "status",
        "department",
        "hazard_codes",
        "valid_from",
        "valid_to",
        "is_excavation",
        "is_spading",
        "is_confined_space",
        "is_equipment_test",
        "is_radiography",
        "is_diving",
        "created_at",
        "modified_at",
    )

    ordering = ("-created_at",)
    filter_horizontal = ("hazard_codes",)
    autocomplete_fields = (
        "continuation_of",
        "location_tag",
        "work_order",
        "department",
        "authorized_issuer",
        "permit_holder",
    )

    fieldsets = (
        ("Permit", {"fields": ("permit_number", "status", "description")}),
        ("Validity", {"fields": ("valid_from", "valid_to")}),
        ("Scope / Links", {"fields": ("work_order", "department", "location_tag", "continuation_of")}),
        ("People", {"fields": ("authorized_issuer", "permit_holder")}),
        ("Hazards", {"fields": ("hazard_codes",)}),
        (
            "Special Work Conditions",
            {
                "fields": (
                    "is_excavation",
                    "is_spading",
                    "is_confined_space",
                    "is_equipment_test",
                    "is_radiography",
                    "is_diving",
                )
            },
        ),
        ("Audit", {"fields": ("created_at", "created_by", "modified_at", "modified_by")}),
    )

    def is_currently_valid_display(self, obj: Permit) -> bool:
        return obj.is_currently_valid

    is_currently_valid_display.boolean = True
    is_currently_valid_display.short_description = "Currently valid?"
