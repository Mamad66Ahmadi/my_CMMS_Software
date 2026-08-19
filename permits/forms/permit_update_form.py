from django import forms
from .permit_create_forms import PermitCreateForm
from permits.models import Permit, PermitHazard, PermitPrecaution
from permits.models.permit_fg_esd_models import PermitFireGasESD

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
            active_hazard_ids = list(
                PermitHazard.objects.filter(
                    permit=self.instance,
                    is_active=True,
                ).values_list("hazard_id", flat=True)
            )
            active_precaution_ids = list(
                PermitPrecaution.objects.filter(
                    permit=self.instance,
                    is_active=True,
                ).values_list("precaution_id", flat=True)
            )
            active_fire_gas_esd_ids = list(
                PermitFireGasESD.objects.filter(
                    permit=self.instance,
                ).values_list("fire_gas_esd_id", flat=True)
            )

            # model_to_dict() (run inside ModelForm.__init__) populates
            # self.initial["hazards"]/["precautions"] from the raw M2M
            # manager, which returns hazards/precautions linked via ANY
            # PermitHazard/PermitPrecaution row — active or not, since
            # the M2M manager doesn't filter on is_active. That form-level
            # self.initial value takes priority over field.initial when
            # Django resolves what's checked, so it must be corrected here
            # too, not just on the field.
            self.initial["hazards"] = active_hazard_ids
            self.initial["precautions"] = active_precaution_ids
            self.initial["fire_gas_esd_items"] = active_fire_gas_esd_ids

            self.fields["hazards"].initial = active_hazard_ids
            self.fields["precautions"].initial = active_precaution_ids
            self.fields["fire_gas_esd_items"].initial = active_fire_gas_esd_ids

    def clean_continuation_of(self):
        if self.instance and self.instance.pk:
            return self.instance.continuation_of

        return self.cleaned_data.get("continuation_of")
