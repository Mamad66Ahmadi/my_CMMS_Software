# permits/forms/permit_create_form.py

from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from types import SimpleNamespace

from equipment.models import LocationTag
from permits.models import (
    Hazard,
    Permit,
    PermitHazard,
    PermitPrecaution,
    Precaution,
)
from permits.models.permit_fg_esd_models import FireGasESD, PermitFireGasESD
from permits.services.fire_gas_esd_service import PermitFireGasESDService
from work_orders.models.wo_models import WorkOrder
from permits.models.workflow_models import Decision
from permits.models.workflow_models import PermitWorkflowStep


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

    fire_gas_esd_items = forms.ModelMultipleChoiceField(
        queryset=FireGasESD.objects.none(),
        required=False,
        label="Fire, Gas & ESD Isolations",
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

            # Fire, Gas & ESD isolations
            "fire_gas_esd_items",

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
            "fire_gas_esd_items": forms.CheckboxSelectMultiple(),
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
            "fire_gas_esd_items": "Fire, Gas & ESD Isolations",
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

            self._fg_esd_row_errors = {}


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

            if (
                not self.is_bound
                and continuation_of_id
                and not self.initial.get("permit_type")
            ):
                continuation_permit = (
                    Permit.objects
                    .select_related("permit_type")
                    .filter(pk=continuation_of_id)
                    .first()
                )
                if continuation_permit:
                    self.initial["permit_type"] = continuation_permit.permit_type_id
                    self.fields["permit_type"].initial = (
                        continuation_permit.permit_type_id
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

            self.fields["fire_gas_esd_items"].queryset = (
                PermitFireGasESDService.get_active_master_items()
            )

            # Existing remarks, keyed by str(item_id) -> remark text.
            # Empty on create (no instance yet); populated on update.
            self._hazard_remarks = self._existing_remarks_map(
                through_model=PermitHazard,
                related_field="hazard",
            )
            self._precaution_remarks = self._existing_remarks_map(
                through_model=PermitPrecaution,
                related_field="precaution",
            )

            # Existing Fire/Gas/ESD rows, keyed by str(fire_gas_esd_id).
            # Empty on create (no instance yet); populated on update.
            self._fg_esd_rows_map = self._existing_fg_esd_rows_map()

    def _existing_remarks_map(self, *, through_model, related_field):
        if not (self.instance and self.instance.pk):
            return {}

        related_id_field = f"{related_field}_id"

        return {
            str(getattr(record, related_id_field)): record.remarks
            for record in through_model.objects.filter(
                permit=self.instance,
                is_active=True,
            )
        }

    def _existing_fg_esd_rows_map(self):
        if not (self.instance and self.instance.pk):
            return {}

        return {
            str(record.fire_gas_esd_id): record
            for record in PermitFireGasESD.objects.filter(
                permit=self.instance,
            )
        }

    @property
    def hazard_rows(self):
        return self._build_rows(
            field_name="hazards",
            remark_prefix="hazard_remarks",
            remarks_map=self._hazard_remarks,
        )

    @property
    def precaution_rows(self):
        return self._build_rows(
            field_name="precautions",
            remark_prefix="precaution_remarks",
            remarks_map=self._precaution_remarks,
        )

    @property
    def fire_gas_esd_rows(self):
        """
        One row per active FireGasESD master item, mirroring hazard_rows/
        precaution_rows, but carrying the extra unit_zone field and any
        existing isolation / de-isolation state (read-only here; signing
        is handled separately by PermitFireGasESDService/views).
        """
        rows = []

        for checkbox in self["fire_gas_esd_items"]:
            item_id = checkbox.data["value"]
            existing = self._fg_esd_rows_map.get(str(item_id))

            if self.is_bound:
                # Re-render after a failed submit: show what the user typed.
                unit_zone = (
                    self.data.get(f"fg_esd_unit_zone_{item_id}") or ""
                ).strip()
                remark = (
                    self.data.get(f"fg_esd_remarks_{item_id}") or ""
                ).strip()
            else:
                unit_zone = existing.unit_zone if existing else ""
                remark = existing.remarks if existing else ""

            rows.append(
                SimpleNamespace(
                    checkbox=checkbox,
                    item_id=item_id,
                    unit_zone=unit_zone,
                    remark=remark,
                    existing=existing,
                    unit_zone_error=self._fg_esd_row_errors.get(str(item_id)),
                )
            )

        return rows

    def _build_rows(self, *, field_name, remark_prefix, remarks_map):
        rows = []

        for checkbox in self[field_name]:
            item_id = checkbox.data["value"]

            if self.is_bound:
                # Re-render after a failed submit: show what the user typed.
                remark = (self.data.get(f"{remark_prefix}_{item_id}") or "").strip()
            else:
                # Fresh form (create: empty map, update: existing remarks).
                remark = remarks_map.get(str(item_id), "")

            rows.append(
                SimpleNamespace(checkbox=checkbox, item_id=item_id, remark=remark)
            )

        return rows



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
        permit_number = (cleaned_data.get("permit_number") or "").strip().upper()

        if continuation_of and permit_number:
            continuation_number = (
                continuation_of.permit_number or ""
            ).strip().upper()

            if continuation_number == permit_number:
                self.add_error(
                    "continuation_of",
                    (
                        "A permit cannot be a continuation of a permit with the same "
                        "permit number."
                    ),
                )

        if continuation_of:
            eligible_states = {
                PermitWorkflowStep.State.ACTIVE,
                PermitWorkflowStep.State.CLOSED,
            }
            previous_step = continuation_of.current_step
            if (
                previous_step is None
                or previous_step.state not in eligible_states
            ):
                self.add_error(
                    "continuation_of",
                    "Only a permit in Active or Closed status can be continued.",
                )

        # Validate dynamic Unit / Zone inputs for selected FG/ESD items.
        selected_fg_esd_items = cleaned_data.get("fire_gas_esd_items")

        if selected_fg_esd_items:
            has_fg_esd_zone_error = False

            for item in selected_fg_esd_items:
                unit_zone = (
                    self.data.get(f"fg_esd_unit_zone_{item.pk}") or ""
                ).strip()

                if not unit_zone:
                    has_fg_esd_zone_error = True

                    # Used by fire_gas_esd_rows to highlight the exact row.
                    self._fg_esd_row_errors[str(item.pk)] = (
                        "Unit / Zone is required when this isolation is selected."
                    )

            if has_fg_esd_zone_error:
                # Makes form.is_valid() return False, therefore the Permit is not saved.
                self.add_error(
                    "fire_gas_esd_items",
                    "Provide a Unit / Zone for every selected Fire, Gas & ESD isolation.",
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
            remark_prefix="hazard_remarks",
            selected_objects=self.cleaned_data.get("hazards", []),
            user=user,
        )
        self._sync_assessments(
            through_model=PermitPrecaution,
            related_field="precaution",
            remark_prefix="precaution_remarks",
            selected_objects=self.cleaned_data.get("precautions", []),
            user=user,
        )


    def save_fire_gas_esd_items(self, *, user):
        if not self.instance.pk:
            raise ValueError(
                "The permit must be saved before Fire, Gas & ESD items."
            )

        selected_items = self.cleaned_data.get("fire_gas_esd_items", [])

        rows = []
        for item in selected_items:
            item_id = item.pk
            existing = self._fg_esd_rows_map.get(str(item_id))

            rows.append(
                {
                    "pk": existing.pk if existing else None,
                    "fire_gas_esd_id": item_id,
                    "unit_zone": self.data.get(f"fg_esd_unit_zone_{item_id}") or "",
                    "remarks": self.data.get(f"fg_esd_remarks_{item_id}") or "",
                }
            )

        PermitFireGasESDService.sync_items(
            permit=self.instance,
            rows=rows,
            user=user,
        )


    def _sync_assessments(
        self,
        *,
        through_model,
        related_field,
        remark_prefix,
        selected_objects,
        user,
    ):
        selected_ids = {obj.pk for obj in selected_objects}
        related_id_field = f"{related_field}_id"

        remarks_map = {
            obj.pk: (self.data.get(f"{remark_prefix}_{obj.pk}") or "").strip()
            for obj in selected_objects
        }

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

        # Deactivate removed items, update remarks for still-active ones
        for record in active_records:
            rel_id = getattr(record, related_id_field)

            if rel_id not in selected_ids:
                record.deactivate(user=user)
            else:
                new_remark = remarks_map.get(rel_id, "")
                if record.remarks != new_remark:
                    record.remarks = new_remark
                    record.modified_by = user
                    record.save(
                        update_fields=["remarks", "modified_by", "modified_at"]
                    )

        # Reactivate old records or create new ones
        for related_id in selected_ids - active_ids:
            new_remark = remarks_map.get(related_id, "")
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
                inactive_record.remarks = new_remark
                inactive_record.modified_by = user
                inactive_record.save(
                    update_fields=["remarks", "modified_by", "modified_at"]
                )
                continue

            through_model.objects.create(
                permit=self.instance,
                created_by=user,
                modified_by=user,
                remarks=new_remark,
                **{related_id_field: related_id},
            )



# ------------------ Work flow ---------------------------

class PermitWorkflowDecisionForm(forms.Form):
    role_code = forms.CharField(
        max_length=50,
        widget=forms.HiddenInput(),
    )

    decision = forms.ChoiceField(
        choices=Decision.choices,
        widget=forms.HiddenInput(),
    )

    comment = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional comment...",
            }
        ),
    )
