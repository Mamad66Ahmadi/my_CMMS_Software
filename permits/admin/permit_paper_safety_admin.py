from django import forms
from django.contrib import admin, messages
from django.contrib.admin.helpers import ActionForm
from django.core.exceptions import PermissionDenied, ValidationError

from permits.models import (
    PermitPaperSafetyPermit,
    PermitPaperSafetyPermitStatusHistory,
    PaperSafetyPermitType,
    PaperSafetyPermitWorkflowStep,
)
from permits.services.paper_safety_permit_service import (
    PaperSafetyPermitReviewService,
)


class PermitPaperSafetyPermitInline(admin.TabularInline):
    """Paper safety permits attached to the main Permit-to-Work."""

    model = PermitPaperSafetyPermit
    extra = 1
    show_change_link = True
    verbose_name = "Required Paper Safety Permit"
    verbose_name_plural = "Required Paper Safety Permits"
    fields = (
        "safety_type",
        "safety_permit_number",
        "status",
        "reviewed_by",
        "reviewed_at",
        "review_comment",
    )
    readonly_fields = (
        "status",
        "reviewed_by",
        "reviewed_at",
        "review_comment",
    )

    def get_extra(self, request, obj=None, **kwargs):
        return 0 if obj and obj.activated_at else self.extra

    def has_add_permission(self, request, obj=None):
        if obj and obj.activated_at:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.activated_at:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.activated_at:
            return False
        return super().has_delete_permission(request, obj)


class PaperSafetyPermitActionForm(ActionForm):
    review_comment = forms.CharField(
        label="Review comment",
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Required when rejecting",
                "size": 35,
            }
        ),
    )


@admin.register(PermitPaperSafetyPermit)
class PermitPaperSafetyPermitAdmin(admin.ModelAdmin):
    """Permit Office review screen for paper safety permits."""

    action_form = PaperSafetyPermitActionForm
    actions = (
        "approve_selected_paper_safety_permits",
        "reject_selected_paper_safety_permits",
    )
    list_display = (
        "safety_permit_number_display",
        "safety_type",
        "permit",
        "status",
        "reviewed_by",
        "reviewed_at",
    )
    list_filter = (
        "status",
        "safety_type",
        "reviewed_at",
    )
    search_fields = (
        "safety_permit_number",
        "permit__permit_number",
        "permit__scope_of_work",
    )
    autocomplete_fields = ("permit",)
    list_select_related = (
        "permit",
        "reviewed_by",
        "created_by",
        "modified_by",
    )
    ordering = ("status", "safety_type", "permit__permit_number", "pk")
    fields = (
        "permit",
        "safety_type",
        "safety_permit_number",
        "status",
        "reviewed_by",
        "reviewed_at",
        "review_comment",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )
    readonly_fields = (
        "permit",
        "status",
        "reviewed_by",
        "reviewed_at",
        "review_comment",
        "created_at",
        "created_by",
        "modified_at",
        "modified_by",
    )

    @admin.display(description="Safety Permit Number", ordering="safety_permit_number")
    def safety_permit_number_display(self, obj):
        return obj.safety_permit_number or "Number pending"

    def has_add_permission(self, request):
        # Required paper permits are created within their main permit.
        return False

    def has_delete_permission(self, request, obj=None):
        # Deletion belongs to the editable main-permit form, not review.
        return False

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if obj and (
            obj.status == PermitPaperSafetyPermit.Status.ACTIVE
            or obj.permit.activated_at
        ):
            readonly.extend(("safety_type", "safety_permit_number"))
        return tuple(dict.fromkeys(readonly))

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Approve selected paper safety permits")
    def approve_selected_paper_safety_permits(self, request, queryset):
        comment = (request.POST.get("review_comment") or "").strip()
        approved = 0
        skipped = 0
        failures = []

        for record in queryset:
            if record.status == PermitPaperSafetyPermit.Status.ACTIVE:
                skipped += 1
                continue

            try:
                PaperSafetyPermitReviewService.approve(
                    paper_safety_permit_id=record.pk,
                    actor=request.user,
                    comment=comment,
                )
                approved += 1
            except (PermissionDenied, ValidationError) as exc:
                failures.append(
                    f"{record}: {self._validation_message(exc)}"
                )

        if approved:
            self.message_user(
                request,
                f"Approved {approved} paper safety permit(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} paper safety permit(s) already approved.",
                level=messages.WARNING,
            )
        self._report_failures(request, failures)

    @admin.action(description="Reject selected paper safety permits")
    def reject_selected_paper_safety_permits(self, request, queryset):
        comment = (request.POST.get("review_comment") or "").strip()
        if not comment:
            self.message_user(
                request,
                "Enter a review comment before rejecting paper safety permits.",
                level=messages.ERROR,
            )
            return

        rejected = 0
        skipped = 0
        failures = []

        for record in queryset:
            if record.status == PermitPaperSafetyPermit.Status.DEACTIVE:
                skipped += 1
                continue

            try:
                PaperSafetyPermitReviewService.reject(
                    paper_safety_permit_id=record.pk,
                    actor=request.user,
                    comment=comment,
                )
                rejected += 1
            except (PermissionDenied, ValidationError) as exc:
                failures.append(
                    f"{record}: {self._validation_message(exc)}"
                )

        if rejected:
            self.message_user(
                request,
                f"Rejected {rejected} paper safety permit(s).",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} paper safety permit(s) already rejected.",
                level=messages.WARNING,
            )
        self._report_failures(request, failures)

    @staticmethod
    def _validation_message(exc):
        if isinstance(exc, ValidationError):
            return "; ".join(exc.messages)
        return str(exc)

    def _report_failures(self, request, failures):
        if not failures:
            return

        shown = failures[:5]
        remaining = len(failures) - len(shown)
        message = " | ".join(shown)
        if remaining:
            message += f" | and {remaining} more failure(s)"
        self.message_user(request, message, level=messages.ERROR)


@admin.register(PermitPaperSafetyPermitStatusHistory)
class PermitPaperSafetyPermitStatusHistoryAdmin(admin.ModelAdmin):
    """Read-only audit history for paper safety permit status changes."""

    list_display = (
        "permit_safety_permit",
        "from_status_display",
        "to_status_display",
        "changed_by",
        "changed_at",
        "remarks",
    )
    list_filter = (
        "to_status",
        "changed_at",
    )
    search_fields = (
        "permit_safety_permit__safety_permit_number",
        "permit_safety_permit__permit__permit_number",
        "permit_safety_permit__permit__scope_of_work",
        "changed_by__username",
        "remarks",
    )
    list_select_related = (
        "permit_safety_permit",
        "permit_safety_permit__permit",
        "changed_by",
    )
    ordering = ("-changed_at", "-pk")
    fields = (
        "permit_safety_permit",
        "from_status_display",
        "to_status_display",
        "changed_by",
        "changed_at",
        "remarks",
    )
    readonly_fields = fields

    @admin.display(description="From status")
    def from_status_display(self, obj):
        return PermitPaperSafetyPermit.status_labels().get(
            obj.from_status, obj.from_status or "—"
        )

    @admin.display(description="To status", ordering="to_status")
    def to_status_display(self, obj):
        return PermitPaperSafetyPermit.status_labels().get(
            obj.to_status, obj.to_status
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PaperSafetyPermitType)
class PaperSafetyPermitTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "sort_order")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("sort_order", "name")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PaperSafetyPermitWorkflowStep)
class PaperSafetyPermitWorkflowStepAdmin(admin.ModelAdmin):
    list_display = ("step_order", "name", "status", "is_active")
    list_filter = ("is_active", "status")
    search_fields = ("name",)
    ordering = ("step_order", "pk")

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        obj.modified_by = request.user
        super().save_model(request, obj, form, change)
