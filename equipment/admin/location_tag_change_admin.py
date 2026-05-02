from django.contrib import admin
from equipment.admin.location_tag_admin import LocationTagResource
from .base_admin_mixin import *
from .request_base_admin_mixin import *

from equipment.models.request_equipment_models import (
    LocationTagChangeRequest,
    EquipmentChangeRequest,
    EquipmentDocumentChangeRequest,
)
@admin.register(LocationTagChangeRequest)
class LocationTagChangeRequestAdmin(BaseChangeRequestAdmin):

    list_display = (
        "id",
        "loc_tag",
        "action",
        "colored_status",
        "requested_by",
        "requested_at",
    )

    search_fields = ("loc_tag",)

    list_select_related = (
        "location_tag",
        "parent",
        "requested_by",
        "reviewed_by",
    )

    fieldsets = (
        ("Request Info", {
            "fields": (
                "action",
                "status",
                "location_tag",
            )
        }),
        ("Proposed Data", {
            "fields": (
                "loc_tag",
                "parent",
                "description",
                "long_tag",
                "obj_criticality",
                "obj_type",
                "obj_category",
                "unit",
                "train",
                "note",
                "mih_level",
            )
        }),
        ("Audit", {
            "fields": (
                "requested_by",
                "requested_at",
                "reviewed_by",
                "reviewed_at",
            )
        }),
    )


class EquipmentDocumentChangeRequestInline(admin.TabularInline):
    model = EquipmentDocumentChangeRequest
    extra = 1  # how many empty rows to show by default
    fields = ("file", "file_name", "description")
    readonly_fields = ()
    # if you want to disallow deleting once created:
    # can_delete = False




@admin.register(EquipmentChangeRequest)
class EquipmentChangeRequestAdmin(BaseChangeRequestAdmin):

    list_display = (
        "id",
        "equipment",
        "action",
        "colored_status",
        "requested_by",
        "requested_at",
    )

    list_select_related = (
        "equipment",
        "functional_location",
        "requested_by",
        "reviewed_by",
    )

    fieldsets = (
        ("Request Info", {
            "fields": (
                "action",
                "status",
                "equipment",
            )
        }),
        ("Proposed Data", {
            "fields": (
                "functional_location",
                "serial_number",
                "manufacturer",
                "model",
                "note",
            )
        }),
        ("Audit", {
            "fields": (
                "requested_by",
                "requested_at",
                "reviewed_by",
                "reviewed_at",
            )
        }),
    )

    inlines = [EquipmentDocumentChangeRequestInline]




