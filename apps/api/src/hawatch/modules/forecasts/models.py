from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class WeatherPoint(models.Model):
    class Kind(models.TextChoices):
        DESTINATION = "destination", "destination"
        ROUTE_POINT = "route_point", "route_point"

    slug = models.SlugField(max_length=96, unique=True)
    name = models.CharField(max_length=80)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    location = models.PointField(srid=4326, spatial_index=False)
    elevation_m = models.PositiveIntegerField()
    destination = models.ForeignKey(
        "destinations.Destination",
        on_delete=models.PROTECT,
        related_name="weather_points",
        null=True,
        blank=True,
    )
    route_point = models.OneToOneField(
        "routes.RoutePoint",
        on_delete=models.CASCADE,
        related_name="weather_point",
        null=True,
        blank=True,
    )
    climate = models.CharField(max_length=32)
    data_mode = models.CharField(max_length=16, default="demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")

    class Meta:
        indexes = [
            models.Index(fields=["kind", "destination"], name="weatherpoint_kind_dest_idx"),
            models.Index(fields=["slug"], name="weatherpoint_slug_idx"),
            GistIndex(fields=["location"], name="weatherpoint_location_gist"),
        ]

    def __str__(self) -> str:
        return self.slug


class ForecastRecord(models.Model):
    class Freshness(models.TextChoices):
        READY = "ready", "ready"
        STALE = "stale", "stale"
        PARTIAL = "partial", "partial"

    class Severity(models.TextChoices):
        NORMAL = "normal", "normal"
        CHANGE = "change", "change"
        CRITICAL = "critical", "critical"

    weather_point = models.ForeignKey(
        WeatherPoint,
        on_delete=models.CASCADE,
        related_name="forecasts",
    )
    forecast_at = models.DateTimeField()
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    generated_at = models.DateTimeField()
    hour_bucket = models.CharField(max_length=16)
    temperature_c = models.SmallIntegerField()
    apparent_temperature_c = models.SmallIntegerField()
    weather_code = models.CharField(max_length=16)
    condition_label = models.CharField(max_length=48)
    icon = models.CharField(max_length=8)
    wind_speed_kmh = models.PositiveSmallIntegerField()
    wind_gust_kmh = models.PositiveSmallIntegerField()
    wind_direction_deg = models.PositiveSmallIntegerField()
    precipitation_probability = models.PositiveSmallIntegerField()
    precipitation_mm = models.DecimalField(max_digits=5, decimal_places=1)
    visibility_km = models.DecimalField(max_digits=5, decimal_places=1)
    cloud_cover_pct = models.PositiveSmallIntegerField()
    uv_index = models.PositiveSmallIntegerField()
    freezing_level_m = models.PositiveIntegerField(null=True, blank=True)
    cloud_base_m = models.PositiveIntegerField(null=True, blank=True)
    severity = models.CharField(max_length=16, choices=Severity.choices)
    freshness = models.CharField(max_length=16, choices=Freshness.choices, default=Freshness.READY)
    data_mode = models.CharField(max_length=16, default="demo")
    source = models.CharField(max_length=32, default="hawatch-demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")
    provider = models.CharField(max_length=32, default="demo")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["weather_point", "forecast_at", "seed_version"],
                name="uniq_forecast_point_time_seed",
            )
        ]
        indexes = [
            models.Index(fields=["weather_point", "forecast_at"], name="forecast_point_at_idx"),
            models.Index(fields=["forecast_at"], name="forecast_at_idx"),
            models.Index(fields=["valid_from", "valid_to"], name="forecast_valid_idx"),
            models.Index(fields=["hour_bucket"], name="forecast_hour_bucket_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.weather_point.slug}@{self.forecast_at.isoformat()}"


class DemoSeedState(models.Model):
    """Tracks the last Asia/Tehran hour bucket that demo forecasts were generated for."""

    key = models.CharField(max_length=32, unique=True, default="demo")
    seed_version = models.CharField(max_length=32)
    last_hour_bucket = models.CharField(max_length=16)
    generated_at = models.DateTimeField()
    local_date = models.DateField()
    local_hour = models.PositiveSmallIntegerField()

    def __str__(self) -> str:
        return f"{self.key}:{self.last_hour_bucket}"
