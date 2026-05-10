# equipment/forms/equipment_change_form.py
from django import forms
from django.urls import reverse_lazy
from equipment.models.request_equipment_models import EquipmentChangeRequest, EquipmentDocumentChangeRequest
from equipment.models.equipment_models import LocationTag


class EquipmentChangeRequestForm(forms.ModelForm):

    functional_location = forms.ModelChoiceField(
        queryset=LocationTag.objects.all(),
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
        initial = kwargs.get("initial", {})
        super().__init__(*args, **kwargs)

        # 1. Determine which ID to use (Priority: POST data > Initial data)
        # Use add_prefix to handle cases where the form might have a prefix
        field_name = self.add_prefix("functional_location")
        
        # Check submitted data first
        submitted_val = self.data.get(field_name)
        # Check initial data second
        initial_val = initial.get("functional_location")

        if submitted_val:
            try:
                # If it's a POST request with a value, limit queryset to that value
                self.fields["functional_location"].queryset = (
                    LocationTag.objects.filter(pk=int(submitted_val))
                )
            except (TypeError, ValueError):
                self.fields["functional_location"].queryset = LocationTag.objects.none()

        elif initial_val:
            # If it's a GET request, use the initial object
            loc = initial_val
            self.fields["functional_location_search"].initial = loc.loc_tag
            self.initial["functional_location"] = loc.pk
            self.fields["functional_location"].queryset = (
                LocationTag.objects.filter(pk=loc.pk)
            )
        else:
            # No data and no initial: empty queryset
            self.fields["functional_location"].queryset = LocationTag.objects.none()

    def clean(self):
        cleaned = super().clean()

        search = cleaned.get("functional_location_search")
        floc = cleaned.get("functional_location")

        # case 1: blank input -> allowed
        if not search:
            return cleaned

        # case 2: user typed something but did not select a valid tag
        if search and not cleaned.get("functional_location"):
            self.add_error(
                "functional_location_search",
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





class EquipmentRequestReviewForm(forms.ModelForm):
    functional_location = forms.ModelChoiceField(
        queryset=LocationTag.objects.none(), # Start empty
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
        fields = ["functional_location_search", "functional_location", "serial_number", "manufacturer", "model", "note"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # 1. Determine the ID to use
        # Check POST data first (Reviewer changed it), then initial, then instance
        field_name = self.add_prefix("functional_location")
        submitted_id = self.data.get(field_name)
        
        if submitted_id:
            # Reviewer is submitting a change
            try:
                self.fields["functional_location"].queryset = LocationTag.objects.filter(pk=int(submitted_id))
            except (ValueError, TypeError):
                self.fields["functional_location"].queryset = LocationTag.objects.none()
        
        elif self.instance and self.instance.pk:
            # Loading the form (GET) - use values from the Request object
            loc = self.instance.functional_location
            if loc:
                self.fields["functional_location"].queryset = LocationTag.objects.filter(pk=loc.pk)
                self.fields["functional_location_search"].initial = loc.loc_tag
                self.initial["functional_location"] = loc.pk

    def clean(self):
        cleaned = super().clean()
        search = cleaned.get("functional_location_search")
        floc = cleaned.get("functional_location")

        # If text is entered but no ID is selected via autocomplete
        if search and not floc:
            self.add_error("functional_location_search", "Please select a valid location from the list.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        # Ensure the hidden field value is explicitly set to the model field
        obj.functional_location = self.cleaned_data.get("functional_location")
        if commit:
            obj.save()
        return obj
