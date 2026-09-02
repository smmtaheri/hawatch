from django.db import migrations
from django.db.models.deletion import ProtectedError


POINT_LABELS = {
    "daryasar_spring": "چشمهٔ مسیر اسل‌محله تا دشت دریاسر",
    "damavand_icefall": "آبشار یخی دماوند",
    "damavand_northeast_north_join": "محل اتصال یال شمال‌شرقی به مسیر شمالی دماوند",
    "damavand_west_5008": "یال غربی دماوند · ارتفاع ۵۰۰۸ متر",
    "damavand_west_5326": "یال غربی دماوند · ارتفاع ۵۳۲۶ متر",
    "damavand_west_5505": "یال غربی دماوند · ارتفاع ۵۵۰۵ متر",
    "eskelim_mid_route_stop": "چشم‌انداز طلوع خورشید",
    "azadkouh_kelakbala_camp1": "کمپ اول مسیر کلاک",
    "azadkouh_kelakbala_camp2": "چشمهٔ کمپ دوم کلاک",
    "azadkouh_kelakbala_camp3": "کمپ سوم کلاک",
    "azadkouh_shirkamar_intersection": "محل اتصال شیرکمر به مسیر آزادکوه",
}

REMOVED_AZADKOUH_POINTS = {
    "azadkouh_final_slope",
    "azadkouh_nesen_rest",
    "azadkouh_sotak_rest",
}


def normalize_point_labels(apps, schema_editor):
    WeatherPoint = apps.get_model("forecasts", "WeatherPoint")
    RoutePoint = apps.get_model("routes", "RoutePoint")
    Route = apps.get_model("routes", "Route")

    for slug, name in POINT_LABELS.items():
        WeatherPoint.objects.filter(slug=slug).update(name=name)
        RoutePoint.objects.filter(weather_point__slug=slug).update(name=name)

    # These are generic, non-landmark labels. Remove them from route chains
    # while keeping the operation safe if a deployment has not imported the
    # Azadkouh catalog yet.
    removed_points = WeatherPoint.objects.filter(slug__in=REMOVED_AZADKOUH_POINTS)
    RoutePoint.objects.filter(weather_point__in=removed_points).delete()
    for point in list(removed_points):
        still_referenced = Route.objects.filter(
            origin_weather_point_id=point.pk
        ).exists() or Route.objects.filter(target_weather_point_id=point.pk).exists()
        if not still_referenced:
            try:
                point.delete()
                continue
            except ProtectedError:
                # Keep an unexpectedly shared legacy point out of public
                # catalog/ingest instead of making the whole migration fail.
                pass
        if still_referenced or point.pk:
            point.is_active = False
            point.ingest_enabled = False
            point.save(update_fields=["is_active", "ingest_enabled"])

    timing_versions = {
        "azadkouh-kelakbala": "azadkouh-timing-v2",
        "azadkouh-varangerud": "azadkouh-timing-v2",
        "azadkouh-nesen": "azadkouh-timing-v3",
        "azadkouh-nahiyeh": "azadkouh-timing-v4",
    }
    for slug, version in timing_versions.items():
        Route.objects.filter(slug=slug).update(timing_version=version)


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0010_routepoint_public_and_internal_notes"),
    ]

    operations = [
        migrations.RunPython(normalize_point_labels, migrations.RunPython.noop),
    ]
