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
            # Force the full path here to debug if reverse_lazy is failing
            "data-autocomplete-url": "/equipment/locationtag-autocomplete/" 
        })
    )
    class Meta:
        model = DailyReport
        fields = ['date', 'location_tag_search', 'location_tag', 'wo_number', 'actual_start', 'description', 'status', 'employees', 'department']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'actual_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'wo_number': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'dir': 'auto', # This detects if text is RTL or LTR automatically
                'placeholder': 'Enter description here...'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'employees': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter worker names separated by commas'
            }),
            'department': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['location_tag_search'].required = True
        self.fields['status'].required = True
        self.fields['department'].required = True
        # Set autocomplete URL
        self.fields['location_tag_search'].widget.attrs['data-autocomplete-url'] = reverse_lazy('equipment:locationtag_autocomplete')
        
        # Default department
        if self.request and hasattr(self.request.user, 'department'):
            self.fields['department'].initial = self.request.user.department

        # Pre-fill search
        if self.instance and self.instance.pk and self.instance.location_tag:
            self.fields['location_tag_search'].initial = self.instance.location_tag.loc_tag

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get("date")
        actual_start = cleaned_data.get("actual_start")
        location_tag = cleaned_data.get("location_tag")
        status = cleaned_data.get("status")
        department = cleaned_data.get("department")

        # 1. Date Validation
        if date and actual_start and actual_start < date:
            raise ValidationError({"actual_start": "Actual Start cannot be before the Report Date."})

        # 2. Required Fields
        if not location_tag:
            raise ValidationError({"location_tag_search": "Location Tag is required."})
        
        if not status:
            raise ValidationError({"status": "Status is required."})

        # 3. Department Check (Storing this in a way we can check in JS)
        # We'll add a flag to the form instance
        self.department_changed = (self.request.user.department != department)
        
        return cleaned_data