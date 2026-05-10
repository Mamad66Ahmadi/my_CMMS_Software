from django import forms
from django.urls import reverse_lazy
from equipment.models.request_equipment_models import LocationTagChangeRequest
from equipment.models.equipment_models import LocationTag

class LocationTagRequestForm(forms.ModelForm):

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

        parent_obj = None

        # 1️⃣ POST data
        if "parent" in self.data:
            try:
                parent_id = int(self.data.get("parent"))
                parent_obj = LocationTag.objects.filter(pk=parent_id).first()
            except (TypeError, ValueError):
                parent_obj = None

        # 2️⃣ initial data
        elif self.initial.get("parent"):
            parent_value = self.initial["parent"]

            if isinstance(parent_value, LocationTag):
                parent_obj = parent_value
            else:
                parent_obj = LocationTag.objects.filter(pk=parent_value).first()

        # 3️⃣ instance
        elif self.instance and getattr(self.instance, "parent", None):
            parent_obj = self.instance.parent

        if parent_obj:
            self.fields["parent"].queryset = LocationTag.objects.filter(pk=parent_obj.pk)
            self.initial["parent"] = parent_obj.pk
            self.fields["parent_search"].initial = parent_obj.loc_tag
        else:
            self.fields["parent"].queryset = LocationTag.objects.none()

    def clean(self):
        cleaned_data = super().clean()

        parent_search = cleaned_data.get("parent_search")
        parent = cleaned_data.get("parent")

        if parent_search and not parent:
            raise forms.ValidationError(
                "The parent location tag you entered does not exist. Please select a valid tag."
            )

        return cleaned_data
