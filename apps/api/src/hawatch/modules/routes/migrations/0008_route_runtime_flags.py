from django.db import migrations, models


def mark_existing_fixture_routes(apps, schema_editor):
    Route = apps.get_model("routes", "Route")
    Route.objects.filter(data_mode="live").update(fixture_managed=True)


class Migration(migrations.Migration):
    dependencies = [
        ("routes", "0007_route_timing_status_default_pending"),
    ]

    operations = [
        migrations.AddField(
            model_name="route",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="route",
            name="fixture_managed",
            field=models.BooleanField(
                default=False,
                help_text="True when created/updated from a JSON catalog import; prune only removes fixture_managed rows.",
            ),
        ),
        migrations.AddField(
            model_name="route",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.RunPython(mark_existing_fixture_routes, migrations.RunPython.noop),
    ]
