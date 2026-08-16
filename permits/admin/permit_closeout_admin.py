# permits/admin/permit_closeout_admin.py

from django import forms
from django.contrib import admin

from permits.admin.permit_base_admin import BaseLookupAdmin, AUDIT_FIELDSET
from permits.models import PermitCloseoutItem, PermitCloseoutSignoff


@admin.register(PermitCloseoutItem)
class PermitCloseoutItemAdmin(BaseLookupAdmin):
    list_display = ("code", "name", "role", "display_order", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("code", "name", "description")
    autocomplete_fields = ("role",)

    fieldsets = (
        (
            "Close-out Item",
            {
                "fields": (
                    "code",
                    "name",
                    "description",
                    "role",
                    "display_order",
                    "is_active",
                )
            },
        ),
        AUDIT_FIELDSET,
    )


class PermitCloseoutSignoffForm(forms.ModelForm):
    class Meta:
        model = PermitCloseoutSignoff
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        signed_by = cleaned_data.get("signed_by")
        signed_at = cleaned_data.get("signed_at")

        # Exactly one of the pair is set -> invalid.
        if (signed_by is None) != (signed_at is None):
            raise forms.ValidationError(
                "A sign-off must have both a signer and signing time, "
                "or neither."
            )

        # A signer must be authorized for the close-out item's role
        # (optional but recommended — mirrors your role-based model).
        closeout_item = cleaned_data.get("closeout_item")
        if closeout_item and signed_by:
            # add role checks here if you track role->user mapping
            pass

        return cleaned_data


@admin.register(PermitCloseoutSignoff)
class PermitCloseoutSignoffAdmin(admin.ModelAdmin):
    form = PermitCloseoutSignoffForm

    list_display = (
        "permit",
        "closeout_item",
        "role",
        "signed_by",
        "signed_at",
        "status",
    )

    list_filter = (
        "closeout_item__role",
        "signed_at",
        "permit__permit_type",
    )

    search_fields = (
        "permit__permit_number",
        "closeout_item__code",
        "closeout_item__name",
        "signed_by__username",
        "signed_by__first_name",
        "signed_by__last_name",
    )

    autocomplete_fields = (
        "permit",
        "closeout_item",
        "signed_by",
    )

    list_select_related = (
        "permit",
        "closeout_item",
        "closeout_item__role",
        "signed_by",
    )

    ordering = ("permit", "closeout_item__display_order")

    readonly_fields = (
        "created_at",
        "created_by",
    )

    fieldsets = (
        (
            "Close-out Sign-off",
            {
                "fields": ("permit", "closeout_item"),
            },
        ),
        (
            "Signature",
            {
                "fields": ("signed_by", "signed_at"),
                "description": (
                    "Leave both fields empty while the sign-off is pending. "
                    "Once signed, both the signer and signing time must be "
                    "recorded."
                ),
            },
        ),
        (
            "Remarks",
            {
                "fields": ("remarks",),
            },
        ),
        (
            "Audit Information",
            {
                "classes": ("collapse",),
                "fields": ("created_at", "created_by"),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Status")
    def status(self, obj):
        if obj.signed_by_id and obj.signed_at:
            return "Signed"
        return "Pending"

    @admin.display(description="Role")
    def role(self, obj):
        return obj.closeout_item.role
