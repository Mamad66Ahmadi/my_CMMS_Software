from django.contrib import admin

from permits.admin.common import AuditAdminMixin
from permits.models import (
    ApprovalRole,
    FireGasSystem,
    GasType,
    Hazard,
    IsolationType,
    PermitType,
    PPE,
    Precaution,
    ShiftType,
)


class BaseLookupAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "display_order",
        "is_active",
        "modified_at",
    )
    list_display_links = ("code", "name")
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "description")
    ordering = ("display_order", "code")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description")}),
        ("Control", {"fields": ("display_order", "is_active")}),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "created_by",
                    "modified_at",
                    "modified_by",
                ),
            },
        ),
    )


@admin.register(PermitType)
class PermitTypeAdmin(BaseLookupAdmin):
    list_display = BaseLookupAdmin.list_display[:-1] + (
        "requires_gas_test",
        "requires_fire_watch",
        "requires_isolation",
        "requires_risk_assessment",
        "modified_at",
    )
    list_filter = (
        "requires_gas_test",
        "requires_fire_watch",
        "requires_isolation",
        "requires_risk_assessment",
        "is_active",
    )
    fieldsets = BaseLookupAdmin.fieldsets[:1] + (
        (
            "Permit Requirements",
            {
                "fields": (
                    "requires_gas_test",
                    "requires_fire_watch",
                    "requires_isolation",
                    "requires_risk_assessment",
                )
            },
        ),
    ) + BaseLookupAdmin.fieldsets[1:]


@admin.register(Hazard)
class HazardAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "display_order",
        "is_active",
        "modified_at",
    )
    list_filter = ("category", "is_active")
    fieldsets = (
        ("Identity", {"fields": ("code", "name", "description", "category")}),
    ) + BaseLookupAdmin.fieldsets[1:]


@admin.register(PPE)
class PPEAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "mandatory_by_default",
        "display_order",
        "is_active",
        "modified_at",
    )
    list_filter = ("mandatory_by_default", "is_active")
    fieldsets = BaseLookupAdmin.fieldsets[:1] + (
        ("Requirement", {"fields": ("mandatory_by_default",)}),
    ) + BaseLookupAdmin.fieldsets[1:]


@admin.register(Precaution)
class PrecautionAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "requires_verification",
        "display_order",
        "is_active",
        "modified_at",
    )
    list_filter = ("requires_verification", "is_active")
    fieldsets = BaseLookupAdmin.fieldsets[:1] + (
        ("Verification", {"fields": ("requires_verification",)}),
    ) + BaseLookupAdmin.fieldsets[1:]


admin.site.register(FireGasSystem, BaseLookupAdmin)
admin.site.register(IsolationType, BaseLookupAdmin)
admin.site.register(ApprovalRole, BaseLookupAdmin)
admin.site.register(ShiftType, BaseLookupAdmin)


@admin.register(GasType)
class GasTypeAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "unit",
        "minimum_limit",
        "maximum_limit",
        "display_order",
        "is_active",
    )
    list_editable = ("display_order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "unit")
    ordering = ("display_order", "code")
    fieldsets = (
        ("Gas", {"fields": ("code", "name", "unit")}),
        ("Safe Range", {"fields": ("minimum_limit", "maximum_limit")}),
        ("Control", {"fields": ("display_order", "is_active")}),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "created_by",
                    "modified_at",
                    "modified_by",
                ),
            },
        ),
    )
