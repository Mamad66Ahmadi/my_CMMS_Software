from django import forms
from django.contrib import admin

from permits.models.permit_shift_models import PermitShiftSignoff


class PermitShiftSignoffForm(forms.ModelForm):
    class Meta:
        model = PermitShiftSignoff
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        signed_by = cleaned_data.get("signed_by")
        signed_at = cleaned_data.get("signed_at")

        if (signed_by is None) != (signed_at is None):
            raise forms.ValidationError(
                "A signoff must have both a signer and signing time, "
                "or neither."
            )

        return cleaned_data


@admin.register(PermitShiftSignoff)
class PermitShiftSignoffAdmin(admin.ModelAdmin):
    form = PermitShiftSignoffForm

    list_display = (
        "work_shift",
        "role",
        "signed_by",
        "signed_at",
        "status",
    )

    list_filter = (
        "role",
        "signed_at",
        "work_shift__shift",
        "work_shift__date",
    )

    search_fields = (
        "work_shift__permit__permit_number",
        "role__code",
        "role__name",
        "signed_by__username",
        "signed_by__first_name",
        "signed_by__last_name",
    )

    autocomplete_fields = (
        "work_shift",
        "role",
        "signed_by",
    )

    list_select_related = (
        "work_shift",
        "work_shift__permit",
        "role",
        "signed_by",
    )

    ordering = (
        "work_shift__date",
        "work_shift__shift",
        "role__name",
    )

    fieldsets = (
        (
            "Shift Signoff",
            {
                "fields": (
                    "work_shift",
                    "role",
                ),
            },
        ),
        (
            "Signature",
            {
                "fields": (
                    "signed_by",
                    "signed_at",
                ),
                "description": (
                    "Leave both fields empty while the signoff is pending. "
                    "Once signed, both the signer and signing time must be "
                    "recorded."
                ),
            },
        ),
    )

    @admin.display(description="Status")
    def status(self, obj):
        if obj.signed_by_id and obj.signed_at:
            return "Signed"

        return "Pending"