import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0002_disable_auto_spatial_indexes"),
        ("routes", "0002_disable_auto_spatial_indexes"),
        ("destinations", "0002_disable_auto_spatial_indexes"),
    ]

    operations = [
        # NOTE: WeatherPoint.route_point is intentionally kept here.
        # routes.0003 adds RoutePoint.weather_point; forecasts.0005 backfills then removes
        # the legacy OneToOne so associations are preserved safely.
        migrations.AlterField(
            model_name="weatherpoint",
            name="elevation_m",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="weatherpoint",
            name="kind",
            field=models.CharField(
                choices=[
                    ("destination", "destination"),
                    ("route_point", "route_point"),
                    ("shared", "shared"),
                ],
                default="shared",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="status",
            field=models.CharField(
                choices=[
                    ("approved", "approved"),
                    ("provisional", "provisional"),
                    ("unresolved_elevation", "unresolved_elevation"),
                ],
                default="approved",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="provenance",
            field=models.CharField(
                choices=[
                    ("curated", "curated"),
                    ("demo_fixture", "demo_fixture"),
                    ("dem_pending", "dem_pending"),
                ],
                default="curated",
                max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="weatherpoint",
            name="catalog_version",
            field=models.CharField(blank=True, default="", max_length=64),
        ),
        migrations.AddIndex(
            model_name="weatherpoint",
            index=models.Index(fields=["catalog_version"], name="weatherpoint_catalog_ver_idx"),
        ),
        migrations.CreateModel(
            name="ForecastSnapshot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(default="open-meteo", max_length=32)),
                ("source", models.CharField(default="open-meteo-forecast", max_length=64)),
                ("catalog_version", models.CharField(blank=True, default="", max_length=64)),
                ("timezone_name", models.CharField(default="Asia/Tehran", max_length=64)),
                ("models_param", models.CharField(default="best_match", max_length=32)),
                ("cell_selection", models.CharField(default="land", max_length=16)),
                ("forecast_days", models.PositiveSmallIntegerField(default=7)),
                ("past_days", models.PositiveSmallIntegerField(default=1)),
                ("batch_size", models.PositiveSmallIntegerField(default=100)),
                ("point_count", models.PositiveIntegerField(default=0)),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "success"), ("partial", "partial"), ("failed", "failed")],
                        default="success",
                        max_length=16,
                    ),
                ),
                (
                    "freshness",
                    models.CharField(
                        choices=[("ready", "ready"), ("stale", "stale"), ("partial", "partial")],
                        default="ready",
                        max_length=16,
                    ),
                ),
                ("requested_at", models.DateTimeField()),
                ("generated_at", models.DateTimeField()),
                ("valid_from", models.DateTimeField(blank=True, null=True)),
                ("valid_to", models.DateTimeField(blank=True, null=True)),
                ("checksum", models.CharField(blank=True, default="", max_length=64)),
                ("raw_response", models.JSONField(blank=True, default=dict)),
                ("notes", models.CharField(blank=True, default="", max_length=255)),
            ],
            options={
                "ordering": ["-generated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="forecastsnapshot",
            index=models.Index(fields=["provider", "-generated_at"], name="forecastsnap_prov_gen_idx"),
        ),
        migrations.AddIndex(
            model_name="forecastsnapshot",
            index=models.Index(fields=["freshness", "-generated_at"], name="forecastsnap_fresh_idx"),
        ),
        migrations.AddIndex(
            model_name="forecastsnapshot",
            index=models.Index(fields=["checksum"], name="forecastsnap_checksum_idx"),
        ),
        migrations.CreateModel(
            name="ForecastPointResolution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requested_latitude", models.FloatField()),
                ("requested_longitude", models.FloatField()),
                ("requested_elevation_m", models.PositiveIntegerField(blank=True, null=True)),
                ("elevation_requested", models.BooleanField(default=False)),
                ("resolved_latitude", models.FloatField(blank=True, null=True)),
                ("resolved_longitude", models.FloatField(blank=True, null=True)),
                ("resolved_elevation_m", models.FloatField(blank=True, null=True)),
                ("utc_offset_seconds", models.IntegerField(blank=True, null=True)),
                ("generationtime_ms", models.FloatField(blank=True, null=True)),
                ("timezone_abbreviation", models.CharField(blank=True, default="", max_length=16)),
                (
                    "snapshot",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="resolutions",
                        to="forecasts.forecastsnapshot",
                    ),
                ),
                (
                    "weather_point",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="provider_resolutions",
                        to="forecasts.weatherpoint",
                    ),
                ),
            ],
        ),
        migrations.AddConstraint(
            model_name="forecastpointresolution",
            constraint=models.UniqueConstraint(
                fields=("snapshot", "weather_point"),
                name="uniq_snapshot_weather_point_resolution",
            ),
        ),
        migrations.AddIndex(
            model_name="forecastpointresolution",
            index=models.Index(fields=["weather_point", "snapshot"], name="fpr_point_snap_idx"),
        ),
        migrations.AddField(
            model_name="forecastrecord",
            name="snapshot",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="hourly_records",
                to="forecasts.forecastsnapshot",
            ),
        ),
        migrations.AddField(
            model_name="forecastrecord",
            name="snowfall_cm",
            field=models.DecimalField(blank=True, decimal_places=1, max_digits=5, null=True),
        ),
        migrations.AddIndex(
            model_name="forecastrecord",
            index=models.Index(fields=["snapshot", "weather_point"], name="forecast_snap_point_idx"),
        ),
    ]
