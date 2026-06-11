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
            "project_code",
            "fault_desc",
            "priority",
            "symptom",
            "executing_department",
        ]
        widgets = {
            "location_tag": forms.HiddenInput(),
            "equipment": forms.Select(attrs={"class": "form-select"}),
            "directive": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 255,
                "placeholder": "Enter directive",
            }),
            "project_code": forms.Select(attrs={"class": "form-select"}),
            "fault_desc": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Describe the fault",
            }),
            "priority": forms.Select(attrs={"class": "form-select"}),
            "symptom": forms.Select(attrs={"class": "form-select"}),
            "executing_department": forms.Select(attrs={"class": "form-select"}),
        }

    def clean(self):
        cleaned = super().clean()

        instance = self.instance
        instance.location_tag = cleaned.get("location_tag")
        instance.equipment = cleaned.get("equipment")
        instance.directive = cleaned.get("directive")
        instance.project_code = cleaned.get("project_code")
        instance.fault_desc = cleaned.get("fault_desc")
        instance.priority = cleaned.get("priority")
        instance.symptom = cleaned.get("symptom")
        instance.executing_department = cleaned.get("executing_department")

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
