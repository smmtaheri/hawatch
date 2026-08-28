from django.db import models


class SearchIndexEntry(models.Model):
    """Denormalized prefix-search row for destinations and canonical weather points."""

    class Kind(models.TextChoices):
        DESTINATION = "destination", "destination"
        POINT = "point", "point"

    class MatchKind(models.TextChoices):
        NAME = "name", "name"
        ALIAS = "alias", "alias"

    kind = models.CharField(max_length=16, choices=Kind.choices)
    match_kind = models.CharField(max_length=8, choices=MatchKind.choices, default=MatchKind.NAME)
    normalized_term = models.CharField(max_length=160)
    display_label = models.CharField(max_length=120)
    display_hint = models.CharField(max_length=160, blank=True, default="")
    destination_slug = models.CharField(max_length=80, blank=True, default="")
    weather_point_slug = models.CharField(max_length=96, blank=True, default="")
    rank = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_term", "rank"], name="search_term_rank_idx"),
            models.Index(fields=["kind", "weather_point_slug"], name="search_kind_point_idx"),
            models.Index(fields=["kind", "destination_slug"], name="search_kind_dest_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.display_label}"
