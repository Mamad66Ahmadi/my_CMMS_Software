#permits/models/approval_models.py

"""
Permit approval models.

Stores every approval/signature related to a Permit.

Unlike a paper permit, approvals are stored as individual records,
providing a complete audit trail.

Author: Mohammad Ahmadi
"""

from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from permits.models.permit_models import Permit


User = get_user_model()


# ============================================================
# Approval Roles
# ============================================================

class ApprovalRoleChoices(models.TextChoices):

    REQUESTER = "REQUESTER", "Requester"

    WORK_SUPERVISOR = "WORK_SUPERVISOR", "Work Supervisor"

    AREA_AUTHORITY = "AREA_AUTHORITY", "Area Authority"

    OPERATIONS = "OPERATIONS", "Operations"

    HSE = "HSE", "HSE Officer"

    GAS_TESTER = "GAS_TESTER", "Gas Tester"

    FIRE_WATCH = "FIRE_WATCH", "Fire Watch"

    CONTRACTOR_SUPERVISOR = (
        "CONTRACTOR_SUPERVISOR",
        "Contractor Supervisor",
    )

    PERMIT_HOLDER = (
        "PERMIT_HOLDER",
        "Permit Holder",
    )

    PERMIT_ISSUER = (
        "PERMIT_ISSUER",
        "Permit Issuer",
    )

    MAINTENANCE_SUPERVISOR = (
        "MAINTENANCE_SUPERVISOR",
        "Maintenance Supervisor",
    )

    PROCESS_ENGINEER = (
        "PROCESS_ENGINEER",
        "Process Engineer",
    )

    ELECTRICAL_SUPERVISOR = (
        "ELECTRICAL_SUPERVISOR",
        "Electrical Supervisor",
    )

    INSTRUMENT_SUPERVISOR = (
        "INSTRUMENT_SUPERVISOR",
        "Instrument Supervisor",
    )

    CLOSE_OUT = (
        "CLOSE_OUT",
        "Close-out Authority",
    )


# =============================================================================
# Approval Decision
# =============================================================================

class ApprovalDecision(models.TextChoices):

    PENDING = "PENDING", "Pending"

    APPROVED = "APPROVED", "Approved"

    REJECTED = "REJECTED", "Rejected"

    RETURNED = "RETURNED", "Returned for Correction"

    CANCELLED = "CANCELLED", "Cancelled"


# =============================================================================
# Permit Approval
# =============================================================================

class PermitApproval(models.Model):
    """
    One approval/signature for one permit.

    A permit normally contains several approvals.

    Example

    Permit 10455

        Requester
        ✔ Approved

        Area Authority
        ✔ Approved

        Gas Tester
        ✔ Approved

        Permit Issuer
        ✔ Approved
    """

    permit = models.ForeignKey(
        Permit,
        on_delete=models.CASCADE,
        related_name="approvals",
    )

    role = models.CharField(
        max_length=40,
        choices=ApprovalRoleChoices.choices,
        db_index=True,
    )

    sequence = models.PositiveSmallIntegerField(
        default=1,
        help_text="Workflow order.",
    )

    approver = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="permit_approvals",
    )

    decision = models.CharField(
        max_length=20,
        choices=ApprovalDecision.choices,
        default=ApprovalDecision.PENDING,
        db_index=True,
    )

    comments = models.TextField(
        blank=True,
    )

    signed_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional approval expiry.",
    )

    is_current = models.BooleanField(
        default=True,
        db_index=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_permit_approvals",
    )

    modified_at = models.DateTimeField(
        auto_now=True,
    )

    modified_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modified_permit_approvals",
    )

    class Meta:

        ordering = [
            "sequence",
            "created_at",
        ]

        indexes = [

            models.Index(
                fields=[
                    "permit",
                    "role",
                ]
            ),

            models.Index(
                fields=[
                    "permit",
                    "decision",
                ]
            ),

            models.Index(
                fields=[
                    "approver",
                    "decision",
                ]
            ),

        ]

        constraints = [

            models.UniqueConstraint(
                fields=[
                    "permit",
                    "role",
                    "sequence",
                ],
                condition=Q(is_current=True),
                name="uq_current_permit_role_step",
            ),
            models.CheckConstraint(
                condition=Q(sequence__gt=0),
                name="permit_approval_sequence_ck",
            ),

        ]

    def __str__(self):

        return (
            f"{self.permit.permit_number}"
            f" - {self.get_role_display()}"
        )

    def clean(self):
        super().clean()
        signed_decisions = {
            ApprovalDecision.APPROVED,
            ApprovalDecision.REJECTED,
            ApprovalDecision.RETURNED,
        }

        if self.decision in signed_decisions and not self.signed_at:
            raise ValidationError(
                {"signed_at": "Signed at is required for this decision."}
            )
        if self.decision not in signed_decisions and self.signed_at:
            raise ValidationError(
                {"signed_at": "Unsigned decisions cannot have a signature time."}
            )
        if (
            self.decision in {ApprovalDecision.REJECTED, ApprovalDecision.RETURNED}
            and not self.comments.strip()
        ):
            raise ValidationError(
                {"comments": "Comments are required for rejection or return."}
            )
        if self.expires_at and self.signed_at and self.expires_at <= self.signed_at:
            raise ValidationError(
                {"expires_at": "Expiry must be after the signature time."}
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def is_signed(self):

        return self.decision == ApprovalDecision.APPROVED

    @property
    def is_pending(self):

        return self.decision == ApprovalDecision.PENDING

    @property
    def is_rejected(self):

        return self.decision == ApprovalDecision.REJECTED

    @property
    def has_expired(self):

        if self.expires_at is None:
            return False

        return timezone.now() > self.expires_at

    def approve(self, user, comments=""):

        self.approver = user
        self.comments = comments
        self.decision = ApprovalDecision.APPROVED
        self.signed_at = timezone.now()
        self.modified_by = user
        self.save()

    def reject(self, user, comments):

        self.approver = user
        self.comments = comments
        self.decision = ApprovalDecision.REJECTED
        self.signed_at = timezone.now()
        self.modified_by = user
        self.save()

    def return_for_revision(self, user, comments):

        self.approver = user
        self.comments = comments
        self.decision = ApprovalDecision.RETURNED
        self.signed_at = timezone.now()
        self.modified_by = user
        self.save()
