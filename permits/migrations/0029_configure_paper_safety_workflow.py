from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


DEFAULT_TYPES = [
    ("ISOLATION", "Isolation"),
    ("CONFINED_SPACE", "Confined Space"),
    ("DIVING", "Diving"),
    ("EXCAVATION", "Excavation"),
    ("EQUIPMENT_TEST", "Equipment Test"),
    ("RADIOGRAPHY", "Radiography"),
]
DEFAULT_STATUSES = [
    ("PENDING", "Pending"),
    ("ACTIVE", "Active"),
    ("CANCELLED", "Cancelled"),
    ("TERMINATED", "Terminated"),
]


def seed_configuration(apps, schema_editor):
    PermitType = apps.get_model("permits", "PaperSafetyPermitType")
    Status = apps.get_model("permits", "PaperSafetyPermitStatus")
    for order, (code, name) in enumerate(DEFAULT_TYPES):
        PermitType.objects.get_or_create(
            code=code, defaults={"name": name, "sort_order": order}
        )
    for order, (code, name) in enumerate(DEFAULT_STATUSES):
        Status.objects.get_or_create(
            code=code, defaults={"name": name, "sort_order": order}
        )
    Step = apps.get_model("permits", "PaperSafetyPermitWorkflowStep")
    status_ids = dict(Status.objects.values_list("code", "id"))
    for order, (code, name) in enumerate(DEFAULT_STATUSES):
        Step.objects.get_or_create(
            name=name,
            defaults={
                "status_id": status_ids[code],
                "step_order": order,
            },
        )


def migrate_safety_type_values(apps, schema_editor):
    Permit = apps.get_model("permits", "PermitPaperSafetyPermit")
    PermitType = apps.get_model("permits", "PaperSafetyPermitType")
    type_ids = dict(PermitType.objects.values_list("code", "id"))
    for record in Permit.objects.all().iterator():
        record.safety_type_ref_id = type_ids.get(record.safety_type)
        record.save(update_fields=["safety_type_ref"])


class Migration(migrations.Migration):
    dependencies = [("permits", "0028_paper_safety_status_history")]

    operations = [
        migrations.CreateModel(
            name="PaperSafetyPermitType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=30, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "name", "pk"]},
        ),
        migrations.CreateModel(
            name="PaperSafetyPermitStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("is_active", models.BooleanField(default=True)),
                ("sort_order", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ["sort_order", "pk"]},
        ),
        migrations.CreateModel(
            name="PaperSafetyPermitWorkflowStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100)),
                ("step_order", models.PositiveIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("status", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="workflow_steps", to="permits.papersafetypermitstatus")),
            ],
            options={"ordering": ["step_order", "pk"]},
        ),
        migrations.AddConstraint(
            model_name="papersafetypermitworkflowstep",
            constraint=models.UniqueConstraint(fields=("name",), name="uq_paper_safety_workflow_step_name"),
        ),
        migrations.RunPython(seed_configuration, migrations.RunPython.noop),
        migrations.AddField(
            model_name="permitpapersafetypermit",
            name="safety_type_ref",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="_legacy_paper_safety_permits", to="permits.papersafetypermittype"),
        ),
        migrations.RunPython(migrate_safety_type_values, migrations.RunPython.noop),
        migrations.RemoveConstraint(
            model_name="permitpapersafetypermit",
            name="uq_paper_safety_type_number",
        ),
        migrations.RemoveIndex(
            model_name="permitpapersafetypermit",
            name="paper_safety_permit_type_idx",
        ),
        migrations.RemoveField(model_name="permitpapersafetypermit", name="safety_type"),
        migrations.RenameField(model_name="permitpapersafetypermit", old_name="safety_type_ref", new_name="safety_type"),
        migrations.AlterField(
            model_name="permitpapersafetypermit",
            name="safety_type",
            field=models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.PROTECT, related_name="paper_safety_permits", to="permits.papersafetypermittype"),
        ),
        migrations.AddConstraint(
            model_name="permitpapersafetypermit",
            constraint=models.UniqueConstraint(
                condition=~models.Q(safety_permit_number=""),
                fields=("safety_type", "safety_permit_number"),
                name="uq_paper_safety_type_number",
            ),
        ),
        migrations.AddIndex(
            model_name="permitpapersafetypermit",
            index=models.Index(
                fields=("permit", "safety_type"),
                name="paper_safety_permit_type_idx",
            ),
        ),
        migrations.AlterField(
            model_name="permitpapersafetypermitstatushistory",
            name="to_status",
            field=models.CharField(max_length=20),
        ),
    ]
