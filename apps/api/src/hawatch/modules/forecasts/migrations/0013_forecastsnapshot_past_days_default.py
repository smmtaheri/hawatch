from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0012_weatherpoint_runtime_flags"),
    ]

    operations = [
        migrations.AlterField(
            model_name="forecastsnapshot",
            name="past_days",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
