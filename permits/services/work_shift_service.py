from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

from permits.models.approval_models import PermitApprovalRoleAssignment
from permits.models.permit_shift_models import (
    PermitShiftSignoff,
    PermitTypeActiveShiftRole,
    PermitWorkShift,
    Shift,
    ShiftSchedule,
)
from permits.services.authorization_service import WorkflowAuthorizationService


class PermitWorkShiftError(ValidationError):
    """Raised when a work-shift operation violates a business rule."""


@dataclass(frozen=True)
class WorkShiftResult:
    work_shift: PermitWorkShift


@dataclass(frozen=True)
class ShiftSignoffResult:
    signoff: PermitShiftSignoff


class PermitWorkShiftService:
    # Older data in this project uses the display name as the role code
    # ("Permit Office"), while newer configurations use "PERMIT_OFFICE".
    # Accept both while the role master data is being standardized.
    PERMIT_OFFICE_ROLE_CODES = ("PERMIT_OFFICE", "Permit Office")
    MAX_WORK_SHIFTS_PER_PERMIT = 14

    @classmethod
    def can_manage_work_shifts(cls, *, actor, permit) -> bool:
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

    @classmethod
    def can_sign_work_shift(cls, *, actor, permit, role) -> bool:
        """Display helper for the active-shift signoff policy."""
        try:
            cls._ensure_actor_can_sign_work_shift(
                actor=actor,
                permit=permit,
                role=role,
            )
        except PermissionDenied:
            return False
        return True

    @classmethod
    @transaction.atomic
    def create_work_shift(cls, *, permit_id, actor, date, shift, work_leader=None, worker_count=None):
        from permits.models.permit_models import Permit

        permit = (
            Permit.objects.select_for_update()
            .select_related("permit_type", "current_step", "department", "location_tag", "location_tag__unit")
            .get(pk=permit_id)
        )
        cls._ensure_permit_is_active(permit)
        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=cls._get_permit_office_role(),
            action_label="create a permit work shift",
        )

        cls._close_expired_work_shift_for_permit(permit=permit)
        cls._validate_shift(shift)
        cls._ensure_date_within_permit_validity(permit=permit, date=date)

        if PermitWorkShift.objects.filter(
            permit=permit,
            status=PermitWorkShift.Status.OPEN,
        ).exists():
            raise PermitWorkShiftError(
                "Close the current open work shift before opening another one."
            )

        if PermitWorkShift.objects.filter(permit=permit).count() >= cls.MAX_WORK_SHIFTS_PER_PERMIT:
            raise PermitWorkShiftError(
                f"This permit cannot have more than {cls.MAX_WORK_SHIFTS_PER_PERMIT} work shifts."
            )
        if PermitWorkShift.objects.filter(permit=permit, date=date, shift=shift).exists():
            raise PermitWorkShiftError("A work shift already exists for this permit, date and shift.")

        role_configurations = list(
            PermitTypeActiveShiftRole.objects.select_related("role")
            .filter(permit_type=permit.permit_type, role__is_active=True)
            .order_by("sequence", "id")
        )
        if not role_configurations:
            raise PermitWorkShiftError(
                "This permit type has no active-shift roles configured. The work shift cannot be created."
            )

        work_shift = PermitWorkShift.objects.create(
            permit=permit,
            date=date,
            shift=shift,
            work_leader=(work_leader or "").strip() or None,
            worker_count=worker_count,
            created_by=actor,
        )
        PermitShiftSignoff.objects.bulk_create([
            PermitShiftSignoff(
                work_shift=work_shift,
                role=config.role,
                sequence=config.sequence,
                is_required=config.is_required,
            )
            for config in role_configurations
        ])
        return WorkShiftResult(work_shift=work_shift)

    @classmethod
    @transaction.atomic
    def sign_shift(cls, *, work_shift_id, actor, role_code):
        work_shift = (
            PermitWorkShift.objects.select_for_update()
            .select_related("permit", "permit__current_step", "permit__permit_type", "permit__department", "permit__location_tag", "permit__location_tag__unit")
            .get(pk=work_shift_id)
        )
        cls._ensure_permit_is_active(work_shift.permit)
        if work_shift.status != PermitWorkShift.Status.OPEN:
            raise PermitWorkShiftError(
                "This work shift is closed and can no longer be signed."
            )
        try:
            signoff = (
                PermitShiftSignoff.objects.select_for_update().select_related("role")
                .get(work_shift=work_shift, role__code=role_code)
            )
        except PermitShiftSignoff.DoesNotExist:
            raise PermitWorkShiftError("This role is not configured as a signoff role for this work shift.")
        if signoff.signed_by_id:
            raise PermitWorkShiftError(
                f"This work shift has already been signed as {signoff.role.name}."
            )
        cls._ensure_actor_can_sign_work_shift(
            actor=actor,
            permit=work_shift.permit,
            role=signoff.role,
        )
        signoff.signed_by = actor
        signoff.signed_at = timezone.now()
        signoff.save(update_fields=["signed_by", "signed_at"])
        return ShiftSignoffResult(signoff=signoff)

    @classmethod
    @transaction.atomic
    def close_work_shift(cls, *, work_shift_id, actor):
        work_shift = (
            PermitWorkShift.objects.select_for_update()
            .select_related(
                "permit",
                "permit__current_step",
                "permit__department",
                "permit__location_tag",
                "permit__location_tag__unit",
            )
            .get(pk=work_shift_id)
        )
        permit = work_shift.permit
        cls._ensure_permit_is_active(permit)
        WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
            actor=actor,
            permit=permit,
            role=cls._get_permit_office_role(),
            action_label="close a permit work shift",
        )
        if work_shift.status != PermitWorkShift.Status.OPEN:
            raise PermitWorkShiftError("This work shift is already closed.")

        work_shift.status = PermitWorkShift.Status.CLOSED
        work_shift.closed_by = actor
        work_shift.closed_at = timezone.now()
        work_shift.save(update_fields=["status", "closed_by", "closed_at"])
        return WorkShiftResult(work_shift=work_shift)

    @classmethod
    def is_shift_ready(cls, *, work_shift) -> bool:
        return not work_shift.signoffs.filter(is_required=True, signed_by__isnull=True).exists()

    @classmethod
    def get_pending_signoffs(cls, *, work_shift):
        return (
            work_shift.signoffs.filter(is_required=True, signed_by__isnull=True)
            .select_related("role").order_by("sequence", "id")
        )

    @staticmethod
    def _ensure_actor_can_sign_work_shift(*, actor, permit, role):
        if not actor.is_authenticated:
            raise PermissionDenied("Authentication is required.")
        if actor.is_superuser:
            return
        if role is None:
            raise PermissionDenied("No role is configured for this shift signoff.")

        permit_unit = permit.location_tag.unit if permit.location_tag else None

        assignments = PermitApprovalRoleAssignment.objects.filter(
            user=actor, role=role, is_active=True,
        ).filter(
            Q(permit_type__isnull=True) | Q(permit_type=permit.permit_type)
        )

        if role.department_scope == role.ScopeRequirement.REQUIRED:
            assignments = assignments.filter(department=permit.department)

        if role.unit_scope == role.ScopeRequirement.REQUIRED:
            if permit_unit is None:
                raise PermissionDenied("Permit has no operational unit.")
            assignments = assignments.filter(Q(all_units=True) | Q(units=permit_unit))

        final_match = assignments.exists()

        print(
            f"[AUTH] {actor} | role={role.code} | dept_scope={role.department_scope} "
            f"unit_scope={role.unit_scope} | permit_dept={permit.department_id} "
            f"permit_unit={getattr(permit_unit, 'pk', None)} | match={final_match}"
        )

        if not final_match:
            raise PermissionDenied(
                f"You do not hold an active '{role.name}' assignment "
                f"matching this permit's scope."
            )



    @classmethod
    def _get_permit_office_role(cls):
        from permits.models.approval_models import PermitApprovalRoleChoices
        try:
            return PermitApprovalRoleChoices.objects.get(
                Q(code__in=cls.PERMIT_OFFICE_ROLE_CODES)
                | Q(name__iexact="Permit Office"),
                is_active=True,
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

    @staticmethod
    def _ensure_permit_is_active(permit):
        from permits.models.workflow_models import PermitWorkflowStep
        if not permit.current_step_id:
            raise PermitWorkShiftError("The permit does not have a current workflow step.")
        if permit.current_step.state != PermitWorkflowStep.State.ACTIVE:
            raise PermitWorkShiftError("Work shifts can only be managed while the permit is ACTIVE.")

    @staticmethod
    def _ensure_date_within_permit_validity(*, permit, date):
        if permit.valid_from and date < timezone.localtime(permit.valid_from).date():
            raise PermitWorkShiftError("The work-shift date cannot be before the permit validity period.")
        if permit.valid_to and date > timezone.localtime(permit.valid_to).date():
            raise PermitWorkShiftError("The work-shift date cannot be after the permit validity period.")

    @staticmethod
    def _validate_shift(shift):
        if shift not in {value for value, _label in Shift.choices}:
            raise PermitWorkShiftError({"shift": "The supplied shift is not valid."})


    @classmethod
    def can_view_work_shifts(cls, *, actor, permit) -> bool:
        """Role check only — work shifts stay visible in every permit status."""
        if not actor.is_authenticated:
            return False
        try:
            WorkflowAuthorizationService.ensure_actor_has_role_for_permit(
                actor=actor,
                permit=permit,
                role=cls._get_permit_office_role(),
                action_label="view permit work shifts",
            )
        except (PermissionDenied, ValidationError):
            return False
        return True

    @classmethod
    def can_manage_work_shifts(cls, *, actor, permit) -> bool:
        """Role + ACTIVE check — mutations are only allowed on ACTIVE permits.

        In every other status the actor can still view the existing rows,
        but cannot add or close a work shift.
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


    @classmethod
    def _get_shift_change_datetime(cls, *, work_shift):
        try:
            schedule = ShiftSchedule.objects.get(
                shift=work_shift.shift,
                is_active=True,
            )
        except ShiftSchedule.DoesNotExist:
            return None
        except ShiftSchedule.MultipleObjectsReturned:
            raise PermitWorkShiftError(
                f"More than one active schedule exists for shift '{work_shift.shift}'."
            )

        next_schedule = (
            ShiftSchedule.objects
            .filter(
                is_active=True,
                start_time__gt=schedule.start_time,
            )
            .order_by("start_time", "id")
            .first()
        )

        if next_schedule is None:
            next_schedule = (
                ShiftSchedule.objects
                .filter(is_active=True)
                .order_by("start_time", "id")
                .first()
            )

            if next_schedule is None:
                return None

            change_date = work_shift.date + timedelta(days=1)
        else:
            change_date = work_shift.date

        return timezone.make_aware(
            datetime.combine(change_date, next_schedule.start_time),
            timezone.get_current_timezone(),
        )


    @classmethod
    @transaction.atomic
    def _close_expired_work_shift_for_permit(cls, *, permit):
        """
        Close the currently open work shift when its configured next-shift
        boundary has passed.

        Expected to be called after the permit has been locked by the caller.
        """
        now = timezone.now()

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

        shift_change_at = cls._get_shift_change_datetime(work_shift=work_shift)

        # Do not silently close shifts if schedule master data is absent.
        if shift_change_at is None:
            return None

        if now < shift_change_at:
            return None

        work_shift.status = PermitWorkShift.Status.CLOSED
        work_shift.closed_at = now
        work_shift.closed_by = None

        # Recommended if you add this field:
        # work_shift.close_reason = PermitWorkShift.CloseReason.SHIFT_CHANGE

        work_shift.save(
            update_fields=[
                "status",
                "closed_at",
                "closed_by",
                # "close_reason",
            ]
        )

        return work_shift
