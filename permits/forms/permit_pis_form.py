
from django import forms
from accounts.models import UserQualification
from django.contrib.auth import get_user_model

User = get_user_model()
# -------------- PIS -------------------------

class AddPISQualificationForm(forms.ModelForm):
    class Meta:
        model = UserQualification
        fields = [
            "user",
            "granted_date",
            "expiry_date",
            "note",
        ]
        widgets = {
            "user": forms.HiddenInput(),
            "granted_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "expiry_date": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "note": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["user"].queryset = (
            User.objects
            .filter(is_active=True)
            .order_by("personnel_number")
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
            exists = UserQualification.objects.filter(
                user=user,
                qualification__code__iexact="PIS",
            ).exists()

            if exists:
                self.add_error(
                    "user",
                    "This user already has PIS qualification.",
                )

        return cleaned_data
