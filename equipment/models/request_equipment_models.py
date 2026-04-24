
# equipment/models/request_equipment_models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from equipment.models.equipment_models import *


# ----------------------    Getting user model object    ----------------------------------
User = get_user_model()

# --------------------- Base Request Model -----------------------------
from django.utils import timezone

class BaseChangeRequest(models.Model):
    """
    Abstract base class for change request models.
    Provides action/status enums, workflow, and audit fields.
    """

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED_WITH_CHANGE = "approved_with_change", "Approved with Change"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    action = models.CharField(
        max_length=20,
        choices=Action.choices,
        verbose_name="Action Type",
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )

    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_requested",
        verbose_name="Requested By",
    )
    requested_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Requested At",
    )

    reviewed_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_reviewed",
        verbose_name="Reviewed By",
    )
    reviewed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Reviewed At",
    )

    class Meta:
        abstract = True
        ordering = ["-requested_at"]

    # Common state-transition helpers (optional, but handy)
    def _ensure_pending(self):
        if self.status != self.Status.PENDING:
            raise ValidationError("Only pending requests can be processed.")

    def mark_approved(self, reviewer, with_change=False):
        self.status = (
            self.Status.APPROVED_WITH_CHANGE if with_change else self.Status.APPROVED
        )
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])

    def mark_rejected(self, reviewer):
        self._ensure_pending()
        self.status = self.Status.REJECTED
        self.reviewed_by = reviewer
        self.reviewed_at = timezone.now()
        self.save(update_fields=["status", "reviewed_by", "reviewed_at"])


# --------------------- Location Tag Change Request -----------------------------
class LocationTagChangeRequest(BaseChangeRequest):
    """
    Request to create or update a LocationTag.
    """

    location_tag = models.ForeignKey(
        LocationTag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_requests",
        verbose_name="Target Location Tag",
    )

    # requested fields (proposed values)
    loc_tag = models.CharField(
        max_length=50,
        verbose_name="Location Tag Code",
    )

    parent = models.ForeignKey(
        LocationTag,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="child_location_tag_requests",
        verbose_name="Parent Location Tag",
    )

    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )
    long_tag = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name="Long Tag",
    )

    obj_criticality = models.ForeignKey(
        ObjectCriticality,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_tag_change_requests",
    )
    obj_type = models.ForeignKey(
        ObjectType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_tag_change_requests",
    )
    obj_category = models.ForeignKey(
        ObjectCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_tag_change_requests",
    )

    unit = models.ForeignKey(
        Unit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="location_tag_change_requests",
    )
    train = models.IntegerField(
        null=True,
        blank=True,
    )
    note = models.TextField(
        max_length=500,
        null=True,
        blank=True,
    )
    mih_level = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name="MIH Level",
    )

    def clean(self):
        super().clean()

        if self.action == self.Action.CREATE and self.location_tag:
            raise ValidationError("CREATE request must not have location_tag set.")

        if self.action == self.Action.UPDATE and not self.location_tag:
            raise ValidationError("UPDATE request must have a location_tag.")

    def __str__(self):
        return f"[{self.get_action_display()}] {self.loc_tag}"

    # ---------- Core workflow: apply changes ----------
    def approve_request(self, reviewer):
        """
        Apply the requested changes to LocationTag and mark this request as approved.
        """
        from django.db import transaction

        self._ensure_pending()

        with transaction.atomic():
            if self.action == self.Action.CREATE:
                tag = LocationTag.objects.create(
                    loc_tag=self.loc_tag,
                    parent=self.parent,
                    description=self.description,
                    long_tag=self.long_tag,
                    obj_criticality=self.obj_criticality,
                    obj_type=self.obj_type,
                    obj_category=self.obj_category,
                    unit=self.unit,
                    train=self.train,
                    note=self.note,
                    mih_level=self.mih_level,
                    created_by=self.requested_by,  # or reviewer, depending on your policy
                )
                self.location_tag = tag

            elif self.action == self.Action.UPDATE:
                tag = self.location_tag
                if not tag:
                    raise ValidationError("No target LocationTag to update.")

                tag.loc_tag = self.loc_tag
                tag.parent = self.parent
                tag.description = self.description
                tag.long_tag = self.long_tag
                tag.obj_criticality = self.obj_criticality
                tag.obj_type = self.obj_type
                tag.obj_category = self.obj_category
                tag.unit = self.unit
                tag.train = self.train
                tag.note = self.note
                tag.mih_level = self.mih_level
                tag.modified_by = reviewer

                tag.save()

            # mark request as approved
            self.mark_approved(reviewer=reviewer)
            # ensure link to created object is saved if CREATE
            self.save(update_fields=["location_tag"])


# --------------------- Equipment Change Request -----------------------------
class EquipmentChangeRequest(BaseChangeRequest):
    """
    Request to create or update an Equipment.
    """

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_requests",
        verbose_name="Target Equipment",
    )

    # requested values
    functional_location = models.ForeignKey(
        LocationTag,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipment_change_requests",
        verbose_name="Functional Location",
    )

    serial_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Serial Number",
    )

    note = models.TextField(
        max_length=500,
        null=True,
        blank=True,
    )
    manufacturer = models.CharField(
        max_length=100,
        null=True,
        blank=True,
    )
    model = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Model",
    )

    def clean(self):
        super().clean()

        if self.action == self.Action.CREATE and self.equipment:
            raise ValidationError("CREATE request must not have equipment set.")

        if self.action == self.Action.UPDATE and not self.equipment:
            raise ValidationError("UPDATE request must have an equipment.")

    def __str__(self):
        return f"[{self.get_action_display()}] Equipment Request #{self.pk}"

    def approve_request(self, reviewer):
        """
        Apply the requested changes to Equipment and mark this request as approved.
        """
        from django.db import transaction

        self._ensure_pending()

        with transaction.atomic():
            if self.action == self.Action.CREATE:
                eq = Equipment.objects.create(
                    functional_location=self.functional_location,
                    serial_number=self.serial_number,
                    note=self.note,
                    manufacturer=self.manufacturer,
                    model=self.model,
                    created_by=self.requested_by,
                )
                self.equipment = eq

            elif self.action == self.Action.UPDATE:
                eq = self.equipment
                if not eq:
                    raise ValidationError("No target Equipment to update.")

                eq.functional_location = self.functional_location
                eq.serial_number = self.serial_number
                eq.note = self.note
                eq.manufacturer = self.manufacturer
                eq.model = self.model
                eq.modified_by = reviewer
                eq.save()

            self.mark_approved(reviewer=reviewer)
            self.save(update_fields=["equipment"])

# --------------------- Equipment Document Change Request -----------------------------
class EquipmentDocumentChangeRequest(BaseChangeRequest):
    """
    Request to create or update an EquipmentDocument.
    """

    document = models.ForeignKey(
        EquipmentDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="change_requests",
        verbose_name="Target Document",
    )

    equipment = models.ForeignKey(
        Equipment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="document_change_requests",
        verbose_name="Equipment",
    )

    file_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="File Name",
    )
    file = models.FileField(
        upload_to=get_document_upload_path,
        null=True,
        blank=True,
        verbose_name="Document File",
    )

    description = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    def clean(self):
        super().clean()

        if self.action == self.Action.CREATE and self.document:
            raise ValidationError("CREATE request must not have document set.")

        if self.action == self.Action.UPDATE and not self.document:
            raise ValidationError("UPDATE request must have a document.")

    def __str__(self):
        return f"[{self.get_action_display()}] Document Request #{self.pk}"

    def approve_request(self, reviewer):
        """
        Apply the requested changes to EquipmentDocument and mark this request as approved.
        """
        from django.db import transaction

        self._ensure_pending()

        with transaction.atomic():
            if self.action == self.Action.CREATE:
                doc = EquipmentDocument.objects.create(
                    equipment=self.equipment,
                    file_name=self.file_name or (self.file.name if self.file else ""),
                    file=self.file,
                    description=self.description,
                    created_by=self.requested_by,
                )
                self.document = doc

            elif self.action == self.Action.UPDATE:
                doc = self.document
                if not doc:
                    raise ValidationError("No target EquipmentDocument to update.")

                doc.equipment = self.equipment
                doc.file_name = self.file_name or doc.file_name
                if self.file:
                    doc.file = self.file
                doc.description = self.description
                doc.modified_by = reviewer
                doc.save()

            self.mark_approved(reviewer=reviewer)
            self.save(update_fields=["document"])
