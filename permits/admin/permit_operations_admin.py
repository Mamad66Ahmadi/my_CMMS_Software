from django.contrib import admin

from permits.admin.common import AuditAdminMixin
from permits.models import (
    AttachmentVersion,
    FireGasAction,
    IsolationPoint,
    IsolationVerification,
    PermitApproval,
    PermitAttachment,
    PermitComment,
    PermitExtension,
    PermitFireGas,
    PermitGasReading,
    PermitGasTest,
    PermitHazard,
    PermitHistory,
    PermitIsolation,
    PermitPPE,
    PermitPrecaution,
    PermitShiftLog,
)


class PermitRelatedAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_per_page = 50
    autocomplete_fields = ("permit",)


@admin.register(PermitHazard)
class PermitHazardAdmin(PermitRelatedAdmin):
    list_display = (
        "permit",
        "hazard",
        "risk_level",
        "residual_risk_level",
        "modified_at",
    )
    list_filter = ("risk_level", "residual_risk_level", "hazard__category")
    search_fields = (
        "permit__permit_number",
        "hazard__code",
        "hazard__name",
        "control_measure",
    )
    autocomplete_fields = ("permit", "hazard")


@admin.register(PermitPPE)
class PermitPPEAdmin(PermitRelatedAdmin):
    list_display = (
        "permit",
        "ppe",
        "is_mandatory",
        "verified_by",
        "verified_at",
    )
    list_filter = ("is_mandatory", "ppe")
    search_fields = (
        "permit__permit_number",
        "ppe__code",
        "ppe__name",
        "verified_by__username",
    )
    autocomplete_fields = ("permit", "ppe", "verified_by")


@admin.register(PermitPrecaution)
class PermitPrecautionAdmin(PermitRelatedAdmin):
    list_display = (
        "permit",
        "precaution",
        "status",
        "verified_by",
        "verified_at",
    )
    list_filter = ("status", "precaution")
    search_fields = (
        "permit__permit_number",
        "precaution__code",
        "precaution__name",
        "verified_by__username",
    )
    autocomplete_fields = ("permit", "precaution", "verified_by")


@admin.register(PermitApproval)
class PermitApprovalAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "permit",
        "sequence",
        "role",
        "approver",
        "decision",
        "signed_at",
        "expires_at",
        "is_current",
    )
    list_filter = ("decision", "role", "is_current", "signed_at", "expires_at")
    search_fields = (
        "permit__permit_number",
        "approver__username",
        "approver__first_name",
        "approver__last_name",
        "comments",
    )
    autocomplete_fields = ("permit", "approver")
    ordering = ("permit", "sequence", "created_at")


class GasReadingInline(admin.TabularInline):
    model = PermitGasReading
    extra = 0
    autocomplete_fields = ("gas_type",)
    fields = ("gas_type", "measured_value", "is_safe", "remarks")
    readonly_fields = ("is_safe",)


@admin.register(PermitGasTest)
class PermitGasTestAdmin(PermitRelatedAdmin):
    date_hierarchy = "test_datetime"
    list_display = (
        "permit",
        "test_type",
        "test_datetime",
        "gas_tester",
        "acceptable",
        "calibration_due_date",
    )
    list_filter = ("test_type", "acceptable", "test_datetime")
    search_fields = (
        "permit__permit_number",
        "gas_tester__username",
        "gas_detector_serial",
        "gas_detector_model",
        "location_description",
    )
    autocomplete_fields = ("permit", "gas_tester")
    inlines = (GasReadingInline,)


class IsolationPointInline(admin.TabularInline):
    model = IsolationPoint
    extra = 0
    autocomplete_fields = ("equipment_tag", "isolated_by", "restored_by")
    fields = (
        "point_number",
        "equipment_tag",
        "description",
        "status",
        "lock_number",
        "tag_number",
        "blind_number",
        "isolated_by",
        "isolated_at",
        "restored_by",
        "restored_at",
    )
    show_change_link = True


@admin.register(PermitIsolation)
class PermitIsolationAdmin(PermitRelatedAdmin):
    list_display = (
        "permit",
        "isolation_type",
        "status",
        "requires_loto",
        "blind_list_required",
        "planned_by",
        "verified_at",
        "removed_at",
    )
    list_filter = (
        "status",
        "isolation_type",
        "requires_loto",
        "blind_list_required",
    )
    search_fields = (
        "permit__permit_number",
        "description",
        "planned_by__username",
        "remarks",
    )
    autocomplete_fields = (
        "permit",
        "isolation_type",
        "planned_by",
        "applied_by",
        "verified_by",
        "removed_by",
    )
    inlines = (IsolationPointInline,)


class IsolationVerificationInline(admin.TabularInline):
    model = IsolationVerification
    extra = 0
    autocomplete_fields = ("verified_by",)
    fields = ("verified_by", "verified_at", "passed", "comments")
    show_change_link = True


@admin.register(IsolationPoint)
class IsolationPointAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = (
        "isolation",
        "point_number",
        "equipment_tag",
        "description",
        "status",
        "lock_number",
        "tag_number",
    )
    list_filter = ("status", "isolation__isolation_type")
    search_fields = (
        "isolation__permit__permit_number",
        "point_number",
        "equipment_tag__loc_tag",
        "description",
        "lock_number",
        "tag_number",
        "blind_number",
    )
    autocomplete_fields = (
        "isolation",
        "equipment_tag",
        "isolated_by",
        "restored_by",
    )
    inlines = (IsolationVerificationInline,)


@admin.register(IsolationVerification)
class IsolationVerificationAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("point", "verified_by", "verified_at", "passed")
    list_filter = ("passed", "verified_at")
    search_fields = (
        "point__isolation__permit__permit_number",
        "point__point_number",
        "verified_by__username",
        "comments",
    )
    autocomplete_fields = ("point", "verified_by")


class FireGasActionInline(admin.TabularInline):
    model = FireGasAction
    extra = 0
    autocomplete_fields = ("performed_by",)
    fields = ("action", "performed_by", "action_datetime", "comments")
    show_change_link = True


@admin.register(PermitFireGas)
class PermitFireGasAdmin(PermitRelatedAdmin):
    list_display = (
        "permit",
        "system",
        "system_reference",
        "location_tag",
        "status",
        "inhibited_at",
        "restored_at",
    )
    list_filter = ("status", "system")
    search_fields = (
        "permit__permit_number",
        "system__code",
        "system__name",
        "system_reference",
        "location_tag__loc_tag",
        "reason",
    )
    autocomplete_fields = (
        "permit",
        "system",
        "location_tag",
        "approved_by",
        "inhibited_by",
        "restored_by",
    )
    inlines = (FireGasActionInline,)


@admin.register(FireGasAction)
class FireGasActionAdmin(AuditAdminMixin, admin.ModelAdmin):
    date_hierarchy = "action_datetime"
    list_display = ("fire_gas", "action", "performed_by", "action_datetime")
    list_filter = ("action", "action_datetime")
    search_fields = (
        "fire_gas__permit__permit_number",
        "performed_by__username",
        "comments",
    )
    autocomplete_fields = ("fire_gas", "performed_by")


class AttachmentVersionInline(admin.TabularInline):
    model = AttachmentVersion
    extra = 0
    autocomplete_fields = ("uploaded_by",)
    fields = ("revision", "file", "change_description", "uploaded_by")
    show_change_link = True


@admin.register(PermitAttachment)
class PermitAttachmentAdmin(PermitRelatedAdmin):
    list_display = (
        "permit",
        "document_type",
        "document_number",
        "title",
        "revision",
        "is_latest_revision",
        "is_mandatory",
        "approved_at",
    )
    list_filter = (
        "document_type",
        "is_latest_revision",
        "is_mandatory",
        "approved_at",
    )
    search_fields = (
        "permit__permit_number",
        "document_number",
        "title",
        "description",
        "original_filename",
    )
    autocomplete_fields = ("permit", "uploaded_by", "approved_by")
    readonly_fields = ("original_filename", "file_size", "mime_type")
    inlines = (AttachmentVersionInline,)

    def save_model(self, request, obj, form, change):
        uploaded_file = form.cleaned_data.get("file")
        if uploaded_file:
            obj.original_filename = uploaded_file.name
            obj.file_size = uploaded_file.size
            obj.mime_type = getattr(uploaded_file, "content_type", "") or ""
        if not obj.uploaded_by_id:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(AttachmentVersion)
class AttachmentVersionAdmin(AuditAdminMixin, admin.ModelAdmin):
    list_display = ("attachment", "revision", "uploaded_by", "created_at")
    search_fields = (
        "attachment__permit__permit_number",
        "attachment__title",
        "change_description",
    )
    autocomplete_fields = ("attachment", "uploaded_by")


@admin.register(PermitShiftLog)
class PermitShiftLogAdmin(PermitRelatedAdmin):
    date_hierarchy = "handover_datetime"
    list_display = (
        "permit",
        "from_shift",
        "to_shift",
        "handed_over_by",
        "received_by",
        "handover_datetime",
        "gas_test_required",
    )
    list_filter = ("from_shift", "to_shift", "gas_test_required")
    search_fields = (
        "permit__permit_number",
        "handed_over_by__username",
        "received_by__username",
        "work_status",
        "outstanding_work",
    )
    autocomplete_fields = (
        "permit",
        "handed_over_by",
        "received_by",
        "gas_test_reference",
    )


@admin.register(PermitExtension)
class PermitExtensionAdmin(PermitRelatedAdmin):
    date_hierarchy = "requested_at"
    list_display = (
        "permit",
        "status",
        "requested_by",
        "requested_at",
        "previous_valid_to",
        "requested_valid_to",
        "approved_valid_to",
        "extension_hours",
    )
    list_filter = (
        "status",
        "requires_new_gas_test",
        "requires_new_approval",
    )
    search_fields = (
        "permit__permit_number",
        "requested_by__username",
        "approved_by__username",
        "reason",
    )
    autocomplete_fields = ("permit", "requested_by", "approved_by")
    readonly_fields = ("extension_hours",)


@admin.register(PermitComment)
class PermitCommentAdmin(PermitRelatedAdmin):
    list_display = ("permit", "author", "is_internal", "parent_comment", "created_at")
    list_filter = ("is_internal", "created_at")
    search_fields = (
        "permit__permit_number",
        "author__username",
        "comment",
    )
    autocomplete_fields = ("permit", "author", "parent_comment")


@admin.register(PermitHistory)
class PermitHistoryAdmin(admin.ModelAdmin):
    date_hierarchy = "event_datetime"
    list_display = (
        "permit",
        "event_type",
        "title",
        "performed_by",
        "event_datetime",
        "ip_address",
    )
    list_filter = ("event_type", "event_datetime")
    search_fields = (
        "permit__permit_number",
        "title",
        "description",
        "performed_by__username",
        "ip_address",
    )
    autocomplete_fields = ("permit", "performed_by")
    readonly_fields = (
        "permit",
        "event_type",
        "event_datetime",
        "performed_by",
        "title",
        "description",
        "old_value",
        "new_value",
        "ip_address",
        "user_agent",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.method in {"GET", "HEAD", "OPTIONS"}

    def has_delete_permission(self, request, obj=None):
        return False
