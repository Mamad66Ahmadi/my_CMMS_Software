import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("permits", "0036_paper_safety_many_permits_and_location")]

    operations = [
        migrations.AddField(
            model_name="papersafetypermittype",
            name="display_color",
            field=models.CharField(
                default="#64748B",
                help_text="Color used for this safety-permit type in the permit panel.",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a valid hexadecimal color, for example #64748B.",
                        regex="^#[0-9A-Fa-f]{6}$",
                    )
                ],
                verbose_name="Display color",
            ),
        ),
        migrations.AddField(
            model_name="historicalpapersafetypermittype",
            name="display_color",
            field=models.CharField(
                default="#64748B",
                help_text="Color used for this safety-permit type in the permit panel.",
                max_length=7,
                validators=[
                    django.core.validators.RegexValidator(
                        message="Enter a valid hexadecimal color, for example #64748B.",
                        regex="^#[0-9A-Fa-f]{6}$",
                    )
                ],
                verbose_name="Display color",
            ),
        ),
    ]
