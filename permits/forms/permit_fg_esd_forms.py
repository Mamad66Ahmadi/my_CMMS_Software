# permits/forms/permit_fg_esd_forms.py

from django import forms


class PermitFireGasESDSignoffForm(forms.Form):
    """
    Used to record an isolation or a de-isolation signoff for a single
    PermitFireGasESD row.

    The item and the action (isolate/deisolate) are supplied by the URL,
    never by the browser; this form only captures the actual time and a
    confirmation checkbox.
    """

    time = forms.DateTimeField(
        required=True,
        widget=forms.DateTimeInput(
            format="%Y-%m-%dT%H:%M",
            attrs={
                "class": "form-control",
                "type": "datetime-local",
            },
        ),
    )

    confirm = forms.BooleanField(
        required=True,
        label="I confirm this information is correct.",
        widget=forms.CheckboxInput(
            attrs={
                "class": "form-check-input",
            }
        ),
    )
