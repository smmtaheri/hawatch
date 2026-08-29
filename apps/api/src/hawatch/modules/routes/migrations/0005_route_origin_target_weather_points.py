# Additive origin/target WeatherPoint FKs on Route, backfilled from ordered points.

from django.db import migrations, models
import django.db.models.deletion


def backfill_route_endpoints(apps, schema_editor):
    Route = apps.get_model("routes", "Route")
    RoutePoint = apps.get_model("routes", "RoutePoint")

    for route in Route.objects.all():
        points = list(
            RoutePoint.objects.filter(route_id=route.id)
            .exclude(weather_point_id=None)
            .order_by("sort_order")
        )
        if not points:
            continue
        updates = []
        if route.origin_weather_point_id is None:
            route.origin_weather_point_id = points[0].weather_point_id
            updates.append("origin_weather_point_id")
        if route.target_weather_point_id is None:
            route.target_weather_point_id = points[-1].weather_point_id
            updates.append("target_weather_point_id")
        if updates:
            route.save(update_fields=updates)


def noop_reverse(apps, schema_editor):
    Route = apps.get_model("routes", "Route")
    Route.objects.all().update(origin_weather_point=None, target_weather_point=None)


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0004_route_weather_links"),
        ("forecasts", "0011_search_aliases"),
        ("destinations", "0004_destination_weather_point"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="origin_weather_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="origin_routes",
                to="forecasts.weatherpoint",
            ),
        ),
        migrations.AddField(
            model_name="route",
            name="target_weather_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="target_routes",
                to="forecasts.weatherpoint",
            ),
        ),
        migrations.AddIndex(
            model_name="route",
            index=models.Index(fields=["origin_weather_point"], name="route_origin_wp_idx"),
        ),
        migrations.AddIndex(
            model_name="route",
            index=models.Index(fields=["target_weather_point"], name="route_target_wp_idx"),
        ),
        migrations.RunPython(backfill_route_endpoints, noop_reverse),
    ]
