from django import forms
from django.contrib import admin

from permits.models.permit_shift_models import (
    PermitWorkShift,
    Shift,
)


class PermitWorkShiftForm(forms.ModelForm):
    class Meta:
        model = PermitWorkShift
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()

        permit = cleaned_data.get("permit")
        date = cleaned_data.get("date")
        shift = cleaned_data.get("shift")

        if permit and date and shift:
            qs = PermitWorkShift.objects.filter(
                permit=permit,
                date=date,
                shift=shift,
            )

            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    "This permit already has a work shift registered "
                    "for this date and shift."
                )

        return cleaned_data


@admin.register(PermitWorkShift)
class PermitWorkShiftAdmin(admin.ModelAdmin):
    form = PermitWorkShiftForm

    list_display = (
        "permit",
        "date",
        "shift",
        "work_leader",
        "worker_count",
        "status",
        "created_by",
        "created_at",
        "signoff_status",
    )

    list_filter = (
        "shift",
        "date",
        "status",
    )

    search_fields = (
        "permit__permit_number",
        "work_leader",
        "created_by__username",
        "created_by__first_name",
        "created_by__last_name",
    )

    autocomplete_fields = (
        "permit",
        "created_by",
        "closed_by",
    )

    list_select_related = (
        "permit",
        "created_by",
        "closed_by",
    )

    readonly_fields = (
        "created_at",
        "created_by",
        "status",
        "closed_at",
        "closed_by",
    )

    ordering = (
        "-date",
        "shift",
    )

    fieldsets = (
        (
            "Work Shift",
            {
                "fields": (
                    "permit",
                    "date",
                    "shift",
                    "work_leader",
                    "worker_count",
                ),
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "closed_at",
                    "closed_by",
                ),
                "description": (
                    "Work shifts are opened and closed through the shift "
                    "workflow; these fields are read-only in admin."
                ),
            },
        ),
        (
            "Audit Information",
            {
                "classes": ("collapse",),
                "fields": (
                    "created_at",
                    "created_by",
                ),
            },
        ),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)

    @admin.display(description="Signoffs")
    def signoff_status(self, obj):
        total = obj.signoffs.count()
        signed = obj.signoffs.filter(
            signed_by__isnull=False,
            signed_at__isnull=False,
        ).count()

        if total == 0:
            return "No signoffs"

        if signed == total:
            return f"Complete ({signed}/{total})"

        return f"Pending ({signed}/{total})"
