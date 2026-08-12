from django import forms
from django.contrib import admin

from permits.admin.base_admin import AUDIT_FIELDSET, TimeStampedAdmin
from permits.models.permit_shift_models import PermitTypeActiveShiftRole


class PermitTypeActiveShiftRoleForm(forms.ModelForm):
    class Meta:
        model = PermitTypeActiveShiftRole
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        permit_type = cleaned_data.get("permit_type")
        role = cleaned_data.get("role")
        sequence = cleaned_data.get("sequence")

        if permit_type and role:
            qs = PermitTypeActiveShiftRole.objects.filter(
                permit_type=permit_type,
                role=role,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    {
                        "role": (
                            "This role is already configured for this "
                            "permit type."
                        )
                    }
                )

        if sequence is not None and sequence < 1:
            raise forms.ValidationError(
                {
                    "sequence": "Sequence must be greater than or equal to 1."
                }
            )

        return cleaned_data


@admin.register(PermitTypeActiveShiftRole)
class PermitTypeActiveShiftRoleAdmin(TimeStampedAdmin):
    form = PermitTypeActiveShiftRoleForm

    list_display = (
        "permit_type",
        "sequence",
        "role",
        "is_required",
        "created_at",
        "modified_at",
    )

    list_filter = (
        "permit_type",
        "role",
        "is_required",
    )

    search_fields = (
        "permit_type__code",
        "permit_type__name",
        "role__code",
        "role__name",
    )

    autocomplete_fields = (
        "permit_type",
        "role",
    )

    list_select_related = (
        "permit_type",
        "role",
    )

    ordering = (
        "permit_type",
        "sequence",
        "role__name",
    )

    fieldsets = (
        (
            "Active Shift Role",
            {
                "fields": (
                    "permit_type",
                    "role",
                    "sequence",
                    "is_required",
                ),
                "description": (
                    "Defines which approval roles participate in each "
                    "active work shift for this permit type. "
                    "Sequence controls the approval order/display order."
                ),
            },
        ),
        AUDIT_FIELDSET,
    )