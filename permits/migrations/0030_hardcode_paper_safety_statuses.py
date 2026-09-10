from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import simple_history.models


STEP_STATUS = {
    "Pending": "DEACTIVE",
    "Cancelled": "DEACTIVE",
    "Activated": "ACTIVE",
    "Expired": "DEACTIVE",
    "Terminated": "DEACTIVE",
}


def migrate_statuses_and_steps(apps, schema_editor):
    Permit = apps.get_model("permits", "PermitPaperSafetyPermit")
    Step = apps.get_model("permits", "PaperSafetyPermitWorkflowStep")

    Permit.objects.exclude(status="ACTIVE").update(status="DEACTIVE")
    for order, (name, status) in enumerate(STEP_STATUS.items()):
        Step.objects.update_or_create(
            name=name,
            defaults={"status": status, "step_order": order, "is_active": True},
        )

    activated = Step.objects.get(name="Activated")
    pending = Step.objects.get(name="Pending")
    Permit.objects.filter(status="ACTIVE").update(current_step=activated)
    Permit.objects.filter(status="DEACTIVE").update(current_step=pending)


class Migration(migrations.Migration):
    dependencies = [("permits", "0029_configure_paper_safety_workflow")]

    operations = [
        migrations.AddField(
            model_name="papersafetypermittype",
            name="created_at",
            field=models.DateTimeField(
                auto_now_add=True,
                default=django.utils.timezone.now,
                verbose_name="Registration Date",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="papersafetypermittype",
            name="created_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="permits_papersafetypermittype_created",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Registered By",
            ),
        ),
        migrations.AddField(
            model_name="papersafetypermittype",
            name="modified_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Last Modified"),
        ),
        migrations.AddField(
            model_name="papersafetypermittype",
            name="modified_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="permits_papersafetypermittype_modified",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Modified By",
            ),
        ),
        migrations.CreateModel(
            name="HistoricalPaperSafetyPermitType",
            fields=[
                ("id", models.BigIntegerField(blank=True, db_index=True)),
                ("code", models.CharField(db_index=True, max_length=30)),
                ("name", models.CharField(max_length=100)),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(blank=True, editable=False, verbose_name="Registration Date")),
                ("modified_at", models.DateTimeField(blank=True, editable=False, verbose_name="Last Modified")),
                ("is_active", models.BooleanField(default=True)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_type", models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1)),
                ("created_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Registered By")),
                ("history_user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("modified_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Modified By")),
            ],
            options={"ordering": ("-history_date", "-history_id"), "get_latest_by": ("history_date", "history_id"), "verbose_name": "historical Paper Safety Permit Type"},
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name="papersafetypermitworkflowstep",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now, verbose_name="Registration Date"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="papersafetypermitworkflowstep",
            name="created_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="permits_papersafetypermitworkflowstep_created", to=settings.AUTH_USER_MODEL, verbose_name="Registered By"),
        ),
        migrations.AddField(
            model_name="papersafetypermitworkflowstep",
            name="modified_at",
            field=models.DateTimeField(auto_now=True, verbose_name="Last Modified"),
        ),
        migrations.AddField(
            model_name="papersafetypermitworkflowstep",
            name="modified_by",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="permits_papersafetypermitworkflowstep_modified", to=settings.AUTH_USER_MODEL, verbose_name="Modified By"),
        ),
        migrations.CreateModel(
            name="HistoricalPaperSafetyPermitWorkflowStep",
            fields=[
                ("id", models.BigIntegerField(blank=True, db_index=True)),
                ("name", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[("ACTIVE", "Active"), ("DEACTIVE", "Deactive")], default="DEACTIVE", max_length=10)),
                ("step_order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(blank=True, editable=False, verbose_name="Registration Date")),
                ("modified_at", models.DateTimeField(blank=True, editable=False, verbose_name="Last Modified")),
                ("is_active", models.BooleanField(default=True)),
                ("history_id", models.AutoField(primary_key=True, serialize=False)),
                ("history_date", models.DateTimeField(db_index=True)),
                ("history_change_reason", models.CharField(max_length=100, null=True)),
                ("history_type", models.CharField(choices=[("+", "Created"), ("~", "Changed"), ("-", "Deleted")], max_length=1)),
                ("created_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Registered By")),
                ("history_user", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to=settings.AUTH_USER_MODEL)),
                ("modified_by", models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name="+", to=settings.AUTH_USER_MODEL, verbose_name="Modified By")),
            ],
            options={"ordering": ("-history_date", "-history_id"), "get_latest_by": ("history_date", "history_id"), "verbose_name": "historical Paper Safety Permit Workflow Step"},
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.AddField(
            model_name="permitpapersafetypermit",
            name="current_step",
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="paper_safety_permits", to="permits.papersafetypermitworkflowstep"),
        ),
        migrations.RemoveField(model_name="papersafetypermitworkflowstep", name="status"),
        migrations.AddField(
            model_name="papersafetypermitworkflowstep",
            name="status",
            field=models.CharField(choices=[("ACTIVE", "Active"), ("DEACTIVE", "Deactive")], default="DEACTIVE", max_length=10),
        ),
        migrations.AlterField(
            model_name="permitpapersafetypermit",
            name="status",
            field=models.CharField(choices=[("ACTIVE", "Active"), ("DEACTIVE", "Deactive")], db_index=True, default="DEACTIVE", editable=False, max_length=10),
        ),
        migrations.RunPython(migrate_statuses_and_steps, migrations.RunPython.noop),
        migrations.DeleteModel(name="PaperSafetyPermitStatus"),
    ]
