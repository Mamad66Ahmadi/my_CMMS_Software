# daily_reports/forms.py
from django import forms
from django.urls import reverse_lazy
from django.core.exceptions import ValidationError
from .models import DailyReport
from equipment.models.equipment_models import LocationTag

class DailyReportForm(forms.ModelForm):
    location_tag = forms.ModelChoiceField(
        queryset=LocationTag.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )

    location_tag_search = forms.CharField(
        required=False,
        label="Location Tag",
        widget=forms.TextInput(attrs={
            "id": "location-search",
            "autocomplete": "off",
            "class": "form-control",
            "data-autocomplete-url": "/equipment/locationtag-autocomplete/"
        })
    )

    class Meta:
        model = DailyReport
        fields = ['date', 'location_tag_search', 'location_tag', 'wo_number',
                  'actual_start', 'description', 'status', 'employees', 'department']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'actual_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'wo_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control','rows': 3,'dir': 'auto'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'employees': forms.TextInput(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['location_tag_search'].required = False
        self.fields['status'].required = True
        self.fields['department'].required = True

        self.fields['location_tag_search'].widget.attrs['data-autocomplete-url'] = reverse_lazy('equipment:locationtag_autocomplete')

        if self.request and hasattr(self.request.user, 'department'):
            self.fields['department'].initial = self.request.user.department

        if self.instance and self.instance.pk and self.instance.location_tag:
            self.fields['location_tag_search'].initial = self.instance.location_tag.loc_tag

    def clean(self):
        cleaned = super().clean()

        date = cleaned.get("date")
        actual_start = cleaned.get("actual_start")
        description = (cleaned.get("description") or "").strip()
        department = cleaned.get("department")
        status = cleaned.get("status")
        location_tag = cleaned.get("location_tag")

        errors = {}

        # required fields
        if not date:
            errors["date"] = "Date is required."
        if not department:
            errors["department"] = "Department is required."
        if not status:
            errors["status"] = "Status is required."
        if not description:
            errors["description"] = "Description is required."

        # optional but recommended for your flow (since location is chosen first)
        if not location_tag:
            errors["location_tag_search"] = "Please select a valid location tag from the list."

        # actual_start rule
        if date and actual_start and actual_start > date:
            errors["actual_start"] = "Actual start cannot be after the report date."

        if errors:
            raise ValidationError(errors)

        cleaned["description"] = description
        return cleaned
