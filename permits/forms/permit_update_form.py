from django import forms
from .permit_create_forms import PermitCreateForm
from permits.models import Permit, PermitHazard, PermitPrecaution


class PermitUpdateForm(PermitCreateForm):
    immutable_fields = (
        "permit_number",
        "permit_type",
        "continuation_of",
    )

    class Meta(PermitCreateForm.Meta):
        fields = PermitCreateForm.Meta.fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk:
            self.fields["permit_number"].initial = self.instance.permit_number
            self.fields["permit_type"].initial = self.instance.permit_type_id
            self.fields["continuation_of"].initial = self.instance.continuation_of_id

            self.fields["continuation_of"].queryset = self._single_object_queryset(
                Permit,
                self.instance.continuation_of_id,
            )

        for field_name in self.immutable_fields:
            if field_name in self.fields:
                self.fields[field_name].disabled = True

        self.fields["continuation_of"].widget = forms.HiddenInput()

        if self.instance and self.instance.pk and not self.is_bound:
            self.fields["hazards"].initial = list(
                PermitHazard.objects.filter(
                    permit=self.instance,
                    is_active=True,
                ).values_list("hazard_id", flat=True)
            )

            self.fields["precautions"].initial = list(
                PermitPrecaution.objects.filter(
                    permit=self.instance,
                    is_active=True,
                ).values_list("precaution_id", flat=True)
            )

    def clean_continuation_of(self):
        if self.instance and self.instance.pk:
            return self.instance.continuation_of

        return self.cleaned_data.get("continuation_of")
