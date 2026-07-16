# permits/forms.py

from django import forms
from django.urls import reverse_lazy

from equipment.models import LocationTag
from permits.models import Permit
from work_orders.models.wo_models import WorkOrder
from accounts.models import UserQualification
from django.contrib.auth import get_user_model


User = get_user_model()

# ------------------------------- Create Permit Form ---------------------
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



# -------------- PIS -------------------------
class AddPISQualificationForm(forms.ModelForm):
    class Meta:
        model = UserQualification
        fields = ["user", "granted_date", "expiry_date", "note"]
        widgets = {
            "user": forms.HiddenInput(),
            "granted_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "expiry_date": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "note": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(is_active=True).order_by(
            "personnel_number"
        )
        self.fields["user"].empty_label = "Select a user"

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get("user")
        granted_date = cleaned_data.get("granted_date")
        expiry_date = cleaned_data.get("expiry_date")

        if granted_date and expiry_date and expiry_date < granted_date:
            self.add_error(
                "expiry_date",
                "Expiry date cannot be earlier than granted date.",
            )

        if user:
            if UserQualification.objects.filter(
                user=user,
                qualification__code__iexact="PIS",
            ).exists():
                self.add_error("user", "This user already has PIS qualification.")

        return cleaned_data