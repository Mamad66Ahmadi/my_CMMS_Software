# equipment/forms/location_tag_create_form.py
from django import forms
from django.urls import reverse_lazy
from equipment.models.request_equipment_models import LocationTagChangeRequest
from equipment.models.equipment_models import LocationTag
class LocationTagCreateRequestForm(forms.ModelForm):

    parent = forms.ModelChoiceField(
        queryset=LocationTag.objects.all(),   # FIXED
        required=False,
        widget=forms.HiddenInput()
    )

    parent_search = forms.CharField(
        required=False,
        label="Parent Location Tag",
        widget=forms.TextInput(attrs={
            "id": "parent-search",
            "autocomplete": "off",
            "data-autocomplete-url": reverse_lazy("equipment:locationtag_autocomplete")
        })
    )

    class Meta:
        model = LocationTagChangeRequest
        fields = [
            "loc_tag",
            "parent_search",
            "parent",
            "description",
            "long_tag",
            "obj_criticality",
            "obj_type",
            "obj_category",
            "unit",
            "train",
            "note",
            "mih_level",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate queryset dynamically so the hidden ID is recognized
        self.fields["parent"].queryset = LocationTag.objects.all()

    def clean(self):
        cleaned_data = super().clean()

        parent_search = cleaned_data.get("parent_search")
        parent = cleaned_data.get("parent")

        if parent_search and not parent:
            raise forms.ValidationError(
                "The parent location tag you entered does not exist. Please select a valid tag."
            )

        return cleaned_data
