from django.db import migrations, models


def mark_existing_fixture_route_points(apps, schema_editor):
    RoutePoint = apps.get_model("routes", "RoutePoint")
    RoutePoint.objects.filter(data_mode="live").update(fixture_managed=True)


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0008_route_runtime_flags"),
    ]

    operations = [
        migrations.AddField(
            model_name="routepoint",
            name="fixture_managed",
            field=models.BooleanField(
                default=False,
                help_text="True when created/updated from a JSON catalog import; prune only removes fixture_managed rows.",
            ),
        ),
        migrations.RunPython(mark_existing_fixture_route_points, migrations.RunPython.noop),
    ]
