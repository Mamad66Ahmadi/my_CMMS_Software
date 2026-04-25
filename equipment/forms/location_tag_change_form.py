from django import forms
from django.urls import reverse_lazy
from equipment.models.request_equipment_models import LocationTagChangeRequest
from equipment.models.equipment_models import LocationTag

class LocationTagChangeRequestForm(forms.ModelForm):

    parent = forms.ModelChoiceField(
        queryset=LocationTag.objects.none(),
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

        # 1. Set existing parent in search box
        if "initial" in kwargs and kwargs["initial"].get("parent"):
            parent_obj = kwargs["initial"]["parent"]
            self.fields["parent_search"].initial = parent_obj.loc_tag

        # 2. Ensure parent queryset is valid when POSTing
        if "parent" in self.data:
            try:
                parent_id = int(self.data.get("parent"))
                self.fields["parent"].queryset = LocationTag.objects.filter(pk=parent_id)
            except (TypeError, ValueError):
                pass

        # 3. When editing an existing request — (not used now)
        elif self.instance and getattr(self.instance, "parent", None):
            self.fields["parent"].queryset = LocationTag.objects.filter(
                pk=self.instance.parent.pk
            )

    def clean(self):
        cleaned_data = super().clean()

        parent_search = cleaned_data.get("parent_search")
        parent = cleaned_data.get("parent")

        # User typed something but didn't select a valid tag
        if parent_search and not parent:
            raise forms.ValidationError(
                "The parent location tag you entered does not exist. Please select a valid tag from the list."
            )

        return cleaned_data