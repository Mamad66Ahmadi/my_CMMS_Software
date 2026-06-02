from django import forms
from django.core.exceptions import ValidationError

from work_orders.models.fault_report_models import FaultReport


class FaultReportCreateForm(forms.ModelForm):
    class Meta:
        model = FaultReport
        fields = [
            "location_tag",
            "equipment",
            "directive",
            "fault_desc",
            "priority",
            "symptom",
            "is_breakdown",
        ]
        widgets = {
            "location_tag": forms.HiddenInput(),
            "equipment": forms.Select(attrs={"class": "form-select"}),
            "directive": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 255,
                "placeholder": "Enter directive",
            }),
            "fault_desc": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the fault",
            }),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "symptom": forms.Select(attrs={"class": "form-select"}),
            "is_breakdown": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean(self):
        cleaned = super().clean()

        instance = FaultReport(
            location_tag=cleaned.get("location_tag"),
            equipment=cleaned.get("equipment"),
            directive=cleaned.get("directive") or "",
            fault_desc=cleaned.get("fault_desc") or "",
            priority=cleaned.get("priority"),
            symptom=cleaned.get("symptom"),
            is_breakdown=cleaned.get("is_breakdown") or False,
        )

        try:
            instance.full_clean(exclude=[
                "report_number",
                "reported_by",
                "reported_department",
                "reported_at",
                "status",
                "reviewed_by",
                "reviewed_at",
                "planner",
                "planner_reviewed_at",
                "review_comment",
            ])
        except ValidationError as e:
            if hasattr(e, "message_dict"):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        self.add_error(field if field in self.fields else None, error)
            else:
                self.add_error(None, e)

        return cleaned
