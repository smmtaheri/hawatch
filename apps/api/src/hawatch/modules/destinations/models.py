from django.contrib.gis.db import models
from django.contrib.postgres.indexes import GistIndex


class Destination(models.Model):
    slug = models.SlugField(max_length=64, unique=True)
    tile_name = models.CharField(max_length=64)
    name = models.CharField(max_length=128)
    short_category = models.CharField(max_length=32)
    category = models.CharField(max_length=128)
    category_key = models.CharField(max_length=32)
    region = models.CharField(max_length=64)
    elevation_m = models.PositiveIntegerField()
    # Explicit GiST only — disable PointField's automatic spatial index to avoid duplicates.
    location = models.PointField(srid=4326, spatial_index=False)
    image = models.CharField(max_length=255)
    image_alt = models.CharField(max_length=255)
    popular_order = models.PositiveSmallIntegerField(default=0)
    climate = models.CharField(max_length=32)
    is_popular = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    aliases = models.JSONField(default=list, blank=True)
    data_mode = models.CharField(max_length=16, default="demo")
    seed_version = models.CharField(max_length=32, default="hawatch-demo-v1")

    class Meta:
        indexes = [
            models.Index(fields=["is_popular", "popular_order"], name="destination_is_popu_idx"),
            models.Index(fields=["is_active"], name="destination_is_acti_idx"),
            GistIndex(fields=["location"], name="destination_location_gist"),
        ]

    def __str__(self) -> str:
        return self.slug
