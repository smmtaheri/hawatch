from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class Route(models.Model):
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
    distance_km = models.DecimalField(max_digits=5, decimal_places=1)
    ascent_m = models.PositiveIntegerField()
    round_trip_minutes = models.PositiveIntegerField()
    default_start_minutes = models.PositiveIntegerField()
    featured = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    origin_location = models.PointField(srid=4326, spatial_index=False)
    data_mode = models.CharField(max_length=16, default="demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")

    class Meta:
        indexes = [
            models.Index(fields=["destination", "sort_order"], name="route_dest_sort_idx"),
            models.Index(fields=["featured"], name="route_featured_idx"),
            GistIndex(fields=["origin_location"], name="route_origin_gist"),
        ]

    def __str__(self) -> str:
        return self.slug


class RoutePoint(models.Model):
    route = models.ForeignKey(Route, on_delete=models.CASCADE, related_name="points")
    destination = models.ForeignKey(
        "destinations.Destination",
        on_delete=models.PROTECT,
        related_name="route_points",
        null=True,
        blank=True,
    )
    slug = models.SlugField(max_length=80)
    name = models.CharField(max_length=80)
    elevation_m = models.PositiveIntegerField()
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    location = models.PointField(srid=4326, spatial_index=False)
    base_minutes = models.PositiveIntegerField()
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
            GistIndex(fields=["location"], name="routepoint_location_gist"),
        ]
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return f"{self.route.slug}:{self.slug}"
