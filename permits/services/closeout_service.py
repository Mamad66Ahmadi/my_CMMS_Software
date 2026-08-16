# permits/services/closeout_service.py

from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
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

    1. Initialize the permit-specific close-out checklist when a permit
       enters an ACTIVE workflow step.

    2. Authorize and record individual close-out sign-offs.

    Close-out requirements are defined by PermitCloseoutItem.

    PermitCloseoutSignoff is the permit-specific snapshot of those
    requirements.
    """

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
            .filter(
                permit=permit,
            )
            .values_list(
                "closeout_item_id",
                flat=True,
            )
        )

        closeout_items = (
            PermitCloseoutItem.objects
            .filter(
                is_active=True,
            )
            .exclude(
                pk__in=existing_item_ids,
            )
            .order_by(
                "display_order",
                "code",
            )
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
            return CloseoutInitializationResult(
                created_count=0,
            )

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
        - Actor must hold that role for this permit, including:
            * qualification
            * permit type
            * department scope
            * unit scope
        - signed_by and signed_at are written atomically.
        """

        # ---------------------------------------------------------------------
        # Lock the sign-off row.
        #
        # This prevents two simultaneous requests from successfully signing
        # the same close-out requirement.
        # ---------------------------------------------------------------------

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
            .get(
                pk=signoff_id,
            )
        )

        permit = signoff.permit
        closeout_item = signoff.closeout_item
        role = closeout_item.role

        # ---------------------------------------------------------------------
        # 1. Authentication
        # ---------------------------------------------------------------------

        if not actor.is_authenticated:
            raise PermissionDenied(
                "Authentication is required."
            )

        # ---------------------------------------------------------------------
        # 2. Permit must currently be ACTIVE
        # ---------------------------------------------------------------------

        if (
            not permit.current_step_id
            or permit.current_step.state
            != PermitWorkflowStep.State.ACTIVE
        ):
            raise ValidationError(
                "Close-out sign-offs can only be completed while "
                "the permit is in an ACTIVE workflow step."
            )

        # ---------------------------------------------------------------------
        # 3. Cannot sign an already completed requirement
        # ---------------------------------------------------------------------

        if signoff.signed_by_id is not None:
            raise ValidationError(
                "This close-out item has already been signed."
            )

        # ---------------------------------------------------------------------
        # 4. Responsible role must exist
        # ---------------------------------------------------------------------

        if role is None:
            raise ValidationError(
                "This close-out item has no responsible role configured."
            )

        # ---------------------------------------------------------------------
        # 5. Centralized authorization
        #
        # IMPORTANT:
        # The role is taken from the database:
        #
        #     signoff.closeout_item.role
        #
        # It is NOT supplied by the browser.
        # ---------------------------------------------------------------------

        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=role,
            action_label="sign this close-out item",
        )

        # ---------------------------------------------------------------------
        # 6. Record sign-off
        # ---------------------------------------------------------------------

        now = timezone.now()

        signoff.signed_by = actor
        signoff.signed_at = now

        signoff.save(
            update_fields=[
                "signed_by",
                "signed_at",
            ]
        )

        return CloseoutSignoffResult(
            signoff=signoff,
        )