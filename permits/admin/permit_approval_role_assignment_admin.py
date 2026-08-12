# permits/admin/permit_approval_role_assignment_admin.py

from django import forms
from django.contrib import admin

from permits.admin.base_admin import AUDIT_FIELDSET, TimeStampedAdmin
from permits.models.approval_models import (
    PermitApprovalRoleAssignment,
)


class PermitApprovalRoleAssignmentForm(forms.ModelForm):
    class Meta:
        model = PermitApprovalRoleAssignment
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        all_units = cleaned_data.get("all_units")
        units = cleaned_data.get("units")

        if all_units and units:
            raise forms.ValidationError(
                {
                    "units": (
                        "An assignment with all-units access cannot also "
                        "contain selected units."
                    )
                }
            )

        return cleaned_data


@admin.register(PermitApprovalRoleAssignment)
class PermitApprovalRoleAssignmentAdmin(TimeStampedAdmin):
    form = PermitApprovalRoleAssignmentForm

    list_display = (
        "user",
        "role",
        "permit_type",
        "department",
        "all_units",
        "is_active",
        "created_at",
        "modified_at",
    )

    list_filter = (
        "role",
        "permit_type",
        "department",
        "all_units",
        "is_active",
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "role__code",
        "role__name",
        "department__department_code",
        "department__name",
        "permit_type__code",
        "permit_type__name",
    )

    list_select_related = (
        "user",
        "role",
        "permit_type",
        "department",
    )

    filter_horizontal = (
        "units",
    )

    fieldsets = (
        (
            "Assignment",
            {
                "fields": (
                    "user",
                    "role",
                    "is_active",
                ),
            },
        ),
        (
            "Permit Scope",
            {
                "fields": (
                    "permit_type",
                    "department",
                ),
            },
        ),
        (
            "Unit Scope",
            {
                "fields": (
                    "all_units",
                    "units",
                ),
                "description": (
                    "Use all-units access for roles that are not restricted "
                    "to selected units. For department-only roles, leave "
                    "all_units disabled and leave units empty."
                ),
            },
        ),
        AUDIT_FIELDSET,
    )
