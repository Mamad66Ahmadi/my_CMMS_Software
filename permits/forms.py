# permits/forms.py

from django import forms
from django.urls import reverse_lazy

from equipment.models import LocationTag
from permits.models import Permit
from work_orders.models.wo_models import WorkOrder


class PermitCreateForm(forms.ModelForm):
    location_tag = forms.ModelChoiceField(
        queryset=LocationTag.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )

    continuation_of = forms.ModelChoiceField(
        queryset=Permit.objects.none(),
        required=False,
        widget=forms.HiddenInput(
            attrs={
                "hx-get": reverse_lazy("permits:get_permit_data"),
                "hx-trigger": "change",
                "hx-target": "this",
                "hx-swap": "none",
            }
        ),
    )

    work_order = forms.ModelChoiceField(
        queryset=WorkOrder.objects.none(),
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

        location_tag_id = None
        continuation_of_id = None
        work_order_id = None

        if self.is_bound:
            location_tag_id = self.data.get("location_tag")
            continuation_of_id = self.data.get("continuation_of")
            work_order_id = self.data.get("work_order")
        elif self.instance.pk:
            location_tag_id = self.instance.location_tag_id
            continuation_of_id = self.instance.continuation_of_id
            work_order_id = self.instance.work_order_id
        else:
            location_tag_id = self.initial.get("location_tag")
            continuation_of_id = self.initial.get("continuation_of")
            work_order_id = self.initial.get("work_order")

        self.fields["location_tag"].queryset = (
            LocationTag.objects.filter(pk=location_tag_id)
            if location_tag_id else LocationTag.objects.none()
        )

        self.fields["continuation_of"].queryset = (
            Permit.objects.filter(pk=continuation_of_id)
            if continuation_of_id else Permit.objects.none()
        )

        self.fields["work_order"].queryset = (
            WorkOrder.objects.filter(pk=work_order_id)
            if work_order_id else WorkOrder.objects.none()
        )
