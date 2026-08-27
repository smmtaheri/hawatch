import django.contrib.gis.db.models.fields
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0002_disable_auto_spatial_indexes"),
        ("forecasts", "0003_live_forecast_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="catalog_key",
            field=models.SlugField(blank=True, default="", max_length=80),
        ),
        migrations.AddField(
            model_name="route",
            name="timing_status",
            field=models.CharField(
                choices=[("curated", "curated"), ("estimated", "estimated"), ("pending", "pending")],
                default="estimated",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="route",
            name="ascent_m",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="route",
            name="default_start_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="route",
            name="distance_km",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True),
        ),
        migrations.AlterField(
            model_name="route",
            name="round_trip_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="route",
            index=models.Index(fields=["catalog_key"], name="route_catalog_key_idx"),
        ),
        migrations.AddField(
            model_name="routepoint",
            name="weather_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="route_links",
                to="forecasts.weatherpoint",
            ),
        ),
        migrations.AddField(
            model_name="routepoint",
            name="segment_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="routepoint",
            name="cumulative_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="routepoint",
            name="segment_distance_m",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="routepoint",
            name="progress_pct",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True),
        ),
        migrations.AddField(
            model_name="routepoint",
            name="timing_status",
            field=models.CharField(
                choices=[("curated", "curated"), ("estimated", "estimated"), ("pending", "pending")],
                default="pending",
                max_length=16,
            ),
        ),
        migrations.AlterField(
            model_name="routepoint",
            name="base_minutes",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="routepoint",
            name="elevation_m",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="routepoint",
            name="location",
            field=django.contrib.gis.db.models.fields.PointField(
                blank=True, null=True, spatial_index=False, srid=4326
            ),
        ),
        migrations.AddIndex(
            model_name="routepoint",
            index=models.Index(fields=["weather_point"], name="routepoint_weather_idx"),
        ),
    ]
