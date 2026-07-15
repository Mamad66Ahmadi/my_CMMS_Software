from django import forms
from permits.models import Permit
from equipment.models import LocationTag


class PermitCreateForm(forms.ModelForm):
    location_tag = forms.ModelChoiceField(
        queryset=LocationTag.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )

    class Meta:
        model = Permit
        exclude = ["status", "created_by", "modified_by"]
        widgets = {
            "valid_from": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "valid_to": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        selected_id = None
        if self.is_bound:
            selected_id = self.data.get("location_tag")
        elif self.instance.pk and self.instance.location_tag_id:
            selected_id = self.instance.location_tag_id
        elif self.initial.get("location_tag"):
            selected_id = self.initial.get("location_tag")

        if selected_id:
            self.fields["location_tag"].queryset = LocationTag.objects.filter(pk=selected_id)
        else:
            self.fields["location_tag"].queryset = LocationTag.objects.none()
