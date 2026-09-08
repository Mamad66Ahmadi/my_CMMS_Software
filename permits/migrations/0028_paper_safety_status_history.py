from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def migrate_legacy_statuses(apps, schema_editor):
    PaperSafetyPermit = apps.get_model("permits", "PermitPaperSafetyPermit")
    PaperSafetyPermit.objects.filter(status="APPROVED").update(status="ACTIVE")
    PaperSafetyPermit.objects.filter(status="REJECTED").update(status="CANCELLED")


class Migration(migrations.Migration):
    dependencies = [("permits", "0027_replace_digital_safety_permits_with_paper_records")]

    operations = [
        migrations.AlterField(
            model_name="permitpapersafetypermit",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
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
        migrations.RunPython(
            code=migrate_legacy_statuses,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RemoveConstraint(
            model_name="permitpapersafetypermit",
            name="paper_safety_status_values_ck",
        ),
        migrations.AddConstraint(
            model_name="permitpapersafetypermit",
            constraint=models.CheckConstraint(
                condition=~models.Q(status="ACTIVE") | ~models.Q(safety_permit_number=""),
                name="paper_safety_active_complete_ck",
            ),
        ),
        migrations.CreateModel(
            name="PermitPaperSafetyPermitStatusHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_status", models.CharField(blank=True, max_length=20)),
                ("to_status", models.CharField(choices=[("PENDING", "Pending"), ("ACTIVE", "Active"), ("CANCELLED", "Cancelled"), ("TERMINATED", "Terminated")], max_length=20)),
                ("changed_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("remarks", models.TextField(blank=True)),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="paper_safety_permit_status_changes", to=settings.AUTH_USER_MODEL)),
                ("permit_safety_permit", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_history", to="permits.permitpapersafetypermit")),
            ],
            options={
                "ordering": ["-changed_at", "-pk"],
                "verbose_name": "Paper Safety Permit Status History",
                "verbose_name_plural": "Paper Safety Permit Status History",
            },
        ),
        migrations.AddIndex(
            model_name="permitpapersafetypermitstatushistory",
            index=models.Index(fields=["permit_safety_permit", "-changed_at"], name="paper_safety_status_hist_idx"),
        ),
    ]
