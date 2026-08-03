# permits/admin/permit_base_admin.py

from django.contrib import admin

from permits.models.permit_base_models import (
    ApprovalRole,
    FireGasSystem,
    Hazard,
    IsolationType,
    PPE,
    PermitType,
    Precaution,
    ShiftType,
)


class BaseLookupAdmin(admin.ModelAdmin):
    """
    Shared admin configuration for PTW master/lookup data.

    All lookup models inherit from BaseLookupModel -> TimeStampedModel.
    """

    list_display = (
        "code",
        "name",
        "display_order",
        "created_at",
        "modified_at",
    )
    list_display_links = ("code", "name")
    search_fields = ("code", "name", "description")
    ordering = ("display_order", "code")
    readonly_fields = ("created_at", "modified_at")
    list_per_page = 50

    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "display_order",
                )
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(PermitType)
class PermitTypeAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "active_workflow",
        "display_order",
        "created_at",
        "modified_at",
    )
    list_select_related = ("active_workflow",)

    fieldsets = (
        (
            "Permit Type Details",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "display_order",
                )
            },
        ),
        (
            "Workflow Configuration",
            {
                "fields": ("active_workflow",),
                "description": (
                    "New permits of this type will use the selected active "
                    "workflow version."
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Hazard)
class HazardAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "display_order",
        "created_at",
        "modified_at",
    )
    list_filter = ("category",)

    fieldsets = (
        (
            "Hazard Details",
            {
                "fields": (
                    "code",
                    "name",
                    "category",
                    "description",
                    "display_order",
                )
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(PPE)
class PPEAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "mandatory_by_default",
        "display_order",
        "created_at",
        "modified_at",
    )
    list_filter = ("mandatory_by_default",)

    fieldsets = (
        (
            "PPE Details",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "display_order",
                    "mandatory_by_default",
                )
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(Precaution)
class PrecautionAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "requires_verification",
        "display_order",
        "created_at",
        "modified_at",
    )
    list_filter = ("requires_verification",)

    fieldsets = (
        (
            "Precaution Details",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "display_order",
                    "requires_verification",
                )
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "modified_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(FireGasSystem)
class FireGasSystemAdmin(BaseLookupAdmin):
    pass


@admin.register(IsolationType)
class IsolationTypeAdmin(BaseLookupAdmin):
    pass


@admin.register(ApprovalRole)
class ApprovalRoleAdmin(BaseLookupAdmin):
    pass


@admin.register(ShiftType)
class ShiftTypeAdmin(BaseLookupAdmin):
    pass
