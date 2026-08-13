from django import forms
from django.utils import timezone

from permits.models.permit_shift_models import (
    PermitWorkShift,
    PermitShiftSignoff,
    PermitTypeActiveShiftRole,
    Shift,
)


class PermitWorkShiftForm(forms.ModelForm):
    """
    Form used by Permit Office to create a work shift
    for an ACTIVE permit.
    """

    def __init__(self, *args, permit=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.permit = permit

    class Meta:
        model = PermitWorkShift
        fields = (
            "date",
            "shift",
            "work_leader",
        )

        widgets = {
            "date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "form-control",
                }
            ),
            "shift": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "work_leader": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Enter work leader",
                    "maxlength": 45,
                }
            ),
        }

        labels = {
            "date": "Work Date",
            "shift": "Shift",
            "work_leader": "Work Leader",
        }

    def clean(self):
        cleaned_data = super().clean()

        date = cleaned_data.get("date")
        shift = cleaned_data.get("shift")

        if not self.permit or not date or not shift:
            return cleaned_data

        queryset = PermitWorkShift.objects.filter(
            permit=self.permit,
            date=date,
            shift=shift,
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                {
                    "shift": (
                        "A work shift already exists for this "
                        "permit on the selected date and shift."
                    )
                }
            )

        # ----------------------------------------------------------
        # Validate against permit validity
        # ----------------------------------------------------------

        if self.permit.valid_from:
            if date < timezone.localtime(self.permit.valid_from).date():
                raise forms.ValidationError(
                    {
                        "date": (
                            "The work-shift date cannot be before "
                            "the permit valid-from date."
                        )
                    }
                )

        if self.permit.valid_to:
            if date > timezone.localtime(self.permit.valid_to).date():
                raise forms.ValidationError(
                    {
                        "date": (
                            "The work-shift date cannot be after "
                            "the permit valid-to date."
                        )
                    }
                )

        return cleaned_data


class PermitShiftSignoffForm(forms.Form):
    """
    Form used to confirm a shift signoff.

    The role is supplied by the server and should not be freely
    selectable by the user.
    """

    confirm = forms.BooleanField(
        required=True,
        label="I confirm that I have completed this signoff.",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )

class PermitTypeActiveShiftRoleForm(forms.ModelForm):
    """
    Defines which approval roles are required for work shifts
    of a particular PermitType.
    """

    class Meta:
        model = PermitTypeActiveShiftRole
        fields = (
            "permit_type",
            "role",
            "sequence",
            "is_required",
        )

        widgets = {
            "permit_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "role": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "sequence": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1,
                }
            ),
            "is_required": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

    def clean_sequence(self):
        sequence = self.cleaned_data["sequence"]

        if sequence < 1:
            raise forms.ValidationError(
                "Sequence must be greater than zero."
            )

        return sequence

    def clean(self):
        cleaned_data = super().clean()

        permit_type = cleaned_data.get("permit_type")
        role = cleaned_data.get("role")

        if not permit_type or not role:
            return cleaned_data

        queryset = PermitTypeActiveShiftRole.objects.filter(
            permit_type=permit_type,
            role=role,
        )

        if self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise forms.ValidationError(
                {
                    "role": (
                        "This role is already configured for "
                        "this permit type."
                    )
                }
            )

        return cleaned_data
