import django.db.models.deletion
from django.db import migrations, models


def copy_primary_permits_to_links(apps, schema_editor):
    safety_model = apps.get_model("permits", "PermitPaperSafetyPermit")
    through = safety_model._meta.get_field("permits").remote_field.through
    for record in safety_model.objects.exclude(permit_id=None).only("pk", "permit_id"):
        through.objects.get_or_create(
            permitpapersafetypermit_id=record.pk,
            permit_id=record.permit_id,
        )


class Migration(migrations.Migration):
    dependencies = [("permits", "0035_historicalpapersafetypermittype_validity_shifts_and_more")]

    operations = [
        migrations.AlterField(
            model_name="permitpapersafetypermit",
            name="permit",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="primary_paper_safety_permits",
                to="permits.permit",
            ),
        ),
        migrations.AddField(
            model_name="permitpapersafetypermit",
            name="location_tag",
            field=models.ForeignKey(
                blank=True,
                help_text="Location where this safety permit applies; may differ from the main permit.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="paper_safety_permits",
                to="equipment.locationtag",
            ),
        ),
        migrations.AddField(
            model_name="permitpapersafetypermit",
            name="permits",
            field=models.ManyToManyField(
                blank=True,
                related_name="paper_safety_permits",
                to="permits.permit",
                verbose_name="Main permits",
            ),
        ),
        migrations.RunPython(copy_primary_permits_to_links, migrations.RunPython.noop),
    ]
