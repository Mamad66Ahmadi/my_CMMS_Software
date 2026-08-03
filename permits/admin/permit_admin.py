# from django.contrib import admin
# from django.utils import timezone

# from permits.admin.common import AuditAdminMixin
# from permits.models import (
#     Permit,
#     PermitApproval,
#     PermitHazard,
#     PermitPrecaution,
# )


# class PermitHazardInline(admin.TabularInline):
#     model = PermitHazard
#     extra = 0
#     autocomplete_fields = ("hazard", "removed_by")
#     fields = ("hazard", "remarks", "is_active", "removed_by", "removed_at")
#     show_change_link = True




# class PermitPrecautionInline(admin.TabularInline):
#     model = PermitPrecaution
#     extra = 0
#     autocomplete_fields = ("precaution", "removed_by")
#     fields = (
#         "precaution",
#         "remarks",
#         "is_active",
#         "removed_by",
#         "removed_at",
#     )
#     show_change_link = True


# class PermitApprovalInline(admin.TabularInline):
#     model = PermitApproval
#     extra = 0
#     can_delete = False
#     autocomplete_fields = ("actor", "role", "from_step", "to_step", "transition")
#     fields = (
#         "actor",
#         "role",
#         "from_step",
#         "to_step",
#         "decision",
#         "comment",
#         "transition",
#     )
#     readonly_fields = fields
#     show_change_link = True

#     def has_add_permission(self, request, obj=None):
#         return False


# @admin.register(Permit)
# class PermitAdmin(AuditAdminMixin, admin.ModelAdmin):
#     date_hierarchy = "valid_from"
#     list_display = (
#         "permit_number",
#         "permit_type",
#         "current_step",
#         "location_tag",
#         "work_order",
#         "valid_from",
#         "valid_to",
#         "validity_state",
#     )
#     list_display_links = ("permit_number",)
#     list_filter = (
#         "permit_type",
#         "current_step",
#         "department",
#         "vehicle_required",
#         "valid_from",
#         "valid_to",
#     )
#     search_fields = (
#         "permit_number",
#         "scope_of_work",
#         "location_tag__loc_tag",
#         "work_order__wo_number",
#         "department__department_code",
#         "department__name",
#     )
#     ordering = ("-created_at",)
#     autocomplete_fields = (
#         "continuation_of",
#         "permit_type",
#         "workflow",
#         "current_step",
#         "work_order",
#         "location_tag",
#         "work_supervisor",
#         "designated_area_authority",
#         "designated_area_supervisor",
#         "department",
#     )
#     filter_horizontal = ("related_permits",)
#     readonly_fields = (
#         "duration_display",
#         "issued_by_supervisor_at",
#         "issued_by_area_authority_at",
#         "issued_by_area_supervisor_at",
#         "issued_by_permit_office_at",
#         "issued_by_check_point_at",
#         "issued_by_area_operator_at",
#     )
#     inlines = (
#         PermitHazardInline,
#         PermitPrecautionInline,
#         PermitApprovalInline,
#     )
#     fieldsets = (
#         (
#             "Identification and Workflow",
#             {
#                 "fields": (
#                     "permit_number",
#                     "permit_type",
#                     "workflow",
#                     "current_step",
#                     "continuation_of",
#                     "related_permits",
#                 )
#             },
#         ),
#         (
#             "Work Scope",
#             {
#                 "fields": (
#                     "work_order",
#                     "location_tag",
#                     "department",
#                     "scope_of_work",
#                     ("duration_value", "duration_unit"),
#                     "estimated_personnel",
#                 )
#             },
#         ),
#         (
#             "Personnel",
#             {
#                 "fields": (
#                     "work_supervisor",
#                     "designated_area_authority",
#                     "designated_area_supervisor",
#                 )
#             },
#         ),
#         (
#             "Tools and Materials",
#             {
#                 "classes": ("collapse",),
#                 "fields": (
#                     "electrical_tools",
#                     "mechanical_tools",
#                     "other_tools",
#                     "hazardous_materials",
#                     "non_explosion_proof_equipment",
#                     "vehicle_required",
#                     "vehicle_description",
#                 ),
#             },
#         ),
#         (
#             "Risk Assessment",
#             {
#                 "fields": (
#                     "previous_incidents",
#                     "area_authority_comments",
#                 )
#             },
#         ),
#         (
#             "Equipment Preparation",
#             {
#                 "fields": (
#                     "mechanical_isolation",
#                     "process_isolation",
#                     "equipment_depressurized",
#                     "equipment_drained",
#                     "equipment_purged",
#                     "area_authority_present_required",
#                     "fire_watch_present_required",
#                     "equipment_preparation_notes",
#                 )
#             },
#         ),
#         (
#             "Validity",
#             {
#                 "fields": (
#                     ("valid_from", "valid_to"),
#                     "duration_display",
#                     ("activated_at", "suspended_at"),
#                     ("completed_at", "closed_at"),
#                 )
#             },
#         ),
#         (
#             "Workflow Audit",
#             {
#                 "classes": ("collapse",),
#                 "fields": (
#                     "issued_by_supervisor_at",
#                     "issued_by_area_authority_at",
#                     "issued_by_area_supervisor_at",
#                     "issued_by_permit_office_at",
#                     "issued_by_check_point_at",
#                     "issued_by_area_operator_at",
#                 ),
#             },
#         ),
#         ("Remarks", {"fields": ("remarks",)}),
#         (
#             "Audit",
#             {
#                 "classes": ("collapse",),
#                 "fields": (
#                     "created_at",
#                     "created_by",
#                     "modified_at",
#                     "modified_by",
#                 ),
#             },
#         ),
#     )

#     def get_queryset(self, request):
#         return (
#             super()
#             .get_queryset(request)
#             .select_related(
#                 "permit_type",
#                 "workflow",
#                 "current_step",
#                 "location_tag",
#                 "work_order",
#                 "department",
#             )
#         )

#     @admin.display(description="Validity", ordering="valid_to")
#     def validity_state(self, obj):
#         if obj.has_expired:
#             return "Expired"
#         if obj.is_active:
#             return "Active"
#         if obj.valid_from > timezone.now():
#             return "Scheduled"
#         return "Inactive"

#     @admin.display(description="Duration")
#     def duration_display(self, obj):
#         if not obj or not obj.duration:
#             return "—"
#         total_seconds = int(obj.duration.total_seconds())
#         hours, remainder = divmod(total_seconds, 3600)
#         minutes = remainder // 60
#         return f"{hours}h {minutes}m"
