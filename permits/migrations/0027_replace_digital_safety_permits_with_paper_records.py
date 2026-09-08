# Generated for the temporary paper safety-permit phase.

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("permits", "0026_remove_safetypermit_activated_at_and_more"),
    ]

    operations = [
        # Park the future structured safety-permit models in Django's model
        # state without dropping their database tables or existing data.
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.RemoveField(
                    model_name="permit",
                    name="required_safety_permits",
                ),
                migrations.DeleteModel(
                    name="PermitSafetyRequirement",
                ),
                migrations.DeleteModel(
                    name="ConfinedSpacePermit",
                ),
                migrations.DeleteModel(
                    name="DivingPermit",
                ),
                migrations.DeleteModel(
                    name="EquipmentTestPermit",
                ),
                migrations.DeleteModel(
                    name="ExcavationPermit",
                ),
                migrations.DeleteModel(
                    name="IsolationPermit",
                ),
                migrations.DeleteModel(
                    name="RadiographyPermit",
                ),
                migrations.DeleteModel(
                    name="SafetyPermit",
                ),
            ],
        ),
        migrations.CreateModel(
            name="PermitPaperSafetyPermit",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "safety_type",
                    models.CharField(
                        choices=[
                            ("ISOLATION", "Isolation"),
                            ("CONFINED_SPACE", "Confined Space"),
                            ("DIVING", "Diving"),
                            ("EXCAVATION", "Excavation"),
                            ("EQUIPMENT_TEST", "Equipment Test"),
                            ("RADIOGRAPHY", "Radiography"),
                        ],
                        db_index=True,
                        max_length=30,
                    ),
                ),
                (
                    "safety_permit_number",
                    models.CharField(
                        blank=True,
                        help_text=(
                            "May be left blank until the paper safety permit is issued."
                        ),
                        max_length=30,
                        validators=[
                            django.core.validators.RegexValidator(
                                message=(
                                    "Use uppercase letters, numbers, periods, "
                                    "underscores, or hyphens only."
                                ),
                                regex=r"^[A-Z0-9][A-Z0-9._-]*$",
                            )
                        ],
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending Permit Office Review"),
                            ("ACTIVE", "Active"),
                            ("CANCELLED", "Cancelled"),
                            ("TERMINATED", "Terminated"),
                        ],
                        db_index=True,
                        default="PENDING",
                        editable=False,
                        max_length=20,
                    ),
                ),
                (
                    "review_comment",
                    models.TextField(blank=True, editable=False),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(blank=True, editable=False, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("modified_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="created_paper_safety_permits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "modified_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="modified_paper_safety_permits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "permit",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="paper_safety_permits",
                        to="permits.permit",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reviewed_paper_safety_permits",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Paper Safety Permit",
                "verbose_name_plural": "Paper Safety Permits",
                "ordering": ["permit", "safety_type", "pk"],
                "indexes": [
                    models.Index(
                        fields=["permit", "status"],
                        name="paper_safety_permit_status_idx",
                    ),
                    models.Index(
                        fields=["permit", "safety_type"],
                        name="paper_safety_permit_type_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=~models.Q(safety_permit_number=""),
                        fields=("safety_type", "safety_permit_number"),
                        name="uq_paper_safety_type_number",
                    ),
                    models.CheckConstraint(
                        condition=(
                            ~models.Q(status="ACTIVE")
                            | ~models.Q(safety_permit_number="")
                        ),
                        name="paper_safety_active_complete_ck",
                    ),
                    models.CheckConstraint(
                        condition=models.Q(status__in=["PENDING", "ACTIVE", "CANCELLED", "TERMINATED"]),
                        name="paper_safety_status_values_ck",
                    ),
                ],
            },
        ),
    ]
