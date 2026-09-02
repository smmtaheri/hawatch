from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class WeatherPoint(models.Model):
    """Shared weather-point catalog entry (coordinates/elevation are catalog truth)."""

    class Kind(models.TextChoices):
        DESTINATION = "destination", "destination"
        ROUTE_POINT = "route_point", "route_point"
        SHARED = "shared", "shared"

    class Status(models.TextChoices):
        APPROVED = "approved", "approved"
        PROVISIONAL = "provisional", "provisional"
        UNRESOLVED_ELEVATION = "unresolved_elevation", "unresolved_elevation"

    class Provenance(models.TextChoices):
        CURATED = "curated", "curated"
        DEMO_FIXTURE = "demo_fixture", "demo_fixture"
        DEM_PENDING = "dem_pending", "dem_pending"

    slug = models.SlugField(max_length=96, unique=True)
    name = models.CharField(max_length=80)
    aliases = models.JSONField(default=list, blank=True)
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.SHARED)
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    location = models.PointField(srid=4326, spatial_index=False)
    # Catalog elevation; null means genuinely unresolved — never invent or copy provider elevation here.
    elevation_m = models.PositiveIntegerField(null=True, blank=True)
    # Legacy provenance retained for compatibility with the pre-snapshot schema.
    elevation_source = models.CharField(max_length=255, blank=True, default="")
    destination = models.ForeignKey(
        "destinations.Destination",
        on_delete=models.PROTECT,
        related_name="weather_points",
        null=True,
        blank=True,
    )
    climate = models.CharField(max_length=32, default="alpine")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.APPROVED)
    provenance = models.CharField(max_length=32, choices=Provenance.choices, default=Provenance.CURATED)
    catalog_version = models.CharField(max_length=64, blank=True, default="")
    data_mode = models.CharField(max_length=16, default="demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")
    # Runtime lifecycle — database is source of truth; JSON fixtures only bootstrap/import.
    is_active = models.BooleanField(default=True)
    ingest_enabled = models.BooleanField(default=True)
    fixture_managed = models.BooleanField(
        default=False,
        help_text="True when created/updated from a JSON catalog import; prune only removes fixture_managed rows.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["kind", "destination"], name="weatherpoint_kind_dest_idx"),
            models.Index(fields=["slug"], name="weatherpoint_slug_idx"),
            models.Index(fields=["catalog_version"], name="weatherpoint_catalog_ver_idx"),
            models.Index(fields=["is_active", "ingest_enabled"], name="weatherpoint_ingest_idx"),
            GistIndex(fields=["location"], name="weatherpoint_location_gist"),
        ]

    def __str__(self) -> str:
        return self.slug


class ForecastSnapshot(models.Model):
    """One provider ingest run; stores raw payload + freshness metadata."""

    class Status(models.TextChoices):
        SUCCESS = "success", "success"
        PARTIAL = "partial", "partial"
        FAILED = "failed", "failed"

    class Freshness(models.TextChoices):
        READY = "ready", "ready"
        STALE = "stale", "stale"
        PARTIAL = "partial", "partial"

    provider = models.CharField(max_length=32, default="open-meteo")
    source = models.CharField(max_length=64, default="open-meteo-forecast")
    catalog_version = models.CharField(max_length=64, blank=True, default="")
    timezone_name = models.CharField(max_length=64, default="Asia/Tehran")
    models_param = models.CharField(max_length=32, default="best_match")
    cell_selection = models.CharField(max_length=16, default="land")
    forecast_days = models.PositiveSmallIntegerField(default=7)
    past_days = models.PositiveSmallIntegerField(default=0)
    batch_size = models.PositiveSmallIntegerField(default=100)
    point_count = models.PositiveIntegerField(default=0)
    requested_point_count = models.PositiveIntegerField(default=0)
    retry_count = models.PositiveIntegerField(default=0)
    duration_seconds = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SUCCESS)
    freshness = models.CharField(max_length=16, choices=Freshness.choices, default=Freshness.READY)
    requested_at = models.DateTimeField()
    generated_at = models.DateTimeField()
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    checksum = models.CharField(max_length=64, blank=True, default="")
    raw_response = models.JSONField(default=dict, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["provider", "-generated_at"], name="forecastsnap_prov_gen_idx"),
            models.Index(fields=["freshness", "-generated_at"], name="forecastsnap_fresh_idx"),
            models.Index(fields=["checksum"], name="forecastsnap_checksum_idx"),
        ]
        ordering = ["-generated_at"]

    def __str__(self) -> str:
        return f"{self.provider}:{self.generated_at.isoformat()}:{self.status}"


class ForecastPointResolution(models.Model):
    """Provider-resolved coordinates/elevation for a catalog weather point (never catalog truth)."""

    snapshot = models.ForeignKey(
        ForecastSnapshot,
        on_delete=models.CASCADE,
        related_name="resolutions",
    )
    weather_point = models.ForeignKey(
        WeatherPoint,
        on_delete=models.CASCADE,
        related_name="provider_resolutions",
    )
    requested_latitude = models.FloatField()
    requested_longitude = models.FloatField()
    requested_elevation_m = models.PositiveIntegerField(null=True, blank=True)
    elevation_requested = models.BooleanField(default=False)
    resolved_latitude = models.FloatField(null=True, blank=True)
    resolved_longitude = models.FloatField(null=True, blank=True)
    # Open-Meteo returned elevation — provider metadata only.
    resolved_elevation_m = models.FloatField(null=True, blank=True)
    utc_offset_seconds = models.IntegerField(null=True, blank=True)
    generationtime_ms = models.FloatField(null=True, blank=True)
    timezone_abbreviation = models.CharField(max_length=16, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["snapshot", "weather_point"],
                name="uniq_snapshot_weather_point_resolution",
            )
        ]
        indexes = [
            models.Index(fields=["weather_point", "snapshot"], name="fpr_point_snap_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.weather_point.slug}@{self.snapshot_id}"


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
    snapshot = models.ForeignKey(
        ForecastSnapshot,
        on_delete=models.CASCADE,
        related_name="hourly_records",
        null=True,
        blank=True,
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
    # Open-Meteo rain is the liquid precipitation component in mm for the hour.
    rain_mm = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    snowfall_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    visibility_km = models.DecimalField(max_digits=5, decimal_places=1)
    cloud_cover_pct = models.PositiveSmallIntegerField(null=True, blank=True)
    uv_index = models.PositiveSmallIntegerField(null=True, blank=True)
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
            models.Index(fields=["snapshot", "weather_point"], name="forecast_snap_point_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.weather_point.slug}@{self.forecast_at.isoformat()}"


class ForecastDaily(models.Model):
    """Legacy daily provider values retained while hourly snapshots are primary."""

    weather_point = models.ForeignKey(WeatherPoint, on_delete=models.CASCADE, related_name="daily_forecasts")
    forecast_date = models.DateField()
    sunrise_at = models.DateTimeField(null=True, blank=True)
    sunset_at = models.DateTimeField(null=True, blank=True)
    generated_at = models.DateTimeField()
    data_mode = models.CharField(max_length=16, default="demo")
    source = models.CharField(max_length=32, default="hawatch-demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")
    provider = models.CharField(max_length=32, default="demo")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["weather_point", "forecast_date", "seed_version"],
                name="uniq_daily_point_date_seed",
            )
        ]
        indexes = [
            models.Index(fields=["weather_point", "forecast_date"], name="daily_point_date_idx"),
            models.Index(fields=["generated_at"], name="daily_generated_idx"),
        ]


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
