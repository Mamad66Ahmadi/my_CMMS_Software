# permits/services/fire_gas_esd_service.py

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from permits.models.permit_fg_esd_models import FireGasESD, PermitFireGasESD
from permits.models.workflow_models import PermitWorkflowStep
from permits.services.authorization_service import (
    WorkflowAuthorizationService,
)


# =============================================================================
# Results
# =============================================================================

@dataclass(frozen=True)
class FireGasESDIsolationResult:
    item: PermitFireGasESD


@dataclass(frozen=True)
class FireGasESDDeisolationResult:
    item: PermitFireGasESD


# =============================================================================
# Permit Fire, Gas & ESD Service
# =============================================================================

class PermitFireGasESDService:
    """
    Application service for permit Fire, Gas & ESD isolation items.

    Responsibilities:
    1. Provide the list of active FireGasESD master-data items available
       to add/remove on a permit while it is editable, mirroring the
       hazard/precaution pattern.
    2. Sync the selected FireGasESD items for a permit from an edit/create
       form submission (create rows for newly selected items, delete rows
       for de-selected items).
    3. Authorize and record isolation / de-isolation sign-offs. These are
       independently permitted from permit editing: they can be recorded
       at any time and only by the role configured on the FireGasESD item.
    4. Enforce that rows cannot be removed once the permit is no longer
       in an editable workflow step.
    """

    # =========================================================================
    # Query Helpers
    # =========================================================================

    @classmethod
    def get_active_master_items(cls):
        return (
            FireGasESD.objects
            .filter(is_active=True)
            .select_related("role")
            .order_by("display_order", "code")
        )

    @classmethod
    def get_permit_items(cls, *, permit):
        return (
            PermitFireGasESD.objects
            .filter(permit=permit)
            .select_related(
                "fire_gas_esd",
                "fire_gas_esd__role",
                "isolated_confirmed_by",
                "deisolated_confirmed_by",
            )
            .order_by(
                "fire_gas_esd__display_order",
                "fire_gas_esd__code",
                "unit_zone",
                "pk",
            )
        )

    # =========================================================================
    # Permission Helpers
    # =========================================================================

    @classmethod
    def can_remove_item(cls, *, permit, actor) -> bool:
        """
        Rows can only be removed while the permit is editable by the actor,
        same rule that governs hazards/precautions.
        """
        return WorkflowAuthorizationService.actor_can_edit_permit(
            actor=actor,
            permit=permit,
        )

    @classmethod
    def can_sign_isolation(cls, *, item: PermitFireGasESD, actor) -> bool:
        return cls._can_sign(item=item, actor=actor, deisolation=False)

    @classmethod
    def can_sign_deisolation(cls, *, item: PermitFireGasESD, actor) -> bool:
        return cls._can_sign(item=item, actor=actor, deisolation=True)

    @classmethod
    def _can_sign(cls, *, item: PermitFireGasESD, actor, deisolation: bool) -> bool:
        if not actor or not actor.is_authenticated:
            return False

        if deisolation and item.deisolated_confirmed_at is not None:
            return False

        if not deisolation and item.isolated_confirmed_at is not None:
            return False

        role = item.fire_gas_esd.role
        if not role:
            return False

        try:
            WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
                actor=actor,
                permit=item.permit,
                role=role,
                action_label=(
                    "sign this de-isolation"
                    if deisolation
                    else "sign this isolation"
                ),
            )
            return True
        except (PermissionDenied, ValidationError):
            return False

    # =========================================================================
    # Sync (Create / Edit)
    # =========================================================================

    @classmethod
    @transaction.atomic
    def sync_items(
        cls,
        *,
        permit,
        rows,
        user,
    ):
        """
        Sync the permit's Fire/Gas/ESD rows against the submitted rows.

        `rows` is an iterable of dicts, each with:
            - "fire_gas_esd_id" (required)
            - "unit_zone" (required)
            - "remarks" (optional)
            - "pk" (optional, present when editing an existing row)

        Existing rows not present in `rows` (by pk) are deleted. New rows
        are created. Rows that already carry isolation/de-isolation data
        cannot be removed unless still explicitly present in `rows`.

        The caller is responsible for ensuring the actor is authorized to
        edit the permit before invoking this method.
        """
        existing_items = {
            item.pk: item
            for item in PermitFireGasESD.objects.filter(permit=permit)
        }

        submitted_pks = set()

        for row in rows:
            pk = row.get("pk")
            fire_gas_esd_id = row.get("fire_gas_esd_id")
            unit_zone = (row.get("unit_zone") or "").strip()
            remarks = (row.get("remarks") or "").strip()

            if not fire_gas_esd_id or not unit_zone:
                continue

            if pk and pk in existing_items:
                submitted_pks.add(pk)
                item = existing_items[pk]

                if (
                    item.unit_zone != unit_zone
                    or item.remarks != remarks
                ):
                    item.unit_zone = unit_zone
                    item.remarks = remarks
                    item.modified_by = user
                    item.save(
                        update_fields=[
                            "unit_zone",
                            "remarks",
                            "modified_by",
                            "modified_at",
                        ]
                    )
                continue

            item = PermitFireGasESD.objects.create(
                permit=permit,
                fire_gas_esd_id=fire_gas_esd_id,
                unit_zone=unit_zone,
                remarks=remarks,
                created_by=user,
                modified_by=user,
            )
            submitted_pks.add(item.pk)

        removed_pks = set(existing_items) - submitted_pks

        for pk in removed_pks:
            existing_items[pk].delete()

    # =========================================================================
    # Isolation / De-isolation Signing
    # =========================================================================

    @classmethod
    @transaction.atomic
    def sign_isolation(
        cls,
        *,
        item_id: int,
        isolated_time,
        actor,
    ) -> FireGasESDIsolationResult:
        item = (
            PermitFireGasESD.objects
            .select_for_update()
            .select_related("permit", "fire_gas_esd", "fire_gas_esd__role")
            .get(pk=item_id)
        )

        if not actor or not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if item.isolated_confirmed_at is not None:
            raise ValidationError("This item has already been isolated and signed.")

        if not isolated_time:
            raise ValidationError({"isolated_time": "Isolation time is required."})

        role = item.fire_gas_esd.role
        if role is None:
            raise ValidationError(
                "This Fire, Gas & ESD item has no responsible role configured."
            )

        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=item.permit,
            role=role,
            action_label="sign this isolation",
        )

        item.isolated_time = isolated_time
        item.isolated_confirmed_by = actor
        item.isolated_confirmed_at = timezone.now()
        item.modified_by = actor

        item.save(
            update_fields=[
                "isolated_time",
                "isolated_confirmed_by",
                "isolated_confirmed_at",
                "modified_by",
                "modified_at",
            ]
        )

        return FireGasESDIsolationResult(item=item)

    @classmethod
    @transaction.atomic
    def sign_deisolation(
        cls,
        *,
        item_id: int,
        deisolated_time,
        actor,
    ) -> FireGasESDDeisolationResult:
        item = (
            PermitFireGasESD.objects
            .select_for_update()
            .select_related("permit", "fire_gas_esd", "fire_gas_esd__role")
            .get(pk=item_id)
        )

        if not actor or not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        if item.isolated_confirmed_at is None:
            raise ValidationError(
                "This item must be isolated and signed before it can be de-isolated."
            )

        if item.deisolated_confirmed_at is not None:
            raise ValidationError("This item has already been de-isolated and signed.")

        if not deisolated_time:
            raise ValidationError({"deisolated_time": "De-isolation time is required."})

        role = item.fire_gas_esd.role
        if role is None:
            raise ValidationError(
                "This Fire, Gas & ESD item has no responsible role configured."
            )

        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=item.permit,
            role=role,
            action_label="sign this de-isolation",
        )

        item.deisolated_time = deisolated_time
        item.deisolated_confirmed_by = actor
        item.deisolated_confirmed_at = timezone.now()
        item.modified_by = actor

        item.save(
            update_fields=[
                "deisolated_time",
                "deisolated_confirmed_by",
                "deisolated_confirmed_at",
                "modified_by",
                "modified_at",
            ]
        )

        return FireGasESDDeisolationResult(item=item)
