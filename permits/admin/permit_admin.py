from django.contrib import admin
from django.utils import timezone

from permits.admin.common import AuditAdminMixin
from permits.models import (
    Permit,
    PermitApproval,
    PermitHazard,
    PermitPPE,
    PermitPrecaution,
)


class PermitHazardInline(admin.TabularInline):
    model = PermitHazard
    extra = 0
    autocomplete_fields = ("hazard",)
    fields = (
        "hazard",
        "risk_level",
        "control_measure",
        "residual_risk_level",
    )
    show_change_link = True


class PermitPPEInline(admin.TabularInline):
    model = PermitPPE
    extra = 0
    autocomplete_fields = ("ppe", "verified_by")
    fields = (
        "ppe",
        "is_mandatory",
        "verified_by",
        "verified_at",
        "remarks",
    )
    show_change_link = True


class PermitPrecautionInline(admin.TabularInline):
    model = PermitPrecaution
    extra = 0
    autocomplete_fields = ("precaution", "verified_by")
    fields = (
        "precaution",
        "status",
        "verified_by",
        "verified_at",
        "remarks",
    )
    show_change_link = True


class PermitApprovalInline(admin.TabularInline):
    model = PermitApproval
    extra = 0
    autocomplete_fields = ("approver",)
    fields = (
        "sequence",
        "role",
        "approver",
        "decision",
        "signed_at",
        "expires_at",
        "is_current",
    )
    show_change_link = True


@admin.register(Permit)
class PermitAdmin(AuditAdminMixin, admin.ModelAdmin):
    date_hierarchy = "valid_from"
    list_display = (
        "permit_number",
        "permit_type",
        "status",
        "location_tag",
        "work_order",
        "permit_holder",
        "valid_from",
        "valid_to",
        "validity_state",
    )
    list_display_links = ("permit_number",)
    list_filter = (
        "status",
        "permit_type",
        "department",
        "fire_watch_required",
        "vehicle_required",
        "valid_from",
        "valid_to",
    )
    search_fields = (
        "permit_number",
        "serial_number",
        "scope_of_work",
        "location_tag__loc_tag",
        "work_order__wo_number",
        "department__department_code",
        "department__name",
        "requested_by__username",
        "requested_by__first_name",
        "requested_by__last_name",
        "permit_holder__username",
        "permit_holder__first_name",
        "permit_holder__last_name",
    )
    ordering = ("-created_at",)
    autocomplete_fields = (
        "continuation_of",
        "permit_type",
        "work_order",
        "location_tag",
        "requested_by",
        "permit_holder",
        "work_supervisor",
        "area_authority",
        "contractor_supervisor",
        "department",
    )
    filter_horizontal = ("related_permits",)
    readonly_fields = (
        "issued_at",
        "activated_at",
        "suspended_at",
        "completed_at",
        "closed_at",
        "duration_display",
    )
    inlines = (
        PermitHazardInline,
        PermitPPEInline,
        PermitPrecautionInline,
        PermitApprovalInline,
    )
    fieldsets = (
        (
            "Identification",
            {
                "fields": (
                    "permit_number",
                    "serial_number",
                    "permit_type",
                    "status",
                    "continuation_of",
                    "related_permits",
                )
            },
        ),
        (
            "Work Scope",
            {
                "fields": (
                    "work_order",
                    "location_tag",
                    "department",
                    "scope_of_work",
                    "estimated_duration_hours",
                    "estimated_personnel",
                )
            },
        ),
        (
            "Personnel",
            {
                "fields": (
                    "requested_by",
                    "permit_holder",
                    "work_supervisor",
                    "area_authority",
                    "contractor_supervisor",
                )
            },
        ),
        (
            "Tools and Materials",
            {
                "classes": ("collapse",),
                "fields": (
                    "electrical_tools",
                    "mechanical_tools",
                    "other_tools",
                    "hazardous_materials",
                    "non_explosion_proof_equipment",
                    "vehicle_required",
                    "vehicle_description",
                ),
            },
        ),
        (
            "Risk Assessment",
            {
                "fields": (
                    "previous_incidents",
                    "area_authority_comments",
                    "additional_precautions",
                )
            },
        ),
        (
            "Equipment Preparation",
            {
                "fields": (
                    "mechanical_isolation",
                    "process_isolation",
                    "equipment_depressurized",
                    "equipment_drained",
                    "equipment_purged",
                    "area_authority_present",
                    "fire_watch_required",
                    "fire_watch_present",
                    "equipment_preparation_notes",
                )
            },
        ),
        (
            "Validity",
            {
                "fields": (
                    ("valid_from", "valid_to"),
                    "duration_display",
                    ("issued_at", "activated_at"),
                    ("suspended_at", "completed_at", "closed_at"),
                )
            },
        ),
        ("Remarks", {"fields": ("remarks",)}),
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

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related(
                "permit_type",
                "location_tag",
                "work_order",
                "department",
                "permit_holder",
            )
        )

    @admin.display(description="Validity", ordering="valid_to")
    def validity_state(self, obj):
        if obj.has_expired:
            return "Expired"
        if obj.is_active:
            return "Active"
        if obj.valid_from > timezone.now():
            return "Scheduled"
        return "Inactive"

    @admin.display(description="Duration")
    def duration_display(self, obj):
        if not obj or not obj.duration:
            return "—"
        total_seconds = int(obj.duration.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes = remainder // 60
        return f"{hours}h {minutes}m"
