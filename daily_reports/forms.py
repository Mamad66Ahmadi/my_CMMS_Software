# daily_reports/forms.py
from django import forms
from django.utils import timezone

from .models import DailyReport, DailyReportStatus
from equipment.models.equipment_models import LocationTag

class DailyReportForm(forms.ModelForm):
    location_tag = forms.ModelChoiceField(
        queryset=LocationTag.objects.all(),
        widget=forms.HiddenInput(attrs={"id": "id_location_tag"})
    )

    class Meta:
        model = DailyReport
        fields = [
            "date", "actual_start", "location_tag", "status", 
            "wo_number", "description", "employees", "department"
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "actual_start": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "status": forms.Select(attrs={"class": "form-select"}),
            "description": forms.Textarea(attrs={
                "class": "form-control multi-lang-input", 
                "rows": 4,
                'placeholder': 'Enter your report...'
            }),
            # Changed "form-select" to "form-control" and kept it as Textarea based on your placeholder
            "employees": forms.Textarea(attrs={
                "class": "form-control multi-lang-input", 
                "rows": 2, 
                'placeholder': 'List names separated by commas (e.g., عباس شاه امیری، سیدعلی میرمحمدی)'
            }),
            "wo_number": forms.TextInput(attrs={"class": "form-control"}),
            "department": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make the first choice of status an empty placeholder like "-----"
        self.fields["status"].empty_label = "---------"

    def clean_actual_start(self):
        actual_start = self.cleaned_data.get("actual_start")
        date = self.cleaned_data.get("date")

        # mandatory and must be <= date
        if not actual_start:
            raise forms.ValidationError("Actual start date is required.")
        if date and actual_start > date:
            raise forms.ValidationError("Actual start cannot be later than the report date.")
        return actual_start

    def clean_status(self):
        status = self.cleaned_data.get("status")
        if not status:
            raise forms.ValidationError("Status is required.")
        return status

    def clean_description(self):
        description = self.cleaned_data.get("description")
        if not description:
            raise forms.ValidationError("Description is required.")
        return description
