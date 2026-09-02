from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0013_forecastsnapshot_past_days_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="forecastrecord",
            name="rain_mm",
            field=models.DecimalField(decimal_places=1, default=0, max_digits=5),
        ),
    ]
