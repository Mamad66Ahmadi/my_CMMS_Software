# permits/admin/permit_base_admin.py

from django.contrib import admin

from permits.admin.base_admin import AUDIT_FIELDS, AUDIT_FIELDSET, TimeStampedAdmin
from permits.models.permit_base_models import (
    FireGasSystem,
    Hazard,
    IsolationType,
    PPE,
    PermitType,
    Precaution,
    ShiftType,
)


class BaseLookupAdmin(TimeStampedAdmin):
    """
    Shared admin configuration for PTW master/lookup data.

    All lookup models inherit from BaseLookupModel -> TimeStampedModel.
    """

    list_display = (
        "code",
        "name",
        "display_order",
        "is_active",
    )
    list_display_links = ("code", "name")
    search_fields = ("code", "name", "description")
    ordering = ("display_order", "code")
    list_filter = ("is_active",)
    list_per_page = 50
    readonly_fields = AUDIT_FIELDS

    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "display_order",
                    "is_active",
                )
            },
        ),
        AUDIT_FIELDSET,
    )


@admin.register(PermitType)
class PermitTypeAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "active_workflow",
        "display_order",
        "is_active",
    )

    list_filter = (
        "active_workflow",
        "is_active",
    )

    list_select_related = ("active_workflow",)
    autocomplete_fields = ("active_workflow",)

    fieldsets = (
        (
            "Permit Type Details",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "display_order",
                    "is_active",
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
        AUDIT_FIELDSET,
    )


@admin.register(Hazard)
class HazardAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "category",
        "display_order",
        "is_active",
    )

    list_filter = (
        "category",
        "is_active",
    )

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
                    "is_active",
                )
            },
        ),
        AUDIT_FIELDSET,
    )



@admin.register(Precaution)
class PrecautionAdmin(BaseLookupAdmin):
    list_display = (
        "code",
        "name",
        "requires_verification",
        "display_order",
        "is_active",
    )

    list_filter = (
        "requires_verification",
        "is_active",
    )

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
                    "is_active",
                )
            },
        ),
        AUDIT_FIELDSET,
    )


@admin.register(FireGasSystem)
class FireGasSystemAdmin(BaseLookupAdmin):
    pass


@admin.register(IsolationType)
class IsolationTypeAdmin(BaseLookupAdmin):
    pass


@admin.register(ShiftType)
class ShiftTypeAdmin(BaseLookupAdmin):
    pass



# @admin.register(PPE)
# class PPEAdmin(BaseLookupAdmin):
#     list_display = (
#         "code",
#         "name",
#         "mandatory_by_default",
#         "display_order",
#         "is_active",
#     )

#     list_filter = (
#         "mandatory_by_default",
#         "is_active",
#     )

#     fieldsets = (
#         (
#             "PPE Details",
#             {
#                 "fields": (
#                     "code",
#                     "name",
#                     "description",
#                     "display_order",
#                     "mandatory_by_default",
#                     "is_active",
#                 )
#             },
#         ),
#         AUDIT_FIELDSET,
#     )
