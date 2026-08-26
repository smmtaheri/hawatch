import django.contrib.gis.db.models.fields
import django.contrib.postgres.indexes
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("destinations", "0001_initial"),
        ("routes", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="WeatherPoint",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=96, unique=True)),
                ("name", models.CharField(max_length=80)),
                ("kind", models.CharField(choices=[("destination", "destination"), ("route_point", "route_point")], max_length=16)),
                ("location", django.contrib.gis.db.models.fields.PointField(srid=4326)),
                ("elevation_m", models.PositiveIntegerField()),
                ("climate", models.CharField(max_length=32)),
                ("data_mode", models.CharField(default="demo", max_length=16)),
                ("seed_version", models.CharField(default="hawatch-demo-v1", max_length=32)),
                (
                    "destination",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="weather_points",
                        to="destinations.destination",
                    ),
                ),
                (
                    "route_point",
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="weather_point",
                        to="routes.routepoint",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ForecastRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("forecast_at", models.DateTimeField()),
                ("valid_from", models.DateTimeField()),
                ("valid_to", models.DateTimeField()),
                ("generated_at", models.DateTimeField()),
                ("hour_bucket", models.CharField(max_length=16)),
                ("temperature_c", models.SmallIntegerField()),
                ("apparent_temperature_c", models.SmallIntegerField()),
                ("weather_code", models.CharField(max_length=16)),
                ("condition_label", models.CharField(max_length=48)),
                ("icon", models.CharField(max_length=8)),
                ("wind_speed_kmh", models.PositiveSmallIntegerField()),
                ("wind_gust_kmh", models.PositiveSmallIntegerField()),
                ("wind_direction_deg", models.PositiveSmallIntegerField()),
                ("precipitation_probability", models.PositiveSmallIntegerField()),
                ("precipitation_mm", models.DecimalField(decimal_places=1, max_digits=5)),
                ("visibility_km", models.DecimalField(decimal_places=1, max_digits=5)),
                ("cloud_cover_pct", models.PositiveSmallIntegerField()),
                ("uv_index", models.PositiveSmallIntegerField()),
                ("freezing_level_m", models.PositiveIntegerField(blank=True, null=True)),
                ("cloud_base_m", models.PositiveIntegerField(blank=True, null=True)),
                ("severity", models.CharField(choices=[("normal", "normal"), ("change", "change"), ("critical", "critical")], max_length=16)),
                ("freshness", models.CharField(choices=[("ready", "ready"), ("stale", "stale"), ("partial", "partial")], default="ready", max_length=16)),
                ("data_mode", models.CharField(default="demo", max_length=16)),
                ("source", models.CharField(default="hawatch-demo", max_length=32)),
                ("seed_version", models.CharField(default="hawatch-demo-v1", max_length=32)),
                ("provider", models.CharField(default="demo", max_length=32)),
                (
                    "weather_point",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="forecasts",
                        to="forecasts.weatherpoint",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="DemoSeedState",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(default="demo", max_length=32, unique=True)),
                ("seed_version", models.CharField(max_length=32)),
                ("last_hour_bucket", models.CharField(max_length=16)),
                ("generated_at", models.DateTimeField()),
                ("local_date", models.DateField()),
                ("local_hour", models.PositiveSmallIntegerField()),
            ],
        ),
        migrations.AddIndex(
            model_name="weatherpoint",
            index=models.Index(fields=["kind", "destination"], name="weatherpoint_kind_dest_idx"),
        ),
        migrations.AddIndex(
            model_name="weatherpoint",
            index=models.Index(fields=["slug"], name="weatherpoint_slug_idx"),
        ),
        migrations.AddIndex(
            model_name="weatherpoint",
            index=django.contrib.postgres.indexes.GistIndex(fields=["location"], name="weatherpoint_location_gist"),
        ),
        migrations.AddConstraint(
            model_name="forecastrecord",
            constraint=models.UniqueConstraint(fields=("weather_point", "forecast_at", "seed_version"), name="uniq_forecast_point_time_seed"),
        ),
        migrations.AddIndex(
            model_name="forecastrecord",
            index=models.Index(fields=["weather_point", "forecast_at"], name="forecast_point_at_idx"),
        ),
        migrations.AddIndex(
            model_name="forecastrecord",
            index=models.Index(fields=["forecast_at"], name="forecast_at_idx"),
        ),
        migrations.AddIndex(
            model_name="forecastrecord",
            index=models.Index(fields=["valid_from", "valid_to"], name="forecast_valid_idx"),
        ),
        migrations.AddIndex(
            model_name="forecastrecord",
            index=models.Index(fields=["hour_bucket"], name="forecast_hour_bucket_idx"),
        ),
    ]
