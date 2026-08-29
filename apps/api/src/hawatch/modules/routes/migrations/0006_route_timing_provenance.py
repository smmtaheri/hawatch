# Additive route timing provenance / one-way duration fields for catalog-driven estimates.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0005_route_origin_target_weather_points"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="one_way_minutes",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Estimated one-way ascent duration at medium pace (not round-trip).",
            ),
        ),
        migrations.AddField(
            model_name="route",
            name="timing_method",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="route",
            name="timing_version",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddField(
            model_name="route",
            name="timing_confidence",
            field=models.CharField(blank=True, default="", max_length=16),
        ),
        migrations.AddField(
            model_name="route",
            name="timing_uncertainty_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="route",
            name="timing_source_urls",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
