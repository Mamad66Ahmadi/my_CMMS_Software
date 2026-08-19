# permits/admin/permit_fg_esd_admin.py

from django.contrib import admin
from permits.models.permit_fg_esd_models import FireGasESD, PermitFireGasESD
from permits.admin.base_admin import AUDIT_FIELDS, AUDIT_FIELDSET, TimeStampedAdmin
from permits.admin.permit_base_admin import BaseLookupAdmin

@admin.register(FireGasESD)
class FireGasESDAdmin(BaseLookupAdmin):
    """
    Inherits list_display (code, name, is_active), search, and AUDIT_FIELDSET 
    logic from BaseLookupAdmin.
    """
    # Extend list_display to include the role
    list_display = BaseLookupAdmin.list_display + ("role",)
    list_filter = BaseLookupAdmin.list_filter + ("role",)
    
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "code",
                    "name",
                    "role", # Added here
                    "description",
                    "display_order",
                    "is_active",
                )
            },
        ),
        AUDIT_FIELDSET,
    )

class PermitFireGasESDInline(admin.TabularInline):
    model = PermitFireGasESD
    extra = 0

    readonly_fields = AUDIT_FIELDS
    classes = ("collapse",)

    autocomplete_fields = [
        "fire_gas_esd",
        "isolated_confirmed_by",
        "deisolated_confirmed_by",
        "created_by",
        "modified_by",
    ]

    fields = (
        "fire_gas_esd",
        "unit_zone",
        "isolated_time",
        "isolated_confirmed_by",
        "isolated_confirmed_at",
        "deisolated_time",
        "deisolated_confirmed_by",
        "deisolated_confirmed_at",
        "remarks",
        "created_by",
        "modified_by",
    )


    # We don't register this; it gets added to PermitAdmin.inlines
