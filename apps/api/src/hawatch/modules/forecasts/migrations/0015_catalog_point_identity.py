from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0014_forecastrecord_rain_mm"),
    ]

    operations = [
        migrations.AddField(
            model_name="weatherpoint",
            name="page_name",
            field=models.CharField(blank=True, default="", max_length=160),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="short_label",
            field=models.CharField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="place_type",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="identity_summary",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="importance",
            field=models.CharField(default="support", max_length=16),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="name_status",
            field=models.CharField(default="descriptive", max_length=16),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="source_urls",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
