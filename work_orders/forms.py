from django import forms
from django.core.exceptions import ValidationError

from work_orders.models.wo_models import WorkOrderTask
from work_orders.models.fault_report_models import FaultReport


class FaultReportCreateForm(forms.ModelForm):
    class Meta:
        model = FaultReport
        fields = [
            "location_tag",
            "equipment",
            "directive",
            "project_code",
            "detection_method",
            "work_type",
            "parent_work_order_number",
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
            "detection_method": forms.Select(attrs={"class": "form-select"}),
            "work_type": forms.Select(attrs={"class": "form-select"}),
            "parent_work_order_number": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": 30,
                "placeholder": "Enter parent work order number (optional)",
            }),
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
        instance.detection_method = cleaned.get("detection_method")
        instance.work_type = cleaned.get("work_type")
        instance.parent_work_order_number = cleaned.get("parent_work_order_number")
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




class WorkOrderTaskForm(forms.ModelForm):
    class Meta:
        model = WorkOrderTask
        # Exclude internal/system-managed fields; include editables
        exclude = [
            'work_order', 
            'task_number', 
            'is_main_task', 
            'created_at', 
            'created_by', 
            'modified_at', 
            'modified_by', 
            'modified_itam'
        ]
        widgets = {
            'planned_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'planned_finish': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'actual_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'actual_finish': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'directive': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'work_done_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'waiting_history': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'readonly': 'readonly'}),
            'remarks': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'task_requester_department': forms.Select(attrs={'class': 'form-select'}),
            'task_executing_department': forms.Select(attrs={'class': 'form-select'}),
            'performed_action': forms.Select(attrs={'class': 'form-select'}),
            'awaiting_reason': forms.Select(attrs={'class': 'form-select'}),
            'planner': forms.Select(attrs={'class': 'form-select'}),
            'work_master': forms.Select(attrs={'class': 'form-select'}),
            'work_leader': forms.Select(attrs={'class': 'form-select'}),
            'permit': forms.TextInput(attrs={'class': 'form-control'}),
        }
