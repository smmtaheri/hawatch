import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("forecasts", "0005_legacy_route_relation_name"),
        ("routes", "0002_disable_auto_spatial_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="routepoint",
            name="weather_point",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="route_points",
                to="forecasts.weatherpoint",
            ),
        )
    ]

