from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy

from accounts.models import UserQualification
from equipment.models import LocationTag
from permits.models import (
    Hazard,
    Permit,
    PermitHazard,
    PermitPrecaution,
    Precaution,
)
from work_orders.models.wo_models import WorkOrder


User = get_user_model()


class PermitCreateForm(forms.ModelForm):
    """
    Form for creating a Permit using the workflow-based Permit model.

    Workflow state fields such as workflow, current_step, activated_at,
    suspended_at, completed_at, and closed_at are managed by the workflow
    engine and are intentionally excluded from this form.
    """

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
                "hx-swap": "none",
            }
        ),
    )

    work_order = forms.ModelChoiceField(
        queryset=WorkOrder.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )

    work_supervisor = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=True,
        widget=forms.HiddenInput(),
    )

    designated_area_authority = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )

    designated_area_supervisor = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.HiddenInput(),
    )

    hazards = forms.ModelMultipleChoiceField(
        queryset=Hazard.objects.none(),
        required=False,
        label="Identified Hazards",
        widget=forms.CheckboxSelectMultiple(),
    )

    precautions = forms.ModelMultipleChoiceField(
        queryset=Precaution.objects.none(),
        required=False,
        label="Required Precautions",
        widget=forms.CheckboxSelectMultiple(),
    )

    class Meta:
        model = Permit

        fields = [
            # Identification
            "permit_number",
            "permit_type",
            "continuation_of",

            # Location and work order
            "location_tag",
            "work_order",
            "department",

            # Personnel
            "work_supervisor",
            "designated_area_authority",
            "designated_area_supervisor",

            # Work details
            "scope_of_work",
            "remarks",

            # Hazards and precautions
            "hazards",
            "precautions",

            # Duration and manpower
            "duration_value",
            "duration_unit",
            "estimated_personnel",

            # Tools and materials
            "electrical_tools",
            "mechanical_tools",
            "other_tools",
            "hazardous_materials",
            "non_explosion_proof_equipment",

            # Vehicle
            "vehicle_required",
            "vehicle_description",

            # Equipment preparation and isolation
            "mechanical_isolation",
            "equipment_depressurized",
            "equipment_drained",
            "equipment_purged",
            "process_isolation",
            "area_authority_present_required",
            "fire_watch_present_required",
            "equipment_preparation_notes",

            # Validity
            "valid_from",
            "valid_to",
        ]

        widgets = {
            "permit_number": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Permit number",
                }
            ),
            "permit_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "department": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "scope_of_work": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe the scope of work...",
                }
            ),
            "remarks": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Additional remarks...",
                }
            ),
            "hazards": forms.CheckboxSelectMultiple(),
            "precautions": forms.CheckboxSelectMultiple(),
            "duration_value": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
            "duration_unit": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "estimated_personnel": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                }
            ),
            "electrical_tools": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                }
            ),
            "mechanical_tools": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                }
            ),
            "other_tools": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                }
            ),
            "hazardous_materials": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                }
            ),
            "non_explosion_proof_equipment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                }
            ),
            "vehicle_required": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "vehicle_description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Vehicle description",
                }
            ),
            "mechanical_isolation": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "equipment_depressurized": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "equipment_drained": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "equipment_purged": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "process_isolation": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "area_authority_present_required": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "fire_watch_present_required": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
            "equipment_preparation_notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
            "valid_from": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
            "valid_to": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),
        }

        labels = {
            "scope_of_work": "Scope of Work",
            "remarks": "Remarks",
            "hazards": "Identified Hazards",
            "precautions": "Required Precautions",
            "duration_value": "Duration",
            "duration_unit": "Duration Unit",
            "estimated_personnel": "Estimated Personnel",
            "mechanical_isolation": "Mechanical Isolation",
            "equipment_depressurized": "Equipment Depressurized",
            "equipment_drained": "Equipment Drained",
            "equipment_purged": "Equipment Purged",
            "process_isolation": "Process Isolation",
            "area_authority_present_required": "Area Authority Present Required",
            "fire_watch_present_required": "Fire Watch Required",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.is_bound:
            location_tag_id = self.data.get("location_tag")
            continuation_of_id = self.data.get("continuation_of")
            work_order_id = self.data.get("work_order")
            work_supervisor_id = self.data.get("work_supervisor")
            area_authority_id = self.data.get("designated_area_authority")
            area_supervisor_id = self.data.get("designated_area_supervisor")

        elif self.instance.pk:
            location_tag_id = self.instance.location_tag_id
            continuation_of_id = self.instance.continuation_of_id
            work_order_id = self.instance.work_order_id
            work_supervisor_id = self.instance.work_supervisor_id
            area_authority_id = self.instance.designated_area_authority_id
            area_supervisor_id = self.instance.designated_area_supervisor_id

        else:
            location_tag_id = self.initial.get("location_tag")
            continuation_of_id = self.initial.get("continuation_of")
            work_order_id = self.initial.get("work_order")
            work_supervisor_id = self.initial.get("work_supervisor")
            area_authority_id = self.initial.get("designated_area_authority")
            area_supervisor_id = self.initial.get("designated_area_supervisor")

        self.fields["location_tag"].queryset = self._single_object_queryset(
            LocationTag,
            location_tag_id,
        )

        self.fields["continuation_of"].queryset = self._single_object_queryset(
            Permit,
            continuation_of_id,
        )

        self.fields["work_order"].queryset = self._single_object_queryset(
            WorkOrder,
            work_order_id,
        )

        self.fields["work_supervisor"].queryset = self._single_user_queryset(
            work_supervisor_id,
        )

        self.fields["designated_area_authority"].queryset = self._single_user_queryset(
            area_authority_id,
        )

        self.fields["designated_area_supervisor"].queryset = self._single_user_queryset(
            area_supervisor_id,
        )

        # Only active master data should be selectable.
        self.fields["hazards"].queryset = (
            Hazard.objects
            .filter(is_active=True)
            .order_by("display_order", "code")
        )

        self.fields["precautions"].queryset = (
            Precaution.objects
            .filter(is_active=True)
            .order_by("display_order", "code")
        )

    @staticmethod
    def _single_object_queryset(model, object_id):
        if not object_id:
            return model.objects.none()

        return model.objects.filter(pk=object_id)

    @staticmethod
    def _single_user_queryset(user_id):
        if not user_id:
            return User.objects.none()

        return User.objects.filter(
            pk=user_id,
            is_active=True,
        )

    def clean(self):
        cleaned_data = super().clean()

        valid_from = cleaned_data.get("valid_from")
        valid_to = cleaned_data.get("valid_to")

        if valid_from and valid_to and valid_to <= valid_from:
            self.add_error(
                "valid_to",
                "Valid To must be later than Valid From.",
            )

        vehicle_required = cleaned_data.get("vehicle_required")
        vehicle_description = cleaned_data.get("vehicle_description")

        if vehicle_required and not vehicle_description:
            self.add_error(
                "vehicle_description",
                "Vehicle description is required when a vehicle is required.",
            )

        continuation_of = cleaned_data.get("continuation_of")
        permit_number = cleaned_data.get("permit_number")

        if continuation_of and permit_number:
            if continuation_of.permit_number == permit_number:
                self.add_error(
                    "continuation_of",
                    "A permit cannot be a continuation of itself.",
                )

        return cleaned_data

    def save_assessments(self, *, user):
        if not self.instance.pk:
            raise ValueError(
                "The permit must be saved before hazards and precautions."
            )

        self._sync_assessments(
            through_model=PermitHazard,
            related_field="hazard",
            selected_objects=self.cleaned_data["hazards"],
            user=user,
        )
        self._sync_assessments(
            through_model=PermitPrecaution,
            related_field="precaution",
            selected_objects=self.cleaned_data["precautions"],
            user=user,
        )

    def _sync_assessments(
        self,
        *,
        through_model,
        related_field,
        selected_objects,
        user,
    ):
        selected_ids = {obj.pk for obj in selected_objects}
        related_id_field = f"{related_field}_id"

        active_records = list(
            through_model.objects.filter(
                permit=self.instance,
                is_active=True,
            )
        )
        active_ids = {
            getattr(record, related_id_field)
            for record in active_records
        }

        for record in active_records:
            if getattr(record, related_id_field) not in selected_ids:
                record.deactivate(user=user)

        for related_id in selected_ids - active_ids:
            inactive_record = (
                through_model.objects.filter(
                    permit=self.instance,
                    is_active=False,
                    **{related_id_field: related_id},
                )
                .order_by("-modified_at", "-pk")
                .first()
            )

            if inactive_record:
                inactive_record.reactivate(user=user)
                continue

            through_model.objects.create(
                permit=self.instance,
                created_by=user,
                modified_by=user,
                **{related_id_field: related_id},
            )


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
