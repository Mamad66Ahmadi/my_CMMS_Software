# permits/services/closeout_service.py

from dataclasses import dataclass
from typing import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models, transaction
from django.utils import timezone

from permits.models.permit_closeout_models import (
    PermitCloseoutItem,
    PermitCloseoutSignoff,
)
from permits.models.workflow_models import PermitWorkflowStep
from permits.services.authorization_service import (
    WorkflowAuthorizationService,
)


# =============================================================================
# Results
# =============================================================================

@dataclass(frozen=True)
class CloseoutInitializationResult:
    created_count: int


@dataclass(frozen=True)
class CloseoutSignoffResult:
    signoff: PermitCloseoutSignoff


# =============================================================================
# Permit Closeout Service
# =============================================================================

class PermitCloseoutService:
    """
    Application service for permit close-out operations.

    Responsibilities:
    1. Provide query access and role/state permissions for close-out checklists.
    2. Initialize the permit-specific close-out checklist when a permit enters an ACTIVE step.
    3. Authorize and record individual close-out sign-offs (ACTIVE state only).
    """

    # =========================================================================
    # Permission & Query Helpers
    # =========================================================================

    @classmethod
    def can_view_closeout_signoffs(cls, *, permit, actor) -> bool:
        """
        Check if the actor is permitted to view closeout checklists.
        Visibility is allowed across ALL workflow states (Draft, Active, Suspended, Closed, etc.)
        as long as the user is authenticated.
        """
        if not actor or not actor.is_authenticated:
            return False

        if actor.is_superuser:
            return True

        # Any authenticated actor with basic permit view access can view sign-offs.
        # If your system uses a specific permission check on permit, hook it here.
        return True

    @classmethod
    def can_sign_closeout_item(cls, *, signoff: PermitCloseoutSignoff, actor) -> bool:
        """
        Determine whether the actor can sign a specific close-out requirement.
        Requires:
        1. Actor authenticated
        2. Permit in ACTIVE workflow state
        3. Close-out item not already signed
        4. Actor has the required role & scope
        """
        if not actor or not actor.is_authenticated:
            return False

        permit = signoff.permit

        # 1. State check
        if (
            not permit.current_step_id
            or permit.current_step.state != PermitWorkflowStep.State.ACTIVE
        ):
            return False

        # 2. Already signed
        if signoff.signed_by_id is not None:
            return False

        # 3. Role existence
        role = getattr(signoff.closeout_item, "role", None)
        if not role:
            return False

        # 4. Role qualification & scope check
        try:
            WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
                actor=actor,
                permit=permit,
                role=role,
                action_label="sign this close-out item",
            )
            return True
        except (PermissionDenied, ValidationError):
            return False

    @classmethod
    def get_closeout_signoffs_for_permit(
        cls,
        *,
        permit,
    ) -> models.QuerySet[PermitCloseoutSignoff]:
        """
        Fetch all close-out signoffs for a permit with optimized select_related.
        """
        return (
            PermitCloseoutSignoff.objects
            .filter(permit=permit)
            .select_related(
                "closeout_item",
                "closeout_item__role",
                "signed_by",
                "created_by",
            )
            .order_by(
                "closeout_item__display_order",
                "closeout_item__code",
                "id",
            )
        )

    # =========================================================================
    # Internal Guards
    # =========================================================================

    @classmethod
    def _ensure_permit_is_active(cls, permit) -> None:
        """
        Enforce that the permit is strictly in an ACTIVE workflow step.
        """
        if (
            not permit.current_step_id
            or permit.current_step.state != PermitWorkflowStep.State.ACTIVE
        ):
            raise ValidationError(
                "Close-out sign-offs can only be completed while "
                "the permit is in an ACTIVE workflow step."
            )

    # =========================================================================
    # Initialize Close-out Checklist
    # =========================================================================

    @classmethod
    @transaction.atomic
    def initialize_closeout_signoffs(
        cls,
        *,
        permit,
        actor,
    ) -> CloseoutInitializationResult:
        """
        Create one pending sign-off for every currently active
        PermitCloseoutItem that does not already exist for this permit.

        The generated sign-offs are intentionally left unsigned.
        """
        existing_item_ids = set(
            PermitCloseoutSignoff.objects
            .filter(permit=permit)
            .values_list("closeout_item_id", flat=True)
        )

        closeout_items = (
            PermitCloseoutItem.objects
            .filter(is_active=True)
            .exclude(pk__in=existing_item_ids)
            .order_by("display_order", "code")
        )

        signoffs = [
            PermitCloseoutSignoff(
                permit=permit,
                closeout_item=item,
                created_by=actor,
                signed_by=None,
                signed_at=None,
            )
            for item in closeout_items
        ]

        if not signoffs:
            return CloseoutInitializationResult(created_count=0)

        created = PermitCloseoutSignoff.objects.bulk_create(
            signoffs,
            ignore_conflicts=True,
        )

        return CloseoutInitializationResult(
            created_count=len(created),
        )

    # =========================================================================
    # Sign Close-out Requirement
    # =========================================================================

    @classmethod
    @transaction.atomic
    def sign_closeout(
        cls,
        *,
        signoff_id: int,
        actor,
    ) -> CloseoutSignoffResult:
        """
        Sign one permit close-out requirement.

        Security rules:
        - Actor must be authenticated.
        - Superusers are allowed by the centralized authorization service.
        - Permit must currently be in an ACTIVE workflow step.
        - Sign-off must not already be signed.
        - Responsible role is taken from the close-out item itself.
        - Actor must hold that role for this permit.
        - signed_by and signed_at are written atomically.
        """
        # 1. Authentication
        if not actor or not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")

        # 2. Lock sign-off row
        signoff = (
            PermitCloseoutSignoff.objects
            .select_for_update()
            .select_related(
                "permit",
                "permit__current_step",
                "permit__permit_type",
                "permit__department",
                "permit__location_tag",
                "permit__location_tag__unit",
                "closeout_item",
                "closeout_item__role",
                "closeout_item__role__required_qualification",
                "signed_by",
                "created_by",
            )
            .get(pk=signoff_id)
        )

        permit = signoff.permit
        closeout_item = signoff.closeout_item
        role = closeout_item.role

        # 3. Permit state guard
        cls._ensure_permit_is_active(permit)

        # 4. Cannot sign an already completed requirement
        if signoff.signed_by_id is not None:
            raise ValidationError("This close-out item has already been signed.")

        # 5. Responsible role configuration
        if role is None:
            raise ValidationError("This close-out item has no responsible role configured.")

        # 6. Centralized authorization
        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=role,
            action_label="sign this close-out item",
        )

        # 7. Record sign-off
        signoff.signed_by = actor
        signoff.signed_at = timezone.now()

        signoff.save(
            update_fields=[
                "signed_by",
                "signed_at",
            ]
        )

        return CloseoutSignoffResult(
            signoff=signoff,
        )
