# permits/services/permit_work_shift_service.py

from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from permits.models.permit_shift_models import (
    PermitShiftSignoff,
    PermitTypeActiveShiftRole,
    PermitWorkShift,
    Shift,
    ShiftSchedule,
)
from permits.services.authorization_service import WorkflowAuthorizationService


# =====================================================================
# Exceptions
# =====================================================================

class PermitWorkShiftError(ValidationError):
    """
    Raised when a work-shift operation violates a business rule.
    """
    pass


# =====================================================================
# Result objects
# =====================================================================

@dataclass(frozen=True)
class WorkShiftResult:
    work_shift: PermitWorkShift


@dataclass(frozen=True)
class ShiftSignoffResult:
    signoff: PermitShiftSignoff


# =====================================================================
# Work Shift Service
# =====================================================================

class PermitWorkShiftService:

    # -----------------------------------------------------------------
    # Configuration
    # -----------------------------------------------------------------

    # Older data in this project uses the display name as the role code
    # ("Permit Office"), while newer configurations use "PERMIT_OFFICE".
    #
    # Keep both temporarily while role master data is standardized.
    PERMIT_OFFICE_ROLE_CODES = (
        "PERMIT_OFFICE",
        "Permit Office",
    )

    MAX_WORK_SHIFTS_PER_PERMIT = 14

    # =================================================================
    # DISPLAY / AUTHORIZATION HELPERS
    # =================================================================

    @classmethod
    def can_view_work_shifts(cls, *, actor, permit) -> bool:
        """
        Determine whether the actor may VIEW the work-shift panel.

        Policy:
            Any authenticated user who can already access the permit
            may view its work shifts.

        Viewing work shifts does NOT require:
            - Permit Office role
            - signoff role
            - qualification
            - department assignment
            - unit assignment

        The permit detail view / endpoint remains responsible for
        protecting access to the permit itself.
        """

        return bool(actor.is_authenticated)

    # -----------------------------------------------------------------

    @classmethod
    def can_manage_work_shifts(cls, *, actor, permit) -> bool:
        """
        Display helper for CREATE/CLOSE work-shift actions.

        Policy:
            - Actor must be authenticated.
            - Permit must currently be ACTIVE.
            - Actor must have the Permit Office role assignment.
            - The normal role assignment rules are handled centrally
              by WorkflowAuthorizationService.

        This method is intended for UI display only.

        The actual create_work_shift() and close_work_shift() methods
        perform the authorization again and therefore remain protected.
        """

        if not actor.is_authenticated:
            return False

        try:
            cls._ensure_permit_is_active(permit)

            WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
                actor=actor,
                permit=permit,
                role=cls._get_permit_office_role(),
                action_label="manage permit work shifts",
            )

        except (PermissionDenied, ValidationError):
            return False

        return True

    # -----------------------------------------------------------------

    @classmethod
    def can_sign_work_shift(cls, *, actor, permit, role) -> bool:
        """
        Display helper for shift signoff.

        Policy:
            The actor may sign only if they have an active assignment
            for the specific signoff role.

        The actual sign_shift() method performs the same authorization
        again before writing the signature.

        Note:
            The caller should pass the role from the actual
            PermitShiftSignoff record, not an arbitrary role.
        """

        try:
            cls._ensure_actor_can_sign_work_shift(
                actor=actor,
                permit=permit,
                role=role,
            )

        except PermissionDenied:
            return False

        return True

    # =================================================================
    # CREATE / OPEN WORK SHIFT
    # =================================================================

    @classmethod
    @transaction.atomic
    def create_work_shift(
        cls,
        *,
        permit_id,
        actor,
        date,
        shift,
        work_leader=None,
        worker_count=None,
    ):
        """
        Create/open a new work shift.

        Authorization:
            ONLY Permit Office.

        Business rules:
            - Permit must be ACTIVE.
            - Only one open shift may exist per permit.
            - Maximum 14 shifts per permit.
            - Same permit/date/shift combination cannot exist twice.
            - Date must be within permit validity.
            - Permit type must have active shift-signoff roles.
            - Signoff requirements are snapshotted into PermitShiftSignoff.
        """

        from permits.models.permit_models import Permit

        # -------------------------------------------------------------
        # Lock permit
        # -------------------------------------------------------------

        permit = (
            Permit.objects
            .select_for_update()
            .select_related(
                "permit_type",
                "current_step",
                "department",
                "location_tag",
                "location_tag__unit",
            )
            .get(pk=permit_id)
        )

        # -------------------------------------------------------------
        # Permit state
        # -------------------------------------------------------------

        cls._ensure_permit_is_active(permit)

        # -------------------------------------------------------------
        # Authorization
        # -------------------------------------------------------------

        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=cls._get_permit_office_role(),
            action_label="create a permit work shift",
        )

        # -------------------------------------------------------------
        # Automatically close an expired open shift
        # -------------------------------------------------------------

        cls._close_expired_work_shift_for_permit(
            permit=permit
        )

        # -------------------------------------------------------------
        # Validate supplied shift
        # -------------------------------------------------------------

        cls._validate_shift(shift)

        # -------------------------------------------------------------
        # Validate date
        # -------------------------------------------------------------

        cls._ensure_date_within_permit_validity(
            permit=permit,
            date=date,
        )

        # -------------------------------------------------------------
        # Only one open shift per permit
        # -------------------------------------------------------------

        if PermitWorkShift.objects.filter(
            permit=permit,
            status=PermitWorkShift.Status.OPEN,
        ).exists():

            raise PermitWorkShiftError(
                "Close the current open work shift before opening another one."
            )

        # -------------------------------------------------------------
        # Maximum number of shifts
        # -------------------------------------------------------------

        if (
            PermitWorkShift.objects
            .filter(permit=permit)
            .count()
            >= cls.MAX_WORK_SHIFTS_PER_PERMIT
        ):
            raise PermitWorkShiftError(
                f"This permit cannot have more than "
                f"{cls.MAX_WORK_SHIFTS_PER_PERMIT} work shifts."
            )

        # -------------------------------------------------------------
        # Prevent duplicate permit/date/shift
        # -------------------------------------------------------------

        if PermitWorkShift.objects.filter(
            permit=permit,
            date=date,
            shift=shift,
        ).exists():

            raise PermitWorkShiftError(
                "A work shift already exists for this permit, "
                "date and shift."
            )

        # -------------------------------------------------------------
        # Get active signoff configuration
        #
        # IMPORTANT:
        # These configurations are copied into PermitShiftSignoff.
        # Future changes to PermitTypeActiveShiftRole therefore do not
        # alter the requirements of an already-created work shift.
        # -------------------------------------------------------------

        role_configurations = list(
            PermitTypeActiveShiftRole.objects
            .select_related("role")
            .filter(
                permit_type=permit.permit_type,
                role__is_active=True,
            )
            .order_by("sequence", "id")
        )

        if not role_configurations:
            raise PermitWorkShiftError(
                "This permit type has no active-shift roles configured. "
                "The work shift cannot be created."
            )

        # -------------------------------------------------------------
        # Create work shift
        # -------------------------------------------------------------

        work_shift = PermitWorkShift.objects.create(
            permit=permit,
            date=date,
            shift=shift,
            work_leader=(work_leader or "").strip() or None,
            worker_count=worker_count,
            created_by=actor,
        )

        # -------------------------------------------------------------
        # Snapshot signoff requirements
        # -------------------------------------------------------------

        PermitShiftSignoff.objects.bulk_create(
            [
                PermitShiftSignoff(
                    work_shift=work_shift,
                    role=config.role,
                    sequence=config.sequence,
                    is_required=config.is_required,
                )
                for config in role_configurations
            ]
        )

        return WorkShiftResult(
            work_shift=work_shift
        )

    # =================================================================
    # SIGN WORK SHIFT
    # =================================================================

    @classmethod
    @transaction.atomic
    def sign_shift(
        cls,
        *,
        work_shift_id,
        actor,
        role_code,
    ):
        """
        Sign a specific work-shift signoff.

        Authorization:
            The actor must have an active assignment for the exact role
            configured on the PermitShiftSignoff.

        The central WorkflowAuthorizationService handles:
            - authentication
            - superuser bypass
            - required qualification
            - active role assignment
            - permit type scope
            - department scope
            - unit scope

        Business rules:
            - Permit must be ACTIVE.
            - Shift must be OPEN.
            - The role must actually be configured on this shift.
            - The signoff must not already be signed.
        """

        # -------------------------------------------------------------
        # Lock work shift
        # -------------------------------------------------------------

        work_shift = (
            PermitWorkShift.objects
            .select_for_update()
            .select_related(
                "permit",
                "permit__current_step",
                "permit__permit_type",
                "permit__department",
                "permit__location_tag",
                "permit__location_tag__unit",
            )
            .get(pk=work_shift_id)
        )

        permit = work_shift.permit

        # -------------------------------------------------------------
        # Permit must be ACTIVE
        # -------------------------------------------------------------

        cls._ensure_permit_is_active(permit)

        # -------------------------------------------------------------
        # Shift must be OPEN
        # -------------------------------------------------------------

        if work_shift.status != PermitWorkShift.Status.OPEN:
            raise PermitWorkShiftError(
                "This work shift is closed and can no longer be signed."
            )

        # -------------------------------------------------------------
        # Find the actual signoff configured on this shift
        # -------------------------------------------------------------

        try:
            signoff = (
                PermitShiftSignoff.objects
                .select_for_update()
                .select_related("role")
                .get(
                    work_shift=work_shift,
                    role__code=role_code,
                )
            )

        except PermitShiftSignoff.DoesNotExist:
            raise PermitWorkShiftError(
                "This role is not configured as a signoff role "
                "for this work shift."
            )

        # -------------------------------------------------------------
        # Prevent duplicate signature
        # -------------------------------------------------------------

        if signoff.signed_by_id:
            raise PermitWorkShiftError(
                f"This work shift has already been signed "
                f"as {signoff.role.name}."
            )

        # -------------------------------------------------------------
        # Authorization
        #
        # IMPORTANT:
        # We authorize against signoff.role, not role_code supplied
        # independently by the user.
        # -------------------------------------------------------------

        cls._ensure_actor_can_sign_work_shift(
            actor=actor,
            permit=permit,
            role=signoff.role,
        )

        # -------------------------------------------------------------
        # Sign
        # -------------------------------------------------------------

        signoff.signed_by = actor
        signoff.signed_at = timezone.now()

        signoff.save(
            update_fields=[
                "signed_by",
                "signed_at",
            ]
        )

        return ShiftSignoffResult(
            signoff=signoff
        )

    # =================================================================
    # CLOSE WORK SHIFT
    # =================================================================

    @classmethod
    @transaction.atomic
    def close_work_shift(
        cls,
        *,
        work_shift_id,
        actor,
    ):
        """
        Manually close a work shift.

        Authorization:
            ONLY Permit Office.

        Business rules:
            - Permit must be ACTIVE.
            - Shift must currently be OPEN.
        """

        # -------------------------------------------------------------
        # Lock work shift
        # -------------------------------------------------------------

        work_shift = (
            PermitWorkShift.objects
            .select_for_update()
            .select_related(
                "permit",
                "permit__current_step",
                "permit__permit_type",
                "permit__department",
                "permit__location_tag",
                "permit__location_tag__unit",
            )
            .get(pk=work_shift_id)
        )

        permit = work_shift.permit

        # -------------------------------------------------------------
        # Permit must be ACTIVE
        # -------------------------------------------------------------

        cls._ensure_permit_is_active(permit)

        # -------------------------------------------------------------
        # Authorization
        # -------------------------------------------------------------

        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=cls._get_permit_office_role(),
            action_label="close a permit work shift",
        )

        # -------------------------------------------------------------
        # Shift must be OPEN
        # -------------------------------------------------------------

        if work_shift.status != PermitWorkShift.Status.OPEN:
            raise PermitWorkShiftError(
                "This work shift is already closed."
            )

        # -------------------------------------------------------------
        # Close
        # -------------------------------------------------------------

        work_shift.status = PermitWorkShift.Status.CLOSED
        work_shift.closed_by = actor
        work_shift.closed_at = timezone.now()

        work_shift.save(
            update_fields=[
                "status",
                "closed_by",
                "closed_at",
            ]
        )

        return WorkShiftResult(
            work_shift=work_shift
        )

    # =================================================================
    # SIGNOFF STATUS HELPERS
    # =================================================================

    @classmethod
    def is_shift_ready(cls, *, work_shift) -> bool:
        """
        Return True when all required signoffs have been completed.

        Optional signoffs do not prevent readiness.
        """

        return not (
            work_shift.signoffs
            .filter(
                is_required=True,
                signed_by__isnull=True,
            )
            .exists()
        )

    # -----------------------------------------------------------------

    @classmethod
    def get_pending_signoffs(cls, *, work_shift):
        """
        Return all required, unsigned signoffs in sequence order.
        """

        return (
            work_shift.signoffs
            .filter(
                is_required=True,
                signed_by__isnull=True,
            )
            .select_related("role")
            .order_by("sequence", "id")
        )

    # =================================================================
    # SIGNOFF AUTHORIZATION
    # =================================================================

    @staticmethod
    def _ensure_actor_can_sign_work_shift(
        *,
        actor,
        permit,
        role,
    ):
        """
        Authorize an actor for a particular shift signoff role.

        IMPORTANT:
        Do NOT duplicate the assignment / qualification / department /
        unit authorization logic here.

        The central WorkflowAuthorizationService owns that logic.

        Therefore the same authorization rules are used for:
            - workflow transitions
            - permit editing
            - shift signoff
            - Permit Office shift management
        """

        if not actor.is_authenticated:
            raise PermissionDenied(
                "Authentication is required."
            )

        if actor.is_superuser:
            return

        if role is None:
            raise PermissionDenied(
                "No role is configured for this shift signoff."
            )

        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=role,
            action_label="sign this work shift",
        )

    # =================================================================
    # PERMIT OFFICE ROLE
    # =================================================================

    @classmethod
    def _get_permit_office_role(cls):
        """
        Resolve the single active Permit Office role.

        During role-master-data standardization we temporarily accept:
            - code = PERMIT_OFFICE
            - code = Permit Office
            - name = Permit Office
        """

        from permits.models.approval_models import (
            PermitApprovalRoleChoices,
        )

        try:
            return (
                PermitApprovalRoleChoices.objects
                .get(
                    Q(code__in=cls.PERMIT_OFFICE_ROLE_CODES)
                    | Q(name__iexact="Permit Office"),
                    is_active=True,
                )
            )

        except PermitApprovalRoleChoices.DoesNotExist:
            raise PermitWorkShiftError(
                "The Permit Office approval role is not configured."
            )

        except PermitApprovalRoleChoices.MultipleObjectsReturned:
            raise PermitWorkShiftError(
                "More than one active Permit Office role is configured. "
                "Keep only one active Permit Office role."
            )

    # =================================================================
    # PERMIT STATE
    # =================================================================

    @staticmethod
    def _ensure_permit_is_active(permit):
        """
        Work-shift mutations are allowed only while the permit is ACTIVE.
        """

        from permits.models.workflow_models import PermitWorkflowStep

        if not permit.current_step_id:
            raise PermitWorkShiftError(
                "The permit does not have a current workflow step."
            )

        if permit.current_step.state != PermitWorkflowStep.State.ACTIVE:
            raise PermitWorkShiftError(
                "Work shifts can only be managed while the permit is ACTIVE."
            )

    # =================================================================
    # DATE VALIDATION
    # =================================================================

    @staticmethod
    def _ensure_date_within_permit_validity(
        *,
        permit,
        date,
    ):
        """
        Ensure the work-shift date falls within the permit validity period.
        """

        if (
            permit.valid_from
            and date < timezone.localtime(
                permit.valid_from
            ).date()
        ):
            raise PermitWorkShiftError(
                "The work-shift date cannot be before "
                "the permit validity period."
            )

        if (
            permit.valid_to
            and date > timezone.localtime(
                permit.valid_to
            ).date()
        ):
            raise PermitWorkShiftError(
                "The work-shift date cannot be after "
                "the permit validity period."
            )

    # =================================================================
    # SHIFT VALIDATION
    # =================================================================

    @staticmethod
    def _validate_shift(shift):
        """
        Validate that the supplied shift is one of Shift.choices.
        """

        valid_shifts = {
            value
            for value, _label in Shift.choices
        }

        if shift not in valid_shifts:
            raise PermitWorkShiftError(
                {
                    "shift": (
                        "The supplied shift is not valid."
                    )
                }
            )

    # =================================================================
    # SHIFT CHANGE TIME
    # =================================================================

    @classmethod
    def _get_shift_change_datetime(
        cls,
        *,
        work_shift,
    ):
        """
        Calculate the datetime at which this work shift should
        automatically close because the next configured shift begins.
        """

        try:
            schedule = (
                ShiftSchedule.objects
                .get(
                    shift=work_shift.shift,
                    is_active=True,
                )
            )

        except ShiftSchedule.DoesNotExist:
            # Do not silently close a shift if the schedule configuration
            # is missing.
            return None

        except ShiftSchedule.MultipleObjectsReturned:
            raise PermitWorkShiftError(
                f"More than one active schedule exists for "
                f"shift '{work_shift.shift}'."
            )

        # -------------------------------------------------------------
        # Find the next active shift in the same day
        # -------------------------------------------------------------

        next_schedule = (
            ShiftSchedule.objects
            .filter(
                is_active=True,
                start_time__gt=schedule.start_time,
            )
            .order_by(
                "start_time",
                "id",
            )
            .first()
        )

        # -------------------------------------------------------------
        # If there is no later shift today, the next shift is the
        # earliest shift of the following day.
        # -------------------------------------------------------------

        if next_schedule is None:

            next_schedule = (
                ShiftSchedule.objects
                .filter(is_active=True)
                .order_by(
                    "start_time",
                    "id",
                )
                .first()
            )

            if next_schedule is None:
                return None

            change_date = work_shift.date + timedelta(days=1)

        else:
            change_date = work_shift.date

        # -------------------------------------------------------------
        # Return timezone-aware datetime
        # -------------------------------------------------------------

        return timezone.make_aware(
            datetime.combine(
                change_date,
                next_schedule.start_time,
            ),
            timezone.get_current_timezone(),
        )

    # =================================================================
    # AUTOMATIC SHIFT CLOSING
    # =================================================================

    @classmethod
    @transaction.atomic
    def _close_expired_work_shift_for_permit(
        cls,
        *,
        permit,
    ):
        """
        Automatically close the currently open work shift when its
        configured next-shift boundary has passed.

        Expected:
            The caller has already locked the permit.

        Important:
            This is a system/business-rule operation, not a manual
            Permit Office operation.

        Therefore:
            - No actor is required.
            - closed_by remains NULL.
            - The shift is closed automatically.
        """

        now = timezone.now()

        # -------------------------------------------------------------
        # Lock currently open shift
        # -------------------------------------------------------------

        work_shift = (
            PermitWorkShift.objects
            .select_for_update()
            .filter(
                permit=permit,
                status=PermitWorkShift.Status.OPEN,
            )
            .order_by("id")
            .first()
        )

        if work_shift is None:
            return None

        # -------------------------------------------------------------
        # Calculate configured shift boundary
        # -------------------------------------------------------------

        shift_change_at = cls._get_shift_change_datetime(
            work_shift=work_shift
        )

        # -------------------------------------------------------------
        # Do not silently close if schedule configuration is missing
        # -------------------------------------------------------------

        if shift_change_at is None:
            return None

        # -------------------------------------------------------------
        # Boundary has not yet been reached
        # -------------------------------------------------------------

        if now < shift_change_at:
            return None

        # -------------------------------------------------------------
        # Automatically close
        # -------------------------------------------------------------

        work_shift.status = PermitWorkShift.Status.CLOSED
        work_shift.closed_at = now

        # No human closed the shift.
        work_shift.closed_by = None

        work_shift.save(
            update_fields=[
                "status",
                "closed_at",
                "closed_by",
            ]
        )

        return work_shift