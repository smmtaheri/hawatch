from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("destinations", "0005_destination_popular_default"),
        ("forecasts", "0016_unify_point_profile"),
        ("routes", "0019_catalog_identity_cleanup"),
    ]

    operations = [
        migrations.RenameField(
            model_name="route",
            old_name="destination_label",
            new_name="target_label",
        ),
        migrations.RemoveIndex(
            model_name="route",
            name="route_dest_sort_idx",
        ),
        migrations.AddIndex(
            model_name="route",
            index=models.Index(
                fields=["target_weather_point", "sort_order"],
                name="route_target_sort_idx",
            ),
        ),
        migrations.RemoveIndex(
            model_name="routepoint",
            name="routepoint_dest_idx",
        ),
        migrations.RemoveField(model_name="route", name="destination"),
        migrations.RemoveField(model_name="routepoint", name="destination"),
    ]
