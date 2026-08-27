from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class Route(models.Model):
    class TimingStatus(models.TextChoices):
        CURATED = "curated", "curated"
        ESTIMATED = "estimated", "estimated"
        PENDING = "pending", "pending"

    slug = models.SlugField(max_length=80, unique=True)
    destination = models.ForeignKey(
        "destinations.Destination",
        on_delete=models.PROTECT,
        related_name="routes",
    )
    title = models.CharField(max_length=160)
    subtitle = models.CharField(max_length=255)
    trail_label = models.CharField(max_length=64)
    origin = models.CharField(max_length=64)
    destination_label = models.CharField(max_length=64)
    region = models.CharField(max_length=64)
    distance_km = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    ascent_m = models.PositiveIntegerField(null=True, blank=True)
    round_trip_minutes = models.PositiveIntegerField(null=True, blank=True)
    default_start_minutes = models.PositiveIntegerField(null=True, blank=True)
    timing_status = models.CharField(
        max_length=16,
        choices=TimingStatus.choices,
        default=TimingStatus.ESTIMATED,
    )
    featured = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    origin_location = models.PointField(srid=4326, spatial_index=False)
    catalog_key = models.SlugField(max_length=80, blank=True, default="")
    data_mode = models.CharField(max_length=16, default="demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")

    class Meta:
        indexes = [
            models.Index(fields=["destination", "sort_order"], name="route_dest_sort_idx"),
            models.Index(fields=["featured"], name="route_featured_idx"),
            models.Index(fields=["catalog_key"], name="route_catalog_key_idx"),
            GistIndex(fields=["origin_location"], name="route_origin_gist"),
        ]

    def __str__(self) -> str:
        return self.slug


class RoutePoint(models.Model):
    """Ordered link from a route to a shared WeatherPoint, plus UI/timing fields."""

    class TimingStatus(models.TextChoices):
        CURATED = "curated", "curated"
        ESTIMATED = "estimated", "estimated"
        PENDING = "pending", "pending"

    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="points")
    weather_point = models.ForeignKey(
        "forecasts.WeatherPoint",
        on_delete=models.PROTECT,
        related_name="route_links",
        null=True,
        blank=True,
    )
    destination = models.ForeignKey(
        "destinations.Destination",
        on_delete=models.PROTECT,
        related_name="route_points",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=80)
    name = models.CharField(max_length=80)
    # Denormalized display copies; catalog truth lives on WeatherPoint when linked.
    elevation_m = models.PositiveIntegerField(null=True, blank=True)
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    location = models.PointField(srid=4326, spatial_index=False, null=True, blank=True)
    # Legacy demo offset; prefer cumulative_minutes when curated.
    base_minutes = models.PositiveIntegerField(null=True, blank=True)
    segment_minutes = models.PositiveIntegerField(null=True, blank=True)
    cumulative_minutes = models.PositiveIntegerField(null=True, blank=True)
    segment_distance_m = models.PositiveIntegerField(null=True, blank=True)
    progress_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    timing_status = models.CharField(
        max_length=16,
        choices=TimingStatus.choices,
        default=TimingStatus.PENDING,
    )
    sort_order = models.PositiveSmallIntegerField()
    note = models.CharField(max_length=255, blank=True)
    axis_x = models.PositiveSmallIntegerField(default=10)
    axis_y = models.PositiveSmallIntegerField(default=50)
    data_mode = models.CharField(max_length=16, default="demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["route", "sort_order"], name="uniq_route_point_order"),
            models.UniqueConstraint(fields=["route", "slug"], name="uniq_route_point_slug"),
        ]
        indexes = [
            models.Index(fields=["route", "sort_order"], name="routepoint_route_sort_idx"),
            models.Index(fields=["slug"], name="routepoint_slug_idx"),
            models.Index(fields=["destination"], name="routepoint_dest_idx"),
            models.Index(fields=["weather_point"], name="routepoint_weather_idx"),
            GistIndex(fields=["location"], name="routepoint_location_gist"),
        ]
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return f"{self.route.slug}:{self.slug}"

    @property
    def effective_location(self):
        if self.weather_point_id and self.weather_point.location:
            return self.weather_point.location
        return self.location

    @property
    def effective_elevation_m(self) -> int | None:
        if self.weather_point_id:
            return self.weather_point.elevation_m
        return self.elevation_m
