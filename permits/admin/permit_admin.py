# permits/admin/permit_admin.py

from django.contrib import admin
from django.db import transaction
from django.utils import timezone

from permits.models.permit_models import Permit, PermitHazard, PermitPrecaution


class PermitHazardInline(admin.TabularInline):
    """
    Inline administrator for managing hazards assigned to a Permit.
    Includes validation support for is_active and soft-removal statuses.
    """

    model = PermitHazard
    extra = 1
    verbose_name = "Hazard Assessment"
    verbose_name_plural = "Hazard Assessments"
    classes = ("collapse",)
    autocomplete_fields = ["hazard"]
    readonly_fields = (
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
        "removed_at",
        "removed_by",
    )
    fields = (
        "hazard",
        "remarks",
        "is_active",
        "created_by",
        "modified_by",
        "removed_by",
        "removed_at",
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user

        # Handle soft-deactivation updates via UI changes
        if "is_active" in form.changed_data:
            if not obj.is_active:
                obj.removed_by = request.user
                obj.removed_at = timezone.now()
            else:
                obj.removed_by = None
                obj.removed_at = None

        super().save_model(request, obj, form, change)


class PermitPrecautionInline(admin.TabularInline):
    """
    Inline administrator for precautions assigned to a Permit.
    """

    model = PermitPrecaution
    extra = 1
    verbose_name = "Required Precaution"
    verbose_name_plural = "Required Precautions"
    classes = ("collapse",)
    autocomplete_fields = ["precaution"]
    readonly_fields = (
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
        "removed_at",
        "removed_by",
    )
    fields = (
        "precaution",
        "remarks",
        "is_active",
        "created_by",
        "modified_by",
        "removed_by",
        "removed_at",
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        obj.modified_by = request.user

        if "is_active" in form.changed_data:
            if not obj.is_active:
                obj.removed_by = request.user
                obj.removed_at = timezone.now()
            else:
                obj.removed_by = None
                obj.removed_at = None

        super().save_model(request, obj, form, change)


@admin.register(Permit)
class PermitAdmin(admin.ModelAdmin):
    """
    Admin configuration for the core Permit to Work (PTW) entity.
    """

    list_display = (
        "permit_number",
        "permit_type",
        "current_step",
        "work_order",
        "location_tag",
        "valid_from",
        "valid_to",
        "is_permit_active",
    )
    list_filter = (
        "permit_type",
        "current_step",
        "department",
        "vehicle_required",
        "valid_to",
    )
    search_fields = (
        "permit_number",
        "scope_of_work",
        "work_order__wo_number",  # Assuming wo_number exists in work orders
        "location_tag__tag",      # Assuming tag exists in location tags
    )
    ordering = ["-created_at", "-pk"]
    autocomplete_fields = [
        "continuation_of",
        "permit_type",
        "workflow",
        "current_step",
        "work_order",
        "location_tag",
        "work_supervisor",
        "department",
        "designated_area_authority",
        "designated_area_supervisor",
        "created_by",
        "modified_by",
    ]
    raw_id_fields = ("related_permits",)

    # Inlines for M2M associations containing audit statuses
    inlines = [PermitHazardInline, PermitPrecautionInline]

    readonly_fields = (
        # Audit Metadata
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
        # Validity Action Timestamps
        "issued_by_supervisor_at",
        "issued_by_area_authority_at",
        "issued_by_area_supervisor_at",
        "issued_by_permit_office_at",
        "issued_by_check_point_at",
        "issued_by_area_operator_at",
        "activated_at",
        "suspended_at",
        "completed_at",
        "closed_at",
    )

    fieldsets = (
        (
            "Identification & Workflow Configuration",
            {
                "fields": (
                    "permit_number",
                    "continuation_of",
                    "permit_type",
                    "workflow",
                    "current_step",
                )
            },
        ),
        (
            "Location & Linked Work",
            {
                "fields": (
                    "work_order",
                    "location_tag",
                )
            },
        ),
        (
            "Work Scope & Sizing",
            {
                "fields": (
                    "scope_of_work",
                    "duration_value",
                    "duration_unit",
                    "estimated_personnel",
                )
            },
        ),
        (
            "Tools & Equipment Details",
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
            "Equipment Preparations & Isolations",
            {
                "classes": ("collapse",),
                "fields": (
                    "mechanical_isolation",
                    "equipment_depressurized",
                    "equipment_drained",
                    "equipment_purged",
                    "process_isolation",
                    "area_authority_present_required",
                    "fire_watch_present_required",
                    "equipment_preparation_notes",
                ),
            },
        ),
        (
            "Operational Assignments",
            {
                "fields": (
                    "work_supervisor",
                    "department",
                    "designated_area_authority",
                    "designated_area_supervisor",
                )
            },
        ),
        (
            "Validity Windows",
            {
                "fields": (
                    "valid_from",
                    "valid_to",
                )
            },
        ),
        (
            "Step Audit Action Timestamps",
            {
                "classes": ("collapse",),
                "fields": (
                    "issued_by_supervisor_at",
                    "issued_by_area_authority_at",
                    "issued_by_area_supervisor_at",
                    "issued_by_permit_office_at",
                    "issued_by_check_point_at",
                    "issued_by_area_operator_at",
                    "activated_at",
                    "suspended_at",
                    "completed_at",
                    "closed_at",
                ),
            },
        ),
        (
            "Relations & Remarks",
            {
                "fields": (
                    "related_permits",
                    "previous_incidents",
                    "area_authority_comments",
                    "remarks",
                )
            },
        ),
        (
            "Auditing Info",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "modified_at",
                    "modified_by",
                )
            },
        ),
    )

    @admin.display(boolean=True, description="Is Active Now")
    def is_permit_active(self, obj):
        return obj.is_active

    def save_model(self, request, obj, form, change):
        """
        Populate auditing meta fields during creation and modification.
        """
        with transaction.atomic():
            if not change:
                obj.created_by = request.user
            obj.modified_by = request.user
            super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        """
        Ensure inline models (PermitHazard, PermitPrecaution) get their auditing
        relations configured correctly during transaction saving.
        """
        instances = formset.save(commit=False)
        
        # Handle deletions (when utilizing Django default deletion)
        for obj in formset.deleted_objects:
            obj.delete()

        # Handle new creations or existing edits
        for instance in instances:
            if not instance.pk:
                instance.created_by = request.user
            instance.modified_by = request.user
            
            # Explicit sync of soft deletion indicators if toggled
            if "is_active" in formset.readonly_fields or "is_active" in instance.__dict__:
                if not instance.is_active and not instance.removed_at:
                    instance.removed_by = request.user
                    instance.removed_at = timezone.now()
                elif instance.is_active:
                    instance.removed_by = None
                    instance.removed_at = None
                    
            instance.save()
        formset.save_m2m()
