from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0008_forecastsnapshot_ingest_metrics"),
    ]

    operations = [
        migrations.AddField(
            model_name="weatherpoint",
            name="aliases",
            field=models.JSONField(blank=True, default=list),
        ),
    ]

