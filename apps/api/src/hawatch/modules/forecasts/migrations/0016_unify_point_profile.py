from django.db import migrations, models


def copy_profile_fields(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    Destination = apps.get_model("destinations", "Destination")
    for profile in Destination.objects.all().iterator():
        point = WeatherPoint.objects.filter(
            pk=getattr(profile, "weather_point_id", None)
        ).first()
        if point is None:
            point = WeatherPoint.objects.filter(destination_id=profile.pk).order_by("id").first()
        if point is None:
            continue
        point.tile_name = profile.tile_name
        point.short_category = profile.short_category
        point.category = profile.category
        point.category_key = profile.category_key
        point.region = profile.region
        point.image = profile.image
        point.image_alt = profile.image_alt
        point.popular_order = profile.popular_order
        point.is_popular = profile.is_popular
        point.climate = profile.climate
        point.is_active = profile.is_active
        point.aliases = list(dict.fromkeys([*(point.aliases or []), *(profile.aliases or [])]))
        point.kind = "primary"
        point.importance = "primary"
        point.seo_indexable = bool(profile.is_active)
        point.save(update_fields=[
            "tile_name", "short_category", "category", "category_key", "region",
            "image", "image_alt", "popular_order", "is_popular", "climate",
            "is_active", "aliases", "kind", "importance", "seo_indexable",
        ])
    WeatherPoint.objects.filter(kind="destination").update(kind="primary", importance="primary", seo_indexable=True)


class Migration(migrations.Migration):
    dependencies = [
        ("destinations", "0005_destination_popular_default"),
        ("forecasts", "0015_catalog_point_identity"),
    ]

    operations = [
        migrations.AddField("weatherpoint", "tile_name", models.CharField(blank=True, default="", max_length=64)),
        migrations.AddField("weatherpoint", "short_category", models.CharField(blank=True, default="", max_length=32)),
        migrations.AddField("weatherpoint", "category", models.CharField(blank=True, default="", max_length=128)),
        migrations.AddField("weatherpoint", "category_key", models.CharField(blank=True, default="", max_length=32)),
        migrations.AddField("weatherpoint", "region", models.CharField(blank=True, default="", max_length=64)),
        migrations.AddField("weatherpoint", "image", models.CharField(blank=True, default="", max_length=255)),
        migrations.AddField("weatherpoint", "image_alt", models.CharField(blank=True, default="", max_length=255)),
        migrations.AddField("weatherpoint", "popular_order", models.PositiveSmallIntegerField(default=0)),
        migrations.AddField("weatherpoint", "is_popular", models.BooleanField(default=False)),
        migrations.AddField("weatherpoint", "seo_indexable", models.BooleanField(default=False)),
        migrations.AlterField(
            model_name="weatherpoint",
            name="kind",
            field=models.CharField(choices=[("primary", "primary"), ("route_point", "route_point"), ("shared", "shared")], default="shared", max_length=16),
        ),
        migrations.RemoveIndex(
            model_name="weatherpoint",
            name="weatherpoint_kind_dest_idx",
        ),
        migrations.AddIndex(
            model_name="weatherpoint",
            index=models.Index(
                fields=["kind", "importance"],
                name="weatherpoint_kind_imp_idx",
            ),
        ),
        migrations.RunPython(copy_profile_fields, migrations.RunPython.noop),
        migrations.RemoveField("weatherpoint", "destination"),
    ]
