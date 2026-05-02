# equipment/forms/equipment_change_form.py
from django import forms
from django.forms import modelformset_factory, inlineformset_factory
from django.urls import reverse_lazy
from equipment.models.equipment_models import Equipment
from equipment.models.request_equipment_models import EquipmentChangeRequest, EquipmentDocumentChangeRequest
from equipment.models.equipment_models import LocationTag


class EquipmentChangeRequestForm(forms.ModelForm):

    functional_location = forms.ModelChoiceField(
        queryset=LocationTag.objects.none(),
        required=False,
        widget=forms.HiddenInput()
    )

    functional_location_search = forms.CharField(
        required=False,
        label="Functional Location",
        widget=forms.TextInput(attrs={
            "id": "location-search",
            "autocomplete": "off",
            "data-autocomplete-url": reverse_lazy("equipment:locationtag_autocomplete")
        })
    )

    class Meta:
        model = EquipmentChangeRequest
        fields = [
            "functional_location_search",
            "functional_location",
            "serial_number",
            "manufacturer",
            "model",
            "note",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Pre-fill search input
        if "initial" in kwargs and kwargs["initial"].get("functional_location"):
            loc_obj = kwargs["initial"]["functional_location"]
            self.fields["functional_location_search"].initial = loc_obj.loc_tag

        # 2. Make sure POSTed parent value resolves
        if "functional_location" in self.data:
            try:
                loc_id = int(self.data.get("functional_location"))
                self.fields["functional_location"].queryset = LocationTag.objects.filter(pk=loc_id)
            except Exception:
                pass

    def clean(self):
        cleaned = super().clean()

        search = cleaned.get("functional_location_search")
        floc = cleaned.get("functional_location")

        # case 1: blank input -> allowed
        if not search:
            return cleaned

        # case 2: user typed something but did not select a valid tag
        if search and not floc:
            raise forms.ValidationError(
                "The functional location you entered does not exist. Please choose one from the list."
            )

        return cleaned


class EquipmentDocumentChangeRequestForm(forms.ModelForm):
    class Meta:
        model = EquipmentDocumentChangeRequest
        fields = ["file", "file_name", "description"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
        }

# If you want multiple docs per request:
EquipmentDocumentChangeRequestFormSet = inlineformset_factory(
    EquipmentChangeRequest,
    EquipmentDocumentChangeRequest,
    form=EquipmentDocumentChangeRequestForm,
    extra=1,          # how many empty rows to show initially
    can_delete=True,  # allow user to remove a row
)